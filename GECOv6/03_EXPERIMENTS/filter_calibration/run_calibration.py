#!/usr/bin/env python3
"""Frozen, two-invocation V6 fit/tune then internal-test evaluation.

Run with /opt/anaconda3/bin/python; no test metric is computed by the fit mode.
"""
from pathlib import Path
import sys, os, json, hashlib, datetime, time, platform, traceback, argparse
from dataclasses import asdict
from concurrent.futures import ProcessPoolExecutor, as_completed
ROOT=Path(__file__).resolve().parents[2]
IMPL=ROOT/'02_IMPLEMENTATION'; OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(IMPL))
import numpy as np
import pandas as pd
import scipy
from geco_v4.datasets import load_hupa_ucm,load_d1namo
from geco_v4.calibrate import (calibrate_participant,eligibility_report,calibration_split,
    alarm_summary,_due_errors,_lag1)
from geco_v4.physiology import TwinParams,evaluate_causal_forecasts


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def clean(x):
    if isinstance(x,dict):return {str(k):clean(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [clean(v) for v in x]
    if isinstance(x,np.ndarray):return clean(x.tolist())
    if isinstance(x,(np.integer,)):return int(x)
    if isinstance(x,(float,np.floating)):return float(x) if np.isfinite(x) else None
    return x

def write_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(clean(data),indent=2,allow_nan=False)+'\n');temp.replace(path)

def source_hashes():
    paths=[IMPL/'geco_v4'/n for n in ('physiology.py','calibrate.py','datasets.py','detectors.py','numerics.py')]
    paths += [Path(__file__),OUT/'PREREGISTRATION.md',OUT/'PREREGISTRATION_RECEIPT.json']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths}

def runtime():
    try:import numba;nv=numba.__version__
    except ImportError:nv=None
    return {'python':sys.version,'executable':sys.executable,'numpy':np.__version__,'scipy':scipy.__version__,
            'pandas':pd.__version__,'numba':nv,'platform':platform.platform(),'argv':sys.argv,
            'model_identity':'unknown','utc':now()}

def load():
    raw=IMPL/'data/raw'
    return load_hupa_ucm(str(raw/'HUPA-UCM'))+load_d1namo(str(raw/'D1NAMO'))

def array_hash(s):
    h=hashlib.sha256()
    for a in (s.timestamps,s.cgm,s.basal,s.bolus,s.carbs):
        a=np.ascontiguousarray(a);h.update(str(a.dtype).encode());h.update(str(a.shape).encode());h.update(a.tobytes())
    return h.hexdigest()

def fit_one(s,max_iter):
    started=time.perf_counter();elig=eligibility_report(s)
    record={'participant':s.participant_id,'source':s.source,'array_sha256':array_hash(s),
            'eligibility':elig,'started_utc':now(),'status':'excluded'}
    if elig['eligible']:
        try:
            params,validation,_=calibrate_participant(s,max_iter=max_iter)
            record.update(status='frozen',params=asdict(params),validation=asdict(validation))
        except Exception as e:
            record.update(status='failed',error_type=type(e).__name__,error=str(e),
                          diagnostics=getattr(e,'fit_diagnostics',{}),traceback=traceback.format_exc())
    record['elapsed_seconds']=time.perf_counter()-started
    return record

def fit(args):
    if (OUT/'FIT_FREEZE_RECEIPT.json').exists():raise RuntimeError('Existing fit freeze is immutable; do not rerun over it')
    sources=source_hashes();series=load()
    inventory=[{'participant':s.participant_id,'source':s.source,'array_sha256':array_hash(s),**eligibility_report(s)} for s in series]
    write_json(OUT/'INPUT_ARRAY_MANIFEST.json',inventory)
    write_json(OUT/'FIT_INVOCATION.json',{'runtime':runtime(),'source_hashes':sources,'max_nfev_per_start':args.max_iter,'workers':args.workers})
    records={};started=time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures={ex.submit(fit_one,s,args.max_iter):s.participant_id for s in series}
        for f in as_completed(futures):
            record=f.result();pid=record['participant'];records[pid]=record
            write_json(OUT/'participants'/f'{pid}.json',record)
            print(pid,record['status'],round(record['elapsed_seconds'],2),flush=True)
    if source_hashes()!=sources:raise RuntimeError('Source changed during calibration; do not freeze mixed results')
    ordered={s.participant_id:records[s.participant_id] for s in series}
    write_json(OUT/'FROZEN_CALIBRATION.json',ordered)
    write_json(OUT/'FIT_FREEZE_RECEIPT.json',{'frozen_utc':now(),'source_hashes':sources,
        'frozen_calibration_sha256':sha(OUT/'FROZEN_CALIBRATION.json'),
        'array_manifest_sha256':sha(OUT/'INPUT_ARRAY_MANIFEST.json'),'runtime':runtime(),
        'counts':{v:sum(r['status']==v for r in records.values()) for v in ('frozen','excluded','failed')},
        'elapsed_seconds':time.perf_counter()-started,'test_outcomes_computed':False})
    print('FIT FREEZE COMPLETE',flush=True)


def test(args):
    if (OUT/'TEST_RESULTS.json').exists():raise RuntimeError('Existing locked evaluation is immutable')
    freeze=json.loads((OUT/'FIT_FREEZE_RECEIPT.json').read_text())
    if sha(OUT/'FROZEN_CALIBRATION.json')!=freeze['frozen_calibration_sha256']:raise RuntimeError('Changed frozen calibration')
    if source_hashes()!=freeze['source_hashes']:raise RuntimeError('Changed source after calibration freeze')
    records=json.loads((OUT/'FROZEN_CALIBRATION.json').read_text());results={}
    write_json(OUT/'TEST_INVOCATION.json',{'runtime':runtime(),'fit_freeze_sha256':sha(OUT/'FIT_FREEZE_RECEIPT.json')})
    started=time.perf_counter()
    for series in load():
        pid=series.participant_id;record=records[pid]
        if array_hash(series)!=record['array_sha256']:raise RuntimeError('Changed arrays')
        if record['status']!='frozen':
            results[pid]={'status':'not_evaluated','reason':record['status']};continue
        test=calibration_split(series)[2];v=record['validation'];p=TwinParams(**record['params'])
        e=evaluate_causal_forecasts(p,test.cgm,test.insulin,test.carbs,forecast_policy=v['forecast_policy'],
                                   ar1_rho=v['ar1_rho'],inflation=v['innovation_inflation'],r_std=v['r_std'])
        kind=v['forecast_policy']['kind'];z6=_due_errors(e,kind,len(test.cgm))/v['sigma6_mgdl']
        a1=alarm_summary(e['z'],v['cusum_drift'],v['cusum_threshold'])
        a6=alarm_summary(z6,v['cusum_drift'],v['cusum6_threshold'])
        union=sorted(set(a1['alarm_indices'])|set(a6['alarm_indices']))
        z=e['z'][np.isfinite(e['z'])];zf=z6[np.isfinite(z6)]
        results[pid]={'status':'evaluated','source':series.source,'selected_policy':kind,
            'metrics':e['metrics'],'selected_metrics':e['metrics'][kind],'pair_coverage':e['pair_coverage'],
            'n_slots':len(test.cgm),'observed_cgm':int(np.isfinite(test.cgm).sum()),
            'innovation_coverage95':float(np.mean(np.abs(z)<=1.96)),
            'selected_forecast_coverage95':float(np.mean(np.abs(zf)<=1.96)),
            'innovation_mean':float(np.mean(z)),'innovation_std':float(np.std(z)),
            'innovation_lag1':_lag1(e['z']),'forecast_lag1':_lag1(z6),
            'alarm_innovation':a1,'alarm_forecast':a6,'alarm_union_count':len(union),
            'alarm_union_episodes_per_calendar_day':len(union)/test.n_days,
            'filter_reset_slots':np.flatnonzero(e['reset_flags']).tolist()}
        origins=e['origins'];j=('mechanistic','persistence','trend').index(kind)
        pd.DataFrame({'origin_index':origins,'target_index':origins+6,
            'origin_timestamp':test.timestamps[origins],'target_timestamp':test.timestamps[origins+6],
            'target_cgm':test.cgm[origins+6],
            'mechanistic':e['predictions'][origins,0],'persistence':e['predictions'][origins,1],
            'trend':e['predictions'][origins,2],'selected':e['predictions'][origins,j]}).to_csv(OUT/'test_predictions'/f'{pid}.csv',index=False)
        print(pid,'test evaluated',len(origins),'pairs',flush=True)
    write_json(OUT/'TEST_RESULTS.json',results)
    write_json(OUT/'TEST_RECEIPT.json',{'utc':now(),'runtime':runtime(),'elapsed_seconds':time.perf_counter()-started,
        'test_results_sha256':sha(OUT/'TEST_RESULTS.json'),'fit_freeze_sha256':sha(OUT/'FIT_FREEZE_RECEIPT.json'),
        'forecast_csv_hashes':{p.name:sha(p) for p in sorted((OUT/'test_predictions').glob('*.csv'))}})


def report(args):
    records=json.loads((OUT/'FROZEN_CALIBRATION.json').read_text());test=json.loads((OUT/'TEST_RESULTS.json').read_text())
    rows=[]
    for pid,r in test.items():
        if r['status']!='evaluated':continue
        v=records[pid]['validation']
        row={'participant':pid,'source':r['source'],'selected_policy':r['selected_policy'],
             'pair_coverage':r['pair_coverage'],'test_pairs':r['selected_metrics']['n_pairs'],
             'innovation_coverage95':r['innovation_coverage95'],'forecast_coverage95':r['selected_forecast_coverage95'],
             'test_alarm_union_per_day':r['alarm_union_episodes_per_calendar_day'],
             'tune_alarm_union_per_day':v['alarm_summary_val']['union_episodes_per_calendar_day'],
             'inflation':v['innovation_inflation'],'rho':v['ar1_rho'],'sigma6':v['sigma6_mgdl'],
             'jacobian_condition':v['fit_diagnostics']['jacobian_condition'],
             'bound_proximity_1pct':','.join(v['fit_diagnostics']['bound_proximity_1pct'])}
        for k in ('mechanistic','persistence','trend'):
            row[k+'_rmse']=r['metrics'][k]['rmse'];row[k+'_tune_rmse']=v['forecast_metrics_val'][k]['rmse']
        row['selected_rmse']=r['selected_metrics']['rmse'];row['selected_mae']=r['selected_metrics']['mae'];rows.append(row)
    df=pd.DataFrame(rows);df.to_csv(OUT/'PARTICIPANT_RESULTS.csv',index=False)
    rng=np.random.default_rng(20260907)
    aggregate={'n_evaluated':len(df),'status_counts':{k:sum(r['status']==k for r in records.values()) for k in ('frozen','failed','excluded')},
               'selection_counts':df.selected_policy.value_counts().to_dict(),'all_test_pairs':int(df.test_pairs.sum()),
               'participant_median':{k:float(df[k].median()) for k in df.select_dtypes(include='number').columns},
               'paired_rmse_comparisons':{},'interpretation':'Descriptive participant bootstrap; previously exposed internal tests, not external validation.'}
    for a,b in [('mechanistic','persistence'),('trend','persistence'),('selected','persistence'),('selected','mechanistic')]:
        d=(df[a+'_rmse']-df[b+'_rmse']).to_numpy();boot=np.mean(d[rng.integers(0,len(d),(10000,len(d)))],axis=1)
        aggregate['paired_rmse_comparisons'][a+'_minus_'+b]={'mean_difference_mgdl':float(d.mean()),
            'participant_bootstrap95':np.quantile(boot,[.025,.975]).tolist(),
            'better_count':int((d<-1e-9).sum()),'tie_count':int((np.abs(d)<=1e-9).sum()),'worse_count':int((d>1e-9).sum())}
    write_json(OUT/'AGGREGATE_RESULTS.json',aggregate)
    print(json.dumps(clean(aggregate),indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['fit','test','report']);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--max-iter',type=int,default=80)
    args=ap.parse_args();(OUT/'test_predictions').mkdir(exist_ok=True)
    {'fit':fit,'test':test,'report':report}[args.mode](args)
