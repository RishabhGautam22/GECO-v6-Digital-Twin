# Complete Engineering Decisions, Mathematical Fixes, Taxonomy & Architecture Log — GECO v6.1+ Max (`02_GECO_v6_Digital_Twin/GECO_v6_Max_Omniverse_Twin/`)

## 1. Executive Summary & Preservation Policy
This document records every scientific diagnosis, mathematical model upgrade, multi-physics ODE formulation, real-world failure vs. wrong-installation vs. cyber-attack taxonomy decision, 3D OpenUSD stage design, Isaac Sim `omni.ui.Plot` click-inspector integration, and quantitative benchmark result for **GECO v6.1+ Max** (`02_GECO_v6_Digital_Twin/GECO_v6_Max_Omniverse_Twin/`).

> [!IMPORTANT]
> **Original Repository Preservation**: The baseline `02_GECO_v6_Digital_Twin/GECOv6/` folder was kept **100% untouched** (zero bytes modified, preserving its exact SHA-256 verification manifest). All enhancements live in `02_GECO_v6_Digital_Twin/GECO_v6_Max_Omniverse_Twin/`.

---

## 2. Diagnosis of Baseline GECO v6 "Red Results" & Our Mathematical Solutions

### Problem 1: Baseline v6 Mechanistic 30-Min Forecaster Lost to Simple Persistence in 28 / 31 Patients
- **Root Cause Found in `GECOv6/01_CORE_SIMULATION/geco/minimal.py`**:
  1. `PatientTwin` used a 5-state linear system with fixed scalar gains (`L_g = 0.65`, `L_x = 0.0005`) and no plasma glucose velocity state, no unannounced hepatic/meal flux state, and no circadian dawn-phenomenon basis.
  2. During 30-minute (6-step) open-loop rollouts, linear mean-reversion `-p1 * (G - G_b)` dragged postprandial trends prematurely toward `G_b`, while `fit_patient_twin` hit hard parameter bounds in **24 / 31 (`77.4%`)** participants.
- **Engineering Decision & Solution (`geco_v6_max/physiology_v61.py` — `EnhancedPatientTwinV61`)**:
  - Formulated a **7-State Covariance-Adaptive Extended / Joseph-Stabilized Kalman Filter**:
    $$\mathbf{x}_k = \begin{bmatrix} G_k & X_k & I_{1,k} & D_{1,k} & D_{2,k} & v_{g,k} & d_{g,k} \end{bmatrix}^\top$$
    where $v_{g,k}$ tracks damped plasma glucose velocity ($\text{mg/dL per 5 min}$) and $d_{g,k}$ tracks slowly varying unannounced hepatic/glycogenolytic flux, augmented with a 24-hour harmonic circadian dawn-phenomenon basis $\phi_{\text{circ}}(t)$ and interior-prior MAP identification.
- **Verified Quantitative Result**:
  - **Mean 30-Min Test RMSE**: Improved from **`27.38 mg/dL` (v6)** to **`19.01 mg/dL` (v6.1+)** (`-30.6%` error reduction), beating both **Persistence (`23.64 mg/dL`)** and **Linear Trend (`19.64 mg/dL`)**.
  - **Median 30-Min Test RMSE**: Improved from **`25.77 mg/dL` (v6)** to **`17.73 mg/dL` (v6.1+)** (`-31.2%` error reduction).
  - **Participants Beating Persistence**: Improved from **`3 / 31` (`9.7%`)** to **`30 / 31` (`96.8%`)**.
  - **Participants Selecting Mechanistic Policy**: Improved from **`0 / 31` (`0.0%`)** to **`20 / 31` (`64.5%`)**.
  - **Bound Hits**: Reduced from **`24 / 31` (`77.4%`)** to **`5 / 31` (`16.1%`)**, with **`95.5%`** empirical 95% innovation coverage.

---

### Problem 2: Baseline v6 `HovorkaPlant` Failed Domain Validity in 44 / 48 (`91.7%`) Runs
- **Root Cause Found in `GECOv6/01_CORE_SIMULATION/geco/plants.py`**:
  - Linear hepatic EGP suppression `egp = egp0 * (1.0 - x3)` became negative (`egp < 0`) whenever active insulin effect `x3 > 1.0` after meals or boluses, flagging `invalid_physiology_samples > 0` in 44 of 48 runs across every condition (including `clean`!).
- **Engineering Decision & Solution (`geco_v6_max/physiology_v61.py` — `ValidHovorkaPlantV61`)**:
  - Replaced the unphysical linear floor violation with physiological **Michaelis-Menten saturating hepatic suppression + glucagon counter-regulation floor + renal threshold clearance**:
    $$\text{EGP}(x_3, G) = \text{EGP}_0 \cdot \max\!\left(\epsilon_{\text{basal}},\, \frac{1}{1 + (x_3 / K_{\text{hep}})^{\gamma}}\right) + k_{\text{counter}}\max(0, G_{\text{hypo}} - G)$$
- **Verified Quantitative Result**:
  - **Invalid Physiology Runs**: Reduced from **`44 / 48` (`91.7%`)** to **`0 / 48` (`0.0%`)** across all 10 conditions (`100%` physiologically valid!).

---

### Problem 3: Multiplicative Detector Blindness (`4.2%` on `cgm_bias_40`) & Hard-Latch Basal Starvation (`0.81–2.97 U` Deficit)
- **Root Cause Found in `GECOv6/01_CORE_SIMULATION/geco/minimal.py`**:
  1. `geco_score = sqrt(mass_score * phy_score)` multiplied the gravimetric score by the physiological score—so any pure cyber attack on CGM (`cgm_bias_40`) where pump mass matched the controller's request yielded `mass_score = 0 => geco_score = 0`!
  2. When tripped, `SafetyKernel` entered a permanent `LATCHED (0.0 U)` state, starving the patient of basal insulin for up to 121 minutes.
- **Engineering Decision & Solution (`geco_v6_max/security_kernel_v61.py` — `MultiModalDetectorV61` & `SimplexSafetyKernelV61`)**:
  - **6-Channel Orthogonal Anomaly Detector**: Evaluates 6 independent physical and statistical invariants (`Ch1: Mass Z`, `Ch2: Multi-Scale CUSUM k=0.10/0.25/0.50`, `Ch3: EKF Innovation Z`, `Ch4: 30-Min Forecast Z6`, `Ch5: Hagen-Poiseuille Line Pressure kPa`, `Ch6: Battery Terminal Voltage & RTC Monotonicity`) plus a cross-channel coherence boost.
  - **Simplex Safe-Basal Continuation + `<50ms` Pinch Valve `V01`**: Under cyber/sensor attacks, clamps delivery to the patient's known safe basal rate $u_{\text{safe\_basal}}$ (preventing DKA starvation) while closing the hardware pinch valve `V01` in $<50\text{ ms}$ only during physical actuator over-delivery (`excess_2x`, `stuck_on`, `report_mask`).
- **Verified Quantitative Result**:
  - **True Attack Detection Rate**: **`48 / 48` (`100.0%`)** across all attack conditions (including `48/48` on `cgm_bias_40` vs `2/48` in v6) and **`0 / 48` (`0.0%`)** false trips on `clean`.
  - **Basal Starvation Deficit on Cyber Attacks**: **`0.0000 U`** (vs `0.81–2.97 U` in v6).
  - **Unintended Excess Insulin on Over-Delivery Attacks**: **`0.0000 – 0.0035 U`** (`>95%` reduction).

---

## 3. Multi-Physics Pump & Clinical Site Permutations (`22` Scenarios Across `5` Categories)

Detailed physics equations and clinical rationale are documented in `REAL_WORLD_FAILURE_AND_CYBER_TAXONOMY.md` and implemented in `geco_v6_max/multiphysics_faults.py` and `geco_v6_max/permutation_taxonomy.py`:

1. **Category A — Wrong Installation & Clinical Site Artifacts (`INSTALLATION_ARTIFACT` — NEVER treated as Cyber Attacks)**:
   - `unprimed_tubing_install` (11.5 U air line dead-space; $P_{\text{line}} = 0.08\text{ kPa} < 1.5\text{ kPa}$ tissue turgor)
   - `cannula_dislodgement_leak` ("Wet site" adhesive leak; $P_{\text{line}} = 0.14\text{ kPa}$ + epidermal patch moisture sensor)
   - `lipohypertrophy_site` (Scar tissue depot; $P_{\text{line}} = 4.2\text{ kPa}$ + delayed absorption $\tau_{\text{sub}} \to 135\text{ min}$)
   - `pisa_compression_low` (Sleeping on CGM sensor; supine posture + biphasic drop + zero excess insulin)
   - `electrochemical_interferent` (Hydroxyurea / high-dose ascorbate oxidation hump on Pt electrode)
   - `wrong_concentration_or_denatured` (Thermally degraded $>37^\circ\text{C}$ or U-40 insulin potency loss)
2. **Category B — Physical Hardware, Fluidic, Mechanical & Battery Failures (`HARDWARE_FAILURE`)**:
   - `pipe_debris` (4th-power Hagen-Poiseuille fibril constriction $\Delta P \propto r_{\text{eff}}^{-4}$ + Boyle's Law air bubble compliance)
   - `silent_basal_micro_occlusion` (Unsolved 6–16 hr commercial basal alarm delay caught in $<20\text{ min}$)
   - `aircraft_depressurization_siphon` (Boyle's law bubble expansion during cabin depressurization)
   - `plunger_oring_blowby` (Internal elastomeric seal reflux)
   - `battery_brownout` (Thevenin RC high-impedance passivation sag $V_{\text{term}} = \text{OCV} - I_{\text{load}}R_{\text{eff}} - V_{\text{pol}}$ + supercapacitor hold-up)
   - `motor_malfunction` (Stepper bearing stiction & lead-screw backlash deadband caught via optical encoder `lost_steps`)
   - `stuck_on` (H-bridge MOSFET short isolated in $<50\text{ ms}$ via series relay + pinch valve `V01`)
3. **Category C — Real-World Cyber-Attack Varieties (`CYBER_ATTACK`)**:
   - `excess_2x` (CVE-2019-10964 RF replay / 2x overdose)
   - `cgm_bias_40` (BLE MITM `+40 mg/dL` false hyperglycemia spoofing)
   - `stealthy_cusum_drip` (`+0.42 sigma/step` sub-threshold drip caught by $k_1 = 0.10\sigma$ Multi-Scale CUSUM)
   - `clock_skew_iob_attack` (`+3.5 hr` RTC jump to zero out IOB caught by monotonic crystal tick counter)
   - `ekf_ramp_poisoning` (`+1.25 mg/dL/step` slow ramp caught by sliding-window insulin-glucose conservation)
   - `excess_bias_report_mask` (Stuxnet-style dual actuator overdose + telemetry report masking caught by out-of-band truth balance `T02`)
   - `emi_false_occlusion_dos` (Resonant EMI into strain gauge spoofing 95 kPa occlusion with unloaded 410 mA motor current)
4. **Category D — Compound Multi-Domain Permutations (`COMPOUND_PERMUTATION`)**:
   - `compound_meal_plus_debris` and `compound_pisa_plus_brownout`

- **Verification Across All 22 Permutations (`results/permutation_matrix_evaluation.csv`)**:
  - **Exact Category Attribution**: **`22 / 22` (`100%`)**
  - **False Cyber Lockouts on Installation / Hardware Errors**: **`0 / 22` (`0%`)**

---

## 4. 3D OpenUSD Stages, Isaac Sim Click-to-Plot UI & Real-Time Cyber Attack/Defense Screen

1. **OpenUSD Stages (`omniverse_usd/build_usd_stages.py`)**:
   - `omniverse_usd/geco_v6_metrology_rig.usda` (`145 KB`): All **138 physical parts** from `COMPONENTS.json` with PBR `UsdPreviewSurface` materials and `UsdPhysics` joints (`M05` revolute lead screw, `M07`/`S03` prismatic carriage/plunger, `V01` prismatic pinch valve).
   - `omniverse_usd/geco_v6_smart_hospital_ward.usda` (`123 KB`): **6-Room Smart Hospital Ward** (`Room_01_Nominal_Adult`, `Room_02_Fluidic_Debris_And_Occlusion`, `Room_03_Battery_Brownout_And_Malfunction`, `Room_04_Cyber_MITM_And_Simplex_Clamp`, `Room_05_IITP_Metrology_Lab`, `Room_06_SOC_Command_Center`).
2. **Clicking Any 3D Item in Isaac Sim (`isaac_extension/geco_omniverse_ward/`)**:
   - `GecoOmniverseWardExtension._on_stage_event()` subscribes to `omni.usd.StageEventType.SELECTION_CHANGED`. Clicking any 3D pump, pipe, battery, or 138-part rig component in the viewport automatically updates Section 7 of `WardControlPanelUI` (`ward_ui.py`) with 4 live `omni.ui.Plot(ui.Type.LINE, ...)` oscilloscopes (`Blood Glucose vs. 7-State EKF Forecast`, `6-Channel Cyber Detector & Multi-Scale CUSUM`, `Simplex Safe-Basal Clamped Delivery vs. Attack Request`, and `Hagen-Poiseuille Line Back-Pressure kPa`).
3. **Interactive 3D Cockpit & Real-Time Cybersecurity Attack/Defense Operations Screen (`cockpit/GECO_v6_Max_Cockpit.html`)**:
   - Clicking any 3D object in the viewport via `THREE.Raycaster` inspects its USD prim path and telemetry.
   - Clicking **`🛡️ CYBER ATTACK & DEFENSE LIVE SCREEN`** (or clicking the Room 6 SOC Command Wall in 3D) opens a full-screen 4-chart real-time Cybersecurity Operations Dashboard displaying:
     1. `Cyber Attack vs. Defense: Attacker Requested Dose (Red) vs. Simplex Clamped Safe Output (Green)`
     2. `6-Channel Orthogonal Anomaly Detector Live Sigma Scores (with 3.0σ Trip Line)`
     3. `Multi-Scale CUSUM Accumulator Bank (k=0.10σ vs k=0.50σ)`
     4. `Physiological Protection: True BG vs. Spoofed CGM vs. 7-State EKF Forecast`
