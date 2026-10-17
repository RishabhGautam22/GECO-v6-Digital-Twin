# GECO v6 Multi-Cubicle Simulation and Experimental Analysis Report

## 1. Cubicle-by-Cubicle Scenario Assignments

The GECO v6 Smart Hospital Ward simulates 12 specialized cubicles concurrently (10 clinical patient bays `P01`-`P10`, the 138-part gravimetric saline metrology lab in `ROOM_05`, and the central nursing/cybersecurity operations center with the IEEE-1588v2 PTP Grandmaster Clock in `ROOM_06`).

| Cubicle ID | Cubicle Name | Patient / Rig Profile | Active Scenario | Category | Mean BG (mg/dL) | Line P (kPa) | Battery (V) |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| `ROOM_01` | Cubicle 01 - Adult Baseline & Site Absorption | Patient P01 (Adult, 75 kg, ISF 42 mg/dL/U) | `clean` (Nominal Closed-Loop 7-State EKF Control) | `NOMINAL_BASELINE` | 120.4 | 1.57 | 3.90 |
| `ROOM_02` | Cubicle 02 - Microbore Fluidics & Occlusion Physics | Patient P02 (Adolescent, 58 kg, ISF 50 mg/dL/U) | `pipe_debris` (B2: Insulin Fibril Debris & Micro-Occlusion (72%)) | `FLUIDIC_FAULT` | 130.8 | 133.15 | 3.79 |
| `ROOM_03` | Cubicle 03 - Power Rail & Electromechanical Cut-Away | Patient P03 (Elderly, 82 kg, ISF 36 mg/dL/U) | `battery_brownout` (B5: High-Impedance Li-Ion Passivation & Bolus Brownout) | `ELECTROMECHANICAL_FAULT` | 173.7 | 1.50 | 2.10 |
| `ROOM_04` | Cubicle 04 - Wireless MITM Spoofing & Simplex Defense | Patient P04 (Brittle T1D, 64 kg, ISF 55 mg/dL/U) | `cgm_bias_40` (C2: BLE Man-in-the-Middle +40 mg/dL CGM Spoofing) | `CYBER_ATTACK` | 95.9 | 1.54 | 3.92 |
| `ROOM_05` | Cubicle 05 - 138-Part Gravimetric Saline Metrology Rig | Hardware-in-the-Loop Gravimetric Balance & Optical Truth Node T04 | `excess_bias_report_mask` (C6: Coordinated Actuator 2x Overdose + Telemetry Masking) | `METROLOGY_VERIFICATION` | 106.1 | 1.57 | 3.88 |
| `ROOM_06` | Cubicle 06 - Central Nursing & Cyber SOC Command Wall | 12-Bay Ward Aggregator & IEEE-1588v2 PTP Grandmaster Clock (Part A05/A06) | `soc_monitoring` (Ward-Wide Root-Cause Disambiguation & Large Telemetry Dashboard) | `SOC_COMMAND_HUB` | 115.0 | 1.80 | 3.98 |
| `ROOM_07` | Cubicle 07 - Cannula Dislodgement ('Wet Site' Leak) | Patient P05 (Adult, 68 kg, ISF 44 mg/dL/U) | `cannula_dislodgement_leak` (A2: Pulled-Out Subcutaneous Cannula ('Wet Site' Patch Leak)) | `INSTALLATION_FAULT` | 162.6 | 0.14 | 3.84 |
| `ROOM_08` | Cubicle 08 - Sleep PISA Sensor Compression Artifact | Patient P06 (Adult, 71 kg, ISF 40 mg/dL/U) | `pisa_compression_low` (A4: Pressure-Induced Sensor Attenuation (PISA -36 mg/dL Drop)) | `INSTALLATION_FAULT` | 101.2 | 1.54 | 3.92 |
| `ROOM_09` | Cubicle 09 - RTC Timestamp Manipulation Defense | Patient P07 (Dawn Phenomenon T1D, 79 kg, ISF 38 mg/dL/U) | `clock_skew_iob_attack` (C4: +3.5h RTC Clock-Skew IOB Zeroing Attack) | `CYBER_ATTACK` | 96.0 | 1.54 | 3.92 |
| `ROOM_10` | Cubicle 10 - Zero-Dynamics Sub-Threshold Drip Defense | Patient P08 (Insulin-Sensitive T1D, 62 kg, ISF 52 mg/dL/U) | `stealthy_cusum_drip` (C3: Stealthy Sub-Threshold (+0.42 sigma) CUSUM Drip Attack) | `CYBER_ATTACK` | 99.9 | 1.54 | 3.92 |
| `ROOM_11` | Cubicle 11 - Sub-GHz RF Replay Overdose Interlock | Patient P09 (Brittle T1D, 55 kg, ISF 60 mg/dL/U) | `excess_2x` (C1: Unauthenticated RF Replay 2x Bolus Injection (CVE-2019-10964)) | `CYBER_ATTACK` | 99.7 | 1.55 | 3.90 |
| `ROOM_12` | Cubicle 12 - Unprimed Catheter Dead-Space Detection | Patient P10 (Adult T1D, 73 kg, ISF 43 mg/dL/U) | `unprimed_tubing_install` (A1: Unprimed 60 cm Infusion Tubing (68.05 uL Air Dead-Space)) | `INSTALLATION_FAULT` | 173.7 | 0.08 | 3.84 |

## 2. Catalog of Scenarios Tested Across the Ward

- **Category A (Clinical Installation & Site Artifacts)**:
  - `A1: unprimed_tubing_install` (Cubicle 12) - 68.05 uL air dead-space on reconnect.
  - `A2: cannula_dislodgement_leak` (Cubicle 07) - Subcutaneous cannula pull-out ('wet site' leak, line pressure < 0.55 kPa).
  - `A3: lipohypertrophy_site` (Cubicle 01) - Delayed subcutaneous absorption in scar tissue (tau = 135 min).
  - `A4: pisa_compression_low` (Cubicle 08) - Nocturnal supine tissue compression (-36 mg/dL CGM drop).
  - `A5: wrong_concentration_or_denatured` (Cubicle 02) - Reduced insulin potency (U-40 or thermally degraded U-100).
  - `A6: electrochemical_interferent` (Cubicle 04) - Hydroxyurea / IV ascorbate oxidation at the CGM electrode.
- **Category B (Fluidic, Mechanical & Power Faults)**:
  - `B0: silent_basal_micro_occlusion` (Cubicle 02) - Early dP/dV pulse-wave stiffness detection in 15-20 min.
  - `B1: aircraft_depressurization_siphon` (Cubicle 02) - Boyle's-law air pocket expansion blocked by pinch valve V01.
  - `B2: pipe_debris` (Cubicle 02) - 72% isoelectric insulin fibril occlusion and microbore lumen swelling.
  - `B3: stuck_on` (Cubicle 03) - H-bridge MOSFET runaway cutoff via independent supervisor relay.
  - `B4: plunger_oring_blowby` (Cubicle 03) - Internal backward leakage past elastomeric plunger seal S03.
  - `B5: battery_brownout` (Cubicle 03) - High-impedance Li-Ion cell sag (1.85 Ohm) mitigated by 1.5 F supercapacitor hold-up.
  - `B6: motor_malfunction` (Cubicle 03) - Stepper stiction and lead-screw backlash detected by optical encoder.
- **Category C (Adversarial Cyber-Physical Attacks)**:
  - `C1: excess_2x` (Cubicle 11) - Sub-GHz RF replay 2x bolus injection stopped in <50 ms by hardware pinch valve V01.
  - `C2: cgm_bias_40` (Cubicle 04) - BLE MITM +40 mg/dL false hyperglycemia spoofing clamped to Simplex Safe-Basal.
  - `C3: stealthy_cusum_drip` (Cubicle 10) - Sub-threshold +0.42 sigma micro-overdose caught by multi-scale CUSUM (k=0.10 sigma).
  - `C4: clock_skew_iob_attack` (Cubicle 09) - +3.5h RTC clock jump blocked by IEEE-1588v2 PTP Grandmaster Part A05.
  - `C5: ekf_ramp_poisoning` (Cubicle 04) - Slow +1.25 mg/dL/step ramp poisoning caught by 90-min conservation invariant.
  - `C6: excess_bias_report_mask` (Cubicle 05) - Coordinated Stuxnet-style overdose + telemetry mask unmasked by gravimetric balance T04.
  - `C7: emi_false_occlusion_dos` (Cubicle 04) - Resonant EMI 95 kPa false-occlusion rejected via unloaded motor current cross-check.
  - `C8: param_table_ram_corruption` (Cubicle 11) - Unauthorized BLE ISF modification blocked by SHA-256 parameter seal.
- **Category D (Compound Multi-Domain Scenarios)**:
  - `D1: compound_meal_plus_debris` (Cubicle 02) - 65g meal bolus concurrent with 72% fibril occlusion.
  - `D2: compound_pisa_plus_brownout` (Cubicle 03) - Nocturnal PISA compression low concurrent with battery voltage sag.

## 3. Summary of Quantitative Benchmark Results

1. **31-Participant 30-Minute Glucose Forecasting (`participant_v6_vs_v61_benchmark.csv`)**: The 7-state Joseph-form EKF reduces mean 30-minute RMSE from 25.77 mg/dL (5-state baseline) to 16.82 mg/dL, outperforming zero-order persistence (22.56 mg/dL) in all 31 participants with 0/31 boundary-hitting fits.
2. **Hovorka Plant Domain Validity (`intervention_v6_vs_v61_summary.csv`)**: Enforcing Michaelis-Menten hepatic receptor saturation eliminates negative endogenous glucose production, improving locked-test physiological domain validity from 8.3% (4/48 runs) to 100.0% (48/48 runs).
3. **Root-Cause Disambiguation (`permutation_matrix_evaluation.csv`)**: Cross-domain physical invariants separate installation errors, fluidic/power faults, and cyber attacks with 100% classification accuracy and 0% false cyber lockouts on clinical site faults.
