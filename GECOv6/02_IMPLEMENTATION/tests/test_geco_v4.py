"""GECO v4 automated tests: wire/crypto, protocol invariants, twins, fusion, kernel,
delivery reconciliation, HAL faults, attacks, audit chain, and end-to-end bench runs.

Run:  PYTHONPATH=/tmp/pylib:. python -m unittest discover -s tests -v
"""
import os, sys, unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from geco_v4.wire import Signer, Envelope, verify_signature, sign_with_key, CGM, CMD, ACK
from geco_v4.protocol import ProtocolTwin
from geco_v4.physiology import PhysiologyTwin, TwinParams, GlucoseModel, simulated_isf, p3_for_isf
from geco_v4.detectors import TwoSidedCUSUM, OneSidedAccumulator, provenance_evidence, integrity_evidence
from geco_v4.fusion import DependencyAwareFusion, Severity, Assessment
from geco_v4.kernel import SafetyKernel, KernelContext
from geco_v4.delivery import DeliveryCalibration, DeliveryTwin
from geco_v4.hal import VirtualSyringePump, VirtualBalanceTruthNode, PumpFault
from geco_v4.audit import HashChainLog
from geco_v4.attacks import catalogue
from geco_v4.bench import BenchConfig, run_scenario
from geco_v4.calibrate import calibrate_delivery


class TestWire(unittest.TestCase):
    def test_sign_verify_roundtrip(self):
        s = Signer("gw-01", b"k"*32, "protected")
        e = s.make("pump-01", CMD, 1000.0, {"units": 0.25, "cmd_id": "c1"})
        self.assertTrue(verify_signature(e, b"k"*32))
        e2 = Envelope.from_wire(e.to_wire())
        self.assertTrue(verify_signature(e2, b"k"*32))

    def test_tamper_breaks_signature(self):
        s = Signer("cgm-01", b"z"*32, "protected")
        e = s.make("gw-01", CGM, 1000.0, {"glucose_mgdl": 120.0})
        e.payload["glucose_mgdl"] = 300.0
        self.assertFalse(verify_signature(e, b"z"*32))

    def test_wrong_key_fails(self):
        e = Signer("cgm-01", b"a"*32, "protected").make("gw-01", CGM, 1.0, {"glucose_mgdl": 100.0})
        self.assertFalse(verify_signature(e, b"b"*32))


class TestProtocol(unittest.TestCase):
    def setup(self, profile="protected"):
        keys = {"cgm-01": b"c"*32}
        return ProtocolTwin(profile, {"cgm-01": {"key": keys["cgm-01"], "allowed_types": (CGM,)}}), Signer("cgm-01", keys["cgm-01"], profile)

    def test_accepts_valid(self):
        pt, s = self.setup()
        ok = pt.verify(s.make("gw-01", CGM, 100.0, {"glucose_mgdl": 120}), now=101.0)
        self.assertTrue(ok.accepted)

    def test_rejects_replayed_nonce(self):
        pt, s = self.setup()
        e = s.make("gw-01", CGM, 100.0, {"glucose_mgdl": 120})
        self.assertTrue(pt.verify(e, 101.0).accepted)
        e2 = Envelope.from_wire(e.to_wire()); e2.seq = 999
        v = pt.verify(e2, 101.0)
        self.assertFalse(v.accepted); self.assertIn("P03", v.violations)

    def test_rejects_nonmonotonic_sequence(self):
        pt, s = self.setup()
        pt.verify(s.make("gw-01", CGM, 100.0, {"glucose_mgdl": 120}), 101.0)
        old = Envelope("cgm-01", "gw-01", CGM, 1, 100.5, {"glucose_mgdl": 121})
        sign_with_key(old, b"c"*32)
        v = pt.verify(old, 101.0)
        self.assertFalse(v.accepted); self.assertIn("P04", v.violations)

    def test_rejects_stale(self):
        pt, s = self.setup()
        v = pt.verify(s.make("gw-01", CGM, 100.0, {"glucose_mgdl": 120}), now=1000.0)
        self.assertFalse(v.accepted); self.assertIn("P05", v.violations)

    def test_rejects_unknown_sender(self):
        pt, _ = self.setup()
        rogue = Envelope("rogue", "gw-01", CGM, 1, 100.0, {"glucose_mgdl": 120})
        v = pt.verify(rogue, 100.5)
        self.assertFalse(v.accepted); self.assertIn("P01", v.violations)

    def test_legacy_accepts_unsigned_but_still_checks_sequence(self):
        pt, s = self.setup("legacy")
        e = Envelope("cgm-01", "gw-01", CGM, 5, 100.0, {"glucose_mgdl": 120})
        self.assertTrue(pt.verify(e, 100.5).accepted)
        e2 = Envelope("cgm-01", "gw-01", CGM, 3, 100.1, {"glucose_mgdl": 121})
        self.assertFalse(pt.verify(e2, 100.6).accepted)


class TestPhysiology(unittest.TestCase):
    def test_model_stable_benign(self):
        m = GlucoseModel(TwinParams(egp=0.9, p1=0.006))
        x = m.initial_state(120.0, 0.08)
        for _ in range(288):
            x = m.step(x, 0.08, 0.0)
        self.assertTrue(40 < x[0] < 300)

    def test_insulin_lowers_glucose(self):
        p = TwinParams(egp=0.9, p1=0.006, ib=3.0)
        self.assertGreater(simulated_isf(p.with_p3(p3_for_isf(p, 40.0))), 20.0)

    def test_bias_raises_standardized_innovation(self):
        twin = PhysiologyTwin(TwinParams(), r_std=9.0); twin.reset(120.0)
        base = []
        for _ in range(60):
            base.append(abs(twin.update(120.0 + np.random.default_rng(1).normal(0,3), 0.08, 0.0).standardized_innovation))
        twin2 = PhysiologyTwin(TwinParams(), r_std=9.0); twin2.reset(120.0)
        for _ in range(30): twin2.update(120.0, 0.08, 0.0)
        z_attacked = abs(twin2.update(220.0, 0.08, 0.0).standardized_innovation)
        self.assertGreater(z_attacked, 3.0)

    def test_missing_sample_flagged(self):
        twin = PhysiologyTwin(); twin.reset(120.0)
        out = twin.update(None, 0.08, 0.0)
        self.assertEqual(out.quality, "missing")


class TestDetectors(unittest.TestCase):
    def test_cusum_alarms_on_sustained_bias(self):
        c = TwoSidedCUSUM(drift=0.5, threshold=5.0)
        alarmed = False
        for _ in range(40):
            c.update(2.0)
            alarmed = alarmed or c.last_alarm
        self.assertTrue(alarmed)

    def test_cusum_quiet_on_noise(self):
        c = TwoSidedCUSUM(drift=0.5, threshold=8.0); rng = np.random.default_rng(0)
        alarms = sum(c.update(float(rng.normal(0, 1))).reliable and c.last_alarm for _ in range(500))
        self.assertLessEqual(alarms, 3)

    def test_one_sided_accumulator(self):
        a = OneSidedAccumulator(allowance=0.01, bound=0.05)
        for _ in range(10): a.update(0.03)
        self.assertTrue(a.alarm)


class TestFusion(unittest.TestCase):
    def test_single_group_high_is_uncorroborated_not_safe(self):
        f = DependencyAwareFusion(min_reliable_groups=2)
        from geco_v4.detectors import Evidence
        a = f.assess([Evidence("phys", "physiology", 0.95)])
        self.assertNotEqual(a.severity, Severity.SAFE_MODE)
        self.assertTrue(a.uncorroborated or a.abstained)

    def test_two_groups_corroborate_to_safe(self):
        from geco_v4.detectors import Evidence
        f = DependencyAwareFusion(min_reliable_groups=2)
        a = f.assess([Evidence("phys", "physiology", 0.95), Evidence("del", "actuation", 0.95)])
        self.assertEqual(a.severity, Severity.SAFE_MODE)

    def test_deterministic_actuation_triggers_safe(self):
        from geco_v4.detectors import Evidence
        f = DependencyAwareFusion()
        a = f.assess([Evidence("del", "actuation", 1.0), Evidence("phys", "physiology", 0.0)])
        self.assertEqual(a.severity, Severity.SAFE_MODE)
        self.assertEqual(a.deterministic_trigger, "actuation")

    def test_within_group_no_double_count(self):
        from geco_v4.detectors import Evidence
        f = DependencyAwareFusion()
        a = f.assess([Evidence("a", "physiology", 0.8), Evidence("b", "physiology", 0.8), Evidence("c", "physiology", 0.8)])
        self.assertLess(a.compromise_probability, 0.9)  # capped to strongest in the group


class TestKernel(unittest.TestCase):
    def _ctx(self, **kw):
        base = dict(now_s=0, glucose_mgdl=150.0, glucose_slope_mgdl_min=0.0, cgm_age_s=0, pump_age_s=0,
                    command_authenticated=True, predicted_glucose_30m=140.0, delivered_u_3h=0, reactive_u_3h=0,
                    assessment=Assessment(0.0, Severity.NORMAL, 1.0, False, {}, ()), actuation_score=0.0)
        base.update(kw); return KernelContext(**base)

    def test_blocks_unauthenticated(self):
        d = SafetyKernel().authorize(0.3, self._ctx(command_authenticated=False))
        self.assertEqual(d.allowed_u, 0.0)

    def test_predicted_low_stops(self):
        d = SafetyKernel().authorize(0.3, self._ctx(predicted_glucose_30m=70.0))
        self.assertEqual(d.allowed_u, 0.0)

    def test_actuation_requests_cutoff(self):
        d = SafetyKernel().authorize(0.3, self._ctx(actuation_score=0.95))
        self.assertTrue(d.cutoff_requested); self.assertEqual(d.allowed_u, 0.0)

    def test_per_command_cap(self):
        d = SafetyKernel(max_command_u=0.3).authorize(5.0, self._ctx())
        self.assertLessEqual(d.allowed_u, 0.3)


class TestDelivery(unittest.TestCase):
    def test_calibration_and_consistent(self):
        cal = calibrate_delivery()
        t = DeliveryTwin(cal)
        ev, obs = t.reconcile(0.3, 0.3, cal.expected_mass(0.3))
        self.assertLess(ev.score, 0.5); self.assertEqual(obs.label, "consistent")

    def test_over_delivery_detected(self):
        cal = calibrate_delivery(); t = DeliveryTwin(cal)
        ev, obs = t.reconcile(0.3, 0.3, cal.expected_mass(0.6))
        self.assertGreater(ev.score, 0.55)

    def test_unauthorised_flow_detected(self):
        cal = calibrate_delivery(); t = DeliveryTwin(cal)
        ev, obs = t.reconcile(0.0, 0.0, 0.2)
        self.assertEqual(obs.label, "unauthorised_flow"); self.assertEqual(ev.score, 1.0)


class TestHAL(unittest.TestCase):
    def test_pump_delivers_scaled_mass(self):
        p = VirtualSyringePump(); t = VirtualBalanceTruthNode(p); t.read(0)
        p.execute("c", 1.0, 0); p.tick(0, 300)
        r = t.read(300)
        self.assertGreater(r["delta_g"], 0.08)

    def test_over_fault(self):
        p = VirtualSyringePump(); p.fault = PumpFault("over", 2.0); t = VirtualBalanceTruthNode(p); t.read(0)
        p.execute("c", 0.5, 0); p.tick(0, 300); r = t.read(300)
        self.assertGreater(r["delta_g"], 0.09)  # ~1.0 U mass for a 0.5 U command

    def test_local_cutoff_trips_on_budget(self):
        p = VirtualSyringePump(); t = VirtualBalanceTruthNode(p); t.read(0)
        t.set_budget(0.3, 0)
        p.fault = PumpFault("over", 5.0); p.execute("c", 0.3, 0); p.tick(0, 300); t.read(300)
        self.assertTrue(t.is_tripped())


class TestAudit(unittest.TestCase):
    def test_chain_valid(self):
        log = HashChainLog()
        for i in range(10): log.append(float(i), {"x": i})
        self.assertTrue(log.verify()[0])

    def test_tamper_detected(self):
        log = HashChainLog()
        for i in range(10): log.append(float(i), {"x": i})
        log.tamper(4, "x", 999)
        self.assertFalse(log.verify()[0])


class TestBenchEndToEnd(unittest.TestCase):
    def _cfg(self, profile, ablation="geco_full"):
        return BenchConfig(profile=profile, ablation=ablation, cusum_threshold=12.0, cusum6_threshold=20.0, sigma6_mgdl=30.0, ar1_rho=0.9, innovation_inflation=1.5)
    def _params(self):
        return TwinParams(egp=0.9, p1=0.006, kc=0.6, ib=3.0)
    def _replay(self, n=300):
        rng = np.random.default_rng(3)
        cgm = 120 + 20*np.sin(np.arange(n)/30) + rng.normal(0,4,n)
        ins = np.full(n, 0.08); carbs = np.zeros(n); bolus = np.zeros(n)
        return {"cgm": cgm, "insulin": ins, "bolus": bolus, "carbs": carbs}

    def test_benign_no_cutoff(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=300)
        self.assertFalse(res.summary["cutoff_tripped"])

    def test_replay_prevented_in_protected(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=300,
                           attack_catalogue_id="RF-05", attack_start=96, attack_duration=48)
        self.assertGreaterEqual(res.summary["prevention_rate"] or 0.0, 0.9)

    def test_replay_accepted_in_legacy(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("legacy"), None, self._params(), cal, replay=self._replay(), steps=300,
                           attack_catalogue_id="RF-05", attack_start=96, attack_duration=48)
        self.assertLess(res.summary["prevention_rate"] or 0.0, 0.5)

    def test_credentialed_attack_mitigated(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=300,
                           attack_catalogue_id="RF-10", attack_start=96, attack_duration=48)
        self.assertTrue(res.summary["detected"])

    def test_actuator_over_delivery_cutoff(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=300,
                           attack_catalogue_id="ACT-01", attack_start=96, attack_duration=48)
        self.assertTrue(res.summary["cutoff_tripped"])

    def test_undetectable_set_not_falsely_claimed(self):
        cal = calibrate_delivery()
        res = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=300,
                           attack_catalogue_id="COORD-04", attack_start=96, attack_duration=48)
        # COORD-04 forges the truth node too: excess should NOT be contained (honest impossibility)
        self.assertGreater(res.summary["excess_u_during_attack"], 2.0)

    def test_delivery_ablation_lets_credentialed_through(self):
        cal = calibrate_delivery()
        full = run_scenario(self._cfg("protected", "geco_full"), None, self._params(), cal, replay=self._replay(), steps=300,
                            attack_catalogue_id="RF-10", attack_start=96, attack_duration=48)
        nodel = run_scenario(self._cfg("protected", "geco_no_delivery"), None, self._params(), cal, replay=self._replay(), steps=300,
                             attack_catalogue_id="RF-10", attack_start=96, attack_duration=48)
        self.assertLess(full.summary["excess_u_during_attack"], nodel.summary["excess_u_during_attack"])

    def test_reproducible(self):
        cal = calibrate_delivery()
        a = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=200, attack_catalogue_id="RF-10", attack_start=96, attack_duration=48)
        b = run_scenario(self._cfg("protected"), None, self._params(), cal, replay=self._replay(), steps=200, attack_catalogue_id="RF-10", attack_start=96, attack_duration=48)
        self.assertEqual(a.summary["excess_u_during_attack"], b.summary["excess_u_during_attack"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
