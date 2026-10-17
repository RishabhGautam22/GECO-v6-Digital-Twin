#!/usr/bin/env python3
"""Independent full-trace numerical audit; imports no study/production code."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib,json,gzip,itertools,sys,datetime
import numpy as np
import pandas as pd
R=Path(__file__).resolve().parents[2];P=R/'03_EXPERIMENTS/supplement_fasting';O=R/'08_REVIEW_AND_QA/filter/supplement_cross_review';O.mkdir(exist_ok=True)
SPEC=json.loads((P/'PREREGISTERED_SPEC.json').read_text());N=SPEC['steps'];DT=SPEC['dt_min'];START=SPEC['fault_start_step'];END=SPEC['fault_end_step_exclusive']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(path):
    with gzip.open(path,'rt') as f:return json.load(f)

def streak_length(mask):
    a=np.flatnonzero(np.diff(np.r_[False,mask,False]))
    return int(np.max(a[1::2]-a[::2],initial=0))

def one_group(rows):
    errors=[];out=[];reference_cache={}
    for row in rows:
        trace_path=R/row['trace_path'];trace=read(trace_path);c=trace['columns'];pid=row['run_id']
        def err(field,got,expected):errors.append({'mode':row['mode'],'run_id':pid,'field':field,'computed':got,'published':expected})
        if sha(trace_path)!=row['trace_sha256']:err('sha256',sha(trace_path),row['trace_sha256'])
        for key,values in c.items():
            if len(values)!=N:err('denominator:'+key,len(values),N)
        if c['sample']!=list(range(N)):err('sample_order','invalid','0..575')
        if not np.allclose(c['t_min'],np.arange(N)*DT):err('start_clock','invalid','five-minute grid')
        if not np.allclose(c['end_t_min'],(np.arange(N)+1)*DT):err('end_clock','invalid','five-minute grid')
        refpath=P/'references'/f"{row['unit_id']}_{row['seed']}_clean_reference.json.gz"
        if str(refpath) not in reference_cache:reference_cache[str(refpath)]=read(refpath)
        rc=reference_cache[str(refpath)]['columns']
        u=np.asarray(c['actual_emitted_u']);mass=np.asarray(c['actual_emitted_g']);plant=np.asarray(c['virtual_plant_input_u']);ref=np.asarray(rc['actual_emitted_u'])
        if not np.isfinite(mass).all() or np.any(mass<0):err('physical_emitted_mass','invalid','finite nonnegative')
        if np.max(np.abs(mass/.1005-plant))>1e-10 or np.max(np.abs(u-plant))>1e-10:err('mass_to_plant','mismatch','same physical emission')
        g=np.asarray(c['true_glucose_mgdl']);gr=np.asarray(rc['true_glucose_mgdl']);req=np.asarray(c['requested_u']);auth=np.asarray(c['authorized_u'])
        if not np.isfinite(g).all():err('glucose','nonfinite','finite')
        if not np.array_equal(req,rc['requested_u']) or not np.array_equal(c['carbs_g'],rc['carbs_g']):err('common_tape','mismatch','identical request/meal tape')
        if not np.all(np.asarray(c['carbs_g'])==0):err('fasting_carbs','nonzero','zero')
        if not np.all(req==req[0]):err('constant_request','variable','constant')
        comp=trace['metadata']['compensation'];target=comp['target_equilibrium_basal_u'];chosen=comp['requested_constant_u']
        grid=np.arange(61)/200.
        nominal=np.where(grid>0,1.015*grid+.0015/.1005,0.)
        best=grid[np.argmin(np.abs(nominal-target))]
        if abs(chosen-best)>1e-12:err('compensation_nearest_microstep',float(best),chosen)
        expected_nominal=0. if chosen==0 else round(chosen*200)/200.*1.015+.0015/.1005
        supplemental={'total_requested_u':float(req.sum()),'total_authorized_u':float(auth.sum()),
                      'compensated_zero_request_slots':int(np.count_nonzero(req==0)),
                      'physical_error_vs_equilibrium_target_u':float(u.sum()-target*N),
                      'requested_constant_u':chosen,'target_equilibrium_basal_u':target,
                      'nominal_emitted_u_per_step':expected_nominal,
                      'nominal_quantization_residual_u_per_step':expected_nominal-target,
                      'nominal_bias_48h_u':(expected_nominal-target)*N,
                      'compensated_zero_command':chosen==0}
        off=np.asarray(c['state_before_emission'])=='LATCHED';no_flow=(u<=1e-12)&(req>0)
        trips=np.flatnonzero(c['trip_event']);positive=u-ref
        calc={'total_emitted_u':float(u.sum()),'stepwise_excess_vs_clean_u':float(positive[positive>0].sum()),
              'stepwise_deficit_vs_clean_u':float(-positive[positive<0].sum()),'net_emission_difference_u':float(positive.sum()),
              'longest_interruption_min':streak_length(no_flow)*DT,'total_interruption_min':int(no_flow.sum())*DT,
              'total_commanded_latch_exposure_min':int(off.sum())*DT,'end_state_latched_samples':int(np.count_nonzero(c['cutoff'])),
              'glucose_rmse_vs_clean':float(np.linalg.norm(g-gr)/np.sqrt(N)),
              'glucose_mean_difference_vs_clean':float((g-gr).sum()/N),'minimum_true_glucose_mgdl':float(g.min()),'maximum_true_glucose_mgdl':float(g.max()),
              'trip_count':len(trips),'reset_count':int(np.count_nonzero(c['reset_event'])),
              'first_trip_latency_min':None if not len(trips) else float(c['end_t_min'][trips[0]]-START*DT),
              'trip_before_fault':bool(len(trips) and trips[0]<START),
              'invalid_physiology_samples':int(N-np.count_nonzero(c['plant_valid'])),
              'clean_reference_invalid_samples':int(N-np.count_nonzero(rc['plant_valid']))}
        for name,mask,refmask in [('time_below54_pct',g<54,gr<54),('time_below70_pct',g<70,gr<70),
                                  ('time70to180_pct',(g>=70)&(g<=180),(gr>=70)&(gr<=180)),
                                  ('time_above180_pct',g>180,gr>180),('time_above250_pct',g>250,gr>250)]:
            calc[name]=float(np.count_nonzero(mask)*100/N)
            calc[name+'_difference_vs_clean_pp']=float((np.count_nonzero(mask)-np.count_nonzero(refmask))*100/N)
        for name in ['negative_egp_evaluator_only','plasma_glucose_clamped','interstitial_glucose_clamped','remote_action_clamped']:
            calc[name+'_samples']=int(np.count_nonzero(c[name]))
        good=(~np.asarray(c['cutoff'],dtype=bool))&(auth>=.95*req)
        windows=np.lib.stride_tricks.sliding_window_view(good,6).all(axis=1)
        demand=np.lib.stride_tricks.sliding_window_view(req>0,6).any(axis=1)
        candidates=np.flatnonzero(windows & demand);candidates=candidates[candidates>=END]
        onset=None if not len(candidates) else int(candidates[0]-END)*DT
        calc.update(post_fault_recovery_latency_min=onset,recovery_window_onset_latency_min=onset,
                    recovery_window_confirmed_latency_min=None if onset is None else onset+6*DT,
                    recovery_censored=onset is None,recovery_latency_restricted_min=(N-END)*DT if onset is None else onset)
        calc.update(supplemental)
        for key,computed in calc.items():
            published=row[key]
            if computed is None or published is None:
                if computed!=published:err(key,computed,published)
            elif isinstance(computed,(bool,np.bool_)):
                if computed!=published:err(key,bool(computed),published)
            elif not np.isclose(computed,published,rtol=1e-10,atol=1e-9):err(key,float(computed),published)
        out.append({k:row[k] for k in ['run_id','unit_id','family','seed','condition','arm','stop_model','mode']}|calc|{'numerical_reset_count':c['sensor_quality'].count('numerical_reset'),'gap_reset_count':c['sensor_quality'].count('gap_reset'),'trace_sha256':row['trace_sha256'],'reference_path':str(refpath.relative_to(R))})
    return out,errors


def main():
    rows=json.loads((P/'RUN_RESULTS.json').read_text());units=json.loads((P/'SYNTHETIC_PARAMETER_SPLIT.json').read_text())
    receipt=json.loads((P/'EXECUTION_MANIFEST.json').read_text());actual=[];groups={}
    for r in rows:
        r['stop_model']='one_sample_baseline'
        actual.append((r['unit_id'],r['seed'],r['condition'],r['arm']))
        groups.setdefault((r['unit_id'],r['seed']),[]).append(r)
    expected=[(u['unit_id'],seed,condition,arm) for u in units if u['split']=='locked_test'
              for seed,condition,arm in itertools.product(SPEC['noise_meal_seeds'],SPEC['conditions'],SPEC['arms'])]
    coverage={'expected_runs':len(expected),'actual_rows':len(actual),'unique_rows':len(set(actual)),
              'missing':[list(k) for k in sorted(set(expected)-set(actual))],
              'unexpected':[list(k) for k in sorted(set(actual)-set(expected))],
              'manifest_failed_runs':receipt['failed_runs'],'manifest_source_unchanged':receipt['source_unchanged']}
    allrows=[];errors=[]
    with ProcessPoolExecutor(max_workers=4) as pool:
        for i,f in enumerate(as_completed([pool.submit(one_group,g) for g in groups.values()]),1):
            a,e=f.result();allrows+=a;errors+=e
    df=pd.DataFrame(allrows).sort_values('run_id');df.to_csv(O/'INDEPENDENT_RECOMPUTED_METRICS.csv',index=False)
    summary={'coverage':coverage,'trace_rows_audited':len(df),'sample_slots_audited':int(len(df)*N),
             'metric_or_integrity_discrepancies':len(errors),'errors':errors,
             'numerical_reset_count':int(df.numerical_reset_count.sum()),'gap_reset_count':int(df.gap_reset_count.sum()),
             'source_hashes':{'script':sha(__file__),'run_results':sha(P/'RUN_RESULTS.json'),'execution_manifest':sha(P/'EXECUTION_MANIFEST.json')},
             'runtime':sys.version,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
             'method':'No simulation/production helper imports. All traces, constant request/zero meal checks, full-grid nearest nominal equilibrium compensation check; previous review metrics reused independently.'}
    (O/'TRACE_AUDIT.json').write_text(json.dumps(summary,indent=2)+'\n')
    metrics=['stepwise_excess_vs_clean_u','stepwise_deficit_vs_clean_u','total_interruption_min','recovery_latency_restricted_min',
             'time_below54_pct','time_below70_pct','time70to180_pct','time_above180_pct','time_above250_pct']
    rng=np.random.default_rng(202609073);comparisons=[]
    for (family,condition),block in df.groupby(['family','condition']):
        for left,right in [('full','masscusum'),('masscusum','simple'),('full','simple')]:
            aname,bname=left+'_supervised',right+'_supervised'
            b=block[block.arm.isin([aname,bname])]
            for metric in metrics:
                means=b.groupby(['unit_id','arm'])[metric].mean().unstack()
                delta=(means[aname]-means[bname]).to_numpy();boots=delta[rng.integers(0,len(delta),(4096,len(delta)))].mean(axis=1)
                lo,hi=np.quantile(boots,[.025,.975])
                comparisons.append({'family':family,'condition':condition,'contrast':left+'_minus_'+right,'metric':metric,
                    'parameter_units':len(delta),'seeds_per_unit':2,'left_unit_mean':float(means[aname].mean()),'right_unit_mean':float(means[bname].mean()),
                    'paired_mean_difference':float(delta.mean()),'bootstrap95_low':float(lo),'bootstrap95_high':float(hi),
                    'negative_units':int((delta<-1e-9).sum()),'tie_units':int((np.abs(delta)<=1e-9).sum()),'positive_units':int((delta>1e-9).sum())})
    pd.DataFrame(comparisons).to_csv(O/'INDEPENDENT_PAIRED_UNIT_COMPARISONS.csv',index=False)
    domain=[]
    for family,b in df.groupby('family'):
        clean=b[b.condition=='clean']
        domain.append({'family':family,'runs':len(b),'invalid_runs':int((b.invalid_physiology_samples>0).sum()),
            'invalid_samples':int(b.invalid_physiology_samples.sum()),'negative_egp_samples':int(b.negative_egp_evaluator_only_samples.sum()),
            'remote_action_clamp_samples':int(b.remote_action_clamped_samples.sum()),'plasma_clamp_samples':int(b.plasma_glucose_clamped_samples.sum()),
            'interstitial_clamp_samples':int(b.interstitial_glucose_clamped_samples.sum()),'zero_command_units':int(b.loc[b.compensated_zero_command,'unit_id'].nunique()),
            'minimum_g':float(b.minimum_true_glucose_mgdl.min()),'maximum_g':float(b.maximum_true_glucose_mgdl.max()),
            'clean_minimum_g':float(clean.minimum_true_glucose_mgdl.min()),'clean_maximum_g':float(clean.maximum_true_glucose_mgdl.max()),
            'clean_runs':len(clean),'clean_runs_with_trips':int((clean.trip_count>0).sum()),'recovery_censored_runs':int(b.recovery_censored.sum())})
    (O/'DOMAIN_AND_CLEAN_SUMMARY.json').write_text(json.dumps(domain,indent=2)+'\n')
    print(json.dumps(summary,indent=2));print(json.dumps(domain,indent=2))

if __name__=='__main__':main()
