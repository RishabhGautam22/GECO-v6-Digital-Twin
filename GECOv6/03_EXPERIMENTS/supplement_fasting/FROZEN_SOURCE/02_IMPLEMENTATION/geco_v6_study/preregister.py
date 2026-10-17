"""Materialize study design and synthetic split before outcome execution."""
from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "03_EXPERIMENTS/comparative_study"

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "PREREGISTERED_SPEC.json"
    if path.exists():
        raise RuntimeError("Preregistration exists; amendments must be separate files")
    spec = {
      "version": "1.0", "registered_utc": datetime.now(timezone.utc).isoformat(),
      "purpose": "Offline synthetic fault-containment comparison; not a patient holdout or deployment study",
      "plant_families": ["geco_original", "hovorka_2004"],
      "units_per_family": {"calibration": 8, "locked_test": 24},
      "independent_unit": "synthetic parameter vector; two repeated seeds are averaged within unit before inference",
      "noise_meal_seeds": [1103, 2707], "parameter_seed": 202609071,
      "steps": 576, "dt_min": 5.0, "fault_start_step": 144, "fault_end_step_exclusive": 168,
      "warmup_steps": 36,
      "conditions": ["clean", "excess_2x", "occlusion", "stuck_on", "cgm_bias_40", "cgm_missing", "excess_bias_25", "excess_bias_report_mask"],
      "fault_mapping": {
        "excess_2x": "ACT-01 physical emission multiplier 2",
        "occlusion": "ACT-02 physical delivery zero",
        "stuck_on": "ACT-03 adds 0.25 research U per step while powered",
        "cgm_bias_40": "Existing RF-05 numerical +40 mg/dL sensor perturbation only; no wire or security simulation",
        "cgm_missing": "Existing missing-sensor abstraction; no RF execution",
        "excess_bias_25": "Existing COORD-03 2x physical multiplier and +25 mg/dL components only; no injected commands/keys",
        "excess_bias_report_mask": "Same plus existing COORD-04 reported mass replacement with authorized mass; local cutoff remains enabled in ALL arms"
      },
      "arms": ["full_manual", "full_supervised", "simple_manual", "simple_supervised", "sham_manual", "oracle"],
      "main_run_count": 4608,
      "primary_estimand": "Fixed-clean-command intervention: generate one clean feedback command tape per parameter unit/seed, then apply identical requested commands, meals and exogenous random arrays in each condition/arm. Paired arm-minus-clean outcomes and full-minus-simple differences quantify containment/recovery on that fixed tape, not autonomous closed-loop efficacy.",
      "clean_controller": "Production ResearchController; unit-specific equilibrium basal, default target/gain/cap; current clean sensor and corrected production twin 30-minute forecast, with causal basal-hold future insulin and no future meals",
      "production_integration": "Import corrected geco_v4.PhysiologyTwin, GlucoseModel, ResearchController and freshly refitted parameter/calibration records; pooled median frozen calibration drives study twin; new study adapter only coordinates offline sensors, detectors and recovery",
      "detectors": {
        "simple": "absolute single-step reported-mass residual / fixed benign mass residual scale",
        "full": "new study adapter: max(two-sided delivery CUSUM, geometric corroboration of delivery CUSUM and one physiology-group CUSUM). Physiology group uses max standardized innovation and causal due forecast residual, never counts two CGM transforms as separate evidence groups. This adapter is not the unmodified v4 complete protocol/kernel stack.",
        "cusum": "drift 0.5, absolute standardized input clipped at 6, reset on statistical containment; physiology uses production corrected filter and selected forecast policy",
        "calibration": "Separate full/simple threshold strictly above maximum warmup-excluded clean run statistic on all 32 calibration runs; both have zero empirical calibration-run statistical containments. No proven population false-alarm bound. Freeze thresholds before test outcomes; report locked clean containments separately."
      },
      "shared_authority": {
        "max_command_u": 0.30, "grams_per_research_unit": 0.1005,
        "local_per_step_margin_g": 0.03, "local_rolling_12_step_margin_g": 0.05,
        "budget_factor": 1.05, "sensor_missing_trip_steps": 6,
        "measurement": "0.01-g quantized cumulative balance, median five 0.003-g Gaussian samples; same pre-generated noise array across arms. Physical pump quantization 200 steps/U, calibration factor1.015, 0.0015-g dribble and 0.0008-g noise only on positive delivery.",
        "stop": "Main simulation stops future powered emission on next five-minute sample after observed trip; current-sample emission cannot be undone. No subsecond measured latency claim."
      },
      "recovery": {
        "states": ["RUN", "LATCHED", "VERIFY", "PROBATION"],
        "operator_authorization": "Fixed every24 samples (120min), independent of fault condition/end/evaluator truth; all arms share authorization schedule",
        "latch_min_steps": 6, "quiet_window_steps": 6,
        "manual": "At operator slot, after cooldown and six observed quiet local-mass samples plus currently available CGM, clear latch. No retrospective fault-end knowledge.",
        "supervised": "Same operator/quiet prerequisites, then three bounded verification samples (min(clean request,0.08U)), requiring available CGM and aggregate local mass within0.012g of expected calibrated mass; then six probation samples capped0.08U before RUN. Monitor-visible evidence can be insufficient or misleading; this is supervised-reset emulation, not certified autonomy.",
        "catchup": "None; missed commands never accumulated or repaid",
        "oracle": "Offline evaluator-only fault-window delivery inhibition for physical faults; explicitly privileged reference, no clinical ideality claim"
      },
      "secondary_sensitivity": {
        "parameter_units": "First6 locked units of each family, both seeds",
        "conditions": ["clean", "excess_2x", "occlusion", "stuck_on"],
        "arms": ["full_supervised", "simple_supervised"],
        "feedback": "Same controller settings, but each arm updates requests from its own sensor/twin; paired clean reference matches arm and stop assumption. This is a separate feedback-policy estimand, not fixed commands.",
        "stop_models": ["one_sample_baseline", "one_additional_sample_of_power", "residual_tail_0.02U_per_step_for3steps"],
        "run_count": 576,
        "limitations": "Stop delay and residual tail are prespecified engineering assumptions, not measured rig characteristics; powered delay conservatively keeps prior authorized request and current physical fault abstraction."
      },
      "metrics": ["total_emitted_u", "stepwise_excess_vs_clean_u", "stepwise_deficit_vs_clean_u", "net_emission_difference_u", "longest_interruption_min", "total_interruption_min", "post_fault_recovery_latency_min_or_censored", "time_below54_pct", "time_below70_pct", "time70to180_pct", "time_above180_pct", "time_above250_pct", "glucose_rmse_vs_clean", "glucose_mean_difference_vs_clean", "first_trip_latency_min", "trip_count", "reset_count", "failed_verification_count", "invalid_physiology_samples"],
      "inference": "Two-sided percentile95% paired bootstrap with4096 resamples at parameter-unit level, averaging two seeds within each unit; report separately by plant, condition and policy. Null/adverse estimates retained. Descriptive, no multiplicity-adjusted superiority or clinical claim.",
      "invalid_and_failures": "Every attempted run logged append-only with exception/attempt number. No failed or invalid trajectory silently dropped. Negative/nonfinite physiological states flagged; invalidity counts reported; retries separately recorded.",
      "trace_schema": "All samples include clocks, requested/authorized/emitted/local measured/reported/plant-input quantities, true and reported glucose, detector scores/state, local/statistical trip, cutoff, reset state and simulated authorization.",
      "source_freeze_gate": "Final runs require corrected filter/calibration frozen source and file hashes. This initial spec does not assert they are already available.",
      "amendments": "Any implementation or design change before/after outcomes goes into an appended amendment file; initial specification is immutable."
    }
    units = []
    rng = np.random.default_rng(spec["parameter_seed"])
    for family in spec["plant_families"]:
      for i in range(32):
        # These are independent synthetic perturbations, not fitted participant draws.
        factors = {k: float(np.exp(rng.uniform(np.log(.75), np.log(1.25)))) for k in ("sensitivity", "absorption", "clearance", "glucose_flux", "glucose_effectiveness", "gut_gain")}
        units.append({"unit_id": f"{family}_{i:02d}", "family": family, "split": "calibration" if i < 8 else "locked_test", "body_weight_kg": float(rng.uniform(55, 100)), "initial_glucose_mgdl": 120.0, "factors": factors})
    path.write_text(json.dumps(spec, indent=2) + "\n")
    unitpath=OUT / "SYNTHETIC_PARAMETER_SPLIT.json"
    unitpath.write_text(json.dumps(units, indent=2) + "\n")
    commit={"registered_utc":spec["registered_utc"], "outcomes_executed":False, "files": {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,unitpath,Path(__file__))}, "external_timestamp_registration":False}
    (OUT / "PREREGISTRATION_COMMIT.json").write_text(json.dumps(commit, indent=2)+"\n")
    print(json.dumps(commit))

if __name__ == "__main__": main()
