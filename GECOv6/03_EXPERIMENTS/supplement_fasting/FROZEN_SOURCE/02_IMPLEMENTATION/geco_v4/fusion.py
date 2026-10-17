"""Dependency-aware evidence fusion with abstention.

Rules (all deliberately simple and auditable):

1. Evidence is grouped by provenance. Inside a group only the strongest score
   counts, so five transforms of one CGM stream cannot masquerade as five
   independent witnesses.
2. High confidence requires corroboration from at least two independent groups,
   OR a deterministic integrity/actuation violation (those are facts measured on
   the physical side of the trust boundary, not statistical suspicion).
3. Missing independent evidence lowers authority and can force abstention. It is
   never converted into reassurance.
4. The output is a compromise probability, a severity, a confidence and an
   explicit ``abstained`` flag with a rationale string per group.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum

from .detectors import Evidence


class Severity(str, Enum):
    NORMAL = "normal"
    WATCH = "watch"
    CONTAIN = "contain"
    SAFE_MODE = "safe_mode"


@dataclass(frozen=True)
class Assessment:
    compromise_probability: float
    severity: Severity
    confidence: float
    abstained: bool
    group_scores: dict
    rationale: tuple[str, ...]
    deterministic_trigger: str = ""
    uncorroborated: bool = False


class DependencyAwareFusion:
    DETERMINISTIC_GROUPS = ("actuation", "integrity")

    def __init__(self, min_reliable_groups: int = 2, contain_p: float = 0.70, safe_p: float = 0.90, watch_p: float = 0.50, deterministic_threshold: float = 0.90):
        self.min_reliable_groups = min_reliable_groups
        self.contain_p = contain_p
        self.safe_p = safe_p
        self.watch_p = watch_p
        self.deterministic_threshold = deterministic_threshold

    def assess(self, evidence: list[Evidence]) -> Assessment:
        grouped: dict[str, list[Evidence]] = defaultdict(list)
        unreliable: set[str] = set()
        for item in evidence:
            if item.reliable:
                grouped[item.group].append(item)
            else:
                unreliable.add(item.group)
        group_scores = {g: max(i.score for i in items) for g, items in grouped.items() if items}
        reliable_groups = len(group_scores)
        rationale = tuple(f"{g}={s:.2f}" for g, s in sorted(group_scores.items())) + tuple(f"{g}=unreliable" for g in sorted(unreliable - set(group_scores)))
        if not group_scores:
            return Assessment(0.5, Severity.WATCH, 0.0, True, {}, ("no reliable evidence",))
        probability = 1.0 - math.prod(1.0 - s for s in group_scores.values())
        support = sum(s >= 0.55 for s in group_scores.values())
        deterministic = ""
        for g in self.DETERMINISTIC_GROUPS:
            if group_scores.get(g, 0.0) >= self.deterministic_threshold:
                deterministic = g
        abstained = reliable_groups < self.min_reliable_groups
        uncorroborated = probability >= self.contain_p and support < 2 and not deterministic
        confidence = min(1.0, reliable_groups / 4.0) * (0.5 + 0.5 * abs(probability - 0.5) * 2.0)
        if deterministic:
            severity = Severity.SAFE_MODE
            abstained = False
        elif probability >= self.safe_p and support >= 2:
            severity = Severity.SAFE_MODE
        elif probability >= self.contain_p and support >= 2:
            severity = Severity.CONTAIN
        elif probability >= self.watch_p:
            severity = Severity.WATCH
        else:
            severity = Severity.NORMAL
        if (abstained or uncorroborated) and severity == Severity.NORMAL:
            severity = Severity.WATCH
        return Assessment(probability, severity, confidence, abstained, dict(group_scores), rationale, deterministic, uncorroborated)
