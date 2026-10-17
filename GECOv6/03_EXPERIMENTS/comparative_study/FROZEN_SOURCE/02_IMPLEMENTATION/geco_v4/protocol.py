"""Protocol-state twin.

A deterministic state machine that tracks what trusted devices and messages *should*
look like, and turns every violation into an exact, named invariant failure.

It is the correct place to detect replay, stale traffic, unauthorised senders,
unexpected pairing, impossible state transitions, missing/duplicate/forged
acknowledgements and command/acknowledgement disagreement. None of these are
physiology guesses; they are cyber facts.

Under the ``legacy`` profile the twin can only check sequence, rate and cmd/ack
consistency (there is no signature or nonce to check). Under ``protected`` every
message is authenticated before anything else looks at it. Rejected messages never
enter the control path - they are counted as *prevented*, and separately surfaced
as provenance evidence for the fusion layer.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .wire import ACK, ASSOC, BUDGET, CGM, CMD, CONFIG, HEARTBEAT, TRUTH, Envelope, verify_signature
from .numerics import finite_number, payload_numeric_issue


class PeerState(str, Enum):
    UNKNOWN = "unknown"
    PAIRED = "paired"
    ACTIVE = "active"
    STALE = "stale"
    QUARANTINED = "quarantined"


# Invariant codes. Each is a precise, testable statement.
INV = {
    "P01": "sender identity is provisioned",
    "P02": "signature verifies under sender key",
    "P03": "nonce has not been seen before for this sender",
    "P04": "sequence number is strictly increasing",
    "P05": "message age is within the freshness window",
    "P06": "message is not future-dated beyond clock-skew allowance",
    "P07": "message type is permitted for this sender",
    "P08": "inter-arrival time is physically plausible for this stream",
    "P09": "acknowledgement references an outstanding command",
    "P10": "acknowledged amount equals authorised amount",
    "P11": "each command receives exactly one acknowledgement within the ack window",
    "P12": "association requests occur only inside the commissioning window",
    "P13": "sequence gap is within the loss allowance",
    "P14": "configuration release carries a valid signature and a newer version",
    "P15": "numerical message fields are finite and schema-valid",
}


@dataclass
class Verdict:
    accepted: bool
    violations: tuple[str, ...] = ()
    detail: str = ""

    @property
    def prevented(self) -> bool:
        return not self.accepted


@dataclass
class PeerRecord:
    identity: str
    key: bytes | None
    allowed_types: tuple[str, ...]
    state: PeerState = PeerState.PAIRED
    last_seq: int = 0
    last_rx_ts: float | None = None
    min_interval_s: float = 0.0
    seen_nonces: deque = field(default_factory=lambda: deque(maxlen=4096))
    seq_gaps: int = 0


@dataclass
class OutstandingCommand:
    cmd_id: str
    units: float
    issued_ts: float
    acked: bool = False


class ProtocolTwin:
    """Tracks identity, freshness, sequence, nonce, pairing and command/ack state."""

    def __init__(
        self,
        profile: str,
        peers: dict[str, dict[str, Any]],
        max_age_s: float = 20.0,
        max_future_skew_s: float = 2.0,
        ack_window_s: float = 30.0,
        max_seq_gap: int = 20,
        commissioning_open: bool = False,
        config_version: int = 1,
    ):
        self.profile = profile
        self.max_age_s = max_age_s
        self.max_future_skew_s = max_future_skew_s
        self.ack_window_s = ack_window_s
        self.max_seq_gap = max_seq_gap
        self.commissioning_open = commissioning_open
        self.config_version = config_version
        self.peers: dict[str, PeerRecord] = {}
        for identity, cfg in peers.items():
            self.peers[identity] = PeerRecord(
                identity=identity,
                key=cfg.get("key"),
                allowed_types=tuple(cfg.get("allowed_types", ())),
                min_interval_s=float(cfg.get("min_interval_s", 0.0)),
            )
        self.outstanding: dict[str, OutstandingCommand] = {}
        self.counters: dict[str, int] = {code: 0 for code in INV}
        self.accepted_count = 0
        self.rejected_count = 0
        self.recent_violations: deque = deque(maxlen=64)
        self.unexpected_assoc = 0
        self.ack_amount_mismatch = 0
        self.missing_acks = 0

    # ------------------------------------------------------------------ helpers
    def peer_age_s(self, identity: str, now: float) -> float:
        rec = self.peers.get(identity)
        if rec is None or rec.last_rx_ts is None:
            return float("inf")
        return max(0.0, now - rec.last_rx_ts)

    def register_command(self, cmd_id: str, units: float, now: float) -> None:
        self.outstanding[cmd_id] = OutstandingCommand(cmd_id, units, now)

    def expire_commands(self, now: float) -> int:
        """Count commands whose ack window elapsed without an acknowledgement."""
        expired = [c for c in self.outstanding.values() if not c.acked and now - c.issued_ts > self.ack_window_s]
        for c in expired:
            self.missing_acks += 1
            self.counters["P11"] += 1
            self.recent_violations.append(("P11", c.cmd_id, now))
            del self.outstanding[c.cmd_id]
        # drop old acked commands
        for cid in [c.cmd_id for c in self.outstanding.values() if c.acked and now - c.issued_ts > 10 * self.ack_window_s]:
            self.outstanding.pop(cid, None)
        return len(expired)

    # ------------------------------------------------------------------ verify
    def verify(self, env: Envelope, now: float) -> Verdict:
        violations: list[str] = []
        rec = self.peers.get(env.src)
        issue = payload_numeric_issue(env.type, env.payload)
        try:
            finite_number(now, "receiver time")
            finite_number(env.ts, "message timestamp")
        except ValueError as exc:
            issue = str(exc)
        if issue:
            return self._finish(env, ["P15"], now, rec)
        if rec is None:
            violations.append("P01")
            if env.type == ASSOC:
                if not self.commissioning_open:
                    violations.append("P12")
                    self.unexpected_assoc += 1
            return self._finish(env, violations, now, rec)
        if env.type not in rec.allowed_types:
            violations.append("P07")
        if self.profile == "protected":
            if rec.key is None or not verify_signature(env, rec.key):
                violations.append("P02")
            if not env.nonce or env.nonce in rec.seen_nonces:
                violations.append("P03")
            age = now - env.ts
            if age > self.max_age_s:
                violations.append("P05")
            if age < -self.max_future_skew_s:
                violations.append("P06")
        if env.seq <= rec.last_seq:
            violations.append("P04")
        elif env.seq - rec.last_seq - 1 > self.max_seq_gap:
            violations.append("P13")
            rec.seq_gaps += 1
        if rec.last_rx_ts is not None and rec.min_interval_s > 0.0:
            if now - rec.last_rx_ts < rec.min_interval_s:
                violations.append("P08")
        if env.type == ASSOC and not self.commissioning_open:
            violations.append("P12")
            self.unexpected_assoc += 1
        if env.type == ACK:
            cid = str(env.payload.get("cmd_id", ""))
            cmd = self.outstanding.get(cid)
            if cmd is None or cmd.acked:
                violations.append("P09")
            else:
                executed = float(env.payload.get("executed_units", 0.0))
                if abs(executed - cmd.units) > 1e-6:
                    violations.append("P10")
                    self.ack_amount_mismatch += 1
        if env.type == CONFIG:
            version = int(env.payload.get("version", 0))
            if version <= self.config_version or "P02" in violations or self.profile == "legacy":
                violations.append("P14")
        return self._finish(env, violations, now, rec)

    def _finish(self, env: Envelope, violations: list[str], now: float, rec: PeerRecord | None) -> Verdict:
        for v in violations:
            self.counters[v] += 1
            self.recent_violations.append((v, env.type, now))
        # Hard rejections: anything that breaks authentication, freshness, replay or identity.
        hard = {"P01", "P02", "P03", "P04", "P05", "P06", "P07", "P12", "P14", "P15"}
        accepted = not any(v in hard for v in violations)
        if accepted and rec is not None:
            rec.last_seq = env.seq
            rec.last_rx_ts = now
            if env.nonce:
                rec.seen_nonces.append(env.nonce)
            rec.state = PeerState.ACTIVE
            if env.type == ACK:
                cid = str(env.payload.get("cmd_id", ""))
                cmd = self.outstanding.get(cid)
                if cmd is not None:
                    cmd.acked = True
            if env.type == CONFIG:
                self.config_version = int(env.payload.get("version", self.config_version))
        if accepted:
            self.accepted_count += 1
        else:
            self.rejected_count += 1
        detail = ",".join(violations) if violations else "ok"
        return Verdict(accepted, tuple(violations), detail)

    # ------------------------------------------------------------------ evidence
    def evidence_score(self, now: float, window_s: float) -> tuple[float, str]:
        """Graded provenance evidence from violations inside a recent window.

        Hard authentication failures are prevention events; they are still evidence
        that an active adversary or fault is present on the link. Soft failures
        (rate, gaps, ack mismatch, missing ack) accumulate.
        """
        recent = [v for v in self.recent_violations if now - v[2] <= window_s]
        if not recent:
            return 0.0, "no protocol violations in window"
        hard = sum(1 for v in recent if v[0] in {"P01", "P02", "P03", "P05", "P06", "P12", "P14"})
        soft = sum(1 for v in recent if v[0] in {"P04", "P08", "P09", "P10", "P11", "P13"})
        score = min(1.0, 0.45 * min(hard, 2) + 0.25 * min(soft, 3))
        codes = sorted({v[0] for v in recent})
        return score, "violations=" + "+".join(codes)
