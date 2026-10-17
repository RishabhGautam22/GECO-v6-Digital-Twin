"""Delivery-reconciliation twin.

Estimates the saline mass that the *authorised* command should have moved, and
compares it with the mass independently measured by the truth node's balance.

Scaled-volume mapping
---------------------
Real insulin: 1 U (U-100) = 10 uL. A 0.01 g balance cannot resolve that. The bench
therefore uses a declared scale factor: 1 research unit = 100 uL of saline
(~0.1005 g at 1.005 g/mL), so a 0.01 g balance resolves 0.1 U and a 0.001 g
balance resolves 0.01 U. The factor is part of the run manifest; all delivery
metrics are reported in research units and in grams.

Thresholds are derived only from benign calibration runs (99.9th percentile of
absolute residual, or median + 3.3 MAD, whichever is larger) and frozen before
any actuator attack is executed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .detectors import Evidence, OneSidedAccumulator
from .numerics import finite_number, positive_number


@dataclass
class DeliveryCalibration:
    grams_per_unit: float = 0.1005   # scaled mapping incl. saline density
    gain: float = 1.0                # fitted: measured = gain * expected + offset
    offset_g: float = 0.0
    residual_sigma_g: float = 0.004
    threshold_g: float = 0.02        # frozen from benign runs
    noise_floor_g: float = 0.01      # balance resolution
    unauthorised_flow_g: float = 0.03  # mass increase with no outstanding command
    rel_sigma: float = 0.01          # relative residual scatter for large deliveries

    def __post_init__(self):
        for name in ("grams_per_unit", "gain", "threshold_g", "noise_floor_g"):
            positive_number(getattr(self, name), name)
        for name in ("residual_sigma_g", "unauthorised_flow_g", "rel_sigma"):
            finite_number(getattr(self, name), name, minimum=0)
        finite_number(self.offset_g, "offset_g")

    def expected_mass(self, units: float) -> float:
        return self.gain * self.grams_per_unit * max(0.0, units) + self.offset_g

    def threshold_for(self, expected_g: float) -> float:
        return max(self.threshold_g, 3.3 * self.rel_sigma * max(0.0, expected_g))

    @staticmethod
    def from_benign_runs(expected_g: np.ndarray, measured_g: np.ndarray, grams_per_unit: float, resolution_g: float) -> "DeliveryCalibration":
        expected_g = np.asarray(expected_g, dtype=float)
        measured_g = np.asarray(measured_g, dtype=float)
        if len(expected_g) < 3:
            raise ValueError("need at least three benign deliveries")
        A = np.vstack([expected_g, np.ones_like(expected_g)]).T
        gain, offset = np.linalg.lstsq(A, measured_g, rcond=None)[0]
        resid = measured_g - (gain * expected_g + offset)
        mad = float(np.median(np.abs(resid - np.median(resid)))) * 1.4826
        p999 = float(np.percentile(np.abs(resid), 99.9))
        thr = max(p999, float(np.median(np.abs(resid))) + 3.3 * mad, 2.0 * resolution_g)
        big = expected_g > 0.1
        rel = float(np.std(resid[big] / expected_g[big])) if big.sum() > 5 else 0.01
        return DeliveryCalibration(
            grams_per_unit=grams_per_unit,
            gain=float(gain),  # dimensionless: measured_g = gain * expected_g + offset_g
            offset_g=float(offset),
            residual_sigma_g=float(np.std(resid)) if len(resid) > 1 else resolution_g,
            threshold_g=thr,
            noise_floor_g=resolution_g,
            unauthorised_flow_g=max(3.0 * resolution_g, thr),
            rel_sigma=max(rel, 0.005),
        )


@dataclass
class DeliveryObservation:
    authorised_u: float
    acked_u: float | None
    delta_mass_g: float
    expected_g: float
    residual_g: float
    score: float
    label: str


@dataclass
class DeliveryTwin:
    cal: DeliveryCalibration = field(default_factory=DeliveryCalibration)
    cumulative_authorised_g: float = 0.0
    cumulative_measured_g: float = 0.0
    excess_g: float = 0.0
    history: list = field(default_factory=list)
    over_acc: OneSidedAccumulator = None
    under_acc: OneSidedAccumulator = None

    def __post_init__(self) -> None:
        # allowance = half the per-step threshold; bound = 2.5x threshold (frozen with the calibration)
        self.over_acc = OneSidedAccumulator(0.5 * self.cal.threshold_g, 2.5 * self.cal.threshold_g)
        self.under_acc = OneSidedAccumulator(0.5 * self.cal.threshold_g, 2.5 * self.cal.threshold_g)

    def reconcile(self, authorised_u: float, acked_u: float | None, delta_mass_g: float) -> tuple[Evidence, DeliveryObservation]:
        finite_number(authorised_u, "authorised_u", minimum=0)
        finite_number(delta_mass_g, "delta_mass_g")
        if acked_u is not None:
            finite_number(acked_u, "acked_u", minimum=0)
        expected = self.cal.expected_mass(authorised_u) if authorised_u > 0 else 0.0
        residual = delta_mass_g - expected
        thr = self.cal.threshold_for(expected)
        self.over_acc.update(residual)
        self.under_acc.update((-residual - max(0.0, thr - self.cal.threshold_g)) if authorised_u > 0 else 0.0)
        label = "consistent"
        if authorised_u <= 0.0 and delta_mass_g > self.cal.unauthorised_flow_g:
            score, label = 1.0, "unauthorised_flow"
        elif residual > thr:
            score = min(1.0, 0.6 + 0.4 * (residual - thr) / max(thr, 1e-6))
            label = "over_delivery"
        elif residual < -thr and authorised_u > 0:
            score = min(1.0, 0.6 + 0.4 * (-residual - thr) / max(thr, 1e-6))
            label = "under_delivery"
        else:
            score = 0.0   # inside the calibrated band: no partial suspicion (the accumulators watch slow drift)
        if label == "consistent" and self.over_acc.alarm:
            score, label = 1.0, "cumulative_over_delivery"
        elif label == "consistent" and self.under_acc.alarm:
            score, label = max(score, 0.9), "cumulative_under_delivery"
        if acked_u is not None and authorised_u > 0 and abs(acked_u - authorised_u) < 1e-6 and label == "under_delivery" and delta_mass_g < self.cal.noise_floor_g:
            label = "false_acknowledgement"
            score = 1.0
        self.cumulative_authorised_g += expected
        self.cumulative_measured_g += delta_mass_g
        self.excess_g = max(0.0, self.cumulative_measured_g - self.cumulative_authorised_g)
        obs = DeliveryObservation(authorised_u, acked_u, delta_mass_g, expected, residual, score, label)
        self.history.append(obs)
        ev = Evidence("delivery_reconciliation", "actuation", score, detail=f"{label}:res={residual:+.4f}g")
        return ev, obs

    def excess_units(self) -> float:
        return self.excess_g / max(self.cal.grams_per_unit * self.cal.gain, 1e-9)
