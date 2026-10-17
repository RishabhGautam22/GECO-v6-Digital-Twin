"""Shared numerical validity rules for the v5 research-only compatibility fork.

These checks enforce representation and physical sign constraints, not clinical
thresholds. Missing sensor values use None/NaN only at documented input boundaries.
"""
import math
from numbers import Real


def finite_number(value, name, *, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return value


def positive_number(value, name):
    value = finite_number(value, name, minimum=0)
    if value == 0:
        raise ValueError(f"{name} must be positive")
    return value


def finite_tree(value, name="payload"):
    """Reject non-finite nested numbers before JSON serialization/signing."""
    if isinstance(value, float):
        finite_number(value, name)
    elif isinstance(value, dict):
        for key, item in value.items():
            finite_tree(item, f"{name}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            finite_tree(item, f"{name}[{i}]")


def payload_numeric_issue(message_type, payload):
    """Return a data-schema explanation, without throwing through runtime ingress."""
    try:
        finite_tree(payload)
        required = {"CGM": ("glucose_mgdl",), "CMD": ("units",),
                    "ACK": ("executed_units",), "BUDGET": ("units",),
                    "TRUTH": ("mass_g", "delta_g")}.get(message_type, ())
        for field in required:
            minimum = 0 if field in ("units", "executed_units") else None
            finite_number(payload.get(field), field, minimum=minimum)
        if message_type == "CONFIG":
            version = payload.get("version")
            if isinstance(version, bool) or not isinstance(version, int) or version < 0:
                raise ValueError("version must be a nonnegative integer")
    except (ValueError, TypeError) as exc:
        return str(exc)
    return None
