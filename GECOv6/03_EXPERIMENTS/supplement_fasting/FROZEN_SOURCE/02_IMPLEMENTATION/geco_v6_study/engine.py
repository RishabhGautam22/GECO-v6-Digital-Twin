"""Offline shared-authority study engine, with explicit evaluator/monitor separation."""
from dataclasses import asdict
import math
import numpy as np
from geco_v4.physiology import PhysiologyTwin, TwinParams
from geco_v4.controller import ResearchController
from .plants import make_plant

GPU=.1005

def twin_from_config(config, basal, glucose=120.):
    twin=PhysiologyTwin(TwinParams(**config["params"]),r_std=config.get("r_std",9.),forecast_policy=config["forecast_policy"])
    twin.configure_calibration(config)
    twin.reset(glucose,basal)
    return twin

def exogenous(unit,seed,steps=576):
    # Family/unit identity changes random stream, while paired arms share arrays.
    index=int(unit["unit_id"].split("_")[-1])
    family=0 if unit["family"]=="geco_original" else 1
    rng=np.random.default_rng(np.random.SeedSequence([seed,index,family]))
    meals=np.zeros(steps)
    for day in range((steps+287)//288):
        for hour,grams in ((8,40),(13,60),(19,60)):
            at=day*288+hour*12+int(rng.integers(-3,4))
            if at<steps: meals[at]=grams*float(rng.uniform(.8,1.2))
    return {"carbs":meals,"cgm_noise":rng.normal(0,3,steps),"pump_noise":rng.normal(0,.0008,steps),"balance_noise":rng.normal(0,.003,(steps,5))}

class Accumulator:
    def __init__(self):self.pos=0.;self.neg=0.
    def update(self,z):
        if z is None or not math.isfinite(z):return max(self.pos,self.neg)
        z=float(np.clip(z,-6,6));self.pos=max(0,self.pos+z-.5);self.neg=max(0,self.neg-z-.5)
        return max(self.pos,self.neg)
    def reset(self):self.pos=self.neg=0.

class Detector:
    def __init__(self,kind,threshold,mass_sigma):
        self.kind=kind;self.threshold=threshold;self.mass_sigma=mass_sigma
        self.mass=Accumulator();self.phys=Accumulator()
    def reset(self):self.mass.reset();self.phys.reset()
    def observe(self,residual_g,z,z6):
        mass=self.mass.update(residual_g/self.mass_sigma)
        # Both CGM transforms form ONE channel, selected by absolute magnitude.
        zs=[v for v in (z,z6) if v is not None and math.isfinite(v)]
        phy=self.phys.update(max(zs,key=abs) if zs else None)
        simple=abs(residual_g)/self.mass_sigma
        full=max(mass,math.sqrt(mass*phy) if zs else 0.)
        score=full if self.kind=="full" else simple
        return {"simple_score":simple,"full_score":full,"mass_cusum":mass,"physiology_cusum":phy,"score":score,"alarm":bool(score>self.threshold and self.kind in ("full","simple"))}

def expected_mass(u):
    return round(u*200)/200*GPU*1.015+.0015 if u>0 else 0.

def nominal_emission(u,noise):
    base=round(max(0.,u)*200)/200*GPU*1.015
    return max(0.,base+noise+.0015) if base>0 else 0.

def fault_fields(condition,active):
    if not active:return 1.,False,0.,False,False
    return (2. if condition.startswith("excess") else 1.,condition=="occlusion",.25 if condition=="stuck_on" else 0.,condition=="cgm_missing",condition=="excess_bias_report_mask")

def run(unit,seed,condition,arm,config,spec,clean=None,feedback=False,stop_model="one_sample_baseline",calibration=False):
    n=spec["steps"];dt=spec["dt_min"];start=spec["fault_start_step"];end=spec["fault_end_step_exclusive"]
    plant=make_plant(unit);noise=exogenous(unit,seed,n)
    controller=ResearchController(basal_u_per_step=plant.basal_u)
    kind=arm.split("_")[0];recovery="supervised" if arm.endswith("supervised") else "manual"
    need_twin=kind=="full" or clean is None or feedback or calibration
    twin=twin_from_config(config,plant.basal_u) if need_twin else None
    detector=Detector(kind,config.get("thresholds",{}).get(kind,math.inf),config.get("mass_sigma_g",.005143506785294255))
    state="RUN";latched_end_sample=-999;previous_request=0.;prev_u=0.;prev_carbs=0.
    cumulative_mass=0.;last_read=0.;rolling=[];local_deltas=[];missing_streak=0
    verify_mass=0.;verify_expected=0.;verify_count=0;probation=0;extra_power=0;tail_steps=0
    trip_count=reset_count=failed_verifications=0;first_trip=None;rows=[];scoremax={"full":0.,"simple":0.}
    physical_fault=condition in ("excess_2x","occlusion","stuck_on","excess_bias_25","excess_bias_report_mask")
    for k in range(n):
        active=start<=k<end
        factor,occlusion,stuck,missing,mask=fault_fields(condition,active)
        true_start=plant.glucose
        y=float(np.clip(plant.sensor+noise["cgm_noise"][k],20,600))
        if active and condition=="cgm_bias_40":y+=40
        if active and condition in ("excess_bias_25","excess_bias_report_mask"):y+=25
        if missing:y=None
        missing_streak=missing_streak+1 if y is None else 0
        z=z6=forecast=None;quality="missing" if y is None else "ok"
        if twin is not None:
            if k>0:
                out=twin.update(y,prev_u,prev_carbs)
                z=out.standardized_innovation if out.innovation_valid else None
                z6=twin.last_forecast_residual_z;quality=out.quality
            forecast=twin.forecast(6)
        requested=float(controller.request(y,forecast)) if clean is None or feedback else float(clean["requested_u"][k])
        requested=min(.3,max(0.,requested))
        operator_authorized=bool(k>0 and k%24==0)
        reset_event=False;trip_event=False;trip_reason=""
        quiet=len(local_deltas)>=6 and abs(sum(local_deltas[-6:]))<=.01
        # Recovery sees ONLY observations/operator schedule, never active/end/plant.
        if state=="LATCHED" and operator_authorized and k-latched_end_sample>=6 and quiet and y is not None:
            reset_event=True;reset_count+=1;detector.reset();rolling=[]
            if recovery=="supervised":
                state="VERIFY";verify_count=0;verify_mass=verify_expected=0.
            else:state="RUN"
        beginning_state=state
        authorized=0. if state=="LATCHED" else min(requested,.08) if state in ("VERIFY","PROBATION") else requested
        # Privileged fault oracle is a labelled evaluator reference, not a detector.
        if arm=="oracle" and active and physical_fault:authorized=0.
        enabled=state!="LATCHED" and not (arm=="oracle" and active and physical_fault)
        if extra_power>0:
            enabled=True;power_request=previous_request;extra_power-=1
        else:power_request=authorized
        moved=nominal_emission(power_request*factor,noise["pump_noise"][k]) if enabled and not occlusion else 0.
        if enabled:moved+=stuck*GPU*1.015
        if tail_steps>0:
            moved+=.02*GPU;tail_steps-=1
        cumulative_mass+=moved
        reading=round(float(np.median(cumulative_mass+noise["balance_noise"][k]))/.01)*.01
        delta=reading-last_read;last_read=reading;local_deltas.append(delta)
        reported=authorized*GPU if mask else delta
        exp=expected_mass(authorized)
        residual=reported-exp
        signals=detector.observe(residual,z,z6)
        if k>=spec["warmup_steps"]:
            scoremax["full"]=max(scoremax["full"],signals["full_score"])
            scoremax["simple"]=max(scoremax["simple"],signals["simple_score"])
        rolling.append((delta,authorized*GPU*1.05));rolling=rolling[-12:]
        local_trip=delta>authorized*GPU*1.05+.03 or sum(d-b for d,b in rolling)>.05
        statistical_trip=signals["alarm"] and k>=spec["warmup_steps"]
        quality_trip=missing_streak>=6
        verification_trip=False
        if state=="VERIFY":
            verify_count+=1;verify_mass+=delta;verify_expected+=exp
            if y is None:verification_trip=True
            elif verify_count>=3:
                if verify_expected>0 and abs(verify_mass-verify_expected)<=.012:
                    state="PROBATION";probation=0
                else:verification_trip=True
            if verification_trip:failed_verifications+=1
        elif state=="PROBATION":
            probation+=1
            if probation>=6:state="RUN"
        trigger=local_trip or quality_trip or statistical_trip or verification_trip
        if calibration:trigger=False
        if trigger and state!="LATCHED":
            state="LATCHED";latched_end_sample=k+1;trip_event=True;trip_count+=1
            if first_trip is None:first_trip=k
            trip_reason="local_budget" if local_trip else "sensor_quality" if quality_trip else "verification_failed" if verification_trip else "statistical"
            if stop_model=="one_additional_sample_of_power":extra_power=1
            if stop_model=="residual_tail_0.02U_per_step_for3steps":tail_steps=3
            detector.reset()
        emitted_u=moved/GPU
        g,sensor=plant.step(emitted_u,float(noise["carbs"][k]))
        if not np.isfinite(plant.x).all():raise FloatingPointError(f"nonfinite plant state at{k}")
        rows.append({"sample":k,"t_min":k*dt,"end_t_min":(k+1)*dt,"requested_u":requested,"authorized_u":authorized,"actual_emitted_g":moved,"actual_emitted_u":emitted_u,"local_measured_delta_g":delta,"network_reported_delta_g":reported,"virtual_plant_input_u":emitted_u,"true_glucose_mgdl":g,"true_glucose_start_mgdl":true_start,"reported_cgm_mgdl":y,"carbs_g":float(noise["carbs"][k]),"forecast30_mgdl":forecast,"innovation_z":z,"due_forecast_z":z6,"sensor_quality":quality,"detector_score":signals["score"],"full_score":signals["full_score"],"simple_score":signals["simple_score"],"mass_cusum":signals["mass_cusum"],"physiology_cusum":signals["physiology_cusum"],"detector_threshold":None if math.isinf(detector.threshold) else detector.threshold,"cutoff":state=="LATCHED","state_before_emission":beginning_state,"recovery_state":state,"trip_event":trip_event,"trip_reason":trip_reason,"local_trip_observed":bool(local_trip),"statistical_trip_observed":bool(statistical_trip),"operator_authorized":operator_authorized,"reset_event":reset_event,"fault_active_evaluator_only":active,"plant_valid":plant.valid})
        rows[-1].update(plant.diagnostics)
        rows[-1]["last_trip_end_t_min"]=None if latched_end_sample<0 else latched_end_sample*dt
        previous_request=authorized;prev_u=authorized;prev_carbs=float(noise["carbs"][k])
    columns={key:[row[key] for row in rows] for key in rows[0]}
    return {"metadata":{"unit_id":unit["unit_id"],"family":unit["family"],"seed":seed,"condition":condition,"arm":arm,"feedback":feedback,"stop_model":stop_model,"basal_u_per_step":plant.basal_u,"plant_params":asdict(plant.p),"trip_count":trip_count,"reset_count":reset_count,"failed_verification_count":failed_verifications,"first_trip_step":first_trip,"score_maxima":scoremax},"columns":columns}

def metrics(trace,reference,spec):
    c=trace["columns"];r=reference["columns"];dt=spec["dt_min"];n=len(c["sample"])
    emitted=np.array(c["actual_emitted_u"]);clean=np.array(r["actual_emitted_u"])
    glucose=np.array(c["true_glucose_mgdl"]);gref=np.array(r["true_glucose_mgdl"])
    interruption=(np.array(c["requested_u"])>0)&(emitted<=1e-12)
    longest=streak=0
    for flag in interruption:streak=streak+1 if flag else 0;longest=max(longest,streak)
    end=spec["fault_end_step_exclusive"];recovered=None
    for k in range(end,n-5):
        good=[not c["cutoff"][j] and c["authorized_u"][j]>=.95*c["requested_u"][j] for j in range(k,k+6)]
        if all(good) and any(c["requested_u"][j]>0 for j in range(k,k+6)):
            recovered=(k-end)*dt;break
    first=trace["metadata"]["first_trip_step"]
    out={"total_emitted_u":float(emitted.sum()),"stepwise_excess_vs_clean_u":float(np.maximum(emitted-clean,0).sum()),"stepwise_deficit_vs_clean_u":float(np.maximum(clean-emitted,0).sum()),"net_emission_difference_u":float((emitted-clean).sum()),"longest_interruption_min":longest*dt,"total_interruption_min":float(interruption.sum()*dt),"total_commanded_latch_exposure_min":sum(s=="LATCHED" for s in c["state_before_emission"])*dt,"end_state_latched_samples":sum(c["cutoff"]),"post_fault_recovery_latency_min":recovered,"recovery_window_onset_latency_min":recovered,"recovery_window_confirmed_latency_min":None if recovered is None else recovered+6*dt,"recovery_censored":recovered is None,"recovery_latency_restricted_min":(n-end)*dt if recovered is None else recovered,"time_below54_pct":float(np.mean(glucose<54)*100),"time_below70_pct":float(np.mean(glucose<70)*100),"time70to180_pct":float(np.mean((glucose>=70)&(glucose<=180))*100),"time_above180_pct":float(np.mean(glucose>180)*100),"time_above250_pct":float(np.mean(glucose>250)*100),"glucose_rmse_vs_clean":float(np.sqrt(np.mean((glucose-gref)**2))),"glucose_mean_difference_vs_clean":float(np.mean(glucose-gref)),"minimum_true_glucose_mgdl":float(glucose.min()),"maximum_true_glucose_mgdl":float(glucose.max()),"first_trip_latency_min":None if first is None else ((first+1)-spec["fault_start_step"])*dt,"trip_before_fault":first is not None and first<spec["fault_start_step"],"invalid_physiology_samples":sum(not x for x in c["plant_valid"]),"clean_reference_invalid_samples":sum(not x for x in r["plant_valid"])}
    for key in ("trip_count","reset_count","failed_verification_count"):out[key]=trace["metadata"][key]
    for key in ("negative_egp_evaluator_only","plasma_glucose_clamped","interstitial_glucose_clamped","remote_action_clamped"):
        out[key+"_samples"]=sum(c[key])
    for label,mask in (("time_below54_pct",gref<54),("time_below70_pct",gref<70),("time70to180_pct",(gref>=70)&(gref<=180)),("time_above180_pct",gref>180),("time_above250_pct",gref>250)):
        out[label+"_difference_vs_clean_pp"]=out[label]-float(np.mean(mask)*100)
    return out
