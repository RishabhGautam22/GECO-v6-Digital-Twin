"""Synthetic data-contract fixtures. These are not physical measurements."""
import unittest
from validate_acquisition import validate_samples

class AcquisitionContractTests(unittest.TestCase):
    def row(self, **changes):
        row = dict(trial_id="SYNTHETIC_TEST", device_id="balance_fixture", channel="balance_indication",
                   sequence="0", device_time_s="0", host_monotonic_s="100", value="-0.01",
                   unit="g", status="valid", calibration_id="SYNTHETIC_CALIBRATION_FIXTURE")
        row.update(changes)
        return row
    def check(self, rows):
        return validate_samples(rows, "SYNTHETIC_TEST", ["balance_fixture"])
    def test_signed_mass_preserved(self):
        self.assertEqual(self.check([self.row()]), [])
    def test_missing_is_not_zero(self):
        self.assertTrue(self.check([self.row(status="missing", value="0")]))
        self.assertEqual(self.check([self.row(status="missing", value="")]), [])
    def test_nan_infinity_rejected(self):
        for value in ("NaN", "inf", "-inf"):
            self.assertTrue(self.check([self.row(value=value)]))
    def test_wrong_units_rejected(self):
        self.assertTrue(self.check([self.row(unit="mg")]))
    def test_order_and_reset_explicit(self):
        self.assertTrue(self.check([self.row(), self.row()]))
        self.assertTrue(self.check([self.row(), self.row(sequence="1", device_time_s="-1")]))
    def test_empty_template_not_validation(self):
        self.assertTrue(self.check([]))
    def test_calibration_and_device_required(self):
        self.assertTrue(self.check([self.row(calibration_id="")]))
        self.assertTrue(self.check([self.row(device_id="unknown")]))

if __name__ == "__main__":
    unittest.main()
