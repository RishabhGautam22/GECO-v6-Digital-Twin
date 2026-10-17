"""
GECO v6 Max — OpenUSD 12-Bay Smart Hospital Scene Controller (`ward_scene_controller.py`)
=========================================================================================
Synchronizes live multi-room telemetry from the GECO v6.1+ simulation engine
or WebSocket stream directly onto the OpenUSD stage prims across all 12 bays
(10 Patients P01-P10, Bay 11 138-Part Metrology Rig, and Bay 12 IEEE-1588v2 PTP
Master Clock & SOC Command Center) of `geco_v6_smart_hospital_ward.usda`.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import omni.usd
    import omni.kit.viewport.utility as vp_util
    from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
    HAS_OMNI_USD = True
except ImportError:
    HAS_OMNI_USD = False


CAMERA_PRIM_PATHS: Dict[str, str] = {
    "OVERVIEW": "/World/Cameras/Cam_Ward_Overview",
    "WARD_TOP": "/World/Cameras/Cam_Ward_Top",
    "WARD_ORTHO_TOP": "/World/Cameras/Cam_Ward_Ortho_Top",
    "WARD_SIDE": "/World/Cameras/Cam_Ward_Side",
    "WARD_FRONT": "/World/Cameras/Cam_Ward_Front",
    "DASHBOARD": "/World/Cameras/Cam_LargeDashboardWall",
    "ROOM_01": "/World/Cameras/Cam_ROOM_01_PERSP",
    "ROOM_02": "/World/Cameras/Cam_ROOM_02_PERSP",
    "ROOM_03": "/World/Cameras/Cam_ROOM_03_PERSP",
    "ROOM_04": "/World/Cameras/Cam_ROOM_04_PERSP",
    "ROOM_05": "/World/Cameras/Cam_ROOM_05_PERSP",
    "ROOM_06": "/World/Cameras/Cam_ROOM_06_PERSP",
    "ROOM_07": "/World/Cameras/Cam_ROOM_07_PERSP",
    "ROOM_08": "/World/Cameras/Cam_ROOM_08_PERSP",
    "ROOM_09": "/World/Cameras/Cam_ROOM_09_PERSP",
    "ROOM_10": "/World/Cameras/Cam_ROOM_10_PERSP",
    "ROOM_11": "/World/Cameras/Cam_ROOM_11_PERSP",
    "ROOM_12": "/World/Cameras/Cam_ROOM_12_PERSP",
}

for _idx in range(1, 13):
    _r_id = f"ROOM_{_idx:02d}"
    for _mode in ("PERSP", "TOP", "SIDE", "FRONT", "ORTHO_TOP", "ORTHO_SIDE", "MACRO"):
        CAMERA_PRIM_PATHS[f"{_r_id}_{_mode}"] = f"/World/Cameras/Cam_{_r_id}_{_mode}"
    CAMERA_PRIM_PATHS[f"{_r_id}_ORTHO"] = f"/World/Cameras/Cam_{_r_id}_ORTHO_TOP"

PATIENT_BAY_PATHS: Dict[str, tuple[str, str, str]] = {
    "ROOM_01": ("Room_01_Nominal_Adult", "Patient_01_Adult_75kg", "Pump_01"),
    "ROOM_02": ("Room_02_Fluidic_Debris_And_Occlusion", "Patient_02_Adolescent_58kg", "Pump_02"),
    "ROOM_03": ("Room_03_Battery_Brownout_And_Malfunction", "Patient_03_Elderly_82kg", "Pump_03"),
    "ROOM_04": ("Room_04_Cyber_MITM_And_Simplex_Clamp", "Patient_04_Brittle_64kg", "Pump_04"),
    "ROOM_07": ("Room_07_Wet_Site_Adult_P05", "Patient_05_Adult_68kg", "Pump_05"),
    "ROOM_08": ("Room_08_PISA_Compression_P06", "Patient_06_Adult_71kg", "Pump_06"),
    "ROOM_09": ("Room_09_Clock_Skew_Dawn_P07", "Patient_07_Dawn_79kg", "Pump_07"),
    "ROOM_10": ("Room_10_Stealth_CUSUM_P08", "Patient_08_Sensitive_62kg", "Pump_08"),
    "ROOM_11": ("Room_11_Brittle_Variable_P09", "Patient_09_Brittle_55kg", "Pump_09"),
    "ROOM_12": ("Room_12_Unprimed_Line_P10", "Patient_10_Adult_73kg", "Pump_10"),
}


class WardSceneController:
    """Drives OpenUSD prim transforms, custom attributes, and PBR shaders for all 12 Bays."""

    def __init__(self, stage: Optional[Any] = None) -> None:
        self._stage = stage
        self._tick_counter: int = 0
        self._active_camera_key: str = "OVERVIEW"
        self._last_telemetry: Dict[str, Any] = {}

    @property
    def stage(self) -> Optional[Any]:
        if self._stage is not None:
            return self._stage
        if HAS_OMNI_USD:
            ctx = omni.usd.get_context()
            if ctx is not None:
                return ctx.get_stage()
        return None

    def load_ward_stage(self, usda_path: Optional[str] = None) -> bool:
        """Open `geco_v6_smart_hospital_ward.usda` in the Omniverse USD context."""
        if usda_path is None:
            default_path = (
                Path(__file__).resolve().parents[2]
                / "omniverse_usd"
                / "geco_v6_smart_hospital_ward.usda"
            )
            usda_path = str(default_path)
        if HAS_OMNI_USD:
            ctx = omni.usd.get_context()
            if ctx is not None:
                return bool(ctx.open_stage(usda_path))
        return False

    def switch_camera(self, room_key: str) -> str:
        """Switch the active Omniverse viewport camera to any of the 12 bays, per-room angles (TOP/SIDE/FRONT/ORTHO/MACRO), or ward overview."""
        key_u = room_key.strip().upper()
        if key_u.startswith("/WORLD/CAMERAS/"):
            cam_path = room_key.strip()
        else:
            cam_path = CAMERA_PRIM_PATHS.get(key_u, CAMERA_PRIM_PATHS["OVERVIEW"])
        self._active_camera_key = key_u
        if HAS_OMNI_USD:
            try:
                stage = self.stage
                if stage is None or not stage.GetPrimAtPath(cam_path).IsValid():
                    self.load_ward_stage()
                vp = vp_util.get_active_viewport()
                if vp is not None:
                    vp.camera_path = cam_path
            except Exception:
                pass
        return cam_path

    # ------------------------------------------------------------------
    # Low-Level USD Prim Helpers
    # ------------------------------------------------------------------

    def _set_translate(self, prim_path: str, x: float, y: float, z: float) -> None:
        stage = self.stage
        if stage is None or not HAS_OMNI_USD:
            return
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return
        attr = prim.GetAttribute("xformOp:translate")
        if not attr.IsValid():
            xform = UsdGeom.Xformable(prim)
            attr = xform.AddTranslateOp()
        attr.Set(Gf.Vec3d(float(x), float(y), float(z)))

    def _set_rotate_xyz(self, prim_path: str, rx: float, ry: float, rz: float) -> None:
        stage = self.stage
        if stage is None or not HAS_OMNI_USD:
            return
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return
        attr = prim.GetAttribute("xformOp:rotateXYZ")
        if not attr.IsValid():
            xform = UsdGeom.Xformable(prim)
            attr = xform.AddRotateXYZOp()
        attr.Set(Gf.Vec3f(float(rx), float(ry), float(rz)))

    def _set_scale(self, prim_path: str, sx: float, sy: float, sz: float) -> None:
        stage = self.stage
        if stage is None or not HAS_OMNI_USD:
            return
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return
        attr = prim.GetAttribute("xformOp:scale")
        if not attr.IsValid():
            xform = UsdGeom.Xformable(prim)
            attr = xform.AddScaleOp()
        attr.Set(Gf.Vec3f(float(sx), float(sy), float(sz)))

    def _set_custom_attr(self, prim_path: str, attr_name: str, value: Any, sdf_type: Any = None) -> None:
        stage = self.stage
        if stage is None or not HAS_OMNI_USD:
            return
        prim = stage.GetPrimAtPath(prim_path)
        if not prim.IsValid():
            return
        attr = prim.GetAttribute(attr_name)
        if not attr.IsValid() and sdf_type is not None:
            attr = prim.CreateAttribute(attr_name, sdf_type, True)
        if attr.IsValid():
            attr.Set(value)

    @staticmethod
    def _get_room_dict(rooms: Dict[str, Any], short_key: str, full_name: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        for k in (short_key, full_name, short_key.lower()):
            val = rooms.get(k)
            if isinstance(val, dict):
                return val
        return fallback

    # ------------------------------------------------------------------
    # Real-Time 12-Bay Telemetry Animation
    # ------------------------------------------------------------------

    def apply_ward_telemetry(self, payload: Dict[str, Any]) -> None:
        """
        Update all 12 bays on the OpenUSD stage from a GECO v6.1+ telemetry frame.
        """
        self._tick_counter += 1
        self._last_telemetry = payload
        phase = self._tick_counter * 0.15

        rooms = payload.get("rooms", {})
        r1 = self._get_room_dict(rooms, "ROOM_01", "Room_01_Nominal_Adult", payload)
        r2 = self._get_room_dict(rooms, "ROOM_02", "Room_02_Fluidic_Debris_And_Occlusion", payload)
        r3 = self._get_room_dict(rooms, "ROOM_03", "Room_03_Battery_Brownout_And_Malfunction", payload)
        r4 = self._get_room_dict(rooms, "ROOM_04", "Room_04_Cyber_MITM_And_Simplex_Clamp", payload)
        r5 = self._get_room_dict(rooms, "ROOM_05", "Room_05_IITP_Metrology_Lab", payload)

        self._animate_room_01_nominal(r1, phase)
        self._animate_room_02_pipe_debris(r2, phase)
        self._animate_room_03_battery_brownout(r3, phase)
        self._animate_room_04_cyber_mitm(r4, phase)
        self._animate_room_05_metrology_rig(r5, phase)
        self._animate_room_06_soc_center(rooms, payload.get("master_clock_ptp", {}), phase)

        # Animate CompleteHardwareStack & Patient vitals across all 10 Patient Bays (including Rooms 07-12)
        for short_key, (room_prim, pat_prim, pump_prim) in PATIENT_BAY_PATHS.items():
            rdata = self._get_room_dict(rooms, short_key, room_prim, {})
            if rdata:
                self._animate_patient_hardware_stack(room_prim, pat_prim, pump_prim, rdata, phase)

    def _animate_patient_hardware_stack(
        self,
        room_prim: str,
        pat_prim: str,
        pump_prim: str,
        data: Dict[str, Any],
        phase: float,
    ) -> None:
        base = f"/World/Ward/{room_prim}"
        bg = float(data.get("true_glucose_mgdl", data.get("bg_mg_dl", 115.0)) or 115.0)
        cgm = float(data.get("reported_cgm_mgdl", data.get("cgm_mg_dl", bg)) or bg)
        emitted_u = float(data.get("emitted_u", 0.08) or 0.08)
        flow_u_hr = float(data.get("effective_flow_u_hr", emitted_u * 12.0))

        self._set_custom_attr(f"{base}/{pat_prim}", "geco:bg_mg_dl", bg)
        self._set_custom_attr(f"{base}/{pat_prim}", "geco:cgm_mg_dl", cgm)
        self._set_rotate_xyz(f"{base}/{pump_prim}/StepperMotor", (phase * 40.0 * flow_u_hr) % 360.0, 0.0, 0.0)
        self._set_rotate_xyz(f"{base}/{pump_prim}/LeadScrew_M05", (phase * 40.0 * flow_u_hr) % 360.0, 0.0, 0.0)

        stack_base = f"{base}/{pat_prim}/CompleteHardwareStack"
        self._set_rotate_xyz(f"{stack_base}/Part_M05_LeadScrew", (phase * 45.0 * flow_u_hr) % 360.0, 0.0, 0.0)

        # Animate 3D Overhead CubicleScenarioBoard bars in each cubicle
        board_base = f"{base}/CubicleScenarioBoard"
        press_kpa = float(data.get("line_pressure_kpa", 14.2) or 14.2)
        bg_ratio = max(0.08, min(1.0, bg / 260.0))
        p_ratio = max(0.08, min(1.0, press_kpa / 100.0))
        self._set_scale(f"{board_base}/Bar_BG", 0.28, 0.015, 0.28 * bg_ratio)
        self._set_scale(f"{board_base}/Bar_Pressure", 0.28, 0.015, 0.28 * p_ratio)
        cinfo = data.get("cubicle_info") or {}
        if cinfo:
            self._set_custom_attr(board_base, "geco:active_scenario_code", str(cinfo.get("active_scenario_code", "")))
            self._set_custom_attr(board_base, "geco:active_scenario_name", str(cinfo.get("active_scenario_name", "")))

    def _animate_room_01_nominal(self, data: Dict[str, Any], phase: float) -> None:
        base = "/World/Ward/Room_01_Nominal_Adult"
        bg = float(data.get("bg_mg_dl", data.get("true_glucose_mgdl", 114.0)) or 114.0)
        cgm = float(data.get("cgm_mg_dl", data.get("reported_cgm_mgdl", 114.5)) or 114.5)
        iob = float(data.get("iob_u", 1.2) or 1.2)
        flow = float(data.get("effective_flow_u_hr", data.get("commanded_basal_u_hr", 1.0)) or 1.0)

        self._set_custom_attr(f"{base}/Patient_01_Adult_75kg", "geco:bg_mg_dl", bg)
        self._set_custom_attr(f"{base}/Patient_01_Adult_75kg", "geco:cgm_mg_dl", cgm)
        self._set_custom_attr(f"{base}/Patient_01_Adult_75kg", "geco:iob_u", iob)
        self._set_rotate_xyz(f"{base}/Pump_01/StepperMotor", (phase * 40.0 * flow) % 360.0, 0.0, 0.0)

    def _animate_room_02_pipe_debris(self, data: Dict[str, Any], phase: float) -> None:
        pipe_base = "/World/Ward/Room_02_Fluidic_Debris_And_Occlusion/InfusionPipe"
        debris_frac = float(
            data.get(
                "debris_occlusion_ratio",
                data.get("debris_fraction", data.get("pipe_debris_pct", 0.0) / 100.0),
            )
            or 0.0
        )
        bubble_ul = float(data.get("air_bubble_ul", 0.0) or 0.0)
        kink_ratio = float(data.get("cannula_kink_ratio", 0.0) or 0.0)
        pressure_kpa = float(
            data.get(
                "line_pressure_kpa",
                14.2 + 95.0 * (debris_frac ** 2) + 60.0 * (kink_ratio ** 2),
            )
            or 14.2
        )
        flow_u_hr = float(data.get("effective_flow_u_hr", max(0.05, 1.0 * (1.0 - 0.85 * debris_frac))))
        relief_open = bool(data.get("relief_valve_open", pressure_kpa > 65.0))

        self._set_custom_attr(pipe_base, "geco:debris_fraction", debris_frac)
        self._set_custom_attr(pipe_base, "geco:air_bubble_ul", bubble_ul)
        self._set_custom_attr(pipe_base, "geco:cannula_kink_ratio", kink_ratio)
        self._set_custom_attr(pipe_base, "geco:line_pressure_kpa", pressure_kpa)
        self._set_custom_attr(pipe_base, "geco:effective_flow_u_hr", flow_u_hr)
        self._set_custom_attr(pipe_base, "geco:relief_valve_open", relief_open)

        radial_expansion = 1.0 + min(0.38, max(0.0, (pressure_kpa - 14.0) / 160.0))
        self._set_scale(f"{pipe_base}/OuterLumen", 1.0, radial_expansion, radial_expansion)

        base_x_positions = [-0.16, -0.08, 0.01, 0.09, 0.16]
        for idx, _bx in enumerate(base_x_positions, start=1):
            drift = ((phase * 0.012 * flow_u_hr) + idx * 0.04) % 0.32 - 0.16
            lodge_x = 0.16 - (idx * 0.014)
            px = (1.0 - debris_frac) * drift + debris_frac * lodge_x
            py = 0.002 * math.sin(phase + idx)
            pz = 0.002 * math.cos(phase + idx)
            p_scale = 0.65 + 1.15 * debris_frac
            self._set_translate(f"{pipe_base}/DebrisParticles/Debris_0{idx}", px, py, pz)
            self._set_scale(f"{pipe_base}/DebrisParticles/Debris_0{idx}", p_scale, p_scale, p_scale)

        b_scale = max(0.2, min(2.2, 0.4 + bubble_ul / 15.0))
        for b_idx, bx0 in enumerate([-0.10, 0.05], start=1):
            bx = bx0 + 0.02 * math.sin(phase * 0.5 + b_idx)
            self._set_translate(f"{pipe_base}/AirBubbles/Bubble_0{b_idx}", bx, 0.0, 0.003)
            self._set_scale(f"{pipe_base}/AirBubbles/Bubble_0{b_idx}", b_scale * 1.3, b_scale * 0.9, b_scale * 0.9)

        kink_angle = kink_ratio * 34.0
        kink_pinch = max(0.28, 1.0 - 0.65 * kink_ratio)
        self._set_rotate_xyz(f"{pipe_base}/CannulaKinkZone", 0.0, kink_angle, 0.0)
        self._set_scale(f"{pipe_base}/CannulaKinkZone", 1.0, kink_pinch, kink_pinch)

        valve_z = 0.036 if relief_open else 0.024
        self._set_translate(f"{pipe_base}/BackPressureReliefValve", 0.12, 0.0, valve_z)

    def _animate_room_03_battery_brownout(self, data: Dict[str, Any], phase: float) -> None:
        pump_base = "/World/Ward/Room_03_Battery_Brownout_And_Malfunction/Pump_03"
        soc = float(data.get("battery_soc", 0.88) or 0.88)
        r_int = float(data.get("battery_r_int_ohm", 0.18) or 0.18)
        v_term = float(data.get("battery_v_term", data.get("battery_terminal_v", 3.2 + 0.95 * soc - 0.25 * r_int)) or 3.85)
        brownout = bool(data.get("brownout_tripped", v_term < 3.05))
        stiction = bool(data.get("stiction_fault", int(data.get("motor_lost_steps", 0) or 0) > 0))
        power_state = "BROWNOUT_SAFE_HOLD" if brownout else ("LOW_VOLTAGE_WARN" if v_term < 3.35 else "NOMINAL")

        cell_path = f"{pump_base}/BatteryPack/LiIon_Cell"
        self._set_custom_attr(cell_path, "geco:soc", soc)
        self._set_custom_attr(cell_path, "geco:v_term", v_term)
        self._set_custom_attr(cell_path, "geco:r_int_ohm", r_int)
        self._set_custom_attr(cell_path, "geco:power_state", power_state)

        self._set_custom_attr(f"{pump_base}/PowerRegulation/BrownoutWatchdog", "geco:brownout_tripped", brownout)
        self._set_custom_attr(f"{pump_base}/Actuator/StepperMotor_M03", "geco:stiction_fault", stiction)

        if not brownout and not stiction:
            rot_deg = (phase * 55.0) % 360.0
        elif stiction:
            rot_deg = 8.0 * math.sin(phase * 6.0)
        else:
            rot_deg = 0.0

        self._set_rotate_xyz(f"{pump_base}/Actuator/StepperMotor_M03", rot_deg, 0.0, 0.0)
        self._set_rotate_xyz(f"{pump_base}/Actuator/OpticalEncoder", rot_deg, 0.0, 0.0)
        self._set_rotate_xyz(f"{pump_base}/Actuator/LeadScrew_BacklashZone", rot_deg, 0.0, 0.0)

        self._set_custom_attr(f"{pump_base}/Safety/FailSafeRelay", "geco:relay_closed", not brownout)
        self._set_custom_attr(f"{pump_base}/Safety/PinchValve", "geco:pinch_engaged", brownout)
        pinch_z = -0.008 if brownout else 0.0
        self._set_translate(f"{pump_base}/Safety/PinchValve", 0.02, 0.0, pinch_z)

    def _animate_room_04_cyber_mitm(self, data: Dict[str, Any], phase: float) -> None:
        r4_base = "/World/Ward/Room_04_Cyber_MITM_And_Simplex_Clamp"
        attr_info = data.get("root_cause_attribution") or {}
        attack_active = bool(data.get("attack_active", attr_info.get("is_cyber_attack", False)))
        attack_mode = str(data.get("attack_mode", data.get("active_scenario", "NONE")))
        simplex_engaged = bool(
            data.get(
                "simplex_clamp_engaged",
                attack_active or data.get("safety_kernel_mode") not in (None, "RUN", "CLOSED_LOOP"),
            )
        )

        sdr_base = f"{r4_base}/Rogue_MITM_Transceiver"
        self._set_custom_attr(sdr_base, "geco:attack_active", attack_active)
        self._set_custom_attr(sdr_base, "geco:attack_mode", attack_mode)
        self._set_custom_attr(f"{r4_base}/GECO_v61_Security_Gateway", "geco:simplex_clamp_engaged", simplex_engaged)

        for idx in (1, 2, 3):
            if attack_active:
                wave_scale = 0.85 + 0.55 * ((math.sin(phase * 2.5 - idx * 0.9) + 1.0) * 0.5)
            else:
                wave_scale = 0.05
            self._set_scale(f"{sdr_base}/RF_WaveRing_0{idx}", wave_scale, wave_scale, 1.0)

        dome_scale = 1.15 + 0.08 * math.sin(phase * 3.0) if simplex_engaged else 0.25
        self._set_scale(f"{r4_base}/SimplexSafeBasalClamp/SimplexShieldDome", dome_scale, dome_scale, dome_scale)

    def _animate_room_05_metrology_rig(self, data: Dict[str, Any], phase: float) -> None:
        rig_base = "/World/Ward/Room_05_IITP_Metrology_Lab/MetrologyRig_130Part_Assembly"
        plunger_travel_mm = float(data.get("plunger_travel_mm", (self._tick_counter * 0.08) % 45.0))
        delivered_mass_g = float(data.get("delivered_mass_g", plunger_travel_mm * 0.452))
        valve_tripped = bool(data.get("pinch_valve_tripped", False))

        dx_m = plunger_travel_mm / 1000.0
        screw_deg = (plunger_travel_mm * 180.0) % 360.0

        self._set_rotate_xyz(f"{rig_base}/Actuator_And_Mechanism/Part_M05", screw_deg, 0.0, 0.0)
        self._set_translate(f"{rig_base}/Actuator_And_Mechanism/Part_M07", 0.145 + dx_m, 0.144, 0.056)
        self._set_translate(f"{rig_base}/Actuator_And_Mechanism/Part_M08", 0.150 + dx_m, 0.144, 0.088)
        self._set_translate(f"{rig_base}/Syringe_Assembly/Part_S03", 0.211 + dx_m, 0.144, 0.102)
        self._set_translate(f"{rig_base}/Syringe_Assembly/Part_S04", 0.181 + dx_m, 0.144, 0.102)
        self._set_translate(f"{rig_base}/Syringe_Assembly/Part_S05", 0.153 + dx_m, 0.144, 0.102)

        v01_z = 0.043 if valve_tripped else 0.049
        self._set_translate(f"{rig_base}/Pinch_Valve_Safety/Part_V01", 0.365, 0.135, v01_z)

        pan_deflect_m = min(0.0015, delivered_mass_g * 0.00004)
        self._set_translate(
            f"{rig_base}/Gravimetric_Balance_And_Fluid_Path/Part_T02",
            0.488,
            0.158,
            0.054 - pan_deflect_m,
        )

    def _animate_room_06_soc_center(self, rooms: Dict[str, Any], ptp_clock: Dict[str, Any], phase: float) -> None:
        soc_base = "/World/Ward/Room_06_SOC_Command_Center"
        room_dicts = [r for r in rooms.values() if isinstance(r, dict)]
        any_alarm = any(
            bool(
                r.get("alarm_active", False)
                or r.get("simplex_clamp_engaged", False)
                or r.get("brownout_tripped", False)
                or (r.get("root_cause_attribution") or {}).get("category", "NOMINAL") != "NOMINAL"
            )
            for r in room_dicts
        )
        state_str = "ALARM_SIMPLEX_CLAMP" if any_alarm else "NORMAL"
        self._set_custom_attr(f"{soc_base}/MasterAlarmBeacon", "geco:ward_alarm_state", state_str)
        beacon_rot = (phase * 120.0) % 360.0 if any_alarm else 0.0
        self._set_rotate_xyz(f"{soc_base}/MasterAlarmBeacon", 0.0, 0.0, beacon_rot)

        # Animate LargeWallDashboardScreen 3D bars with live ward aggregates
        dash_base = f"{soc_base}/LargeWallDashboardScreen"
        bgs = [float(r.get("true_glucose_mgdl", r.get("bg_mg_dl", 118.0)) or 118.0) for r in room_dicts] or [118.0]
        mean_bg = sum(bgs) / max(1, len(bgs))
        in_range = sum(1 for b in bgs if 70.0 <= b <= 180.0) / max(1, len(bgs))
        max_p = max([float(r.get("line_pressure_kpa", 14.2) or 14.2) for r in room_dicts] or [14.2])
        min_v = min([float(r.get("battery_terminal_v", r.get("battery_v_term", 3.98)) or 3.98) for r in room_dicts] or [3.98])
        max_cusum = max([float((r.get("detector") or {}).get("cusum_fast", 0.35) or 0.35) for r in room_dicts] or [0.35])
        alarm_cnt = sum(1 for r in room_dicts if r.get("alarm_active") or r.get("attack_active"))

        bars = [
            ("Bar_WardMeanBG", -1.35, max(0.08, min(1.0, mean_bg / 250.0))),
            ("Bar_WardTIR", -0.81, max(0.08, min(1.0, in_range))),
            ("Bar_MaxLinePressure", -0.27, max(0.08, min(1.0, max_p / 110.0))),
            ("Bar_MinBatteryV", 0.27, max(0.08, min(1.0, (min_v - 2.5) / 1.7))),
            ("Bar_MaxCUSUM", 0.81, max(0.08, min(1.0, max_cusum / 10.0))),
            ("Bar_ActiveAlarms", 1.35, max(0.08, min(1.0, alarm_cnt / 8.0))),
        ]
        for b_name, bx, ratio in bars:
            bh = 0.88 * ratio
            bz = -0.68 + 0.5 * bh
            self._set_scale(f"{dash_base}/{b_name}", 0.34, 0.02, bh)
            self._set_translate(f"{dash_base}/{b_name}", bx, -0.045, bz)

        # Pulse Optical Sync Beacon Part_A06 at 10Hz phase
        ptp_base = f"{soc_base}/MasterClock_PTP_Hub"
        if ptp_clock:
            self._set_custom_attr(ptp_base, "geco:monotonic_tick", int(ptp_clock.get("monotonic_tick", 0)))
        strobe_scale = 1.0 + 0.18 * abs(math.sin(phase * 4.0))
        self._set_scale(f"{ptp_base}/Part_A06_Optical_Sync_Strobe", strobe_scale, strobe_scale, strobe_scale)
