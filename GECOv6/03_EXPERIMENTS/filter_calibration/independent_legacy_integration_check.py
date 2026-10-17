"""Independent late integration checks; no campaign rerun or source mutation."""
from pathlib import Path
import sys, json, hashlib, datetime
from unittest.mock import patch
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '02_IMPLEMENTATION'))
from geco_v4.bench import BenchConfig, run_scenario
from geco_v4.physiology import PhysiologyTwin, TwinParams, GlucoseModel
from geco_v4.delivery import DeliveryCalibration
from geco_v4.detectors import TwoSidedCUSUM
from geco_v4.campaign import _cfg_from_validation
from geco_v4.calibrate import TwinValidation

checks = []
update = PhysiologyTwin.update
plant_step = GlucoseModel.step
detector_update = TwoSidedCUSUM.update

def observe(cfg, replay=None, steps=None):
    events, plants, channels = [], [], {}
    def observed_update(self, y, u, c):
        out = update(self, y, u, c)
        events.append((y, u, c, out.state.copy()))
        return out
    def observed_plant(self, x, u, c):
        plants.append((u, c))
        return plant_step(self, x, u, c)
    def observed_detector(self, z):
        channels.setdefault(self.threshold, []).append(z)
        return detector_update(self, z)
    with patch.object(PhysiologyTwin, 'update', observed_update), patch.object(GlucoseModel, 'step', observed_plant), patch.object(TwoSidedCUSUM, 'update', observed_detector):
        result = run_scenario(cfg, None, TwinParams(), DeliveryCalibration(), replay=replay, steps=steps)
    return events, plants, channels, result

n = 60
u = .05 + np.arange(n) * .001
c = np.zeros(n); c[[4, 18, 41]] = [7., 19., 31.]
y = 130. + np.sin(np.arange(n) * .15) * 4.
replay = {'cgm': y, 'insulin': u, 'bolus': np.zeros(n), 'carbs': c}
cfg = BenchConfig(ablation='no_geco', cusum_threshold=101., cusum6_threshold=102., innovation_cusum_start_step=36, forecast_cusum_start_step=42)
a, _, ch, _ = observe(cfg, replay)
np.testing.assert_array_equal([r[1] for r in a], np.r_[0., u[:-1]])
np.testing.assert_array_equal([r[2] for r in a], np.r_[0., c[:-1]])
checks.append('All 60 replay inputs use preceding interval, with zero initial input.')

# Current/future event perturbation cannot change the state at that origin.
altered = {k: v.copy() for k, v in replay.items()}
altered['insulin'][18:] += .17; altered['carbs'][18:] += 9.
b, _, _, _ = observe(cfg, altered)
np.testing.assert_array_equal(np.stack([r[3] for r in a[:19]]), np.stack([r[3] for r in b[:19]]))
assert not np.allclose(a[19][3], b[19][3])
checks.append('Replay suffix intervention at index18 leaves states0..18 identical; first effect occurs at19.')
assert len(ch[101.]) == n and len(ch[102.]) == n
assert all(z is None for z in ch[101.][:36]) and np.isfinite(ch[101.][36])
assert all(z is None for z in ch[102.][:42]) and np.isfinite(ch[102.][42])
checks.append('Real filter startup streams are masked through35/41 and become eligible at36/42.')

# The plant call exposes the actual generated meal event. With full announcement,
# the twin must receive that event one interval later, alongside authorization.
e, p, _, result = observe(BenchConfig(mode='closed_loop', ablation='no_geco', meal_announcement_rate=1., seed=4), steps=110)
assert any(meal > 0 for _, meal in p)
np.testing.assert_allclose([v[1] for v in e], np.r_[0., [r.allowed_u for r in result.records[:-1]]], rtol=0, atol=0)
np.testing.assert_allclose([v[2] for v in e], np.r_[0., [v[1] for v in p[:-1]]], rtol=0, atol=0)
checks.append('Closed-loop prior authorization and the previously announced generated meal match exact inputs.')
e, p, _, _ = observe(BenchConfig(mode='closed_loop', ablation='no_geco', meal_announcement_rate=0., seed=4), steps=110)
assert any(meal > 0 for _, meal in p) and all(v[2] == 0 for v in e)
checks.append('Unannounced generated meals never enter twin updates.')

# Read a truly frozen fresh record rather than manufacturing the validation object.
frozen = json.loads((ROOT / '03_EXPERIMENTS/filter_calibration/FROZEN_CALIBRATION.json').read_text())
def find_validation(obj):
    if isinstance(obj, dict):
        if all(k in obj for k in ('participant', 'rmse30_cal', 'threshold_result')): return obj
        for value in obj.values():
            found = find_validation(value)
            if found is not None: return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_validation(value)
            if found is not None: return found
    return None
v = TwinValidation(**find_validation(frozen))
calcfg = _cfg_from_validation(v, 'protected')
assert (calcfg.innovation_cusum_start_step, calcfg.forecast_cusum_start_step) == (36, 42)
assert (BenchConfig().innovation_cusum_start_step, BenchConfig().forecast_cusum_start_step) == (0, 0)
checks.append('Fresh frozen participant runtime selects36/42; explicitly uncalibrated default remains0/0.')

snapshots = []
for name in ('comparative_study', 'supplement_fasting'):
    receipt_path = ROOT / '03_EXPERIMENTS' / name / 'FROZEN_SOURCE_RECEIPT.json'
    receipt = json.loads(receipt_path.read_text())
    mismatches = []
    for row in receipt['files']:
        actual = hashlib.sha256((ROOT / row['frozen_copy_relative_path']).read_bytes()).hexdigest()
        if actual != row['sha256']: mismatches.append(row['original_relative_path'])
    assert not mismatches
    snapshots.append({'campaign': name, 'files_checked': len(receipt['files']), 'mismatches': mismatches, 'receipt_sha256': hashlib.sha256(receipt_path.read_bytes()).hexdigest()})
checks.append('All25 primary and30 supplementary preserved source files match their recorded SHA256.')

out = {'status': 'passed', 'checks': checks, 'source_snapshots': snapshots,
       'runtime': sys.version, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'scope': 'Offline benign integration countertests only; completed campaigns are not rerun or altered.',
       'source_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__), ROOT/'02_IMPLEMENTATION/geco_v4/bench.py', ROOT/'02_IMPLEMENTATION/geco_v4/campaign.py', ROOT/'02_IMPLEMENTATION/geco_v4/physiology.py']}}
dest = ROOT/'08_REVIEW_AND_QA/filter/LEGACY_INTEGRATION_RECHECK.json'
dest.write_text(json.dumps(out, indent=2)+'\n')
print(json.dumps(out, indent=2))
