"""Canonical-fixture checks before any new supplemental parameter outcomes."""
import unittest
import numpy as np
from geco_v6_study import engine
from geco_v6_study.supplement.study import compensated_command,adapter,run_one,SupplementDetector

UNIT={"unit_id":"geco_original_fixture_99","family":"geco_original","body_weight_kg":75.,"factors":{k:1. for k in ("sensitivity","absorption","clearance","glucose_flux","glucose_effectiveness","gut_gain")}}

class SupplementChecks(unittest.TestCase):
    def test_compensation_is_nearest_achievable_command(self):
        candidates=np.arange(61)/200
        for target in (.001,.01,.025,.05,.08,.3):
            c=compensated_command(target)
            errors=[abs(engine.expected_mass(u)/.1005-target) for u in candidates]
            self.assertAlmostEqual(abs(c["nominal_quantization_residual_u_per_step"]),min(errors),places=14)
            self.assertAlmostEqual(c["nominal_bias_48h_u"],576*c["nominal_quantization_residual_u_per_step"])
    def test_zero_command_count_and_mapping(self):
        c=compensated_command(.001)
        self.assertTrue(c["compensated_zero_command"])
        self.assertEqual(c["nominal_emitted_u_per_step"],0)
    def test_adapter_removes_meals_and_restores_originals(self):
        original=engine.exogenous;detector=engine.Detector
        with adapter():
            noise=engine.exogenous(UNIT,999,576)
            self.assertFalse(np.any(noise["carbs"]))
        self.assertIs(engine.exogenous,original);self.assertIs(engine.Detector,detector)
    def test_mass_arm_is_same_accumulator_without_physiology(self):
        full=SupplementDetector("full",2,.005);mass=SupplementDetector("masscusum",2,.005)
        for _ in range(3):
            f=full.observe(.005,6.,6.);m=mass.observe(.005,None,None)
            self.assertEqual(f["mass_cusum"],m["mass_cusum"])
            self.assertEqual(m["score"],m["mass_cusum"])
        self.assertGreater(f["score"],m["score"])
        self.assertTrue(f["alarm"]);self.assertFalse(m["alarm"])
    def test_shared_constant_requests_and_physics_with_disabled_statistics(self):
        config={"params":{},"forecast_policy":{"kind":"persistence","hold_insulin_u":.08},"thresholds":{k:1e9 for k in ("full","masscusum","simple")}}
        spec={"steps":60,"dt_min":5.,"fault_start_step":10,"fault_end_step_exclusive":20,"warmup_steps":36}
        traces=[run_one(UNIT,999,"clean",arm,config,spec)["columns"] for arm in ("full_supervised","masscusum_supervised","simple_supervised","sham_supervised")]
        for c in traces:
            self.assertEqual(len(set(c["requested_u"])),1)
            self.assertFalse(any(c["carbs_g"]))
            for key in ("requested_u","authorized_u","actual_emitted_g","local_measured_delta_g","true_glucose_mgdl"):
                self.assertEqual(c[key],traces[0][key])
        self.assertTrue(any(x is not None for x in traces[0]["forecast30_mgdl"]))
        self.assertTrue(all(x is None for x in traces[1]["forecast30_mgdl"]))

if __name__=="__main__":unittest.main()
