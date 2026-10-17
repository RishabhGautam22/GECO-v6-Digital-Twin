# GECOv6 rig explained

Synthetic narration: macOS Aman, nominal 155 words/minute. The voice is not a recording of a team member. All physical measurements remain pending.

## C01 What this bench is meant to establish

This is the proposed GECO water and saline research bench. Its purpose is to compare a permitted pump command with evidence of fluid reaching a defined outlet, then study what happens when the monitor intervenes. The animation explains the planned arrangement; it is not footage of a completed experiment. Every component shown still needs final selection and verification. The amber labels identify physical measurements that the IIT Patna team must collect before any hardware performance claim can be made.

## C02 Follow the command and the evidence

Begin with the data path. A glucose observation enters a physiological model and a control policy. The policy proposes an amount, the authorization layer permits or rejects it, and the pump endpoint records what it accepted. These records describe digital decisions. They do not measure fluid delivery. GECO keeps the emitted fluid, the balance indication and the received measurement report as separate quantities. Timestamps connect the forward command path with the returning evidence path, so discrepancies can be compared over the same interval.

## C03 What the gateway can and cannot establish

The gateway coordinates messages, records authorized commands and supplies the monitor with the information its policy is allowed to use. Authentication can establish the source and integrity of defined message bytes. It cannot prove that a credentialed request is appropriate or that an actuator obeyed it. The experiment must therefore state which device, message, clock or firmware an injected fault can change. It must also name the evidence that remains available and the authority available to each comparison method.

## C04 From motor motion to carriage motion

The drive illustration contains a motor, a coupling, a lead screw and a moving carriage. Rotation is intended to translate the carriage along the rails. This is a mechanical proposal, not proof of travel accuracy. Backlash, compliance, misalignment and missed motion can make commanded displacement differ from actual displacement. The team must record the chosen parts, travel limits and assembly dimensions, then characterize their behavior. The named components show how the proposed drive works, while part selection and measured performance remain for the team to establish.

## C05 The syringe and the fluid path

The carriage pushes a syringe plunger, and the syringe connects to tubing and the proposed stop mechanism before the receiving outlet. Plunger motion is not identical to immediate outlet flow. Fluid storage in compliant tubing, trapped air, hydraulic resistance and the outlet height can change the timing. The selected syringe bore, usable stroke, tubing dimensions and fluid preparation must be recorded. This work uses water or saline as a research fluid; the illustrated conversion to a virtual model is not a clinical insulin dose.

## C06 The receiver and balance

The receiving vessel rests on a balance. The instrument reports an indication affected by its calibration, resolution, noise, drift and environment. Tubing or a temperature probe touching the receiver can add forces that look like mass. The outlet and tubing therefore need a tested support arrangement, with contact, wetting and settling effects documented. We preserve the raw signed balance readings rather than treating each upward change as delivery. The receiver, outlet definition and blank-run conditions must stay consistent across matched trials.

## C07 Calibration before comparison

The reference-mass tray represents the planned calibration resources. Showing reference masses does not establish traceability; the actual identifiers, certificates, dates and uncertainty must accompany the experiment. The balance should be checked over the working range for repeatability and response, with before-and-after checks as defined by the protocol. The resulting uncertainty budget will combine the relevant measurement contributions and their correlations. This process determines what size of discrepancy the bench can resolve; it does not itself validate the monitor or the stop action.

## C08 Temperature and mass-to-volume conversion

The separate sample vial holds the temperature measurement so that the probe does not load the balance receiver. The team must establish whether this temperature represents the delivered fluid and record its timing and uncertainty. A mass-to-volume calculation also requires fluid identity and an appropriate density relation or measurement. Temperature changes, evaporation and buoyancy may matter at the intended flow scale. These corrections and their uncertainty belong in the recorded method, not in an unexplained constant hidden inside the visualization.

## C09 One synchronized record

The logger screen brings together command events, endpoint acknowledgments, balance samples, monitor decisions and stop commands. A proposed camera and visible time marker help inspect the physical sequence and align independent records. Neither the camera nor the logger becomes ground truth merely by recording it. Clock offsets, drift, frame timing, lost messages and acquisition latency must be measured. Keep the original sample times and raw files so that another researcher can reconstruct the sequence and understand the timing uncertainty.

## C10 Reconstruct delivery without an oracle

In a simulation, the program can expose the true emitted mass and keep it separate from a noisy or forged balance report. A physical rig has no such hidden truth variable available to the experimenter. Before its output drives a virtual patient, the team must select and validate a reconstruction method against an appropriate reference, including uncertainty and delay. Accumulating only positive noisy increments can create apparent delivery during zero flow. Blank and low-flow validation are therefore essential parts of this handoff.

## C11 Detection and the proposed stop path

The monitor compares authorized delivery with the available delivery evidence using a stated interval, uncertainty allowance and missing-data policy. If its rule requests a stop, a dedicated path is proposed to act on the fluid system. The team must measure the complete sequence from deviation to decision, electrical command and flow cessation. Residual flow after the command matters. Power, firmware, clock and calibration dependencies must also be tested before describing the path as independent. The animation shows the intended path, not successful containment.

## C12 Recovery belongs in the experiment

A stopped pump also withholds subsequent intended delivery. A fair experiment follows the system through that period and through re-enabling, rather than ending the trace at the first alarm. Who may restart, what happens to outstanding commands and how power or communication restoration is handled must be specified. Record both excess and deficit, and report nuisance stops and missed deviations. A monitor that stops sooner may still have a worse overall outcome if its recovery behavior or false-stop burden is unacceptable.

## C13 Compare methods under the same conditions

The software study asks whether a more complex monitor improves on a simpler one with the same response authority. Established physiological models provide the experimental setting; they are not new inventions of GECO. Hold the available inputs, tuning opportunities, disturbances and follow-up rules constant. Read excess together with deficit, interruption and recovery. Report failures and uncertainty as well as average effects. The rig diagram explains this experimental logic. It does not predict that the full method will outperform its comparators.

## C14 The next evidence comes from the laboratory

The immediate handoff is a measurement plan: select the actual components, validate the reference method, establish calibration and synchronized acquisition, test zero-flow reconstruction, then measure delivery, stopping and recovery across repeated trials. Each amber field will be replaced only by a traceable record and an uncertainty statement. Until then, the rig remains conceptual and the demonstrated results remain within their stated simulation scope. The video uses disclosed synthetic narration; the team can replace it with a recorded explanation without changing the scientific claims.
