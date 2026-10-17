"""Deterministic safety kernel.

A small, auditable command gate in the spirit of Simplex-style runtime assurance
and the GlucOS BioKernel. Differences that matter for GECO:

* The stale-data stop is driven by the *protocol twin's* freshness state, not by
  the sensor's own timestamp. A replayed or delayed stream therefore stops
  predictive dosing even when the payload looks plausible.
* Actuation evidence from the independent truth node can request the physical
  cut-off. The cut-off itself is executed by the truth node, whose trip path does
  not depend on this software.
* The kernel never diagnoses, repairs or re-images anything. It bounds authority
  and records exact reason codes.

Every decision is reproducible from (context, parameters).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping

from .fusion import Assessment, Severity
from .numerics import finite_number, positive_number


@dataclass(frozen=True)
class KernelContext:
    now_s: float
    glucose_mgdl: float | None
    glucose_slope_mgdl_min: float
    cgm_age_s: float
    pump_age_s: float
    command_authenticated: bool
    predicted_glucose_30m: float | None
    delivered_u_3h: float
    reactive_u_3h: float
    assessment: Assessment
    actuation_score: float = 0.0
    metadata: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class KernelDecision:
    requested_u: float
    allowed_u: float
    severity: Severity
    reasons: tuple[str, ...]
    cutoff_requested: bool
    requires_human_review: bool


class SafetyKernel:
    def __init__(
        self,
        max_command_u: float = 0.30,
        max_cgm_age_s: float = 12 * 60,
        max_pump_age_s: float = 15 * 60,
        low_stop_mgdl: float = 80.0,
        predicted_low_mgdl: float = 75.0,
        predictive_budget_u_3h: float = 0.60,
        cutoff_actuation_score: float = 0.90,
    ):
        for name, value in (("max_command_u", max_command_u), ("max_cgm_age_s", max_cgm_age_s),
                            ("max_pump_age_s", max_pump_age_s), ("low_stop_mgdl", low_stop_mgdl),
                            ("predicted_low_mgdl", predicted_low_mgdl)):
            positive_number(value, name)
        finite_number(predictive_budget_u_3h, "predictive_budget_u_3h", minimum=0)
        finite_number(cutoff_actuation_score, "cutoff_actuation_score", minimum=0, maximum=1)
        self.max_command_u = max_command_u
        self.max_cgm_age_s = max_cgm_age_s
        self.max_pump_age_s = max_pump_age_s
        self.low_stop_mgdl = low_stop_mgdl
        self.predicted_low_mgdl = predicted_low_mgdl
        self.predictive_budget_u_3h = predictive_budget_u_3h
        self.cutoff_actuation_score = cutoff_actuation_score

    def authorize(self, requested_u: float, ctx: KernelContext) -> KernelDecision:
        # Invalid context is unavailable evidence, never numerical reassurance.
        try:
            finite_number(ctx.now_s, "now_s")
            finite_number(ctx.glucose_slope_mgdl_min, "glucose_slope_mgdl_min")
            for name in ("cgm_age_s", "pump_age_s", "delivered_u_3h", "reactive_u_3h"):
                finite_number(getattr(ctx, name), name, minimum=0)
            for name in ("glucose_mgdl", "predicted_glucose_30m"):
                if getattr(ctx, name) is not None:
                    finite_number(getattr(ctx, name), name)
            finite_number(ctx.actuation_score, "actuation_score", minimum=0, maximum=1)
            finite_number(ctx.assessment.compromise_probability, "compromise_probability", minimum=0, maximum=1)
            finite_number(ctx.assessment.confidence, "confidence", minimum=0, maximum=1)
            if ctx.assessment.severity not in _ORDER:
                raise ValueError("unrecognized assessment severity")
        except (ValueError, TypeError) as exc:
            return KernelDecision(requested_u, 0.0, Severity.SAFE_MODE,
                                  (f"K13 invalid numerical context: {exc}",), False, True)
        reasons: list[str] = []
        allowed = requested_u
        severity = ctx.assessment.severity
        cutoff = False

        try:
            finite_number(requested_u, "requested_u", minimum=0)
            command_valid = True
        except (ValueError, TypeError):
            command_valid = False
        if not command_valid:
            allowed, severity = 0.0, Severity.SAFE_MODE
            reasons.append("K01 invalid command")
            return KernelDecision(requested_u, 0.0, severity, tuple(reasons), False, True)
        if not ctx.command_authenticated:
            allowed, severity = 0.0, Severity.SAFE_MODE
            reasons.append("K02 command source not authenticated")
        if ctx.cgm_age_s > self.max_cgm_age_s:
            allowed = 0.0
            severity = max_sev(severity, Severity.CONTAIN)
            reasons.append("K03 CGM stale (protocol twin freshness) - predictive dosing stopped")
        if ctx.pump_age_s > self.max_pump_age_s:
            allowed = 0.0
            severity = max_sev(severity, Severity.CONTAIN)
            reasons.append("K04 pump link stale - no acknowledged state")
        if ctx.glucose_mgdl is not None and ctx.glucose_mgdl <= self.low_stop_mgdl:
            allowed, severity = 0.0, max_sev(severity, Severity.CONTAIN)
            reasons.append("K05 current glucose at/below low stop")
        if ctx.predicted_glucose_30m is not None and ctx.predicted_glucose_30m <= self.predicted_low_mgdl:
            allowed, severity = 0.0, max_sev(severity, Severity.CONTAIN)
            reasons.append("K06 predicted low glucose")
        if ctx.glucose_mgdl is not None and ctx.glucose_slope_mgdl_min < -2.0 and ctx.glucose_mgdl < 110.0:
            allowed, severity = 0.0, max_sev(severity, Severity.CONTAIN)
            reasons.append("K07 rapid fall near low range")
        if ctx.assessment.severity == Severity.SAFE_MODE:
            allowed = 0.0
            reasons.append("K08 fused assessment requires safe mode")
        elif ctx.assessment.severity == Severity.CONTAIN or ctx.assessment.abstained:
            allowed = min(allowed, self.max_command_u * 0.25)
            reasons.append("K09 containment cap (uncertain or corroborated suspicion)")
        allowed = min(max(0.0, allowed), self.max_command_u)
        if allowed < max(0.0, requested_u) and "K10 per-command cap" not in reasons and allowed == self.max_command_u:
            reasons.append("K10 per-command cap")
        advance = ctx.delivered_u_3h - ctx.reactive_u_3h
        remaining = max(0.0, self.predictive_budget_u_3h - advance)
        if allowed > remaining:
            allowed = remaining
            reasons.append("K11 rolling predictive-over-reactive budget")
        if ctx.actuation_score >= self.cutoff_actuation_score:
            cutoff = True
            allowed = 0.0
            severity = Severity.SAFE_MODE
            reasons.append("K12 independent delivery mismatch - physical cut-off requested")
        if not reasons:
            reasons.append("K00 within validated envelope")
        return KernelDecision(
            requested_u=requested_u,
            allowed_u=round(allowed, 4),
            severity=severity,
            reasons=tuple(dict.fromkeys(reasons)),
            cutoff_requested=cutoff,
            requires_human_review=severity in (Severity.SAFE_MODE,) or cutoff,
        )


_ORDER = {Severity.NORMAL: 0, Severity.WATCH: 1, Severity.CONTAIN: 2, Severity.SAFE_MODE: 3}


def max_sev(a: Severity, b: Severity) -> Severity:
    return a if _ORDER[a] >= _ORDER[b] else b
