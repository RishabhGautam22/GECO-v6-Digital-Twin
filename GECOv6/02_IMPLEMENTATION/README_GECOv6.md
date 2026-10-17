# GECOv6 implementation  -  authoritative entry point

This README describes the current GECOv6 research release. `ARCHIVED_V5_README.md` (renamed with its bytes preserved), `requirements-runtime.txt`, `frozen_v4/`, copied publication scripts and the legacy `geco_v4.__version__` string are retained historical compatibility material. Their 53-test count and statement that covariance repair is still open describe v5, not the current numerical implementation. The import name remains `geco_v4`; identify GECOv6 by its release files and exact source hashes rather than that inherited version string.

Use [REPRODUCE_EXPERIMENTS.md](../09_REPRODUCIBILITY/REPRODUCE_EXPERIMENTS.md) for current commands, the recorded scientific dependencies, input/licensing provenance and safe fresh output directories. Do not run the copied v4 campaign/publication helpers expecting GECOv6 manuscript results.

Current work comprises:

- `geco_v4/physiology.py` and `calibrate.py`: corrected covariance and gap handling, causal selected forecasts, explicit fitting/threshold failures and fresh participant calibration. The selected causal fallback improves internal-test forecasting; it does not prove mechanistic identification or external clinical validity.
- `geco_v4/bench.py` and `campaign.py`: current legacy integration forwards calibration, policy and noise settings, supplies prior-slot monitor-visible inputs, and matches the participant-calibrated CUSUM startup at indices 36/42. These last two timing repairs occurred after the completed synthetic studies and have a separate patch/review receipt.
- `geco_v6_study/`: frozen offline comparison engine, structurally different plant, fair shared sensing/authority, complete paired outcomes and supervised-reset emulation. `supplement/` adds the separately registered, post-primary exploratory fasting and mass-CUSUM component comparison.
- `tests/`: 103 current ordinary unit/regression tests; the recorded final software log is `../08_REVIEW_AND_QA/software/legacy_timing_integration/TESTS.log`. The independent final legacy check is `../08_REVIEW_AND_QA/filter/LEGACY_INTEGRATION_RECHECK.json`.

The completed synthetic studies use exact source copies under each experiment's `FROZEN_SOURCE/`, with matching receipts. Restore these into a new workspace for exact study reproduction. The current source has intentionally different hashes in the two late legacy integration files; never rewrite a completed study manifest to match current code. Original study equations, traces and outcomes remain unchanged.

All execution reported here is offline numerical research. No participant, insulin delivery system, radio, firmware or physical rig was exercised. Baseline software licensing is not established by this release; retain the source/license records described in the reproduction guide. Unresolved measurement requirements, the primary Hovorka domain failures, internal-test exposure, identifiability limits and adverse detector comparisons remain visible in [FIX_COMPLETION_MATRIX.md](../08_REVIEW_AND_QA/FIX_COMPLETION_MATRIX.md).
