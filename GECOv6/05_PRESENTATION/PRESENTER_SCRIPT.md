# GECOv6 presenter script

A complete tour is eight minutes. Main slides can be presented selectively; technical appendix is optional. All media and assistance provenance are disclosed.

## 1. GECO: evidence, intervention and recovery

Open with the practical question: when a system reports that it delivered something, what evidence would persuade us? GECOv6 is a research package, not an approved medical device. All numerical units are research model units. The IIT Patna rig is a proposal pending construction and measurement.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 2. The motivating question

Explain the three verbs: request, permit and emit. They name different events. Then explain the tradeoff in ordinary language: stopping a malfunction can help, but a stop that lasts too long also has a cost. Do not suggest the simulations establish patient benefit.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 3. The evidence boundary

Trace the six boxes in order. A digital acknowledgment belongs near authorization; it must not be used as a substitute for emitted fluid. The experiment distinguishes local mass evidence from the network report, which matters when only the report is masked.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 4. The contribution to test

The contribution is the accountable method and evidence separation. Prior work already includes insulin safety monitors, physiological models and gravimetric pump assessment. Do not claim the first digital twin, first safety monitor or first mass-sensing pump.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 5. What each evidence source can establish

Keep these four evidence classes separate throughout the talk. The new simulated parameter vectors were unexamined before execution, but their physiological model structure is not independent clinical evidence.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 6. Corrections before new experiments

Describe what changed without calling the earlier numerical findings reliable. No predicted or authorized dose substitutes for the emitted input to the plant. Calibration infeasibility is a result to report, not a threshold to silently force.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 7. Calibration and causal prediction

Parameter fitting uses the first chronological half; tuning uses the next quarter. The last quarter is an internal held-out segment of already supplied records. Forecasts are compared on identical due pairs. Offline interpolation upstream in supplied preprocessing limits strict claims about raw-data causality.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 8. Thirty-minute prediction error

Embedded chart values are rounded to 6 decimalplaces from the linked exact source; labels display 1 decimal. The selected model was trend for 30 participants and persistence for 1; none selected the mechanistic predictor. A median of selected participant errors is not the same as selecting the best method on the final test set.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json

## 9. Prediction findings and limits

Bootstrap intervals describe variation across these participants, not an external population guarantee. The median empirical 95% forecast coverage was 95.82%, ranging 87.50–98.92%. Good median coverage conceals poor coverage for individual participants.24/31 fits approached parameter bounds; do not infer physiological identifiability.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 10. What this says about the model

This is the plain-language answer to whether the model is “good.” A scientifically defensible model earns its role through comparison. Here the forecast evidence favors a trend or persistence fallback. Avoid referring to a vague “Jacob model”; distinguish the supplied mechanistic predictor from its numerical Jacobian.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 11. Matched intervention experiments

The primary request tape is generated in a clean reference run and replayed into each arm. This isolates intervention under a common demand. Feedback-stopping sensitivity is separately reported. Practical methods share observation channels and local cutoffs; the oracle is deliberately privileged and cannot be treated as an implementable competitor.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 12. The primary experiment

The Hovorka implementation retains the published unclipped endogenous glucose production expression and logs domain failures. The48 runs per condition/arm are 24 parameter vectors each paired over 2 seeds. Confidence intervals resample parameter vectors after averaging paired seeds.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 13. Faults and observation assumptions

The factor 2 is applied before quantization, gain, noise and dribble, so do not say exactly twice the emitted dose. Masked network reports do not compromise the independent local mass cutoff. This makes the model of remaining trusted evidence narrower than total sensor compromise.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 14. The six primary response arms

Full and simple differ in temporal aggregation as well as physiological input. Their difference alone cannot identify the incremental value of physiology. The separate exploratory fasting supplement adds a mass-CUSUM-only arm to address this component question.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 15. Response and recovery states

Trip timing is measured at the end of the triggering interval; stop effect is at the next interval in the primary model. Cooldown starts at that interval boundary. Supervised checks require current CGM and six quiet local readings; probe aggregate mass must meet the specified tolerance. The state before emission determines latch exposure. Guards remain active throughout probation.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 16. Outcomes that a stop can hide

All research-U quantities are simulated model amounts, not clinical dosing recommendations. The simulated reference is a clean model trajectory; in the physical work it must be replaced or qualified by a measured reference with an uncertainty budget.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 17. Primary experiment outcome

Execution success means the specified software ran; it does not mean the model was physiologically valid.2,108 of 4,608 main runs had domain violations, all in the Hovorka branch. This is a central limitation, not a footnote.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/comparative_study/ARM_SUMMARIES.json; 03_EXPERIMENTS/comparative_study/PAIRED_PARAMETER_UNIT_CI.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 18. Selected paired contrasts

These are parameter-vector paired bootstrap contrasts, averaged across the 2 seeds before resampling. They illustrate the central non-superiority finding; the full paper and machine-readable table contain every prespecified contrast. Hovorka comparisons cannot support credible clinical benefit because domain checks failed.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/comparative_study/PAIRED_PARAMETER_UNIT_CI.json

## 19. Physiological validity audit

EGP is endogenous glucose production. Negative EGP in the retained equations is a physiological-domain violation. The original branch also reaches remote-action clamps, which must be disclosed. We preserve all traces and do not delete problematic units to produce a favorable claim.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/comparative_study/ARM_SUMMARIES.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 20. A separate validity and component check

Clearly distinguish this post-primary protocol from the originally frozen experiment. It removes meals and compensates the nominal actuator mapping analytically. It is not an external cohort, therapy validation or a retrospective repair of primary results. The final results slide is generated only from reviewed supplemental output.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 21. Fasting supplement: validity and false stops

Post-primary exploratory design; 16 new test parameter vectors per plant,2 new noise seeds,8 conditions and 4 supervised arms. Analytically selected actuator-aware fasting commands avoid the primary meal-driven domain failures. This does not validate meal responses or actual physiology. No unit or unsuccessful result was excluded. The original family still recorded 18,648 remote-action clamp slots, including 51 in clean runs; passing the screen is not physiological validation.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/supplement_fasting/RESULT_SUMMARY.json; 03_EXPERIMENTS/supplement_fasting/ARM_SUMMARIES.json

## 22. Full versus mass CUSUM: benefits and costs

These contrasts compare the added physiological rule together with its separately clean-calibrated threshold: full 2.8330 versus mass-only 2.5291. They do not isolate physiology at an identical numerical threshold. The full detector can gain sensitivity when observations support it and incur costs when CGM is biased. These four examples do not replace the complete six-contrast table and all 8 condition results.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/supplement_fasting/PAIRED_PARAMETER_UNIT_CI.json

## 23. Reading the simulation movies

The ten cases were selected before outcome inspection: first test vector 08, seed 1103, five conditions, two plants. They are demonstrations of trace interpretation rather than a representative statistical sample. The primary estimates use all paired runs.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 24. Doubled actuator input: original model

Play the 55 second trace once. Point out the fault interval, then compare the two response states. Extra stopping is not automatically better. For Hovorka, explicitly name the domain flag counter before discussing glucose. The movie has no narration; presenter notes supply the explanation.

Evidence: SIMULATION / METHODS. Sources: 06_RIG_AND_MEDIA/Result_Player/SOURCE_RECEIPT.json

## 25. Stuck-on delivery and recovery

Play the 55 second trace once. Point out the fault interval, then compare the two response states. Extra stopping is not automatically better. For Hovorka, explicitly name the domain flag counter before discussing glucose. The movie has no narration; presenter notes supply the explanation.

Evidence: SIMULATION / METHODS. Sources: 06_RIG_AND_MEDIA/Result_Player/SOURCE_RECEIPT.json

## 26. Missing observation and interruption

Play the 55 second trace once. Point out the fault interval, then compare the two response states. Extra stopping is not automatically better. For Hovorka, explicitly name the domain flag counter before discussing glucose. The movie has no narration; presenter notes supply the explanation.

Evidence: SIMULATION / METHODS. Sources: 06_RIG_AND_MEDIA/Result_Player/SOURCE_RECEIPT.json

## 27. Combined fault: Hovorka domain flags

Play the 55 second trace once. Point out the fault interval, then compare the two response states. Extra stopping is not automatically better. For Hovorka, explicitly name the domain flag counter before discussing glucose. The movie has no narration; presenter notes supply the explanation.

Evidence: SIMULATION / METHODS. Sources: 06_RIG_AND_MEDIA/Result_Player/SOURCE_RECEIPT.json

## 28. The proposed saline twin

Walk left to right from motor and syringe to outlet receiver, balance and acquisition computer. No instrument shown has been purchased, certified or physically validated by this release. Dimensions illustrate assembly relationships and must be finalized by the team.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 29. The complete rig explanation

In Slide Show, press Tab then Enter to play the embedded movie full screen. Narration is disclosed macOS synthetic speech. The model is a conceptual render; arrows indicate paths rather than measured flow rates. Use the complete tour for a general audience, or skip it and use the following chapter clips for an engineering seminar.

Evidence: CONCEPTUAL RIG. Sources: 06_RIG_AND_MEDIA/narration/FINAL_TRANSCRIPT.md; 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md

## 30. Drive mechanism

Use the chapter clip and pause at its final component view. All performance quantities remain pending. Ask the audience to identify the reference instrument, the recorded event and the uncertainty contribution. These clips are exact excerpts from the full narrated tour.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 31. Mass measurement

Use the chapter clip and pause at its final component view. All performance quantities remain pending. Ask the audience to identify the reference instrument, the recorded event and the uncertainty contribution. These clips are exact excerpts from the full narrated tour.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 32. Independent recording and clocks

Use the chapter clip and pause at its final component view. All performance quantities remain pending. Ask the audience to identify the reference instrument, the recorded event and the uncertainty contribution. These clips are exact excerpts from the full narrated tour.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 33. Local interruption

Use the chapter clip and pause at its final component view. All performance quantities remain pending. Ask the audience to identify the reference instrument, the recorded event and the uncertainty contribution. These clips are exact excerpts from the full narrated tour.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 34. From indication to a measurement

Mass indication is not automatically true outlet delivery. The definition must identify the outlet, transport delay and capture efficiency. The balance may settle after flow changes. Density and temperature are measured or supported by a valid model. An uncertainty budget must match the actual apparatus and interval.

Evidence: PHYSICAL PROTOCOL. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md

## 35. Objective measurements at IIT Patna

A camera can support an event record, but it is not automatically a calibrated flowmeter. The local load-cell signal and an independent reference must not be the same unexamined evidence. Never label the interlock “physically stopping flow” using only a software acknowledgment.

Evidence: PHYSICAL PROTOCOL. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 36. Calibration and temperature

No mass class, certificate, sensor accuracy or vendor part is asserted. The separate probe vial avoids mechanically loading the receiver. Characterize whether that sample represents fluid temperature at the measurement boundary.

Evidence: CONCEPTUAL RIG. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md

## 37. An immutable acquisition record

The delivered validator checks data-contract consistency, not instrument accuracy. It never controls hardware. A successful validation only means the fields and rules passed. Calibration validity, physical uncertainty and experimental interpretation still require review.

Evidence: PHYSICAL PROTOCOL. Sources: 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md; 07_IIT_PATNA_HANDOFF/tools/validate_acquisition.py

## 38. Paper fields to fill after the build

These are measurement tasks, not numbers to be estimated by the writing team. Do not remove pending markers merely because the rig is assembled; remove a marker only when its evidence, analysis and review are complete.

Evidence: PHYSICAL PROTOCOL. Sources: 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md; 07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md

## 39. M01–M08: apparatus and metrology

Use the exact M01–M16 checklist in the manuscript companion; this slide groups work for planning. Confirm each identifier against the authoritative table before assigning tasks. The presentation does not authorize an unsupervised medical experiment.

Evidence: PHYSICAL PROTOCOL. Sources: 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 40. M09–M16: interruption and transfer

These are grouped labels; the exact evidence requirements and manuscript insertion locations are in the M matrix. A safe-looking animation supplies none of these measurements.

Evidence: PHYSICAL PROTOCOL. Sources: 04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md

## 41. What can be claimed now

The paper is ready for team review as a simulation/methods manuscript. Publication acceptance is a reviewer decision. The scientific value includes the negative result: added monitor complexity did not earn an unconditional superiority claim.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 42. What remains before submission

Hardware is not automatically required for every simulation paper. A submission can proceed on a carefully scoped simulation contribution if the venue accepts that scope. Hardware accuracy, physical cessation and clinical safety claims need the corresponding evidence; the manuscript does not make them.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 43. The research story

Close by returning to the opening question. The contribution is more persuasive when the audience can see what would falsify it. Explain that future saline measurements can either support or challenge the assumed sensor and actuator behavior.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 44. Technical: prediction and calibration

Refer to the paper equations and exact frozen configuration for numerical details. The filter uses a Joseph covariance update and records reset behavior. Separate one-step innovation coverage from 30-minute forecast coverage.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 45. Technical: model assumptions

These are simulation assumptions, not measured specifications of the proposed saline rig. The calibrated synthetic balance scale is not a traceable physical uncertainty. The actuator also adds configured positive-command noise and the study records all delivered values.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md

## 46. Technical: uncertainty and pairing

A large number of five-minute samples does not create the same number of independent subjects. HUPA0027P contributes 41,285 of 77,110 forecast pairs, which is why equal participant weighting and participant bootstrap matter.

Evidence: SIMULATION / METHODS. Sources: 03_EXPERIMENTS/filter_calibration/AGGREGATE_RESULTS.json; 03_EXPERIMENTS/comparative_study/PAIRED_PARAMETER_UNIT_CI.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 47. Technical: prior work and distinction

Consult the numbered manuscript references and source ledger for exact DOI, year, title and access limits. Use primary sources for factual attribution; preserve metadata-only limitations where full text was inaccessible.

Evidence: SIMULATION / METHODS. Sources: 01_RESEARCH_PROTOCOL/literature_editorial/SOURCE_LEDGER.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 48. Technical: originality and provenance

The work includes AI-assisted code, analysis, text and visuals. Style changes must not alter numerical results or erase assistance provenance. A zero exact 12 word overlap finding is not a comprehensive plagiarism check and does not cover a proprietary publication database.

Evidence: SIMULATION / METHODS. Sources: 08_REVIEW_AND_QA/editorial/FINAL_MANUSCRIPT_LOCAL_OVERLAP.json; 04_PAPER/GECOv6_MANUSCRIPT.md

## 49. Technical: reproduce and inspect

The all-in-one package contains the source and native media projects. External build tools and environments are documented. Never present a simulator replay as a physical measurement. Any sharing of the private prior archive requires a separate rights and privacy review.

Evidence: SIMULATION / METHODS. Sources: 04_PAPER/GECOv6_MANUSCRIPT.md