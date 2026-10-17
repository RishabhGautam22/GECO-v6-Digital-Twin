"""Ordinary numerical, missing-data and causal-model regressions. Offline only."""
import dataclasses
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
from geco_v4.bench import BenchConfig, GatewayRuntime, run_scenario
from geco_v4.datasets import _event_amount, load_d1namo
from geco_v4.delivery import DeliveryCalibration
from geco_v4.detectors import TwoSidedCUSUM
from geco_v4.fusion import Assessment, Severity
from geco_v4.hal import VirtualBalanceTruthNode
from geco_v4.kernel import KernelContext, SafetyKernel
from geco_v4.numerics import payload_numeric_issue
from geco_v4.physiology import GlucoseModel, PhysiologyTwin, TwinParams
from geco_v4.wire import Envelope


class NumericalValidity(unittest.TestCase):
    def context(self, **changes):
        values=dict(now_s=0.,glucose_mgdl=150.,glucose_slope_mgdl_min=0.,cgm_age_s=0.,pump_age_s=0.,
                    command_authenticated=True,predicted_glucose_30m=140.,delivered_u_3h=0.,reactive_u_3h=0.,
                    assessment=Assessment(0.,Severity.NORMAL,1.,False,{},()),actuation_score=0.)
        values.update(changes)
        return KernelContext(**values)

    def test_nonfinite_context_requests_review_and_zero_output(self):
        for field in ('now_s','glucose_mgdl','glucose_slope_mgdl_min','cgm_age_s','pump_age_s',
                      'predicted_glucose_30m','delivered_u_3h','reactive_u_3h','actuation_score'):
            for bad in (float('nan'),float('inf'),float('-inf')):
                with self.subTest(field=field,bad=bad):
                    decision=SafetyKernel().authorize(.1,self.context(**{field:bad}))
                    self.assertEqual(decision.allowed_u,0.)
                    self.assertEqual(decision.severity,Severity.SAFE_MODE)
                    self.assertTrue(decision.requires_human_review)

    def test_invalid_command_is_total_function(self):
        for bad in (float('nan'),float('inf'),-.1,'missing',True):
            with self.subTest(bad=bad):
                self.assertEqual(SafetyKernel().authorize(bad,self.context()).allowed_u,0.)

    def test_invalid_parameters_rejected_without_new_thresholds(self):
        constructors=[lambda:BenchConfig(dt_min=0),lambda:BenchConfig(grams_per_unit=float('nan')),
                      lambda:BenchConfig(ar1_rho=1),lambda:SafetyKernel(predictive_budget_u_3h=float('inf')),
                      lambda:TwinParams(sub_steps=0),lambda:TwinParams(tau_i=float('nan')),
                      lambda:DeliveryCalibration(gain=0)]
        for constructor in constructors:
            with self.assertRaises(ValueError):constructor()

    def test_missing_first_sensor_sample_keeps_finite_state(self):
        twin=PhysiologyTwin();out=twin.update(float('nan'),.08,0.)
        self.assertEqual(out.quality,'missing');self.assertTrue(np.isfinite(out.state).all())

    def test_nonfinite_plant_inputs_raise(self):
        model=GlucoseModel();x=model.initial_state(120.)
        for insulin,carbs in [(float('nan'),0.),(.08,float('inf'))]:
            with self.assertRaises(ValueError):model.step(x,insulin,carbs)

    def test_json_and_payload_numeric_validation(self):
        self.assertIsNotNone(payload_numeric_issue('ACK',{'executed_units':float('nan')}))
        self.assertIsNotNone(payload_numeric_issue('ACK',{'executed_units':'missing'}))
        self.assertIsNone(payload_numeric_issue('ACK',{'executed_units':.3}))
        for token in ('NaN','Infinity','1e999'):
            raw=('{"src":"a","dst":"b","type":"TRUTH","seq":1,"ts":0,"payload":{"delta_g":'+token+'}}').encode()
            with self.assertRaises(ValueError):Envelope.from_wire(raw)

    def test_missing_sample_does_not_repeat_alarm_event(self):
        c=TwoSidedCUSUM(threshold=1);c.update(4.);self.assertTrue(c.last_alarm)
        for _ in range(3):
            ev=c.update(None);self.assertFalse(c.last_alarm);self.assertFalse(ev.reliable)
        self.assertEqual(c.alarms,1)

    def test_blank_event_amount_policy_and_invalid_values(self):
        self.assertEqual(_event_amount(float('nan'),'amount'),0.)
        self.assertEqual(_event_amount(2.,'amount'),2.)
        for bad in (-1.,float('inf'),'invalid'):
            with self.assertRaises(ValueError):_event_amount(bad,'amount')

    def test_loaded_d1namo_event_arrays_are_finite(self):
        data=Path(__file__).parents[1]/'data/raw/D1NAMO'
        series=load_d1namo(str(data));self.assertTrue(series)
        for item in series:
            for values in (item.insulin,item.bolus,item.carbs):
                self.assertTrue(np.isfinite(values).all());self.assertTrue((values>=0).all())

    def test_replay_input_shape_and_finite_event_contract(self):
        replay={'cgm':np.full(3,120.),'insulin':np.full(3,.08),'bolus':np.zeros(3),'carbs':np.zeros(3)}
        bad=dict(replay,carbs=np.zeros(2))
        with self.assertRaises(ValueError):run_scenario(BenchConfig(),None,TwinParams(),DeliveryCalibration(),replay=bad)
        bad=dict(replay,insulin=np.array([.08,np.nan,.08]))
        with self.assertRaises(ValueError):run_scenario(BenchConfig(),None,TwinParams(),DeliveryCalibration(),replay=bad)


class CausalMassSeparation(unittest.TestCase):
    def test_plant_is_invariant_to_balance_noise_with_feedback_disabled(self):
        original=VirtualBalanceTruthNode.read
        def shifted_measurement(device,now):
            r=original(device,now)
            # Measurement-only sensor offset; actual pump state is untouched.
            r['mass_g']+=1.;r['delta_g']+=.1
            return r
        for seed in (0,1,2):
            cfg=BenchConfig(mode='closed_loop',ablation='no_geco',seed=seed)
            reference=run_scenario(cfg,None,TwinParams(),DeliveryCalibration(),steps=48)
            with patch.object(VirtualBalanceTruthNode,'read',shifted_measurement):
                shifted=run_scenario(cfg,None,TwinParams(),DeliveryCalibration(),steps=48)
            self.assertEqual([r.true_glucose for r in reference.records],[r.true_glucose for r in shifted.records])
            self.assertEqual([r.virtual_plant_input_u for r in reference.records],[r.virtual_plant_input_u for r in shifted.records])
            self.assertNotEqual([r.local_measured_delta_g for r in reference.records],[r.local_measured_delta_g for r in shifted.records])

    def test_emission_mapping_and_recorded_measurement_domains(self):
        result=run_scenario(BenchConfig(mode='closed_loop'),None,TwinParams(),DeliveryCalibration(),steps=16)
        for row in result.records:
            self.assertAlmostEqual(row.virtual_plant_input_u,row.pump_emitted_mass_g/.1005)
            self.assertEqual(row.pump_executed_physical_u,row.virtual_plant_input_u)
            self.assertEqual(row.local_measured_delta_g,row.delta_mass_g)
            self.assertTrue(row.network_truth_accepted)
            self.assertAlmostEqual(row.network_reported_delta_g,row.local_measured_delta_g,places=4)
        json.dumps([dataclasses.asdict(r) for r in result.records],allow_nan=False)

    def test_missing_measurement_remains_unreliable(self):
        keys={name:bytes([1])*32 for name in ('cgm','gateway','pump','truth','updater')}
        runtime=GatewayRuntime(BenchConfig(),keys,TwinParams(),DeliveryCalibration())
        evidence,observation=runtime.reconcile(.1,None,0.)
        self.assertFalse(evidence.reliable);self.assertIsNone(observation)
        self.assertEqual(len(runtime.delivery.history),0)


if __name__=='__main__':unittest.main()
