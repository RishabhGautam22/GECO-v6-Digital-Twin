# GECO: Delivery-Evidence Monitoring for Insulin-Pump Research

Working IEEE methods-paper narrative; author names and affiliations pending the team. This is a content draft, not a final submission or a report of completed physical experiments. Use the venue-specific IEEE template when the venue is selected. Reference labels R01–R12 are provisional stable keys, to be numbered by final citation order.

## Central question and contribution

Can a monitor that separates authorized commands from evidence of delivered fluid improve fault and attack response without creating unacceptable underdelivery? GECO investigates that question through explicit signal boundaries, controlled comparisons and an instrumented water/saline bench design. The main paper should lead with the measurement and mitigation method, not the chronology of the source audit.

**Working contribution statement:** We define a research architecture in which command authorization, simulated emission, delivery measurement and stop authority are represented separately. We specify matched experiments that distinguish the value of delivery evidence from the effect of granting a stop action. We evaluate the architecture on explicitly named physiological model implementations and define an uncertainty-aware route to physical measurement. The final contribution statement must replace “specify” with “evaluate” only for experiments that have completed and survived review.

**Result slot:** [Pending frozen GECOv6 simulation results: comparator, independent unit, complete run count, effect with uncertainty, principal failure or tradeoff.] Do not fill this slot with GECOv5 results or unpublished physical numbers.

## Abstract scaffold

Automated insulin-delivery systems coordinate glucose sensing, dose computation and pump actuation. A valid command acknowledgment does not by itself quantify fluid reaching an outlet, while a stop action can prevent further delivery and also prolong underdelivery. This paper investigates a delivery-evidence monitoring architecture that separates command authorization, emission, observation and mitigation authority. The method compares monitoring policies under matched actuation authority and evaluates their behavior using explicitly documented physiological models and fault scenarios. [Insert the frozen GECOv6 experiment design, independent sample count, primary effect and uncertainty.] [Insert the main limitation or negative finding.] We also define a water/saline measurement protocol for validating delivered-fluid reconstruction and stop dynamics. Physical measurements at IIT Patna remain pending, so the present evidence supports simulation findings and a proposed bench protocol rather than physical or clinical performance.

The final abstract must be rewritten from completed results, remain self-contained and follow the chosen IEEE venue's length limit. It should not contain bracketed references or an implied institutional endorsement.

## I. Introduction — why delivery evidence matters

An automated insulin-delivery loop turns an observation of glucose into a command for a pump. Each step answers a different question. The controller selects an intended action; an authorization policy decides whether that action is permitted; the endpoint accepts a message; the actuator moves fluid; and a measurement system estimates what reached a defined outlet. Treating these quantities as interchangeable obscures both accidental faults and attacks. GECO therefore treats delivery evidence as a separate observation with a stated measurement model.

A second distinction concerns response. Detecting a mismatch and stopping a pump are different capabilities. A latched stop can limit additional emission while withholding subsequent intended delivery. A system that appears successful when only excess is measured may perform poorly when deficits and recovery are included. The evaluation should therefore ask how much each observation contributes, what action it enables and what cost that action creates.

The surrounding ideas are established. GlucOS develops a reference-monitor architecture for automated insulin delivery [R01], and KnowSafe studies predictive hazard mitigation [R02]. Insulin-pump calibration and sensor-assisted measurement are also established [R03,R04]. The proposed distinction here is an explicitly testable separation of evidence and authority, together with matched comparisons and a physical-measurement handoff. Its added value is an empirical question, not a claim of being the first digital twin or pump monitor.

End the introduction with three concrete, outcome-neutral contributions: (1) a signal/authority model; (2) matched evidence and mitigation experiments, naming which actually completed; (3) a measurement protocol with explicit pending physical work. Keep source-audit details in supplementary provenance, except where a repaired assumption directly motivates the method.

## II. Related work — three close comparisons

Use three short subsections: runtime authorization and hazard mitigation [R01,R02]; pump delivery metrology [R03,R04,R09]; physiological models and state estimation [R05–R08]. Compare what each observes, what it can change and what was evaluated. Do not present absence of physical HIL in a software work as an error if it was outside that work's claim. A compact table should have columns: prior method, observation, mitigation authority, evaluation setting and remaining GECO question. Restrict rows to works needed for the argument.

## III. System model and threat boundaries

Define the stages with explicit units and timestamps:

1. Requested amount: controller intent in the model's documented insulin units per interval.
2. Authorized amount: command permitted by policy, with provenance and sequence information.
3. Accepted/acknowledged amount: endpoint message result, not delivered-fluid evidence.
4. Emitted mass: latent actuator output available within a simulator; unavailable as an oracle on a physical rig.
5. Balance indication and received report: instrument output and communication payload, each with errors and possible compromises.
6. Reconstructed delivered fluid: a physical estimate with a defined outlet, time interval and uncertainty; **IIT Patna measurement pending**.
7. Physiological plant input: a unit-checked model input. In physical HIL this requires a validated mapping from the reconstructed delivery, not positive-only noisy increments.

Table I: capability matrix for each attack/fault. State which command, report, firmware, clock, measurement or stop path can change and which witness remains trusted. Separate forged measurement from disabled stop authority. When all remaining observations are identical under two physical histories, the monitor has no justified special knowledge of which history occurred without additional assumptions.

## IV. Monitoring and response method

Explain the authorized-delivery budget, the time-aligned delivery estimate, the uncertainty/latency allowance and the resulting discrepancy. Present cumulative signed residual, cumulative excess and cumulative deficit separately. Specify threshold origin, calibration data and the treatment of missing/delayed reports. Give pseudocode only after implementation freezes.

The response state machine should name normal, alert, stopped and re-enable states. Define who can stop, who can re-enable, how outstanding commands are handled and what happens on communication or power loss. Compare the full policy with a simpler equal-authority comparator, a command-only baseline, and evidence/stop ablations as supported by the final experiment plan. An observation-only arm must not accidentally receive a different controller policy.

Table II: method/ablation matrix, with identical stop authority and controller-policy columns made visible. A separate row must expose whether a comparison changes sensing, thresholding, controller behavior or actuation authority.

## V. Experimental design

### A. Reproducible simulation

Name the exact implementation versions, parameter sources, initial conditions, integration method, observation cadence, experiment duration, attack timing, seeds and failure handling. The independent Hovorka plant must be described as a GECO implementation of a published model, with any modified assumptions identified [R05]. Do not call the implementation FDA-approved. Use a second model family only when executed and verified; separate model-family mismatch from random parameter perturbation.

### B. Estimation and prediction

If comparing EKF and UKF, hold observation inputs, tuning opportunity, forecast origins and horizon constant. Use historical information available at each origin. Report persistence alongside model forecasts. Published UKF work motivates the comparison [R06,R07] but does not establish that UKF will win in this setting. Evaluate forecast error and uncertainty calibration separately from mitigation outcomes.

### C. Analysis

Specify independent experimental units and pair comparisons at that level. Distinguish subjects, synthetic parameter sets, seeds, windows and timepoints. Report all assigned runs, exclusions and numerical failures. Report both excess and deficit, delay, nuisance stops, missed detections and recovery. Physiological range summaries need fixed denominators and full follow-up. A primary outcome and uncertainty method should be frozen before inspecting the final comparison.

### D. Proposed physical study

**[AMBER BLOCK — IIT Patna measurement pending]** The physical water/saline study has not yet established delivery accuracy, reconstruction accuracy, stop latency, residual flow or hardware independence. Component selection, reference method validation, traceable calibration and synchronized records are pending. Simulated emitted mass is unavailable to the rig; the virtual-patient input will require a validated physical reconstruction with uncertainty and a demonstrated zero-flow behavior. A balance or camera is not automatically ground truth. **[/AMBER BLOCK]**

Figure 1: signal and authority architecture. Figure 2: component/dataflow diagram. Figure 3: proposed measurement rig with separate temperature vial, balance receiver, reference-mass tray, camera/time marker and logger. Each physical figure should carry “Conceptual rig; component selection and IIT Patna measurements pending.” Use `IIT_PATNA_PENDING_MEASUREMENTS.md` for the required fields.

## VI. Results — fill only from frozen GECOv6 tables

Table III: primary matched comparison, with unit, run count and uncertainty. Figure 4: effect across model families and failure classes, including negative results. Figure 5: representative full-follow-up traces with event markers and separate excess/deficit. Table IV: false stops, underdelivery and recovery. Table V: ablations and failed/unsupported cases. Table VI: physical measurement results, all entries explicitly pending until acquired.

Results text should state what happened before interpreting why. Do not hide failed numerical runs in the denominator. Do not mix retrospective patient data with physical tests or describe synthetic parameter sets as patients. A faster alarm without preserved delivery is not enough to claim improved safety.

## VII. Discussion and limits

State which comparison isolates delivery evidence, which isolates authority and where conclusions depend on thresholds, model assumptions and remaining trusted witnesses. Discuss missed cases, false stops, deficit after cutoff, recovery, estimator mismatch and common-mode failure. Physical uncertainty and reference-method validation remain open. A water/saline rig cannot demonstrate drug absorption, tissue delivery, clinical safety or patient benefit.

Explain the practical point in one sentence: GECO can only support decisions about what its available evidence and response path can establish; it cannot infer an unobserved physical truth by naming a sensor “independent.”

## VIII. Conclusion

Write after results freeze: one sentence for the evaluated method, one for the primary finding, one for the main limit and the next physical measurement. Avoid broad deployment or treatment recommendations.

## Back matter and supplementary package

Author information, contributions, funding, conflicts, ethics/data-governance status and approvals are team fields. Use an accurate AI-use acknowledgment [R10] rather than an editing-only claim; disclose synthetic narration. Include code/environment/run manifest, source/claim ledger, complete results and failures, additional traces, calibration protocol and the pending measurement table. Keep audit chronology and exhaustive evidence inventories in this supplement so the main paper stays focused on the method.
