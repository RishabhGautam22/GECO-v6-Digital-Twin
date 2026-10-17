# Real-World Insulin Pump Failure, Installation Error & Cyber-Attack Taxonomy

This document summarizes the 20 clinical, mechanical, power-rail, and cyber-physical scenarios modeled across the 12 cubicles of the GECO v6 Smart Hospital Ward Digital Twin.

---

## 1. Why Root-Cause Attribution Matters

A major operational challenge in closed-loop insulin pump security is avoiding false cyber lockouts during benign clinical or mechanical anomalies. If a patient rolls onto their CGM sensor during sleep (causing a Pressure-Induced Sensor Attenuation drop) or installs an unprimed infusion set, locking out the pump as if it were under a cyber-attack disrupts therapy. Conversely, if an adversary injects a slow micro-bolus drip or replays an RF bolus packet, the safety kernel must clamp delivery to a safe basal rate immediately.

The GECO v6 6-channel orthogonal detector separates these failure modes by cross-checking hydraulic back-pressure (`Ch5`), motor phase current (`Ch6`), local gravimetric/encoder displacement (`Ch1`), cryptographic sequence nonces (`Ch2`), and 7-state EKF physiological innovation residuals (`Ch3`/`Ch4`).

---

## 2. Category A: Installation Errors & Subcutaneous Site Artifacts (Non-Cyber)

| Code | Scenario | Assigned Cubicle | Physical / Physiological Signature | System Response |
| :--- | :--- | :--- | :--- | :--- |
| **A1** | Unprimed 60 cm Catheter (`68.05 uL` Dead-Space) | `ROOM_12` (`P10`) | Sub-nominal line pressure (`< 0.2 kPa`) while air column clears; delayed tissue insulin action | Tracks 68.05 uL hold-up volume and prompts line prime; no cyber lockout |
| **A2** | Dislodged Subcutaneous Cannula ("Wet Site") | `ROOM_07` (`P05`) | Low hydraulic back-pressure with rising positive EKF glucose residual | Alerts nurse to inspect infusion patch; no cyber lockout |
| **A3** | Lipohypertrophy / Scar-Tissue Placement | `ROOM_01` (`P01`) | Prolonged subcutaneous absorption time constant ($\tau_{\text{ins}} = 135\text{ min}$) and reduced bioavailability | Adapts EKF absorption covariance and advises site rotation |
| **A4** | Sleep PISA Compression Low (`-36 mg/dL` Step) | `ROOM_08` (`P06`) | Abrupt negative CGM step exceeding physiological rate-of-change limit without preceding IOB surge | Rejects outlier sample via rate gate and maintains basal delivery |
| **A5** | Wrong Insulin Concentration (`U-40`) / Thermal Degradation | `ROOM_02` (`P02`) | Normal fluidic delivery and pressure with persistent 60% potency deficit in EKF innovation | Flags reservoir potency mismatch for cartridge replacement |

---

## 3. Category B: Fluidic, Mechanical & Power-Rail Hardware Faults

| Code | Scenario | Assigned Cubicle | Physical Signature | System Response |
| :--- | :--- | :--- | :--- | :--- |
| **B1** | Cabin Depressurization Plunger Siphon | `ROOM_02` (`P02`) | Uncommanded meniscus motion during ambient pressure drop with zero motor steps | Actuates hardware pinch valve `Part_V01` to block unintended siphon |
| **B2** | 72% Isoelectric Fibril Debris & Micro-Occlusion | `ROOM_02` (`P02`) | Hagen-Poiseuille back-pressure surge (`> 65 kPa`) and elevated motor current | Opens back-pressure relief valve and triggers physical occlusion alarm |
| **B3** | Capacitive Moisture Ghost Bolus / Stuck MOSFET | `ROOM_03` (`P03`) | Uncommanded motor drive current detected by independent hardware watchdog | Opens fail-safe power relay and engages pinch valve `V01` |
| **B4** | Plunger O-Ring Blow-By / Lead-Screw Nut Strip | `ROOM_03` (`P03`) | Normal stepper rotation (`M03`) with near-zero line pressure (`< 1 kPa`) | Flags mechanical drive decoupling alarm |
| **B5** | Li-Ion ESR Surge (`1.85 Ohm`) & Voltage Brownout | `ROOM_03` (`P03`) | Terminal voltage sag below `3.05 V` under bolus load | Supercapacitor hold-up preserves state; brownout watchdog enters safe hold |
| **B6** | Lead-Screw Stiction & Backlash (`0.28 mm`) | `ROOM_03` (`P03`) | Phase lag between commanded stepper pulses and optical encoder `Part_M08` | Compensates backlash and flags actuator maintenance |

---

## 4. Category C: Adversarial Cyber-Physical Attacks

| Code | Scenario | Assigned Cubicle | Attack Vector & Signature | Simplex Defense Response |
| :--- | :--- | :--- | :--- | :--- |
| **C1** | Sub-GHz RF 2x Bolus Replay (`CVE-2019-10964`) | `ROOM_11` (`P09`) | Replayed wireless bolus frame with duplicate sequence nonce | Rejects frame via nonce counter and clamps delivery via Simplex kernel |
| **C2** | BLE MITM CGM Spoofing (`+40 mg/dL` Offset) | `ROOM_04` (`P04`) | Abrupt divergence between reported CGM and 7-state EKF prediction ($z_{\text{innov}} > 3.0\sigma$) | Engages Simplex safe-basal clamp (`1.0 U/hr`) and blocks induced overdose |
| **C3** | Stealthy Sub-Threshold CUSUM Drip (`+0.35 U/hr`) | `ROOM_10` (`P08`) | Low-rate micro-bolus drift below single-step $3\sigma$ gate | Dual-scale CUSUM ($k = 0.10\sigma$) crosses $h = 4.2$ and clamps pump before hypoglycemia |
| **C4** | RTC Clock-Skew (`+3h`) IOB Zeroing Attack | `ROOM_09` (`P07`) | Local RTC jumped forward 3 hours to expire active IOB and force dawn basal surge | IEEE-1588v2 PTP Grandmaster (`Part_A05`) detects clock skew and locks schedule |
| **C5** | EKF Innovation Ramp Poisoning | `ROOM_04` (`P04`) | Gradual `+0.8 mg/dL/step` CGM ramp injection | Multi-step 30-minute EKF forecast residual detects drift and engages Simplex hold |
| **C6** | Stuxnet Dual-Channel Telemetry Masking | `ROOM_05` (`Rig`) | Compromised gateway replays nominal telemetry while over-actuating stepper | Out-of-band optical/gravimetric truth node (`T04`/`A05`) trips hardware cutoff `V01` |
| **C7** | Resonant Acoustic/EMI Pressure Spoofing (`95 kPa`) | `ROOM_04` (`P04`) | Fake `95 kPa` pressure transducer reading while stepper current remains unloaded (`410 mA`) | Cross-validates pressure against motor current to reject false occlusion DoS |

---

## 5. Category D: Compound Multi-Domain Permutations

- **D1 (`ROOM_02`)**: 65g carbohydrate meal bolus occurring simultaneously with a 72% fibril debris line occlusion. The detector attributes the high glucose residual to the verified physical line occlusion (`Ch5 > 65 kPa`) rather than a cyber-attack.
- **D2 (`ROOM_03`)**: Sleep PISA compression dropout occurring simultaneously with a low-battery voltage sag. Both physical artifacts are handled by their respective rate and power guards with zero false cyber lockouts.
