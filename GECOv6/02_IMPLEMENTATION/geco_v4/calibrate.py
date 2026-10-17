"""Per-participant twin calibration, validation and threshold freezing.

Sequence (never reordered):
  1. fit physiological parameters on the calibration window (benign data only);
  2. validate forecast error and standardised-innovation statistics on the
     validation window;
  3. choose the CUSUM threshold on the validation window so that benign
     alarm episodes do not exceed the pre-registered budget;
  4. freeze before separate evaluation of the previously exposed internal test window.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field

import numpy as np

from .datasets import ParticipantSeries, chronological_split
from .delivery import DeliveryCalibration
from .detectors import TwoSidedCUSUM
from .hal import VirtualBalanceTruthNode, VirtualSyringePump
from .physiology import TwinParams, ForecastPolicy, fit_participant_detailed, evaluate_causal_forecasts, simulated_isf


@dataclass
class TwinValidation:
    participant: str
    cal_days: float
    val_days: float
    test_days: float
    rmse30_cal: float
    rmse30_val: float
    z_mean_val: float
    z_std_val: float
    z_lag1_autocorr_val: float
    coverage95_val: float
    cusum_drift: float
    cusum_threshold: float
    benign_alarm_episodes_per_day_val: float
    ar1_rho: float
    z_lag1_autocorr_val_whitened: float
    sigma6_mgdl: float
    cusum6_threshold: float
    innovation_inflation: float
    isf_mgdl_per_u: float
    params: dict
    forecast_policy: dict = field(default_factory=dict)
    threshold_result: dict = field(default_factory=dict)
    threshold6_result: dict = field(default_factory=dict)
    fit_diagnostics: dict = field(default_factory=dict)
    split_provenance: dict = field(default_factory=dict)
    forecast_metrics_cal: dict = field(default_factory=dict)
    forecast_metrics_val: dict = field(default_factory=dict)
    alarm_summary_val: dict = field(default_factory=dict)
    empirical_coverage_val: dict = field(default_factory=dict)
    selection_rule: str = "V6: tune RMSE; ties persistence, trend, mechanistic"
    r_std: float = 9.0


def alarm_episode_indices(z, drift, threshold):
    c = TwoSidedCUSUM(drift=drift,threshold=threshold)
    indices = []
    for k,v in enumerate(z):
        c.update(float(v) if np.isfinite(v) else None)
        if c.last_alarm and np.isfinite(v): indices.append(k)
    return indices


def alarm_summary(z, drift, threshold, dt_min=5.0):
    z = np.asarray(z,dtype=float)
    idx = alarm_episode_indices(z,drift,threshold)
    observed = int(np.isfinite(z).sum())
    days = len(z)*dt_min/1440.
    observed_days = observed*dt_min/1440.
    return {"alarm_count":len(idx),"alarm_indices":idx,"slots":len(z),"observed_slots":observed,
            "coverage":observed/max(1,len(z)),"calendar_days":days,"observed_equivalent_days":observed_days,
            "episodes_per_calendar_day":len(idx)/days if days else None,
            "episodes_per_observed_equivalent_day":len(idx)/observed_days if observed_days else None}


def cusum_episodes_per_day(z, drift, threshold, dt_min=5.0):
    value = alarm_summary(z,drift,threshold,dt_min)["episodes_per_calendar_day"]
    return float(value) if value is not None else float("nan")


def search_threshold(z_val, drift, target_episodes_per_day, candidates=None):
    """Return explicit feasibility and coverage; never disguise a failed search."""
    z_val = np.asarray(z_val,dtype=float)
    candidates = np.arange(4.,128.5,.5) if candidates is None else np.asarray(candidates,dtype=float)
    if z_val.ndim!=1 or np.isinf(z_val).any(): raise ValueError("z must be a vector without infinities")
    if not len(candidates) or not np.isfinite(candidates).all() or np.any(candidates<=0) or np.any(np.diff(candidates)<=0):
        raise ValueError("threshold candidates must be finite, positive, strictly increasing")
    if not np.isfinite(target_episodes_per_day) or target_episodes_per_day<0: raise ValueError("invalid alarm budget")
    count = int(np.isfinite(z_val).sum())
    result = {"feasible":False,"threshold":None,"target_episodes_per_calendar_day":target_episodes_per_day,
              "candidate_min":float(candidates[0]),"candidate_max":float(candidates[-1]),
              "observed_slots":count,"slots":len(z_val),"coverage":count/max(1,len(z_val)),"search":[]}
    if len(z_val)==0 or count==0 or count/len(z_val)<.5:
        result["reason"] = "insufficient_observed_channel_coverage"
        return result
    chosen = None
    for h in candidates:
        a = alarm_summary(z_val,drift,float(h))
        result["search"].append({"threshold":float(h),"alarm_count":a["alarm_count"],
                                 "episodes_per_calendar_day":a["episodes_per_calendar_day"]})
        if chosen is None and a["episodes_per_calendar_day"]<=target_episodes_per_day:
            chosen = (float(h),a)
    if chosen is None:
        result["reason"] = "no_candidate_meets_budget"
    else:
        result.update(feasible=True,threshold=chosen[0],achieved=chosen[1],reason="budget_met_on_tune_only")
    return result


def freeze_threshold(z_val, drift, target_episodes_per_day, candidates=None):
    result = search_threshold(z_val,drift,target_episodes_per_day,candidates)
    if not result["feasible"]: raise ValueError("threshold calibration infeasible: "+result["reason"])
    return result["threshold"]


def calibration_split(series):
    """Exact chronological 50/25/25 split; no day-flooring to an empty window."""
    n = len(series.cgm)
    a,b = int(.5*n),int(.75*n)
    return series.slice(0,a),series.slice(a,b),series.slice(b,n)


def split_provenance(series):
    n = len(series.cgm); a,b = int(.5*n),int(.75*n)
    out = {"rule":"floor(0.50N),floor(0.75N); disjoint chronological windows",
           "holdout_status":"previously exposed internal test; not external", "windows":{}}
    for name,start,stop in (("fit",0,a),("tune",a,b),("test",b,n)):
        y = series.cgm[start:stop]
        origins = np.arange(max(0,len(y)-6))
        pairs = int(np.sum((origins>=36)&np.isfinite(y[origins])&np.isfinite(y[origins+6])))
        out["windows"][name] = {"start_index":start,"stop_index_exclusive":stop,"slots":len(y),
                                 "first_timestamp":str(series.timestamps[start]) if len(y) else None,
                                 "last_timestamp":str(series.timestamps[stop-1]) if len(y) else None,
                                 "observed_cgm":int(np.isfinite(y).sum()),
                                 "cgm_coverage":float(np.isfinite(y).mean()) if len(y) else 0.,
                                 "eligible_forecast_pairs":pairs}
    return out


def eligibility_report(series):
    provenance = split_provenance(series)
    reasons = []
    for name,w in provenance["windows"].items():
        if w["slots"] < (288 if name=="fit" else 144): reasons.append(name+":too_short")
        if w["cgm_coverage"]<.5: reasons.append(name+":observed_cgm_below_50pct")
        if w["eligible_forecast_pairs"]<50: reasons.append(name+":fewer_than_50_forecast_pairs")
    return {"eligible":not reasons,"reasons":reasons,"split_provenance":provenance}


def _lag1(z):
    z = np.asarray(z)
    mask = np.isfinite(z[:-1])&np.isfinite(z[1:])
    if mask.sum()<10 or np.std(z[:-1][mask])<1e-12 or np.std(z[1:][mask])<1e-12: return 0.
    return float(np.corrcoef(z[:-1][mask],z[1:][mask])[0,1])


def select_forecast_policy(metrics):
    """No test data accepted by this selection function."""
    best_name,best_rmse = None,float("inf")
    for name in ("persistence","trend","mechanistic"):
        rmse = metrics[name]["rmse"]
        if np.isfinite(rmse) and rmse<best_rmse-1e-9: best_name,best_rmse=name,rmse
    if best_name is None: raise ValueError("no finite validation forecasts")
    return best_name


def _due_errors(evaluation, kind, n):
    j = ("mechanistic","persistence","trend").index(kind)
    e = np.full(n,np.nan)
    e[evaluation["origins"]+6] = -evaluation["errors"][:,j]
    return e


def calibrate_participant(series, drift=.5, target_fa_per_day=1., max_iter=80):
    eligibility = eligibility_report(series)
    if not eligibility["eligible"]: raise ValueError("ineligible: "+str(eligibility["reasons"]))
    cal,val,test = calibration_split(series)
    hold = float(np.median(cal.basal))
    fit = fit_participant_detailed(cal.cgm,cal.insulin,cal.carbs,max_iter=max_iter,hold_insulin_u=hold)
    params = fit.params
    policy = ForecastPolicy(hold_insulin_u=hold)
    fit0 = evaluate_causal_forecasts(params,cal.cgm,cal.insulin,cal.carbs,forecast_policy=policy)
    rho = float(np.clip(_lag1(fit0["z"]),0.,.98))
    fitw = evaluate_causal_forecasts(params,cal.cgm,cal.insulin,cal.carbs,forecast_policy=policy,ar1_rho=rho)
    zw = fitw["z"][np.isfinite(fitw["z"])]
    if len(zw)<50: raise ValueError("insufficient finite fit innovations")
    inflation = float(max(1e-6,(np.quantile(np.abs(zw),.95)/1.96)**2))
    val0 = evaluate_causal_forecasts(params,val.cgm,val.insulin,val.carbs,forecast_policy=policy,inflation=inflation)
    vale = evaluate_causal_forecasts(params,val.cgm,val.insulin,val.carbs,forecast_policy=policy,ar1_rho=rho,inflation=inflation)
    chosen = select_forecast_policy(vale["metrics"])
    policy = ForecastPolicy(kind=chosen,hold_insulin_u=hold)
    ecal = _due_errors(fit0,chosen,len(cal.cgm))
    sigma6 = float(max(1.,np.quantile(np.abs(ecal[np.isfinite(ecal)]),.95)/1.96))
    z6 = _due_errors(vale,chosen,len(val.cgm))/sigma6
    result = search_threshold(vale["z"],drift,target_fa_per_day*.5)
    result6 = search_threshold(z6,drift,target_fa_per_day*.5)
    if not result["feasible"] or not result6["feasible"]:
        exc = ValueError("participant threshold search infeasible")
        exc.fit_diagnostics = {"fit":fit.diagnostics,"params":asdict(params),
                               "forecast_policy":asdict(policy),"threshold_result":result,"threshold6_result":result6}
        raise exc
    a1 = result["achieved"]; a6 = result6["achieved"]
    union = sorted(set(a1["alarm_indices"])|set(a6["alarm_indices"]))
    z = vale["z"][np.isfinite(vale["z"])]
    v = TwinValidation(participant=series.participant_id,cal_days=cal.n_days,val_days=val.n_days,test_days=test.n_days,
        rmse30_cal=fit0["metrics"][chosen]["rmse"],rmse30_val=vale["metrics"][chosen]["rmse"],
        z_mean_val=float(np.mean(z)),z_std_val=float(np.std(z)),z_lag1_autocorr_val=_lag1(val0["z"]),
        coverage95_val=float(np.mean(np.abs(z)<=1.96)),cusum_drift=drift,cusum_threshold=result["threshold"],
        benign_alarm_episodes_per_day_val=a1["episodes_per_calendar_day"],ar1_rho=rho,
        z_lag1_autocorr_val_whitened=_lag1(vale["z"]),sigma6_mgdl=sigma6,cusum6_threshold=result6["threshold"],
        innovation_inflation=inflation,isf_mgdl_per_u=simulated_isf(params),params=asdict(params),
        forecast_policy=asdict(policy),threshold_result=result,threshold6_result=result6,fit_diagnostics=fit.diagnostics,
        split_provenance=eligibility["split_provenance"],forecast_metrics_cal=fit0["metrics"],forecast_metrics_val=vale["metrics"],
        alarm_summary_val={"innovation":a1,"forecast":a6,"union_count":len(union),"union_indices":union,
                           "union_episodes_per_calendar_day":len(union)/val.n_days},
        empirical_coverage_val={"innovation_95":float(np.mean(np.abs(z)<=1.96)),
                                "selected_forecast_95":float(np.mean(np.abs(z6[np.isfinite(z6)])<=1.96)),
                                "innovation_channel_coverage":a1["coverage"],"forecast_channel_coverage":a6["coverage"]})
    return params,v,test


def calibrate_delivery(grams_per_unit: float = 0.1005, n: int = 120, seed: int = 7) -> DeliveryCalibration:
    """Benign delivery calibration on the (virtual) bench: commanded units vs measured mass."""
    rng = np.random.default_rng(seed)
    pump = VirtualSyringePump(grams_per_unit=grams_per_unit, rng=np.random.default_rng(seed + 1), max_units_per_step=10.0)
    truth = VirtualBalanceTruthNode(pump, rng=np.random.default_rng(seed + 2))
    truth.read(0.0)
    expected, measured = [], []
    t = 0.0
    for i in range(n):
        u = float(rng.choice([0.0, 0.05, 0.08, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 4.0]))
        pump.execute(f"cal{i}", u, t)
        pump.tick(t, 300.0)
        r = truth.read(t + 270.0)
        expected.append(u * grams_per_unit)
        measured.append(r["delta_g"])
        t += 300.0
    return DeliveryCalibration.from_benign_runs(np.array(expected), np.array(measured), grams_per_unit, truth.resolution_g)
