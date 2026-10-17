"""Coupled Multi-Physics Fault Simulation Engine for GECO v6.1+ Max.

Models first-principles fluidic, electro-thermal, and electromechanical physics
for the insulin infusion pump, microbore tubing, cannula, power subsystem, and
130-part gravimetric metrology testbed:

1. `PipeDebrisAndFluidicsModel`:
   - Microbore tubing ($L = 600$ mm, $r_0 = 0.19$ mm) Hagen-Poiseuille laminar flow
   - Insulin fibril / micro-precipitate debris transport, lodging, and 4th-power
     hydraulic resistance scaling: $R(t) = R_0 / (1 - \\alpha_{\\text{debris}}(t))^4$
   - Compressible air bubble compliance via Boyle's Law:
     $C_{\\text{bubble}}(P) = V_{\\text{air},0} P_{\\text{atm}} / (P_{\\text{atm}} + P_{\\text{line}})^2$
   - Subcutaneous cannula kinking & Luer-lock micro-leakage
   - Inline strain-gauge pressure transducer ($P_{\\text{line}}$ in kPa) & pressure-relief venting

2. `BatteryElectroThermalModel`:
   - Nonlinear Li-Ion OCV curve $V_{\\text{OCV}}(\\text{SOC})$
   - Thevenin equivalent circuit with series resistance $R_{\\text{int}}(\\text{SOC}, T, \\text{fault})$
     and RC polarization branch $V_{\\text{rc}}(t)$
   - Terminal voltage sag $V_{\\text{term}} = V_{\\text{OCV}} - I_{\\text{load}} R_{\\text{int}} - V_{\\text{rc}}$
     during high-current stepper motor + solenoid pulses
   - $< 3.05$ V Brownout Watchdog & $1.5$ F Supercapacitor emergency hold-up rail

3. `ElectromechanicalPumpModel`:
   - Stepper motor (`M03`) pull-out torque vs back-pressure & bearing stiction
   - Lead-screw (`M05`) backlash deadband ($\\delta_{\\text{backlash}}$) & nut (`M06`) wear
   - Optical encoder discrepancy detection (commanded vs actual shaft steps)
   - Fail-safe solenoid pinch valve (`V01`) & CGM membrane biofouling drift
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import math
import numpy as np

GRAMS_PER_UNIT = 0.1005       # 1 U U-100 insulin = 10 uL = 0.01005 g (10x scaled rig = 0.1005 g/U)
UL_PER_UNIT = 10.0            # 1 U U-100 insulin = 10.0 uL


@dataclass
class FluidicState:
    debris_occlusion_ratio: float = 0.0     # alpha_debris in [0, 0.98]
    effective_radius_mm: float = 0.19       # nominal 0.19 mm inner radius
    air_bubble_volume_ul: float = 0.0       # compressible air pocket in line (uL)
    cannula_kink_ratio: float = 0.0         # cannula kink restriction [0, 0.98]
    luer_leak_fraction: float = 0.0         # fractional leak at Luer connector [0, 0.8]
    line_pressure_kpa: float = 1.8          # inline gauge pressure above atmospheric (kPa)
    stored_elastic_volume_ul: float = 0.0   # volume trapped in compliant tubing/bubbles (uL)
    flow_rate_ul_min: float = 0.0           # actual flow delivered out of cannula (uL/min)
    debris_particle_positions: list[float] | None = None  # normalized [0..1] along tube


class PipeDebrisAndFluidicsModel:
    """Hagen-Poiseuille + Boyle's Law compliant microbore infusion pipe model."""

    def __init__(self, nominal_radius_mm: float = 0.19, tube_length_mm: float = 600.0):
        self.r0_mm = float(nominal_radius_mm)
        self.length_mm = float(tube_length_mm)
        self.p_atm_kpa = 101.325
        self.p_tissue_kpa = 1.5
        # Nominal hydraulic resistance (kPa / (uL/min)) for microbore tube + 29G cannula
        self.r_hyd_0 = 0.42
        # Nominal elastomeric PVC/PE tubing compliance (uL / kPa)
        self.c_tube_ul_per_kpa = 0.045
        self.state = FluidicState(
            effective_radius_mm=self.r0_mm,
            debris_particle_positions=[0.12, 0.28, 0.46, 0.64, 0.81],
        )

    def reset(self):
        self.state = FluidicState(
            effective_radius_mm=self.r0_mm,
            debris_particle_positions=[0.12, 0.28, 0.46, 0.64, 0.81],
        )

    def inject_fault(self, *, debris_ratio: float | None = None, air_bubble_ul: float | None = None,
                     cannula_kink: float | None = None, luer_leak: float | None = None):
        if debris_ratio is not None:
            self.state.debris_occlusion_ratio = float(np.clip(debris_ratio, 0.0, 0.97))
            self.state.effective_radius_mm = self.r0_mm * (1.0 - self.state.debris_occlusion_ratio)
        if air_bubble_ul is not None:
            self.state.air_bubble_volume_ul = float(max(0.0, air_bubble_ul))
        if cannula_kink is not None:
            self.state.cannula_kink_ratio = float(np.clip(cannula_kink, 0.0, 0.97))
        if luer_leak is not None:
            self.state.luer_leak_fraction = float(np.clip(luer_leak, 0.0, 0.85))

    def vent_pressure_relief(self):
        """Actuate back-pressure relief valve to safely dump trapped elastic volume."""
        self.state.stored_elastic_volume_ul = 0.0
        self.state.line_pressure_kpa = self.p_tissue_kpa

    def step(self, plunger_displaced_u: float, dt_min: float = 5.0,
             pinch_valve_closed: bool = False, progressive_debris_rate: float = 0.0) -> dict:
        """Integrate compliant pipe pressure, debris lodging, and outflow over `dt_min`."""
        s = self.state
        if progressive_debris_rate > 0.0 and plunger_displaced_u > 0.0:
            s.debris_occlusion_ratio = float(min(0.95, s.debris_occlusion_ratio + progressive_debris_rate * plunger_displaced_u))
        s.effective_radius_mm = self.r0_mm * (1.0 - s.debris_occlusion_ratio)

        # 4th-power Hagen-Poiseuille hydraulic resistance scaling
        r_debris_factor = 1.0 / max(1e-4, (1.0 - s.debris_occlusion_ratio) ** 4)
        r_kink_factor = 1.0 / max(1e-4, (1.0 - s.cannula_kink_ratio) ** 3)
        r_total = self.r_hyd_0 * (0.65 * r_debris_factor + 0.35 * r_kink_factor)

        q_in_ul = max(0.0, float(plunger_displaced_u)) * UL_PER_UNIT
        n_sub = 25
        h_min = dt_min / n_sub
        q_in_rate = q_in_ul / dt_min
        delivered_ul = 0.0
        leaked_ul = 0.0

        for _ in range(n_sub):
            # Boyle's Law air bubble compliance: C_air = V_air0 * P_atm / (P_atm + P_line)^2
            c_bubble = (
                s.air_bubble_volume_ul * self.p_atm_kpa / ((self.p_atm_kpa + max(0.0, s.line_pressure_kpa)) ** 2)
                if s.air_bubble_volume_ul > 0.0 else 0.0
            )
            c_tot = self.c_tube_ul_per_kpa + c_bubble

            if pinch_valve_closed:
                q_out_rate = 0.0
            else:
                dp = max(0.0, s.line_pressure_kpa - self.p_tissue_kpa)
                # Steady flow at low resistance, pressure-limited under occlusion
                q_out_rate = dp / r_total

            # Luer-lock leak proportional to line pressure
            q_leak_rate = s.luer_leak_fraction * q_in_rate if s.luer_leak_fraction > 0 else 0.0

            # If unobstructed and no air bubble, quasi-steady equilibrium avoids numerical stiffness
            if r_total < 3.0 and s.air_bubble_volume_ul < 0.5 and not pinch_valve_closed:
                q_net_avail = max(0.0, q_in_rate - q_leak_rate)
                q_out_rate = q_net_avail
                s.line_pressure_kpa = self.p_tissue_kpa + q_out_rate * r_total
            else:
                d_vol = h_min * (q_in_rate - q_out_rate - q_leak_rate)
                s.stored_elastic_volume_ul = max(0.0, s.stored_elastic_volume_ul + d_vol)
                s.line_pressure_kpa = self.p_tissue_kpa + s.stored_elastic_volume_ul / max(c_tot, 1e-4)
                s.line_pressure_kpa = min(s.line_pressure_kpa, 185.0)

            delivered_ul += h_min * q_out_rate
            leaked_ul += h_min * q_leak_rate

        s.flow_rate_ul_min = delivered_ul / dt_min
        # Update 3D debris particle positions along tube (stalling at constriction point ~0.72)
        if s.debris_particle_positions is not None:
            lodging_point = 0.72
            updated_pos = []
            step_adv = 0.04 * (s.flow_rate_ul_min / max(0.15, q_in_rate + 1e-6))
            for pos in s.debris_particle_positions:
                if s.debris_occlusion_ratio > 0.35 and pos >= lodging_point - 0.06:
                    # Particles pile up at the constriction throat
                    new_p = min(lodging_point, pos + 0.005)
                else:
                    new_p = (pos + step_adv) % 0.95
                updated_pos.append(round(float(new_p), 4))
            s.debris_particle_positions = updated_pos

        delivered_u = delivered_ul / UL_PER_UNIT
        return {
            "commanded_plunger_u": float(plunger_displaced_u),
            "delivered_cannula_u": float(delivered_u),
            "leaked_u": float(leaked_ul / UL_PER_UNIT),
            "line_pressure_kpa": float(s.line_pressure_kpa),
            "effective_radius_mm": float(s.effective_radius_mm),
            "debris_occlusion_ratio": float(s.debris_occlusion_ratio),
            "air_bubble_volume_ul": float(s.air_bubble_volume_ul),
            "cannula_kink_ratio": float(s.cannula_kink_ratio),
            "hydraulic_resistance_ratio": float(r_total / self.r_hyd_0),
            "flow_rate_ul_min": float(s.flow_rate_ul_min),
            "debris_particle_positions": list(s.debris_particle_positions or []),
        }


@dataclass
class BatteryState:
    soc: float = 0.92                       # State of charge [0..1]
    ocv_v: float = 4.08                     # Open-circuit voltage (V)
    terminal_v: float = 4.02                # Terminal voltage under load (V)
    internal_resistance_ohm: float = 0.18   # Series resistance R_int (Ohm)
    polarization_v: float = 0.01            # RC polarization overpotential (V)
    load_current_ma: float = 18.0           # Instantaneous load current (mA)
    cell_temp_c: float = 31.5               # Cell temperature (C)
    supercap_v: float = 4.95                # 5V emergency hold-up supercap voltage (V)
    brownout_tripped: bool = False          # True if V_term < 3.05 V


class BatteryElectroThermalModel:
    """Li-Ion / Li-SOCl2 equivalent-circuit battery model with bolus load sag and supercap hold-up."""

    def __init__(self, initial_soc: float = 0.92, capacity_mah: float = 1200.0):
        self.capacity_mah = float(capacity_mah)
        self.brownout_threshold_v = 3.05
        self.state = BatteryState(soc=float(initial_soc))
        self._update_ocv()

    def _update_ocv(self):
        soc = float(np.clip(self.state.soc, 0.001, 1.0))
        # Realistic nonlinear Li-Ion OCV curve (3.0V at 0% -> 4.18V at 100%, steep knee below 12%)
        self.state.ocv_v = (
            3.02
            + 1.02 * soc
            - 0.06 / (soc + 0.10)
            + 0.18 * math.exp(-12.0 * (1.0 - soc))
        )

    def reset(self, soc: float = 0.92):
        self.state = BatteryState(soc=float(soc))
        self._update_ocv()
        self.state.terminal_v = self.state.ocv_v - 0.02

    def inject_fault(self, *, soc: float | None = None, internal_resistance_ohm: float | None = None,
                     cell_temp_c: float | None = None):
        if soc is not None:
            self.state.soc = float(np.clip(soc, 0.0, 1.0))
            self._update_ocv()
        if internal_resistance_ohm is not None:
            self.state.internal_resistance_ohm = float(max(0.08, internal_resistance_ohm))
        if cell_temp_c is not None:
            self.state.cell_temp_c = float(cell_temp_c)

    def step(self, motor_active_u: float, line_pressure_kpa: float = 2.0,
             pinch_valve_energized: bool = False, rapid_drain_rate: float = 0.0,
             dt_min: float = 5.0) -> dict:
        s = self.state
        # Base MCU + BLE telemetry quiescent current (18 mA peak, 1.8 mA sleep) + stepper motor pulse current
        pressure_load_ma = 1.5 * max(0.0, line_pressure_kpa - 1.8)
        motor_pulse_ma = (400.0 * min(1.0, max(0.25, motor_active_u / 0.12)) + pressure_load_ma) if motor_active_u > 0 else 0.0
        valve_ma = 160.0 if pinch_valve_energized else 0.0
        peak_current_ma = 18.0 + motor_pulse_ma + valve_ma
        # Motor pulse lasts ~0.3s out of every 300s (0.1% duty cycle)
        avg_current_ma = 2.2 + 0.003 * motor_pulse_ma + 0.01 * valve_ma

        # Coulomb counting + optional rapid battery drain / short fault
        d_soc = (avg_current_ma * (dt_min / 60.0)) / self.capacity_mah + rapid_drain_rate
        s.soc = float(max(0.0, s.soc - d_soc))
        self._update_ocv()

        # Internal resistance increases sharply at low SOC (<12%)
        low_soc_r = 0.65 * math.exp(-16.0 * s.soc)
        r_eff = s.internal_resistance_ohm + low_soc_r

        # RC polarization voltage & terminal voltage sag during peak motor actuation pulse
        i_peak_a = peak_current_ma / 1000.0
        s.polarization_v = 0.6 * s.polarization_v + 0.4 * (0.12 * i_peak_a)
        s.terminal_v = float(max(2.1, s.ocv_v - i_peak_a * r_eff - s.polarization_v))
        s.load_current_ma = float(peak_current_ma)
        s.cell_temp_c = float(31.0 + 0.05 * (i_peak_a ** 2) * r_eff * 100.0)

        if s.terminal_v < self.brownout_threshold_v:
            s.brownout_tripped = True
            # Supercapacitor discharges slowly to sustain safety supervisor & pinch valve
            s.supercap_v = float(max(3.3, s.supercap_v - 0.08))
        else:
            s.supercap_v = float(min(4.95, s.supercap_v + 0.05))

        return asdict(s)


@dataclass
class ElectromechanicalState:
    motor_stiction_factor: float = 0.0      # [0..1] bearing friction / stiction
    lead_screw_backlash_mm: float = 0.0     # lost motion deadband on reversal/start
    commanded_steps: int = 0
    encoder_measured_steps: int = 0
    step_loss_count: int = 0
    pinch_valve_closed: bool = False
    cgm_drift_mgdl: float = 0.0


class ElectromechanicalPumpModel:
    """Stepper motor `M03`, lead screw `M05`, optical encoder, and pinch valve `V01`."""

    STEPS_PER_UNIT = 200  # 1 step = 0.005 U (50 nL)

    def __init__(self):
        self.state = ElectromechanicalState()
        self._uncompensated_backlash_u = 0.0

    def reset(self):
        self.state = ElectromechanicalState()
        self._uncompensated_backlash_u = 0.0

    def inject_fault(self, *, stiction: float | None = None, backlash_mm: float | None = None,
                     cgm_drift_mgdl: float | None = None):
        if stiction is not None:
            self.state.motor_stiction_factor = float(np.clip(stiction, 0.0, 0.98))
        if backlash_mm is not None:
            self.state.lead_screw_backlash_mm = float(max(0.0, backlash_mm))
            self._uncompensated_backlash_u = self.state.lead_screw_backlash_mm * 0.12
        if cgm_drift_mgdl is not None:
            self.state.cgm_drift_mgdl = float(cgm_drift_mgdl)

    def step(self, commanded_u: float, terminal_v: float, line_pressure_kpa: float,
             stuck_on_u: float = 0.0, gain_factor: float = 1.0,
             pump_noise_g: float = 0.0) -> dict:
        s = self.state
        # If battery voltage drops below brownout (2.85V), stepper driver loses phase current
        voltage_torque_ratio = float(np.clip((terminal_v - 2.65) / (4.0 - 2.65), 0.0, 1.15))
        # Load torque ratio from pipe back-pressure + bearing stiction
        load_torque_ratio = 0.20 + 0.0085 * max(0.0, line_pressure_kpa - 1.8) + 0.85 * s.motor_stiction_factor

        effective_cmd_u = max(0.0, commanded_u * gain_factor) + stuck_on_u
        cmd_steps = int(round(effective_cmd_u * self.STEPS_PER_UNIT))

        if cmd_steps > 0:
            if voltage_torque_ratio < 0.35:
                # Severe brownout stall
                actual_steps = int(round(cmd_steps * 0.15 * voltage_torque_ratio))
            elif load_torque_ratio > voltage_torque_ratio:
                # Partial/full stepper stall due to high back-pressure or stiction
                slip_fraction = float(np.clip(1.0 - (load_torque_ratio - voltage_torque_ratio) * 1.4, 0.0, 1.0))
                actual_steps = int(round(cmd_steps * slip_fraction))
            else:
                actual_steps = cmd_steps
        else:
            actual_steps = 0

        lost_steps = max(0, cmd_steps - actual_steps)
        s.commanded_steps += cmd_steps
        s.encoder_measured_steps += actual_steps
        s.step_loss_count += lost_steps

        plunger_u = actual_steps / float(self.STEPS_PER_UNIT)
        # Apply lead-screw backlash deadband if present
        if self._uncompensated_backlash_u > 0.0 and plunger_u > 0.0:
            absorbed = min(plunger_u, self._uncompensated_backlash_u)
            plunger_u -= absorbed
            self._uncompensated_backlash_u -= absorbed

        # Add mechanical quantization + noise (matching GECO v6 nominal_emission characteristics when healthy)
        if plunger_u > 0.0:
            noise_u = pump_noise_g / GRAMS_PER_UNIT
            plunger_u = max(0.0, plunger_u * 1.015 + 0.0015 / GRAMS_PER_UNIT + noise_u)

        return {
            "commanded_steps_delta": cmd_steps,
            "encoder_steps_delta": actual_steps,
            "lost_steps_delta": lost_steps,
            "plunger_displaced_u": float(plunger_u),
            "voltage_torque_ratio": float(voltage_torque_ratio),
            "load_torque_ratio": float(load_torque_ratio),
            "step_loss_total": int(s.step_loss_count),
        }


class MultiPhysicsPumpRig:
    """Coupled Fluidic + Electro-Thermal Battery + Electromechanical + Gravimetric Balance Rig."""

    def __init__(self):
        self.fluidics = PipeDebrisAndFluidicsModel()
        self.battery = BatteryElectroThermalModel()
        self.mechanics = ElectromechanicalPumpModel()
        self.cumulative_mass_g = 0.0
        self.last_balance_read_g = 0.0

    def reset(self):
        self.fluidics.reset()
        self.battery.reset()
        self.mechanics.reset()
        self.cumulative_mass_g = 0.0
        self.last_balance_read_g = 0.0

    def step(self, authorized_u: float, *, condition: str = "clean", active: bool = False,
             pinch_valve_closed: bool = False, pump_noise_g: float = 0.0,
             balance_noise_vec: np.ndarray | None = None, dt_min: float = 5.0) -> dict:
        """Execute one 5-minute coupled multi-physics step."""
        # Configure active fault physics based on scenario condition
        gain_factor = 1.0
        stuck_on_u = 0.0
        report_mask = False
        cgm_bias = 0.0
        cgm_missing = False
        prog_debris = 0.0
        rapid_drain = 0.0

        if active:
            if condition == "excess_2x":
                gain_factor = 2.0
            elif condition == "occlusion":
                self.fluidics.inject_fault(debris_ratio=0.92, cannula_kink=0.65)
            elif condition == "pipe_debris":
                prog_debris = 0.35
                self.fluidics.inject_fault(
                    debris_ratio=max(0.76, self.fluidics.state.debris_occlusion_ratio),
                    air_bubble_ul=12.0,
                )
            elif condition == "battery_brownout":
                rapid_drain = 0.12
                self.battery.inject_fault(
                    soc=min(0.08, self.battery.state.soc),
                    internal_resistance_ohm=2.45,
                )
            elif condition == "motor_malfunction":
                self.mechanics.inject_fault(stiction=0.78, backlash_mm=0.35)
            elif condition == "stuck_on":
                stuck_on_u = 0.25
            elif condition == "cgm_bias_40":
                cgm_bias = 40.0
            elif condition == "cgm_missing":
                cgm_missing = True
            elif condition == "excess_bias_25":
                gain_factor = 2.0
                cgm_bias = 25.0
            elif condition == "excess_bias_report_mask":
                gain_factor = 2.0
                cgm_bias = 25.0
                report_mask = True
        else:
            # Post-fault physical recovery when fault window ends
            if condition in ("occlusion", "pipe_debris") and self.fluidics.state.debris_occlusion_ratio > 0:
                self.fluidics.inject_fault(debris_ratio=0.0, air_bubble_ul=0.0, cannula_kink=0.0)
                self.fluidics.vent_pressure_relief()
            if condition == "battery_brownout" and self.battery.state.internal_resistance_ohm > 0.5:
                self.battery.reset(soc=0.88)
            if condition == "motor_malfunction" and self.mechanics.state.motor_stiction_factor > 0:
                self.mechanics.inject_fault(stiction=0.0, backlash_mm=0.0)

        # 1. Battery step under motor & pinch-valve load
        bat_info = self.battery.step(
            motor_active_u=authorized_u * gain_factor + stuck_on_u,
            line_pressure_kpa=self.fluidics.state.line_pressure_kpa,
            pinch_valve_energized=pinch_valve_closed,
            rapid_drain_rate=rapid_drain,
            dt_min=dt_min,
        )

        # 2. Electromechanical actuator step
        if pinch_valve_closed:
            mech_info = {
                "commanded_steps_delta": 0,
                "encoder_steps_delta": 0,
                "lost_steps_delta": 0,
                "plunger_displaced_u": 0.0,
                "voltage_torque_ratio": 1.0,
                "load_torque_ratio": 0.2,
                "step_loss_total": int(self.mechanics.state.step_loss_count),
            }
        else:
            mech_info = self.mechanics.step(
                commanded_u=authorized_u,
                terminal_v=bat_info["terminal_v"],
                line_pressure_kpa=self.fluidics.state.line_pressure_kpa,
                stuck_on_u=stuck_on_u,
                gain_factor=gain_factor,
                pump_noise_g=pump_noise_g,
            )

        # 3. Microbore pipe fluidics & debris step
        fluid_info = self.fluidics.step(
            plunger_displaced_u=mech_info["plunger_displaced_u"],
            dt_min=dt_min,
            pinch_valve_closed=pinch_valve_closed,
            progressive_debris_rate=prog_debris,
        )

        # 4. Gravimetric balance (`T01`..`T06`) truth measurement
        emitted_u = fluid_info["delivered_cannula_u"]
        emitted_g = emitted_u * GRAMS_PER_UNIT
        self.cumulative_mass_g += emitted_g
        b_noise = np.zeros(5) if balance_noise_vec is None else np.asarray(balance_noise_vec, dtype=float)
        reading_g = round(float(np.median(self.cumulative_mass_g + b_noise)) / 0.01) * 0.01
        delta_g = reading_g - self.last_balance_read_g
        self.last_balance_read_g = reading_g
        reported_delta_g = authorized_u * GRAMS_PER_UNIT if report_mask else delta_g

        return {
            "emitted_u": float(emitted_u),
            "emitted_g": float(emitted_g),
            "local_measured_delta_g": float(delta_g),
            "network_reported_delta_g": float(reported_delta_g),
            "cgm_bias_mgdl": float(cgm_bias),
            "cgm_missing": bool(cgm_missing),
            "report_mask": bool(report_mask),
            "fluidics": fluid_info,
            "battery": bat_info,
            "mechanics": mech_info,
        }
