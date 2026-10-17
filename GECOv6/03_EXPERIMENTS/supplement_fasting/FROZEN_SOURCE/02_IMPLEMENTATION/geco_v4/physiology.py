"""Physiology and treatment-response twin.

A compact nonlinear glucose-insulin-carbohydrate model with an explicit interstitial
compartment (CGM lag), an extended Kalman filter that produces *standardised*
innovations rather than raw mg/dL residuals, and per-participant calibration from
benign data only.

This is a research twin. It is NOT a clinical dosing model. Its role in GECO is to
say how surprised the twin is by the reported glucose, with a calibrated
uncertainty, and to give the safety kernel a bounded short-horizon forecast.

State  x = [G, X, I, Q, Gi]
  G  plasma glucose (mg/dL)
  X  remote insulin action (1/min)
  I  plasma insulin above zero (arbitrary, driven by delivered units)
  Q  gut carbohydrate (g)
  Gi interstitial glucose (mg/dL) - what the CGM sees, lagged by tau_i
Input u = [insulin_u (U per sample), carbs_g (g per sample)]
Output y = Gi + v
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import Iterable

import numpy as np
from .numerics import finite_number, positive_number


@dataclass
class TwinParams:
    dt_min: float = 5.0
    sub_steps: int = 5
    gb: float = 120.0          # reference glucose (mg/dL), used only for initialisation
    egp: float = 1.2           # endogenous glucose production (mg/dL/min) - fitted
    p1: float = 0.006          # glucose effectiveness (1/min)
    p2: float = 0.020          # insulin action decay (1/min)
    p3: float = 6.0e-5         # insulin action gain (1/min per insulin unit-state)
    ki: float = 0.030          # plasma insulin decay (1/min)
    ku: float = 6.0            # plasma insulin per delivered unit
    ib: float = 3.2            # basal plasma-insulin level (insulin action is relative to basal)
    ka: float = 0.025          # gut absorption (1/min)
    kc: float = 0.40           # glucose rise per gram absorbed per min (mg/dL/min/g)
    tau_i: float = 9.0         # interstitial lag (min)

    def __post_init__(self):
        for name in ("dt_min", "gb", "p1", "p2", "ki", "ku", "ka", "tau_i"):
            positive_number(getattr(self, name), name)
        for name in ("egp", "p3", "ib", "kc"):
            finite_number(getattr(self, name), name, minimum=0)
        if isinstance(self.sub_steps, bool) or not isinstance(self.sub_steps, int) or self.sub_steps < 1:
            raise ValueError("sub_steps must be a positive integer")

    def vector(self) -> np.ndarray:
        return np.array([self.egp, self.p1, self.kc], dtype=float)

    def with_vector(self, v: Iterable[float]) -> "TwinParams":
        egp, p1, kc = [float(x) for x in v]
        d = asdict(self)
        d.update(egp=egp, p1=p1, kc=kc)
        return TwinParams(**d)

    def with_p3(self, p3: float) -> "TwinParams":
        d = asdict(self)
        d.update(p3=float(p3))
        return TwinParams(**d)


class GlucoseModel:
    N_STATES = 5

    def __init__(self, params: TwinParams | None = None):
        self.p = params or TwinParams()

    def initial_state(self, glucose: float, basal_u_per_sample: float = 0.0) -> np.ndarray:
        finite_number(glucose, "initial glucose")
        finite_number(basal_u_per_sample, "initial basal", minimum=0)
        p = self.p
        i_ss = p.ku * basal_u_per_sample / max(p.ki * p.dt_min, 1e-9) if basal_u_per_sample > 0 else p.ib
        x_ss = p.p3 * (i_ss - p.ib) / max(p.p2, 1e-9)
        return np.array([glucose, x_ss, i_ss, 0.0, glucose], dtype=float)

    def step(self, x: np.ndarray, insulin_u: float, carbs_g: float) -> np.ndarray:
        self._validate_input(x, insulin_u, carbs_g)
        return _transition(np.asarray(x, dtype=float), insulin_u, carbs_g, _parameter_array(self.p), False)[0]

    def step_with_jacobian(self, x, insulin_u, carbs_g):
        self._validate_input(x, insulin_u, carbs_g)
        return _transition(np.asarray(x, dtype=float), insulin_u, carbs_g, _parameter_array(self.p), True)

    def _validate_input(self, x, insulin_u, carbs_g):
        if np.shape(x) != (5,) or not np.isfinite(x).all():
            raise ValueError("model state must contain five finite values")
        finite_number(insulin_u, "model insulin input", minimum=0)
        finite_number(carbs_g, "model carbohydrate input", minimum=0)


# Optional compilation accelerates the identical arithmetic used by streaming and
# array evaluation. No fastmath; the pure Python fallback has the same interface.
try:
    from numba import njit as _njit
except ImportError:
    def _njit(*args, **kwargs):
        return lambda f: f


def _parameter_array(p):
    return np.array([p.dt_min, p.sub_steps, p.gb, p.egp, p.p1, p.p2,
                     p.p3, p.ki, p.ku, p.ib, p.ka, p.kc, p.tau_i], dtype=float)


@_njit(cache=True)
def _transition(x, insulin_u, carbs_g, p, jacobian=True):
    h = p[0] / int(p[1])
    g, xa, ins, gut, gi = x
    F = np.eye(5)
    for _ in range(int(p[1])):
        if jacobian:
            A = np.eye(5)
            A[0, 0] = 1.0 - h * (p[4] + (xa if g > 30.0 else 0.0))
            A[0, 1] = -h * max(g, 30.0)
            A[0, 3] = h * p[11] * p[10]
            A[1, 1], A[1, 2] = 1.0 - h*p[5], h*p[6]
            A[2, 2], A[3, 3] = 1.0-h*p[7], 1.0-h*p[10]
            A[4, 0], A[4, 4] = h/p[12], 1.0-h/p[12]
        gn = g + h * (p[3] - p[4]*g - xa*max(g, 30.0) + p[11]*p[10]*gut)
        xn = xa + h * (-p[5]*xa + p[6]*(ins-p[9]))
        inn = ins + h * (-p[7]*ins + p[8]*insulin_u/p[0])
        qn = gut + h * (-p[10]*gut + carbs_g/p[0])
        gin = gi + h*(g-gi)/p[12]
        if jacobian:
            if gn <= 20.0 or gn >= 600.0: A[0, :] = 0.0
            if xn <= -0.5*p[4]: A[1, :] = 0.0
            if inn <= 0.0: A[2, :] = 0.0
            if qn <= 0.0: A[3, :] = 0.0
            if gin <= 20.0 or gin >= 600.0: A[4, :] = 0.0
            F = A @ F
        g, xa = min(max(gn, 20.0), 600.0), max(xn, -0.5*p[4])
        ins, gut, gi = max(inn, 0.0), max(qn, 0.0), min(max(gin, 20.0), 600.0)
    return np.array([g, xa, ins, gut, gi]), F


@_njit(cache=True)
def _guard_covariance(P):
    if not np.isfinite(P).all():
        return P, False
    scale = max(1.0, np.max(np.abs(P)))
    if np.max(np.abs(P-P.T)) > 1e-7*scale:
        return P, False
    P = (P+P.T)*0.5
    eig, V = np.linalg.eigh(P)
    if eig[0] < -1e-8*scale:
        return P, False
    if eig[0] < 0.0:
        P = (V * np.maximum(eig, 0.0)) @ V.T
        P = (P+P.T)*0.5
    return P, True


@_njit(cache=True)
def _joseph_update(x_pred, P_pred, observation, r_var):
    # R is nominal measurement variance. Anomaly inflation never enters this step.
    r = r_var * (1.6 if x_pred[4] < 70.0 else (1.5 if x_pred[4] > 250.0 else 1.0))
    s = P_pred[4, 4] + r
    innovation = observation - x_pred[4]
    K = P_pred[:, 4] / s
    A = np.eye(5)
    A[:, 4] -= K
    P = A @ P_pred @ A.T + r * np.outer(K, K)
    return x_pred + K*innovation, (P+P.T)*0.5, innovation, np.sqrt(s)


@dataclass(frozen=True)
class ForecastPolicy:
    """A frozen causal CGM forecast policy; hold amount is learned on fit data."""
    kind: str = "mechanistic"
    hold_insulin_u: float = 0.0
    trend_window: int = 4
    trend_damping: float = 0.5
    slope_limit_mgdl_min: float = 3.0

    def __post_init__(self):
        if self.kind not in ("mechanistic", "persistence", "trend"):
            raise ValueError("unknown forecast policy")
        finite_number(self.hold_insulin_u, "hold_insulin_u", minimum=0)
        finite_number(self.trend_damping, "trend_damping", minimum=0)
        positive_number(self.slope_limit_mgdl_min, "slope_limit_mgdl_min")
        if not isinstance(self.trend_window, int) or not 2 <= self.trend_window <= 32:
            raise ValueError("trend_window must be an integer from 2 to 32")


@_njit(cache=True)
def _forecast_value(x, history, p, horizon, kind, hold, damping, slope_limit):
    if kind == 0 or len(history) == 0:
        xf = x.copy()
        for _ in range(horizon):
            xf = _transition(xf, hold, 0.0, p, False)[0]
        return xf[4]
    value = history[-1]
    if kind == 2 and len(history) >= 2:
        n = len(history)
        center = (n-1)*0.5
        numerator, denominator = 0.0, 0.0
        for j in range(n):
            t = (j-center)*p[0]
            numerator += t*history[j]
            denominator += t*t
        slope = min(max(numerator/denominator, -slope_limit), slope_limit)
        value += damping*slope*horizon*p[0]
    return min(max(value, 20.0), 600.0)


@dataclass
class TwinOutput:
    predicted_cgm: float
    innovation: float
    innovation_std: float
    standardized_innovation: float
    state: np.ndarray
    quality: str
    innovation_valid: bool = True


class PhysiologyTwin:
    """Joseph-form EKF with independently calibrated anomaly normalization.

    update(y_k, u_{k-1}, c_{k-1}) consumes the preceding interval's events.
    forecast(6) and the due-residual buffer use exactly the same frozen policy.
    """
    H = np.array([[0., 0., 0., 0., 1.]])

    def __init__(self, params=None, r_std=9.0, forecast_policy=None):
        positive_number(r_std, "r_std")
        self.model = GlucoseModel(params)
        self.p = self.model.p
        self._pv = _parameter_array(self.p)
        self.r_var = float(r_std)**2
        self.q_cov = np.diag([9., 1e-8, .4, 12., 2.])
        self.forecast_policy = (ForecastPolicy(**forecast_policy) if isinstance(forecast_policy, dict)
                                else forecast_policy or ForecastPolicy())
        self.ar1_rho, self.innovation_inflation, self.sigma6 = 0.0, 1.0, 25.0
        self.forecast_horizon, self.max_missing_steps = 6, 12
        self.numerical_resets = 0
        self.last_reset_reason = None
        self.reset(self.p.gb, self.forecast_policy.hold_insulin_u)
        self.initialised = False
        self.last_reported = None

    def configure_calibration(self, calibration):
        """Accept a validation/config mapping; ignore unrelated detector settings."""
        calibration = calibration.get("validation", calibration)
        self.ar1_rho = float(calibration.get("ar1_rho", self.ar1_rho))
        self.innovation_inflation = float(calibration.get("innovation_inflation", self.innovation_inflation))
        self.sigma6 = float(calibration.get("sigma6_mgdl", calibration.get("sigma6", self.sigma6)))
        if "forecast_policy" in calibration:
            policy = calibration["forecast_policy"]
            self.forecast_policy = ForecastPolicy(**policy) if isinstance(policy, dict) else policy
        self._validate_calibration()
        return self

    def _validate_calibration(self):
        positive_number(self.innovation_inflation, "innovation_inflation")
        positive_number(self.sigma6, "sigma6")
        finite_number(self.ar1_rho, "ar1_rho", minimum=0)
        if self.ar1_rho >= 1: raise ValueError("ar1_rho must be less than 1")

    def reset(self, glucose, basal_u_per_sample=0.0):
        self.x = self.model.initial_state(glucose, basal_u_per_sample)
        self.P = np.diag([100., 1e-6, 20., 40., 100.])
        self.initialised = True
        self.missing_streak, self.frozen_streak, self._k = 0, 0, 0
        self.last_reported = float(glucose)
        self._history = [float(glucose)]
        self._last_z = None
        self._forecast_buffer = []
        self.last_forecast_residual_z = None
        self.last_reset_reason = "explicit"

    def _jacobian(self, x, insulin_u, carbs_g):
        return self.model.step_with_jacobian(x, insulin_u, carbs_g)[1]

    def _range_r(self, predicted_cgm):
        return self.r_var*(1.6 if predicted_cgm < 70 else (1.5 if predicted_cgm > 250 else 1.0))

    def update(self, cgm, insulin_u, carbs_g):
        if cgm is not None and np.isnan(cgm): cgm = None
        if cgm is not None: finite_number(cgm, "CGM")
        finite_number(insulin_u, "model insulin input", minimum=0)
        finite_number(carbs_g, "model carbohydrate input", minimum=0)
        self._validate_calibration()
        self.last_forecast_residual_z = None
        self._k += 1
        if np.shape(self.P) == (5, 5):
            P, covariance_ok = _guard_covariance(np.asarray(self.P, dtype=float))
        else:
            P, covariance_ok = self.P, False
        state_ok = np.shape(self.x) == (5,) and np.isfinite(self.x).all()
        reason = None
        if not covariance_ok or not state_ok: reason = "numerical_reset"
        elif cgm is not None and not self.initialised: reason = "initializing"
        elif cgm is not None and self.missing_streak >= self.max_missing_steps: reason = "gap_reset"
        if reason is not None:
            k = self._k
            self.reset(cgm if cgm is not None else self.p.gb, self.forecast_policy.hold_insulin_u)
            self._k, self.last_reset_reason = k, reason
            if reason == "numerical_reset": self.numerical_resets += 1
            if cgm is None:
                self.initialised = False
                self.last_reported = None
                self._history = []
                self.missing_streak = 1
            else:
                self._forecast_buffer.append((self._k+self.forecast_horizon, self.forecast(self.forecast_horizon)))
            return TwinOutput(float(self.x[4]), 0., float(np.sqrt(self.r_var)), 0., self.x.copy(),
                              reason if cgm is not None else "missing", False)
        self.P = P
        due = [f for k, f in self._forecast_buffer if k == self._k]
        self._forecast_buffer = [(k, f) for k, f in self._forecast_buffer if k > self._k]
        if cgm is not None and due:
            self.last_forecast_residual_z = float((cgm-due[0])/self.sigma6)
        xp, F = _transition(self.x, insulin_u, carbs_g, self._pv, True)
        Pp = F @ self.P @ F.T + self.q_cov
        if cgm is None:
            self.x, self.P = xp, Pp
            self.missing_streak += 1
            self._last_z, self._history = None, []
            self.last_reported, self.frozen_streak = None, 0
            return TwinOutput(float(xp[4]), 0., float(np.sqrt(Pp[4,4]+self._range_r(xp[4]))),
                              0., self.x.copy(), "missing", False)
        self.x, self.P, innovation, nominal_std = _joseph_update(xp, Pp, cgm, self.r_var)
        guarded, ok = _guard_covariance(self.P)
        if not ok or not np.isfinite(self.x).all():
            k = self._k
            self.reset(cgm, self.forecast_policy.hold_insulin_u)
            self._k, self.last_reset_reason = k, "numerical_reset"
            self.numerical_resets += 1
            self._forecast_buffer.append((k+self.forecast_horizon, self.forecast(self.forecast_horizon)))
            return TwinOutput(float(self.x[4]), 0., float(np.sqrt(self.r_var)), 0.,
                              self.x.copy(), "numerical_reset", False)
        self.P = guarded
        self.missing_streak = 0
        quality = "ok"
        self.frozen_streak = (self.frozen_streak+1 if self.last_reported is not None and abs(cgm-self.last_reported)<1e-9 else 0)
        if self.frozen_streak >= 6: quality = "frozen"
        elif self.last_reported is not None and abs(cgm-self.last_reported)>4*self.p.dt_min: quality = "implausible_rate"
        self.last_reported = float(cgm)
        self._history = (self._history+[float(cgm)])[-self.forecast_policy.trend_window:]
        std = nominal_std*np.sqrt(self.innovation_inflation)
        raw_z = innovation/std
        z = raw_z if self._last_z is None else (raw_z-self.ar1_rho*self._last_z)/np.sqrt(1-self.ar1_rho**2)
        self._last_z = raw_z
        self._forecast_buffer.append((self._k+self.forecast_horizon, self.forecast(self.forecast_horizon)))
        return TwinOutput(float(xp[4]), float(innovation), float(std), float(z), self.x.copy(), quality, True)

    def forecast(self, horizon_steps, planned_insulin_u=None):
        """Selected causal CGM forecast, matching the due-residual channel.

        A supplied plan explicitly overrides the policy with a mechanistic forecast;
        the default uses the frozen policy, never a repeated bolus or future log.
        """
        if isinstance(horizon_steps, bool) or not isinstance(horizon_steps, (int, np.integer)) or horizon_steps < 0:
            raise ValueError("horizon_steps must be a nonnegative integer")
        policy = self.forecast_policy
        hold = policy.hold_insulin_u if planned_insulin_u is None else planned_insulin_u
        finite_number(hold, "planned insulin", minimum=0)
        kind = (0 if planned_insulin_u is not None else {"mechanistic":0,"persistence":1,"trend":2}[policy.kind])
        return float(_forecast_value(self.x, np.asarray(self._history), self._pv, horizon_steps,
                                     kind, float(hold), policy.trend_damping, policy.slope_limit_mgdl_min))

    def forecast_series(self, horizon_steps, planned_insulin_u=None):
        return [self.forecast(k, planned_insulin_u) for k in range(1, horizon_steps+1)]

    @property
    def insulin_on_board_proxy(self):
        return float(self.x[2]/self.p.ku)


def _validate_arrays(cgm, insulin, carbs):
    cgm, insulin, carbs = [np.asarray(a, dtype=float) for a in (cgm, insulin, carbs)]
    if cgm.ndim != 1 or cgm.shape != insulin.shape or cgm.shape != carbs.shape or not len(cgm):
        raise ValueError("CGM, insulin, carbs must be nonempty aligned one-dimensional arrays")
    if np.isinf(cgm).any() or not np.isfinite(insulin).all() or not np.isfinite(carbs).all():
        raise ValueError("inputs must be finite; only CGM may contain missing NaN")
    if np.any(insulin<0) or np.any(carbs<0): raise ValueError("input amounts must be nonnegative")
    return cgm, insulin, carbs


@_njit(cache=True)
def _batch_filter(cgm, insulin, carbs, p, hold, r_var, horizon, rho, inflation, trend_window, damping, slope_limit):
    """Array execution of the same streaming transition/Joseph/forecast functions."""
    n = len(cgm)
    predictions = np.full((n,3), np.nan)
    innov, z = np.full(n, np.nan), np.full(n, np.nan)
    x = np.array([p[2], 0., p[9], 0., p[2]])
    P = np.diag(np.array([100.,1e-6,20.,40.,100.]))
    Q = np.diag(np.array([9.,1e-8,.4,12.,2.]))
    history = np.empty(trend_window)
    nh, gap, initialized = 0, 0, False
    previous_z = np.nan
    reset_flags = np.zeros(n, dtype=np.int64)
    for k in range(n):
        y = cgm[k]
        P, good = _guard_covariance(P)
        finite = np.isfinite(y)
        reset = (not good or not np.isfinite(x).all() or (finite and (not initialized or gap>=12)))
        if reset:
            glucose = y if finite else p[2]
            ins_ss = p[8]*hold/(p[7]*p[0]) if hold>0 else p[9]
            x = np.array([glucose,p[6]*(ins_ss-p[9])/p[5],ins_ss,0.,glucose])
            P = np.diag(np.array([100.,1e-6,20.,40.,100.]))
            nh, gap, initialized, previous_z = 0, 0, finite, np.nan
            reset_flags[k] = 1
        else:
            u = insulin[k-1] if k>0 else 0.
            c = carbs[k-1] if k>0 else 0.
            xp, F = _transition(x, u, c, p, True)
            Pp = F @ P @ F.T + Q
            if finite:
                x, P, e, sd = _joseph_update(xp, Pp, y, r_var)
                innov[k] = e
                raw_z = e/(sd*np.sqrt(inflation))
                z[k] = raw_z if not np.isfinite(previous_z) else (raw_z-rho*previous_z)/np.sqrt(1-rho*rho)
                previous_z = raw_z
                gap = 0
            else:
                x, P = xp, Pp
        if not finite:
            gap += 1
            nh, previous_z = 0, np.nan
            continue
        if nh == trend_window:
            for j in range(trend_window-1): history[j] = history[j+1]
            nh -= 1
        history[nh] = y
        nh += 1
        for kind in range(3):
            predictions[k,kind] = _forecast_value(x, history[:nh], p, horizon, kind, hold, damping, slope_limit)
    return predictions, innov, z, reset_flags


def evaluate_causal_forecasts(params, cgm, insulin, carbs, *, forecast_policy=None,
                              horizon_steps=6, r_std=9., warmup=36, ar1_rho=0., inflation=1.):
    """Score all three causal policies on one shared origin mask; never fit here."""
    cgm, insulin, carbs = _validate_arrays(cgm, insulin, carbs)
    policy = ForecastPolicy(**forecast_policy) if isinstance(forecast_policy, dict) else forecast_policy or ForecastPolicy()
    positive_number(r_std, "r_std"); positive_number(inflation, "inflation")
    if not 0 <= ar1_rho < 1: raise ValueError("rho outside [0,1)")
    pred, innov, z, reset = _batch_filter(cgm, insulin, carbs, _parameter_array(params),
                                        policy.hold_insulin_u, r_std*r_std, horizon_steps,
                                        ar1_rho, inflation, policy.trend_window,
                                        policy.trend_damping, policy.slope_limit_mgdl_min)
    origins = np.arange(max(0, len(cgm)-horizon_steps))
    eligible = (origins>=warmup) & np.isfinite(cgm[origins]) & np.isfinite(cgm[origins+horizon_steps])
    origins = origins[eligible]
    errors = pred[origins] - cgm[origins+horizon_steps,None]
    metrics = {}
    for j, name in enumerate(("mechanistic","persistence","trend")):
        e = errors[:,j]
        metrics[name] = {"rmse": float(np.sqrt(np.mean(e*e))) if len(e) else float("nan"),
                         "mae": float(np.mean(np.abs(e))) if len(e) else float("nan"),
                         "n_pairs": len(e)}
    z[:warmup] = np.nan
    innov[:warmup] = np.nan
    return {"predictions":pred,"innovations":innov,"z":z,"origins":origins,
            "errors":errors,"metrics":metrics,"reset_flags":reset,
            "pair_coverage":len(origins)/max(1,len(cgm)-warmup-horizon_steps)}


def run_open_loop_forecast_error(params, cgm, insulin, carbs, horizon_steps=6, r_std=9.,
                                 warmup=36, ar1_rho=0., inflation=1., forecast_policy=None):
    """Compatibility wrapper: V6 errors are causal; no future logged input access."""
    r = evaluate_causal_forecasts(params,cgm,insulin,carbs,horizon_steps=horizon_steps,
                                  r_std=r_std,warmup=warmup,ar1_rho=ar1_rho,
                                  inflation=inflation,forecast_policy=forecast_policy)
    policy = forecast_policy or ForecastPolicy()
    kind = policy.get("kind","mechanistic") if isinstance(policy,dict) else policy.kind
    j = ("mechanistic","persistence","trend").index(kind)
    z6 = np.full(len(cgm),np.nan)
    z6[r["origins"]+horizon_steps] = -r["errors"][:,j]
    run_open_loop_forecast_error.last_z6 = z6  # legacy only; new calibration uses explicit arrays
    return r["metrics"][kind]["rmse"],r["innovations"],r["z"]


def simulated_isf(params: TwinParams, basal_u_per_step: float | None = None, horizon_steps: int = 72) -> float:
    """Glucose drop (mg/dL) 6 h after a 1 U bolus on top of steady basal - the model's insulin sensitivity."""
    m = GlucoseModel(params)
    p = params
    if basal_u_per_step is None:
        basal_u_per_step = p.ib * p.ki * p.dt_min / p.ku
    g_ss = p.egp / max(p.p1, 1e-9)
    x = np.array([g_ss, 0.0, p.ib, 0.0, g_ss], dtype=float)
    xb = x.copy()
    for k in range(horizon_steps):
        x = m.step(x, basal_u_per_step + (1.0 if k == 0 else 0.0), 0.0)
        xb = m.step(xb, basal_u_per_step, 0.0)
    return float(xb[0] - x[0])


def p3_for_isf(params: TwinParams, isf_target: float, basal_u_per_step: float = 0.08) -> float:
    """Bisection on log p3 so that the model's 6-h drop per unit equals the target ISF."""
    lo, hi = np.log(1e-7), np.log(5e-3)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if simulated_isf(params.with_p3(np.exp(mid)), basal_u_per_step) < isf_target:
            lo = mid
        else:
            hi = mid
    return float(np.exp(0.5 * (lo + hi)))


@dataclass
class FitResult:
    params: TwinParams
    rmse: float
    diagnostics: dict = field(default_factory=dict)


def fit_participant_detailed(cgm, insulin, carbs, base=None, horizon_steps=6,
                             max_iter=80, hold_insulin_u=None):
    """Actually fit four bounded parameters using causal training forecast errors."""
    cgm, insulin, carbs = _validate_arrays(cgm,insulin,carbs)
    if np.isfinite(cgm).sum()<50: raise ValueError("fit needs at least 50 observed CGM samples")
    from scipy.optimize import least_squares
    base = base or TwinParams()
    hold = float(np.median(insulin)) if hold_insulin_u is None else float(hold_insulin_u)
    finite_number(hold,"hold_insulin_u",minimum=0)
    d = asdict(base)
    mean_g = float(np.clip(np.nanmean(cgm),80.,320.))
    d.update(gb=mean_g,ib=base.ku*hold/(base.ki*base.dt_min))
    base = TwinParams(**d)
    policy = ForecastPolicy(hold_insulin_u=hold)
    lower = np.log([80.,.0001,.05,1e-7])
    upper = np.log([320.,.03,3.,.005])
    def unpack(logv):
        equilibrium,p1,kc,p3 = np.exp(logv)
        d = asdict(base); d.update(egp=equilibrium*p1,p1=p1,kc=kc,p3=p3)
        return TwinParams(**d)
    def residual(logv):
        result = evaluate_causal_forecasts(unpack(logv),cgm,insulin,carbs,
                                           forecast_policy=policy,horizon_steps=horizon_steps)
        e = result["errors"][::6,0]
        if len(e)<8 or not np.isfinite(e).all(): raise ValueError("insufficient finite causal fit pairs")
        return e
    attempts, converged = [], []
    for kc0 in (.4,1.2):
        x0 = np.log([mean_g,.006,kc0,6e-5])
        result = least_squares(residual,x0,bounds=(lower,upper),max_nfev=max_iter,
                               ftol=.001,xtol=.001,gtol=.001)
        attempts.append({"kc_start":kc0,"success":bool(result.success),"status":int(result.status),
                         "message":str(result.message),"nfev":int(result.nfev),
                         "cost":float(result.cost),"optimality":float(result.optimality),
                         "log_parameters":result.x.tolist()})
        if result.success and np.isfinite(result.cost): converged.append(result)
    if not converged:
        error = ValueError("no optimizer-converged fit; attempts="+str(attempts))
        error.fit_diagnostics = {"attempts":attempts}
        raise error
    best = min(converged,key=lambda a:a.cost)
    params = unpack(best.x)
    all_result = evaluate_causal_forecasts(params,cgm,insulin,carbs,forecast_policy=policy)
    sv = np.linalg.svd(best.jac,compute_uv=False)
    names = ["equilibrium_glucose","p1","kc","p3"]
    diagnostics = {"method":"scipy.optimize.least_squares","objective":"causal30_rmse_every_sixth_eligible_origin",
                   "attempts":attempts,"selected_log_parameters":best.x.tolist(),
                   "bound_proximity_1pct":[names[j] for j in range(4) if min(best.x[j]-lower[j],upper[j]-best.x[j]) < .01*(upper[j]-lower[j])],
                   "jacobian_singular_values":sv.tolist(),"jacobian_condition":float(sv[0]/sv[-1]) if sv[-1]>0 else None,
                   "hold_insulin_u":hold,"fit_pairs_all":len(all_result["origins"]),
                   "fit_pairs_objective":len(all_result["origins"][::6]),
                   "identification_claim":"none; local conditioning does not establish physiological identifiability"}
    return FitResult(params,all_result["metrics"]["mechanistic"]["rmse"],diagnostics)


def fit_participant(cgm, insulin, carbs, base=None, horizon_steps=6, max_iter=80, isf_target=None):
    if isf_target is not None:
        raise ValueError("V6 does not impose an ISF clinical prior; use explicit model parameters for simulations")
    fit = fit_participant_detailed(cgm,insulin,carbs,base,horizon_steps,max_iter)
    return fit.params,fit.rmse
