"""Campaign runner: calibration, replay attack matrix, closed-loop ablations, figures.

Everything is deterministic given the seeds and the frozen calibrations. Outputs go
to results/<campaign>/ as CSV/JSON plus PNG figures. Nothing here touches hardware.
"""
from __future__ import annotations

import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict

import numpy as np
import pandas as pd

from .attacks import catalogue
from .bench import BenchConfig, RunResult, records_to_rows, run_scenario
from .calibrate import TwinValidation, calibrate_delivery, calibrate_participant, calibration_split
from .datasets import ParticipantSeries, load_d1namo, load_hupa_ucm, quality_report
from .physiology import TwinParams

ATTACKS_REPLAY = ["RF-01", "RF-02", "RF-03", "RF-04", "RF-05", "RF-05b", "RF-05r", "RF-05f", "RF-06", "RF-07", "RF-08", "RF-09", "RF-10",
                  "ACT-01", "ACT-02", "ACT-03", "ACT-04", "INT-01", "INT-02", "COORD-01", "COORD-02", "COORD-03", "COORD-04"]
ATTACKS_CLOSED = ["RF-05", "RF-05b", "RF-05r", "RF-06", "RF-10", "ACT-01", "ACT-03", "COORD-01", "COORD-03", "COORD-04"]
ABLATIONS = ["no_geco", "kernel_only", "geco_no_delivery", "geco_full"]


def _cfg_from_validation(v: TwinValidation, profile: str, ablation: str = "geco_full", mode: str = "replay", seed: int = 0) -> BenchConfig:
    # V6 threshold failures are explicit; never consume a failed search ceiling.
    for name, scalar in (("threshold_result", v.cusum_threshold), ("threshold6_result", v.cusum6_threshold)):
        result = getattr(v, name, {})
        if result and (not result.get("feasible", False) or result.get("threshold") != scalar):
            raise ValueError(f"Cannot construct runtime from inconsistent/infeasible {name}")
    return BenchConfig(
        profile=profile,
        mode=mode,
        ablation=ablation,
        cusum_drift=v.cusum_drift,
        cusum_threshold=v.cusum_threshold,
        r_std=v.r_std,
        forecast_policy=v.forecast_policy,
        ar1_rho=v.ar1_rho,
        sigma6_mgdl=v.sigma6_mgdl,
        cusum6_threshold=v.cusum6_threshold,
        innovation_inflation=v.innovation_inflation,
        seed=seed,
    )


# ------------------------------------------------------------------ calibration
def _calibrate_one(args):
    series, max_iter = args
    t0 = time.time()
    params, val, test = calibrate_participant(series, max_iter=max_iter)
    return series.participant_id, params, val, test, time.time() - t0


def load_frozen(series_list: list[ParticipantSeries], out_dir: str) -> dict[str, tuple[TwinParams, TwinValidation, ParticipantSeries]]:
    """Rebuild the calibration dict from a saved twin_params_frozen.json without refitting.

    Test windows are re-derived deterministically from the dataset split, so stages 2/3
    can run in separate (foreground) processes after stage 1 has frozen the parameters.
    """
    from .datasets import chronological_split
    with open(os.path.join(out_dir, "twin_params_frozen.json")) as f:
        frozen = json.load(f)
    by_id = {s.participant_id: s for s in series_list}
    out: dict[str, tuple[TwinParams, TwinValidation, ParticipantSeries]] = {}
    for pid, blob in frozen.items():
        if pid not in by_id:
            continue
        if blob.get("status", "frozen") != "frozen":
            continue
        params = TwinParams(**blob["params"])
        val = TwinValidation(participant=pid, params=blob["params"], **{k: v for k, v in blob["validation"].items() if k not in ("participant", "params")})
        # Preserve the split that generated the calibration; V6 uses exact50/25/25.
        _, _, test = calibration_split(by_id[pid]) if val.split_provenance else chronological_split(by_id[pid])
        out[pid] = (params, val, test)
    return out


def calibrate_all(series_list: list[ParticipantSeries], out_dir: str, max_iter: int = 120, workers: int = 4, batch: int | None = None) -> dict[str, tuple[TwinParams, TwinValidation, ParticipantSeries]]:
    """Fit + freeze twins. Incremental: participants already present in
    twin_params_frozen.json are skipped, and (with `batch`) at most that many new
    participants are processed per call, so each call fits inside a short timeout."""
    os.makedirs(out_dir, exist_ok=True)
    frozen_path = os.path.join(out_dir, "twin_params_frozen.json")
    frozen = json.load(open(frozen_path)) if os.path.exists(frozen_path) else {}
    todo = [s for s in series_list if s.participant_id not in frozen]
    if batch is not None:
        todo = todo[:batch]
    if todo:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for pid, params, val, test, dt in ex.map(_calibrate_one, [(s, max_iter) for s in todo]):
                frozen[pid] = {"params": asdict(params), "validation": {k: v for k, v in asdict(val).items() if k != "params"}}
                json.dump(frozen, open(frozen_path, "w"), indent=1)  # save after each so partial progress survives a timeout
                print(f"calibrated {pid} in {dt:.1f}s: rmse30_val={val.rmse30_val:.1f} h={val.cusum_threshold} h6={val.cusum6_threshold} rho={val.ar1_rho:.2f} infl={val.innovation_inflation:.2f}", flush=True)
        rows = [{"participant": pid, **{k: v for k, v in blob["validation"].items()}} | {"p_" + k: v for k, v in blob["params"].items()} for pid, blob in frozen.items()]
        pd.DataFrame(rows).to_csv(os.path.join(out_dir, "twin_validation.csv"), index=False)
    print(f"frozen total={len(frozen)}, remaining={len([s for s in series_list if s.participant_id not in frozen])}", flush=True)
    return load_frozen(series_list, out_dir)


# ------------------------------------------------------------------ replay campaign
def _replay_one(args):
    pid, params, val, replay, delivery_cal, attack_id, profile, steps, start, duration = args
    cfg = _cfg_from_validation(val, profile)
    res = run_scenario(cfg, None, params, delivery_cal, replay=replay, steps=steps, attack_catalogue_id=attack_id, attack_start=start, attack_duration=duration)
    row = {"participant": pid, **res.summary}
    trace = records_to_rows(res.records) if attack_id in ("RF-10", "COORD-03", "COORD-04", "RF-05b", "ACT-01", "RF-06") else None
    return row, trace, attack_id, profile, pid


def replay_campaign(calibrations, out_dir: str, delivery_cal, steps: int = 360, start: int = 96, duration: int = 48, workers: int = 4, attacks=None, time_budget_s: float = 150.0) -> pd.DataFrame:
    """Resumable: appends each run to replay_attack_matrix.csv and skips (participant,
    attack,profile) triples already present, so it can be run across several short calls."""
    import time as _t
    os.makedirs(os.path.join(out_dir, "traces"), exist_ok=True)
    attacks = attacks or ATTACKS_REPLAY
    csv_path = os.path.join(out_dir, "replay_attack_matrix.csv")
    done = set()
    if os.path.exists(csv_path):
        prev = pd.read_csv(csv_path)
        done = set(zip(prev["participant"], prev["attack_id"], prev["profile"]))
    jobs = []
    for pid, (params, val, test) in calibrations.items():
        replay = test.replay_dict()
        if len(replay["cgm"]) < steps:
            continue
        for aid in attacks:
            for profile in ("legacy", "protected"):
                if (pid, aid, profile) in done:
                    continue
                jobs.append((pid, params, val, replay, delivery_cal, aid, profile, steps, start, duration))
    if not jobs:
        return pd.read_csv(csv_path)
    header_needed = not os.path.exists(csv_path)
    t0 = _t.time()
    kept_traces = 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row, trace, aid, profile, pid in ex.map(_replay_one, jobs, chunksize=2):
            pd.DataFrame([row]).to_csv(csv_path, mode="a", header=header_needed, index=False)
            header_needed = False
            if trace is not None and kept_traces < 60 and pid.endswith(("0001P", "0003P", "0010P")):
                pd.DataFrame(trace).to_csv(os.path.join(out_dir, "traces", f"{pid}_{aid}_{profile}.csv"), index=False)
                kept_traces += 1
            if _t.time() - t0 > time_budget_s:
                print(f"replay time budget reached; {len(done)}+ done, resume to continue", flush=True)
                break
    return pd.read_csv(csv_path)


def _benign_one(args):
    pid, params, val, replay, delivery_cal, profile = args
    cfg = _cfg_from_validation(val, profile)
    res = run_scenario(cfg, None, params, delivery_cal, replay=replay)
    return {"participant": pid, **res.summary, "phys_alarms_per_day": sum(1 for r in res.records if (r.cusum >= cfg.cusum_threshold) or (r.cusum6 >= cfg.cusum6_threshold)) / max(res.summary["days"], 1e-9)}


def benign_campaign(calibrations, out_dir: str, delivery_cal, workers: int = 4) -> pd.DataFrame:
    jobs = [(pid, params, val, test.replay_dict(), delivery_cal, profile) for pid, (params, val, test) in calibrations.items() for profile in ("legacy", "protected")]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(_benign_one, jobs))
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(out_dir, "benign_replay.csv"), index=False)
    return df


# ------------------------------------------------------------------ closed loop
def _closed_one(args):
    pid, params, val, delivery_cal, attack_id, profile, ablation, seed, steps, start, duration = args
    cfg = _cfg_from_validation(val, profile, ablation=ablation, mode="closed_loop", seed=seed)
    rng = np.random.default_rng(1000 + seed)
    # plant = calibrated participant with deliberate parameter mismatch (+-15 %)
    plant = TwinParams(**{**asdict(params), "p3": params.p3 * rng.uniform(0.85, 1.15), "kc": params.kc * rng.uniform(0.85, 1.15), "p1": params.p1 * rng.uniform(0.85, 1.15)})
    res = run_scenario(cfg, None, params, delivery_cal, plant_params=plant, steps=steps, attack_catalogue_id=attack_id if attack_id != "NONE" else None, attack_start=start, attack_duration=duration)
    trace = records_to_rows(res.records) if (seed == 0 and ablation in ("geco_full", "no_geco") and profile == "legacy") else None
    return {"participant": pid, "seed": seed, **res.summary}, trace, attack_id, profile, ablation, pid


def closed_loop_campaign(calibrations, out_dir: str, delivery_cal, participants: list[str] | None = None, seeds: int = 3, steps: int = 576, start: int = 120, duration: int = 60, workers: int = 4, attacks=None, time_budget_s: float = 150.0) -> pd.DataFrame:
    """Resumable closed-loop ablation; appends per-run and skips completed keys."""
    import time as _t
    os.makedirs(os.path.join(out_dir, "traces_closed"), exist_ok=True)
    attacks = attacks or ATTACKS_CLOSED
    pids = participants or list(calibrations.keys())
    csv_path = os.path.join(out_dir, "closed_loop_ablation.csv")
    done = set()
    if os.path.exists(csv_path):
        prev = pd.read_csv(csv_path)
        done = set(zip(prev["participant"], prev["attack_id"], prev["profile"], prev["ablation"], prev["seed"]))
    jobs = []
    for pid in pids:
        params, val, _ = calibrations[pid]
        for aid in ["NONE"] + attacks:
            for profile in ("legacy", "protected"):
                for ablation in ABLATIONS:
                    for seed in range(seeds):
                        if (pid, aid, profile, ablation, seed) in done:
                            continue
                        jobs.append((pid, params, val, delivery_cal, aid, profile, ablation, seed, steps, start, duration))
    if not jobs:
        return pd.read_csv(csv_path)
    header_needed = not os.path.exists(csv_path)
    t0 = _t.time()
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for row, trace, aid, profile, ablation, pid in ex.map(_closed_one, jobs, chunksize=2):
            pd.DataFrame([row]).to_csv(csv_path, mode="a", header=header_needed, index=False)
            header_needed = False
            if trace is not None:
                pd.DataFrame(trace).to_csv(os.path.join(out_dir, "traces_closed", f"{pid}_{aid}_{profile}_{ablation}.csv"), index=False)
            if _t.time() - t0 > time_budget_s:
                print("closed-loop time budget reached; resume to continue", flush=True)
                break
    return pd.read_csv(csv_path)


# ------------------------------------------------------------------ aggregation
def aggregate_replay(df: pd.DataFrame) -> pd.DataFrame:
    def agg(g: pd.DataFrame) -> pd.Series:
        n = len(g)
        return pd.Series(
            {
                "n": n,
                "prevention_rate_mean": g["prevention_rate"].mean(skipna=True),
                "watch_detect_frac": g["first_watch_delay_min"].notna().mean(),
                "contain_detect_frac": g["first_containment_delay_min"].notna().mean(),
                "physiology_alarm_frac": g["first_physiology_alarm_delay_min"].notna().mean(),
                "cutoff_frac": g["first_cutoff_delay_min"].notna().mean(),
                "contain_delay_median_min": g["first_containment_delay_min"].median(),
                "cutoff_delay_median_min": g["first_cutoff_delay_min"].median(),
                "excess_u_median": g["excess_u_during_attack"].median(),
                "excess_before_cutoff_median": g["excess_u_before_cutoff"].median(),
                "unmet_auto_u_attack_median": g["unmet_automated_units_during_attack"].median(),
                "false_containment_pre_per_day_mean": g["false_containment_episodes_per_benign_day"].mean(),
                "false_cutoffs_sum": g["false_cutoffs"].sum(),
            }
        )
    return df.groupby(["attack_id", "profile"]).apply(agg).reset_index()


def aggregate_closed(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["tbr_70", "tbr_54", "tir_70_180", "min_glucose", "excess_u_during_attack", "first_containment_delay_min", "first_cutoff_delay_min", "false_containment_episodes_per_benign_day", "unmet_automated_units_during_attack"]
    g = df.groupby(["attack_id", "profile", "ablation"])[cols].agg(["median", "mean"])
    g.columns = ["_".join(c) for c in g.columns]
    return g.reset_index()
