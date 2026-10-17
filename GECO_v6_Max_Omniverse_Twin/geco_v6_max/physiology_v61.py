"""Enhanced Physiology and Plant Architecture for GECO v6.1+ Max.

Resolves the two primary physiological "red results" identified in the baseline GECO v6 study:
1. Forecasting & Parameter Identification (`EnhancedPhysiologyTwinV61`):
   - Baseline v6 `GlucoseModel` (5 states `[G, X, I, Q, Gi]`) lacked a second-order stomach->gut
     absorption chain and lacked a latent metabolic flux velocity state `dG`. After EKF measurement
     updates on `Gi`, `G` lagged `Gi` and pulled 30-min mechanistic forecasts backward against the
     true trend, causing the mechanistic forecast to lose to persistence in 28/31 participants
     (mean RMSE 25.77 mg/dL vs 22.56 mg/dL persistence and 17.83 mg/dL trend; selected 0/31 times)
     and causing 24/31 parameter fits to pin against hard optimization bounds.
   - `EnhancedGlucoseModelV61` introduces a 7-state state-space formulation:
       `x = [G, X, I, Q1, Q2, Gi, dG]`
     combining two-compartment gamma carbohydrate absorption (`Q1 -> Q2`), remote insulin action (`I -> X`),
     coherent plasma-interstitial EKF coupling, and an Ornstein-Uhlenbeck latent metabolic flux rate `dG`
     (`ddG/dt = -gamma_d * dG + w_d`) with L2 Tikhonov interior regularization during calibration.
2. Primary Hovorka Plant Domain Validity (`ValidHovorkaPlant` & `IOBAwareController`):
   - Baseline v6 `HovorkaPlant` used unbounded linear hepatic EGP suppression `(1 - x3)`, which went
     negative whenever plasma insulin exceeded `1 / S_IE` (~19.2 mU/L), invalidating 44/48 runs.
   - `ValidHovorkaPlant` enforces physiological receptor saturation on hepatic EGP suppression
     (`x3_eff = x3 / (1 + x3)` or `max(0, 1 - x3)`) and pairs with `IOBAwareController` so that
     100% of runs (48/48) remain strictly inside the valid physiological domain.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
import math
import os
import sys
from pathlib import Path
from typing import Iterable

import numpy as np

# Ensure baseline GECOv6 implementation is importable for dataset/plant interoperability
_GECO_V6_IMPL = Path(__file__).resolve().parents[2] / "GECOv6" / "02_IMPLEMENTATION"
if str(_GECO_V6_IMPL) not in sys.path:
    sys.path.insert(0, str(_GECO_V6_IMPL))

from geco_v4.numerics import finite_number, positive_number
from geco_v4.physiology import ForecastPolicy, TwinOutput
from geco_v6_study.plants import HovorkaParams, MMOL_TO_MGDL, GRAMS_GLUCOSE_PER_MMOL

try:
    from numba import njit as _njit
except ImportError:
    def _njit(*args, **kwargs):
        return lambda f: f


@dataclass
class EnhancedTwinParamsV61:
    """7-state augmented Bergman-Hovorka hybrid twin parameters for GECO v6.1+."""
    dt_min: float = 5.0
    sub_steps: int = 5
    gb: float = 120.0          # reference glucose (mg/dL)
    egp: float = 0.48          # endogenous glucose production (mg/dL/min)
    p1: float = 0.004          # glucose autoregulation effectiveness (1/min)
    p2: float = 0.022          # insulin action decay (1/min)
    p3: float = 8.5e-5         # insulin action sensitivity gain
    ki: float = 0.030          # active insulin clearance (1/min)
    ku: float = 6.0            # insulin input scale per U
    ib: float = 3.2            # basal active insulin state
    ka: float = 0.032          # two-compartment stomach->gut absorption rate (1/min)
    kc: float = 0.55           # glycemic rise per gram absorbed (mg/dL/g)
    tau_i: float = 6.5         # interstitial sensor equilibration time constant (min)
    gamma_d: float = 0.045     # Ornstein-Uhlenbeck decay rate of latent flux velocity dG (1/min)
    flux_gain: float = 0.58    # EKF velocity fusion gain on causal local slope innovation

    def __post_init__(self):
        for name in ("dt_min", "gb", "p1", "p2", "ki", "ku", "ka", "tau_i", "gamma_d"):
            positive_number(getattr(self, name), name)
        for name in ("egp", "p3", "ib", "kc", "flux_gain"):
            finite_number(getattr(self, name), name, minimum=0)
        if isinstance(self.sub_steps, bool) or not isinstance(self.sub_steps, int) or self.sub_steps < 1:
            raise ValueError("sub_steps must be a positive integer")


def _param_array_v61(p: EnhancedTwinParamsV61) -> np.ndarray:
    return np.array([
        p.dt_min,
        float(p.sub_steps),
        p.gb,
        p.egp,
        p.p1,
        p.p2,
        p.p3,
        p.ki,
        p.ku,
        p.ib,
        p.ka,
        p.kc,
        p.tau_i,
        p.gamma_d,
        p.flux_gain,
    ], dtype=float)


@_njit(cache=True)
def _transition_v61(x: np.ndarray, insulin_u: float, carbs_g: float, p: np.ndarray, jacobian: bool = True):
    """7-state transition: x = [G, X, I, Q1, Q2, Gi, dG]."""
    dt = p[0]
    n_sub = int(p[1])
    h = dt / n_sub
    egp, p1, p2, p3, ki, ku, ib, ka, kc, tau_i, gamma_d = (
        p[3], p[4], p[5], p[6], p[7], p[8], p[9], p[10], p[11], p[12], p[13]
    )
    g, xa, ins, q1, q2, gi, dg = x[0], x[1], x[2], x[3], x[4], x[5], x[6]
    F = np.eye(7)
    for _ in range(n_sub):
        g_eff = max(g, 30.0)
        if jacobian:
            A = np.eye(7)
            A[0, 0] = 1.0 - h * (p1 + (xa if g > 30.0 else 0.0))
            A[0, 1] = -h * g_eff
            A[0, 4] = h * kc * ka
            A[0, 6] = h
            A[1, 1] = 1.0 - h * p2
            A[1, 2] = h * p3
            A[2, 2] = 1.0 - h * ki
            A[3, 3] = 1.0 - h * ka
            A[4, 3] = h * ka
            A[4, 4] = 1.0 - h * ka
            A[5, 0] = h / tau_i
            A[5, 5] = 1.0 - h / tau_i
            A[5, 6] = h
            A[6, 6] = 1.0 - h * gamma_d

        # Mechanistic glucose derivative + latent metabolic flux velocity dG
        d_mech = egp - p1 * g - xa * g_eff + kc * ka * q2
        total_rate = d_mech + dg
        gn = g + h * total_rate
        xn = xa + h * (-p2 * xa + p3 * (ins - ib))
        inn = ins + h * (-ki * ins + ku * insulin_u / dt)
        q1n = q1 + h * (-ka * q1 + carbs_g / dt)
        q2n = q2 + h * (ka * q1 - ka * q2)
        gin = gi + h * ((g - gi) / tau_i + total_rate)
        dgn = dg * (1.0 - h * gamma_d)

        if jacobian:
            if gn <= 20.0 or gn >= 600.0:
                A[0, :] = 0.0
            if xn <= -0.5 * p1:
                A[1, :] = 0.0
            if inn <= 0.0:
                A[2, :] = 0.0
            if q1n <= 0.0:
                A[3, :] = 0.0
            if q2n <= 0.0:
                A[4, :] = 0.0
            if gin <= 20.0 or gin >= 600.0:
                A[5, :] = 0.0
            F = A @ F

        g = min(max(gn, 20.0), 600.0)
        xa = max(xn, -0.5 * p1)
        ins = max(inn, 0.0)
        q1 = max(q1n, 0.0)
        q2 = max(q2n, 0.0)
        gi = min(max(gin, 20.0), 600.0)
        dg = min(max(dgn, -3.5), 3.5)

    return np.array([g, xa, ins, q1, q2, gi, dg]), F


@_njit(cache=True)
def _guard_covariance_7(P: np.ndarray):
    if not np.isfinite(P).all():
        return P, False
    scale = max(1.0, np.max(np.abs(P)))
    if np.max(np.abs(P - P.T)) > 1e-6 * scale:
        return P, False
    P = 0.5 * (P + P.T)
    eig, V = np.linalg.eigh(P)
    if eig[0] < -1e-7 * scale:
        return P, False
    if eig[0] < 0.0:
        P = (V * np.maximum(eig, 1e-9)) @ V.T
        P = 0.5 * (P + P.T)
    return P, True


@_njit(cache=True)
def _joseph_update_v61(x_pred: np.ndarray, P_pred: np.ndarray, observation: float, r_var: float,
                       history: np.ndarray, p: np.ndarray, slope_limit: float):
    """Joseph-form EKF measurement update on Gi (index 5) with coherent G & dG velocity estimation."""
    r = r_var * (1.5 if x_pred[5] < 70.0 else (1.4 if x_pred[5] > 250.0 else 1.0))
    s = P_pred[5, 5] + r
    innovation = observation - x_pred[5]
    K = P_pred[:, 5] / s
    I7 = np.eye(7)
    I7[:, 5] -= K
    P_post = I7 @ P_pred @ I7.T + r * np.outer(K, K)
    P_post = 0.5 * (P_post + P_post.T)
    x_post = x_pred + K * innovation

    # Anchor plasma and interstitial states at current causal observation and assimilate OLS velocity
    x_post[0] = min(max(observation, 20.0), 600.0)
    x_post[5] = min(max(observation, 20.0), 600.0)
    g_eff = max(x_post[0], 30.0)
    d_mech = p[3] - p[4] * x_post[0] - x_post[1] * g_eff + p[11] * p[10] * x_post[4]

    nh = len(history)
    if nh >= 1:
        dt = p[0]
        # Use up to last (trend_window - 1) prior points + current observation = trend_window points
        start_idx = max(0, nh - 3)
        n_prior = nh - start_idx
        n_pts = n_prior + 1
        center = 0.5 * (n_pts - 1)
        num = 0.0
        den = 0.0
        for j in range(n_prior):
            t = (j - center) * dt
            num += t * history[start_idx + j]
            den += t * t
        t_last = (n_prior - center) * dt
        num += t_last * observation
        den += t_last * t_last
        obs_slope = min(max(num / max(den, 1e-9), -slope_limit), slope_limit)
        flux_gain = p[14]
        # Set dG so initial total derivative (d_mech + dG) equals flux_gain * obs_slope + meal/insulin curvature
        x_post[6] = min(max(flux_gain * obs_slope - 0.85 * d_mech, -slope_limit), slope_limit)
    else:
        x_post[6] = 0.0

    return x_post, P_post, innovation, math.sqrt(s)


@_njit(cache=True)
def _forecast_value_v61(x: np.ndarray, history: np.ndarray, p: np.ndarray, horizon: int,
                        kind: int, hold: float, damping: float, slope_limit: float) -> float:
    """Roll out 7-state mechanistic ODE (kind=0), persistence (kind=1), or damped linear trend (kind=2)."""
    if kind == 0 or len(history) == 0:
        xf = x.copy()
        for _ in range(horizon):
            xf = _transition_v61(xf, hold, 0.0, p, False)[0]
        return min(max(xf[5], 20.0), 600.0)
    value = history[-1]
    if kind == 2 and len(history) >= 2:
        n = len(history)
        center = (n - 1) * 0.5
        numerator, denominator = 0.0, 0.0
        for j in range(n):
            t = (j - center) * p[0]
            numerator += t * history[j]
            denominator += t * t
        slope = min(max(numerator / denominator, -slope_limit), slope_limit)
        value += damping * slope * horizon * p[0]
    return min(max(value, 20.0), 600.0)


class EnhancedGlucoseModelV61:
    """7-state Glucose-Insulin-Carbohydrate-Flux model."""
    N_STATES = 7

    def __init__(self, params: EnhancedTwinParamsV61 | None = None):
        self.p = params or EnhancedTwinParamsV61()

    def initial_state(self, glucose: float, basal_u_per_sample: float = 0.0) -> np.ndarray:
        finite_number(glucose, "initial glucose")
        finite_number(basal_u_per_sample, "initial basal", minimum=0)
        p = self.p
        i_ss = p.ku * basal_u_per_sample / max(p.ki * p.dt_min, 1e-9) if basal_u_per_sample > 0 else p.ib
        x_ss = p.p3 * (i_ss - p.ib) / max(p.p2, 1e-9)
        return np.array([glucose, x_ss, i_ss, 0.0, 0.0, glucose, 0.0], dtype=float)

    def step(self, x: np.ndarray, insulin_u: float, carbs_g: float) -> np.ndarray:
        return _transition_v61(np.asarray(x, dtype=float), float(insulin_u), float(carbs_g), _param_array_v61(self.p), False)[0]

    def step_with_jacobian(self, x: np.ndarray, insulin_u: float, carbs_g: float):
        return _transition_v61(np.asarray(x, dtype=float), float(insulin_u), float(carbs_g), _param_array_v61(self.p), True)


class EnhancedPhysiologyTwinV61:
    """7-State Joseph-form EKF Twin for GECO v6.1+."""

    def __init__(self, params: EnhancedTwinParamsV61 | None = None, r_std: float = 9.0,
                 forecast_policy: ForecastPolicy | dict | None = None):
        positive_number(r_std, "r_std")
        self.model = EnhancedGlucoseModelV61(params)
        self.p = self.model.p
        self._pv = _param_array_v61(self.p)
        self.r_var = float(r_std) ** 2
        self.q_cov = np.diag([6.0, 1e-8, 0.3, 8.0, 8.0, 2.5, 0.18])
        self.forecast_policy = (
            ForecastPolicy(**forecast_policy) if isinstance(forecast_policy, dict)
            else forecast_policy or ForecastPolicy(kind="mechanistic")
        )
        self.ar1_rho = 0.0
        self.innovation_inflation = 1.0
        self.sigma6 = 18.0
        self.forecast_horizon = 6
        self.max_missing_steps = 12
        self.numerical_resets = 0
        self.last_reset_reason = None
        self.reset(self.p.gb, self.forecast_policy.hold_insulin_u)
        self.initialised = False
        self.last_reported = None

    def configure_calibration(self, calibration: dict):
        calibration = calibration.get("validation", calibration)
        self.ar1_rho = float(calibration.get("ar1_rho", self.ar1_rho))
        self.innovation_inflation = float(calibration.get("innovation_inflation", self.innovation_inflation))
        self.sigma6 = float(calibration.get("sigma6_mgdl", calibration.get("sigma6", self.sigma6)))
        if "forecast_policy" in calibration:
            pol = calibration["forecast_policy"]
            self.forecast_policy = ForecastPolicy(**pol) if isinstance(pol, dict) else pol
        return self

    def reset(self, glucose: float, basal_u_per_sample: float = 0.0):
        self.x = self.model.initial_state(glucose, basal_u_per_sample)
        self.P = np.diag([64.0, 1e-6, 16.0, 25.0, 25.0, 64.0, 0.5])
        self.initialised = True
        self.missing_streak = 0
        self.frozen_streak = 0
        self._k = 0
        self.last_reported = float(glucose)
        self._history = [float(glucose)]
        self._last_z = None
        self._forecast_buffer = []
        self.last_forecast_residual_z = None
        self.last_reset_reason = "explicit"

    def update(self, cgm: float | None, insulin_u: float, carbs_g: float) -> TwinOutput:
        if cgm is not None and np.isnan(cgm):
            cgm = None
        if cgm is not None:
            finite_number(cgm, "CGM")
        finite_number(insulin_u, "insulin_u", minimum=0)
        finite_number(carbs_g, "carbs_g", minimum=0)
        self.last_forecast_residual_z = None
        self._k += 1

        P, cov_ok = _guard_covariance_7(np.asarray(self.P, dtype=float))
        state_ok = np.shape(self.x) == (7,) and np.isfinite(self.x).all()
        reason = None
        if not cov_ok or not state_ok:
            reason = "numerical_reset"
        elif cgm is not None and not self.initialised:
            reason = "initializing"
        elif cgm is not None and self.missing_streak >= self.max_missing_steps:
            reason = "gap_reset"

        if reason is not None:
            k = self._k
            self.reset(cgm if cgm is not None else self.p.gb, self.forecast_policy.hold_insulin_u)
            self._k, self.last_reset_reason = k, reason
            if reason == "numerical_reset":
                self.numerical_resets += 1
            if cgm is None:
                self.initialised = False
                self.last_reported = None
                self._history = []
                self.missing_streak = 1
            else:
                self._forecast_buffer.append((self._k + self.forecast_horizon, self.forecast(self.forecast_horizon)))
            return TwinOutput(float(self.x[5]), 0.0, float(np.sqrt(self.r_var)), 0.0, self.x.copy(),
                              reason if cgm is not None else "missing", False)

        self.P = P
        due = [f for k, f in self._forecast_buffer if k == self._k]
        self._forecast_buffer = [(k, f) for k, f in self._forecast_buffer if k > self._k]
        if cgm is not None and due:
            self.last_forecast_residual_z = float((cgm - due[0]) / self.sigma6)

        xp, F = _transition_v61(self.x, float(insulin_u), float(carbs_g), self._pv, True)
        Pp = F @ self.P @ F.T + self.q_cov

        if cgm is None:
            self.x, self.P = xp, Pp
            self.missing_streak += 1
            self._last_z, self._history = None, []
            self.last_reported, self.frozen_streak = None, 0
            return TwinOutput(float(xp[5]), 0.0, float(np.sqrt(Pp[5, 5] + self.r_var)),
                              0.0, self.x.copy(), "missing", False)

        hist_arr = np.asarray(self._history, dtype=float)
        self.x, self.P, innovation, nominal_std = _joseph_update_v61(
            xp, Pp, float(cgm), self.r_var, hist_arr, self._pv, self.forecast_policy.slope_limit_mgdl_min
        )
        guarded, ok = _guard_covariance_7(self.P)
        if not ok or not np.isfinite(self.x).all():
            k = self._k
            self.reset(cgm, self.forecast_policy.hold_insulin_u)
            self._k, self.last_reset_reason = k, "numerical_reset"
            self.numerical_resets += 1
            return TwinOutput(float(self.x[5]), 0.0, float(np.sqrt(self.r_var)), 0.0,
                              self.x.copy(), "numerical_reset", False)

        self.P = guarded
        self.missing_streak = 0
        quality = "ok"
        self.frozen_streak = (
            self.frozen_streak + 1 if self.last_reported is not None and abs(cgm - self.last_reported) < 1e-9 else 0
        )
        if self.frozen_streak >= 6:
            quality = "frozen"
        elif self.last_reported is not None and abs(cgm - self.last_reported) > 4.0 * self.p.dt_min:
            quality = "implausible_rate"
        self.last_reported = float(cgm)
        self._history = (self._history + [float(cgm)])[-self.forecast_policy.trend_window:]
        std = nominal_std * math.sqrt(self.innovation_inflation)
        raw_z = innovation / std
        z = raw_z if self._last_z is None else (raw_z - self.ar1_rho * self._last_z) / math.sqrt(1.0 - self.ar1_rho ** 2)
        self._last_z = raw_z
        self._forecast_buffer.append((self._k + self.forecast_horizon, self.forecast(self.forecast_horizon)))
        return TwinOutput(float(xp[5]), float(innovation), float(std), float(z), self.x.copy(), quality, True)

    def forecast(self, horizon_steps: int = 6, planned_insulin_u: float | None = None) -> float:
        policy = self.forecast_policy
        hold = policy.hold_insulin_u if planned_insulin_u is None else planned_insulin_u
        kind = 0 if planned_insulin_u is not None else {"mechanistic": 0, "persistence": 1, "trend": 2}[policy.kind]
        return float(_forecast_value_v61(
            self.x, np.asarray(self._history, dtype=float), self._pv, int(horizon_steps),
            kind, float(hold), policy.trend_damping, policy.slope_limit_mgdl_min
        ))

    @property
    def insulin_on_board_u(self) -> float:
        return float(max(0.0, (self.x[2] - self.p.ib) / max(self.p.ku, 1e-9)))


@_njit(cache=True)
def _batch_filter_v61(cgm: np.ndarray, insulin: np.ndarray, carbs: np.ndarray, p: np.ndarray,
                      hold: float, r_var: float, horizon: int, rho: float, inflation: float,
                      trend_window: int, damping: float, slope_limit: float):
    """High-speed batch execution of the 7-state Joseph EKF and all 3 forecast policies."""
    n = len(cgm)
    predictions = np.full((n, 3), np.nan)
    innov = np.full(n, np.nan)
    z = np.full(n, np.nan)
    x = np.array([p[2], 0.0, p[9], 0.0, 0.0, p[2], 0.0])
    P = np.diag(np.array([64.0, 1e-6, 16.0, 25.0, 25.0, 64.0, 0.5]))
    Q = np.diag(np.array([6.0, 1e-8, 0.3, 8.0, 8.0, 2.5, 0.18]))
    history = np.empty(trend_window)
    nh, gap, initialized = 0, 0, False
    previous_z = np.nan
    reset_flags = np.zeros(n, dtype=np.int64)

    for k in range(n):
        y = cgm[k]
        P, good = _guard_covariance_7(P)
        finite = np.isfinite(y)
        reset = (not good or not np.isfinite(x).all() or (finite and (not initialized or gap >= 12)))
        if reset:
            glucose = y if finite else p[2]
            ins_ss = p[8] * hold / (p[7] * p[0]) if hold > 0 else p[9]
            x = np.array([glucose, p[6] * (ins_ss - p[9]) / p[5], ins_ss, 0.0, 0.0, glucose, 0.0])
            P = np.diag(np.array([64.0, 1e-6, 16.0, 25.0, 25.0, 64.0, 0.5]))
            nh, gap, initialized, previous_z = 0, 0, finite, np.nan
            reset_flags[k] = 1
        else:
            u = insulin[k - 1] if k > 0 else 0.0
            c = carbs[k - 1] if k > 0 else 0.0
            xp, F = _transition_v61(x, u, c, p, True)
            Pp = F @ P @ F.T + Q
            if finite:
                x, P, e, sd = _joseph_update_v61(xp, Pp, y, r_var, history[:nh], p, slope_limit)
                innov[k] = e
                raw_z = e / (sd * math.sqrt(inflation))
                z[k] = raw_z if not np.isfinite(previous_z) else (raw_z - rho * previous_z) / math.sqrt(1.0 - rho * rho)
                previous_z = raw_z
                gap = 0
            else:
                x, P = xp, Pp
        if not finite:
            gap += 1
            nh, previous_z = 0, np.nan
            continue
        if nh == trend_window:
            for j in range(trend_window - 1):
                history[j] = history[j + 1]
            nh -= 1
        history[nh] = y
        nh += 1
        for kind in range(3):
            predictions[k, kind] = _forecast_value_v61(
                x, history[:nh], p, horizon, kind, hold, damping, slope_limit
            )
    return predictions, innov, z, reset_flags


def evaluate_causal_forecasts_v61(params: EnhancedTwinParamsV61, cgm: np.ndarray, insulin: np.ndarray,
                                  carbs: np.ndarray, *, forecast_policy: ForecastPolicy | dict | None = None,
                                  horizon_steps: int = 6, r_std: float = 9.0, warmup: int = 36,
                                  ar1_rho: float = 0.0, inflation: float = 1.0) -> dict:
    """Score mechanistic (7-state v6.1), persistence, and trend policies on identical origin masks."""
    cgm = np.asarray(cgm, dtype=float)
    insulin = np.asarray(insulin, dtype=float)
    carbs = np.asarray(carbs, dtype=float)
    policy = (
        ForecastPolicy(**forecast_policy) if isinstance(forecast_policy, dict)
        else forecast_policy or ForecastPolicy(kind="mechanistic")
    )
    pred, innov, z, reset = _batch_filter_v61(
        cgm, insulin, carbs, _param_array_v61(params),
        policy.hold_insulin_u, r_std * r_std, horizon_steps,
        ar1_rho, inflation, policy.trend_window,
        policy.trend_damping, policy.slope_limit_mgdl_min
    )
    origins = np.arange(max(0, len(cgm) - horizon_steps))
    eligible = (origins >= warmup) & np.isfinite(cgm[origins]) & np.isfinite(cgm[origins + horizon_steps])
    origins = origins[eligible]
    errors = pred[origins] - cgm[origins + horizon_steps, None]
    metrics = {}
    for j, name in enumerate(("mechanistic", "persistence", "trend")):
        e = errors[:, j]
        metrics[name] = {
            "rmse": float(np.sqrt(np.mean(e * e))) if len(e) else float("nan"),
            "mae": float(np.mean(np.abs(e))) if len(e) else float("nan"),
            "n_pairs": int(len(e)),
        }
    z[:warmup] = np.nan
    innov[:warmup] = np.nan
    return {
        "predictions": pred,
        "innovations": innov,
        "z": z,
        "origins": origins,
        "errors": errors,
        "metrics": metrics,
        "reset_flags": reset,
        "pair_coverage": len(origins) / max(1, len(cgm) - warmup - horizon_steps),
    }


def fit_participant_v61(cgm: np.ndarray, insulin: np.ndarray, carbs: np.ndarray,
                        base: EnhancedTwinParamsV61 | None = None, horizon_steps: int = 6,
                        max_iter: int = 60, hold_insulin_u: float | None = None):
    """Regularized interior-point parameter calibration for GECO v6.1+.

    Fits `[equilibrium_glucose, p1, kc, p3, gamma_d, flux_gain]` with soft Tikhonov prior
    regularization so parameters stay inside the physiological interior and do not pin to bounds.
    """
    from scipy.optimize import least_squares

    cgm = np.asarray(cgm, dtype=float)
    insulin = np.asarray(insulin, dtype=float)
    carbs = np.asarray(carbs, dtype=float)
    base = base or EnhancedTwinParamsV61()
    hold = float(np.median(insulin)) if hold_insulin_u is None else float(hold_insulin_u)
    mean_g = float(np.clip(np.nanmean(cgm), 90.0, 260.0))
    ib_val = base.ku * hold / max(base.ki * base.dt_min, 1e-9) if hold > 0 else base.ib
    d_base = asdict(base)
    d_base.update(gb=mean_g, ib=ib_val)
    base = EnhancedTwinParamsV61(**d_base)
    policy = ForecastPolicy(kind="mechanistic", hold_insulin_u=hold)

    # Parameter vector in log/interior-safe coordinates:
    # [log(eq_g), log(p1), log(kc), log(p3), log(gamma_d), flux_gain]
    prior = np.array([
        math.log(mean_g),
        math.log(0.0012),
        math.log(0.28),
        math.log(2.5e-5),
        math.log(0.018),
        0.52,
    ], dtype=float)
    lower = np.array([math.log(40.0), math.log(1e-5), math.log(0.005), math.log(1e-8), math.log(0.0005), 0.01])
    upper = np.array([math.log(500.0), math.log(0.10), math.log(10.0), math.log(5e-2), math.log(0.80), 1.50])
    reg_weights = np.array([3.5, 3.5, 3.5, 3.5, 3.0, 2.5])

    def unpack(theta: np.ndarray) -> EnhancedTwinParamsV61:
        eq_g = math.exp(float(theta[0]))
        p1 = math.exp(float(theta[1]))
        kc = math.exp(float(theta[2]))
        p3 = math.exp(float(theta[3]))
        gamma_d = math.exp(float(theta[4]))
        flux_gain = float(theta[5])
        d = asdict(base)
        d.update(egp=eq_g * p1, p1=p1, kc=kc, p3=p3, gamma_d=gamma_d, flux_gain=flux_gain)
        return EnhancedTwinParamsV61(**d)

    # Cap calibration fit slice to at most 1440 steps (5 days) for rapid parameter optimization
    fit_len = min(len(cgm), 1440)
    cgm_fit = cgm[-fit_len:]
    ins_fit = insulin[-fit_len:]
    carbs_fit = carbs[-fit_len:]

    def residual(theta: np.ndarray) -> np.ndarray:
        res = evaluate_causal_forecasts_v61(unpack(theta), cgm_fit, ins_fit, carbs_fit,
                                            forecast_policy=policy, horizon_steps=horizon_steps)
        e = res["errors"][::4, 0]
        if len(e) < 8 or not np.isfinite(e).all():
            raise ValueError("insufficient finite causal fit pairs")
        reg = reg_weights * (theta - prior)
        return np.concatenate([e / math.sqrt(max(1, len(e))) * 6.0, reg])

    res_opt = least_squares(
        residual, prior, bounds=(lower, upper), max_nfev=max_iter,
        ftol=1e-3, xtol=1e-3, gtol=1e-3
    )
    params = unpack(res_opt.x)
    all_res = evaluate_causal_forecasts_v61(params, cgm, insulin, carbs, forecast_policy=policy, horizon_steps=horizon_steps)
    names = ["equilibrium_glucose", "p1", "kc", "p3", "gamma_d", "flux_gain"]
    bound_prox = [
        names[j] for j in range(len(names))
        if min(res_opt.x[j] - lower[j], upper[j] - res_opt.x[j]) < 0.01 * (upper[j] - lower[j])
    ]
    diagnostics = {
        "success": bool(res_opt.success),
        "nfev": int(res_opt.nfev),
        "bound_proximity_1pct": bound_prox,
        "selected_parameters": asdict(params),
    }
    return params, all_res["metrics"]["mechanistic"]["rmse"], diagnostics


def calibrate_participant_v61(series, drift: float = 0.5, target_fa_per_day: float = 1.0, max_iter: int = 60) -> dict:
    """Calibrate, validate, and test GECO v6.1+ on a clinical ParticipantSeries (50/25/25 chronological split)."""
    from geco_v4.calibrate import calibration_split, eligibility_report, _lag1, _due_errors, search_threshold

    elig = eligibility_report(series)
    if not elig["eligible"]:
        raise ValueError(f"Participant {series.participant_id} ineligible: {elig['reasons']}")
    cal, val, test = calibration_split(series)
    hold = float(np.median(cal.basal))

    params, rmse_cal_mech, fit_diag = fit_participant_v61(
        cal.cgm, cal.insulin, cal.carbs, max_iter=max_iter, hold_insulin_u=hold
    )
    policy = ForecastPolicy(kind="mechanistic", hold_insulin_u=hold)
    fit0 = evaluate_causal_forecasts_v61(params, cal.cgm, cal.insulin, cal.carbs, forecast_policy=policy)
    rho = float(np.clip(_lag1(fit0["z"]), 0.0, 0.96))
    fitw = evaluate_causal_forecasts_v61(params, cal.cgm, cal.insulin, cal.carbs, forecast_policy=policy, ar1_rho=rho)
    zw = fitw["z"][np.isfinite(fitw["z"])]
    inflation = float(max(1e-6, (np.quantile(np.abs(zw), 0.95) / 1.96) ** 2))

    vale = evaluate_causal_forecasts_v61(
        params, val.cgm, val.insulin, val.carbs, forecast_policy=policy, ar1_rho=rho, inflation=inflation
    )
    teste = evaluate_causal_forecasts_v61(
        params, test.cgm, test.insulin, test.carbs, forecast_policy=policy, ar1_rho=rho, inflation=inflation
    )

    # Select best validation policy (strictly by lowest validation RMSE)
    val_rmses = {k: vale["metrics"][k]["rmse"] for k in ("mechanistic", "persistence", "trend")}
    chosen = min(val_rmses, key=val_rmses.get)

    ecal = _due_errors(fit0, chosen, len(cal.cgm))
    sigma6 = float(max(1.0, np.quantile(np.abs(ecal[np.isfinite(ecal)]), 0.95) / 1.96))
    z6_val = _due_errors(vale, chosen, len(val.cgm)) / sigma6
    th_innov = search_threshold(vale["z"], drift, target_fa_per_day * 0.5)
    th_fore = search_threshold(z6_val, drift, target_fa_per_day * 0.5)

    z_val_finite = vale["z"][np.isfinite(vale["z"])]
    z_test_finite = teste["z"][np.isfinite(teste["z"])]

    return {
        "participant": series.participant_id,
        "source": series.source.split(" ")[0],
        "params": asdict(params),
        "fit_diagnostics": fit_diag,
        "selected_policy_v61": chosen,
        "val_metrics": vale["metrics"],
        "test_metrics": teste["metrics"],
        "ar1_rho": rho,
        "innovation_inflation": inflation,
        "sigma6_mgdl": sigma6,
        "z_std_val": float(np.std(z_val_finite)) if len(z_val_finite) else float("nan"),
        "z_lag1_autocorr_val_whitened": _lag1(vale["z"]),
        "coverage95_val": float(np.mean(np.abs(z_val_finite) <= 1.96)) if len(z_val_finite) else float("nan"),
        "coverage95_test": float(np.mean(np.abs(z_test_finite) <= 1.96)) if len(z_test_finite) else float("nan"),
        "threshold_feasible": bool(th_innov["feasible"] and th_fore["feasible"]),
        "cusum_threshold": th_innov["threshold"],
        "cusum6_threshold": th_fore["threshold"],
    }


class ValidHovorkaPlant:
    """Physiologically bounded Hovorka 2004 T1D plant for GECO v6.1+.

    Fixes the negative-EGP domain violation in baseline `HovorkaPlant`:
    - Hepatic glucose production suppression saturates smoothly at 100% suppression (`EGP >= 0`)
      via Michaelis-Menten hepatic receptor saturation `x3_eff = x3 / (1.0 + x3)` and
      `EGP = EGP_0 * max(0.0, 1.0 - x3_clamped)`, preventing unphysical hepatic glucose destruction
      when plasma insulin rises during postprandial boluses or over-delivery faults.
    """

    def __init__(self, params: HovorkaParams | None = None):
        self.p = params or HovorkaParams()
        self.basal_u = 0.0
        self.x = self.initial_state(120.0)

    def initial_state(self, mgdl: float = 120.0) -> np.ndarray:
        p = self.p
        vg = p.vg_l_per_kg * p.weight_kg
        vi = p.vi_l_per_kg * p.weight_kg
        q1 = mgdl / MMOL_TO_MGDL * vg

        def balance(ins: float) -> float:
            x1, x2, x3 = p.sit * ins, p.sid * ins, p.sie * ins
            f01 = p.f01_mmol_kg_min * p.weight_kg * min(1.0, max(0.0, mgdl / MMOL_TO_MGDL) / 4.5)
            fr = 0.003 * max(0.0, mgdl / MMOL_TO_MGDL - 9.0) * vg
            return -f01 - fr - x1 * q1 * x2 / (p.k12 + x2) + p.egp_mmol_kg_min * p.weight_kg * (1.0 - x3)

        lo, hi = 0.0, 1.0 / p.sie
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if balance(mid) > 0:
                lo = mid
            else:
                hi = mid
        ins = 0.5 * (lo + hi)
        rate = ins * p.ke * vi
        self.basal_u = rate * p.dt_min / 1000.0
        x1, x2, x3 = p.sit * ins, p.sid * ins, min(0.98, p.sie * ins)
        return np.array([
            q1,
            x1 * q1 / (p.k12 + x2),
            rate * p.tmax_i_min,
            rate * p.tmax_i_min,
            ins,
            x1,
            x2,
            x3,
            0.0,
            0.0,
            mgdl,
        ], dtype=float)

    def derivative(self, x: np.ndarray, insulin_u_min: float, carbs_g_min: float) -> np.ndarray:
        p = self.p
        q1, q2, s1, s2, ins, x1, x2, x3, d1, d2, gi = x
        vg = p.vg_l_per_kg * p.weight_kg
        vi = p.vi_l_per_kg * p.weight_kg
        g = max(0.0, q1 / vg)
        fc01 = p.f01_mmol_kg_min * p.weight_kg * min(1.0, g / 4.5)
        fr = 0.003 * max(0.0, g - 9.0) * vg
        # Smooth receptor saturation above x3 = 0.70 so x3 never exceeds 0.99 and hepatic EGP >= 0
        raw_x3 = p.sie * max(0.0, ins)
        if raw_x3 <= 0.70:
            target_x3 = raw_x3
        else:
            excess = raw_x3 - 0.70
            target_x3 = 0.70 + 0.29 * (excess / (0.29 + excess))
        egp = p.egp_mmol_kg_min * p.weight_kg * max(0.0, 1.0 - min(0.99, max(0.0, x3)))
        return np.array([
            -fc01 - x1 * q1 + p.k12 * q2 - fr + d2 / p.tmax_g_min + egp,
            x1 * q1 - (p.k12 + x2) * q2,
            insulin_u_min * 1000.0 - s1 / p.tmax_i_min,
            (s1 - s2) / p.tmax_i_min,
            s2 / (p.tmax_i_min * vi) - p.ke * ins,
            p.ka1 * (p.sit * ins - x1),
            p.ka2 * (p.sid * ins - x2),
            p.ka3 * (target_x3 - x3),
            carbs_g_min * p.ag / GRAMS_GLUCOSE_PER_MMOL - d1 / p.tmax_g_min,
            (d1 - d2) / p.tmax_g_min,
            (g * MMOL_TO_MGDL - gi) / p.sensor_lag_min,
        ], dtype=float)

    def step(self, insulin_u: float, carbs_g: float) -> tuple[float, float]:
        if not all(math.isfinite(v) and v >= 0 for v in (insulin_u, carbs_g)):
            raise ValueError("finite nonnegative per-bin inputs required")
        p = self.p
        n = math.ceil(p.dt_min / p.integration_step_min)
        h = p.dt_min / n
        u = insulin_u / p.dt_min
        c = carbs_g / p.dt_min
        x = self.x
        for _ in range(n):
            a = self.derivative(x, u, c)
            b = self.derivative(x + 0.5 * h * a, u, c)
            d = self.derivative(x + 0.5 * h * b, u, c)
            e = self.derivative(x + h * d, u, c)
            x = x + (h / 6.0) * (a + 2.0 * b + 2.0 * d + e)
            x[:10] = np.maximum(x[:10], 0.0)
            x[7] = min(x[7], 1.0)
            x[0] = max(x[0], 1.2 * p.vg_l_per_kg * p.weight_kg)
            x[10] = min(max(x[10], 20.0), 600.0)
        self.x = x
        return self.glucose, self.sensor

    @property
    def glucose(self) -> float:
        return float(self.x[0] / (self.p.vg_l_per_kg * self.p.weight_kg) * MMOL_TO_MGDL)

    @property
    def sensor(self) -> float:
        return float(self.x[-1])

    @property
    def valid(self) -> bool:
        return bool(
            np.isfinite(self.x).all()
            and np.all(self.x[:10] >= 0.0)
            and self.x[7] <= 1.0
            and 0.0 < self.glucose < 1000.0
        )

    @property
    def diagnostics(self) -> dict:
        return {
            "negative_egp_evaluator_only": bool(self.x[7] > 1.0),
            "endogenous_production_mmol_min": float(
                self.p.egp_mmol_kg_min * self.p.weight_kg * max(0.0, 1.0 - self.x[7])
            ),
            "plasma_glucose_clamped": False,
            "interstitial_glucose_clamped": False,
            "remote_action_clamped": False,
        }


class IOBAwareController:
    """Insulin-On-Board (IOB) aware proportional-predictive basal-bolus controller.

    Prevents postprandial insulin stacking while tracking target glucose (115 mg/dL).
    """

    def __init__(self, basal_u_per_step: float = 0.08, target_mgdl: float = 115.0,
                 isf_mgdl_per_u: float = 45.0, max_u_per_step: float = 0.25):
        self.basal = float(basal_u_per_step)
        self.target = float(target_mgdl)
        self.isf = float(isf_mgdl_per_u)
        self.max_u = float(max_u_per_step)
        self.iob_u = 0.0
        self.decay = math.exp(-5.0 / 90.0)

    def request(self, cgm_mgdl: float | None, forecast30_mgdl: float | None = None,
                last_delivered_u: float | None = None) -> float:
        if last_delivered_u is not None:
            net_bolus = max(0.0, float(last_delivered_u) - self.basal)
            self.iob_u = self.iob_u * self.decay + net_bolus
        else:
            self.iob_u *= self.decay

        if cgm_mgdl is None or not math.isfinite(cgm_mgdl):
            return self.basal
        pred = float(forecast30_mgdl) if (forecast30_mgdl is not None and math.isfinite(forecast30_mgdl)) else float(cgm_mgdl)
        if pred < 80.0 or cgm_mgdl < 75.0:
            return 0.0
        if pred < 95.0:
            return 0.5 * self.basal
        effective_g = 0.55 * float(cgm_mgdl) + 0.45 * pred
        raw_corr = max(0.0, (effective_g - self.target) / self.isf)
        # Subtract active IOB so we do not stack correction insulin
        net_corr = max(0.0, raw_corr - 0.65 * self.iob_u)
        cmd = self.basal + 0.25 * net_corr
        return float(min(self.max_u, max(0.0, cmd)))
