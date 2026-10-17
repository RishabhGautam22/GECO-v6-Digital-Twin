"""Append-only, tamper-evident event log with signed checkpoints.

The chain exposes alteration; it is not immutable storage. On the bench, periodic
checkpoints (index, hash) are exported to the truth node's isolated logger so that
a gateway-side attacker cannot silently rewrite history.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuditRecord:
    index: int
    ts: float
    event: dict[str, Any]
    previous_hash: str
    record_hash: str


class HashChainLog:
    GENESIS = "0" * 64

    def __init__(self, checkpoint_key: bytes | None = None, checkpoint_every: int = 12):
        self.records: list[AuditRecord] = []
        self.checkpoints: list[tuple[int, str, str]] = []
        self.checkpoint_key = checkpoint_key
        self.checkpoint_every = checkpoint_every

    @staticmethod
    def _digest(index: int, ts: float, event: dict[str, Any], previous_hash: str) -> str:
        material = json.dumps({"event": event, "index": index, "previous_hash": previous_hash, "ts": ts}, separators=(",", ":"), sort_keys=True, default=str).encode()
        return hashlib.sha256(material).hexdigest()

    def append(self, ts: float, event: dict[str, Any]) -> AuditRecord:
        index = len(self.records)
        previous = self.records[-1].record_hash if self.records else self.GENESIS
        rec = AuditRecord(index, ts, dict(event), previous, self._digest(index, ts, event, previous))
        self.records.append(rec)
        if self.checkpoint_key is not None and index % self.checkpoint_every == 0:
            mac = hmac.new(self.checkpoint_key, f"{index}:{rec.record_hash}".encode(), hashlib.sha256).hexdigest()
            self.checkpoints.append((index, rec.record_hash, mac))
        return rec

    def verify(self) -> tuple[bool, int | None]:
        previous = self.GENESIS
        for i, rec in enumerate(self.records):
            if rec.index != i or rec.previous_hash != previous:
                return False, i
            if not hmac.compare_digest(self._digest(rec.index, rec.ts, rec.event, rec.previous_hash), rec.record_hash):
                return False, i
            previous = rec.record_hash
        if self.checkpoint_key is not None:
            for index, h, mac in self.checkpoints:
                if index >= len(self.records) or self.records[index].record_hash != h:
                    return False, index
                expected = hmac.new(self.checkpoint_key, f"{index}:{h}".encode(), hashlib.sha256).hexdigest()
                if not hmac.compare_digest(expected, mac):
                    return False, index
        return True, None

    def tamper(self, index: int, field: str, value: Any) -> None:
        """Test hook: simulate an attacker editing a stored record in place."""
        rec = self.records[index]
        event = dict(rec.event)
        event[field] = value
        self.records[index] = AuditRecord(rec.index, rec.ts, event, rec.previous_hash, rec.record_hash)
