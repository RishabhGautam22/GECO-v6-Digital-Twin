"""
GECO v6 Max — Omniverse Isaac Sim 6.1.0 Kit Extension Entrypoint (`extension.py`)
=================================================================================
Implements `omni.ext.IExt` for `geco.v6.omniverse.ward`, bridging the OpenUSD
6-Room Smart Hospital Ward & 130-Part Metrology Rig with the GECO v6.1+
Multi-Room WebSocket Server (`ws://127.0.0.1:8766`).
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import threading
import time
from typing import Any, Dict, Optional

try:
    import omni.ext
    import omni.kit.app
    import omni.usd
    BaseExt = omni.ext.IExt
    HAS_OMNI_EXT = True
except ImportError:
    BaseExt = object
    HAS_OMNI_EXT = False

from .ward_scene_controller import WardSceneController
from .ward_ui import WardControlPanelUI


class GecoOmniverseWardExtension(BaseExt):
    """Omniverse Kit Extension lifecycle manager for GECO v6 Max."""

    def __init__(self) -> None:
        super().__init__()
        self.ws_uri: str = os.environ.get("GECO_WS_URI", "ws://127.0.0.1:8766")
        self.controller: Optional[WardSceneController] = None
        self.ui_panel: Optional[WardControlPanelUI] = None
        self._update_sub: Optional[Any] = None
        self._selection_sub: Optional[Any] = None
        self._stop_event = threading.Event()
        self._incoming_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=8)
        self._outgoing_queue: "queue.Queue[Dict[str, Any]]" = queue.Queue(maxsize=32)
        self._ws_thread: Optional[threading.Thread] = None
        self._local_overrides: Dict[str, Any] = {}
        self._frame_count: int = 0
        self._stage_loaded: bool = False

    def on_startup(self, ext_id: str = "geco.v6.omniverse.ward") -> None:
        print(f"[geco.v6.omniverse.ward] Starting extension ({ext_id}), target WS={self.ws_uri}")
        self.controller = WardSceneController()
        if not HAS_OMNI_EXT:
            self.controller.load_ward_stage()
            self._stage_loaded = True

        self.ui_panel = WardControlPanelUI(
            on_camera_select=self._handle_camera_select,
            on_command_send=self._handle_command_send,
        )

        self._stop_event.clear()
        self._ws_thread = threading.Thread(target=self._ws_worker_loop, daemon=True)
        self._ws_thread.start()

        if HAS_OMNI_EXT:
            app = omni.kit.app.get_app()
            stream = app.get_update_event_stream()
            self._update_sub = stream.create_subscription_to_pop(
                self._on_kit_update, name="geco_v6_ward_stage_sync"
            )
            try:
                usd_ctx = omni.usd.get_context()
                self._selection_sub = usd_ctx.get_stage_event_stream().create_subscription_to_pop(
                    self._on_stage_event, name="geco_v6_prim_click_observer"
                )
            except Exception:
                self._selection_sub = None

    def _on_stage_event(self, event: Any) -> None:
        try:
            if int(event.type) == int(omni.usd.StageEventType.SELECTION_CHANGED):
                paths = omni.usd.get_context().get_selection().get_selected_prim_paths()
                if self.ui_panel is not None and paths:
                    self.ui_panel.on_prim_selected(list(paths))
        except Exception:
            pass

    def on_shutdown(self) -> None:
        print("[geco.v6.omniverse.ward] Shutting down extension")
        self._stop_event.set()
        self._update_sub = None
        self._selection_sub = None
        if self.ui_panel is not None:
            self.ui_panel.destroy()
            self.ui_panel = None
        self.controller = None

    def _handle_camera_select(self, room_key: str) -> None:
        if self.controller is not None:
            cam_path = self.controller.switch_camera(room_key)
            if self.ui_panel is not None:
                self.ui_panel.update_status(f"Active Camera: {cam_path}")

    def _handle_command_send(self, cmd: Dict[str, Any]) -> None:
        # Store local override immediately for responsive USD stage feedback AND queue for WebSocket server
        fault_type = cmd.get("fault_type", "")
        params = cmd.get("params", {})
        if fault_type == "CLEAR_ALL_FAULTS":
            self._local_overrides.clear()
        else:
            room_key = params.get("room", "ROOM_02")
            self._local_overrides.setdefault(room_key, {}).update(params)

        try:
            self._outgoing_queue.put_nowait(cmd)
        except queue.Full:
            pass

        if self.ui_panel is not None:
            self.ui_panel.update_status(f"Injected Command: {fault_type}")

    def _on_kit_update(self, _event: Any) -> None:
        if self.controller is None:
            return
        self._frame_count += 1
        if not self._stage_loaded and self._frame_count == 25:
            self._stage_loaded = True
            self.controller.load_ward_stage()
        elif self._frame_count == 40:
            try:
                from omni.kit.viewport.utility import get_active_viewport, frame_viewport_selection
                usd_ctx = omni.usd.get_context()
                usd_ctx.get_selection().set_selected_prim_paths(["/World/Ward"], True)
                vp = get_active_viewport()
                if vp is not None:
                    frame_viewport_selection(vp)
            except Exception:
                pass
        elif self._frame_count == 45:
            try:
                omni.usd.get_context().get_selection().clear_selected_prim_paths()
            except Exception:
                pass
        latest: Optional[Dict[str, Any]] = None
        while not self._incoming_queue.empty():
            try:
                latest = self._incoming_queue.get_nowait()
            except queue.Empty:
                break

        if latest is not None:
            self._last_ws_frame = latest
        elif getattr(self, "_last_ws_frame", None) is not None:
            if self._frame_count % 15 != 0:
                return
            latest = self._last_ws_frame
        else:
            if self._frame_count % 15 != 0:
                return
            latest = self._synthesize_fallback_frame()

        rooms_dict = latest.get("rooms", {})
        for r_key, ov in self._local_overrides.items():
            if r_key in rooms_dict and isinstance(rooms_dict[r_key], dict):
                rooms_dict[r_key].update(ov)

        self.controller.apply_ward_telemetry(latest)
        if self.ui_panel is not None:
            self.ui_panel.update_telemetry_labels(latest)

    def _synthesize_fallback_frame(self) -> Dict[str, Any]:
        rooms: Dict[str, Dict[str, Any]] = {
            "ROOM_01": {"bg_mg_dl": 114.0, "cgm_mg_dl": 114.5, "iob_u": 1.22, "line_pressure_kpa": 1.8, "battery_v_term": 4.02},
            "ROOM_02": {"bg_mg_dl": 132.0, "cgm_mg_dl": 130.5, "debris_fraction": 0.72, "air_bubble_ul": 14.0, "cannula_kink_ratio": 0.15, "line_pressure_kpa": 38.5, "battery_v_term": 3.98},
            "ROOM_03": {"bg_mg_dl": 124.0, "cgm_mg_dl": 125.0, "battery_soc": 0.12, "battery_r_int_ohm": 1.45, "battery_v_term": 3.12, "brownout_tripped": True, "stiction_fault": False, "line_pressure_kpa": 2.1},
            "ROOM_04": {"bg_mg_dl": 118.0, "cgm_mg_dl": 158.0, "attack_active": True, "attack_mode": "cgm_bias_40", "simplex_clamp_engaged": True, "line_pressure_kpa": 1.9, "battery_v_term": 4.00},
            "ROOM_05": {"bg_mg_dl": 110.0, "cgm_mg_dl": 135.0, "line_pressure_kpa": 2.0, "battery_v_term": 4.05},
            "ROOM_07": {"bg_mg_dl": 165.0, "cgm_mg_dl": 164.0, "line_pressure_kpa": 0.14, "battery_v_term": 4.01},
            "ROOM_08": {"bg_mg_dl": 112.0, "cgm_mg_dl": 76.0, "line_pressure_kpa": 1.8, "battery_v_term": 4.00},
            "ROOM_09": {"bg_mg_dl": 128.0, "cgm_mg_dl": 127.0, "line_pressure_kpa": 1.9, "battery_v_term": 3.99},
            "ROOM_10": {"bg_mg_dl": 94.0, "cgm_mg_dl": 95.0, "line_pressure_kpa": 2.1, "battery_v_term": 3.97},
            "ROOM_11": {"bg_mg_dl": 108.0, "cgm_mg_dl": 109.0, "line_pressure_kpa": 2.2, "battery_v_term": 3.98},
            "ROOM_12": {"bg_mg_dl": 172.0, "cgm_mg_dl": 170.0, "line_pressure_kpa": 0.08, "battery_v_term": 4.02},
        }
        for r_key, ov in self._local_overrides.items():
            if r_key in rooms:
                rooms[r_key].update(ov)
        return {"rooms": rooms}

    def _ws_worker_loop(self) -> None:
        try:
            import websockets  # type: ignore
        except ImportError:
            import pathlib
            import sys
            for cand in [
                "/home/axion/twin/omniverse/runtime/isaac-sim-6.1.0/extscache/omni.kit.pip_archive-0.0.0+00c488ae.la64.cp312/pip_prebundle",
                "/home/axion/twin/omniverse/venvs/tools/lib/python3.12/site-packages",
            ]:
                if pathlib.Path(cand).exists() and cand not in sys.path:
                    sys.path.append(cand)
            try:
                import websockets  # type: ignore
            except ImportError:
                print("[geco.v6.omniverse.ward] Could not import websockets in Kit environment")
                return

        async def _connect_and_stream() -> None:
            while not self._stop_event.is_set():
                try:
                    async with websockets.connect(self.ws_uri) as ws:
                        print(f"[geco.v6.omniverse.ward] Connected to {self.ws_uri}")
                        if self.ui_panel is not None:
                            self.ui_panel.update_status(f"Connected: {self.ws_uri}")
                        while not self._stop_event.is_set():
                            while not self._outgoing_queue.empty():
                                cmd = self._outgoing_queue.get_nowait()
                                await ws.send(json.dumps(cmd))
                            try:
                                raw = await asyncio.wait_for(ws.recv(), timeout=0.05)
                                data = json.loads(raw)
                                if self._incoming_queue.full():
                                    try:
                                        self._incoming_queue.get_nowait()
                                    except queue.Empty:
                                        pass
                                self._incoming_queue.put_nowait(data)
                            except asyncio.TimeoutError:
                                pass
                except Exception:
                    time.sleep(1.5)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_connect_and_stream())
