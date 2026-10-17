"""Bench orchestration: nodes, channel, attacker, gateway runtime and event capture.

One bench *step* is one physiological sample (5 min). In virtual mode the step is
computed instantly; on hardware the same code runs with a time-compression factor
(e.g. 5 min of physiology = 15 s of bench time) and real devices behind the HAL.

Trust domains (never collapsed):
  cgm-01    CGM endpoint (dataset replay or virtual patient)
  gw-01     gateway running GECO (protocol twin, physiology twin, fusion, kernel)
  pump-01   therapy endpoint driving the syringe pump
  truth-01  independent balance + de-energise-to-safe relay + local budget rule
  attacker  MITM on the channel; holds only the keys its precondition grants
"""
from __future__ import annotations

import json
import secrets
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

from .attacks import BENIGN, Attacker, AttackSpec
from .audit import HashChainLog
from .controller import ResearchController
from .delivery import DeliveryCalibration, DeliveryTwin
from .detectors import Evidence, TwoSidedCUSUM, integrity_evidence, plausibility_evidence, provenance_evidence
from .fusion import Assessment, DependencyAwareFusion, Severity
from .hal import PumpFault, VirtualBalanceTruthNode, VirtualSyringePump
from .kernel import KernelContext, SafetyKernel
from .physiology import GlucoseModel, PhysiologyTwin, TwinParams, ForecastPolicy
from .wire import ACK, ASSOC, BUDGET, CGM, CMD, CONFIG, TRUTH, Envelope, Signer
from .numerics import finite_number, positive_number, payload_numeric_issue

GW, CGM_ID, PUMP_ID, TRUTH_ID = "gw-01", "cgm-01", "pump-01", "truth-01"


@dataclass
class BenchConfig:
    profile: str = "protected"                 # legacy | protected
    dt_min: float = 5.0
    grams_per_unit: float = 0.1005
    mode: str = "replay"                       # replay | closed_loop
    ablation: str = "geco_full"                # geco_full | geco_no_delivery | kernel_only | no_geco
    cusum_drift: float = 0.5
    cusum_threshold: float = 8.0
    r_std: float = 9.0
    max_age_s: float = 20.0
    max_cgm_age_s: float = 12 * 60
    max_user_bolus_u: float = 15.0
    min_reliable_groups: int = 2
    ar1_rho: float = 0.0
    sigma6_mgdl: float = 25.0
    cusum6_threshold: float = 8.0
    innovation_inflation: float = 1.0
    forecast_policy: dict = field(default_factory=dict)
    innovation_cusum_start_step: int = 0       # participant-calibrated runtime uses 36
    forecast_cusum_start_step: int = 0         # due targets for origins >=36 start at42
    meal_announcement_rate: float = 0.6        # closed loop: fraction of meals the gateway is told about
    seed: int = 0
    time_compression: float = 20.0             # bench seconds per physiological minute^-1 (documentation only in virtual mode)

    def __post_init__(self):
        for name in ("dt_min", "grams_per_unit", "cusum_threshold", "r_std", "max_age_s",
                     "max_cgm_age_s", "sigma6_mgdl", "cusum6_threshold", "innovation_inflation", "time_compression"):
            positive_number(getattr(self, name), name)
        finite_number(self.cusum_drift, "cusum_drift", minimum=0)
        finite_number(self.max_user_bolus_u, "max_user_bolus_u", minimum=0)
        finite_number(self.ar1_rho, "ar1_rho", minimum=0)
        if self.ar1_rho >= 1:
            raise ValueError("ar1_rho must be less than 1")
        finite_number(self.meal_announcement_rate, "meal_announcement_rate", minimum=0, maximum=1)
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for name in ("innovation_cusum_start_step", "forecast_cusum_start_step"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if isinstance(self.min_reliable_groups, bool) or not isinstance(self.min_reliable_groups, int) or not 1 <= self.min_reliable_groups <= 4:
            raise ValueError("min_reliable_groups must be an integer from 1 through 4")
        if self.profile not in ("legacy", "protected") or self.mode not in ("replay", "closed_loop"):
            raise ValueError("unrecognized profile or mode")
        if self.ablation not in ("geco_full", "geco_no_delivery", "kernel_only", "no_geco"):
            raise ValueError("unrecognized ablation")
        self.forecast_policy = asdict(ForecastPolicy(**self.forecast_policy))


@dataclass
class StepRecord:
    step: int
    t_min: float
    true_glucose: float | None
    cgm_sent: float | None
    cgm_accepted: float | None
    cgm_verdict: str
    z: float | None
    cusum: float
    cusum6: float
    phys_score: float
    prov_score: float
    act_score: float
    int_score: float
    probability: float
    severity: str
    kernel_severity: str
    abstained: bool
    requested_u: float
    user_bolus_u: float
    allowed_u: float
    kernel_reasons: str
    pump_claimed_u: float
    pump_executed_physical_u: float
    delta_mass_g: float
    measured_u: float
    delivery_label: str
    cutoff: bool
    attack_active: bool
    attack_actions: str
    rejected_attack_msgs: int
    accepted_attack_msgs: int
    pump_enabled: bool
    # v5: distinct causal domains. Legacy measured fields remain for compatibility.
    pump_emitted_mass_g: float
    local_measured_mass_g: float
    local_measured_delta_g: float
    network_reported_mass_g: float | None
    network_reported_delta_g: float | None
    network_truth_accepted: bool
    virtual_plant_input_u: float


class GatewayRuntime:
    """GECO v4 runtime as deployed on the gateway trust domain."""

    def __init__(self, cfg: BenchConfig, keys: dict[str, bytes], twin_params: TwinParams, delivery_cal: DeliveryCalibration):
        from .protocol import ProtocolTwin

        self.cfg = cfg
        self.keys = keys
        enabled = cfg.ablation
        self.use_protocol = enabled in ("geco_full", "geco_no_delivery")
        self.use_delivery = enabled == "geco_full"
        self.use_kernel = enabled != "no_geco"
        self.protocol = ProtocolTwin(
            profile=cfg.profile if self.use_protocol else "legacy",
            peers={
                CGM_ID: {"key": keys.get("cgm"), "allowed_types": (CGM,), "min_interval_s": 0.0},
                PUMP_ID: {"key": keys.get("pump"), "allowed_types": (ACK,)},
                TRUTH_ID: {"key": keys.get("truth"), "allowed_types": (TRUTH,)},
                "updater": {"key": keys.get("updater"), "allowed_types": (CONFIG,)},
            },
            max_age_s=cfg.max_age_s,
            ack_window_s=cfg.dt_min * 60 * 1.5,
        )
        self.twin = PhysiologyTwin(twin_params, r_std=cfg.r_std, forecast_policy=cfg.forecast_policy)
        self.twin.configure_calibration(asdict(cfg))
        self.cusum = TwoSidedCUSUM(drift=cfg.cusum_drift, threshold=cfg.cusum_threshold)
        self.cusum6 = TwoSidedCUSUM(drift=cfg.cusum_drift, threshold=cfg.cusum6_threshold)
        self.delivery = DeliveryTwin(delivery_cal)
        self.fusion = DependencyAwareFusion(min_reliable_groups=cfg.min_reliable_groups)
        self.kernel = SafetyKernel(max_cgm_age_s=cfg.max_cgm_age_s)
        self.controller = ResearchController()
        self.audit = HashChainLog(checkpoint_key=keys.get("truth"))
        self.signer = Signer(GW, keys.get("gateway"), cfg.profile)
        self.last_cgm: float | None = None
        self.last_cgm_ts: float = -1e9
        self.prev_cgm: float | None = None
        self.last_pump_ts: float = 0.0
        self.last_actuation: Evidence = Evidence("delivery_reconciliation", "actuation", 0.0, reliable=False, detail="no measurement yet")
        self.config_ok = True
        self.delivered_window: list[float] = []
        self.reactive_window: list[float] = []
        self.pending_cmd: dict[str, float] = {}
        self.last_ack_units: float | None = None

    # ------------------------------------------------------------ ingress
    def ingest(self, env: Envelope, now: float) -> tuple[bool, str]:
        """Protocol-twin verification of an inbound envelope. Returns (accepted, detail)."""
        issue = payload_numeric_issue(env.type, env.payload)
        if issue:
            return False, "invalid numeric payload: " + issue
        if not self.use_protocol:
            # Ablations without the protocol twin accept everything (legacy behaviour).
            verdict_ok, detail = True, "unverified"
            if env.type == CGM:
                self._accept_cgm(env, now)
            elif env.type == ACK:
                self.last_pump_ts = now
                self.last_ack_units = float(env.payload.get("executed_units", 0.0))
            return verdict_ok, detail
        v = self.protocol.verify(env, now)
        if v.accepted:
            if env.type == CGM:
                self._accept_cgm(env, now)
            elif env.type == ACK:
                self.last_pump_ts = now
                self.last_ack_units = float(env.payload.get("executed_units", 0.0))
            elif env.type == CONFIG:
                self.config_ok = True  # accepted only if P14 passed
        else:
            if env.type == CONFIG:
                self.config_ok = False if "P14" not in v.violations else self.config_ok
        return v.accepted, v.detail

    def _accept_cgm(self, env: Envelope, now: float) -> None:
        self.prev_cgm = self.last_cgm
        self.last_cgm = float(env.payload["glucose_mgdl"])
        self.last_cgm_ts = now

    # ------------------------------------------------------------ decision
    def decide(self, now: float, step: int, automated_request: float | None, user_bolus_u: float, insulin_logged_u: float, carbs_g: float) -> tuple[Assessment, Any, float, float, TwoSidedCUSUM, dict[str, Any]]:
        cgm_age = now - self.last_cgm_ts
        cgm_value = self.last_cgm if cgm_age <= self.cfg.dt_min * 60 * 0.5 + 1e-6 else None
        out = self.twin.update(cgm_value, insulin_logged_u, carbs_g)
        z = out.standardized_innovation if out.innovation_valid else None
        # Match participant calibration's eligible innovation/forecast targets.
        # Continue causal filtering during startup without accumulating evidence.
        z_for_cusum = z if step >= self.cfg.innovation_cusum_start_step else None
        z6_for_cusum = self.twin.last_forecast_residual_z if step >= self.cfg.forecast_cusum_start_step else None
        ev6 = self.cusum6.update(z6_for_cusum)
        ev6 = Evidence("physiology_forecast_cusum", "physiology", ev6.score, ev6.reliable, ev6.detail)
        ev_phys = [self.cusum.update(z_for_cusum), ev6, plausibility_evidence(out.quality)]
        self.protocol.expire_commands(now)
        pscore, pdetail = self.protocol.evidence_score(now, window_s=self.cfg.dt_min * 60 * 6)
        link_alive = cgm_age <= self.cfg.max_cgm_age_s
        if not link_alive:
            pscore = max(pscore, 0.5)   # a dead link is itself evidence of a fault or jamming
        ev_prov = provenance_evidence(pscore, pdetail, link_alive) if self.use_protocol else Evidence("protocol_state", "provenance", 0.0, reliable=False, detail="disabled")
        ev_act = self.last_actuation if self.use_delivery else Evidence("delivery_reconciliation", "actuation", 0.0, reliable=False, detail="disabled")
        chain_ok, _ = self.audit.verify()
        ev_int = integrity_evidence(self.config_ok, chain_ok)
        assessment = self.fusion.assess(ev_phys + [ev_prov, ev_act, ev_int])
        forecast = self.twin.forecast(6) if cgm_value is not None else None
        slope = 0.0 if (self.last_cgm is None or self.prev_cgm is None) else (self.last_cgm - self.prev_cgm) / self.cfg.dt_min
        requested = automated_request if automated_request is not None else self.controller.request(cgm_value, forecast)
        ctx = KernelContext(
            now_s=now,
            glucose_mgdl=cgm_value,
            glucose_slope_mgdl_min=slope,
            cgm_age_s=cgm_age,
            pump_age_s=now - self.last_pump_ts if step > 2 else 0.0,
            command_authenticated=True,
            predicted_glucose_30m=forecast,
            delivered_u_3h=sum(self.delivered_window),
            reactive_u_3h=sum(self.reactive_window),
            assessment=assessment,
            actuation_score=ev_act.score if ev_act.reliable else 0.0,
        )
        if self.use_kernel:
            decision = self.kernel.authorize(requested, ctx)
            allowed = decision.allowed_u
            reasons = decision.reasons
            cutoff = decision.cutoff_requested
            sev = decision.severity
        else:
            allowed, reasons, cutoff, sev = requested, ("no kernel",), False, assessment.severity
        # User-initiated bolus: bounded separately; blocked only by hard stops.
        bolus_allowed = 0.0
        if user_bolus_u > 0:
            hard_block = any(r.startswith(("K01", "K02", "K12", "K13")) for r in reasons) if self.use_kernel else False
            bolus_allowed = 0.0 if hard_block else min(user_bolus_u, self.cfg.max_user_bolus_u)
        total_allowed = allowed + bolus_allowed
        self.reactive_window = (self.reactive_window + [min(requested, allowed) if cgm_value is not None else 0.0])[-36:]
        self.delivered_window = (self.delivered_window + [allowed])[-36:]
        info = {"z": z, "quality": out.quality, "phys": max(e.score for e in ev_phys), "prov": ev_prov.score if ev_prov.reliable else 0.0, "act": ev_act.score if ev_act.reliable else 0.0, "int": ev_int.score, "reasons": ";".join(reasons), "cutoff": cutoff, "severity": assessment.severity.value, "kernel_severity": sev.value, "forecast": forecast, "cgm_value": cgm_value}
        return assessment, ctx, requested, total_allowed, self.cusum, info

    def issue_command(self, now: float, units: float, step: int) -> tuple[Envelope, Envelope]:
        cmd_id = f"c{step:05d}-{secrets.token_hex(2)}"
        cmd = self.signer.make(PUMP_ID, CMD, now, {"cmd_id": cmd_id, "units": round(units, 4), "mode": "auto"})
        self.protocol.register_command(cmd_id, round(units, 4), now)
        self.pending_cmd = {cmd_id: units}
        budget = self.signer.make(TRUTH_ID, BUDGET, now, {"units": round(units, 4), "window_s": self.cfg.dt_min * 60})
        return cmd, budget

    def reconcile(self, authorised_u: float, delta_mass_g: float | None, now: float) -> tuple[Evidence, Any]:
        if delta_mass_g is None:
            ev = Evidence("delivery_reconciliation", "actuation", 0.0, reliable=False,
                          detail="no accepted numerical truth measurement")
            self.last_actuation = ev
            self.last_ack_units = None
            return ev, None
        ev, obs = self.delivery.reconcile(authorised_u, self.last_ack_units, delta_mass_g)
        self.last_actuation = ev if self.use_delivery else self.last_actuation
        self.last_ack_units = None
        return ev, obs


class PumpEndpoint:
    """Therapy endpoint: verifies commands under its own protocol twin, drives the pump device."""

    def __init__(self, cfg: BenchConfig, keys: dict[str, bytes], device: VirtualSyringePump):
        from .protocol import ProtocolTwin

        self.cfg = cfg
        self.device = device
        self.protocol = ProtocolTwin(cfg.profile, {GW: {"key": keys.get("gateway"), "allowed_types": (CMD,)}}, max_age_s=cfg.max_age_s)
        self.signer = Signer(PUMP_ID, keys.get("pump"), cfg.profile)
        self.executed_physical_u_step = 0.0
        self.claimed_u_step = 0.0

    def receive(self, env: Envelope, now: float) -> list[Envelope]:
        v = self.protocol.verify(env, now)
        if not v.accepted:
            return []
        claim = self.device.execute(str(env.payload["cmd_id"]), float(env.payload["units"]), now)
        self.claimed_u_step += float(claim["executed_units"])
        return [self.signer.make(GW, ACK, now, claim)]


def _make_keys(rng: np.random.Generator) -> dict[str, bytes]:
    return {name: bytes(rng.integers(0, 256, 32, dtype=np.uint8)) for name in ("cgm", "gateway", "pump", "truth", "updater")}


@dataclass
class RunResult:
    records: list[StepRecord]
    summary: dict[str, Any]
    attacker_log: list[dict[str, Any]]
    manifest: dict[str, Any]


def run_scenario(
    cfg: BenchConfig,
    attack: AttackSpec | None,
    twin_params: TwinParams,
    delivery_cal: DeliveryCalibration,
    replay: dict[str, np.ndarray] | None = None,
    plant_params: TwinParams | None = None,
    steps: int | None = None,
    attack_start: int = 96,
    attack_duration: int = 48,
    attack_catalogue_id: str | None = None,
) -> RunResult:
    """Run one scenario on the virtual bench.

    replay      : dict with arrays cgm (mg/dL, NaN = missing), insulin (U per step: basal+bolus),
                  bolus (U per step, user-initiated), carbs (g per step). Used in replay mode.
    plant_params: parameters of the *plant* (true virtual patient) in closed-loop mode; the
                  twin uses twin_params (model mismatch is deliberate).
    """
    from .attacks import catalogue

    if steps is not None and (isinstance(steps, bool) or not isinstance(steps, int) or steps < 1):
        raise ValueError("steps must be a positive integer")
    if not np.isclose(cfg.dt_min, twin_params.dt_min):
        raise ValueError("bench and twin sample durations must agree")
    if plant_params is not None and not np.isclose(cfg.dt_min, plant_params.dt_min):
        raise ValueError("bench and plant sample durations must agree")
    if not np.isclose(cfg.grams_per_unit, delivery_cal.grams_per_unit):
        raise ValueError("bench and delivery calibration mass-unit mappings must agree")

    rng = np.random.default_rng(cfg.seed)
    keys = _make_keys(rng)
    if attack is None:
        attack = BENIGN
    if attack_catalogue_id is not None:
        attack = catalogue(attack_start, attack_duration, keys)[attack_catalogue_id]
    elif attack.id != "NONE":
        # rebind keys granted by precondition to this run's keys
        attack.keys = {k: keys[k] for k in attack.keys.keys() if k in keys}
    attacker = Attacker(attack, rng)

    pump_dev = VirtualSyringePump(grams_per_unit=cfg.grams_per_unit, rng=np.random.default_rng(cfg.seed + 11), max_units_per_step=10.0)
    truth_dev = VirtualBalanceTruthNode(pump_dev, rng=np.random.default_rng(cfg.seed + 23))
    gateway = GatewayRuntime(cfg, keys, twin_params, delivery_cal)
    pump = PumpEndpoint(cfg, keys, pump_dev)
    cgm_signer = Signer(CGM_ID, keys["cgm"], cfg.profile)
    truth_signer = Signer(TRUTH_ID, keys["truth"], cfg.profile)
    use_truth = cfg.ablation == "geco_full"
    use_kernel = cfg.ablation != "no_geco"

    if replay is not None:
        required = ("cgm", "insulin", "bolus", "carbs")
        if any(name not in replay for name in required):
            raise ValueError("replay requires cgm, insulin, bolus, and carbs arrays")
        replay = {name: np.asarray(replay[name], dtype=float) for name in required}
        if any(array.ndim != 1 for array in replay.values()) or len({len(a) for a in replay.values()}) != 1:
            raise ValueError("replay arrays must be one-dimensional and have equal length")
        if np.isinf(replay["cgm"]).any():
            raise ValueError("CGM may contain NaN for missing samples, but not infinity")
        for name in ("insulin", "bolus", "carbs"):
            if not np.isfinite(replay[name]).all() or (replay[name] < 0).any():
                raise ValueError(f"replay {name} must contain finite nonnegative values")
        if np.any(replay["bolus"] > replay["insulin"] + 1e-9):
            raise ValueError("replay total insulin cannot be less than its bolus component")
        n = len(replay["cgm"]) if steps is None else min(steps, len(replay["cgm"]))
        plant = None
        x = None
    else:
        n = steps or 288
        plant = GlucoseModel(plant_params or twin_params)
        x = plant.initial_state(130.0 + rng.normal(0, 10), 0.08)
        meal_times = {int(8 * 12 + rng.integers(-6, 6)): 45.0, int(13 * 12 + rng.integers(-6, 6)): 60.0, int(19 * 12 + rng.integers(-6, 6)): 55.0}
    dt_s = cfg.dt_min * 60.0
    records: list[StepRecord] = []
    truth_dev.read(0.0)
    delivered_units_attack = 0.0
    authorised_units_attack = 0.0
    excess_prior_to_cutoff = None
    previous_carbs_announced = 0.0

    for step in range(n):
        emitted_before_g = pump_dev.dispensed_g
        now = step * dt_s
        active = attack.active(step)
        pump_dev.fault = attacker.actuator_fault(step)
        truth_dev.compromised = bool(active and attack.id == "COORD-04")
        pump.claimed_u_step = 0.0
        pump_dev.last_executed_u = 0.0
        rejected_attack, accepted_attack = 0, 0
        actions: list[str] = []

        # ---- 1. patient sample
        if replay is not None:
            true_g = None
            cgm_val = float(replay["cgm"][step]) if np.isfinite(replay["cgm"][step]) else None
            insulin_logged = float(replay["insulin"][step])
            user_bolus = float(replay["bolus"][step])
            carbs = float(replay["carbs"][step])
            automated_request = float(replay["insulin"][step]) - user_bolus
        else:
            true_g = float(x[0])
            cgm_noise = rng.normal(0.0, 6.0)
            cgm_val = float(np.clip(x[4] + cgm_noise, 40.0, 400.0))
            if rng.random() < 0.01:
                cgm_val = None       # benign dropout
            user_bolus = 0.0
            carbs = meal_times.get(step % 288, 0.0) * rng.uniform(0.8, 1.2) if (step % 288) in meal_times else 0.0
            insulin_logged = 0.0     # closed loop: the gateway only knows what it authorised (set below)
            automated_request = None

        # ---- 2. CGM endpoint -> channel -> attacker -> gateway
        inbound: list[Envelope] = []
        if cgm_val is not None:
            env = cgm_signer.make(GW, CGM, now, {"glucose_mgdl": round(cgm_val, 1), "trend": 0.0, "status": "ok"})
            inbound.extend(attacker.intercept(env, step, now))
        inbound.extend(attacker.inject(step, now, GW, PUMP_ID, CGM_ID, TRUTH_ID))
        cgm_accepted_val = None
        verdict_detail = "none"
        for env in inbound:
            if env.dst == GW:
                ok, detail = gateway.ingest(env, now)
                is_attack = "attack" in env.meta
                if is_attack:
                    actions.append(env.meta.get("attack_action", "?"))
                    if ok:
                        accepted_attack += 1
                    else:
                        rejected_attack += 1
                if env.type == CGM:
                    verdict_detail = detail
                    if ok:
                        cgm_accepted_val = float(env.payload["glucose_mgdl"])
            elif env.dst == PUMP_ID:
                # injected command straight to the pump (RF-04 / credentialed)
                acks = pump.receive(env, now)
                if acks:
                    accepted_attack += 1
                    actions.append(env.meta.get("attack_action", "?") + "->executed")
                    for a in acks:
                        for e2 in attacker.intercept(a, step, now):
                            gateway.ingest(e2, now)
                else:
                    rejected_attack += 1
                    actions.append(env.meta.get("attack_action", "?") + "->rejected")

        # ---- 3. gateway decision
        # CGM at k precedes delivery/meal inputs during interval k. The repaired
        # twin API therefore receives logged/authorized inputs from interval k-1.
        insulin_for_twin = (float(replay["insulin"][step - 1]) if step else 0.0) if replay is not None else (records[-1].allowed_u if records else 0.0)
        carbs_announced = carbs if (replay is not None or rng.random() < cfg.meal_announcement_rate) else 0.0
        assessment, ctx, requested, allowed, cusum, info = gateway.decide(now, step, automated_request, user_bolus, insulin_for_twin, previous_carbs_announced)
        previous_carbs_announced = carbs_announced
        if not use_kernel:
            allowed = requested + user_bolus

        # ---- 4. command to pump (through attacker) and budget to truth node
        cmd, budget = gateway.issue_command(now, allowed, step)
        if use_truth:
            truth_dev.set_budget(allowed, now)
        for env in attacker.intercept(cmd, step, now):
            acks = pump.receive(env, now)
            if "attack" in env.meta:
                actions.append(env.meta.get("attack_action", "?") + ("->executed" if acks else "->rejected"))
                accepted_attack += 1 if acks else 0
                rejected_attack += 0 if acks else 1
            for a in acks:
                for e2 in attacker.intercept(a, step, now):
                    gateway.ingest(e2, now)
        if info["cutoff"] and use_truth:
            truth_dev.trip(now, "gateway cut-off request: " + info["reasons"])
            actions.append("gateway_cutoff")

        # ---- 5. physical world advances; truth node reads the balance
        pump_dev.tick(now, dt_s)
        emitted_mass_g = pump_dev.dispensed_g - emitted_before_g
        reading = truth_dev.read(now + dt_s * 0.9)
        truth_env = truth_signer.make(GW, TRUTH, now + dt_s * 0.9, {"mass_g": reading["mass_g"], "delta_g": round(reading["delta_g"], 4), "cutoff": reading["cutoff"], "budget_g": reading["budget_g"]})
        network_mass_g = None
        network_delta_g = None
        network_truth_accepted = False
        delivery_label = "n/a"
        if use_truth:
            for env in attacker.intercept(truth_env, step, now + dt_s * 0.9):
                ok, _ = gateway.ingest(env, now + dt_s * 0.9)
                if ok:
                    network_mass_g = float(env.payload["mass_g"])
                    network_delta_g = float(env.payload["delta_g"])
                    network_truth_accepted = True
            _, delivery_obs = gateway.reconcile(allowed, network_delta_g, now)
            delivery_label = delivery_obs.label if delivery_obs is not None else "missing"
        measured_u = reading["delta_g"] / cfg.grams_per_unit      # signed: balance flicker cancels in sums
        physical_u = emitted_mass_g / cfg.grams_per_unit
        expected_u = delivery_cal.expected_mass(allowed) / cfg.grams_per_unit if allowed > 0 else 0.0
        if active:
            delivered_units_attack += measured_u
            authorised_units_attack += expected_u
            if reading["cutoff"] and excess_prior_to_cutoff is None:
                excess_prior_to_cutoff = delivered_units_attack - authorised_units_attack

        # ---- 6. plant integrates what physically moved (closed loop only)
        if plant is not None:
            x = plant.step(x, physical_u, carbs)

        # ---- 7. audit + record
        gateway.audit.append(now, {"step": step, "allowed": allowed, "sev": info["severity"], "delta_g": round(reading["delta_g"], 4)})
        if attack.id == "INT-02" and active and step == attack.start_step + 2:
            gateway.audit.tamper(max(0, len(gateway.audit.records) - 5), "allowed", 9.9)
            actions.append("log_tamper")
        records.append(
            StepRecord(
                step=step,
                t_min=step * cfg.dt_min,
                true_glucose=true_g,
                cgm_sent=cgm_val,
                cgm_accepted=cgm_accepted_val,
                cgm_verdict=verdict_detail,
                z=info["z"],
                cusum=cusum.statistic if not cusum.last_alarm else cfg.cusum_threshold,
                cusum6=gateway.cusum6.statistic if not gateway.cusum6.last_alarm else cfg.cusum6_threshold,
                phys_score=info["phys"],
                prov_score=info["prov"],
                act_score=info["act"],
                int_score=info["int"],
                probability=assessment.compromise_probability,
                severity=info["severity"],
                kernel_severity=info["kernel_severity"],
                abstained=assessment.abstained,
                requested_u=requested,
                user_bolus_u=user_bolus,
                allowed_u=allowed,
                kernel_reasons=info["reasons"],
                pump_claimed_u=pump.claimed_u_step,
                pump_executed_physical_u=physical_u,
                delta_mass_g=reading["delta_g"],
                measured_u=measured_u,
                delivery_label=delivery_label,
                cutoff=reading["cutoff"],
                attack_active=active,
                attack_actions="|".join(actions),
                rejected_attack_msgs=rejected_attack,
                accepted_attack_msgs=accepted_attack,
                pump_enabled=pump_dev.enabled,
                pump_emitted_mass_g=emitted_mass_g,
                local_measured_mass_g=reading["mass_g"],
                local_measured_delta_g=reading["delta_g"],
                network_reported_mass_g=network_mass_g,
                network_reported_delta_g=network_delta_g,
                network_truth_accepted=network_truth_accepted,
                virtual_plant_input_u=physical_u,
            )
        )

    summary = summarise(records, attack, cfg, gateway, truth_dev, delivered_units_attack, authorised_units_attack, excess_prior_to_cutoff)
    manifest = {
        "implementation": "GECO v5 numerical and causal fork of v4 (compatibility package geco_v4)",
        "plant_input_semantics": "actual pump dispensed_g increment divided by grams_per_unit; independent of balance measurement noise",
        "truth_input_semantics": "network-reported mass and delta are None unless an accepted numerical TRUTH envelope exists",
        "config": asdict(cfg),
        "attack": {"id": attack.id, "name": attack.name, "channel": attack.channel, "start": attack.start_step, "end": attack.end_step, "params": attack.params, "precondition": attack.precondition, "expected_control": attack.expected_control, "keys_granted": sorted(attack.keys.keys())},
        "twin_params": asdict(twin_params),
        "delivery_calibration": asdict(delivery_cal),
        "steps": n,
        "mode": cfg.mode,
    }
    return RunResult(records, summary, attacker.log, manifest)


def summarise(records: list[StepRecord], attack: AttackSpec, cfg: BenchConfig, gateway: GatewayRuntime, truth_dev: VirtualBalanceTruthNode, delivered_attack_u: float, authorised_attack_u: float, excess_prior_to_cutoff: float | None) -> dict[str, Any]:
    active = np.array([r.attack_active for r in records])
    sev = np.array([r.severity for r in records])
    contain = np.isin(sev, ["contain", "safe_mode"])
    cutoff = np.array([r.cutoff for r in records])
    cusum_alarm = np.array([(r.cusum >= cfg.cusum_threshold) or (r.cusum6 >= cfg.cusum6_threshold) for r in records])
    watch = np.isin(sev, ["watch", "contain", "safe_mode"])
    phys_stop = np.array([any(code in r.kernel_reasons for code in ("K05", "K06", "K07")) for r in records])
    n_days = max(len(records) * cfg.dt_min / 1440.0, 1e-9)
    rejected = int(sum(r.rejected_attack_msgs for r in records))
    accepted = int(sum(r.accepted_attack_msgs for r in records))
    first_detect = None
    first_cusum = None
    first_cutoff = None
    if active.any():
        start = int(np.argmax(active))
        idx = np.where(contain & active)[0]
        first_detect = float((idx[0] - start) * cfg.dt_min) if len(idx) else None
        idx2 = np.where(cusum_alarm & active)[0]
        first_cusum = float((idx2[0] - start) * cfg.dt_min) if len(idx2) else None
        idx3 = np.where(cutoff & active)[0]
        first_cutoff = float((idx3[0] - start) * cfg.dt_min) if len(idx3) else None
        idx4 = np.where(watch & active)[0]
        first_watch = float((idx4[0] - start) * cfg.dt_min) if len(idx4) else None
    else:
        first_watch = None
    # False containment: episodes (runs of contain) in the benign period *before* the attack
    # (after an attack the system may legitimately remain contained until a human resets it).
    if active.any():
        pre = np.arange(len(records)) < int(np.argmax(active))
        post = np.arange(len(records)) >= int(np.argmax(active)) + int(active.sum())
    else:
        pre = np.ones(len(records), dtype=bool)
        post = np.zeros(len(records), dtype=bool)
    benign_days = max(float(pre.sum()) * cfg.dt_min / 1440.0, 1e-9)
    fc = contain & pre
    episodes = int(np.sum(fc[1:] & ~fc[:-1]) + (1 if (len(fc) and fc[0]) else 0)) if len(fc) else 0
    false_cutoff = int(np.sum(cutoff & pre))
    residual_contain_after_min = float(np.sum(contain & post) * cfg.dt_min)
    unmet_attack = float(sum(max(0.0, r.requested_u - r.allowed_u) for r in records if r.attack_active and not any(k in r.kernel_reasons for k in ("K05", "K06", "K07"))))
    tg = np.array([r.true_glucose for r in records if r.true_glucose is not None], dtype=float)
    safety = {}
    if len(tg):
        safety = {"tir_70_180": float(np.mean((tg >= 70) & (tg <= 180))), "tbr_70": float(np.mean(tg < 70)), "tbr_54": float(np.mean(tg < 54)), "tar_250": float(np.mean(tg > 250)), "min_glucose": float(tg.min())}
    unmet = float(sum(max(0.0, r.requested_u - r.allowed_u) for r in records if not r.attack_active and not any(k in r.kernel_reasons for k in ("K05", "K06", "K07"))))
    return {
        "attack_id": attack.id,
        "profile": cfg.profile,
        "ablation": cfg.ablation,
        "mode": cfg.mode,
        "steps": len(records),
        "days": round(n_days, 3),
        "attack_msgs_rejected": rejected,
        "attack_msgs_accepted": accepted,
        "prevention_rate": (rejected / (rejected + accepted)) if (rejected + accepted) else None,
        "first_containment_delay_min": first_detect,
        "first_physiology_alarm_delay_min": first_cusum,
        "first_cutoff_delay_min": first_cutoff,
        "first_watch_delay_min": first_watch,
        "physiological_suspend_steps_frac": float(phys_stop.mean()) if len(phys_stop) else 0.0,
        "watch_frac_benign": float((watch & ~active).mean()) if len(watch) else 0.0,
        "detected": first_detect is not None or first_cutoff is not None,
        "false_containment_episodes_per_benign_day": episodes / benign_days,
        "false_cutoffs": false_cutoff,
        "residual_containment_after_attack_min": residual_contain_after_min,
        "unmet_automated_units_during_attack": round(unmet_attack, 3),
        "time_in_contain_or_safe_frac": float(contain.mean()) if len(contain) else 0.0,
        "authorised_u_during_attack": round(authorised_attack_u, 3),
        "delivered_u_during_attack": round(delivered_attack_u, 3),
        "excess_u_during_attack": round(delivered_attack_u - authorised_attack_u, 3),
        "excess_u_before_cutoff": None if excess_prior_to_cutoff is None else round(excess_prior_to_cutoff, 3),
        "cutoff_tripped": bool(truth_dev.tripped),
        "cutoff_reason": truth_dev.trip_reason,
        "cutoff_relay_latency_s": truth_dev.trip_latency_s,
        "unmet_automated_units_benign_security": round(unmet, 3),
        "protocol_counters": dict(gateway.protocol.counters),
        "audit_chain_valid": gateway.audit.verify()[0],
        "true_emitted_u_during_attack": float(sum(r.virtual_plant_input_u for r in records if r.attack_active)),
        "nominal_authorised_u_during_attack": float(sum(r.allowed_u for r in records if r.attack_active)),
        "true_excess_over_nominal_u_during_attack": float(sum(r.virtual_plant_input_u - r.allowed_u for r in records if r.attack_active)),
        **safety,
    }


def records_to_rows(records: list[StepRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in records]
