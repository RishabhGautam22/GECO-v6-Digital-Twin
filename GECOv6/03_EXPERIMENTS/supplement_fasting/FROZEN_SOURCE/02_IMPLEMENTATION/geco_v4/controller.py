"""Research dosing controller for the bench.

This is deliberately a simple, transparent basal-plus-correction controller. It
exists only so that the bench has a closed loop to protect. It is not a clinical
algorithm and its outputs are research units of saline.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ResearchController:
    basal_u_per_step: float = 0.08      # ~1 U/h at 5-min steps
    target_mgdl: float = 120.0
    correction_gain_u_per_mgdl: float = 0.0025
    correction_threshold_mgdl: float = 150.0
    suspend_below_mgdl: float = 100.0
    max_u_per_step: float = 0.30

    def request(self, glucose_mgdl: float | None, forecast_30m: float | None) -> float:
        if glucose_mgdl is None:
            return self.basal_u_per_step * 0.5      # degraded: half basal when blind
        if glucose_mgdl < self.suspend_below_mgdl or (forecast_30m is not None and forecast_30m < 90.0):
            return 0.0
        u = self.basal_u_per_step
        if glucose_mgdl > self.correction_threshold_mgdl:
            u += (glucose_mgdl - self.correction_threshold_mgdl) * self.correction_gain_u_per_mgdl
        return float(min(self.max_u_per_step, u))
