"""Verify and restore the exact recorded campaign source in a NEW workspace.

No campaign executes here. The current runtime has later benign legacy timing
repairs, so exact campaign reproduction deliberately uses preserved sources.
"""
from pathlib import Path
import argparse,hashlib,json,shutil

ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",choices=["primary","supplement"],required=True)
    p.add_argument("--destination",type=Path)
    p.add_argument("--verify-only",action="store_true")
    p.add_argument("--recalibrate",action="store_true",help="Preserve target config as a reference; leave calibration outputs empty for a new prepare invocation")
    a=p.parse_args();folder="comparative_study" if a.study=="primary" else "supplement_fasting"
    source=ROOT/"03_EXPERIMENTS"/folder
    receipt=json.loads((source/"FROZEN_SOURCE_RECEIPT.json").read_text())
    for row in receipt["files"]:
        if sha(ROOT/row["frozen_copy_relative_path"])!=row["sha256"]:raise RuntimeError("Preserved source mismatch: "+row["original_relative_path"])
    if a.verify_only:
        print(json.dumps({"status":"PASS","study":a.study,"source_files":len(receipt["files"]),"executed_campaign":False}));return
    if a.destination is None:p.error("--destination is required unless --verify-only")
    destination=a.destination.resolve()
    if destination.exists() and any(destination.iterdir()):raise RuntimeError("Destination must be new or empty")
    destination.mkdir(parents=True,exist_ok=True)
    for row in receipt["files"]:
        target=destination/row["original_relative_path"];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/row["frozen_copy_relative_path"],target)
    folders=["comparative_study"] if a.study=="primary" else ["comparative_study","supplement_fasting"]
    target_folder="comparative_study" if a.study=="primary" else "supplement_fasting"
    for folder in folders:
        src=ROOT/"03_EXPERIMENTS"/folder;dst=destination/"03_EXPERIMENTS"/folder;dst.mkdir(parents=True,exist_ok=True)
        for name in ("PREREGISTERED_SPEC.json","SYNTHETIC_PARAMETER_SPLIT.json","PREREGISTRATION_COMMIT.json","FROZEN_STUDY_CONFIG.json","FROZEN_SUPPLEMENT_CONFIG.json","CALIBRATION_RESULTS.json","CALIBRATION_DOMAIN_INVESTIGATION.json","FROZEN_SOURCE_RECEIPT.json"):
            copied_name=name
            if a.recalibrate and folder==target_folder:
                if name in ("FROZEN_STUDY_CONFIG.json","FROZEN_SUPPLEMENT_CONFIG.json"):copied_name="ORIGINAL_CONFIG_REFERENCE.json"
                elif name=="CALIBRATION_RESULTS.json":copied_name="ORIGINAL_CALIBRATION_RESULTS.json"
            if (src/name).exists():shutil.copy2(src/name,dst/copied_name)
        if not (a.recalibrate and folder==target_folder):
            if (src/"calibration_attempts.jsonl").exists():shutil.copy2(src/"calibration_attempts.jsonl",dst/"calibration_attempts.jsonl")
            if (src/"calibration_traces").exists():shutil.copytree(src/"calibration_traces",dst/"calibration_traces")
    command="python -m geco_v6_study.campaign execute --workers 4" if a.study=="primary" else "python -m geco_v6_study.supplement.study execute --workers 4"
    print(json.dumps({"restored":str(destination),"study":a.study,"recalibrate":a.recalibrate,"source_files":len(receipt["files"]),"executed_campaign":False,"next_working_directory":str(destination/"02_IMPLEMENTATION"),"optional_run_command":command,"calibration_required_before_execute":a.recalibrate}))
if __name__=="__main__":main()
