# IIT Patna saline-twin handoff

**Status: IIT Patna measurement pending.** This package supplies a conceptual assembly, measurement definitions, acquisition templates and an offline file validator. It contains no completed laboratory trial and no interface that controls a pump. All dimensions in the rendered assembly are illustrative. Select actual parts and check fit before fabrication.

## What the physical study will answer

The simulation knows an actuator's latent emitted mass. The laboratory does not. The first physical question is therefore whether a stated measurement method reconstructs fluid delivered at a defined outlet, over a defined interval, with an uncertainty small enough for the proposed experiment. Only then should the reconstructed input drive a virtual patient. Water/saline measurements establish apparatus behavior under tested conditions; they do not establish insulin absorption or clinical benefit.

Define the outlet at the free tubing end above the receiver. Record the fluid identity and hydraulic configuration. Keep tubing mechanically supported away from the balance. Neither the tubing nor a temperature probe should load the receiving vessel. The conceptual design uses a separate temperature sample vial. Check that the separate sample represents the delivered fluid temperature closely enough for the density conversion.

## Sequence of work

1. **Freeze the apparatus record (M01-M02).** Complete component models, serials where appropriate, firmware/software versions, dimensions, fluid identity, outlet, receiver, hydraulic head and environmental conditions. Photograph the actual assembly and record departures from the concept.
2. **Validate measurement (M03-M08).** Obtain the reference masses and instrument calibration evidence. Measure signed no-flow records, drift, evaporation, repeatability, settling and sensitivity to tubing/contact/vibration. Select and validate a sufficiently independent reference method. A camera can support timing and observability but is not automatically a flow standard. Retain raw signed readings.
3. **Freeze reconstruction.** Define corrections, lag, sampling, averaging and uncertainty propagation before evaluating the locked physical comparison. Demonstrate no-flow and low-flow behavior. Never sum positive-only differences of noisy mass samples as a substitute for validated flow reconstruction. Do not fill missing readings with simulator truth.
4. **Characterize delivery (M09).** Predeclare steady and pulsed settings, observation horizons, repetitions, randomized order, exclusion rules and an uncertainty-based sample-size rationale. Retain failed and invalid runs. Report aggregate results and the complete trial denominator.
5. **Characterize time and stopping (M10-M13).** Align device and host clocks through a common event. Separately record event occurrence, monitor decision, electrical stop command and observed flow cessation. Predefine a flow-cessation criterion with threshold, observation window and uncertainty. Distinguish fluid crossing the defined outlet from arrival in the receiver and balance settling. Quantify post-stop delivery over a stated follow-up. Test relevant power, communication, clock and actuation common modes.
6. **Evaluate burden and recovery (M14-M15).** Measure benign exposure, nuisance stop episodes, missed deviations, total/longest interruption, withheld delivery and restart overshoot. Recovery authorization and outstanding-command handling must be explicit. Predefine absent-operator and failed-verification cases.
7. **Run the locked study and release records (M16).** Freeze thresholds and analysis before the final physical trials, use randomized order, preserve raw data and deviations, then replace each highlighted manuscript/PPT field with a verified result and uncertainty.

The lab team chooses actual operating ranges, component ratings and acceptance values after calibration and local review. Simulation constants such as a five-minute interval, a mass-per-research-unit convention or the simulated stop threshold are not hardware specifications.

## Quantity and evidence definitions

| Quantity | Record | What it establishes |
|---|---|---|
| Requested/authorized amount | Timestamped command and authorization records | Intended/permitted model action, not outlet delivery |
| Actuator acceptance | Endpoint acknowledgment | Message acceptance, not fluid displacement |
| Raw signed balance indication | Native acquisition sample with status and calibration ID | Instrument indication, subject to drift, force and timing errors |
| Reconstructed delivery | Frozen method/version, estimate, interval and uncertainty | An estimate at the defined outlet, once validated |
| Independent reference | Separate calibrated method and raw records | Agreement or disagreement within stated uncertainty and independence assumptions |
| Stop event chain | Event, decision, stop-command and cessation times | Distinct delays with synchronization uncertainty |
| Virtual patient input | Validated reconstruction and explicit unit mapping | Input to a simulation, not a measured clinical dose |

For a corrected collected-mass difference, write the full model before calculating uncertainty. A simple illustration is `Δm_corrected = m_end − m_start − blank_correction`. If all terms are independent, squared standard uncertainties add. Shared calibration and drift errors can correlate terms; use the covariance terms instead of assuming independence. For volume, propagate density and temperature/model uncertainty through `V = Δm_corrected / ρ`. A negative corrected estimate near zero is a possible noisy observation, not negative physical delivery and not permission to rectify every increment. The proper inferential treatment must be validated for the measurand and interval.

The supplied offline validator deliberately does not estimate flow, choose a filter, assign uncertainty or infer cessation from a camera. Those require the actual calibration and reconstruction evidence.

## Files and acquisition behavior

Copy the blank files in `templates/` to a new trial folder. Fill `trial_metadata.json` and write append-only CSV records. Preserve native instrument timestamps and monotonically increasing sequence numbers. Store the acquisition host monotonic time separately from device time. A later alignment must preserve the original timestamps, transformation/version, residuals and uncertainty.

`samples.csv` carries one channel sample per row. A missing or invalid observation has an empty value and an explicit status, never zero. `events.csv` records transitions with identifiers and supporting record references. `measurement_results.csv` is a reporting template; each row requires a raw-record hash, method/version and uncertainty evidence before it can replace a pending manuscript field. The local file validator checks structure, finite numbers, units and clock/sequence ordering. A PASS is data-contract validity only.

Run `python3 tools/validate_acquisition.py PATH_TO_TRIAL_FOLDER`. Empty templates intentionally fail as incomplete. The tests and small in-memory test data under `tools/` are synthetic software fixtures, not laboratory records.

## Replacement map

Use the stable identifiers M01-M16 in `../04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md`. Every replacement should state the original pending field, the measured value and unit, uncertainty/interval, method/version, trial denominator, deviations, source record hash and human reviewer. Keep the highlighted block until those fields are complete. The paper's simulation findings remain simulation findings after physical data are added.

## Measurement references and limits

JCGM 100:2008, *Evaluation of measurement data  -  Guide to the expression of uncertainty in measurement*, supplies the measurement-model and uncertainty framework: https://doi.org/10.59161/JCGM100-2008E . Consult current supplements and amendments at https://www.bipm.org/en/committees/jc/jcgm/publications . This protocol does not claim certification under that guide.

NIST SP 250-98 describes a gravimetric liquid-flow calibration system: https://doi.org/10.6028/NIST.SP.250-98 . It supports the general mass/time principle. Its large-flow operating range and reported uncertainty do not transfer to this proposed low-flow apparatus.
