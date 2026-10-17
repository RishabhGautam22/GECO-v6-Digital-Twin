"""Read-only actual filter-quality accounting, independent of simulation helpers."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
import gzip,json,hashlib,sys,datetime
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'03_EXPERIMENTS/comparative_study';O=ROOT/'08_REVIEW_AND_QA/filter/study_cross_review'
def inspect(row):
    with gzip.open(ROOT/row['trace_path'],'rt') as f:c=json.load(f)['columns']
    counts=Counter(c['sensor_quality'])
    return {'run_id':row['run_id'],'mode':row['mode'],'family':row['family'],'arm':row['arm'],'counts':dict(counts)}
def main():
    rows=json.loads((P/'RUN_RESULTS.json').read_text())
    with ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(inspect,rows,chunksize=24))
    totals=Counter();groups={}
    for r in results:
        totals.update(r['counts']);key=r['mode']+'/'+r['family']+'/'+r['arm']
        groups.setdefault(key,Counter()).update(r['counts'])
    report={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runtime':sys.version,'runs':len(rows),
            'all_quality_counts':dict(totals),'grouped_quality_counts':{k:dict(v) for k,v in groups.items()},
            'runs_with_numerical_reset':[r['run_id'] for r in results if r['counts'].get('numerical_reset',0)],
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'run_results_sha256':hashlib.sha256((P/'RUN_RESULTS.json').read_bytes()).hexdigest(),
            'interpretation':'Only runs constructing a production twin have filter-derived quality; other arms retain raw observation quality. Counts do not certify latent covariance values that are not stored in traces.'}
    (O/'ACTUAL_FILTER_QUALITY_COUNTS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(totals)))
if __name__=='__main__':main()
