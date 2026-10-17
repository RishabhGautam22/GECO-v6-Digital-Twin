# Reproduce the GECOv6 numerical experiments

Start in the unpacked **GECOv6 directory**. These commands use a new temporary workspace and preserve all delivered outputs. No network, hardware, radio, firmware or new adverse-case construction is needed for experiment execution. Installing dependencies into a new virtual environment may require a package repository; an existing matching environment can instead be used offline. The preserved source restore tools perform copying/hashing only and never execute a study.

## Environment and identity

Recorded computation: CPython **3.12.7**, macOS 26.6.2 arm64, NumPy **1.26.4**, SciPy **1.13.1**, pandas **3.0.2**, Numba **0.60.0**; plotting used Matplotlib **3.9.2**. See each experiment's execution/fit/test receipt for the actual invocation and elapsed time. Computation used CPU workers; optional Numba acceleration has no fastmath. No GPU study computation was configured. The direct-package recipe below is not a complete transitive/Conda lock, and installation on a new operating system has not been demonstrated in this release. Use numerical tolerance comparisons and record the new environment rather than claiming cross-platform bit identity.

```sh
GECO_V6_PACKAGE="$PWD"
GECO_V6_WORK="$(mktemp -d "${TMPDIR:-/tmp}/geco-v6-repro.XXXXXX")"
python3.12 -m venv "$GECO_V6_WORK/environment"
GECO_V6_PY="$GECO_V6_WORK/environment/bin/python"
"$GECO_V6_PY" -m pip install -r "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/requirements-scientific-v6.txt"
```

For an existing environment, set `GECO_V6_PY` to its Python executable instead of creating/installing one. `/opt/anaconda3/bin/python` identifies the original host only and is not a portable requirement. The inherited `02_IMPLEMENTATION/requirements-runtime.txt` describes v5; do not use it as the v6 fitting recipe. The bundled application Python passed 14 filter tests using the pure-Python fallback, but it lacked SciPy and is not a demonstrated full-refit environment.

## Verify sources and current tests without a campaign

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study primary --verify-only
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study supplement --verify-only
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_calibration_workspace.py" --mode frozen-test --verify-only
cd "$GECO_V6_PACKAGE/02_IMPLEMENTATION"
"$GECO_V6_PY" -m unittest discover -s tests -v
```

The current full suite contains **103 tests**, recorded in `08_REVIEW_AND_QA/software/legacy_timing_integration/TESTS.log` (4.035 s on the recorded host). Discovery avoids an unrelated installed `tests` package namespace. Earlier milestones remain: 91 tests in `08_REVIEW_AND_QA/filter/TESTS_FULL_FINAL.txt`; 14 bundled fallback checks in `TESTS_BUNDLED_RUNTIME_FINAL.txt`; 99 pre-supplement tests in `03_EXPERIMENTS/supplement_fasting/PRE_OUTCOME_TESTS.log`. These are historical receipts, not conflicting current totals. Independent late integration review passed in `08_REVIEW_AND_QA/filter/LEGACY_INTEGRATION_RECHECK.json`.

Source verification checks the **preserved** 25-file primary and 30-file supplemental sets against their completed freezes. Current `geco_v4/bench.py` and `campaign.py` include later prior-slot/startup repairs and intentionally differ. The filter/calibration source subset remains equal to its fit freeze. `PARTICIPANT_SOURCE_FILES.json` hashes 52 extracted CSV inputs and two supplied archive files using package-relative paths; the calibration restore verifier checks these before copying. `INPUT_ARRAY_MANIFEST.json` separately records canonical participant arrays, eligibility and chronological windows.

## A. Refit/tune all supplied participant records, then test separately

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_calibration_workspace.py" --mode refit --destination "$GECO_V6_WORK/refit"
cd "$GECO_V6_WORK/refit"
"$GECO_V6_PY" 03_EXPERIMENTS/filter_calibration/run_calibration.py fit --workers 4 --max-iter 80 > fit.log 2>&1
"$GECO_V6_PY" 03_EXPERIMENTS/filter_calibration/run_calibration.py test > test.log 2>&1
"$GECO_V6_PY" 03_EXPERIMENTS/filter_calibration/run_calibration.py report > report.log 2>&1
```

The first invocation performs fit-window parameter/normalization work and tune-window policy/threshold selection, writing the new `FIT_FREEZE_RECEIPT.json` before test outcomes. The second invocation consumes that freeze and guards source and canonical-array hashes. Exact split boundaries are floor(0.50N) and floor(0.75N); these are previously exposed internal test segments, not a new external patient holdout. All 34 supplied records are accounted for: **31 frozen, two eligibility exclusions, one negative-input failure**. Retain exceptions/exclusions; do not change negative source entries or discard failed records to match a desired count.

Reference results are under the delivered `03_EXPERIMENTS/filter_calibration/`: `FROZEN_CALIBRATION.json`, `FIT_FREEZE_RECEIPT.json`, `TEST_RESULTS.json`, `TEST_RECEIPT.json`, `PARTICIPANT_RESULTS.csv`, `AGGREGATE_RESULTS.json` and `test_predictions/`. The original fit receipt reports **107.272 s**, the separate test receipt **3.969 s**. The retained first attempt before an import-guard packaging correction is `attempt001_pre_import_guard_fix/`; it is not silently overwritten. The restore copies the original runner/preregistration bytes and data layout, but original timestamps and JSON file hashes will differ in a new execution.

To evaluate the supplied frozen calibration without refitting, use a **different fresh directory**:

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_calibration_workspace.py" --mode frozen-test --destination "$GECO_V6_WORK/frozen-test"
cd "$GECO_V6_WORK/frozen-test"
"$GECO_V6_PY" 03_EXPERIMENTS/filter_calibration/run_calibration.py test > test.log 2>&1
"$GECO_V6_PY" 03_EXPERIMENTS/filter_calibration/run_calibration.py report > report.log 2>&1
```

Frozen participant calibration SHA256: `4502e797edecb906981e73db4a8d38cde609eea4bc0d74edfcc7282a9b47b649`. Neither restore mode copies delivered test outcomes into the new output directory. The original freeze remains available as `ORIGINAL_FIT_FREEZE_REFERENCE.json`.

## B. Reproduce primary synthetic outcomes using their frozen calibration

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study primary --destination "$GECO_V6_WORK/primary"
cd "$GECO_V6_WORK/primary/02_IMPLEMENTATION"
"$GECO_V6_PY" -m geco_v6_study.campaign execute --workers 4 > ../primary-execution.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.summarize > ../primary-summary.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.audit_results > ../primary-qa.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.plot_results > ../primary-plot.log 2>&1
```

The default `all` mode executes **4,608 fixed-clean-command runs plus 576 separate feedback/stop-assumption runs**, retaining per-run attempts, failures, references, compressed full traces and source hashes. The two seeds are repetitions within each synthetic vector. Main intervals use 24 test vectors per plant; the sensitivity uses six. The shared command tape is part of the main causal estimand and must not be recast as autonomous closed-loop efficacy. Primary config SHA256: `bc1126499a3ccc22d35445dbc6ef94291a217a3a388b806fca0887d11290889e`.

The delivered campaign contains 5,184 completed outcomes and zero execution failures; its recorded driver elapsed time was **117.719 s with four workers**, excluding earlier calibration and later analysis. Independent review checked **2,985,984 slots with zero metric/integrity discrepancies**. Domain-invalid Hovorka results remain in the outputs and limit interpretation. Preserve original `EXECUTION_MANIFEST.json`, attempt ledgers and reviewer receipts when comparing a new run. Do not use full compressed trace hashes as cross-run numerical equivalence tests: GZIP headers and execution timestamps can change while numerical arrays match.

To recompute the **32 clean synthetic calibration runs** as well, restore primary into another fresh directory with `--recalibrate`. This preserves the old config/results under reference names and leaves calibration attempts/traces empty, then prepare before execute:

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study primary --recalibrate --destination "$GECO_V6_WORK/primary-recalibrate"
cd "$GECO_V6_WORK/primary-recalibrate/02_IMPLEMENTATION"
"$GECO_V6_PY" -m geco_v6_study.campaign prepare --calibration "$GECO_V6_PACKAGE/03_EXPERIMENTS/filter_calibration/FROZEN_CALIBRATION.json" > ../primary-calibration.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.campaign execute --workers 4 > ../primary-execution.log 2>&1
```

This preserves the original frozen participant calibration for comparison. Substituting a newly refitted calibration creates a new transferred configuration and must be identified as such. A new config's historical absolute provenance path/timestamp can differ without changing its numerical parameters.

## C. Reproduce the post-primary fasting/component supplement

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study supplement --destination "$GECO_V6_WORK/supplement"
cd "$GECO_V6_WORK/supplement/02_IMPLEMENTATION"
"$GECO_V6_PY" -m geco_v6_study.supplement.study execute --workers 4 > ../supplement-execution.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.supplement.summarize > ../supplement-summary.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.supplement.audit_results > ../supplement-qa.log 2>&1
```

This executes **2,048 runs**: two plants × 16 new test vectors × two new seeds × eight conditions × four supervised arms. It also saves 64 clean references; delivered accounting is 2,112 complete test/reference attempts plus 16 calibration runs, zero failures. Recorded driver elapsed time was **43.921 s with four workers**, excluding calibration and analysis. Independent review checked **1,179,648 outcome slots with zero discrepancies**, including full-grid nominal compensation. Config SHA256: `0dc073508dcddd3eff2f272a7860feccd78dfe16d3e04ddc378f0446d122e983`.

For the **16 clean supplemental calibration runs**, use another fresh supplement restoration with `--recalibrate`, and prepare before execute:

```sh
"$GECO_V6_PY" "$GECO_V6_PACKAGE/09_REPRODUCIBILITY/restore_campaign_workspace.py" --study supplement --recalibrate --destination "$GECO_V6_WORK/supplement-recalibrate"
cd "$GECO_V6_WORK/supplement-recalibrate/02_IMPLEMENTATION"
"$GECO_V6_PY" -m geco_v6_study.supplement.study prepare > ../supplement-calibration.log 2>&1
"$GECO_V6_PY" -m geco_v6_study.supplement.study execute --workers 4 > ../supplement-execution.log 2>&1
```

The copied primary frozen config stays present because it supplies the transferred filter and shared settings. Do not call `register`: the new-run objective is reproduction of the already recorded parameter/seeds split, not a new outcome-selected design. The supplement remains explicitly post-primary exploratory and fasting constant-request; it does not resolve the original meal-excited model failures. All adverse/null comparisons and model-boundary counts must remain. Default outcome-only restorations include the original calibration traces/ledger so the post-run audit has complete calibration accounting; `--recalibrate` deliberately avoids combining original and new calibration attempts.

## Remaining portability limits and concrete remedies

| Item | Status / remedy |
|---|---|
| Current legacy source differs from completed study freeze | Resolved for reproduction by `restore_campaign_workspace.py` and preserved source sets; verification and fresh-directory import/source gates passed. Never edit original manifests to suppress this difference. |
| Calibration runner writes beside itself and refuses existing freezes/tests | Resolved by `restore_calibration_workspace.py`: a new complete relative tree preserves original source/preregistration hashes and extracted CSV paths. Existing delivered outputs remain intact. |
| Original `/opt/anaconda3/bin/python` and user-specific provenance paths | Historical metadata/docstring, not runtime file dependencies in the experiment entry points. Select a matching Python and use the restoration tree. No core experiment execution blocker remains from these paths. |
| Old v5 README, dependency file and package version marker | README bytes renamed to `ARCHIVED_V5_README.md`; `README_GECOv6.md` is authoritative. The legacy import/version string is documented, not relied upon for release identity. The new dependency recipe is separate. |
| Full environment lock / other host performance | Direct package versions are recorded; a complete transitive lock and external-host numerical/performance replication remain unverified. Record package versions, BLAS/CPU/OS and tolerances on the reproducing host. |
| Third-party input/legal provenance | Bundled relative input hashes, participant source records and recorded dataset-license metadata are available in `DATA_AND_DEPENDENCY_PROVENANCE.md`. No open-source license is invented for the baseline or private PDFs. |
| Other media/native-app automation | Rendering and PowerPoint tooling have their own application/runtime requirements and receipts. This numerical guide does not claim those host-specific application entry points are portable. |

This consolidation performed source/data hashing, restore/import/source-gate checks and documentation review only. It did not rerun a long study, refit participants or modify any frozen study file. See `CONSOLIDATION_QA.json`, `RESTORATION_QA.json` and `CALIBRATION_RESTORATION_QA.json` for the bounded verification actually performed.
