"""Evidence constructors and change detectors.

Every piece of evidence carries an *evidence group* so that the fusion layer can
refuse to double count statistics that descend from the same source. The four
groups on the bench are:

  physiology  - everything derived from the CGM stream and the physiology twin
  provenance  - protocol-state twin verdicts (identity, freshness, replay, pairing, ack)
  actuation   - delivery-reconciliation twin (independent mass / cut-off node)
  integrity   - configuration/model signatures and audit-chain checks
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Evidence:
    name: str
    group: str
    score: float
    reliable: bool = True
    detail: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"evidence score out of range: {self.score}")


@dataclass
class TwoSidedCUSUM:
    """Two one-sided CUSUM statistics on standardised innovations.

    ``drift`` is the allowance k, ``threshold`` is h. Both are frozen from benign
    validation data before any attack is injected (see calibrate.py).
    """

    drift: float = 0.5
    threshold: float = 8.0
    positive: float = 0.0
    negative: float = 0.0
    clip: float = 6.0
    alarms: int = 0
    last_alarm: bool = False

    def reset(self) -> None:
        self.positive = 0.0
        self.negative = 0.0

    def update(self, standardized_innovation: float | None) -> Evidence:
        self.last_alarm = False
        if standardized_innovation is None or not math.isfinite(standardized_innovation):
            return Evidence("physiology_cusum", "physiology", min(1.0, self.statistic / self.threshold), reliable=False, detail="missing sample")
        z = max(-self.clip, min(self.clip, float(standardized_innovation)))
        self.positive = max(0.0, self.positive + z - self.drift)
        self.negative = max(0.0, self.negative - z - self.drift)
        score = min(1.0, self.statistic / self.threshold)
        detail = f"S+={self.positive:.2f},S-={self.negative:.2f}"
        self.last_alarm = self.alarm
        if self.alarm:
            self.alarms += 1
            self.reset()   # episode semantics: one alarm, then restart accumulation
            detail += ",ALARM"
        return Evidence("physiology_cusum", "physiology", score, detail=detail)

    @property
    def statistic(self) -> float:
        return max(self.positive, self.negative)

    @property
    def alarm(self) -> bool:
        return self.statistic >= self.threshold


def plausibility_evidence(quality: str) -> Evidence:
    score = {"ok": 0.0, "missing": 0.0, "frozen": 0.7, "implausible_rate": 0.8}.get(quality, 0.0)
    return Evidence("physiology_plausibility", "physiology", score, reliable=quality != "missing", detail=quality)


def provenance_evidence(score: float, detail: str, link_alive: bool) -> Evidence:
    return Evidence("protocol_state", "provenance", max(0.0, min(1.0, score)), reliable=True, detail=detail + ("" if link_alive else ",link_dead"))


def integrity_evidence(config_ok: bool, audit_ok: bool) -> Evidence:
    score = 0.0 if (config_ok and audit_ok) else 1.0
    return Evidence("integrity", "integrity", score, detail=f"config_ok={config_ok},audit_ok={audit_ok}")


@dataclass
class OneSidedAccumulator:
    """One-sided CUSUM on delivery residuals (grams). Alarm when cumulative excess
    beyond the allowance reaches the frozen bound. Used by the delivery twin so
    that small per-command over-deliveries (below the per-step threshold) cannot
    accumulate unnoticed."""

    allowance: float
    bound: float
    statistic: float = 0.0

    def update(self, residual: float) -> float:
        self.statistic = max(0.0, self.statistic + residual - self.allowance)
        return self.statistic

    @property
    def alarm(self) -> bool:
        return self.statistic >= self.bound

    def reset(self) -> None:
        self.statistic = 0.0
