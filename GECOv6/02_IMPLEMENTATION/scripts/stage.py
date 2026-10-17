"""Staged GECO v4 campaign runner (foreground-safe; each stage < ~9 min).

  python scripts/stage.py calibrate   # stage 1: fit + freeze all twins
  python scripts/stage.py replay      # stage 2: benign + attack matrix on locked test
  python scripts/stage.py closed      # stage 3: closed-loop ablation
Each stage persists to results/campaign/ and can be re-run independently.
"""
from __future__ import annotations
import hashlib, json, os, sys, time
from dataclasses import asdict
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geco_v4.calibrate import calibrate_delivery
from geco_v4.campaign import (aggregate_closed, aggregate_replay, benign_campaign, calibrate_all,
                              closed_loop_campaign, load_frozen, replay_campaign)
from geco_v4.datasets import load_d1namo, load_hupa_ucm, quality_report

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "campaign")
os.makedirs(OUT, exist_ok=True)
STAGE = sys.argv[1] if len(sys.argv) > 1 else "calibrate"
MAX_ITER = int(os.environ.get("GECO_MAXITER", "70"))
WORKERS = int(os.environ.get("GECO_WORKERS", "4"))
t0 = time.time()


def load_series():
    hupa = load_hupa_ucm(os.path.join(ROOT, "data/raw/HUPA-UCM"))
    d1 = load_d1namo(os.path.join(ROOT, "data/raw/D1NAMO"))
    # HUPA0026/27/28 span 90-574 days vs the dataset's documented >=14 days: out-of-distribution
    # concatenations, excluded from calibration (recorded as a data-quality exclusion).
    series = [s for s in (hupa + d1) if len(s.cgm) <= 8000]
    return series


def usable(cal):
    return {pid: v for pid, v in cal.items() if len(v[2].cgm) >= 400 and float(pd.isna(v[2].cgm).mean()) < 0.4}


if STAGE == "calibrate":
    def sha256(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for c in iter(lambda: f.read(1 << 20), b""):
                h.update(c)
        return h.hexdigest()
    ledger = []
    for name, path, url, lic in [
        ("HUPA-UCM v1", "data/raw/HUPA-UCM/HUPA-UCM_3hbcscwz44-1.zip", "https://data.mendeley.com/datasets/3hbcscwz44/1", "CC BY 4.0"),
        ("D1NAMO v1.2.0 diabetes subset", "data/raw/D1NAMO/diabetes_subset_pictures-glucose-food-insulin.zip", "https://zenodo.org/records/5651217", "CC BY-SA 4.0")]:
        p = os.path.join(ROOT, path)
        if os.path.exists(p):
            ledger.append({"dataset": name, "file": path, "bytes": os.path.getsize(p), "sha256": sha256(p), "source_url": url, "licence": lic, "accessed": "2026-09-06"})
    json.dump(ledger, open(os.path.join(OUT, "acquisition_ledger.json"), "w"), indent=1)
    series = load_series()
    quality_report(series).to_csv(os.path.join(OUT, "data_quality.csv"), index=False)
    cal = calibrate_all(series, OUT, max_iter=MAX_ITER, workers=WORKERS, batch=int(os.environ.get("GECO_BATCH", "8")))
    dcal = calibrate_delivery()
    json.dump(asdict(dcal), open(os.path.join(OUT, "delivery_calibration.json"), "w"), indent=1)
    print(f"CALIBRATE DONE usable={len(usable(cal))}/{len(cal)} in {time.time()-t0:.0f}s", flush=True)

elif STAGE == "replay":
    from geco_v4.delivery import DeliveryCalibration
    series = load_series()
    cal = usable(load_frozen(series, OUT))
    dcal = DeliveryCalibration(**json.load(open(os.path.join(OUT, "delivery_calibration.json"))))
    if not os.path.exists(os.path.join(OUT, "benign_replay.csv")):
        ben = benign_campaign(cal, OUT, dcal, workers=WORKERS)
        print(f"benign {len(ben)} {time.time()-t0:.0f}s", flush=True)
    rep = replay_campaign(cal, OUT, dcal, workers=WORKERS, time_budget_s=float(os.environ.get("GECO_BUDGET", "150")))
    n_expected = len(cal) * len(__import__("geco_v4.campaign", fromlist=["ATTACKS_REPLAY"]).ATTACKS_REPLAY) * 2
    aggregate_replay(rep).to_csv(os.path.join(OUT, "replay_attack_matrix_aggregate.csv"), index=False)
    print(f"REPLAY {len(rep)}/{n_expected} runs in {time.time()-t0:.0f}s", flush=True)

elif STAGE == "closed":
    from geco_v4.delivery import DeliveryCalibration
    series = load_series()
    cal = usable(load_frozen(series, OUT))
    dcal = DeliveryCalibration(**json.load(open(os.path.join(OUT, "delivery_calibration.json"))))
    pids = [p for p in cal if p.startswith("HUPA")][:6]
    seeds = int(os.environ.get("GECO_SEEDS", "3"))
    clo = closed_loop_campaign(cal, OUT, dcal, participants=pids, seeds=seeds, workers=WORKERS, time_budget_s=float(os.environ.get("GECO_BUDGET", "150")))
    n_expected = len(pids) * (1 + len(__import__("geco_v4.campaign", fromlist=["ATTACKS_CLOSED"]).ATTACKS_CLOSED)) * 2 * 4 * seeds
    aggregate_closed(clo).to_csv(os.path.join(OUT, "closed_loop_ablation_aggregate.csv"), index=False)
    if len(clo) >= n_expected:
        open(os.path.join(OUT, "CAMPAIGN_DONE.txt"), "w").write(f"closed runs={len(clo)} in {time.time()-t0:.0f}s\n")
    print(f"CLOSED {len(clo)}/{n_expected} runs in {time.time()-t0:.0f}s", flush=True)
