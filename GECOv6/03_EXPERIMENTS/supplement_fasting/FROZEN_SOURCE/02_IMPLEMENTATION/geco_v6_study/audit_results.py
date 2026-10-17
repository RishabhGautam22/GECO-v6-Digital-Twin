"""Exhaustive safe trace/data checks after the offline study; no simulation."""
import gzip
import json
from pathlib import Path
import numpy as np
from .campaign import OUT,ROOT,load,dump,sha,timestamp

def main():
    rows=load(OUT/"RUN_RESULTS.json");spec=load(OUT/"PREREGISTERED_SPEC.json")
    issues=[];checked=0;samples=0;commands={};references={}
    for path in (OUT/"main/references").glob("*.json.gz"):
        with gzip.open(path,"rt") as f:trace=json.load(f)
        meta=trace["metadata"];references[(meta["unit_id"],meta["seed"])]=trace["columns"]["requested_u"]
    identifiers=set()
    for row in rows:
        identity=(row["mode"],row["run_id"])
        if identity in identifiers:issues.append({"run_id":row["run_id"],"issue":"duplicate identity"})
        identifiers.add(identity)
        path=ROOT/row["trace_path"]
        if sha(path)!=row["trace_sha256"]:issues.append({"run_id":row["run_id"],"issue":"trace hash differs"});continue
        with gzip.open(path,"rt") as f:trace=json.load(f)
        c=trace["columns"];n=len(c["sample"])
        checks={
          "sample_count":n==spec["steps"],
          "equal_column_lengths":all(len(v)==n for v in c.values()),
          "sample_order":c["sample"]==list(range(n)),
          "start_clock":c["t_min"]==[k*spec["dt_min"] for k in range(n)],
          "end_clock":c["end_t_min"]==[(k+1)*spec["dt_min"] for k in range(n)],
          "mass_to_plant":bool(np.allclose(np.array(c["actual_emitted_g"])/.1005,c["virtual_plant_input_u"],atol=1e-13,rtol=0)),
          "no_negative_emission":bool(np.all(np.array(c["actual_emitted_u"])>=0)),
          "authority_no_catchup":all(0<=a<=min(.3,r)+1e-12 for a,r in zip(c["authorized_u"],c["requested_u"])),
          "operator_slot":all(not reset or (k>0 and k%24==0 and c["operator_authorized"][k]) for k,reset in enumerate(c["reset_event"])),
          "finite_evaluator_glucose":bool(np.isfinite(c["true_glucose_mgdl"]).all()),
        }
        if row["mode"]=="main":checks["identical_clean_requests"]=c["requested_u"]==references[(row["unit_id"],row["seed"])]
        if row["stop_model"]=="one_sample_baseline":
            checks["latched_before_sample_emits_zero"]=all(state!="LATCHED" or abs(mass)<1e-13 for state,mass in zip(c["state_before_emission"],c["actual_emitted_g"]))
        for name,ok in checks.items():
            if not ok:issues.append({"run_id":row["run_id"],"issue":name})
        checked+=1;samples+=n
    attempts=[]
    for path in OUT.glob("*/attempts/*.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():attempts.append(json.loads(line))
    expected_main=spec["main_run_count"];expected_secondary=spec["secondary_sensitivity"]["run_count"]
    main_count=sum(r["mode"]=="main" for r in rows);secondary_count=len(rows)-main_count
    if main_count!=expected_main:issues.append({"issue":"main run count","expected":expected_main,"actual":main_count})
    if secondary_count!=expected_secondary:issues.append({"issue":"sensitivity run count","expected":expected_secondary,"actual":secondary_count})
    result={"generated_utc":timestamp(),"status":"PASS" if not issues else "FAIL","completed_traces_checked":checked,"samples_checked":samples,"main_runs":main_count,"secondary_runs":secondary_count,"expected_main":expected_main,"expected_secondary":expected_secondary,"attempt_records_including_clean_references":len(attempts),"attempt_status_counts":{state:sum(r.get("status")==state for r in attempts) for state in sorted({r.get("status") for r in attempts})},"issues":issues,"not_verified":["physical apparatus behavior","patient validity","every visual movie pixel","external independent simulator reproduction"],"inputs":{"RUN_RESULTS.json":sha(OUT/"RUN_RESULTS.json"),"PREREGISTERED_SPEC.json":sha(OUT/"PREREGISTERED_SPEC.json")}}
    dump(OUT/"EXHAUSTIVE_TRACE_QA.json",result);print(json.dumps(result))
if __name__=="__main__":main()
