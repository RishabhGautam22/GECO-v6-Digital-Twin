"""New synthetic fasting study, preserving the complete primary campaign.

The adapter substitutes only a meal-free exogenous tape and a mass-CUSUM arm.
It calls the original frozen study engine for interval/authority/recovery logic.
"""
from pathlib import Path
from contextlib import contextmanager
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse,hashlib,json,gzip,csv,traceback,sys
from collections import defaultdict
import numpy as np
from geco_v6_study import engine as base
from geco_v6_study.plants import make_plant
from geco_v6_study.campaign import dump,load,sha,timestamp,save_trace,environment,source_hashes as primary_sources
from geco_v6_study.summarize import ci_unit,METRICS

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"03_EXPERIMENTS/supplement_fasting"
PRIMARY=ROOT/"03_EXPERIMENTS/comparative_study"
BASE_EXOGENOUS=base.exogenous
BASE_DETECTOR=base.Detector
ARMS=["full_supervised","simple_supervised","masscusum_supervised","sham_supervised"]

class SupplementDetector(BASE_DETECTOR):
    def observe(self,*args):
        value=super().observe(*args)
        if self.kind=="masscusum":
            value["score"]=value["mass_cusum"]
            value["alarm"]=bool(value["score"]>self.threshold)
        return value

def fasting_exogenous(unit,seed,steps):
    values=BASE_EXOGENOUS(unit,seed,steps)
    values["carbs"][:]=0.
    return values

@contextmanager
def adapter():
    old_exogenous,old_detector=base.exogenous,base.Detector
    base.exogenous,base.Detector=fasting_exogenous,SupplementDetector
    try:yield
    finally:base.exogenous,base.Detector=old_exogenous,old_detector

def compensated_command(basal_u):
    """Nearest achievable noise-free nominal mass using known mapping only.

    The nonnegative stochastic emission clamp can add a small positive bias;
    it is not retuned away and remains in the observed physical-cost endpoint.
    """
    ideal=(basal_u-.0015/.1005)/1.015
    integer=ideal*200
    candidates=sorted({0.,max(1,int(np.floor(integer)))/200,max(1,int(np.ceil(integer)))/200})
    candidates=[min(.30,u) for u in candidates]
    u=min(candidates,key=lambda c:(abs(base.expected_mass(c)/.1005-basal_u),c))
    emitted=base.expected_mass(u)/.1005
    return {"requested_constant_u":u,"target_equilibrium_basal_u":basal_u,"nominal_emitted_u_per_step":emitted,"nominal_quantization_residual_u_per_step":emitted-basal_u,"nominal_bias_48h_u":576*(emitted-basal_u),"compensated_zero_command":u==0.,"candidates_u":candidates,"rule":"minimum absolute nominal physical-basal error among zero and nearest positive microstep commands; ties lower request; no trajectory tuning"}

def sources():
    result=primary_sources()
    for p in sorted(Path(__file__).parent.glob("*.py")):result[str(p.relative_to(ROOT))]=sha(p)
    test=ROOT/"02_IMPLEMENTATION/tests/test_v6_supplement.py"
    result[str(test.relative_to(ROOT))]=sha(test)
    return result

def append(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a") as f:f.write(json.dumps(obj,allow_nan=False)+"\n")

def register():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/"PREREGISTERED_SPEC.json").exists():raise RuntimeError("Supplement preregistration already exists")
    spec=load(PRIMARY/"PREREGISTERED_SPEC.json")
    spec.update(study="post-primary exploratory fasting and component sensitivity",registered_utc=timestamp(),steps=576,dt_min=5.,parameter_seed=202609072,noise_meal_seeds=[3907,4801],units_per_family={"calibration":4,"locked_test":16},arms=ARMS,main_run_count=2048)
    spec["primary_results_preserved"]={"manifest_sha256":sha(PRIMARY/"EXECUTION_MANIFEST.json"),"results_sha256":sha(PRIMARY/"RUN_RESULTS.json"),"scope":"Primary4608+576runs and all adverse/domain findings are unchanged; this is a follow-on study, not original confirmatory preregistration"}
    spec["motivation_calibration_only"]={"investigation":str((PRIMARY/"CALIBRATION_DOMAIN_INVESTIGATION.json").relative_to(ROOT)),"sha256":sha(PRIMARY/"CALIBRATION_DOMAIN_INVESTIGATION.json"),"hovorka_calibration":"16/16runs negativeEGP,1606negativeEGP and1773domain-invalid samples;zero negativeEGP before first meal","original_calibration":"16runs,0domain-invalid samples,4remote-action boundary samples"}
    spec["primary_estimand"]="Fasting fixed constant command intervention; known nominal emission map compensates synthetic equilibrium basal. Not feedback therapy; not a patient holdout."
    spec["command_rule"]="Each unit: analytically calculate fixed mean-equilibrium basal, choose command minimizing absolute nominal physical-emission error among zero and floor/ceil positive200steps/U candidates after1.015gain and0.0015gdribble; ties lower request;0.30Ucap. Record zero-command units, residual per-step/48h, requested/authorized/emitted cost. No outcome-based unit exclusion or retuning."
    spec["command_noise_limitation"]="Compensation inverts the noise-free nominal map; the nonnegative stochastic emission clamp can add small positive bias, retained in observed emission error rather than fitted away."
    spec["meals"]="None in every run; all other paired exogenous random arrays follow the new seeds"
    spec["clean_controller"]="No feedback controller in this supplement: the same analytically compensated constant request is used by all four arms and the clean reference. Production filter remains active in full and clean calibration; mass-only/simple/sham do not require its predictions."
    spec["component_arms"]={"full":"same full score as primary","masscusum":"same two-sided massCUSUM as full, same drift0.5, clipping±6 and sigma; no physiology corroboration","simple":"same single-step residual as primary","sham":"no statistical trips; identical local/quality/cutoff/supervised-reset authority"}
    spec["threshold_calibration"]="Three independent thresholds strictly exceed each score maximum on16new clean calibration runs (8independent new units,2repeated seeds). Same clean exposure, zero empirical calibration statistical containments; no prospective bound. No locked outcomes used."
    spec["detectors"]["calibration"]=spec["threshold_calibration"]
    spec["detectors"]["masscusum"]=spec["component_arms"]["masscusum"]
    spec["recovery"].pop("manual",None);spec["recovery"].pop("oracle",None)
    spec["recovery_policy"]="Supervised emulation only, reusing corrected primary engine including30min cooldown from trip-end, fixed120min operator slots, same verification/probation rules"
    spec["stop_model"]="one_sample_baseline only; prior delayed/tail sensitivity remains in the primary study"
    spec["supplementary_contrasts"]=["full-masscusum (increment of physiology/cross-channel rule under separately matched clean maxima)","masscusum-simple (mass aggregation)","full-simple","full-sham","masscusum-sham","simple-sham"]
    spec["inference"]="Paired mean difference,2seed repetitions averaged within new parameter unit;4096percentile bootstrap resamples at unit level, separately perplant/condition.16testunits perplant. Descriptive exploratory intervals, no clinical or multiplicity-adjusted superiority claim."
    spec["secondary_sensitivity"]="No additional feedback/stop matrix in supplement"
    spec["domain_reporting"]="All cases retained; numerical/domain flags, negativeEGP, original clamp boundaries, glucose bands, compensation bias and zero requests explicitly counted. A stable fasting regime cannot validate the original meal-excited regime."
    rng=np.random.default_rng(spec["parameter_seed"]);units=[]
    for family in spec["plant_families"]:
      for i in range(20):
        factors={k:float(np.exp(rng.uniform(np.log(.75),np.log(1.25)))) for k in ("sensitivity","absorption","clearance","glucose_flux","glucose_effectiveness","gut_gain")}
        units.append({"unit_id":f"{family}_fasting_{i:02d}","family":family,"split":"calibration" if i<4 else "locked_test","body_weight_kg":float(rng.uniform(55,100)),"initial_glucose_mgdl":120.,"factors":factors})
    dump(OUT/"PREREGISTERED_SPEC.json",spec);dump(OUT/"SYNTHETIC_PARAMETER_SPLIT.json",units)
    dump(OUT/"PREREGISTRATION_COMMIT.json",{"registered_utc":timestamp(),"supplement_outcomes_executed":False,"external_registration":False,"stage":"post-primary exploratory, before new supplement outcomes","files":{name:sha(OUT/name) for name in ("PREREGISTERED_SPEC.json","SYNTHETIC_PARAMETER_SPLIT.json")},"source_hashes":sources()})
    print(json.dumps({"spec_sha256":sha(OUT/"PREREGISTERED_SPEC.json"),"split_sha256":sha(OUT/"SYNTHETIC_PARAMETER_SPLIT.json")}))

def run_one(unit,seed,condition,arm,config,spec,calibration=False):
    compensation=compensated_command(make_plant(unit).basal_u)
    clean={"requested_u":[compensation["requested_constant_u"]]*spec["steps"]}
    with adapter():trace=base.run(unit,seed,condition,arm,config,spec,clean=clean,calibration=calibration)
    trace["metadata"].update(study="supplement_fasting",compensation=compensation,meals="none",calibration=calibration)
    return trace

def prepare():
    if (OUT/"FROZEN_SUPPLEMENT_CONFIG.json").exists():raise RuntimeError("Supplement config already frozen")
    config=load(PRIMARY/"FROZEN_STUDY_CONFIG.json")
    if primary_sources()!=config["source_hashes"]:raise RuntimeError("Primary source changed; do not hide an implementation difference")
    config["thresholds"]={};spec=load(OUT/"PREREGISTERED_SPEC.json");units=load(OUT/"SYNTHETIC_PARAMETER_SPLIT.json");before=sources();rows=[];maxima={"full":[],"simple":[],"masscusum":[]}
    for unit in units:
      if unit["split"]!="calibration":continue
      for seed in spec["noise_meal_seeds"]:
        rid=f"cal_{unit['unit_id']}_{seed}";record={"run_id":rid,"attempt":1,"started_utc":timestamp()}
        try:
            trace=run_one(unit,seed,"clean","full_supervised",config,spec,True)
            ev=save_trace(OUT/"calibration_traces"/(rid+".json.gz"),trace)
            maximum={key:max(trace["columns"][field][spec["warmup_steps"]:]) for key,field in (("full","full_score"),("simple","simple_score"),("masscusum","mass_cusum"))}
            for key in maxima:maxima[key].append(maximum[key])
            rows.append({"run_id":rid,"maxima":maximum,"domain_invalid_samples":sum(not v for v in trace["columns"]["plant_valid"]),"negative_egp_samples":sum(trace["columns"]["negative_egp_evaluator_only"]),"compensation":trace["metadata"]["compensation"],"trace":ev})
            record.update(status="complete",finished_utc=timestamp(),trace=ev)
        except Exception:
            record.update(status="failed",finished_utc=timestamp(),exception=traceback.format_exc());append(OUT/"calibration_attempts.jsonl",record);raise
        append(OUT/"calibration_attempts.jsonl",record)
    if sources()!=before:raise RuntimeError("Source changed during supplement calibration")
    config.update(thresholds={k:float(np.nextafter(max(v),float("inf"))) for k,v in maxima.items()},frozen_utc=timestamp(),environment=environment(),supplement_source_hashes=before,supplement_spec_sha256=sha(OUT/"PREREGISTERED_SPEC.json"),supplement_split_sha256=sha(OUT/"SYNTHETIC_PARAMETER_SPLIT.json"),primary_config_sha256=sha(PRIMARY/"FROZEN_STUDY_CONFIG.json"))
    dump(OUT/"CALIBRATION_RESULTS.json",{"runs":rows,"zero_empirical_statistical_containment":{"full":True,"simple":True,"masscusum":True},"no_population_false_alarm_guarantee":True})
    dump(OUT/"FROZEN_SUPPLEMENT_CONFIG.json",config)
    print(json.dumps({"config_sha256":sha(OUT/"FROZEN_SUPPLEMENT_CONFIG.json"),"thresholds":config["thresholds"],"calibration_runs":len(rows)}))

def job(args):
    unit,seed,config,spec=args;rows=[];failures=[];prefix=f"{unit['unit_id']}_{seed}";ledger=OUT/"attempts"/(prefix+".jsonl")
    try:
        reference=run_one(unit,seed,"clean","full_supervised",config,spec,True)
        ev=save_trace(OUT/"references"/(prefix+"_clean_reference.json.gz"),reference)
        append(ledger,{"run_id":prefix+"_clean_reference","role":"clean_reference","attempt":1,"status":"complete","finished_utc":timestamp(),"trace":ev})
    except Exception:
        error={"run_id":prefix+"_clean_reference","attempt":1,"status":"failed","exception":traceback.format_exc()};append(ledger,error);return {"rows":[],"failures":[error]}
    for arm in spec["arms"]:
      for condition in spec["conditions"]:
        rid=f"{prefix}_{condition}_{arm}";attempt={"run_id":rid,"attempt":1,"started_utc":timestamp()}
        try:
            trace=run_one(unit,seed,condition,arm,config,spec)
            m=base.metrics(trace,reference,spec);comp=trace["metadata"]["compensation"]
            m.update(total_requested_u=sum(trace["columns"]["requested_u"]),total_authorized_u=sum(trace["columns"]["authorized_u"]),compensated_zero_request_slots=sum(u==0 for u in trace["columns"]["requested_u"]),physical_error_vs_equilibrium_target_u=m["total_emitted_u"]-comp["target_equilibrium_basal_u"]*spec["steps"])
            ev=save_trace(OUT/"traces"/(rid+".json.gz"),trace)
            rows.append({"run_id":rid,"unit_id":unit["unit_id"],"family":unit["family"],"seed":seed,"condition":condition,"arm":arm,"mode":"supplement_fasting",**m,**{k:v for k,v in comp.items() if k not in ("candidates_u","rule")},"trace_path":ev["path"],"trace_sha256":ev["sha256"]})
            attempt.update(status="complete",finished_utc=timestamp(),trace=ev)
        except Exception:
            attempt.update(status="failed",finished_utc=timestamp(),exception=traceback.format_exc());failures.append(attempt.copy())
        append(ledger,attempt)
    dump(OUT/"unit_results"/(prefix+".json"),{"rows":rows,"failures":failures});return {"rows":rows,"failures":failures}

def execute(workers):
    if (OUT/"EXECUTION_MANIFEST.json").exists():raise RuntimeError("Completed supplement exists")
    config=load(OUT/"FROZEN_SUPPLEMENT_CONFIG.json");spec=load(OUT/"PREREGISTERED_SPEC.json");units=load(OUT/"SYNTHETIC_PARAMETER_SPLIT.json");before=sources()
    if before!=config["supplement_source_hashes"]:raise RuntimeError("Source differs from supplement freeze")
    manifest={"started_utc":timestamp(),"configuration_sha256":sha(OUT/"FROZEN_SUPPLEMENT_CONFIG.json"),"source_hashes_start":before,"environment":environment(),"workers":workers,"command":sys.argv}
    dump(OUT/"EXECUTION_STARTED.json",manifest);jobs=[(u,s,config,spec) for u in units if u["split"]=="locked_test" for s in spec["noise_meal_seeds"]];rows=[];failures=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
      futures=[pool.submit(job,j) for j in jobs]
      for i,future in enumerate(as_completed(futures),1):
        try:r=future.result();rows.extend(r["rows"]);failures.extend(r["failures"])
        except Exception:failures.append({"status":"worker_failed","exception":traceback.format_exc()})
        print(json.dumps({"jobs_done":i,"jobs_total":len(jobs),"complete_runs":len(rows),"failed_runs":len(failures)}),flush=True)
    rows.sort(key=lambda r:r["run_id"]);dump(OUT/"RUN_RESULTS.json",rows);dump(OUT/"FAILED_RUNS.json",failures)
    with (OUT/"RUN_RESULTS.csv").open("w",newline="") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    manifest.update(finished_utc=timestamp(),completed_runs=len(rows),failed_runs=len(failures),source_hashes_end=sources(),source_unchanged=sources()==before,results_sha256=sha(OUT/"RUN_RESULTS.json"))
    dump(OUT/"EXECUTION_MANIFEST.json",manifest);print(json.dumps({"completed_runs":len(rows),"failed_runs":len(failures),"source_unchanged":manifest["source_unchanged"]}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=["register","prepare","execute"]);parser.add_argument("--workers",type=int,default=4);args=parser.parse_args()
    if args.action=="register":register()
    elif args.action=="prepare":prepare()
    else:execute(args.workers)
if __name__=="__main__":main()
