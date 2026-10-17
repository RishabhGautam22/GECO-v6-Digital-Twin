# GECO v6 Multi-Cubicle Smart Hospital Ward & Metrology Digital Twin

This repository contains the GECO v6 and v6.1+ multi-patient insulin infusion digital twin, the 138-part gravimetric saline calibration rig, the 12-cubicle OpenUSD smart hospital ward stage, and the automated publication benchmark pipeline.

---

## Repository Structure

- **`GECO_v6_Max_Omniverse_Twin/`**:
  - `omniverse_usd/`: OpenUSD stage builder (`build_usd_stages.py`), the 138-part metrology rig stage (`geco_v6_metrology_rig.usda`), the 12-cubicle hospital ward stage (`geco_v6_smart_hospital_ward.usda`), and the OpenCascade BRep syringe asset (`geco_v6_brep_pump_cad.usda`).
  - `geco_v6_max/`: Core simulation packages including the 7-state Extended Kalman Filter (`ekf_7state.py`), 8-state Hovorka RK4 solver (`hovorka_rk4.py`), Hagen-Poiseuille fluidics and Li-Ion power model (`multi_physics.py`), 6-channel orthogonal fault/cyber detector (`simplex_safety.py`), WebSocket telemetry server (`ward_telemetry_server.py`), and publication report generator (`paper_report_generator.py`).
  - `isaac_extension/geco_omniverse_ward/`: Native NVIDIA Isaac Sim extension (`ward_scene_controller.py`, `ward_ui.py`) with 12-cubicle camera switching, `LargeWallDashboardScreen` animation, and 1-click paper export.
  - `cockpit/GECO_v6_Max_Cockpit.html`: Standalone full-screen WebGL/Chart.js dashboard displaying all 12 cubicles, active scenarios, highlighted benchmark results, and exported 300-DPI figures.
  - `results/paper_exports/`: Generated CSV telemetry datasets, IEEE LaTeX tables (`ieee_paper_tables.tex`), Markdown analysis report (`SIMULATION_ANALYSIS_REPORT.md`), and 300-DPI PNG/PDF figures.
- **`GECOv6/`**:
  - Baseline 31-participant clinical dataset analysis, 130+ part component manifest (`06_RIG_AND_MEDIA/native/COMPONENTS.json`), and IIT Patna laboratory calibration protocols.
- **`cloud_deployment/`**:
  - `upload_geco_v6_to_nucleus.py`: OpenUSD Nucleus staging and verification tool.

---

## 12-Cubicle Scenario Matrix & What Is Tested in Each Cubicle

Every cubicle in `geco_v6_smart_hospital_ward.usda` has a 3D overhead `CubicleScenarioBoard` showing its active scenario and live telemetry bars, aggregated on the 3.8m x 2.1m `LargeWallDashboardScreen` in Cubicle 06 (`/World/Cameras/Cam_LargeDashboardWall`):

| Cubicle | Patient / Station | Active Scenario Running | Scenarios Tested in Cubicle |
| :--- | :--- | :--- | :--- |
| **ROOM_01** | P01: Adult T1D (75 kg) | `NOMINAL_CLOSED_LOOP` | Baseline closed-loop control, 75g meal bolus tracking, EKF 30m forecast, Hovorka RK4 |
| **ROOM_02** | P02: Adolescent T1D (58 kg) | `A1_A3_FLUIDIC_DEBRIS_OCCLUSION` | 72% fibril debris occlusion (`B2`), 22 uL air bubble compliance (`B1`), cannula kink, relief valve |
| **ROOM_03** | P03: Resistant T1D (82 kg) | `B1_B5_BATTERY_BROWNOUT_STICTION` | Li-Ion ESR surge & brownout (`B5`), lead-screw backlash & stiction (`B6`), O-ring blow-by (`B4`) |
| **ROOM_04** | P04: Cardiac T1D (64 kg) | `C1_C2_CYBER_MITM_SIMPLEX_CLAMP` | BLE +40 mg/dL CGM spoof (`C2`), EKF ramp poisoning (`C5`), EMI pressure spoof (`C7`), Simplex clamp |
| **ROOM_05** | Bay 11: 138-Part Metrology Rig | `METROLOGY_GRAVIMETRIC_CALIBRATION` | Borosilicate S01 3014.78 uL bore, Luer 222.20 uL dead-space, 0.01 mg balance, Stuxnet mask (`C6`) |
| **ROOM_06** | Bay 12: PTP Master Clock & SOC | `WARD_SOC_PTP_TELEMETRY_FUSION` | IEEE-1588v2 PTP clock sync (`Part_A05`/`A06`), 12-cubicle risk ranking, paper report export |
| **ROOM_07** | P05: Adult T1D (68 kg) | `A2_DISLODGED_WET_CANNULA_SITE` | Dislodged subcutaneous cannula (`A2`), 70% skin leakage, low back-pressure + rising EKF residual |
| **ROOM_08** | P06: Adult T1D (71 kg) | `A4_PISA_COMPRESSION_DROPOUT` | Sleep tissue compression (`A4`, -36 mg/dL step drop), physiological rate-of-change gating |
| **ROOM_09** | P07: Dawn T1D (79 kg) | `C4_RTC_CLOCK_SKEW_ATTACK` | +3h RTC time-shift attack (`C4`), premature IOB zeroing, PTP grandmaster drift detection |
| **ROOM_10** | P08: Sensitive T1D (62 kg) | `C3_STEALTH_CUSUM_DRIP_INJECTION` | Low-and-slow +0.35 U/hr micro-basal drift (`C3`), dual-scale CUSUM ($k = 0.10\sigma$) detection |
| **ROOM_11** | P09: Brittle T1D (55 kg) | `C1_RF_2X_BOLUS_REPLAY_MITIGATION` | Sub-GHz RF 14U bolus replay (`C1`), cryptographic sequence nonce check, IOB ceiling clamp |
| **ROOM_12** | P10: Adult T1D (73 kg) | `A1_UNPRIMED_68UL_CATHETER_DEFICIT` | Unprimed 60 cm F01 catheter (`A1`, 68.05 uL air dead-space), delayed tissue delivery lag |

---

## Highlighted Simulation Results

1. **31-Participant 30-Minute Forecast Accuracy**: The 7-state EKF achieves **16.82 mg/dL RMSE** across the 31-participant T1D cohort compared to **25.77 mg/dL RMSE** for the baseline predictor ($p < 0.0001$).
2. **100% Physiological Domain Validity**: The adaptive 8-state Hovorka RK4 solver maintains strictly positive physiological glucose trajectories (`min BG = 74.2 mg/dL`) across all 20 fault and attack scenarios.
3. **100% Root-Cause Separation (Zero False Cyber Lockouts)**: Orthogonal evaluation of Hagen-Poiseuille hydraulic impedance (`Ch5`) and EKF innovation residuals (`Ch3`) separates mechanical/installation faults (Categories A & B) from adversarial cyber-attacks (Category C) with **0.0% false cyber lockouts**.
4. **Hardware Simplex Clamping (`< 50 ms`)**: Upon detecting an unauthorized RF bolus replay or spoofed CGM surge, the Simplex safety kernel actuates pinch valve `Part_V01` in under 50 ms, reducing excess insulin delivery by **96.4%** (`6.65 U -> 0.24 U`).

---

## Quick Start

```bash
cd GECO_v6_Max_Omniverse_Twin

# 1. Build/refresh the OpenUSD stages (138-part rig + 12-cubicle ward)
python3 omniverse_usd/build_usd_stages.py

# 2. Generate publication CSV logs, IEEE LaTeX tables, Markdown report & 300-DPI figures
python3 -m geco_v6_max.paper_report_generator

# 3. Run the live 12-cubicle WebSocket telemetry server (ws://127.0.0.1:8766)
python3 -m geco_v6_max.ward_telemetry_server

# 4. Run the verification test suite
pytest -q
```
