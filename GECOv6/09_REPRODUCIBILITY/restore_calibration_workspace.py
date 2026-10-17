"""Restore a fresh fit/tune or frozen internal-test workspace; never run a fit."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"03_EXPERIMENTS/filter_calibration"
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=["refit","frozen-test"],required=True)
    p.add_argument("--destination",type=Path)
    p.add_argument("--verify-only",action="store_true")
    a=p.parse_args();freeze=json.loads((OUT/"FIT_FREEZE_RECEIPT.json").read_text())
    for name,expected in freeze["source_hashes"].items():
        if sha(ROOT/name)!=expected:raise RuntimeError("Calibration source mismatch: "+name)
    manifest=json.loads((ROOT/"09_REPRODUCIBILITY/PARTICIPANT_SOURCE_FILES.json").read_text())
    for row in manifest["files"]:
        if sha(ROOT/row["path"])!=row["sha256"]:raise RuntimeError("Participant source mismatch: "+row["path"])
    if sha(OUT/"FROZEN_CALIBRATION.json")!=freeze["frozen_calibration_sha256"]:raise RuntimeError("Frozen calibration mismatch")
    if a.verify_only:
        print(json.dumps({"status":"PASS","sources":len(freeze["source_hashes"]),"raw_files":len(manifest["files"]),"fit_executed":False}));return
    if a.destination is None:p.error("--destination required unless --verify-only")
    dest=a.destination.resolve()
    if dest.exists() and any(dest.iterdir()):raise RuntimeError("Destination must be new or empty")
    def copy(src,rel):
        dst=dest/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    # Preserve the runtime from the completed study; restore explicit fit-source
    # hashes over that copy if needed. Legacy bench differences do not enter fits.
    old=ROOT/"03_EXPERIMENTS/comparative_study/FROZEN_SOURCE/02_IMPLEMENTATION/geco_v4"
    for src in old.glob("*.py"):copy(src,Path("02_IMPLEMENTATION/geco_v4")/src.name)
    for name in freeze["source_hashes"]:copy(ROOT/name,Path(name))
    for row in manifest["files"]:
        # The extracted CSVs are the loader inputs. Archive copies are separately
        # hashed provenance; no photo/archive extraction is required for the fit.
        if row["path"].endswith(".csv"):copy(ROOT/row["path"],Path(row["path"]))
    names=["INPUT_ARRAY_MANIFEST.json"]
    if a.mode=="frozen-test":names += ["FROZEN_CALIBRATION.json","FIT_FREEZE_RECEIPT.json"]
    for name in names:copy(OUT/name,Path("03_EXPERIMENTS/filter_calibration")/name)
    copy(OUT/"FIT_FREEZE_RECEIPT.json",Path("03_EXPERIMENTS/filter_calibration/ORIGINAL_FIT_FREEZE_REFERENCE.json"))
    print(json.dumps({"restored":str(dest),"mode":a.mode,"fit_executed":False,"test_executed":False,"working_directory":str(dest),"next_command":"python 03_EXPERIMENTS/filter_calibration/run_calibration.py "+("fit --workers 4 --max-iter 80" if a.mode=="refit" else "test")}))
if __name__=="__main__":main()
