# GECO rig video: narration and storyboard

Working text: 1137 spoken words; estimated 7.8 minutes at 150 words/minute plus short chapter pauses. Actual rendered duration must be measured. Fourteen chapters; add a results chapter only after GECOv6 results freeze.

All hardware is conceptual, component selection is pending, and no physical numbers have been supplied. Preserve the amber **IIT Patna measurement pending** label, explicit synthetic-narration disclosure and subtitles. Sources R01–R12 are in the literature source ledger; M01–M16 are the pending laboratory fields.

## C01. What this bench is meant to establish

Visual focus: overview. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

This is the proposed GECO water and saline research bench. Its purpose is to compare a permitted pump command with evidence of fluid reaching a defined outlet, then study what happens when the monitor intervenes. The animation explains the planned arrangement; it is not footage of a completed experiment. Every component shown still needs final selection and verification. The amber labels identify physical measurements that the IIT Patna team must collect before any hardware performance claim can be made.

On-screen lines: Proposed water/saline research rig / Defined outlet and evidence boundary / No physical results yet.

Measured quantity / future field: Outlet mass or volume over a defined interval; pending. Sources/fields: M01, M02, R03.

## C02. Follow the command and the evidence

Visual focus: dataflow. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

Begin with the data path. A glucose observation enters a physiological model and a control policy. The policy proposes an amount, the authorization layer permits or rejects it, and the pump endpoint records what it accepted. These records describe digital decisions. They do not measure fluid delivery. GECO keeps the emitted fluid, the balance indication and the received measurement report as separate quantities. The diagram should show both the forward command path and the returning evidence path with their timestamps.

On-screen lines: Requested is distinct from authorized / Acknowledgment is distinct from delivery / Keep measurement and report separate.

Measured quantity / future field: Requested/authorized/accepted model amount and timestamp; physical delivery pending. Sources/fields: R01, R05, M02, M10.

## C03. What the gateway can and cannot establish

Visual focus: gateway. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The gateway coordinates messages, records authorized commands and supplies the monitor with the information its policy is allowed to use. Authentication can establish the source and integrity of defined message bytes. It cannot prove that a credentialed request is appropriate or that an actuator obeyed it. The experiment must therefore state which device, message, clock or firmware an injected fault can change. It must also name the evidence that remains available and the authority available to each comparison method.

On-screen lines: State the attack capability / Name remaining trusted evidence / Match response authority.

Measured quantity / future field: Command acceptance, message timing and policy state; device tests pending. Sources/fields: R01, R02, M10, M13.

## C04. From motor motion to carriage motion

Visual focus: mechanism. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The drive illustration contains a motor, a coupling, a lead screw and a moving carriage. Rotation is intended to translate the carriage along the rails. This is a mechanical proposal, not proof of travel accuracy. Backlash, compliance, misalignment and missed motion can make commanded displacement differ from actual displacement. The team must record the chosen parts, travel limits and assembly dimensions, then characterize their behavior. The animation should identify these components without adding a vendor name or an unmeasured performance number.

On-screen lines: Motor → coupling → lead screw / Carriage travel requires verification / Parts and tolerances pending.

Measured quantity / future field: Carriage displacement and repeatability; pending. Sources/fields: M01, M09.

## C05. The syringe and the fluid path

Visual focus: syringe. Approximately 35 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The carriage pushes a syringe plunger, and the syringe connects to tubing and the proposed stop mechanism before the receiving outlet. Plunger motion is not identical to immediate outlet flow. Fluid storage in compliant tubing, trapped air, hydraulic resistance and the outlet height can change the timing. The selected syringe bore, usable stroke, tubing dimensions and fluid preparation must be recorded. This work uses water or saline as a research fluid; the illustrated conversion to a virtual model is not a clinical insulin dose.

On-screen lines: Plunger movement can precede outlet flow / Record syringe and tubing geometry / Water/saline research only.

Measured quantity / future field: Outlet-delivery profile versus displacement; pending. Sources/fields: R03, M01, M02, M09, M12.

## C06. The receiver and balance

Visual focus: mass. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The receiving vessel rests on a balance. The instrument reports an indication affected by its calibration, resolution, noise, drift and environment. Tubing or a temperature probe touching the receiver can add forces that look like mass. The outlet and tubing therefore need a tested support arrangement, with contact, wetting and settling effects documented. We preserve the raw signed balance readings rather than treating each upward change as delivery. The receiver, outlet definition and blank-run conditions must stay consistent across matched trials.

On-screen lines: Balance indication has uncertainty / Test contact and force isolation / Preserve raw signed readings.

Measured quantity / future field: Balance indication in g, blank drift and settling; pending. Sources/fields: R03, R09, M03, M05, M06, M08.

## C07. Calibration before comparison

Visual focus: calibration. Approximately 34 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The reference-mass tray represents the planned calibration resources. Showing reference masses does not establish traceability; the actual identifiers, certificates, dates and uncertainty must accompany the experiment. The balance should be checked over the working range for repeatability and response, with before-and-after checks as defined by the protocol. The resulting uncertainty budget will combine the relevant measurement contributions and their correlations. This process determines what size of discrepancy the bench can resolve; it does not itself validate the monitor or the stop action.

On-screen lines: Record mass certificates and dates / Check working range and repeatability / Report an uncertainty budget.

Measured quantity / future field: Calibration response, repeatability and uncertainty; pending. Sources/fields: R09, M03, M16.

## C08. Temperature and mass-to-volume conversion

Visual focus: measurement. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The separate sample vial holds the temperature measurement so that the probe does not load the balance receiver. The team must establish whether this temperature represents the delivered fluid and record its timing and uncertainty. A mass-to-volume calculation also requires fluid identity and an appropriate density relation or measurement. Temperature changes, evaporation and buoyancy may matter at the intended flow scale. These corrections and their uncertainty belong in the recorded method, not in an unexplained constant hidden inside the visualization.

On-screen lines: Separate vial avoids probe loading / Validate representativeness of temperature / Record density and correction method.

Measured quantity / future field: Temperature, density and corrected volume; pending. Sources/fields: R03, R09, M04, M05.

## C09. One synchronized record

Visual focus: recording. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The logger screen brings together command events, endpoint acknowledgments, balance samples, monitor decisions and stop commands. A proposed camera and visible time marker help inspect the physical sequence and align independent records. Neither the camera nor the logger becomes ground truth merely by recording it. Clock offsets, drift, frame timing, lost messages and acquisition latency must be measured. Keep the original sample times and raw files so that another researcher can reconstruct the sequence and understand the timing uncertainty.

On-screen lines: Preserve native timestamps and raw files / Measure offset, drift, latency and loss / Camera is evidence, not an oracle.

Measured quantity / future field: Synchronization offset, jitter, latency and missing samples; pending. Sources/fields: R09, M07, M10, M16.

## C10. Reconstruct delivery without an oracle

Visual focus: measurement. Approximately 34 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

In a simulation, the program can expose the true emitted mass and keep it separate from a noisy or forged balance report. A physical rig has no such hidden truth variable available to the experimenter. Before its output drives a virtual patient, the team must select and validate a reconstruction method against an appropriate reference, including uncertainty and delay. Accumulating only positive noisy increments can create apparent delivery during zero flow. Blank and low-flow validation are therefore essential parts of this handoff.

On-screen lines: Latent simulator truth is unavailable physically / Validate reconstruction against a reference / Test zero-flow bias and delay.

Measured quantity / future field: Reconstruction error, zero-flow bias and temporal uncertainty; pending. Sources/fields: R04, R09, M07, M08, M09.

## C11. Detection and the proposed stop path

Visual focus: trip. Approximately 34 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The monitor compares authorized delivery with the available delivery evidence using a stated interval, uncertainty allowance and missing-data policy. If its rule requests a stop, a dedicated path is proposed to act on the fluid system. The team must measure the complete sequence from deviation to decision, electrical command and flow cessation. Residual flow after the command matters. Power, firmware, clock and calibration dependencies must also be tested before describing the path as independent. The animation shows the intended path, not successful containment.

On-screen lines: Separate detection from actuation / Measure flow cessation and residual flow / Test common-mode dependencies.

Measured quantity / future field: Detection delay, stop latency and post-stop flow; pending. Sources/fields: R02, M11, M12, M13.

## C12. Recovery belongs in the experiment

Visual focus: recovery. Approximately 33 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

A stopped pump also withholds subsequent intended delivery. A fair experiment follows the system through that period and through re-enabling, rather than ending the trace at the first alarm. Who may restart, what happens to outstanding commands and how power or communication restoration is handled must be specified. Record both excess and deficit, and report nuisance stops and missed deviations. A monitor that stops sooner may still have a worse overall outcome if its recovery behavior or false-stop burden is unacceptable.

On-screen lines: Follow the full post-stop interval / Report excess and deficit separately / Define restart authority.

Measured quantity / future field: Withheld delivery, restart delay, nuisance stops and overshoot; pending. Sources/fields: R02, M14, M15.

## C13. Compare methods under the same conditions

Visual focus: dataflow. Approximately 34 seconds. Evidence: METHODS_DESIGN; GECOv6_RESULTS_PENDING_FREEZE.

The software study asks whether delivery evidence adds useful information and whether a more complex monitor improves on a simpler one with the same response authority. Established physiological models and estimation methods provide the experimental setting; they are not new inventions of GECO. Hold the available inputs, tuning opportunities, disturbances and follow-up rules constant. A separate result chapter will report the frozen new experiments, including failures and uncertainty. Nothing in this conceptual rig animation predicts that the full method will outperform its comparators.

On-screen lines: Equal authority and comparable inputs / Established models, explicit lineage / Results added only after freeze.

Measured quantity / future field: Simulation outcomes and uncertainty; pending frozen GECOv6 results. Sources/fields: R01, R02, R05, R06, R07, R08.

## C14. The next evidence comes from the laboratory

Visual focus: future. Approximately 34 seconds. Evidence: CONCEPTUAL_RIG; IIT_PATNA_MEASUREMENT_PENDING.

The immediate handoff is a measurement plan: select the actual components, validate the reference method, establish calibration and synchronized acquisition, test zero-flow reconstruction, then measure delivery, stopping and recovery across repeated trials. Each amber field will be replaced only by a traceable record and an uncertainty statement. Until then, the rig remains conceptual and the demonstrated results remain within their stated simulation scope. The video uses disclosed synthetic narration; the team can replace it with a recorded explanation without changing the scientific claims.

On-screen lines: Complete the pending measurement matrix / Replace fields only with verified records / Physical and clinical claims remain separate.

Measured quantity / future field: All M01–M16 fields remain unmeasured. Sources/fields: R09, M01, M07, M08, M16.

## Voice and edit handoff

This is synthetic narration working text, not a statement by a named researcher. Use the actual generated voice label in the media provenance record; do not imply that Aman is a team member. A team-recorded replacement should retain all limitations, follow the same chapter order and be checked against subtitles. Avoid an apparent live numeric dashboard: use field names or clear pending labels. Any actual experimental footage or measured trace added later must carry the record identifier, units, timebase and evidence status.
