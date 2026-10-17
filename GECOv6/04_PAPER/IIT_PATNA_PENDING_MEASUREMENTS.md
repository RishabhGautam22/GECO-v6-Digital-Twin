# IIT Patna measurement pending  -  paper and presentation field specification

Every row is prospective. There are no team-measured values in this document. Use visible text plus amber/yellow background in paper and PPT; color alone is insufficient. Recommended visual style: pale amber fill `#FFF2CC`, dark amber border `#BF9000`, dark text, heading **IIT Patna measurement pending**. Keep the block beside the affected claim/table, not only in a closing limitations slide.

The cross-references below apply to the final three-figure manuscript (Markdown SHA-256 `787d1d5372ebdf4ec8a88e0d3f7ac37c5cd61f3d8ccf2c786519027e72fb1c7c`). Its physical pending-results table is **Table IV, IIT Patna Physical Results Pending**. Section VIII is **Proposed IIT Patna Measurement Study**; Fig. 3 is the conceptual rig and measurement chain. Earlier outline table numbers do not apply.

## Primary claim block

**IIT Patna measurement pending.** The rig is conceptual and its components are not selected. Delivery reconstruction, calibration, uncertainty, zero-flow bias, synchronization, stop latency, post-stop flow and recovery remain to be measured. A simulator can expose latent emitted mass; physical hardware cannot. The physical virtual-patient input must come from a separately validated reconstruction. A balance indication or camera record is not automatically ground truth, and positive-only differencing of noisy balance readings is not an adequate substitute for validation.

| ID | Measurement or record still required | Required field/unit and design | Affected paper claim/table | Status |
|---|---|---|---|---|
| M01 | Actual component selection and assembly | Manufacturer/model/serial where relevant; syringe bore and usable stroke; tubing length/bore/material; stop mechanism; firmware revision; dated as-built photos | §VIII, Proposed IIT Patna Measurement Study; Fig. 3 | IIT Patna measurement pending |
| M02 | Measurand and outlet definition | Delivered mass or volume at a stated outlet and interval; receiver geometry; fluid identity/concentration; hydraulic boundary | §VIII measurand definition; Table IV, reconstructed outlet delivery | IIT Patna measurement pending |
| M03 | Traceable balance calibration | Reference-mass identifiers/certificates, calibration date, range, repeatability, resolution, linearity and uncertainty; masses on a separate tray when unused | §VIII calibration/reconstruction requirements; Table IV, reconstructed outlet delivery | IIT Patna measurement pending |
| M04 | Fluid temperature and density | Temperature unit, sensor calibration/placement, sampling times, density equation or measured value and uncertainty; separate sample vial so probe does not load balance | §VIII corrected mass-to-volume conversion; Table IV, reconstructed outlet delivery | IIT Patna measurement pending |
| M05 | Evaporation and environmental effects | No-flow blank with same fluid/receiver/cover and duration; temperature, pressure/humidity when material; drift/vibration/buoyancy corrections and uncertainty | §VIII no-flow/low-flow validation; Table IV, zero-flow cumulative bias | IIT Patna measurement pending |
| M06 | Mechanical force isolation | Tubing support, outlet/receiver contact test, surface-tension/wetting effects, disturbance sensitivity and settling time | §VIII force-isolation and settling requirements; Fig. 3 | IIT Patna measurement pending |
| M07 | Independent reference method selection | Reference balance/flow sensor/validated imaging method selected by lab; calibration chain, independence assumptions and uncertainty; no camera-as-oracle claim | §VIII reference-method validation; Fig. 3; Table IV, reconstructed outlet delivery | IIT Patna measurement pending |
| M08 | Reconstruction model and zero-flow bias | Raw signed readings, filtering/latency model, drift corrections, cumulative estimate and uncertainty; compare with reference; explicit zero-flow and low-flow trials | §III physical-input boundary; §VIII reconstruction; Table IV, delivery and zero-flow bias | IIT Patna measurement pending |
| M09 | Delivery accuracy and timing | Several predeclared steady/pulsed settings and horizons; repeated randomized trials; command, indication, reference estimate and uncertainty | §VIII locked delivery trials; Table IV, reconstructed outlet delivery | IIT Patna measurement pending |
| M10 | Acquisition synchronization | Device/host timestamps, common event marker, offset/drift/jitter/loss, camera-frame alignment and uncertainty; preserve native sampling | §VIII event synchronization; Table IV, stop latency and post-stop delivery | IIT Patna measurement pending |
| M11 | Stop response | Injected event, monitor decision, electrical stop command, actual flow cessation; latency distribution and sample/clock uncertainty | §V assumed simulation timing; §VIII physical event chain; Table IV, stop latency | IIT Patna measurement pending |
| M12 | Post-stop residual flow | Delivered mass/volume after stop, observation window, compliant-tube effects, gravity/head conditions and uncertainty | §VIII measured post-stop follow-up; Table IV, post-stop delivery | IIT Patna measurement pending |
| M13 | Stop-path independence | Power, firmware, clock, communications, calibration and actuation common modes; disconnect/fault tests with predeclared expected behavior | §III authority assumptions; §VIII common-mode testing; §IX limitations | IIT Patna measurement pending |
| M14 | Nuisance alarms and misses | Benign exposure time, event counts, observation windows, false-stop episodes, denominator and uncertainty; missed physical deviations | §VIII physical event/exposure trials; Table IV, false-stop exposure | IIT Patna measurement pending |
| M15 | Restart and recovery | Re-enable authority, outstanding-command handling, power/network restoration, withheld delivery and overshoot, recovery delay | §V simulated recovery policy; §VIII physical restart tests; Table IV, recovery deficit | IIT Patna measurement pending |
| M16 | Locked physical study and records | Protocol/threshold freeze, randomized order, replicate count rationale, failed/invalid trials, operator notes, raw immutable logs and hashes | §VIII locked physical design and records; Data, Code and Supplementary Material | IIT Patna measurement pending |

These measurements do not establish clinical safety or drug-delivery suitability. Use water/saline research language and document the virtual conversion convention separately from clinical insulin units. Do not show a fabricated dose, accuracy, latency or uncertainty to make an empty table look complete.

## Pending endpoints in the final paper  -  Table IV

| Endpoint | Reference / unit | Value | Uncertainty or interval | Evidence |
|---|---|---|---|---|
| Reconstructed outlet delivery | Validated reference method / g or mL | Pending measurement | Pending measurement | IIT Patna measurement pending |
| Zero-flow cumulative bias | Matched blank / g or mL | Pending measurement | Pending measurement | IIT Patna measurement pending |
| Stop latency | Synchronized event chain / s | Pending measurement | Pending measurement | IIT Patna measurement pending |
| Post-stop delivery | Defined follow-up / g or mL | Pending measurement | Pending measurement | IIT Patna measurement pending |
| False-stop exposure | Benign trials / episodes per hour | Pending measurement | Pending measurement | IIT Patna measurement pending |
| Recovery deficit | Reference reconstruction / g or mL | Pending measurement | Pending measurement | IIT Patna measurement pending |

Use the same M01-M16 field identifiers in the lab handoff, figure captions, paper table and video. Once measured, replace a pending row only with a link to the raw record, method/version, uncertainty calculation and verification status.
