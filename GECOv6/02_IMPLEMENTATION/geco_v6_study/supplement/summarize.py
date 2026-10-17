"""All-condition exploratory paired summaries, retaining adverse/null outcomes."""
from collections import defaultdict
import csv,json
import numpy as np
from .study import OUT,load,dump,sha,timestamp,ci_unit,METRICS

EXTRA=["total_requested_u","total_authorized_u","total_emitted_u","compensated_zero_request_slots","physical_error_vs_equilibrium_target_u","nominal_quantization_residual_u_per_step","nominal_bias_48h_u","negative_egp_evaluator_only_samples","plasma_glucose_clamped_samples","interstitial_glucose_clamped_samples","remote_action_clamped_samples"]
CONTRASTS=[("full","masscusum"),("masscusum","simple"),("full","simple"),("full","sham"),("masscusum","sham"),("simple","sham")]

def main():
    rows=load(OUT/"RUN_RESULTS.json");groups=defaultdict(list)
    for row in rows:groups[(row["family"],row["condition"],row["arm"])].append(row)
    summaries=[];contrasts=[];rng=np.random.default_rng(202609080)
    for (family,condition,arm),data in sorted(groups.items()):
        d=dict(family=family,condition=condition,arm=arm,n_runs=len(data),n_parameter_units=len({r["unit_id"] for r in data}),runs_any_trip=sum(r["trip_count"]>0 for r in data),runs_domain_invalid=sum(r["invalid_physiology_samples"]>0 for r in data),runs_negative_egp=sum(r["negative_egp_evaluator_only_samples"]>0 for r in data),runs_recovery_censored=sum(r["recovery_censored"] for r in data),compensated_zero_command_runs=sum(r["compensated_zero_command"] for r in data))
        for metric in METRICS+EXTRA:
            values=[r[metric] for r in data]
            d[metric+"_mean"]=float(np.mean(values));d[metric+"_min"]=min(values);d[metric+"_max"]=max(values);d[metric+"_total"]=sum(values)
        summaries.append(d)
    for family,condition in sorted({k[:2] for k in groups}):
      for a,b in CONTRASTS:
        aa={(r["unit_id"],r["seed"]):r for r in groups[(family,condition,a+"_supervised")]};bb={(r["unit_id"],r["seed"]):r for r in groups[(family,condition,b+"_supervised")]}
        for metric in METRICS+EXTRA[:5]:
            units=defaultdict(list)
            for key in sorted(set(aa)&set(bb)):units[key[0]].append(aa[key][metric]-bb[key][metric])
            complete={k:v for k,v in units.items() if len(v)==2};values=[float(np.mean(v)) for _,v in sorted(complete.items())]
            if not values:continue
            mean,lo,hi=ci_unit(values,rng)
            contrasts.append(dict(family=family,condition=condition,arm_a=a+"_supervised",arm_b=b+"_supervised",metric=metric,mean_paired_difference=mean,ci95_low=lo,ci95_high=hi,n_parameter_units=len(values),seed_repetitions_per_unit=2,missing_seed_pairs=len(set(aa)^set(bb)),incomplete_units=len(units)-len(complete),bootstrap_resamples=4096,unit_means=dict(zip(sorted(complete),values))))
    for stem,data in (("ARM_SUMMARIES",summaries),("PAIRED_PARAMETER_UNIT_CI",contrasts)):
        dump(OUT/(stem+".json"),data)
        flat=[{k:v for k,v in r.items() if k!="unit_means"} for r in data]
        with (OUT/(stem+".csv")).open("w",newline="") as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    unique={r["unit_id"]:r for r in rows};config=load(OUT/"FROZEN_SUPPLEMENT_CONFIG.json")
    result=dict(generated_utc=timestamp(),completed_runs=len(rows),failed_runs=len(load(OUT/"FAILED_RUNS.json")),parameter_units=len(unique),seed_repetitions=2,synthetic_only=True,post_primary_exploratory=True,all_cases_retained=True,thresholds=config["thresholds"],runs_domain_invalid=sum(r["invalid_physiology_samples"]>0 for r in rows),runs_negative_egp=sum(r["negative_egp_evaluator_only_samples"]>0 for r in rows),zero_compensated_command_units=sum(r["compensated_zero_command"] for r in unique.values()),zero_compensated_command_runs=sum(r["compensated_zero_command"] for r in rows),nominal_quantization_residual_u_per_step_range=[min(r["nominal_quantization_residual_u_per_step"] for r in rows),max(r["nominal_quantization_residual_u_per_step"] for r in rows)],inputs={name:sha(OUT/name) for name in ("RUN_RESULTS.json","ARM_SUMMARIES.json","PAIRED_PARAMETER_UNIT_CI.json","FROZEN_SUPPLEMENT_CONFIG.json")})
    dump(OUT/"RESULT_SUMMARY.json",result)
    lines=["# Fasting and detector-component supplement","","This follow-on study was designed after the primary results. Its new synthetic vectors and repeated seeds, fasting constant requests, matching authority and three clean-maxima thresholds were frozen before supplemental outcomes. It is an exploratory structural/domain sensitivity, not an autonomous feedback therapy or patient holdout. All original meal-excited results remain unchanged.","",f"Completed {len(rows)} of 2,048 planned runs; {result['failed_runs']} failures. Domain-invalid runs: {result['runs_domain_invalid']}; negative-EGP runs: {result['runs_negative_egp']}. Compensated zero-command units: {result['zero_compensated_command_units']}/32. Quantization residual range: {result['nominal_quantization_residual_u_per_step_range']} research U per five-minute slot.","",f"Thresholds, strictly above maxima on 16 clean calibration runs (8 vectors × 2 seeds): {config['thresholds']}. These match empirical calibration exposure, not a guaranteed false-alarm probability.","","| Plant | Condition | Contrast | Excess difference U [95% CI] | Deficit difference U [95% CI] |","|---|---|---|---|---|"]
    for family,condition in sorted({k[:2] for k in groups}):
      for a,b in CONTRASTS[:3]:
        selected={r["metric"]:r for r in contrasts if r["family"]==family and r["condition"]==condition and r["arm_a"]==a+"_supervised" and r["arm_b"]==b+"_supervised"}
        def fmt(k):
            r=selected.get(k)
            return "unavailable" if not r else f"{r['mean_paired_difference']:.4f} [{r['ci95_low']:.4f}, {r['ci95_high']:.4f}]"
        lines.append(f"| {family} | {condition} | {a} minus {b} | {fmt('stepwise_excess_vs_clean_u')} | {fmt('stepwise_deficit_vs_clean_u')} |")
    lines += ["","All six contrasts, two-sided glucose bands, interruption, recovery censoring and cost/quantization fields are retained in machine-readable tables. Intervals average seeds within each vector and bootstrap 16 vectors separately per plant and condition; they are exploratory and not multiplicity-adjusted. A reduction in excessive emission can be offset by greater delivery deficit. Full versus mass-CUSUM changes physiology corroboration and its independently calibrated threshold; it is the specified component-policy contrast, not a physiology-only biomarker validation.","","The fixed operator schedule and monitor-visible recovery evidence are identical across arms. A passing finite numerical/domain screen does not validate a physiological plant or measured rig dynamics. This fasting regime cannot erase the original meal-excited domain failures. All movies based on these traces must label this narrower estimand."]
    (OUT/"RESULTS_RELEASE.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(result))
if __name__=="__main__":main()
