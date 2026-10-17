"""Ordinary numerical, measurement and paired-estimator regression checks."""
import copy
from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from geco_v6_study.plants import HovorkaPlant,HovorkaParams,MMOL_TO_MGDL,GRAMS_GLUCOSE_PER_MMOL
from geco_v6_study.engine import run,metrics,Detector,exogenous

UNIT={"unit_id":"geco_original_08","family":"geco_original","body_weight_kg":75.,"factors":{k:1. for k in ("sensitivity","absorption","clearance","glucose_flux","glucose_effectiveness","gut_gain")}}
SPEC={"steps":60,"dt_min":5.,"fault_start_step":10,"fault_end_step_exclusive":20,"warmup_steps":0}
CONFIG={"thresholds":{"simple":1e9},"mass_sigma_g":.005}
CLEAN={"requested_u":[.08]*60}

class HovorkaNumerics(unittest.TestCase):
    def test_equilibrium_and_rate_units(self):
        p=HovorkaPlant();d=p.derivative(p.x,p.basal_u/5,0)
        self.assertLess(np.max(np.abs(d)),1e-10)
        initial=p.x.copy()
        for _ in range(100):p.step(p.basal_u,0)
        np.testing.assert_allclose(p.x,initial,atol=1e-8,rtol=0)
        d0=p.derivative(initial,0,0);d1=p.derivative(initial,1,0)
        self.assertAlmostEqual(d1[2]-d0[2],1000.)
    def test_gut_chain_matches_impulse_solution(self):
        p=HovorkaPlant();dose=20*p.p.ag/GRAMS_GLUCOSE_PER_MMOL
        p.x[8]=dose
        for _ in range(24):p.step(p.basal_u,0)
        expected=dose*(120/p.p.tmax_g_min)*np.exp(-120/p.p.tmax_g_min)
        self.assertAlmostEqual(p.x[9],expected,places=5)
    def test_rk4_step_refinement(self):
        a=HovorkaPlant();b=HovorkaPlant(replace(a.p,integration_step_min=.5))
        values=[]
        for k in range(60):
            u=a.basal_u+(.01 if k==5 else 0)
            values.append(abs(a.step(u,3 if k==0 else 0)[0]-b.step(u,3 if k==0 else 0)[0]))
        self.assertLess(max(values),.001)
    def test_direction_and_conversion(self):
        a=HovorkaPlant();b=HovorkaPlant()
        for k in range(24):
            a.step(a.basal_u,0);b.step(b.basal_u+(.01 if k==0 else 0),0)
        self.assertLess(b.glucose,a.glucose)
        self.assertAlmostEqual(MMOL_TO_MGDL/GRAMS_GLUCOSE_PER_MMOL,100.)
    def test_input_validation(self):
        p=HovorkaPlant()
        for u,c in ((float("nan"),0),(-.1,0),(0,float("inf"))):
            with self.assertRaises(ValueError):p.step(u,c)
        with self.assertRaises(ValueError):HovorkaParams(weight_kg=0)
    def test_negative_production_is_flagged_without_clamping_equation(self):
        p=HovorkaPlant();p.x[7]=1.2
        self.assertTrue(p.diagnostics["negative_egp_evaluator_only"])
        self.assertLess(p.diagnostics["endogenous_production_mmol_min"],0)
        self.assertFalse(p.valid)

class MeasurementAndAuthority(unittest.TestCase):
    def test_missing_physiology_cannot_corroborate_current_mass(self):
        d=Detector("full",100,.005)
        d.phys.pos=100
        signal=d.observe(.005,None,None)
        self.assertEqual(signal["full_score"],signal["mass_cusum"])
    def simulate(self,condition="clean",arm="simple_manual",**kwargs):
        return run(UNIT,1103,condition,arm,CONFIG,SPEC,clean=CLEAN,**kwargs)
    def test_true_mass_drives_plant_despite_report_mask(self):
        trace=self.simulate("excess_bias_report_mask")["columns"]
        np.testing.assert_array_equal(trace["actual_emitted_u"],trace["virtual_plant_input_u"])
        self.assertTrue(any(abs(a-b)>1e-6 for a,b in zip(trace["local_measured_delta_g"],trace["network_reported_delta_g"])))
        np.testing.assert_array_equal(trace["requested_u"],CLEAN["requested_u"])
    def test_local_cutoff_retained_with_report_mask(self):
        a=self.simulate("excess_bias_25")["columns"]
        b=self.simulate("excess_bias_report_mask")["columns"]
        np.testing.assert_array_equal(a["actual_emitted_u"],b["actual_emitted_u"])
        np.testing.assert_array_equal(a["cutoff"],b["cutoff"])
    def test_stop_delay_and_residual_tail_are_visible(self):
        base=self.simulate("stuck_on")["columns"]
        late=self.simulate("stuck_on",stop_model="one_additional_sample_of_power")["columns"]
        tail=self.simulate("stuck_on",stop_model="residual_tail_0.02U_per_step_for3steps")["columns"]
        first=base["trip_event"].index(True)
        self.assertEqual(base["actual_emitted_u"][first+1],0)
        self.assertGreater(late["actual_emitted_u"][first+1],0)
        self.assertAlmostEqual(tail["actual_emitted_u"][first+1],.02)
    def test_recovery_only_at_shared_operator_slots(self):
        c=self.simulate("stuck_on","simple_supervised")["columns"]
        for k,reset in enumerate(c["reset_event"]):
            if reset:
                self.assertTrue(c["operator_authorized"][k]);self.assertEqual(k%24,0)
                self.assertLessEqual(abs(sum(c["local_measured_delta_g"][k-6:k])),.01)
    def test_cooldown_counts_from_trip_interval_end(self):
        def force_trip_at_18(detector,*args):
            k=getattr(detector,"test_counter",-1)+1;detector.test_counter=k
            return {"simple_score":0.,"full_score":0.,"mass_cusum":0.,"physiology_cusum":0.,"score":0.,"alarm":k==18}
        with patch.object(Detector,"observe",force_trip_at_18):
            c=run(UNIT,1103,"clean","simple_manual",CONFIG,SPEC,clean={"requested_u":[0.]*60})["columns"]
        self.assertTrue(c["trip_event"][18])
        self.assertEqual(c["last_trip_end_t_min"][18],95.)
        self.assertFalse(c["reset_event"][24])  #120-95=25min, too soon
        self.assertTrue(c["reset_event"][48])   #next fixed operator slot
    def test_zero_command_noise_does_not_emit_mass(self):
        zero={"requested_u":[0.]*60}
        noise=exogenous(UNIT,1103,60)
        noise["balance_noise"][:]=np.where(np.arange(60)[:,None]%2,.008,-.008)
        with patch("geco_v6_study.engine.exogenous",return_value=noise):
            c=run(UNIT,1103,"clean","simple_manual",CONFIG,SPEC,clean=zero)["columns"]
        self.assertEqual(sum(c["actual_emitted_u"]),0)
        self.assertEqual(sum(c["virtual_plant_input_u"]),0)
        self.assertTrue(any(v!=0 for v in c["local_measured_delta_g"]))
    def test_identical_reference_has_zero_paired_delivery_effect(self):
        a=self.simulate();m=metrics(a,a,SPEC)
        self.assertEqual(m["stepwise_excess_vs_clean_u"],0)
        self.assertEqual(m["stepwise_deficit_vs_clean_u"],0)
        self.assertEqual(m["glucose_rmse_vs_clean"],0)
    def test_interval_end_trip_and_latch_exposure_timing(self):
        t=self.simulate()
        t["metadata"]["first_trip_step"]=SPEC["fault_start_step"]
        t["columns"]["state_before_emission"]=["RUN"]*60
        t["columns"]["state_before_emission"][11:14]=["LATCHED"]*3
        t["columns"]["cutoff"]=[False]*60
        t["columns"]["cutoff"][10:13]=[True]*3
        m=metrics(t,t,SPEC)
        self.assertEqual(m["first_trip_latency_min"],5.)
        self.assertEqual(m["total_commanded_latch_exposure_min"],15.)
        self.assertEqual(m["recovery_window_onset_latency_min"],0.)
        self.assertEqual(m["recovery_window_confirmed_latency_min"],30.)
    def test_fault_end_not_used_by_recovery_on_identical_observations(self):
        a=self.simulate()["columns"]
        altered={**SPEC,"fault_end_step_exclusive":40}
        b=run(UNIT,1103,"clean","simple_manual",CONFIG,altered,clean=CLEAN)["columns"]
        for key in ("recovery_state","reset_event","authorized_u","actual_emitted_u"):
            self.assertEqual(a[key],b[key])
    def test_missing_sensor_uses_common_quality_latch(self):
        c=self.simulate("cgm_missing")["columns"]
        self.assertIn("sensor_quality",c["trip_reason"])

if __name__=="__main__":unittest.main()
