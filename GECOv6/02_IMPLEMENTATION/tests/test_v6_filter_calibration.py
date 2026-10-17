"""V6 known-answer, causal-boundary, and calibration countertests."""
import unittest
import numpy as np
from geco_v4.physiology import (TwinParams, GlucoseModel, PhysiologyTwin, ForecastPolicy,
    _joseph_update, evaluate_causal_forecasts, fit_participant_detailed)
from geco_v4.calibrate import search_threshold, freeze_threshold, select_forecast_policy, calibration_split
from geco_v4.datasets import ParticipantSeries

class FilterCalibrationV6(unittest.TestCase):
    def test_joseph_known_answer(self):
        x=np.array([120.,0.,3.2,0.,120.]);P=np.diag([5.,2.,3.,4.,100.])
        out,cov,error,std=_joseph_update(x,P,140.,25.)
        self.assertAlmostEqual(out[4],136.);self.assertAlmostEqual(cov[4,4],20.)
        np.testing.assert_allclose(np.diag(cov)[:4],[5.,2.,3.,4.])
        self.assertEqual(error,20.);self.assertAlmostEqual(std,np.sqrt(125.))

    def test_inflation_changes_only_normalization(self):
        a,b=PhysiologyTwin(),PhysiologyTwin();a.innovation_inflation=.2;b.innovation_inflation=25.
        for k in range(80):
            y=120.+20*np.sin(k/8)
            oa=a.update(y,.08,10. if k==10 else 0.);ob=b.update(y,.08,10. if k==10 else 0.)
            np.testing.assert_allclose(a.x,b.x,rtol=0,atol=0);np.testing.assert_allclose(a.P,b.P,rtol=0,atol=0)
            if oa.innovation_valid:self.assertAlmostEqual(oa.standardized_innovation*np.sqrt(.2),ob.standardized_innovation*np.sqrt(25.))

    def test_long_missing_gap_and_subunit_inflation_sc017(self):
        t=PhysiologyTwin();t.innovation_inflation=.5;t.update(120.,.08,0.)
        for _ in range(36):
            self.assertEqual(t.update(None,.08,0.).quality,'missing')
            self.assertGreaterEqual(np.linalg.eigvalsh(t.P).min(),-1e-8)
        out=t.update(120.,.08,0.)
        self.assertEqual(out.quality,'gap_reset');self.assertFalse(out.innovation_valid)
        self.assertIsNone(t.last_forecast_residual_z);self.assertGreaterEqual(np.linalg.eigvalsh(t.P).min(),0.)

    def test_material_covariance_failure_guard(self):
        t=PhysiologyTwin();t.update(120.,.08,0.);t.P[4,4]=-500.
        out=t.update(130.,.08,0.)
        self.assertEqual(out.quality,'numerical_reset');self.assertFalse(out.innovation_valid)
        self.assertEqual(t.numerical_resets,1);self.assertTrue(np.isfinite(t.P).all())

    def test_reset_flushes_due_residual_and_ar_history(self):
        t=PhysiologyTwin(forecast_policy={'kind':'persistence'})
        for k in range(10):t.update(120.+k,.08,0.)
        self.assertIsNotNone(t.last_forecast_residual_z);t.reset(140.)
        self.assertIsNone(t.last_forecast_residual_z);self.assertIsNone(t._last_z);self.assertEqual(t._forecast_buffer,[])

    def test_streaming_batch_and_due_match_all_policies(self):
        n=130;y=130.+20*np.sin(np.arange(n)/10.);y[:3]=np.nan;y[30]=np.nan;y[62:80]=np.nan
        u=np.full(n,.08);u[20]=2.;c=np.zeros(n);c[21]=30.
        for kind in ('mechanistic','persistence','trend'):
            policy=ForecastPolicy(kind=kind,hold_insulin_u=.08)
            r=evaluate_causal_forecasts(TwinParams(),y,u,c,forecast_policy=policy,ar1_rho=.7,inflation=.3)
            t=PhysiologyTwin(forecast_policy=policy).configure_calibration({'ar1_rho':.7,'innovation_inflation':.3,'sigma6_mgdl':12.})
            pred=[];zs=[]
            for k in range(n):
                out=t.update(y[k],u[k-1] if k else 0.,c[k-1] if k else 0.)
                pred.append(t.forecast(6) if np.isfinite(y[k]) else np.nan)
                zs.append(out.standardized_innovation if out.innovation_valid and k>=36 else np.nan)
                if k>=6 and np.isfinite(y[k]) and np.isfinite(pred[k-6]) and out.quality not in ('gap_reset','initializing'):
                    self.assertAlmostEqual(t.last_forecast_residual_z,(y[k]-pred[k-6])/12.,places=9)
            j=('mechanistic','persistence','trend').index(kind)
            np.testing.assert_allclose(pred,r['predictions'][:,j],rtol=1e-11,atol=1e-9,equal_nan=True)
            np.testing.assert_allclose(zs,r['z'],rtol=1e-10,atol=1e-9,equal_nan=True)

    def test_future_suffix_does_not_change_prefix(self):
        n=120;y=120.+np.arange(n)*.1;u=np.full(n,.08);c=np.zeros(n)
        r=evaluate_causal_forecasts(TwinParams(),y,u,c);y[70:]=300.;u[70:]=4.;c[70:]=100.
        changed=evaluate_causal_forecasts(TwinParams(),y,u,c)
        np.testing.assert_allclose(r['predictions'][:70],changed['predictions'][:70],rtol=0,atol=0)

    def test_current_event_not_retroactively_assimilated(self):
        n=100;y=np.full(n,120.);u=np.full(n,.08);c=np.zeros(n)
        r=evaluate_causal_forecasts(TwinParams(),y,u,c);u[60]=6.;c[60]=100.
        changed=evaluate_causal_forecasts(TwinParams(),y,u,c)
        np.testing.assert_allclose(r['predictions'][:61],changed['predictions'][:61],rtol=0,atol=0)

    def test_shared_masks_and_trend_known_answer(self):
        y=np.arange(100,dtype=float)+100.;y[50]=np.nan
        r=evaluate_causal_forecasts(TwinParams(),y,np.zeros(100),np.zeros(100))
        self.assertEqual(len(set(v['n_pairs'] for v in r['metrics'].values())),1)
        self.assertAlmostEqual(r['predictions'][45,1],145.);self.assertAlmostEqual(r['predictions'][45,2],148.)
        self.assertAlmostEqual(r['predictions'][51,2],151.)

    def test_empty_bad_arrays_and_fit_rejected(self):
        for a in (([],[],[]),([120.],[.1,.2],[0.]),([120.],[np.nan],[0.]),([120.],[-1.],[0.])):
            with self.assertRaises(ValueError):evaluate_causal_forecasts(TwinParams(),*a)
        with self.assertRaises(ValueError):fit_participant_detailed(np.full(100,np.nan),np.zeros(100),np.zeros(100))

    def test_threshold_failure_and_coverage_honest(self):
        r=search_threshold(np.full(288,6.),.5,0.,np.array([4.,5.]))
        self.assertFalse(r['feasible']);self.assertIsNone(r['threshold'])
        with self.assertRaises(ValueError):freeze_threshold(np.full(288,6.),.5,0.,np.array([4.,5.]))
        r=search_threshold(np.full(288,np.nan),.5,1.)
        self.assertFalse(r['feasible']);self.assertEqual(r['reason'],'insufficient_observed_channel_coverage')
        r=search_threshold(np.zeros(288),.5,.5)
        self.assertTrue(r['feasible']);self.assertEqual(r['threshold'],4.);self.assertEqual(r['achieved']['calendar_days'],1.)

    def test_selection_tie_is_persistence(self):
        m={k:{'rmse':20.} for k in ('mechanistic','persistence','trend')}
        self.assertEqual(select_forecast_policy(m),'persistence');m['trend']['rmse']=19.
        self.assertEqual(select_forecast_policy(m),'trend')

    def test_analytic_jacobian_centered_difference(self):
        model=GlucoseModel();x=np.array([150.,.005,4.,30.,145.]);_,F=model.step_with_jacobian(x,.09,2.)
        for j in range(5):
            h=1e-6 if j==1 else 1e-4;a=x.copy();b=x.copy();a[j]+=h;b[j]-=h
            numeric=(model.step(a,.09,2.)-model.step(b,.09,2.))/(2*h)
            np.testing.assert_allclose(F[:,j],numeric,rtol=1e-6,atol=1e-7)

    def test_short_split_no_empty_windows(self):
        n=600;a=np.ones(n);s=ParticipantSeries('test','test',np.arange(n),120*a,.08*a,0*a,0*a,0*a,0*a)
        self.assertEqual([len(x.cgm) for x in calibration_split(s)],[300,150,150])

if __name__=='__main__':unittest.main()
