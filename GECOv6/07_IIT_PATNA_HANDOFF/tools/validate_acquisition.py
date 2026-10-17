"""Offline acquisition contract check. No hardware control or measurement inference."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math

CHANNEL_UNITS = {
    "balance_indication": "g", "reference_mass": "g",
    "temperature": "degC", "requested_amount": "research_U",
    "authorized_amount": "research_U", "endpoint_ack_amount": "research_U",
    "stop_signal": "bool", "timing_marker": "bool",
}
SAMPLE_COLUMNS = ["trial_id", "device_id", "channel", "sequence", "device_time_s",
                  "host_monotonic_s", "value", "unit", "status", "calibration_id"]
EVENT_COLUMNS = ["trial_id", "event_id", "event_type", "device_id", "sequence",
                 "device_time_s", "host_monotonic_s", "source_record", "note"]

def number(value, label):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label}: a finite numeric value is required") from None
    if not math.isfinite(result):
        raise ValueError(f"{label}: nonfinite number")
    return result

def validate_samples(rows, trial_id, instrument_ids):
    errors, last = [], {}
    if not rows:
        return ["No acquired samples: blank template is incomplete"]
    for i, row in enumerate(rows, 2):
        try:
            if set(row) != set(SAMPLE_COLUMNS):
                raise ValueError("sample column contract differs")
            if row["trial_id"] != trial_id:
                raise ValueError("trial identifier mismatch")
            if row["device_id"] not in instrument_ids:
                raise ValueError("device has no instrument metadata")
            channel = row["channel"]
            if channel not in CHANNEL_UNITS or row["unit"] != CHANNEL_UNITS[channel]:
                raise ValueError("unknown channel or mismatched unit")
            seq = int(row["sequence"])
            if str(seq) != row["sequence"] or seq < 0:
                raise ValueError("sequence must be a nonnegative integer")
            dt = number(row["device_time_s"], "device time")
            ht = number(row["host_monotonic_s"], "host time")
            if dt < 0 or ht < 0:
                raise ValueError("negative monotonic time")
            key = row["device_id"], channel
            if key in last:
                oldseq, olddt, oldht = last[key]
                if seq <= oldseq or dt < olddt or ht < oldht:
                    raise ValueError("sequence or time regressed; preserve reset as a new stream")
            last[key] = seq, dt, ht
            status = row["status"]
            if status not in ("valid", "missing", "invalid"):
                raise ValueError("unrecognized observation status")
            if status == "valid":
                value = number(row["value"], "sample value")
                if channel in ("stop_signal", "timing_marker") and value not in (0, 1):
                    raise ValueError("binary signal must be 0 or 1")
                if channel in ("requested_amount", "authorized_amount", "endpoint_ack_amount") and value < 0:
                    raise ValueError("negative command amount")
                if channel in ("balance_indication", "reference_mass", "temperature") and not row["calibration_id"].strip():
                    raise ValueError("measurement lacks calibration identifier")
            elif row["value"].strip():
                raise ValueError("missing/invalid observation must not contain a numeric substitute")
        except (ValueError, TypeError) as exc:
            errors.append(f"samples.csv row {i}: {exc}")
    return errors

def validate_folder(folder):
    folder = Path(folder)
    errors, hashes = [], {}
    paths = [folder / name for name in ("trial_metadata.json", "samples.csv", "events.csv")]
    for p in paths:
        if not p.is_file():
            errors.append(f"Missing {p.name}")
        else:
            hashes[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    if errors:
        return {"status": "INCOMPLETE", "errors": errors, "sha256": hashes}
    try:
        meta = json.loads(paths[0].read_text())
        for key in ("trial_id", "operator", "acquisition_date", "protocol_sha256", "fluid_identity", "outlet_definition", "software_revision"):
            if not isinstance(meta.get(key), str) or not meta[key].strip():
                errors.append(f"Metadata field {key} pending")
        ids = [x.get("device_id") for x in meta.get("instruments", [])]
        if not ids or any(not x for x in ids) or len(ids) != len(set(ids)):
            errors.append("Instrument identifiers are empty or duplicated")
        with paths[1].open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        errors.extend(validate_samples(rows, meta.get("trial_id"), ids))
        with paths[2].open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != EVENT_COLUMNS:
                errors.append("Event column contract differs")
            seen = set()
            for i, row in enumerate(reader, 2):
                try:
                    if row["trial_id"] != meta.get("trial_id") or not row["event_id"] or row["event_id"] in seen:
                        raise ValueError("event trial/id mismatch or duplicate")
                    seen.add(row["event_id"])
                    if row["device_id"] not in ids or not row["event_type"]:
                        raise ValueError("unknown event device or empty event type")
                    if int(row["sequence"]) < 0:
                        raise ValueError("negative sequence")
                    if number(row["device_time_s"], "event time") < 0 or number(row["host_monotonic_s"], "host time") < 0:
                        raise ValueError("negative event time")
                except (ValueError, TypeError) as exc:
                    errors.append(f"events.csv row {i}: {exc}")
    except (ValueError, TypeError, KeyError, OSError) as exc:
        errors.append(f"Unreadable acquisition contract: {exc}")
    return {"status": "FAIL" if errors else "PASS_DATA_CONTRACT_ONLY", "errors": errors,
            "sha256": hashes, "does_not_validate": ["calibration", "measurement accuracy", "clock alignment", "flow reconstruction", "physical stopping", "clinical safety"]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_folder")
    args = parser.parse_args()
    result = validate_folder(args.trial_folder)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "PASS_DATA_CONTRACT_ONLY" else 2)
