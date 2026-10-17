"""GECO v4 - Saline Digital Twin runtime for automated-insulin-delivery security research.

Non-clinical research software. Never connect to a person, an insulin reservoir or a
care-delivery system. The bench moves water/saline only.

Package layout
--------------
wire        : envelope wire format, HMAC signing, legacy/protected profiles
protocol    : protocol-state twin (identity, freshness, sequence, nonce, cmd/ack matching)
physiology  : physiology twin (5-state model with interstitial lag, EKF, calibration)
delivery    : delivery-reconciliation twin (commanded units vs measured saline mass)
detectors   : two-sided CUSUM, plausibility, evidence constructors
fusion      : dependency-aware fusion with abstention
kernel      : deterministic safety kernel (bounded authority, predictive-low, stale stop)
controller  : research dosing controller (bench only)
attacks     : attack library acting on the real message stream (MITM object)
hal         : hardware abstraction (virtual pump/scale/radio and ESP32 serial/UDP adapters)
bench       : run orchestration, event capture, manifests
datasets    : HUPA-UCM / D1NAMO loaders into the canonical schema
calibrate   : per-participant twin fitting and validation
campaign    : replay and closed-loop campaigns, ablations, metrics, figures
"""

__version__ = "5.0.0-research-numerical-causal"
BASELINE_VERSION = "4.0.0"
RESEARCH_ONLY = True
