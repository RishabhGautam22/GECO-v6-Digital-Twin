"""Paired parameter-unit inference and lossless provenance for study reports."""
from pathlib import Path
import csv
import json
from collections import defaultdict
import numpy as np
from .campaign import OUT,ROOT,load,dump,sha,timestamp

METRICS=["stepwise_excess_vs_clean_u","stepwise_deficit_vs_clean_u","net_emission_difference_u","longest_interruption_min","total_commanded_latch_exposure_min","recovery_latency_restricted_min","time_below54_pct","time_below70_pct","time70to180_pct","time_above250_pct","glucose_rmse_vs_clean","invalid_physiology_samples"]
CONTRASTS=[("full_manual","simple_manual"),("full_supervised","simple_supervised"),("full_supervised","full_manual"),("simple_supervised","simple_manual")]

def ci_unit(values,rng,resamples=4096):
    a=np.asarray(values,dtype=float)
    boot=a[rng.integers(0,len(a),(resamples,len(a)))].mean(axis=1)
    return float(a.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))

def summarize():
    rows=load(OUT/"RUN_RESULTS.json");failed=load(OUT/"FAILED_RUNS.json")
    groups=defaultdict(list)
    for row in rows:groups[(row["mode"],row["family"],row["condition"],row["stop_model"],row["arm"])].append(row)
    descriptive=[]
    for key,data in sorted(groups.items()):
        d={k:v for k,v in zip(("mode","family","condition","stop_model","arm"),key)}
        d.update(n_runs=len(data),n_parameter_units=len({x["unit_id"] for x in data}),runs_any_trip=sum(x["trip_count"]>0 for x in data),runs_with_invalid_physiology=sum(x["invalid_physiology_samples"]>0 for x in data),runs_recovery_censored=sum(x["recovery_censored"] for x in data))
        for field in ("negative_egp_evaluator_only_samples","plasma_glucose_clamped_samples","interstitial_glucose_clamped_samples","remote_action_clamped_samples"):
            d[field+"_mean"]=float(np.mean([x[field] for x in data]));d[field+"_total"]=sum(x[field] for x in data)
        for metric in METRICS:
            d[metric+"_mean"]=float(np.mean([x[metric] for x in data]))
            d[metric+"_min"]=min(x[metric] for x in data);d[metric+"_max"]=max(x[metric] for x in data)
        descriptive.append(d)
    contrasts=[];rng=np.random.default_rng(202609079)
    grouping=sorted({key[:-1] for key in groups})
    for key in grouping:
      for arm_a,arm_b in CONTRASTS:
        if (*key,arm_a) not in groups or (*key,arm_b) not in groups:continue
        aa={(r["unit_id"],r["seed"]):r for r in groups[(*key,arm_a)]}
        bb={(r["unit_id"],r["seed"]):r for r in groups[(*key,arm_b)]}
        common=sorted(set(aa)&set(bb));expected=set(aa)|set(bb)
        for metric in METRICS:
            units=defaultdict(list)
            for pair in common:units[pair[0]].append(aa[pair][metric]-bb[pair][metric])
            complete={k:v for k,v in units.items() if len(v)==2}
            values=[float(np.mean(v)) for _,v in sorted(complete.items())]
            if not values:continue
            mean,lower,upper=ci_unit(values,rng)
            contrasts.append({**dict(zip(("mode","family","condition","stop_model"),key)),"arm_a":arm_a,"arm_b":arm_b,"difference":"arm_a minus arm_b","metric":metric,"mean_paired_difference":mean,"ci95_low":lower,"ci95_high":upper,"n_parameter_units":len(values),"paired_seed_runs":len(common),"missing_pairs":len(expected)-len(common),"incomplete_seed_units":len(units)-len(complete),"bootstrap_resamples":4096,"unit_means":dict(zip(sorted(complete),values)),"interpretation":"Descriptive synthetic parameter-unit percentile interval; seeds averaged within each unit; not multiplicity-adjusted or patient uncertainty"})
    dump(OUT/"ARM_SUMMARIES.json",descriptive);dump(OUT/"PAIRED_PARAMETER_UNIT_CI.json",contrasts)
    for name,data in (("ARM_SUMMARIES.csv",descriptive),("PAIRED_PARAMETER_UNIT_CI.csv",[{k:v for k,v in r.items() if k!="unit_means"} for r in contrasts])):
        with (OUT/name).open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    heroes=[]
    for r in rows:
        if r["mode"]=="main" and r["unit_id"].endswith("_08") and r["seed"]==1103 and r["arm"] in ("full_supervised","simple_supervised"):
            heroes.append({"selection":"First locked parameter unit, first preregistered seed; not outcome selected",**{key:r[key] for key in ("family","condition","arm","trace_path","trace_sha256","invalid_physiology_samples")}})
    dump(OUT/"VIDEO_TRACE_INDEX.json",{"schema":"columnar json.gz;576samples; t_min is sample-start and end_t_min end-state time; true_glucose_mgdl is end-state; requested/auth/emitted values refer to the interval", "traces":heroes})
    result={"generated_utc":timestamp(),"completed_runs":len(rows),"failures":len(failed),"main_runs":sum(r["mode"]=="main" for r in rows),"feedback_stop_runs":sum(r["mode"]!="main" for r in rows),"parameter_units":len({r["unit_id"] for r in rows}),"main_runs_with_invalid_physiology":sum(r["mode"]=="main" and r["invalid_physiology_samples"]>0 for r in rows),"fixed_clean_command_estimand":True,"patient_holdout":False,"files":{name:sha(OUT/name) for name in ("RUN_RESULTS.json","ARM_SUMMARIES.json","PAIRED_PARAMETER_UNIT_CI.json","VIDEO_TRACE_INDEX.json")}}
    dump(OUT/"RESULT_SUMMARY.json",result)
    text=["# Comparative study results", "", "The main estimand applies identical clean-command tapes across arms. It measures delivery-authority interventions under fixed commands, not autonomous closed-loop efficacy. The smaller feedback/stop experiment is reported separately. All parameter units are synthetic; repeated seeds are averaged within parameter unit for confidence intervals.","",f"Completed: {result['main_runs']} main runs and {result['feedback_stop_runs']} feedback/stop runs; {len(failed)} recorded failures. Main runs with any flagged out-of-domain physiology: {result['main_runs_with_invalid_physiology']}. Invalid trajectories remain present; glucose bands on those runs are mathematical summaries, not physiological predictions.","","| Plant | Condition | Recovery | Full minus simple excess (U),95%CI | Full minus simple deficit (U),95%CI |", "|---|---|---|---|---|"]
    for family in ("geco_original","hovorka_2004"):
      for condition in load(OUT/"PREREGISTERED_SPEC.json")["conditions"]:
       for policy in ("manual","supervised"):
        selected=[r for r in contrasts if r["mode"]=="main" and r["family"]==family and r["condition"]==condition and r["arm_a"]=="full_"+policy and r["arm_b"]=="simple_"+policy]
        vals={r["metric"]:r for r in selected}
        def fmt(metric):
            r=vals.get(metric)
            return "unavailable" if r is None else f"{r['mean_paired_difference']:.3f} [{r['ci95_low']:.3f},{r['ci95_high']:.3f}]"
        text.append(f"| {family} | {condition} | {policy} | {fmt('stepwise_excess_vs_clean_u')} | {fmt('stepwise_deficit_vs_clean_u')} |")
    text += ["","All arm, condition, plant and stop assumptions, including sham/oracle references, nulls and adverse differences, are retained in ARM_SUMMARIES and PAIRED_PARAMETER_UNIT_CI. A negative excess difference does not alone establish benefit: deficits, interruptions, false containment, recovery censoring and invalid physiology require joint interpretation.","","Zero calibration statistical containment is a finite-sample fit criterion. Locked clean-run trips include identical local/quality rules and detector contributions; inspect full traces for attribution. Oracle delivery inhibition uses privileged fault labels and is an explanatory reference, not an achievable detection policy.","","See METHODOLOGY.md, PREREGISTERED_SPEC.json, amendment records, all attempt ledgers and EXECUTION_MANIFEST.json for scope, parameter independence, code/config identities and failed-run accounting. No physical experiment, real sensor validation, clinical outcome or cybersecurity efficacy is established."]
    (OUT/"RESULTS_RELEASE.md").write_text("\n".join(text)+"\n")
    print(json.dumps(result))

if __name__=="__main__":summarize()
