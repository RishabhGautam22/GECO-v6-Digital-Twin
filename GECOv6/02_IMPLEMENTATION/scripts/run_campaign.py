"""Run the full GECO v4 in-silico campaign.

Usage:  PYTHONPATH=. python scripts/run_campaign.py [--quick]

Stages (each writes to results/campaign_<date>/):
  0. data ledger and quality report
  1. per-participant twin calibration (HUPA-UCM 25 + D1NAMO) with frozen thresholds
  2. delivery-twin calibration on the virtual bench (benign)
  3. benign replay on locked test windows (false containment / alert burden)
  4. replay attack matrix: 23 scenarios x 2 profiles x participants
  5. closed-loop ablation: virtual patient closed through the (virtual) pump + balance
  6. aggregates
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from dataclasses import asdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geco_v4.calibrate import calibrate_delivery
from geco_v4.campaign import aggregate_closed, aggregate_replay, benign_campaign, calibrate_all, closed_loop_campaign, replay_campaign
from geco_v4.datasets import load_d1namo, load_hupa_ucm, quality_report

QUICK = "--quick" in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "results", "campaign_quick" if QUICK else "campaign")
os.makedirs(OUT, exist_ok=True)
t_start = time.time()


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# 0. ledger + quality
ledger = []
for name, path, url, licence in [
    ("HUPA-UCM v1", "data/raw/HUPA-UCM/HUPA-UCM_3hbcscwz44-1.zip", "https://data.mendeley.com/datasets/3hbcscwz44/1", "CC BY 4.0"),
    ("D1NAMO v1.2.0 diabetes subset (glucose/food/insulin)", "data/raw/D1NAMO/diabetes_subset_pictures-glucose-food-insulin.zip", "https://zenodo.org/records/5651217", "CC BY-SA 4.0"),
]:
    p = os.path.join(ROOT, path)
    if os.path.exists(p):
        ledger.append({"dataset": name, "file": path, "bytes": os.path.getsize(p), "sha256": sha256(p), "source_url": url, "licence": licence, "accessed": "2026-09-06"})
with open(os.path.join(OUT, "acquisition_ledger.json"), "w") as f:
    json.dump(ledger, f, indent=1)

hupa = load_hupa_ucm(os.path.join(ROOT, "data/raw/HUPA-UCM"))
d1 = load_d1namo(os.path.join(ROOT, "data/raw/D1NAMO"))
series = hupa + d1
if QUICK:
    series = hupa[:4] + d1[:2]
qr = quality_report(series)
qr.to_csv(os.path.join(OUT, "data_quality.csv"), index=False)
print(qr.to_string(), flush=True)

# 1. calibration
cal = calibrate_all(series, OUT, max_iter=60 if QUICK else 120, workers=4)
# keep only participants with a usable locked test window (>= 400 steps, < 40 % missing)
usable = {pid: v for pid, v in cal.items() if len(v[2].cgm) >= 400 and float(pd.isna(v[2].cgm).mean()) < 0.4}
print(f"usable participants: {len(usable)} / {len(cal)}", flush=True)

# 2. delivery calibration (virtual bench, benign)
dcal = calibrate_delivery()
with open(os.path.join(OUT, "delivery_calibration.json"), "w") as f:
    json.dump(asdict(dcal), f, indent=1)
print("delivery calibration", dcal, flush=True)

# 3. benign replay
ben = benign_campaign(usable, OUT, dcal)
print("benign done", len(ben), f"{time.time()-t_start:.0f}s", flush=True)

# 4. replay attack matrix
rep = replay_campaign(usable, OUT, dcal, workers=4)
aggregate_replay(rep).to_csv(os.path.join(OUT, "replay_attack_matrix_aggregate.csv"), index=False)
print("replay matrix done", len(rep), f"{time.time()-t_start:.0f}s", flush=True)

# 5. closed loop (subset of participants as virtual patients)
pids = [p for p in usable if p.startswith("HUPA")][: (2 if QUICK else 6)]
clo = closed_loop_campaign(usable, OUT, dcal, participants=pids, seeds=2 if QUICK else 3, workers=4)
aggregate_closed(clo).to_csv(os.path.join(OUT, "closed_loop_ablation_aggregate.csv"), index=False)
print("closed loop done", len(clo), f"{time.time()-t_start:.0f}s", flush=True)

with open(os.path.join(OUT, "CAMPAIGN_DONE.txt"), "w") as f:
    f.write(f"finished in {time.time()-t_start:.0f}s; participants={len(usable)}; replay_runs={len(rep)}; closed_runs={len(clo)}\n")
print("ALL DONE", flush=True)
