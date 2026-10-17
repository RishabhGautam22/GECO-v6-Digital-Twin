"""Envelope wire format and message authentication.

The same JSON envelope travels in-process (virtual bench), over UDP/Wi-Fi to ESP32
endpoints, or over a serial link. Two link profiles are supported so the bench can
measure exactly what cryptographic controls prevent:

* ``legacy``    - no signature, no nonce; only a sequence number. Reproduces the
                  historical failure classes (cleartext, capture-replay, missing
                  authentication) documented in the public CVE record.
* ``protected`` - HMAC-SHA256 over a canonical encoding with per-device keys,
                  random nonce, monotonic sequence and a freshness window.

HMAC with pre-shared research keys is appropriate for a bench. A production device
would use hardware-backed asymmetric identity and attestation; that is explicitly
out of scope.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, field, asdict
from typing import Any
from .numerics import finite_number, finite_tree

PROFILES = ("legacy", "protected")

# Message types on the bench
CGM = "CGM"            # sensor sample from the CGM endpoint
CMD = "CMD"            # therapy command from gateway to pump endpoint
ACK = "ACK"            # pump acknowledgement
TRUTH = "TRUTH"        # independent physical truth (mass, cut-off state)
BUDGET = "BUDGET"      # authorised volume budget from gateway to truth/cut-off node
ASSOC = "ASSOC"        # association / pairing request
HEARTBEAT = "HB"
CONFIG = "CONFIG"      # signed configuration / model release


@dataclass
class Envelope:
    src: str
    dst: str
    type: str
    seq: int
    ts: float
    payload: dict[str, Any]
    nonce: str = ""
    sig: str = ""
    v: int = 1
    # Non-wire metadata (never signed, never transmitted). Used for ground truth.
    meta: dict[str, Any] = field(default_factory=dict)

    def payload_wire(self) -> str:
        """Compact, key-sorted JSON of the payload - the exact bytes that travel and are signed."""
        finite_tree(self.payload)
        return json.dumps(self.payload, separators=(",", ":"), sort_keys=True, allow_nan=False)

    def canonical(self) -> bytes:
        """Signature input. Pipe-joined header fields followed by the payload text verbatim.

        This form is trivial to reproduce on a microcontroller: the receiver copies the
        payload substring from the wire text and reformats ts with six decimals.
        """
        finite_number(self.ts, "timestamp")
        head = f"{self.v}|{self.src}|{self.dst}|{self.type}|{self.seq}|{float(self.ts):.6f}|{self.nonce}|"
        return (head + self.payload_wire()).encode("utf-8")

    def to_wire(self) -> bytes:
        d = asdict(self)
        d.pop("meta", None)
        d["ts"] = float(f"{float(self.ts):.6f}")
        return json.dumps(d, separators=(",", ":"), sort_keys=True, allow_nan=False).encode("utf-8")

    @staticmethod
    def from_wire(raw: bytes) -> "Envelope":
        def invalid_constant(value):
            raise ValueError("non-finite JSON number: " + value)
        d = json.loads(raw.decode("utf-8"), parse_constant=invalid_constant)
        if not isinstance(d, dict) or not isinstance(d.get("payload", {}), dict):
            raise ValueError("envelope and payload must be JSON objects")
        finite_tree(d, "envelope")
        finite_number(d["ts"], "timestamp")
        for name, minimum in (("seq", 0), ("v", 1)):
            value = d.get(name, 1)
            if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
                raise ValueError(name + " must be a valid integer")
        return Envelope(
            src=str(d["src"]),
            dst=str(d["dst"]),
            type=str(d["type"]),
            seq=int(d["seq"]),
            ts=float(d["ts"]),
            payload=dict(d.get("payload", {})),
            nonce=str(d.get("nonce", "")),
            sig=str(d.get("sig", "")),
            v=int(d.get("v", 1)),
        )

    def copy(self, **changes: Any) -> "Envelope":
        d = asdict(self)
        d.update(changes)
        return Envelope(**d)


class Signer:
    """Signs outgoing envelopes for one identity under a link profile."""

    def __init__(self, identity: str, key: bytes | None, profile: str = "protected"):
        if profile not in PROFILES:
            raise ValueError(profile)
        self.identity = identity
        self.key = key
        self.profile = profile
        self._seq = 0

    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def make(self, dst: str, mtype: str, ts: float, payload: dict[str, Any]) -> Envelope:
        env = Envelope(self.identity, dst, mtype, self.next_seq(), ts, dict(payload))
        if self.profile == "protected":
            if self.key is None:
                raise ValueError("protected profile requires a key")
            env.nonce = secrets.token_hex(8)
            env.sig = hmac.new(self.key, env.canonical(), hashlib.sha256).hexdigest()
        return env


def sign_with_key(env: Envelope, key: bytes) -> Envelope:
    """Re-sign an envelope (used by the credentialed-attacker case and by tests)."""
    if not env.nonce:
        env.nonce = secrets.token_hex(8)
    env.sig = hmac.new(key, env.canonical(), hashlib.sha256).hexdigest()
    return env


def verify_signature(env: Envelope, key: bytes) -> bool:
    expected = hmac.new(key, env.canonical(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, env.sig or "")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
