"""Attack library operating on the real message stream.

The attacker is a man-in-the-middle object sitting on the bench channel. It sees
every envelope, can drop, delay, modify or inject, and holds whichever keys the
scenario's precondition grants it. It never gets an oracle: if it modifies a
signed envelope under the protected profile, the signature simply fails at the
receiver - exactly as it would on the wire.

Actuator-side compromises (firmware over-delivery, stuck-on, false ack,
occlusion) are not network attacks; they are expressed as PumpFault objects that
the scenario applies to the pump device during the attack window.

Every scenario declares: id, name, target channel, precondition (what the
attacker must already have), knowledge, start/end steps, parameters, and the
expected primary control (prevention / detection / mitigation). The expected
control is the *hypothesis*; the campaign measures what actually happened.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from .hal import PumpFault
from .wire import ACK, ASSOC, BUDGET, CGM, CMD, CONFIG, TRUTH, Envelope, sign_with_key


@dataclass
class AttackSpec:
    id: str
    name: str
    channel: str                       # cgm | cmd | ack | truth | assoc | config | actuator | log | multi | none
    start_step: int
    end_step: int
    params: dict[str, Any] = field(default_factory=dict)
    precondition: str = ""
    knowledge: str = ""
    expected_control: str = ""         # hypothesis: prevention | detection | mitigation | undetectable
    keys: dict[str, bytes] = field(default_factory=dict)   # credentials granted by the precondition

    def active(self, step: int) -> bool:
        return self.start_step <= step < self.end_step and self.id != "NONE"


BENIGN = AttackSpec("NONE", "benign", "none", 0, 0, expected_control="none")


class Attacker:
    """Man-in-the-middle on the bench channel plus actuator-fault injector."""

    def __init__(self, spec: AttackSpec, rng):
        self.spec = spec
        self.rng = rng
        self.captured_cgm: list[Envelope] = []
        self.captured_cmd: list[Envelope] = []
        self.delayed: list[tuple[int, Envelope]] = []
        self.log: list[dict[str, Any]] = []
        self.injected_seq = 100000
        self.last_authorised_u: float = 0.0
        self.attacker_signer_seq = 0

    # ---------------------------------------------------------------- helpers
    def _note(self, step: int, action: str, env: Envelope | None, extra: str = "") -> None:
        self.log.append({"step": step, "attack": self.spec.id, "action": action, "type": env.type if env else "", "src": env.src if env else "", "detail": extra})

    def _mark(self, env: Envelope, action: str) -> Envelope:
        env.meta = dict(env.meta)
        env.meta["attack"] = self.spec.id
        env.meta["attack_action"] = action
        return env

    ROLE = {"cgm-01": "cgm", "gw-01": "gateway", "pump-01": "pump", "truth-01": "truth", "updater": "updater"}

    def _sign_as(self, env: Envelope, identity: str) -> Envelope:
        key = self.spec.keys.get(self.ROLE.get(identity, identity))
        if key is not None:
            env.nonce = ""
            sign_with_key(env, key)
        else:
            env.sig = ""  # no credentials: forged envelope has no valid signature
        return env

    def actuator_fault(self, step: int) -> PumpFault:
        s = self.spec
        if not s.active(step):
            return PumpFault()
        p = s.params
        if s.id in ("ACT-01", "COORD-03", "COORD-04"):
            return PumpFault("over", float(p.get("factor", 2.0)))
        if s.id == "ACT-02":
            return PumpFault(p.get("mode", "under"), float(p.get("factor", 0.4)))
        if s.id == "ACT-03":
            return PumpFault("stuck_on", 1.0, float(p.get("rate_u_per_step", 0.25)))
        if s.id == "ACT-04":
            return PumpFault("false_ack")
        return PumpFault()

    # ---------------------------------------------------------------- MITM path
    def intercept(self, env: Envelope, step: int, now: float) -> list[Envelope]:
        """Called for every envelope in flight. Returns the envelopes to deliver now."""
        s, p = self.spec, self.spec.params
        # Passive capture is always on (the eavesdropper case measures what is visible).
        if env.type == CGM:
            self.captured_cgm.append(copy.deepcopy(env))
            self.captured_cgm = self.captured_cgm[-600:]
        if env.type == CMD:
            self.captured_cmd.append(copy.deepcopy(env))
            self.captured_cmd = self.captured_cmd[-100:]
            self.last_authorised_u = float(env.payload.get("units", 0.0))
        if not s.active(step):
            return [env]

        if s.id == "RF-01":
            self._note(step, "eavesdrop", env, "payload_plaintext=" + str(env.payload)[:60])
            return [env]

        if s.id == "RF-02" and env.type == CGM:
            # Replace the live sample by a captured one from `lag` steps ago. A capable
            # attacker re-numbers the sequence and timestamp (trivial when there is no
            # signature; under the protected profile this breaks the signature instead).
            lag = int(p.get("lag_steps", 24))
            if len(self.captured_cgm) > lag:
                old = copy.deepcopy(self.captured_cgm[-lag - 1])
                if p.get("renumber", True):
                    old.seq, old.ts = env.seq, env.ts
                self._note(step, "replay", old, f"lag={lag}")
                return [self._mark(old, "replayed")]
            return [env]

        if s.id == "RF-05" and env.type == CGM:
            mode = p.get("mode", "bias")
            e = copy.deepcopy(env)
            g = float(e.payload["glucose_mgdl"])
            if mode == "bias":
                g += float(p.get("magnitude", 40.0))
            elif mode == "ramp":
                g += float(p.get("slope", 1.0)) * (step - s.start_step)
            elif mode == "freeze":
                g = float(p.get("value", g))
            elif mode == "scale":
                g *= float(p.get("factor", 1.3))
            e.payload["glucose_mgdl"] = round(max(20.0, min(600.0, g)), 1)
            self._note(step, f"modify_cgm_{mode}", e, f"{float(env.payload['glucose_mgdl']):.0f}->{g:.0f}")
            return [self._sign_as(self._mark(e, "modified"), env.src) if p.get("resign", False) else self._mark(e, "modified")]

        if s.id == "RF-06" and env.type == CMD:
            e = copy.deepcopy(env)
            e.payload["units"] = round(float(e.payload["units"]) * float(p.get("factor", 5.0)) + float(p.get("add_u", 0.0)), 4)
            self._note(step, "modify_cmd", e, f"{env.payload['units']}->{e.payload['units']}")
            return [self._mark(e, "modified")]

        if s.id == "RF-07":
            if env.type in (CGM, CMD, ACK):
                if self.rng.random() < float(p.get("loss", 0.3)):
                    self._note(step, "drop", env)
                    return []
                d = int(p.get("delay_steps", 0))
                if d > 0:
                    self.delayed.append((step + d, self._mark(copy.deepcopy(env), "delayed")))
                    self._note(step, "delay", env, f"{d} steps")
                    return []
            return [env]

        if s.id == "RF-09" and env.type in (CGM, ACK, TRUTH) and p.get("jam", "cgm") in (env.type.lower(), "all"):
            self._note(step, "jam_drop", env)
            return []

        if s.id in ("COORD-01",):
            if env.type == CGM:
                e = copy.deepcopy(env)
                e.payload["glucose_mgdl"] = round(float(e.payload["glucose_mgdl"]) + float(p.get("bias", 35.0)), 1)
                self._note(step, "modify_cgm_bias", e)
                return [self._mark(e, "modified")]
            if env.type == CMD:
                e = copy.deepcopy(env)
                e.payload["units"] = round(float(e.payload["units"]) * float(p.get("factor", 4.0)), 4)
                self._note(step, "modify_cmd", e)
                return [self._mark(e, "modified")]
            return [env]

        if s.id in ("COORD-03", "COORD-04"):
            # Coherent digital compromise: attacker holds CGM + gateway keys (precondition),
            # keeps the CGM stream plausible (masks the effect of over-delivery) and, in
            # COORD-04, also forges TRUTH so that every digital witness agrees.
            if env.type == CGM:
                e = copy.deepcopy(env)
                e.payload["glucose_mgdl"] = round(float(e.payload["glucose_mgdl"]) + float(p.get("mask_bias", 25.0)), 1)
                e = self._sign_as(self._mark(e, "masked"), env.src)
                self._note(step, "mask_cgm", e)
                return [e]
            if env.type == ACK and s.id == "COORD-04" and str(env.payload.get("cmd_id", "")).startswith("cred-"):
                self._note(step, "suppress_own_ack", env)
                return []
            if env.type == TRUTH and s.id == "COORD-04":
                e = copy.deepcopy(env)
                e.payload["delta_g"] = round(self.last_authorised_u * float(p.get("grams_per_unit", 0.1005)), 4)
                e.payload["cutoff"] = False
                e = self._sign_as(self._mark(e, "forged_truth"), env.src)
                self._note(step, "forge_truth", e)
                return [e]
            return [env]

        return [env]

    def inject(self, step: int, now: float, gateway_id: str, pump_id: str, cgm_id: str, truth_id: str) -> list[Envelope]:
        """Out-of-band injections (spoofing, injection, pairing, config, credentialed commands)."""
        out: list[Envelope] = []
        # release delayed envelopes
        ready = [e for (t, e) in self.delayed if t <= step]
        self.delayed = [(t, e) for (t, e) in self.delayed if t > step]
        out.extend(ready)
        s, p = self.spec, self.spec.params
        if not s.active(step):
            return out
        self.injected_seq += 1

        if s.id == "RF-03":
            base = float(self.captured_cgm[-1].payload["glucose_mgdl"]) if self.captured_cgm else 120.0
            e = Envelope(cgm_id, gateway_id, CGM, self.injected_seq, now, {"glucose_mgdl": round(base + float(p.get("bias", 45.0)), 1), "trend": 0.0, "status": "ok"})
            out.append(self._sign_as(self._mark(e, "spoofed"), cgm_id))
            self._note(step, "spoof_cgm", e)

        elif s.id == "RF-04":
            seq = (self.captured_cmd[-1].seq + 1) if self.captured_cmd else self.injected_seq
            e = Envelope(gateway_id, pump_id, CMD, seq, now, {"cmd_id": f"atk-{step}", "units": float(p.get("units", 1.0)), "mode": "bolus"})
            out.append(self._sign_as(self._mark(e, "injected"), gateway_id))
            self._note(step, "inject_cmd", e)

        elif s.id == "RF-08":
            e = Envelope("rogue-peer-7", gateway_id, ASSOC, self.injected_seq, now, {"request": "pair", "caps": ["CGM"]})
            out.append(self._mark(e, "rogue_assoc"))
            self._note(step, "assoc_request", e)

        elif s.id in ("RF-10", "COORD-02", "COORD-03", "COORD-04"):
            # Credentialed malicious controller: valid gateway key, talks straight to the pump.
            # It continues the captured sequence (+1) so the pump accepts it; the legitimate
            # gateway's next command then collides - an unavoidable side effect of two senders
            # sharing one identity, which the protocol twin sees as P04/P11.
            if (step - s.start_step) % int(p.get("every_steps", 1)) == 0:
                seq = (self.captured_cmd[-1].seq + 1) if self.captured_cmd else self.injected_seq
                e = Envelope(gateway_id, pump_id, CMD, seq, now, {"cmd_id": f"cred-{step}", "units": float(p.get("units", 0.6)), "mode": "bolus"})
                out.append(self._sign_as(self._mark(e, "credentialed"), gateway_id))
                self._note(step, "credentialed_cmd", e)
            if s.id == "COORD-02" and self.captured_cgm:
                lag = int(p.get("lag_steps", 36))
                if len(self.captured_cgm) > lag:
                    old = copy.deepcopy(self.captured_cgm[-lag - 1])
                    out.append(self._mark(old, "replayed"))

        elif s.id == "INT-01":
            e = Envelope("updater", gateway_id, CONFIG, self.injected_seq, now, {"version": int(p.get("version", 0)), "kernel_max_command_u": 5.0, "hash": "deadbeef"})
            out.append(self._sign_as(self._mark(e, "rogue_config"), "updater"))
            self._note(step, "config_push", e)
        return out


# ------------------------------------------------------------------ catalogue
def catalogue(start: int, duration: int, keys: dict[str, bytes]) -> dict[str, AttackSpec]:
    """Standard scenario catalogue. Keys are granted only where the precondition says so."""
    end = start + duration
    gw, cgm, truth = keys.get("gateway", b""), keys.get("cgm", b""), keys.get("truth", b"")
    cat = {
        "RF-01": AttackSpec("RF-01", "Passive eavesdropping", "cgm", start, end, {}, "attacker receiver in range", "none", "n/a (confidentiality assessment)"),
        "RF-02": AttackSpec("RF-02", "CGM frame replay", "cgm", start, end, {"lag_steps": 24}, "valid frames previously captured", "captured traffic", "prevention (nonce/sequence/freshness)"),
        "RF-03": AttackSpec("RF-03", "Spoofed CGM sender", "cgm", start, end, {"bias": 45.0}, "attacker radio in range, no key", "public protocol", "prevention (identity)"),
        "RF-04": AttackSpec("RF-04", "Command injection", "cmd", start, end, {"units": 1.0}, "attacker radio in range, no key", "public protocol", "prevention (command authentication)"),
        "RF-05": AttackSpec("RF-05", "MITM CGM modification (bias)", "cgm", start, end, {"mode": "bias", "magnitude": 40.0}, "relay position on the link", "public protocol", "prevention (integrity) / detection (physiology) in legacy"),
        "RF-05b": AttackSpec("RF-05b", "MITM CGM modification (large bias +80)", "cgm", start, end, {"mode": "bias", "magnitude": 80.0}, "relay position on the link", "public protocol", "prevention / detection (physiology)"),
        "RF-05r": AttackSpec("RF-05r", "MITM CGM modification (slow ramp)", "cgm", start, end, {"mode": "ramp", "slope": 1.0}, "relay position on the link", "public protocol", "prevention / detection"),
        "RF-05f": AttackSpec("RF-05f", "MITM CGM freeze", "cgm", start, end, {"mode": "freeze", "value": 130.0}, "relay position on the link", "public protocol", "prevention / detection (plausibility)"),
        "RF-06": AttackSpec("RF-06", "MITM command multiplication", "cmd", start, end, {"factor": 5.0}, "relay position on the link", "public protocol", "prevention (integrity) / detection (delivery twin) in legacy"),
        "RF-07": AttackSpec("RF-07", "Delay, loss and reordering", "multi", start, end, {"loss": 0.4, "delay_steps": 2}, "relay or channel emulator", "none", "safe degradation (freshness/state machine)"),
        "RF-08": AttackSpec("RF-08", "Rogue association request", "assoc", start, end, {}, "attacker radio in range", "pairing protocol", "prevention (commissioning window)"),
        "RF-09": AttackSpec("RF-09", "Jamming / availability loss", "cgm", start, end, {"jam": "cgm"}, "isolated RF enclosure", "none", "mitigation (watchdog, safe degradation)"),
        "RF-10": AttackSpec("RF-10", "Credentialed malicious controller", "cmd", start, end, {"units": 0.6, "every_steps": 2}, "attacker holds a valid gateway key", "full protocol + key", "detection (delivery twin) + mitigation (cut-off)", {"gateway": gw}),
        "ACT-01": AttackSpec("ACT-01", "Firmware over-delivery (2x, acks commanded)", "actuator", start, end, {"factor": 2.0}, "compromised therapy endpoint", "firmware", "detection (delivery twin) + mitigation (cut-off)"),
        "ACT-02": AttackSpec("ACT-02", "Under-delivery / occlusion", "actuator", start, end, {"mode": "occlusion"}, "fault or compromised endpoint", "firmware", "detection (delivery twin)"),
        "ACT-03": AttackSpec("ACT-03", "Stuck-on motor", "actuator", start, end, {"rate_u_per_step": 0.25}, "fault or compromised endpoint", "firmware", "detection (unauthorised flow) + mitigation (cut-off)"),
        "ACT-04": AttackSpec("ACT-04", "False acknowledgement (no delivery)", "actuator", start, end, {}, "compromised therapy endpoint", "firmware", "detection (delivery twin)"),
        "INT-01": AttackSpec("INT-01", "Unsigned / stale configuration push", "config", start, end, {"version": 0}, "local software attacker", "config format", "prevention (signed release policy)"),
        "INT-02": AttackSpec("INT-02", "Audit-log tamper", "log", start, end, {}, "local storage attacker", "log format", "detection (hash chain)"),
        "COORD-01": AttackSpec("COORD-01", "CGM bias + command multiplication", "multi", start, end, {"bias": 35.0, "factor": 4.0}, "relay position", "public protocol", "prevention in protected; detection (physiology + delivery) in legacy"),
        "COORD-02": AttackSpec("COORD-02", "Replayed plausible CGM + credentialed unlogged delivery", "multi", start, end, {"units": 0.6, "every_steps": 2, "lag_steps": 36}, "captured traffic + gateway key", "protocol + key", "detection (delivery twin) + mitigation (cut-off)", {"gateway": gw}),
        "COORD-03": AttackSpec("COORD-03", "Coherent digital compromise (CGM key + gateway key + firmware over-delivery)", "multi", start, end, {"units": 0.5, "every_steps": 2, "mask_bias": 25.0, "factor": 2.0}, "CGM key + gateway key + endpoint firmware", "everything digital except truth node", "detection only by physical truth + mitigation (cut-off)", {"gateway": gw, "cgm": cgm}),
        "COORD-04": AttackSpec("COORD-04", "Undetectable set: COORD-03 + forged truth node", "multi", start, end, {"units": 0.5, "every_steps": 2, "mask_bias": 25.0, "factor": 2.0, "grams_per_unit": 0.1005}, "all keys incl. truth node", "everything", "undetectable (declared)", {"gateway": gw, "cgm": cgm, "truth": truth}),
    }
    return cat
