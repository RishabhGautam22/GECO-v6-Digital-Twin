"""Separate software-lane check of science-lane repair and benign CLI integration."""
from dataclasses import asdict,fields,MISSING
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from geco_v4.physiology import PhysiologyTwin,TwinParams,ForecastPolicy,evaluate_causal_forecasts
from geco_v4.calibrate import TwinValidation,search_threshold
from geco_v4.bench import BenchConfig,GatewayRuntime,run_scenario
from geco_v4.campaign import _cfg_from_validation,load_frozen
from geco_v4.datasets import ParticipantSeries
from geco_v4.delivery import DeliveryCalibration

def validation(**changes):
    args={f.name:0. for f in fields(TwinValidation) if f.default is MISSING and f.default_factory is MISSING}
    args.update(participant="synthetic_fixture",params=asdict(TwinParams()),cusum_drift=.5,cusum_threshold=9.,cusum6_threshold=11.,ar1_rho=.4,sigma6_mgdl=17.,innovation_inflation=.5,forecast_policy=asdict(ForecastPolicy(kind="trend",hold_insulin_u=.08)),r_std=7.,threshold_result={"feasible":True,"threshold":9.},threshold6_result={"feasible":True,"threshold":11.})
    args.update(changes);return TwinValidation(**args)

class IndependentFilterReview(unittest.TestCase):
    def test_normalization_does_not_change_state_or_covariance(self):
        twins=[PhysiologyTwin(forecast_policy=ForecastPolicy(kind="trend",hold_insulin_u=.08)) for _ in range(2)]
        twins[0].innovation_inflation=.25;twins[1].innovation_inflation=4.
        for k in range(80):
            y=None if 25<=k<61 else 130+7*np.sin(k/7)
            outs=[t.update(y,.08,10 if k==5 else 0) for t in twins]
            np.testing.assert_allclose(twins[0].x,twins[1].x,atol=1e-12,rtol=0)
            np.testing.assert_allclose(twins[0].P,twins[1].P,atol=1e-12,rtol=0)
            self.assertGreaterEqual(np.linalg.eigvalsh(twins[0].P).min(),-1e-9)
            if outs[0].innovation_valid:
                self.assertAlmostEqual(outs[0].standardized_innovation,4*outs[1].standardized_innovation,places=10)
    def test_invalid_covariance_reset_flushes_evidence(self):
        t=PhysiologyTwin();t.update(130.,.08,0);t.update(131.,.08,0)
        t.P[0,0]=-10.;k=t._k
        o=t.update(129.,.08,0)
        self.assertFalse(o.innovation_valid);self.assertEqual(t._k,k+1)
        self.assertIsNone(t.last_forecast_residual_z)
        self.assertIsNone(t._last_z)
        self.assertTrue(all(at>t._k for at,_ in t._forecast_buffer))
    def test_all_policy_streaming_batch_and_gap_equivalence(self):
        p=TwinParams(egp=.9,p1=.007,p3=4e-5)
        n=120;y=140+15*np.sin(np.arange(n)/8);y[25:43]=np.nan;y[85]=np.nan
        u=np.full(n,.08);u[10]=.2;c=np.zeros(n);c[60]=25
        for kind in ("mechanistic","persistence","trend"):
            policy=ForecastPolicy(kind=kind,hold_insulin_u=.08)
            batch=evaluate_causal_forecasts(p,y,u,c,forecast_policy=policy,ar1_rho=.3,inflation=.4,warmup=0)
            t=PhysiologyTwin(p,forecast_policy=policy);t.configure_calibration({"ar1_rho":.3,"innovation_inflation":.4,"sigma6_mgdl":20})
            j=("mechanistic","persistence","trend").index(kind)
            for k in range(n):
                o=t.update(float(y[k]) if np.isfinite(y[k]) else None,float(u[k-1]) if k else 0,float(c[k-1]) if k else 0)
                if np.isfinite(y[k]):self.assertAlmostEqual(t.forecast(6),batch["predictions"][k,j],places=8)
                if o.innovation_valid:self.assertAlmostEqual(o.standardized_innovation,batch["z"][k],places=8)
                self.assertGreaterEqual(np.linalg.eigvalsh(t.P).min(),-1e-8)
    def test_future_suffix_cannot_change_past_forecasts(self):
        n=120;y=120+5*np.sin(np.arange(n)/10);u=np.full(n,.08);c=np.zeros(n)
        a=evaluate_causal_forecasts(TwinParams(),y,u,c,warmup=0)
        y2=y.copy();u2=u.copy();c2=c.copy();y2[70:]+=40;u2[70:]=.2;c2[70:]=3
        b=evaluate_causal_forecasts(TwinParams(),y2,u2,c2,warmup=0)
        np.testing.assert_array_equal(a["predictions"][:70],b["predictions"][:70])
    def test_infeasible_threshold_is_explicit(self):
        result=search_threshold(np.full(288,6.),.5,0.,candidates=np.array([4.,5.]))
        self.assertFalse(result["feasible"]);self.assertIsNone(result["threshold"])
        self.assertEqual(result["reason"],"no_candidate_meets_budget")
    def test_selected_forecast_equals_series_endpoint(self):
        t=PhysiologyTwin(forecast_policy=ForecastPolicy(kind="trend",hold_insulin_u=.08))
        for y in (120.,122.,124.,126.):t.update(y,.08,0.)
        self.assertEqual(t.forecast(6),t.forecast_series(6)[-1])
        self.assertNotEqual(t.forecast(6),t.forecast(6,0.))

class BenignRuntimeIntegration(unittest.TestCase):
    def test_participant_calibration_warmup_gates_both_streams(self):
        cfg=_cfg_from_validation(validation(),"protected")
        self.assertEqual((cfg.innovation_cusum_start_step,cfg.forecast_cusum_start_step),(36,42))
        runtime=GatewayRuntime(cfg,{},TwinParams(),DeliveryCalibration())
        runtime.twin.last_forecast_residual_z=4.
        out=SimpleNamespace(standardized_innovation=4.,innovation_valid=True,quality="ok")
        with patch.object(runtime.twin,"update",return_value=out),patch.object(runtime.twin,"forecast",return_value=120.),patch.object(runtime.cusum,"update",wraps=runtime.cusum.update) as one,patch.object(runtime.cusum6,"update",wraps=runtime.cusum6.update) as six:
            for k in range(44):
                runtime.last_cgm=120.;runtime.last_cgm_ts=k*300.
                runtime.decide(k*300.,k,.08,0.,.08,0.)
            self.assertEqual([c.args[0] for c in one.call_args_list],[None]*36+[4.]*8)
            self.assertEqual([c.args[0] for c in six.call_args_list],[None]*42+[4.]*2)
    def test_benign_replay_inputs_are_prior_slot_requests_are_current(self):
        replay={"cgm":np.array([120.,121.,122.,123.]),"insulin":np.array([.05,.1,.15,.2]),"bolus":np.zeros(4),"carbs":np.array([3.,7.,11.,13.])}
        seen=[];original=GatewayRuntime.decide
        def capture(runtime,*args):
            seen.append(args);return original(runtime,*args)
        with patch.object(GatewayRuntime,"decide",capture):
            run_scenario(BenchConfig(),None,TwinParams(),DeliveryCalibration(),replay=replay)
        self.assertEqual([a[4] for a in seen],[0.,.05,.1,.15])
        self.assertEqual([a[5] for a in seen],[0.,3.,7.,11.])
        self.assertEqual([a[2] for a in seen],[.05,.1,.15,.2])
    def test_startup_steps_must_be_nonnegative_integer(self):
        for name in ("innovation_cusum_start_step","forecast_cusum_start_step"):
            for value in (-1,1.5,True):
                with self.assertRaises(ValueError):BenchConfig(**{name:value})
    def test_benign_closed_loop_uses_prior_visible_announcements_and_authority(self):
        from geco_v4.physiology import GlucoseModel
        plant=GlucoseModel(TwinParams());advance=plant.step;decide=GatewayRuntime.decide
        actual_carbs=[];seen=[]
        def step(x,u,c):
            actual_carbs.append(c);return advance(x,u,c)
        def capture(runtime,*args):
            seen.append(args);return decide(runtime,*args)
        with patch("geco_v4.bench.GlucoseModel",return_value=plant),patch.object(plant,"step",side_effect=step),patch.object(GatewayRuntime,"decide",capture):
            result=run_scenario(BenchConfig(mode="closed_loop",meal_announcement_rate=1.),None,TwinParams(),DeliveryCalibration(),steps=110)
        self.assertTrue(any(actual_carbs))
        self.assertEqual([a[5] for a in seen],[0.]+actual_carbs[:-1])
        self.assertEqual([a[4] for a in seen],[0.]+[r.allowed_u for r in result.records[:-1]])
    def test_study_executes_corrected_production_filter(self):
        from geco_v6_study.engine import run
        from test_v6_study import UNIT,SPEC,CLEAN
        cfg={"params":asdict(TwinParams()),"forecast_policy":asdict(ForecastPolicy(kind="persistence",hold_insulin_u=.08)),"innovation_inflation":.5,"ar1_rho":.2,"sigma6_mgdl":20.,"thresholds":{"full":1e9},"mass_sigma_g":.005}
        with patch("geco_v6_study.engine.PhysiologyTwin",wraps=PhysiologyTwin) as constructor:
            trace=run(UNIT,1103,"clean","full_manual",cfg,SPEC,clean=CLEAN)
        self.assertEqual(constructor.call_count,1)
        self.assertGreater(sum(z is not None for z in trace["columns"]["innovation_z"]),40)
        self.assertGreater(sum(z is not None for z in trace["columns"]["due_forecast_z"]),40)
    def test_validation_reaches_runtime_and_selected_forecast(self):
        cfg=_cfg_from_validation(validation(),"protected")
        runtime=GatewayRuntime(cfg,{},TwinParams(),DeliveryCalibration())
        self.assertEqual(runtime.twin.forecast_policy.kind,"trend")
        self.assertEqual(runtime.twin.innovation_inflation,.5)
        self.assertEqual(runtime.twin.r_var,49.)
        runtime.last_cgm=120.;runtime.last_cgm_ts=0.
        with patch.object(runtime.twin,"forecast",wraps=runtime.twin.forecast) as spy:
            runtime.decide(0.,0,.2,0.,0.,0.)
            self.assertTrue(spy.call_args_list)
            for call in spy.call_args_list:self.assertEqual(call.args,(6,))
        self.assertFalse(runtime.cusum.last_alarm)
    def test_runtime_rejects_infeasible_or_inconsistent_threshold(self):
        for result in ({"feasible":False,"threshold":None},{"feasible":True,"threshold":10.}):
            with self.assertRaises(ValueError):_cfg_from_validation(validation(threshold_result=result),"protected")
    def test_loader_preserves_v6_exact_split_and_skips_failed_records(self):
        n=1001;values=np.arange(n,dtype=float)
        s=ParticipantSeries("synthetic_fixture","unit test",values,120+values/100,np.full(n,.08),np.zeros(n),np.zeros(n),np.zeros(n),np.zeros(n))
        v=validation(split_provenance={"rule":"floor(0.50N),floor(0.75N)"})
        with tempfile.TemporaryDirectory() as d:
            blob={"synthetic_fixture":{"status":"frozen","params":v.params,"validation":{k:x for k,x in asdict(v).items() if k!="params"}},"failed":{"status":"failed"}}
            Path(d,"twin_params_frozen.json").write_text(json.dumps(blob))
            loaded=load_frozen([s],d)
            self.assertEqual(len(loaded["synthetic_fixture"][2].cgm),251)
            self.assertEqual(loaded["synthetic_fixture"][2].timestamps[0],750.)

if __name__=="__main__":unittest.main()
