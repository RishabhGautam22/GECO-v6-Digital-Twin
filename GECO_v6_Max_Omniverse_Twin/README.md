# GECO v6.1+ Smart Hospital Ward & 138-Part Metrology Digital Twin

This directory contains the OpenUSD 12-cubicle hospital ward, the 138-part IIT Patna gravimetric saline calibration rig, the coupled physiological/fluidic/power/cyber simulation engine, and the paper export pipeline.

---

## Core Modules

1. **7-State Extended Kalman Filter (`geco_v6_max/ekf_7state.py`)**:
   - Estimates interstitial CGM lag, plasma glucose, rate of change, active insulin-on-board (`IOB`), gut carbohydrate absorption, insulin sensitivity (`ISF`), and sensor bias.
   - Reduces 30-minute forecast RMSE across the 10-patient ward cohort from `18.54 mg/dL` to `12.48 mg/dL` (`16.82 mg/dL` vs `25.77 mg/dL` across the full 31-participant dataset).
2. **8-State Hovorka RK4 Solver (`geco_v6_max/hovorka_rk4.py`)**:
   - Adaptive 4th-order Runge-Kutta physiological integration with hepatic basal equilibrium anchoring and non-negativity projection.
3. **Coupled Fluidic & Power Physics (`geco_v6_max/multi_physics.py`)**:
   - Hagen-Poiseuille microbore lumen back-pressure ($\Delta P \propto R_{\text{hyd}} / (1 - \alpha_{\text{occ}})^4$), compressible air-bubble compliance, subcutaneous cannula kink modeling, and Li-Ion internal resistance ($R_{\text{int}}$) brownout dynamics.
4. **6-Channel Orthogonal Detector & Simplex Kernel (`geco_v6_max/simplex_safety.py`)**:
   - Combines local gravimetric mass (`Ch1`), network-vs-local command check (`Ch2`), 7-state EKF innovation (`Ch3`), dual-scale CUSUM (`Ch4`, $k = 0.10\sigma$ and $k = 0.50\sigma$), Poiseuille line pressure (`Ch5`), and battery/stepper telemetry (`Ch6`).
   - Distinguishes clinical site/installation errors (`Cat A`) and hardware faults (`Cat B`) from cyber-attacks (`Cat C`) with zero false cyber lockouts.
5. **OpenUSD Stages & Large Dashboard Screen (`omniverse_usd/build_usd_stages.py`)**:
   - Generates `geco_v6_metrology_rig.usda` (138 parts) and `geco_v6_smart_hospital_ward.usda` (12 cubicles, each with a 3D `CubicleScenarioBoard`, plus the 3.8m x 2.1m `LargeWallDashboardScreen` in Room 06).
6. **Paper Report & 300-DPI Figure Generator (`geco_v6_max/paper_report_generator.py`)**:
   - Exports `cubicle_scenarios_telemetry.csv`, `cubicle_scenario_matrix.csv`, `ieee_paper_tables.tex`, `SIMULATION_ANALYSIS_REPORT.md`, and 4 publication figures (`fig1`..`fig4` in 300-DPI PNG and PDF) to `results/paper_exports/`.

---

## Running the System

```bash
# Regenerate OpenUSD stages
python3 omniverse_usd/build_usd_stages.py

# Export paper reports, CSV telemetry, IEEE LaTeX tables & 300-DPI figures
python3 -m geco_v6_max.paper_report_generator

# Launch WebSocket telemetry server on ws://127.0.0.1:8766
python3 -m geco_v6_max.ward_telemetry_server

# Run automated pytest verification suite
pytest -q
```
To view the standalone large-screen browser dashboard, open `cockpit/GECO_v6_Max_Cockpit.html` in any modern web browser.
