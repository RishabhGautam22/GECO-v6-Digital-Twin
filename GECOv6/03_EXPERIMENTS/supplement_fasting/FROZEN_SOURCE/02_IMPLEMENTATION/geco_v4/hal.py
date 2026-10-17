"""Hardware abstraction layer.

The gateway (GECO runtime) never talks to hardware directly. It talks to three
device interfaces:

  CGMSource      - yields the next sensor sample (dataset replay or virtual patient)
  PumpDevice     - executes an authorised command and returns what the pump *claims*
  TruthDevice    - returns the independently measured mass delta and cut-off state,
                   and can be asked to trip the cut-off

Virtual implementations model a stepper syringe pump and a 0.01 g balance with
realistic imperfections (step quantisation, calibration error, dribble,
evaporation drift, noise, settle filtering, relay latency). Hardware adapters
(serial/UDP to ESP32 nodes) implement the same interfaces; see hal_hw.py.

Attack hooks on the virtual devices model *actuator-side* compromises that a
network attacker cannot create (firmware over-delivery, stuck-on, false ack,
occlusion). Network-side attacks live in attacks.py and act on the message
stream, not on the devices.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np


class PumpDevice(Protocol):
    def execute(self, cmd_id: str, units: float, now_s: float) -> dict: ...
    def tick(self, now_s: float, dt_s: float) -> None: ...


class TruthDevice(Protocol):
    def read(self, now_s: float) -> dict: ...
    def set_budget(self, units: float, now_s: float) -> None: ...
    def trip(self, now_s: float, reason: str) -> None: ...
    def is_tripped(self) -> bool: ...


@dataclass
class PumpFault:
    """Actuator-side compromise/fault model applied inside the pump device."""

    kind: str = "none"        # none | over | under | stuck_on | false_ack | occlusion
    factor: float = 1.0       # over/under multiplier
    stuck_rate_u_per_step: float = 0.2


@dataclass
class VirtualSyringePump:
    """Stepper-driven syringe pump moving saline into the collection vessel.

    All quantities in research units (U) and grams. 1 U = grams_per_unit at the
    declared scale factor.
    """

    grams_per_unit: float = 0.1005
    steps_per_unit: float = 200.0         # microsteps per research unit (bench calibration)
    calibration_error: float = 0.015      # fractional systematic error (syringe bore, lead screw)
    dribble_g: float = 0.0015             # post-stop dribble per delivery
    max_units_per_step: float = 20.0      # mechanical limit per bench step (larger boluses are queued on hardware)
    fault: PumpFault = field(default_factory=PumpFault)
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(0))
    enabled: bool = True                  # motor power (controlled by the truth node relay)
    total_steps: int = 0
    dispensed_g: float = 0.0              # true mass moved into the vessel (unobservable to the pump)
    last_executed_u: float = 0.0
    pending_dispense_g: float = 0.0

    def execute(self, cmd_id: str, units: float, now_s: float) -> dict:
        """Execute an authorised command. Returns the pump's own claim (the ACK content)."""
        units = max(0.0, min(units, self.max_units_per_step))
        claimed = units
        physical = units
        f = self.fault
        if f.kind == "over":
            physical = units * f.factor
        elif f.kind == "under":
            physical = units * f.factor
        elif f.kind == "false_ack":
            physical = 0.0
        elif f.kind == "occlusion":
            physical = 0.0     # motor steps but nothing flows; pressure rises
        if not self.enabled:
            physical = 0.0
        steps = int(round(physical * self.steps_per_unit))
        self.total_steps += steps
        mass = steps / self.steps_per_unit * self.grams_per_unit * (1.0 + self.calibration_error)
        if f.kind == "occlusion":
            mass = 0.0
        if mass > 0:
            mass += self.rng.normal(0.0, 0.0008) + self.dribble_g
        self.pending_dispense_g += max(0.0, mass)
        self.last_executed_u = units
        return {"cmd_id": cmd_id, "executed_units": claimed, "steps": int(round(claimed * self.steps_per_unit)), "reservoir_u": 300.0 - self.total_steps / self.steps_per_unit}

    def tick(self, now_s: float, dt_s: float) -> None:
        """Advance the physical pump between commands (stuck-on runs regardless of commands)."""
        if self.fault.kind == "stuck_on" and self.enabled:
            mass = self.fault.stuck_rate_u_per_step * self.grams_per_unit * (1.0 + self.calibration_error)
            self.total_steps += int(round(self.fault.stuck_rate_u_per_step * self.steps_per_unit))
            self.pending_dispense_g += mass
        # The vessel receives what was dispensed during this tick.
        self.dispensed_g += self.pending_dispense_g
        self.pending_dispense_g = 0.0


@dataclass
class VirtualBalanceTruthNode:
    """Independent truth node: 0.01 g balance + de-energise-to-safe relay + local budget rule.

    The node has no access to the pump firmware or the gateway's software state.
    It knows only (a) the mass on the balance and (b) the signed volume budget the
    gateway last authorised. It trips the relay when the measured mass exceeds the
    budget by more than the margin, or when explicitly asked.
    """

    pump: VirtualSyringePump
    resolution_g: float = 0.01
    noise_g: float = 0.003
    evaporation_g_per_s: float = 2.0e-6
    relay_latency_s: float = 0.02
    budget_margin_g: float = 0.03
    rng: np.random.Generator = field(default_factory=lambda: np.random.default_rng(1))
    tare_g: float = 0.0
    last_reading_g: float = 0.0
    budget_g: float = -1.0            # <0 = budget rule disabled until the gateway sets one
    budget_start_mass_g: float = 0.0
    rolling_budgets: list = field(default_factory=list)   # last 12 (start_mass, budget) pairs (1 h)
    rolling_margin_g: float = 0.05
    compromised: bool = False          # COORD-04: node firmware compromised -> local rule disabled
    tripped: bool = False
    trip_reason: str = ""
    trip_time_s: float | None = None
    trip_latency_s: float | None = None
    _drift_g: float = 0.0

    def _true_mass(self) -> float:
        return self.pump.dispensed_g + self._drift_g

    def read(self, now_s: float) -> dict:
        self._drift_g -= self.evaporation_g_per_s * 5.0
        # settle filter: median of five noisy samples
        samples = [self._true_mass() + self.rng.normal(0.0, self.noise_g) for _ in range(5)]
        raw = float(np.median(samples))
        reading = round(raw / self.resolution_g) * self.resolution_g
        delta = reading - self.last_reading_g
        self.last_reading_g = reading
        # Local budget rules (independent of the gateway software): per-step and rolling 1 h
        if not self.tripped and self.budget_g >= 0.0 and not self.compromised:
            consumed = reading - self.budget_start_mass_g
            if consumed > self.budget_g + self.budget_margin_g:
                self._do_trip(now_s, f"local per-step budget exceeded by {consumed - self.budget_g:.3f} g")
            elif self.rolling_budgets:
                consumed_h = reading - self.rolling_budgets[0][0]
                allowed_h = sum(b for _, b in self.rolling_budgets)
                if consumed_h > allowed_h + self.rolling_margin_g:
                    self._do_trip(now_s, f"local rolling budget exceeded by {consumed_h - allowed_h:.3f} g")
        return {"mass_g": reading, "delta_g": delta, "cutoff": self.tripped, "trip_reason": self.trip_reason, "budget_g": self.budget_g}

    def set_budget(self, units: float, now_s: float) -> None:
        self.budget_g = max(0.0, units) * self.pump.grams_per_unit * 1.05 + 0.0
        self.budget_start_mass_g = self.last_reading_g
        if len(self.rolling_budgets) >= 12:
            self.rolling_budgets.pop(0)
        self.rolling_budgets.append((self.last_reading_g, self.budget_g))

    def trip(self, now_s: float, reason: str) -> None:
        if not self.tripped:
            self._do_trip(now_s, reason)

    def _do_trip(self, now_s: float, reason: str) -> None:
        self.tripped = True
        self.trip_reason = reason
        self.trip_time_s = now_s
        self.trip_latency_s = self.relay_latency_s
        self.pump.enabled = False
        # motor de-energised: anything still pending is lost except dribble already in the line
        self.pump.pending_dispense_g = min(self.pump.pending_dispense_g, self.pump.dribble_g)

    def reset(self, operator: str) -> None:
        """Return to test mode requires a named human (recorded by the caller)."""
        self.tripped = False
        self.trip_reason = ""
        self.pump.enabled = True

    def is_tripped(self) -> bool:
        return self.tripped
