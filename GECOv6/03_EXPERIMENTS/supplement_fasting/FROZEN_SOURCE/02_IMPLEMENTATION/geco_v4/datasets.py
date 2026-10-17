"""Dataset loaders into the GECO canonical schema.

Canonical per-sample schema (5-minute grid):
  participant_id, timestamp, glucose_mgdl (NaN = missing), basal_u, bolus_u, carbs_g,
  heart_rate_bpm, steps, source

Raw files are read-only; derived arrays are written to data/derived by the campaign.

HUPA-UCM (CC BY 4.0): 25 T1D participants, FreeStyle Libre 2 (15-min native, 5-min
preprocessed grid), pump basal/bolus, carbs, Fitbit HR/steps/calories.
D1NAMO (CC BY-SA 4.0): 9 T1D participants, CGM + manual glucose, insulin events,
food annotations; irregular timestamps re-gridded here to 5 minutes.
"""
from __future__ import annotations

import glob
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
from .numerics import finite_number

MMOL_TO_MGDL = 18.0182


def _event_amount(value, name):
    """A blank event amount means no amount entered; invalid values are errors.

    Unlike `float(value or 0)`, this policy explicitly handles pandas NaN cells.
    It does not estimate unlogged therapy or food events.
    """
    if pd.isna(value):
        return 0.0
    return finite_number(float(value), name, minimum=0)


@dataclass
class ParticipantSeries:
    participant_id: str
    source: str
    timestamps: np.ndarray
    cgm: np.ndarray          # mg/dL, NaN missing
    basal: np.ndarray        # U per 5-min step
    bolus: np.ndarray        # U per 5-min step (user initiated)
    carbs: np.ndarray        # g per step
    heart_rate: np.ndarray   # bpm, NaN missing
    steps: np.ndarray

    @property
    def insulin(self) -> np.ndarray:
        return self.basal + self.bolus

    @property
    def n_days(self) -> float:
        return len(self.cgm) * 5.0 / 1440.0

    def slice(self, a: int, b: int) -> "ParticipantSeries":
        return ParticipantSeries(self.participant_id, self.source, self.timestamps[a:b], self.cgm[a:b], self.basal[a:b], self.bolus[a:b], self.carbs[a:b], self.heart_rate[a:b], self.steps[a:b])

    def replay_dict(self) -> dict[str, np.ndarray]:
        return {"cgm": self.cgm, "insulin": self.insulin, "bolus": self.bolus, "carbs": self.carbs}


def load_hupa_ucm(root: str) -> list[ParticipantSeries]:
    files = sorted(glob.glob(os.path.join(root, "HUPA-UCM Diabetes Dataset", "Preprocessed", "*.csv")))
    out = []
    for f in files:
        d = pd.read_csv(f, sep=";", parse_dates=["time"])
        d = d.sort_values("time").reset_index(drop=True)
        # Re-grid to a strict 5-minute index (fills gaps with NaN glucose, zero insulin/carbs)
        idx = pd.date_range(d.time.iloc[0].floor("5min"), d.time.iloc[-1].ceil("5min"), freq="5min")
        d["slot"] = d.time.dt.floor("5min")
        g = d.groupby("slot").agg(glucose=("glucose", "mean"), basal=("basal_rate", "sum"), bolus=("bolus_volume_delivered", "sum"), carbs=("carb_input", "sum"), hr=("heart_rate", "mean"), steps=("steps", "sum"))
        g = g.reindex(idx)
        pid = os.path.basename(f).replace(".csv", "")
        out.append(
            ParticipantSeries(
                participant_id=pid,
                source="HUPA-UCM v1 (Mendeley 10.17632/3hbcscwz44.1)",
                timestamps=idx.values,
                cgm=g.glucose.to_numpy(dtype=float),
                basal=np.nan_to_num(g.basal.to_numpy(dtype=float)),
                bolus=np.nan_to_num(g.bolus.to_numpy(dtype=float)),
                carbs=np.nan_to_num(g.carbs.to_numpy(dtype=float)),
                heart_rate=g.hr.to_numpy(dtype=float),
                steps=np.nan_to_num(g.steps.to_numpy(dtype=float)),
            )
        )
    return out


def load_d1namo(root: str) -> list[ParticipantSeries]:
    base = os.path.join(root, "csv", "diabetes_subset_pictures-glucose-food-insulin")
    out = []
    for pdir in sorted(glob.glob(os.path.join(base, "0*"))):
        pid = "D1NAMO-" + os.path.basename(pdir)
        gl = pd.read_csv(os.path.join(pdir, "glucose.csv"))
        gl["t"] = pd.to_datetime(gl["date"] + " " + gl["time"])
        gl = gl[gl["type"] == "cgm"].sort_values("t")
        if len(gl) < 50:
            continue
        ins = pd.read_csv(os.path.join(pdir, "insulin.csv"))
        ins["t"] = pd.to_datetime(ins["date"] + " " + ins["time"])
        idx = pd.date_range(gl.t.iloc[0].floor("5min"), gl.t.iloc[-1].ceil("5min"), freq="5min")
        gl["slot"] = gl.t.dt.floor("5min")
        cgm = gl.groupby("slot")["glucose"].mean().reindex(idx).to_numpy(dtype=float) * MMOL_TO_MGDL
        bolus = np.zeros(len(idx))
        basal = np.zeros(len(idx))
        for _, r in ins.iterrows():
            slot = r["t"].floor("5min")
            if slot in idx:
                k = idx.get_loc(slot)
                fast = _event_amount(r.get("fast_insulin", 0.0), "fast_insulin")
                slow = _event_amount(r.get("slow_insulin", 0.0), "slow_insulin")
                bolus[k] += fast
                # long-acting insulin is spread over 24 h as a pseudo-basal for the twin
                if slow > 0:
                    span = min(288, len(idx) - k)
                    basal[k : k + span] += slow / 288.0
        carbs = np.zeros(len(idx))
        food_path = os.path.join(pdir, "food.csv")
        if os.path.exists(food_path):
            food = pd.read_csv(food_path)
            for _, r in food.iterrows():
                try:
                    t = pd.to_datetime(str(r["datetime"]), format="%Y:%m:%d %H:%M:%S")
                except Exception:
                    continue
                slot = t.floor("5min")
                if slot in idx:
                    # calories -> rough carbohydrate estimate (50% energy from carbs, 4 kcal/g); annotated as estimate
                    carbs[idx.get_loc(slot)] += _event_amount(r.get("calories", 0.0), "calories") * 0.5 / 4.0
        out.append(ParticipantSeries(pid, "D1NAMO v1.2.0 (Zenodo 5651217)", idx.values, cgm, basal, bolus, carbs, np.full(len(idx), np.nan), np.zeros(len(idx))))
    return out


def chronological_split(series: ParticipantSeries, cal_frac: float = 0.5, val_frac: float = 0.25) -> tuple[ParticipantSeries, ParticipantSeries, ParticipantSeries]:
    n = len(series.cgm)
    a = int(n * cal_frac)
    b = int(n * (cal_frac + val_frac))
    # align to day boundaries (288 steps) where possible
    a -= a % 288
    b -= b % 288
    return series.slice(0, a), series.slice(a, b), series.slice(b, n)


def quality_report(series_list: list[ParticipantSeries]) -> pd.DataFrame:
    rows = []
    for s in series_list:
        cg = s.cgm
        rows.append(
            {
                "participant": s.participant_id,
                "source": s.source.split(" ")[0],
                "days": round(s.n_days, 1),
                "samples": len(cg),
                "missing_frac": round(float(np.isnan(cg).mean()), 3),
                "mean_mgdl": round(float(np.nanmean(cg)), 1),
                "tbr70_frac": round(float(np.nanmean(cg < 70)), 3),
                "tar180_frac": round(float(np.nanmean(cg > 180)), 3),
                "basal_u_per_day": round(float(s.basal.sum() / max(s.n_days, 1e-9)), 1),
                "bolus_u_per_day": round(float(s.bolus.sum() / max(s.n_days, 1e-9)), 1),
                "carbs_g_per_day": round(float(s.carbs.sum() / max(s.n_days, 1e-9)), 0),
                "logged_meals_per_day": round(float((s.carbs > 0).sum() / max(s.n_days, 1e-9)), 1),
            }
        )
    return pd.DataFrame(rows)
