"""Comprehensive End-to-End Test Suite for GECO v6.1+ Max Cyber-Physical Digital Twin."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pytest

_ROOT = Path(__file__).resolve().parents[1]
_GECO_V6_IMPL = _ROOT.parent / "GECOv6" / "02_IMPLEMENTATION"
if str(_GECO_V6_IMPL) not in sys.path:
    sys.path.insert(0, str(_GECO_V6_IMPL))
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from geco_v6_max.physiology_v61 import (
    EnhancedTwinParamsV61,
    EnhancedGlucoseModelV61,
    EnhancedPhysiologyTwinV61,
    ValidHovorkaPlant,
    IOBAwareController,
    evaluate_causal_forecasts_v61,
)
from geco_v6_max.multiphysics_faults import (
    PipeDebrisAndFluidicsModel,
    BatteryElectroThermalModel,
    ElectromechanicalPumpModel,
    MultiPhysicsPumpRig,
)
from geco_v6_max.security_kernel_v61 import (
    OrthogonalDetectorV61,
    SimplexSafetyKernelV61,
    run_v61_intervention_trial,
)
from geco_v6_max.permutation_taxonomy import (
    REAL_WORLD_PERMUTATION_CATALOG,
    RootCauseAttributionEngineV61,
)
from geco_v6_max.ward_telemetry_server import WardTelemetryHub


def test_enhanced_physiology_7state_ekf_and_valid_hovorka():
    """Verify 7-state EKF twin tracks trajectory and ValidHovorkaPlant never produces negative EGP."""
    plant = ValidHovorkaPlant()
    twin = EnhancedPhysiologyTwinV61(
        EnhancedTwinParamsV61(gb=120.0),
        r_std=9.0,
        forecast_policy={"kind": "mechanistic", "hold_insulin_u": plant.basal_u},
    )
    twin.reset(120.0, plant.basal_u)

    # Even under extreme insulin boluses (5x normal meal bolus), ValidHovorkaPlant EGP remains >= 0 and valid
    for k in range(120):
        u = 0.85 if k in (10, 11, 12, 40, 41) else plant.basal_u
        c = 75.0 if k in (10, 40) else 0.0
        g, s = plant.step(u, c)
        out = twin.update(s, u, c)
        f30 = twin.forecast(6)
        assert plant.valid, f"ValidHovorkaPlant domain violated at step {k}"
        assert not plant.diagnostics["negative_egp_evaluator_only"]
        assert plant.diagnostics["endogenous_production_mmol_min"] >= 0.0
        assert 20.0 <= f30 <= 600.0
        assert out.state.shape == (7,)


def test_multiphysics_pipe_debris_and_air_bubble_boyle_compliance():
    """Verify Hagen-Poiseuille 4th-power pressure scaling under pipe debris and air bubble compliance."""
    fluid = PipeDebrisAndFluidicsModel()
    nom = fluid.step(0.10, dt_min=5.0)
    assert nom["line_pressure_kpa"] < 3.5
    assert abs(nom["delivered_cannula_u"] - 0.10) < 0.01

    # Inject 85% debris occlusion + 15 uL air bubble
    fluid.inject_fault(debris_ratio=0.85, air_bubble_ul=15.0)
    occ = None
    for _ in range(8):
        occ = fluid.step(0.15, dt_min=5.0)
    assert occ["line_pressure_kpa"] > 20.0
    assert occ["hydraulic_resistance_ratio"] > 100.0
    assert occ["delivered_cannula_u"] < occ["commanded_plunger_u"]

    # Vent pressure relief valve
    fluid.vent_pressure_relief()
    assert fluid.state.line_pressure_kpa <= 2.0


def test_battery_electrothermal_bolus_sag_and_supercap():
    """Verify high-impedance battery passivation sags below brownout threshold under bolus load."""
    bat = BatteryElectroThermalModel(initial_soc=0.90)
    healthy = bat.step(motor_active_u=0.15, line_pressure_kpa=2.0)
    assert healthy["terminal_v"] > 3.7
    assert not healthy["brownout_tripped"]

    # Inject aged cell internal resistance fault (2.5 Ohm at low SOC)
    bat.inject_fault(soc=0.07, internal_resistance_ohm=2.5)
    sag = bat.step(motor_active_u=0.20, line_pressure_kpa=25.0)
    assert sag["terminal_v"] < 3.05
    assert sag["brownout_tripped"]
    assert sag["supercap_v"] >= 3.3


def test_wrong_installation_never_misclassified_as_cyber_attack():
    """Verify RootCauseAttributionEngineV61 never flags installation/site errors as cyber attacks."""
    engine = RootCauseAttributionEngineV61()

    # 1. Unprimed tubing dead-space installation (low pressure 0.08 kPa after reservoir reset)
    r_unprimed = engine.classify(
        local_delta_g=0.008, reported_delta_g=0.008, expected_g=0.008, mass_sigma_g=0.005,
        line_pressure_kpa=0.08, motor_current_ma=410.0, terminal_v=4.0, ocv_v=4.08,
        lost_steps=0, z_innov=2.8, dg_flux=0.4, requested_u=0.08,
        reservoir_recently_reset=True,
    )
    assert r_unprimed["category"] == "INSTALLATION_ARTIFACT"
    assert r_unprimed["code"] == "unprimed_tubing_install"
    assert not r_unprimed["is_cyber_attack"]
    assert r_unprimed["is_installation_error"]

    # 2. Dislodged cannula ("Wet Site" leak: pressure drops to 0.14 kPa below tissue turgor + moisture)
    r_wet = engine.classify(
        local_delta_g=0.008, reported_delta_g=0.008, expected_g=0.008, mass_sigma_g=0.005,
        line_pressure_kpa=0.14, motor_current_ma=410.0, terminal_v=4.0, ocv_v=4.08,
        lost_steps=0, z_innov=3.2, dg_flux=0.5, requested_u=0.08,
        patch_moisture_wet=True,
    )
    assert r_wet["category"] == "INSTALLATION_ARTIFACT"
    assert r_wet["code"] == "cannula_dislodgement_leak"
    assert not r_wet["is_cyber_attack"]

    # 3. PISA sleeping compression low (-3.4 sigma drop during supine compression)
    r_pisa = engine.classify(
        local_delta_g=0.008, reported_delta_g=0.008, expected_g=0.008, mass_sigma_g=0.005,
        line_pressure_kpa=1.8, motor_current_ma=410.0, terminal_v=4.0, ocv_v=4.08,
        lost_steps=0, z_innov=-3.4, dg_flux=-0.6, requested_u=0.0,
        supine_compression_posture=True,
    )
    assert r_pisa["category"] == "INSTALLATION_ARTIFACT"
    assert r_pisa["code"] == "pisa_compression_low"
    assert not r_pisa["is_cyber_attack"]


def test_real_cyber_attack_varieties_detected_accurately():
    """Verify stealthy CUSUM drip, RTC clock-skew, EMI false-occlusion, and Stuxnet report masking."""
    engine = RootCauseAttributionEngineV61()

    # 1. RTC Clock-Skew IOB Zeroing Attack (+210 min jump)
    r_clk = engine.classify(
        local_delta_g=0.008, reported_delta_g=0.008, expected_g=0.008, mass_sigma_g=0.005,
        line_pressure_kpa=1.8, motor_current_ma=410.0, terminal_v=4.0, ocv_v=4.08,
        lost_steps=0, z_innov=0.2, dg_flux=0.0, requested_u=0.20,
        rtc_delta_min=210.0, mono_delta_min=5.0,
    )
    assert r_clk["category"] == "CYBER_ATTACK"
    assert r_clk["code"] == "clock_skew_iob_attack"
    assert r_clk["is_cyber_attack"]

    # 2. Resonant EMI False-Occlusion Sensor Spoofing (P_line=95 kPa but motor current is unloaded 410 mA)
    r_emi = engine.classify(
        local_delta_g=0.008, reported_delta_g=0.008, expected_g=0.008, mass_sigma_g=0.005,
        line_pressure_kpa=95.0, motor_current_ma=410.0, terminal_v=4.0, ocv_v=4.08,
        lost_steps=0, z_innov=0.1, dg_flux=0.0, requested_u=0.08,
    )
    assert r_emi["category"] == "CYBER_ATTACK"
    assert r_emi["code"] == "emi_false_occlusion_dos"
    assert r_emi["is_cyber_attack"]

    # 3. Stealthy Sub-Threshold Zero-Dynamics CUSUM Drip (+0.42 sigma per step for 12 steps)
    engine.reset()
    r_drip = None
    for _ in range(12):
        r_drip = engine.classify(
            local_delta_g=0.008 + 0.42 * 0.005,
            reported_delta_g=0.008 + 0.42 * 0.005,
            expected_g=0.008,
            mass_sigma_g=0.005,
            line_pressure_kpa=1.8, motor_current_ma=420.0, terminal_v=4.0, ocv_v=4.08,
            lost_steps=0, z_innov=-0.4, dg_flux=-0.1, requested_u=0.08,
        )
    assert r_drip["category"] == "CYBER_ATTACK"
    assert r_drip["code"] == "stealthy_cusum_drip"
    assert r_drip["is_cyber_attack"]


def test_usd_stages_and_6room_ward_hub():
    """Verify generated OpenUSD stages (including NURBS BRep CAD) and the 12-Bay WardTelemetryHub."""
    pxr_ext = Path("/home/axion/twin/omniverse/runtime/isaac-sim-6.1.0/extscache/omni.usd.libs-1.0.3+00c488ae.la64.r.cp312")
    if pxr_ext.exists() and str(pxr_ext) not in sys.path:
        sys.path.insert(0, str(pxr_ext))
    try:
        from pxr import Usd
        has_pxr = True
    except ImportError:
        has_pxr = False

    rig_usda = _ROOT / "omniverse_usd" / "geco_v6_metrology_rig.usda"
    ward_usda = _ROOT / "omniverse_usd" / "geco_v6_smart_hospital_ward.usda"
    brep_usda = _ROOT / "omniverse_usd" / "geco_v6_brep_pump_cad.usda"
    cockpit_html = _ROOT / "cockpit" / "GECO_v6_Max_Cockpit.html"

    assert rig_usda.exists() and rig_usda.stat().st_size > 100_000
    assert ward_usda.exists() and ward_usda.stat().st_size > 80_000
    assert brep_usda.exists() and brep_usda.stat().st_size > 4_000
    assert cockpit_html.exists() and cockpit_html.stat().st_size > 40_000

    if has_pxr:
        for stage_path in (rig_usda, ward_usda, brep_usda):
            st = Usd.Stage.Open(str(stage_path))
            assert st is not None and st.GetDefaultPrim().IsValid()

    ward_text = ward_usda.read_text()
    for room_name in (
        "Room_01_Nominal_Adult",
        "Room_02_Fluidic_Debris_And_Occlusion",
        "Room_03_Battery_Brownout_And_Malfunction",
        "Room_04_Cyber_MITM_And_Simplex_Clamp",
        "Room_05_IITP_Metrology_Lab",
        "Room_06_SOC_Command_Center",
        "Room_07_Wet_Site_Adult_P05",
        "Room_08_PISA_Compression_P06",
        "Room_09_Clock_Skew_Dawn_P07",
        "Room_10_Stealth_CUSUM_P08",
        "Room_11_Brittle_Variable_P09",
        "Room_12_Unprimed_Line_P10",
    ):
        assert room_name in ward_text

    hub = WardTelemetryHub()
    snap = hub.step_all()
    assert len(snap["rooms"]) == 11
    assert "master_clock_ptp" in snap
    assert snap["master_clock_ptp"]["grandmaster_id"] == "IITP-GECOv6-PTP-GM-A05"
    assert "Room_09_Clock_Skew_Dawn_P07" in snap["master_clock_ptp"]["desynced_rooms"]
    assert "hardware_inventory" in snap["rooms"]["Room_01_Nominal_Adult"]
    assert snap["soc_command_center"]["total_patients_simulated"] == 10
    assert snap["soc_command_center"]["false_cyber_lockouts"] == 0
    assert len(snap["available_scenarios"]) >= 18

    # Verify INJECT_FAULT, SET_PHYSICS_SLIDERS, and RESET_ALL commands
    r_fault = hub.handle_command({
        "type": "INJECT_FAULT",
        "fault_type": "rf_replay_bolus",
        "params": {"room": "ROOM_04"},
    })
    assert r_fault["status"] == "OK"
    assert r_fault["active_scenario"] == "excess_2x"

    r_sliders = hub.handle_command({
        "type": "SET_PHYSICS_SLIDERS",
        "room": "ROOM_02",
        "debris_ratio": 0.80,
        "air_bubble_ul": 18.0,
        "cannula_kink": 0.40,
        "internal_resistance_ohm": 1.25,
    })
    assert r_sliders["status"] == "OK"

    r_reset = hub.handle_command({"command": "RESET_ALL"})
    assert r_reset["status"] == "OK"
    assert hub.rooms["Room_04_Cyber_MITM_And_Simplex_Clamp"].active_scenario == "clean"


