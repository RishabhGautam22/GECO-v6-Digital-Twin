"""Read-only complete trace checks; independently reviewed endpoints are separate."""
import gzip,json
from collections import Counter
import numpy as np
from .study import OUT,ROOT,load,dump,sha,timestamp

def read(path):
    with gzip.open(path,"rt") as f:return json.load(f)

def main():
    rows=load(OUT/"RUN_RESULTS.json");spec=load(OUT/"PREREGISTERED_SPEC.json");issues=[];samples=0;identities=set();quality=Counter();references={}
    for path in (OUT/"references").glob("*.json.gz"):
        t=read(path);m=t["metadata"];references[(m["unit_id"],m["seed"])]=t["columns"]
    for row in rows:
        rid=row["run_id"]
        if rid in identities:issues.append({"run_id":rid,"issue":"duplicate identity"})
        identities.add(rid);path=ROOT/row["trace_path"]
        if sha(path)!=row["trace_sha256"]:issues.append({"run_id":rid,"issue":"hash mismatch"});continue
        t=read(path);c=t["columns"];r=references[(row["unit_id"],row["seed"])];n=len(c["sample"]);a=np.array(c["actual_emitted_u"]);ref=np.array(r["actual_emitted_u"])
        quality.update((row["arm"]+":"+str(v)) for v in c["sensor_quality"])
        checks={"sample_count":n==576,"column_lengths":all(len(v)==n for v in c.values()),"sample_sequence":c["sample"]==list(range(n)),"start_clock":c["t_min"]==[k*5. for k in range(n)],"end_clock":c["end_t_min"]==[(k+1)*5. for k in range(n)],"zero_meals":not any(c["carbs_g"]),"fixed_constant_requests":len(set(c["requested_u"]))==1,"clean_request_match":c["requested_u"]==r["requested_u"],"compensated_request":c["requested_u"]==[row["requested_constant_u"]]*n,"physical_to_plant":np.allclose(np.array(c["actual_emitted_g"])/.1005,c["virtual_plant_input_u"],atol=1e-13,rtol=0),"no_negative_emission":np.all(a>=0),"command_authority":all(0<=v<=min(.3,u)+1e-12 for u,v in zip(c["requested_u"],c["authorized_u"])),"latched_means_no_flow":all(state!="LATCHED" or abs(mass)<1e-13 for state,mass in zip(c["state_before_emission"],c["actual_emitted_g"])),"finite_evaluator":np.isfinite(c["true_glucose_mgdl"]).all(),"compensated_zero_count":row["compensated_zero_request_slots"]==sum(u==0 for u in c["requested_u"]),"excess_endpoint":abs(row["stepwise_excess_vs_clean_u"]-np.maximum(a-ref,0).sum())<1e-10,"deficit_endpoint":abs(row["stepwise_deficit_vs_clean_u"]-np.maximum(ref-a,0).sum())<1e-10,"domain_count":row["invalid_physiology_samples"]==sum(not x for x in c["plant_valid"])}
        for k,reset in enumerate(c["reset_event"]):
            if reset:
                if not (k>0 and k%24==0 and c["operator_authorized"][k] and c["t_min"][k]-c["last_trip_end_t_min"][k-1]>=30 and abs(sum(c["local_measured_delta_g"][k-6:k]))<=.01 and c["reported_cgm_mgdl"][k] is not None):checks["recovery_visible_eligibility"]=False
        if row["arm"]=="masscusum_supervised":
            checks["mass_only_score"]=c["detector_score"]==c["mass_cusum"]
            checks["mass_no_physiology"]=all(v is None for v in c["innovation_z"]+c["due_forecast_z"]+c["forecast30_mgdl"])
        for name,ok in checks.items():
            if not ok:issues.append({"run_id":rid,"issue":name})
        samples+=n
    attempts=[json.loads(line) for path in (OUT/"attempts").glob("*.jsonl") for line in path.read_text().splitlines() if line.strip()]
    cal=[json.loads(line) for line in (OUT/"calibration_attempts.jsonl").read_text().splitlines() if line.strip()]
    for key,actual,expected in (("runs",len(rows),2048),("references",len(references),64),("attempts",len(attempts),2112),("calibration",len(cal),16)):
        if actual!=expected:issues.append({"issue":key+" count","actual":actual,"expected":expected})
    result=dict(generated_utc=timestamp(),status="PASS" if not issues else "FAIL",completed_traces_checked=len(rows),samples_checked=samples,references=len(references),calibration_attempts=len(cal),attempt_records_including_references=len(attempts),attempt_status_counts=dict(Counter(x["status"] for x in attempts)),production_sensor_quality_by_arm=dict(quality),issues=issues,inputs={name:sha(OUT/name) for name in ("RUN_RESULTS.json","PREREGISTERED_SPEC.json","FROZEN_SUPPLEMENT_CONFIG.json")},limitations=["Not a physical or clinical validation","Endpoint helper remains shared; independent all-trace reviewer receipt is separate","Verification-trip priority can obscure a standalone failed-verification event in trace; metadata retained"])
    dump(OUT/"EXHAUSTIVE_TRACE_QA.json",result);print(json.dumps(result))
if __name__=="__main__":main()
