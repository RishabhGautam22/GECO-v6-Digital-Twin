# GECO v5 numerical and causal research fork

This directory is a new, nonclinical fork of immutable GECO v4. It retains the
`geco_v4` import name for compatibility. The package version identifies the fork
as `5.0.0-research-numerical-causal`. It is not firmware, a clinical algorithm,
a verified hardware system, or a claim of deployment readiness.

The original runtime, original tests, scripts, datasets, and frozen calibration
JSON were copied before applying the changes listed in `PATCH_LEDGER.json`.
Original v4 experiment results remain legacy evidence in the immutable package;
new runs must use a new output directory and identify this fork in their manifest.
The copied original campaign/publication scripts are retained for provenance and
are not independent analysis or new validation.

## Scope of this fork

- Check numerical values, dimensions, missing-data policy, parameter domains,
  mass-unit mappings, and sample-duration consistency explicitly.
- Reject non-finite numerical payloads; represent absent truth measurements as
  missing/unreliable evidence. Do not substitute a private physical measurement.
- Keep actual pump emission separate from local measurement, accepted reported
  measurement, and the simulated plant's input.
- Clear CUSUM event state when a sample is missing so missing samples do not repeat
  the previous alarm event.

No firmware is modified, no new attack capability is added, and no clinical
threshold is proposed. Other round-one findings remain open, including the inactive
supplied scenario IDs, general bolus-versus-safe-mode semantics, predictive-reference
accounting, firmware interoperability, and firmware initialization/time contracts.
The independent science review also records SC-017: the frozen filter covariance
can lose positive semidefiniteness under some inflation/missing-data conditions.
This fork does not change that covariance update, refit parameters, or claim to
resolve that open statistical-model issue.

## Trace semantics

| Field | Meaning |
|---|---|
| `pump_emitted_mass_g` | Actual increment of the virtual pump's `dispensed_g` during this step. |
| `local_measured_mass_g` | Local balance reading with measurement noise, drift, and quantization. |
| `local_measured_delta_g` | Signed local balance increment. |
| `network_reported_mass_g` | Mass in an accepted numerical TRUTH message, otherwise `None`. |
| `network_reported_delta_g` | Delta in an accepted numerical TRUTH message, otherwise `None`. |
| `network_truth_accepted` | Whether an accepted numerical TRUTH message was present. |
| `virtual_plant_input_u` | `pump_emitted_mass_g / grams_per_unit`. This drives the simulated plant. |
| `pump_executed_physical_u` | Compatibility alias for `virtual_plant_input_u` in this fork. Its v4 meaning was different. |
| `delta_mass_g`, `measured_u` | Compatibility fields for signed local measurement, not actual emission. |

The summaries `true_emitted_u_during_attack`,
`nominal_authorised_u_during_attack`, and
`true_excess_over_nominal_u_during_attack` use actual emission and nominal
authorization. Existing `delivered_u_during_attack` and `excess_u_during_attack`
retain the v4 local-balance/calibrated-expected-mass semantics. Compare like
quantities; do not mix these outcome definitions.

## Missing data

CGM input may contain NaN to mark a missing sample; infinity is invalid. Event
arrays (insulin, bolus, carbohydrate) must be finite and nonnegative. The D1NAMO
loader explicitly treats a blank event amount cell as no entered amount (zero);
this does not estimate unlogged events. Nonblank malformed, negative, or infinite
event amounts are rejected. Total insulin must include its bolus component.

## Offline validation

Use CPython 3.12.14 with `requirements-runtime.txt`, then run from this directory:

```text
python -m unittest discover -s tests -v
```

The delivered validation run passed 53 tests: 40 original tests and 13 ordinary
numeric/missing-data/causal-model regressions. The balance-offset regression checks
that the plant trajectory stays identical across three seeds when measurement-only
offsets change and feedback from the balance is disabled. This separates measurement
effects from physical emission. It does not prove clinical or hardware safety.

Frozen v4 parameter files are in `frozen_v4/`; no fitting is needed for frozen
reproduction. Fitting additionally requires SciPy and remains a separate workflow.
