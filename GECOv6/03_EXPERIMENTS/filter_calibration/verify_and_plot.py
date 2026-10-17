#!/usr/bin/env python3
"""Recompute metrics from exported prediction/target columns; draw source-linked figures."""
from pathlib import Path
import json,hashlib,sys,datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parent
OUT=P/'figures';OUT.mkdir(exist_ok=True)
h=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
test=json.loads((P/'TEST_RESULTS.json').read_text());frozen=json.loads((P/'FROZEN_CALIBRATION.json').read_text())
checks=[]
for pid,r in test.items():
    if r['status']!='evaluated':continue
    f=P/'test_predictions'/f'{pid}.csv';d=pd.read_csv(f)
    assert np.isfinite(d[['target_cgm','mechanistic','persistence','trend','selected']]).all().all()
    assert (d.target_index-d.origin_index==6).all()
    for name in ('mechanistic','persistence','trend','selected'):
        e=d[name].to_numpy()-d.target_cgm.to_numpy()
        rmse=float(np.sqrt(np.sum(e**2)/len(e)));mae=float(np.sum(np.abs(e))/len(e))
        target=r['selected_metrics'] if name=='selected' else r['metrics'][name]
        assert abs(rmse-target['rmse'])<1e-9 and abs(mae-target['mae'])<1e-9
        checks.append({'participant':pid,'policy':name,'pairs':len(e),'rmse_mgdl':rmse,'mae_mgdl':mae,'csv_sha256':h(f)})
(P/'INDEPENDENT_CSV_METRIC_CHECK.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'method':'Direct sums of squared/absolute exported prediction-minus-target errors; no original metric helper imported',
    'passed':True,'checks':checks},indent=2)+'\n')
df=pd.read_csv(P/'PARTICIPANT_RESULTS.csv').sort_values('participant')
df.to_csv(OUT/'FIGURE_PARTICIPANT_DATA.csv',index=False)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                     'svg.fonttype':'none','savefig.dpi':200,'axes.titlesize':13})
colors={'mechanistic':'#9A4F1E','persistence':'#677583','trend':'#0F7780','selected':'#164F3C'}
outputs=[]
def save(fig,name,caption):
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight');fig.savefig(OUT/f'{name}.pdf',bbox_inches='tight');fig.savefig(OUT/f'{name}.png',bbox_inches='tight');plt.close(fig)
    outputs.append({'name':name,'caption':caption,'files':{ext:h(OUT/f'{name}.{ext}') for ext in ('svg','pdf','png')}})
fig,ax=plt.subplots(figsize=(9.5,8.6));y=np.arange(len(df))
for i,k in enumerate(('mechanistic','persistence','selected')):
    ax.scatter(df[k+'_rmse'],y+(i-1)*.19,s=24,color=colors[k],label=k.capitalize(),zorder=3)
ax.set_yticks(y,df.participant);ax.invert_yaxis();ax.set_xlabel('30-minute CGM RMSE (mg/dL)');ax.set_xlim(left=0)
ax.grid(axis='x',alpha=.18);ax.legend(ncols=3,loc='lower right')
ax.set_title('Frozen causal forecasts on internal test segments\n31 participants; identical origin/target pairs for each policy',loc='left',pad=13)
fig.tight_layout()
save(fig,'F01_participant_forecast_rmse','Participant-specific matched-pair test RMSE. Selected policy is frozen from tune data (30 trend,1 persistence). Previously exposed internal test; not clinical/external validation.')
fig,(ax,bx)=plt.subplots(1,2,figsize=(10,5.4),gridspec_kw={'width_ratios':[1,1.05]})
for kind in ('mechanistic','selected'):
    ax.scatter(df.persistence_rmse,df[kind+'_rmse'],color=colors[kind],s=35,alpha=.85,label=kind.capitalize())
mx=max(df.mechanistic_rmse.max(),df.persistence_rmse.max())*1.07
ax.plot([0,mx],[0,mx],color='#777777',ls='--',lw=1);ax.set(xlim=(0,mx),ylim=(0,mx),xlabel='Persistence RMSE (mg/dL)',ylabel='Compared policy RMSE (mg/dL)')
ax.legend();ax.set_title('Each point is one participant',loc='left')
delta=(df.selected_rmse-df.persistence_rmse).sort_values();bx.axvline(0,color='#777777',lw=1)
bx.scatter(delta,np.arange(len(delta)),s=27,color=colors['selected']);bx.set_xlabel('Selected − persistence RMSE (mg/dL)');bx.set_yticks([])
bx.set_title('30 better; 1 tie; 0 worse',loc='left');bx.grid(axis='x',alpha=.18)
fig.suptitle('Forecast fallback performance, with selection frozen before test',x=.07,ha='left',fontsize=14);fig.tight_layout(rect=(0,0,1,.94))
save(fig,'F02_forecast_comparison','Lower compared RMSE and negative selected-minus-persistence differences indicate smaller internal-test error. The mechanistic model remains weaker than persistence in28/31 participants; selected fallback is better in30 and ties in1.')
fig,(ax,bx)=plt.subplots(1,2,figsize=(10,5.3))
for col,label,color in [('innovation_coverage95','Innovation','#A56726'),('forecast_coverage95','Selected forecast','#0F7780')]:
    ax.scatter(np.arange(len(df)),df[col]*100,label=label,color=color,s=26)
ax.axhline(95,color='#555555',ls='--',lw=1);ax.set(xlabel='Participant index (CSV order)',ylabel='Empirical coverage of ±1.96 scale (%)',ylim=(0,102));ax.legend();ax.set_title('Frozen fit-window scales',loc='left')
bx.scatter(df.tune_alarm_union_per_day,df.test_alarm_union_per_day,color='#514B79',s=30)
bx.axhline(1,color='#555555',ls='--',lw=1);bx.axvline(1,color='#999999',ls=':',lw=1)
bx.set(xlabel='Tune union alarm episodes / calendar day',ylabel='Test union alarm episodes / calendar day');bx.set_title('Tune budget does not guarantee test burden',loc='left')
fig.tight_layout();save(fig,'F03_coverage_and_alarm_transfer','Empirical ±1.96-scale residual coverage and union-of-channel alarm burden on previously exposed internal tests. Nominal95% and1episode/day reference lines are targets/benchmarks, not guarantees.')
diagnostics=[]
for pid,r in frozen.items():
    row={'participant':pid,'status':r['status'],'source':r['source'],'failure':r.get('error'),
         'exclusion_reasons':'; '.join(r['eligibility']['reasons'])}
    for name,w in r['eligibility']['split_provenance']['windows'].items():
        row[name+'_slots']=w['slots'];row[name+'_cgm_coverage']=w['cgm_coverage'];row[name+'_eligible_pairs']=w['eligible_forecast_pairs']
    if r['status']=='frozen':
        v=r['validation'];diag=v['fit_diagnostics']
        row.update(selected_policy=v['forecast_policy']['kind'],innovation_threshold=v['cusum_threshold'],
                   forecast_threshold=v['cusum6_threshold'],tune_innovation_channel_coverage=v['threshold_result']['coverage'],
                   tune_forecast_channel_coverage=v['threshold6_result']['coverage'],
                   threshold_feasible=v['threshold_result']['feasible'],threshold6_feasible=v['threshold6_result']['feasible'],
                   jacobian_condition=diag['jacobian_condition'],bound_proximity_1pct='; '.join(diag['bound_proximity_1pct']),
                   total_optimizer_nfev=sum(a['nfev'] for a in diag['attempts']),
                   optimizer_converged_starts=sum(a['success'] for a in diag['attempts']))
    diagnostics.append(row)
diagdf=pd.DataFrame(diagnostics);diagdf.to_csv(P/'ALL_PARTICIPANT_DIAGNOSTICS.csv',index=False)
fig,(ax,bx,cx)=plt.subplots(1,3,figsize=(11.5,4.4),gridspec_kw={'width_ratios':[1,1,1.2]})
labels=['Frozen + evaluated','Input failure','Eligibility exclusion']
counts=[sum(r['status']=='frozen' for r in frozen.values()),sum(r['status']=='failed' for r in frozen.values()),sum(r['status']=='excluded' for r in frozen.values())]
ax.barh(labels,counts,color=['#0F7780','#B06040','#8A949D']);ax.invert_yaxis();ax.set_xlabel('Supplied participants')
for j,v in enumerate(counts):ax.text(v+.3,j,str(v),va='center')
ax.set_xlim(0,35);ax.set_title('All 34 records accounted for',loc='left')
for j,col in enumerate(['innovation_threshold','forecast_threshold']):
    vals=diagdf[col].dropna().to_numpy();bx.scatter(np.full(len(vals),j)+np.linspace(-.12,.12,len(vals)),vals,s=20,color=['#A56726','#0F7780'][j])
bx.set_xticks([0,1],['Innovation','Forecast']);bx.set_ylabel('Frozen CUSUM threshold');bx.set_title('Both tune searches feasible in 31',loc='left')
vals=df.jacobian_condition.to_numpy();at_bound=df.bound_proximity_1pct.notna().to_numpy()
cx.scatter(np.arange(len(vals)),vals,c=np.where(at_bound,'#B06040','#0F7780'),s=27);cx.set_yscale('log')
cx.set_xlabel('Participant index (CSV order)');cx.set_ylabel('Local fit Jacobian condition number');cx.set_title('Orange: parameter near a bound',loc='left')
fig.tight_layout();save(fig,'F04_eligibility_fit_thresholds','All34 participant statuses and frozen-fit diagnostics. One input failure has negative supplied bolus entries; two records fail length/coverage rules.24/31 converged fits approach a parameter bound. Local Jacobian conditioning is not proof of physiological identifiability.')
extra={'test_union_above_one_per_day':int((df.test_alarm_union_per_day>1).sum()),
       'test_union_max_per_day':float(df.test_alarm_union_per_day.max()),
       'test_union_max_participant':str(df.loc[df.test_alarm_union_per_day.idxmax(),'participant']),
       'test_innovation_coverage_min':float(df.innovation_coverage95.min()),'test_innovation_coverage_max':float(df.innovation_coverage95.max()),
       'test_forecast_coverage_min':float(df.forecast_coverage95.min()),'test_forecast_coverage_max':float(df.forecast_coverage95.max()),
       'bound_proximity_any_count':int(df.bound_proximity_1pct.notna().sum()),
       'source_counts':df.source.value_counts().to_dict(),
       'participant_duration_note':'HUPA0027P contributes413? pairs: see exact exported CSV; aggregate estimates give participants equal weight.'}
extra['participant_duration_note']='HUPA0027P contributes '+str(int(df.loc[df.participant=='HUPA0027P','test_pairs'].iloc[0]))+' of '+str(int(df.test_pairs.sum()))+' test pairs; reported aggregates weight participants equally.'
(P/'ADDITIONAL_DIAGNOSTICS.json').write_text(json.dumps(extra,indent=2)+'\n')
(OUT/'FIGURE_LINEAGE.json').write_text(json.dumps({'runtime':sys.version,'matplotlib':matplotlib.__version__,
    'numpy':np.__version__,'source_sha256':h(__file__),'input_hashes':{n:h(P/n) for n in ['PARTICIPANT_RESULTS.csv','TEST_RESULTS.json','FROZEN_CALIBRATION.json']},
    'figure_source_data_sha256':h(OUT/'FIGURE_PARTICIPANT_DATA.csv'),'selection':'All31 evaluated participants, no performance filtering; fixed participant-id ordering in FIGURE_PARTICIPANT_DATA.csv','figures':outputs},indent=2)+'\n')
print(json.dumps(extra,indent=2))
