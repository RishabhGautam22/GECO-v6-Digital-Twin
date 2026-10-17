"""Portable study runner. All outputs retain full trace, hashes and attempt records."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime,timezone
import argparse
import csv
import gzip
import hashlib
import json
import importlib.metadata
import platform
import os
import sys
import time
import traceback
from collections import Counter
import numpy as np
from .engine import run,metrics

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"03_EXPERIMENTS/comparative_study"

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n")
def load(path):return json.loads(Path(path).read_text())
def timestamp():return datetime.now(timezone.utc).isoformat()
def environment():
    packages={}
    for name in ("numpy","scipy","numba","pandas"):
        try:packages[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:packages[name]=None
    return {"python":sys.version,"executable":sys.executable,"platform":platform.platform(),"packages":packages,"numerical_acceleration":"Optional Numba; no fastmath; no GPU study computation configured"}
def append(path,obj):
    with Path(path).open("a") as f:f.write(json.dumps(obj,allow_nan=False)+"\n")
def save_trace(path,trace):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(path,"wt",encoding="utf8") as f:json.dump(trace,f,separators=(",",":"),allow_nan=False)
    return {"path":str(path.relative_to(ROOT)),"sha256":sha(path),"samples":len(trace["columns"]["sample"])}
def source_hashes():
    paths=list((ROOT/"02_IMPLEMENTATION/geco_v6_study").glob("*.py"))
    paths+=list((ROOT/"02_IMPLEMENTATION/geco_v4").glob("*.py"))
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}

def pooled_config(calibration_path):
    records=load(calibration_path)
    if "participants" in records:records=records["participants"]
    valid=[(pid,r) for pid,r in records.items() if isinstance(r,dict) and "params" in r and "validation" in r and r.get("status","frozen")=="frozen"]
    if not valid:raise ValueError("No frozen participant calibration records")
    params={k:float(np.median([r["params"][k] for _,r in valid])) for k in valid[0][1]["params"]}
    params["sub_steps"]=int(params["sub_steps"])
    config={"params":params,"r_std":9.,"mass_sigma_g":.005143506785294255}
    for key in ("innovation_inflation","ar1_rho","sigma6_mgdl"):
        config[key]=float(np.median([r["validation"][key] for _,r in valid]))
    policies=[r["validation"]["forecast_policy"] for _,r in valid]
    mode=Counter(p["kind"] for p in policies).most_common(1)[0][0]
    selected=[p for p in policies if p["kind"]==mode]
    config["forecast_policy"]={"kind":mode}
    for key in selected[0]:
        if key!="kind":config["forecast_policy"][key]=float(np.median([p[key] for p in selected]))
    if "trend_window" in config["forecast_policy"]:config["forecast_policy"]["trend_window"]=int(config["forecast_policy"]["trend_window"])
    config["provenance"]={"source":str(Path(calibration_path).resolve()),"sha256":sha(calibration_path),"participant_ids":[pid for pid,_ in valid],"pooling":"Coordinate-wise median of frozen numerical calibration fields; modal selected policy (ties in source record order), median policy parameters among records selecting it. Composite model is an explicit transfer to synthetic plants, not a fitted virtual participant.","mass_sigma_source":"Supplied benign delivery calibration; fixed across every arm, with detector run thresholds newly tuned on synthetic calibration only"}
    return config

def prepare(calibration_path):
    target=OUT/"FROZEN_STUDY_CONFIG.json"
    if target.exists():raise RuntimeError("Configuration already frozen; create explicit amendment instead of overwriting")
    spec=load(OUT/"PREREGISTERED_SPEC.json");units=load(OUT/"SYNTHETIC_PARAMETER_SPLIT.json")
    config=pooled_config(calibration_path);rows=[];maxima={"full":[],"simple":[]}
    before=source_hashes()
    for unit in units:
        if unit["split"]!="calibration":continue
        for seed in spec["noise_meal_seeds"]:
            runid=f"calibration_{unit['unit_id']}_{seed}"
            attempt={"run_id":runid,"attempt":1,"started_utc":timestamp()}
            try:
                trace=run(unit,seed,"clean","full_manual",config,spec,calibration=True)
                evidence=save_trace(OUT/"calibration_traces"/(runid+".json.gz"),trace)
                maximum=trace["metadata"]["score_maxima"]
                for key in maxima:maxima[key].append(maximum[key])
                rows.append({"run_id":runid,"maxima":maximum,"invalid_plant_samples":sum(not x for x in trace["columns"]["plant_valid"]),"trace":evidence})
                attempt.update(status="complete",finished_utc=timestamp(),trace=evidence)
            except Exception:
                attempt.update(status="failed",finished_utc=timestamp(),exception=traceback.format_exc())
                append(OUT/"calibration_attempts.jsonl",attempt);raise
            append(OUT/"calibration_attempts.jsonl",attempt)
    if source_hashes()!=before:raise RuntimeError("Source changed during calibration; preserve attempts and restart explicitly")
    config["thresholds"]={k:float(np.nextafter(max(v),math_inf())) for k,v in maxima.items()}
    config["frozen_utc"]=timestamp();config["source_hashes"]=before;config["environment"]=environment()
    config["spec_sha256"]=sha(OUT/"PREREGISTERED_SPEC.json");config["split_sha256"]=sha(OUT/"SYNTHETIC_PARAMETER_SPLIT.json")
    dump(OUT/"CALIBRATION_RESULTS.json",{"runs":rows,"empirical_statistical_containment_runs":{"full":0,"simple":0},"finite_sample_warning":"32 calibration run maxima do not establish a population false-alarm bound; seeds are repeated within16 parameter units"})
    dump(target,config)
    print(json.dumps({"configuration":str(target),"sha256":sha(target),"thresholds":config["thresholds"]}))

def math_inf():return float("inf")

def run_job(args):
    unit,seed,mode,config,spec=args
    folder=OUT/("main" if mode=="main" else "feedback_stop_sensitivity")
    ledger=folder/"attempts"/f"{unit['unit_id']}_{seed}.jsonl";ledger.parent.mkdir(parents=True,exist_ok=True)
    allrows=[];failures=[]
    common_id=f"{unit['unit_id']}_{seed}"
    clean_reference=None
    # Same fixed clean-command tape before applying any condition.
    if mode=="main":
        rid=f"{common_id}_clean_reference"
        try:
            clean_reference=run(unit,seed,"clean","full_manual",config,spec,calibration=True)
            ev=save_trace(folder/"references"/(rid+".json.gz"),clean_reference)
            append(ledger,{"run_id":rid,"attempt":1,"status":"complete","finished_utc":timestamp(),"trace":ev,"role":"clean_reference_generation"})
        except Exception:
            failure={"run_id":rid,"attempt":1,"status":"failed","exception":traceback.format_exc()};append(ledger,failure)
            return {"rows":[],"failures":[failure]}
    stopmodels=["one_sample_baseline"] if mode=="main" else spec["secondary_sensitivity"]["stop_models"]
    arms=spec["arms"] if mode=="main" else spec["secondary_sensitivity"]["arms"]
    conditions=spec["conditions"] if mode=="main" else spec["secondary_sensitivity"]["conditions"]
    for stop in stopmodels:
      for arm in arms:
        reference=clean_reference
        for condition in conditions:
          runid=f"{common_id}_{condition}_{arm}_{stop}"
          attempt={"run_id":runid,"attempt":1,"started_utc":timestamp()}
          try:
            trace=run(unit,seed,condition,arm,config,spec,clean=clean_reference["columns"] if mode=="main" else None,feedback=mode!="main",stop_model=stop)
            if mode!="main" and condition=="clean":reference=trace
            result=metrics(trace,reference,spec)
            ev=save_trace(folder/"traces"/(runid+".json.gz"),trace)
            row={"run_id":runid,"unit_id":unit["unit_id"],"family":unit["family"],"seed":seed,"condition":condition,"arm":arm,"stop_model":stop,"mode":mode,**result,"trace_path":ev["path"],"trace_sha256":ev["sha256"]}
            allrows.append(row);attempt.update(status="complete",finished_utc=timestamp(),trace=ev)
          except Exception:
            attempt.update(status="failed",finished_utc=timestamp(),exception=traceback.format_exc());failures.append(attempt.copy())
          append(ledger,attempt)
    dump(folder/"unit_results"/f"{common_id}.json",{"rows":allrows,"failures":failures})
    return {"rows":allrows,"failures":failures}

def execute(workers=4,mode="all"):
    config=load(OUT/"FROZEN_STUDY_CONFIG.json");spec=load(OUT/"PREREGISTERED_SPEC.json");units=load(OUT/"SYNTHETIC_PARAMETER_SPLIT.json")
    before=source_hashes()
    if before!=config["source_hashes"]:raise RuntimeError("Source differs from calibration freeze; add documented amendment and retune before executing")
    completed_path=OUT/"EXECUTION_MANIFEST.json"
    if completed_path.exists():raise RuntimeError("Execution receipt exists; do not silently overwrite campaign attempts")
    jobs=[]
    for unit in units:
        if unit["split"]!="locked_test":continue
        for seed in spec["noise_meal_seeds"]:
            if mode in ("all","main"):jobs.append((unit,seed,"main",config,spec))
            if mode in ("all","sensitivity") and int(unit["unit_id"].split("_")[-1])<14:jobs.append((unit,seed,"sensitivity",config,spec))
    manifest={"started_utc":timestamp(),"environment":environment(),"workers":workers,"job_count":len(jobs),"mode":mode,"configuration_sha256":sha(OUT/"FROZEN_STUDY_CONFIG.json"),"source_hashes_start":before,"command":sys.argv,"results":[],"failures":[]}
    dump(OUT/"EXECUTION_STARTED.json",manifest)
    rows=[];failures=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(run_job,j):j[:3] for j in jobs}
        for i,future in enumerate(as_completed(futures),1):
            try:
                result=future.result();rows.extend(result["rows"]);failures.extend(result["failures"])
            except Exception:
                failures.append({"job":str(futures[future]),"exception":traceback.format_exc(),"status":"worker_failed"})
            print(json.dumps({"jobs_done":i,"jobs_total":len(jobs),"runs_completed":len(rows),"failures":len(failures)}),flush=True)
    rows.sort(key=lambda x:x["run_id"]+x["mode"])
    dump(OUT/"RUN_RESULTS.json",rows);dump(OUT/"FAILED_RUNS.json",failures)
    if rows:
        with (OUT/"RUN_RESULTS.csv").open("w",newline="") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    manifest.update(finished_utc=timestamp(),completed_runs=len(rows),failed_runs=len(failures),source_hashes_end=source_hashes(),source_unchanged=source_hashes()==before,run_results_sha256=sha(OUT/"RUN_RESULTS.json"))
    manifest.pop("results");manifest.pop("failures");dump(completed_path,manifest)
    print(json.dumps({"completed_runs":len(rows),"failed_runs":len(failures),"source_unchanged":manifest["source_unchanged"]}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument("action",choices=["prepare","execute"]);parser.add_argument("--calibration");parser.add_argument("--workers",type=int,default=4);parser.add_argument("--mode",choices=["all","main","sensitivity"],default="all")
    args=parser.parse_args()
    if args.action=="prepare":prepare(args.calibration)
    else:execute(args.workers,args.mode)
if __name__=="__main__":main()
