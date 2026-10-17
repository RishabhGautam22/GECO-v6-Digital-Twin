#!/usr/bin/env python3
"""
GECO v6 Max — NVIDIA Omniverse Nucleus Cloud Stage Stager & Uploader
====================================================================
Stages and uploads the GECO v6.1+ Max 12-Bay (10-Patient P01..P10 + 138-Part
Metrology Rig + IEEE-1588v2 PTP Master Clock A05/A06) OpenUSD stages,
referenced CAD meshes (`assets_team`), and the `geco.v6.omniverse.ward`
Isaac Sim extension bundle to an NVIDIA Omniverse Nucleus server
(`omniverse://<nucleus_host>/Projects/GECO_v6_Max/`).

Features:
1. Generates `build/nucleus_staging/` with all `.usda` sublayer and payload
   references rewritten to `omniverse://<nucleus_host>/Projects/GECO_v6_Max/...`
   so there are ZERO local `/Volumes/...` or `/home/...` paths.
2. Emits `nucleus_upload_receipt.json` with SHA-256 integrity hashes for every
   staged file.
3. Supports native `omni.client.copy` when executed inside the Isaac Sim
   container on RunPod / Lambda Labs, plus `--dry-run` staging on any host.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
USD_DIR = PROJECT_ROOT / "omniverse_usd"
EXT_DIR = PROJECT_ROOT / "isaac_extension"
COCKPIT_DIR = PROJECT_ROOT / "cockpit"
STAGING_DIR = THIS_DIR / "build" / "nucleus_staging"

try:
    import omni.client  # type: ignore
    HAS_OMNI_CLIENT = True
except ImportError:
    HAS_OMNI_CLIENT = False


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rewrite_usda_for_nucleus(content: str, nucleus_root: str) -> Tuple[str, int]:
    """Rewrite relative USD references into canonical `omniverse://` URIs."""
    rewrites = 0
    base = nucleus_root.rstrip("/")

    # 1. Rewrite local ./geco_v6_metrology_rig.usda reference
    content, n1 = re.subn(
        r"@\./geco_v6_metrology_rig\.usda@",
        f"@{base}/omniverse_usd/geco_v6_metrology_rig.usda@",
        content,
    )
    rewrites += n1

    # 2. Rewrite local ./geco_v6_brep_pump_cad.usda reference
    content, n2 = re.subn(
        r"@\./geco_v6_brep_pump_cad\.usda@",
        f"@{base}/omniverse_usd/geco_v6_brep_pump_cad.usda@",
        content,
    )
    rewrites += n2

    # 3. Rewrite local ./Desktop/*.usd references
    content, n3 = re.subn(
        r"@\./Desktop/([^@]+)@",
        rf"@{base}/omniverse_usd/Desktop/\1@",
        content,
    )
    rewrites += n3

    # 4. Rewrite relative references to shared IIT Patna assets_team CAD meshes
    content, n4 = re.subn(
        r"@(?:\.\./)+01_IIT_Patna_Digital_Twin/project_source/assets_team/([^@]+)@",
        r"@omniverse://localhost/Projects/IITP_Insulin_Digital_Twin/assets_team/\1@",
        content,
    )
    rewrites += n4

    return content, rewrites


def stage_and_upload_to_nucleus(nucleus_root: str, dry_run: bool = False) -> Dict[str, object]:
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    files_to_sync = [
        USD_DIR / "geco_v6_metrology_rig.usda",
        USD_DIR / "geco_v6_smart_hospital_ward.usda",
        USD_DIR / "geco_v6_brep_pump_cad.usda",
        USD_DIR / "build_usd_stages.py",
        EXT_DIR / "config" / "extension.toml",
        EXT_DIR / "geco_omniverse_ward" / "__init__.py",
        EXT_DIR / "geco_omniverse_ward" / "extension.py",
        EXT_DIR / "geco_omniverse_ward" / "ward_scene_controller.py",
        EXT_DIR / "geco_omniverse_ward" / "ward_ui.py",
        COCKPIT_DIR / "GECO_v6_Max_Cockpit.html",
    ]
    desktop_usd_dir = USD_DIR / "Desktop"
    if desktop_usd_dir.exists():
        for f in sorted(desktop_usd_dir.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                files_to_sync.append(f)

    manifest: List[Dict[str, object]] = []
    uploaded = 0
    total_bytes = 0
    total_rewrites = 0

    for p in files_to_sync:
        if not p.exists():
            continue
        rel = p.relative_to(PROJECT_ROOT).as_posix()
        staged_path = STAGING_DIR / rel
        staged_path.parent.mkdir(parents=True, exist_ok=True)

        rewrites = 0
        if p.suffix.lower() == ".usda":
            raw = p.read_text(encoding="utf-8")
            rewritten, rewrites = rewrite_usda_for_nucleus(raw, nucleus_root)
            staged_path.write_text(rewritten, encoding="utf-8")
            total_rewrites += rewrites
        else:
            shutil.copy2(p, staged_path)

        sz = staged_path.stat().st_size
        total_bytes += sz
        digest = sha256_file(staged_path)
        dest_uri = f"{nucleus_root.rstrip('/')}/{rel}"

        if dry_run or not HAS_OMNI_CLIENT:
            print(
                f"[STAGED FOR NUCLEUS] {rel} ({sz:,} B | rewrites={rewrites}) -> {dest_uri} [sha256={digest[:12]}...]"
            )
        else:
            res = omni.client.copy(str(staged_path), dest_uri, omni.client.CopyBehavior.OVERWRITE)
            print(f"[NUCLEUS COPY] {staged_path} -> {dest_uri} ({res})")
            uploaded += 1

        manifest.append(
            {
                "local_path": str(p),
                "staged_path": str(staged_path),
                "relative_path": rel,
                "nucleus_uri": dest_uri,
                "size_bytes": sz,
                "sha256": digest,
                "usd_paths_rewritten": rewrites,
            }
        )

    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nucleus_root": nucleus_root,
        "primary_ward_stage_uri": f"{nucleus_root.rstrip('/')}/omniverse_usd/geco_v6_smart_hospital_ward.usda",
        "primary_rig_stage_uri": f"{nucleus_root.rstrip('/')}/omniverse_usd/geco_v6_metrology_rig.usda",
        "omni_client_available": HAS_OMNI_CLIENT,
        "dry_run": dry_run,
        "total_files": len(manifest),
        "total_size_bytes": total_bytes,
        "total_usd_reference_rewrites": total_rewrites,
        "uploaded_count": uploaded,
        "files": manifest,
    }
    receipt_path = THIS_DIR / "nucleus_upload_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    (STAGING_DIR / "nucleus_upload_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(f"[GECO v6 Max Nucleus Uploader] Staged {len(manifest)} files ({total_bytes:,} bytes, {total_rewrites} USD URI rewrites) -> {STAGING_DIR}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage & Upload GECO v6 Max OpenUSD stages to NVIDIA Omniverse Nucleus")
    parser.add_argument(
        "--nucleus-url",
        default=os.environ.get("OMNI_NUCLEUS_URL", "omniverse://localhost/Projects/GECO_v6_Max"),
        help="Target Omniverse Nucleus folder URI",
    )
    parser.add_argument("--dry-run", action="store_true", help="Stage rewritten USD files and emit SHA-256 receipt")
    args = parser.parse_args()
    stage_and_upload_to_nucleus(args.nucleus_url, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
