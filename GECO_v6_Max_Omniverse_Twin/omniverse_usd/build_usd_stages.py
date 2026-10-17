#!/usr/bin/env python3
"""
GECO v6 Max — Native OpenUSD Stage Generator
============================================
Generates two production-grade OpenUSD (.usda) stages:
  1. omniverse_usd/geco_v6_metrology_rig.usda
     Exact 130-part gravimetric saline metrology rig read directly from
     GECOv6/06_RIG_AND_MEDIA/native/COMPONENTS.json, complete with PBR
     UsdPreviewSurface materials, BasisCurves fluid/wire paths, and
     UsdPhysics articulation joints (Revolute lead screw, Prismatic
     carriage/plunger, Prismatic pinch valve).
  2. omniverse_usd/geco_v6_smart_hospital_ward.usda
     6-Room Multi-Patient Smart Hospital ICU & Cyber-Physical Ward master
     stage referencing the 130-part metrology rig in Room 5 and modeling
     high-detail patient, fluidic debris, battery brownout, and MITM/Simplex
     hardware across Rooms 1–6.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent
GECOV6_ROOT = PROJECT_ROOT.parent / "GECOv6"
COMPONENTS_JSON = GECOV6_ROOT / "06_RIG_AND_MEDIA" / "native" / "COMPONENTS.json"

RIG_USDA_PATH = THIS_DIR / "geco_v6_metrology_rig.usda"
WARD_USDA_PATH = THIS_DIR / "geco_v6_smart_hospital_ward.usda"


# ---------------------------------------------------------------------------
# Material & Part Classification Helpers for the 130-Part Rig
# ---------------------------------------------------------------------------

CYLINDER_X_IDS = {
    "M04", "M05", "M10_215", "M10_284",
    "S01", "S02", "S03", "S04", "S05", "S06", "S07",
    "A04",
}

CYLINDER_Z_IDS = {
    "B02_30_30", "B02_30_390", "B02_570_30", "B02_570_390",
    "T02", "R01", "R02", "D02", "D04", "D05",
    "A01", "A06",
    "K01", "K02", "K03", "K11", "K12", "K13",
}


def is_cylinder_x(pid: str) -> bool:
    return pid in CYLINDER_X_IDS or pid.startswith("M05t_")


def is_cylinder_z(pid: str) -> bool:
    return pid in CYLINDER_Z_IDS


def classify_rig_group(pid: str) -> str:
    if pid.startswith("B"):
        return "Bench_And_Isolation"
    if pid.startswith("M"):
        return "Actuator_And_Mechanism"
    if pid.startswith("S"):
        return "Syringe_Assembly"
    if pid.startswith("V"):
        return "Pinch_Valve_Safety"
    if pid.startswith(("T", "R", "F")):
        return "Gravimetric_Balance_And_Fluid_Path"
    if pid.startswith(("G", "P", "C", "E", "W")):
        return "Electronics_Gateway_And_Wiring"
    if pid.startswith(("L", "D", "A", "K")):
        return "Metrology_Reference_And_Calibration"
    return "Misc_Rig"


def assign_rig_material(pid: str) -> str:
    if pid in ("S01", "R01", "D04"):
        return "Mat_BorosilicateGlass"
    if pid in ("S02", "R02", "F01", "D05"):
        return "Mat_SalineTeal"
    if pid in ("T05", "P01"):
        return "Mat_PCB_FR4"
    if pid in ("V01", "T06", "A05", "A06", "W01", "W06", "W09"):
        return "Mat_SafetyOrange"
    if pid in ("M07", "M08", "C01", "L03", "W04", "W05", "W07", "W08"):
        return "Mat_AnodizedBlue"
    if pid.startswith(("K0", "K1")):
        return "Mat_GoldCalibration"
    if pid.startswith("M05") or pid in ("M02_105", "M02_183", "M04", "D02"):
        return "Mat_StainlessSteel"
    if pid in ("B01", "M09_215", "M09_284", "M10_215", "M10_284", "S04", "S05", "S06", "S07", "T01", "E01", "D01", "B03"):
        return "Mat_ClinicalWhite"
    if pid in ("M03", "M06", "S03", "T03", "T04", "G01", "L01", "L02", "A01", "A02", "A03", "A04", "K20", "D03", "W02", "W03") or pid.startswith(("B02_", "S08_")):
        return "Mat_MatteDark"
    return "Mat_Aluminum"


def emit_pbr_materials(indent: str = "    ", root_prim: str = "/World") -> str:
    """Emit rich UsdPreviewSurface materials shared across the USD stages."""
    mats = [
        # (name, diffuseRGB, metallic, roughness, opacity, emissiveRGB, ior)
        ("Mat_Aluminum", (0.62, 0.67, 0.71), 0.78, 0.28, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_StainlessSteel", (0.76, 0.79, 0.83), 0.90, 0.18, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_BorosilicateGlass", (0.72, 0.88, 0.95), 0.05, 0.08, 0.34, (0.0, 0.02, 0.04), 1.47),
        ("Mat_SalineTeal", (0.02, 0.62, 0.56), 0.05, 0.14, 0.82, (0.0, 0.08, 0.07), 1.33),
        ("Mat_PCB_FR4", (0.03, 0.32, 0.21), 0.25, 0.35, 1.0, (0.0, 0.02, 0.01), 1.5),
        ("Mat_SafetyOrange", (0.94, 0.31, 0.06), 0.15, 0.30, 1.0, (0.08, 0.02, 0.0), 1.5),
        ("Mat_AnodizedBlue", (0.05, 0.46, 0.68), 0.45, 0.26, 1.0, (0.0, 0.03, 0.06), 1.5),
        ("Mat_MatteDark", (0.09, 0.11, 0.15), 0.22, 0.42, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_ClinicalWhite", (0.86, 0.89, 0.91), 0.06, 0.32, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_GoldCalibration", (0.88, 0.71, 0.24), 0.92, 0.16, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_HospitalFloor", (0.78, 0.82, 0.85), 0.05, 0.38, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_HospitalWall", (0.91, 0.93, 0.95), 0.02, 0.48, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_ObservationGlass", (0.68, 0.85, 0.92), 0.05, 0.06, 0.24, (0.0, 0.0, 0.0), 1.52),
        ("Mat_PatientSkin", (0.84, 0.67, 0.56), 0.02, 0.52, 1.0, (0.0, 0.0, 0.0), 1.4),
        ("Mat_HospitalGown", (0.38, 0.64, 0.78), 0.02, 0.65, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_BedMattress", (0.18, 0.28, 0.38), 0.05, 0.55, 1.0, (0.0, 0.0, 0.0), 1.5),
        ("Mat_DebrisAmber", (0.95, 0.62, 0.12), 0.10, 0.25, 0.95, (0.22, 0.10, 0.0), 1.48),
        ("Mat_AirBubble", (0.92, 0.97, 1.00), 0.0, 0.05, 0.45, (0.05, 0.08, 0.12), 1.0),
        ("Mat_BatteryHealthy", (0.10, 0.78, 0.35), 0.30, 0.25, 1.0, (0.02, 0.25, 0.08), 1.5),
        ("Mat_CyberRed", (0.92, 0.12, 0.16), 0.20, 0.22, 0.88, (0.35, 0.02, 0.04), 1.5),
        ("Mat_SimplexShield", (0.06, 0.82, 0.64), 0.15, 0.15, 0.38, (0.02, 0.30, 0.22), 1.45),
        ("Mat_ScreenTelemetry", (0.04, 0.12, 0.20), 0.10, 0.12, 1.0, (0.04, 0.26, 0.38), 1.5),
        ("Mat_NeonWhiteText", (0.98, 0.99, 1.00), 0.10, 0.14, 1.0, (0.72, 0.80, 0.90), 1.5),
        ("Mat_NeonCyanText", (0.18, 0.94, 1.00), 0.10, 0.14, 1.0, (0.12, 0.82, 0.98), 1.5),
        ("Mat_NeonGoldText", (1.00, 0.86, 0.24), 0.15, 0.16, 1.0, (0.82, 0.58, 0.08), 1.5),
    ]
    lines = [f'{indent}def Scope "Looks" (', f'{indent}    doc = "PBR UsdPreviewSurface Material Library for GECO v6 Max"', f'{indent}) {{']
    for name, diff, met, rough, op, em, ior in mats:
        lines.append(f"""{indent}    def Material "{name}"
{indent}    {{
{indent}        token outputs:surface.connect = <{root_prim}/Looks/{name}/PreviewShader.outputs:surface>
{indent}        def Shader "PreviewShader"
{indent}        {{
{indent}            uniform token info:id = "UsdPreviewSurface"
{indent}            color3f inputs:diffuseColor = ({diff[0]:.3f}, {diff[1]:.3f}, {diff[2]:.3f})
{indent}            color3f inputs:emissiveColor = ({em[0]:.3f}, {em[1]:.3f}, {em[2]:.3f})
{indent}            float inputs:metallic = {met:.3f}
{indent}            float inputs:roughness = {rough:.3f}
{indent}            float inputs:opacity = {op:.3f}
{indent}            float inputs:ior = {ior:.3f}
{indent}            token outputs:surface
{indent}        }}
{indent}    }}""")
    lines.append(f"{indent}}}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stage 1: 130-Part Native OpenUSD Metrology Rig
# ---------------------------------------------------------------------------

def generate_metrology_rig_usda() -> Tuple[int, Path]:
    if not COMPONENTS_JSON.exists():
        raise FileNotFoundError(f"COMPONENTS.json not found at {COMPONENTS_JSON}")

    data = json.loads(COMPONENTS_JSON.read_text(encoding="utf-8"))
    parts: List[Dict[str, Any]] = data["parts"]
    assert len(parts) >= 130, f"Expected >= 130 parts in COMPONENTS.json, got {len(parts)}"

    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for p in parts:
        grp = classify_rig_group(p["id"])
        grouped.setdefault(grp, []).append(p)

    lines: List[str] = []
    lines.append(f"""#usda 1.0
(
    defaultPrim = "GECOv6_Metrology_Rig"
    doc = "GECO v6 Max — {len(parts)}-Part Native OpenUSD Gravimetric Saline Metrology Rig (IIT Patna Calibration Testbed)"
    metersPerUnit = 1.0
    upAxis = "Z"
    timeCodesPerSecond = 24
    startTimeCode = 0
    endTimeCode = 240
)

def Xform "GECOv6_Metrology_Rig" (
    kind = "assembly"
    customData = {{
        string version = "GECOv6_Max_6.1+"
        int total_parts = {len(parts)}
        string source_manifest = "GECOv6/06_RIG_AND_MEDIA/native/COMPONENTS.json"
        string metrology_status = "CONCEPTUAL_IIT_PATNA_MEASUREMENTS_PENDING"
    }}
)
{{
    custom string geco:rig_version = "GECOv6-Max-130Plus-Part-Assembly"
    custom int geco:part_count = {len(parts)}
""")

    # Materials
    lines.append(emit_pbr_materials(indent="    ", root_prim="/GECOv6_Metrology_Rig"))
    lines.append("")

    # Emit all 130 parts organized by functional subassembly scope
    emitted_count = 0
    prim_paths_by_id: Dict[str, str] = {}

    for grp_name, grp_parts in grouped.items():
        lines.append(f'    def Xform "{grp_name}" (')
        lines.append('        kind = "group"')
        lines.append("    )")
        lines.append("    {")
        for p in grp_parts:
            pid = p["id"]
            pname = p["name"].replace('"', "'")
            prole = p["role"].replace('"', "'")
            pstatus = p.get("status", "CONCEPTUAL")
            pos_mm = p["position_mm"]
            px, py, pz = pos_mm[0] / 1000.0, pos_mm[1] / 1000.0, pos_mm[2] / 1000.0
            mat_name = assign_rig_material(pid)
            mat_path = f"</GECOv6_Metrology_Rig/Looks/{mat_name}>"
            prim_path = f"/GECOv6_Metrology_Rig/{grp_name}/Part_{pid}"
            prim_paths_by_id[pid] = prim_path

            dims = p["dimensions_mm"]
            if isinstance(dims, dict) and "path_mm" in dims:
                # Continuous fluid path F01 or electrical wire connection W01..W09, D03
                pts_mm = dims["path_mm"]
                radius_m = float(dims.get("radius_mm", 1.5)) / 1000.0
                pts_str = ", ".join(
                    f"({pt[0]/1000.0:.6f}, {pt[1]/1000.0:.6f}, {pt[2]/1000.0:.6f})"
                    for pt in pts_mm
                )
                widths_str = ", ".join(f"{radius_m * 2.0:.6f}" for _ in pts_mm)
                lines.append(f"""        def BasisCurves "Part_{pid}" (
            prepend apiSchemas = ["MaterialBindingAPI"]
        )
        {{
            uniform token type = "linear"
            int[] curveVertexCounts = [{len(pts_mm)}]
            point3f[] points = [{pts_str}]
            float[] widths = [{widths_str}] (
                interpolation = "vertex"
            )
            rel material:binding = {mat_path}
            custom string geco:component_id = "{pid}"
            custom string geco:name = "{pname}"
            custom string geco:role = "{prole}"
            custom string geco:status = "{pstatus}"
            custom double3 geco:position_mm = ({pos_mm[0]}, {pos_mm[1]}, {pos_mm[2]})
        }}""")
            elif is_cylinder_x(pid):
                dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])
                radius_m = (dx / 2.0) / 1000.0
                height_m = dz / 1000.0
                lines.append(f"""        def Cylinder "Part_{pid}" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
        )
        {{
            uniform token axis = "X"
            double radius = {radius_m:.6f}
            double height = {height_m:.6f}
            double3 xformOp:translate = ({px:.6f}, {py:.6f}, {pz:.6f})
            float3 xformOp:rotateXYZ = (0, 0, 0)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
            rel material:binding = {mat_path}
            custom string geco:component_id = "{pid}"
            custom string geco:name = "{pname}"
            custom string geco:role = "{prole}"
            custom string geco:status = "{pstatus}"
            custom double3 geco:position_mm = ({pos_mm[0]}, {pos_mm[1]}, {pos_mm[2]})
            custom double3 geco:dimensions_mm = ({dx}, {dy}, {dz})
        }}""")
            elif is_cylinder_z(pid):
                dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])
                radius_m = (dx / 2.0) / 1000.0
                height_m = dz / 1000.0
                lines.append(f"""        def Cylinder "Part_{pid}" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
        )
        {{
            uniform token axis = "Z"
            double radius = {radius_m:.6f}
            double height = {height_m:.6f}
            double3 xformOp:translate = ({px:.6f}, {py:.6f}, {pz:.6f})
            float3 xformOp:rotateXYZ = (0, 0, 0)
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
            rel material:binding = {mat_path}
            custom string geco:component_id = "{pid}"
            custom string geco:name = "{pname}"
            custom string geco:role = "{prole}"
            custom string geco:status = "{pstatus}"
            custom double3 geco:position_mm = ({pos_mm[0]}, {pos_mm[1]}, {pos_mm[2]})
            custom double3 geco:dimensions_mm = ({dx}, {dy}, {dz})
        }}""")
            else:
                dx, dy, dz = float(dims[0]), float(dims[1]), float(dims[2])
                sx, sy, sz = dx / 1000.0, dy / 1000.0, dz / 1000.0
                lines.append(f"""        def Cube "Part_{pid}" (
            prepend apiSchemas = ["MaterialBindingAPI", "PhysicsRigidBodyAPI", "PhysicsCollisionAPI"]
        )
        {{
            double size = 1.0
            double3 xformOp:translate = ({px:.6f}, {py:.6f}, {pz:.6f})
            float3 xformOp:rotateXYZ = (0, 0, 0)
            float3 xformOp:scale = ({sx:.6f}, {sy:.6f}, {sz:.6f})
            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            rel material:binding = {mat_path}
            custom string geco:component_id = "{pid}"
            custom string geco:name = "{pname}"
            custom string geco:role = "{prole}"
            custom string geco:status = "{pstatus}"
            custom double3 geco:position_mm = ({pos_mm[0]}, {pos_mm[1]}, {pos_mm[2]})
            custom double3 geco:dimensions_mm = ({dx}, {dy}, {dz})
        }}""")
            emitted_count += 1
        lines.append("    }")
        lines.append("")

    # Emit UsdPhysics Articulation & Joints for M05 Lead Screw, M07 Carriage, S03 Plunger, V01 Pinch Valve, T02 Balance Pan
    lines.append(f"""    def Scope "PhysicsJoints" (
        doc = "UsdPhysics Articulation Joints for GECO v6 Metrology Rig"
    )
    {{
        def PhysicsRevoluteJoint "Joint_M05_LeadScrew_Revolute"
        {{
            uniform token physics:axis = "X"
            rel physics:body0 = <{prim_paths_by_id["M01"]}>
            rel physics:body1 = <{prim_paths_by_id["M05"]}>
            point3f physics:localPos0 = (0.022, -0.001, 0.045)
            point3f physics:localPos1 = (0.0, 0.0, 0.0)
            float physics:lowerLimit = -36000.0
            float physics:upperLimit = 36000.0
        }}

        def PhysicsPrismaticJoint "Joint_M07_Carriage_Prismatic"
        {{
            uniform token physics:axis = "X"
            rel physics:body0 = <{prim_paths_by_id["M01"]}>
            rel physics:body1 = <{prim_paths_by_id["M07"]}>
            point3f physics:localPos0 = (-0.045, -0.001, 0.034)
            point3f physics:localPos1 = (0.0, 0.0, 0.0)
            float physics:lowerLimit = 0.0
            float physics:upperLimit = 0.085
        }}

        def PhysicsPrismaticJoint "Joint_S03_Plunger_Prismatic"
        {{
            uniform token physics:axis = "X"
            rel physics:body0 = <{prim_paths_by_id["S01"]}>
            rel physics:body1 = <{prim_paths_by_id["S03"]}>
            point3f physics:localPos0 = (-0.028, 0.0, 0.0)
            point3f physics:localPos1 = (0.0, 0.0, 0.0)
            float physics:lowerLimit = 0.0
            float physics:upperLimit = 0.075
        }}

        def PhysicsPrismaticJoint "Joint_V01_PinchValve_Prismatic"
        {{
            uniform token physics:axis = "Z"
            rel physics:body0 = <{prim_paths_by_id["V02"]}>
            rel physics:body1 = <{prim_paths_by_id["V01"]}>
            point3f physics:localPos0 = (0.0, 0.0, 0.031)
            point3f physics:localPos1 = (0.0, 0.0, 0.0)
            float physics:lowerLimit = -0.008
            float physics:upperLimit = 0.0
        }}

        def PhysicsPrismaticJoint "Joint_T02_BalancePan_Deflection"
        {{
            uniform token physics:axis = "Z"
            rel physics:body0 = <{prim_paths_by_id["T01"]}>
            rel physics:body1 = <{prim_paths_by_id["T02"]}>
            point3f physics:localPos0 = (0.0, 0.014, 0.027)
            point3f physics:localPos1 = (0.0, 0.0, 0.0)
            float physics:lowerLimit = -0.002
            float physics:upperLimit = 0.001
        }}
    }}
}}
""")

    RIG_USDA_PATH.write_text("\n".join(lines), encoding="utf-8")
    return emitted_count, RIG_USDA_PATH


# ---------------------------------------------------------------------------
# Stage 2: 6-Room Smart Hospital ICU & Cyber-Physical Ward Master Stage
# ---------------------------------------------------------------------------

def emit_patient_and_bed(
    indent: str,
    patient_prim_name: str,
    bed_prim_name: str,
    monitor_prim_name: str,
    pump_prim_name: str,
    patient_label: str,
    weight_kg: float,
    include_standard_pump: bool = True,
    staff_asset: str = "Human_Doctor.usd",
    staff_prim_name: str = "Bedside_Physician_3D",
    include_second_staff: bool = False,
) -> str:
    """Emit a detailed ICU Hospital Bed, 3D Rigged Patient avatar, Clinical Staff, IV Pole, Bedside Vital Monitor, and optional Pump."""
    scale_factor = max(0.86, min(1.05, (weight_kg / 72.0) ** 0.30))
    ps = 0.01 * scale_factor
    second_staff_block = ""
    if include_second_staff:
        second_staff_block = f"""
{indent}def SkelRoot "Bedside_ICU_Nurse_3D" (
{indent}    doc = "3D Rigged ICU Clinical Nurse Monitoring Patient & Infusion Line"
{indent}    prepend references = @./Characters/Human_Nurse.usd@
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (-1.25, 0.72, 0.0)
{indent}    float3 xformOp:rotateXYZ = (0.0, 0.0, -35.0)
{indent}    float3 xformOp:scale = (0.0096, 0.0096, 0.0096)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
{indent}}}"""

    pump_block = ""
    if include_standard_pump:
        pump_block = f"""
{indent}def Xform "{pump_prim_name}" (
{indent}    doc = "Wearable Tethered / Patch Insulin Pump Assembly"
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (0.38, -0.18, 0.92)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    custom double geco:commanded_basal_u_hr = 1.0
{indent}    custom double geco:line_pressure_kpa = 14.2
{indent}    custom double geco:battery_v_term = 3.98

{indent}    def Cube "Pump_Body" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        float3 xformOp:scale = (0.085, 0.054, 0.022)
{indent}        uniform token[] xformOpOrder = ["xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_MatteDark>
{indent}    }}
{indent}    def Cube "Pump_Screen" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (-0.008, 0.0, 0.0115)
{indent}        float3 xformOp:scale = (0.052, 0.036, 0.002)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ScreenTelemetry>
{indent}    }}
{indent}    def Cylinder "Borosilicate_Syringe_S01" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}        doc = "3mL Borosilicate Glass Syringe Barrel (BRep Bore = 3014.78 uL)"
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.0085
{indent}        double height = 0.056
{indent}        double3 xformOp:translate = (0.012, 0.016, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BorosilicateGlass>
{indent}        custom double geco:brep_usable_bore_ul = 3014.78
{indent}    }}
{indent}    def Cylinder "Luer_Cone_S04" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.0042
{indent}        double height = 0.012
{indent}        double3 xformOp:translate = (0.044, 0.016, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BorosilicateGlass>
{indent}        custom double geco:brep_deadspace_ul = 222.20
{indent}    }}
{indent}    def Cylinder "Reservoir" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.0072
{indent}        double height = 0.042
{indent}        double3 xformOp:translate = (0.014, 0.016, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_SalineTeal>
{indent}    }}
{indent}    def Cylinder "Plunger" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.0070
{indent}        double height = 0.009
{indent}        double3 xformOp:translate = (-0.010, 0.016, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_AnodizedBlue>
{indent}    }}
{indent}    def Cylinder "LeadScrew_M05" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.0040
{indent}        double height = 0.036
{indent}        double3 xformOp:translate = (-0.028, 0.016, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_GoldCalibration>
{indent}    }}
{indent}    def Cube "PinchValve_V01" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.052, 0.016, 0.012)
{indent}        float3 xformOp:scale = (0.009, 0.012, 0.012)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_SafetyOrange>
{indent}    }}
{indent}    def Cylinder "StepperMotor" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.008
{indent}        double height = 0.020
{indent}        double3 xformOp:translate = (-0.048, 0.016, 0.012)
{indent}        float3 xformOp:rotateXYZ = (0, 0, 0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}        rel material:binding = </World/Looks/Mat_StainlessSteel>
{indent}    }}
{indent}    def Cylinder "BatteryCell" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "X"
{indent}        double radius = 0.007
{indent}        double height = 0.048
{indent}        double3 xformOp:translate = (0.0, -0.016, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BatteryHealthy>
{indent}    }}
{indent}    def Cube "Button_1" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.028, -0.012, 0.012)
{indent}        float3 xformOp:scale = (0.008, 0.008, 0.003)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_AnodizedBlue>
{indent}    }}
{indent}    def Cube "Button_2" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.028, 0.0, 0.012)
{indent}        float3 xformOp:scale = (0.008, 0.008, 0.003)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_AnodizedBlue>
{indent}    }}
{indent}    def Cube "Button_3" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.028, 0.012, 0.012)
{indent}        float3 xformOp:scale = (0.008, 0.008, 0.003)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_SafetyOrange>
{indent}    }}
{indent}    def BasisCurves "InfusionTube" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token type = "linear"
{indent}        int[] curveVertexCounts = [5]
{indent}        point3f[] points = [(0.042, 0.016, 0.004), (0.080, 0.040, 0.015), (0.020, 0.110, 0.030), (-0.180, 0.160, 0.025), (-0.310, 0.180, 0.010)]
{indent}        float[] widths = [0.004, 0.004, 0.004, 0.004, 0.004] (interpolation = "vertex")
{indent}        rel material:binding = </World/Looks/Mat_SalineTeal>
{indent}    }}
{indent}}}"""

    return f"""{indent}def Xform "{bed_prim_name}"
{indent}{{
{indent}    double3 xformOp:translate = (0.0, 0.0, 0.0)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]

{indent}    def Xform "CAD_HospitalBed_Mesh" (
{indent}        prepend payload = @./Desktop/SM_HospitalBed_01b.usd@
{indent}    )
{indent}    {{
{indent}        float3 xformOp:rotateXYZ = (0.0, 0.0, -90.0)
{indent}        float3 xformOp:scale = (1.0, 1.0, 1.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:rotateXYZ", "xformOp:scale"]
{indent}    }}
{indent}    def Xform "CAD_SideTable_Mesh" (
{indent}        prepend payload = @./Desktop/SM_SideTable_02a.usd@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (-0.65, 1.05, 0.0)
{indent}        float3 xformOp:scale = (1.0, 1.0, 1.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}    }}
{indent}    def Xform "CAD_Computer_Mesh" (
{indent}        prepend payload = @./Desktop/SM_Computer_02b.usd@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (-0.65, 1.05, 0.81)
{indent}        float3 xformOp:scale = (1.0, 1.0, 1.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}    }}
{indent}    def Xform "CAD_SupplyCabinet_Mesh" (
{indent}        prepend payload = @./Desktop/SM_SupplyCabinet_01c.usd@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (-1.75, -1.45, 0.0)
{indent}        float3 xformOp:scale = (1.0, 1.0, 1.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}    }}
{indent}    def Xform "CAD_SupplyCart_Mesh" (
{indent}        prepend payload = @./Desktop/SM_SupplyCart_01e.usd@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (-2.05, 1.45, 0.0)
{indent}        float3 xformOp:scale = (1.0, 1.0, 1.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}    }}
{indent}    def Xform "BRep_CAD_Pump_Shell" (
{indent}        prepend references = @./geco_v6_brep_pump_cad.usda@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (0.38, -0.18, 0.92)
{indent}        float3 xformOp:scale = (0.01, 0.01, 0.01)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}    }}

{indent}    def Cube "BedFrame" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, 0.0, 0.52)
{indent}        float3 xformOp:scale = (2.15, 0.98, 0.10)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_Aluminum>
{indent}    }}
{indent}    def Cube "Mattress" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, 0.0, 0.65)
{indent}        float3 xformOp:scale = (2.05, 0.92, 0.16)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_BedMattress>
{indent}    }}
{indent}    def Cube "Headboard" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (-1.06, 0.0, 0.88)
{indent}        float3 xformOp:scale = (0.06, 0.98, 0.68)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ClinicalWhite>
{indent}    }}
{indent}}}

{indent}def SkelRoot "{staff_prim_name}" (
{indent}    doc = "3D Rigged Clinical Specialist Attending Bedside"
{indent}    prepend references = @./Characters/{staff_asset}@
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (-0.15, 0.92, 0.12)
{indent}    float3 xformOp:rotateXYZ = (0.0, 0.0, -10.0)
{indent}    float3 xformOp:scale = (0.01, 0.01, 0.01)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
{indent}}}{second_staff_block}

{indent}def Xform "{patient_prim_name}" (
{indent}    doc = "{patient_label}"
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (0.0, 0.0, 0.78)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    custom string geco:patient_profile = "{patient_label}"
{indent}    custom double geco:weight_kg = {weight_kg:.1f}
{indent}    custom double geco:bg_mg_dl = 115.0
{indent}    custom double geco:cgm_mg_dl = 115.0
{indent}    custom double geco:iob_u = 1.25

{indent}    def SkelRoot "Human_Patient_3D" (
{indent}        doc = "20,000-Vertex Rigged Reallusion 3D Human Patient Supine on Hospital Bed"
{indent}        prepend references = @./Characters/Human_Patient_Supine.usd@
{indent}    )
{indent}    {{
{indent}        double3 xformOp:translate = (0.85, 0.0, 0.28)
{indent}        float3 xformOp:rotateXYZ = (90.0, 0.0, -90.0)
{indent}        float3 xformOp:scale = ({ps:.5f}, {ps:.5f}, {ps:.5f})
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
{indent}    }}

{indent}    def Sphere "Head" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        double radius = 0.115
{indent}        double3 xformOp:translate = (-0.68, 0.0, 0.14)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_PatientSkin>
{indent}    }}
{indent}    def Cube "Torso" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (-0.18, 0.0, 0.09)
{indent}        float3 xformOp:scale = (0.64, 0.38, 0.20)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalGown>
{indent}    }}
{indent}    def Cylinder "LeftArm" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        uniform token axis = "X"
{indent}        double radius = 0.048
{indent}        double height = 0.56
{indent}        double3 xformOp:translate = (-0.16, 0.25, 0.08)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_PatientSkin>
{indent}    }}
{indent}    def Cylinder "RightArm" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        uniform token axis = "X"
{indent}        double radius = 0.048
{indent}        double height = 0.56
{indent}        double3 xformOp:translate = (-0.16, -0.25, 0.08)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_PatientSkin>
{indent}    }}
{indent}    def Cylinder "LeftLeg" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        uniform token axis = "X"
{indent}        double radius = 0.068
{indent}        double height = 0.78
{indent}        double3 xformOp:translate = (0.48, 0.11, 0.07)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalGown>
{indent}    }}
{indent}    def Cylinder "RightLeg" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        token visibility = "invisible"
{indent}        uniform token axis = "X"
{indent}        double radius = 0.068
{indent}        double height = 0.78
{indent}        double3 xformOp:translate = (0.48, -0.11, 0.07)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalGown>
{indent}    }}
{indent}    def Cylinder "AbdominalInfusionPatch" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "Z"
{indent}        double radius = 0.024
{indent}        double height = 0.008
{indent}        double3 xformOp:translate = (0.04, -0.09, 0.24)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_ClinicalWhite>
{indent}    }}
{indent}    def Cylinder "CannulaHub" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "Z"
{indent}        double radius = 0.009
{indent}        double height = 0.014
{indent}        double3 xformOp:translate = (0.04, -0.09, 0.248)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_SalineTeal>
{indent}    }}
{indent}    def Cube "DexcomCGMPod" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.02, 0.11, 0.245)
{indent}        float3 xformOp:scale = (0.036, 0.022, 0.010)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ClinicalWhite>
{indent}    }}
{indent}    def Sphere "CGMStatusLED" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double radius = 0.004
{indent}        double3 xformOp:translate = (0.02, 0.11, 0.254)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BatteryHealthy>
{indent}    }}
{indent}}}

{indent}def Xform "IV_Pole"
{indent}{{
{indent}    double3 xformOp:translate = (-0.75, -0.70, 0.0)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    def Cylinder "StandRod" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "Z"
{indent}        double radius = 0.016
{indent}        double height = 1.85
{indent}        double3 xformOp:translate = (0.0, 0.0, 0.925)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_StainlessSteel>
{indent}    }}
{indent}    def Cylinder "SalineBag" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        uniform token axis = "Z"
{indent}        double radius = 0.055
{indent}        double height = 0.22
{indent}        double3 xformOp:translate = (0.0, 0.08, 1.68)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BorosilicateGlass>
{indent}    }}
{indent}}}

{indent}def Xform "{monitor_prim_name}"
{indent}{{
{indent}    double3 xformOp:translate = (-0.82, 0.72, 1.32)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    def Cube "MonitorHousing" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        float3 xformOp:scale = (0.08, 0.46, 0.34)
{indent}        uniform token[] xformOpOrder = ["xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_MatteDark>
{indent}    }}
{indent}    def Cube "VitalDisplayScreen" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.042, 0.0, 0.0)
{indent}        float3 xformOp:scale = (0.006, 0.42, 0.30)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ScreenTelemetry>
{indent}    }}
{indent}    def Sphere "AlarmBeacon" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double radius = 0.022
{indent}        double3 xformOp:translate = (0.0, 0.0, 0.19)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}        rel material:binding = </World/Looks/Mat_BatteryHealthy>
{indent}    }}
{indent}}}{pump_block}"""


_FONT_5X7: Dict[str, Tuple[str, ...]] = {
    "A": (" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "B": ("#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "),
    "C": (" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"),
    "D": ("#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "),
    "E": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"),
    "F": ("#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "),
    "G": (" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ####"),
    "H": ("#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"),
    "I": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"),
    "J": ("  ###", "   # ", "   # ", "   # ", "#  # ", "#  # ", " ##  "),
    "K": ("#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"),
    "L": ("#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"),
    "M": ("#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"),
    "N": ("#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"),
    "O": (" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "P": ("#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "),
    "Q": (" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"),
    "R": ("#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"),
    "S": (" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "),
    "T": ("#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "),
    "U": ("#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "),
    "V": ("#   #", "#   #", "#   #", "#   #", "#   #", " # # ", "  #  "),
    "W": ("#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"),
    "X": ("#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"),
    "Y": ("#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "Z": ("#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"),
    "0": (" ### ", "#  ##", "# # #", "# # #", "# # #", "##  #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"),
    "2": (" ### ", "#   #", "    #", "  ## ", " #   ", "#    ", "#####"),
    "3": ("#### ", "    #", "    #", " ### ", "    #", "    #", "#### "),
    "4": ("#   #", "#   #", "#   #", "#####", "    #", "    #", "    #"),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": (" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", "  #  ", "  #  ", "  #  "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "),
    ":": ("     ", "  #  ", "  #  ", "     ", "  #  ", "  #  ", "     "),
    "-": ("     ", "     ", "     ", "#####", "     ", "     ", "     "),
    "+": ("     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "),
    "%": ("##  #", "## # ", "   # ", "  #  ", " #   ", " # ##", "#  ##"),
    ".": ("     ", "     ", "     ", "     ", "     ", " ##  ", " ##  "),
    "/": ("    #", "   # ", "   # ", "  #  ", " #   ", " #   ", "#    "),
    " ": ("     ", "     ", "     ", "     ", "     ", "     ", "     "),
}


def emit_3d_text_mesh(
    indent: str,
    prim_name: str,
    text: str,
    center_xyz: Tuple[float, float, float],
    voxel_w: float,
    voxel_h: float,
    depth: float,
    mat_name: str,
) -> str:
    """Emit a consolidated 3D extruded block-letter UsdGeom.Mesh for `text`."""
    clean = text.upper()
    n_chars = len(clean)
    step_cols = 6.0  # 5 cols + 1 col spacing
    total_w = (n_chars * step_cols - 1.0) * voxel_w
    total_h = 7.0 * voxel_h
    cx, cy, cz = center_xyz
    start_x = cx - total_w / 2.0
    start_z = cz - total_h / 2.0
    y0 = cy - depth / 2.0
    y1 = cy + depth / 2.0

    pts: List[str] = []
    counts: List[str] = []
    indices: List[str] = []
    v_offset = 0

    for c_idx, ch in enumerate(clean):
        glyph = _FONT_5X7.get(ch, _FONT_5X7[" "])
        char_x0 = start_x + c_idx * step_cols * voxel_w
        for r_idx, row_str in enumerate(glyph):
            col = 0
            while col < 5:
                if row_str[col] == "#":
                    c_end = col
                    while c_end + 1 < 5 and row_str[c_end + 1] == "#":
                        c_end += 1
                    x0 = char_x0 + col * voxel_w
                    x1 = char_x0 + (c_end + 1) * voxel_w
                    z0 = start_z + (6 - r_idx) * voxel_h
                    z1 = start_z + (7 - r_idx) * voxel_h
                    box_pts = [
                        (x0, y0, z0),
                        (x1, y0, z0),
                        (x1, y0, z1),
                        (x0, y0, z1),
                        (x0, y1, z0),
                        (x1, y1, z0),
                        (x1, y1, z1),
                        (x0, y1, z1),
                    ]
                    for px, py, pz in box_pts:
                        pts.append(f"({px:.4f}, {py:.4f}, {pz:.4f})")
                    b = v_offset
                    faces = [
                        (b + 0, b + 1, b + 2, b + 3),
                        (b + 5, b + 4, b + 7, b + 6),
                        (b + 3, b + 2, b + 6, b + 7),
                        (b + 4, b + 5, b + 1, b + 0),
                        (b + 4, b + 0, b + 3, b + 7),
                        (b + 1, b + 5, b + 6, b + 2),
                    ]
                    for f0, f1, f2, f3 in faces:
                        counts.append("4")
                        indices.append(f"{f0}, {f1}, {f2}, {f3}")
                    v_offset += 8
                    col = c_end + 1
                else:
                    col += 1

    pts_str = ", ".join(pts)
    cnt_str = ", ".join(counts)
    idx_str = ", ".join(indices)
    return f"""{indent}def Mesh "{prim_name}" (
{indent}    prepend apiSchemas = ["MaterialBindingAPI"]
{indent})
{indent}{{
{indent}    uniform bool doubleSided = 1
{indent}    int[] faceVertexCounts = [{cnt_str}]
{indent}    int[] faceVertexIndices = [{idx_str}]
{indent}    point3f[] points = [{pts_str}]
{indent}    rel material:binding = </World/Looks/{mat_name}>
{indent}}}"""


CUBICLE_USD_SCENARIOS: Dict[str, Dict[str, str]] = {
    "ROOM_01": {
        "patient": "P01: Adult T1D (75 kg, ISF=42 mg/dL/U)",
        "code": "NOMINAL_CLOSED_LOOP",
        "name": "Nominal Closed-Loop & Meal Bolus Tracking",
        "category": "Baseline Closed-Loop Control",
        "tested": "NOMINAL_CLOSED_LOOP | MEAL_75G_DISTURBANCE | EKF_30MIN_FORECAST | HOVORKA_RK4_INTEGRITY",
        "response": "EKF 30-min forecast tracks meal peak within 16.82 mg/dL RMSE; zero alarms",
        "mat": "Mat_BatteryHealthy",
        "short_title": "R01: NOMINAL T1D",
        "short_sub": "100% TIR CLOSED-LOOP",
    },
    "ROOM_02": {
        "patient": "P02: Adolescent T1D (58 kg, ISF=52 mg/dL/U)",
        "code": "A1_A3_FLUIDIC_DEBRIS_OCCLUSION",
        "name": "Microbore Pipe Fibril Debris, Air Bubbles & Cannula Kink (A1/A3)",
        "category": "Category A: Fluidic & Subcutaneous Path Failures",
        "tested": "A1_UNPRIMED_LINE | A3_FIBRIL_DEBRIS_OCCLUSION | A3_AIR_BUBBLE_COMPLIANCE | A3_CANNULA_KINK_RELIEF",
        "response": "Inline pressure >65 kPa triggers physical occlusion alarm; zero false cyber lockouts",
        "mat": "Mat_DebrisAmber",
        "short_title": "R02: PIPE DEBRIS",
        "short_sub": "B2: 72% FIBRIL OCCL",
    },
    "ROOM_03": {
        "patient": "P03: Insulin-Resistant T1D (92 kg, ISF=28 mg/dL/U)",
        "code": "B1_B2_BATTERY_BROWNOUT_STICTION",
        "name": "LiPo ESR Surge, Voltage Brownout & Lead-Screw Stiction (B1/B2)",
        "category": "Category B: Electromechanical & Power-Rail Faults",
        "tested": "B1_LEAD_SCREW_BACKLASH | B1_O_RING_STICTION | B2_LIPO_ESR_BROWNOUT | B3_THERMAL_INSULIN_DEGRADATION",
        "response": "Undervoltage lockout at V_term < 3.25V; tactile alert and telemetry hold",
        "mat": "Mat_SafetyOrange",
        "short_title": "R03: BATT BROWNOUT",
        "short_sub": "B5: 3.05V SUPERCAP",
    },
    "ROOM_04": {
        "patient": "P04: Elderly Cardiac T1D (84 kg, ISF=35 mg/dL/U)",
        "code": "C1_C2_CYBER_MITM_SIMPLEX_CLAMP",
        "name": "RF Bolus Replay, Fake Hypo Spoof & Simplex Pinch-Valve Clamp (C1/C2)",
        "category": "Category C: Adversarial Cyber-Physical Attacks",
        "tested": "C1_UNAUTH_10U_BOLUS_REPLAY | C2_FAKE_HYPO_CGM_SPOOF | C3_STEALTH_CUSUM_DRIP | SIMPLEX_PINCH_VALVE_CLAMP",
        "response": "EKF innovation residual >4.5 sigma triggers hardware pinch-valve V01 in <50 ms",
        "mat": "Mat_CyberRed",
        "short_title": "R04: CYBER MITM +40",
        "short_sub": "C2: SIMPLEX CLAMP",
    },
    "ROOM_05": {
        "patient": "BENCH-05: 130-Part Gravimetric Saline Calibration Rig",
        "code": "METROLOGY_GRAVIMETRIC_CALIBRATION",
        "name": "Sub-Microliter Gravimetric Balance & Optical Plunger Verification",
        "category": "Hardware-in-the-Loop Metrology & CAD Verification",
        "tested": "BREP_3014UL_SYRINGE_BORE | LUER_222UL_DEADSPACE | GRAVIMETRIC_0_01MG_DRIFT | OPTICAL_LVDT_CROSSCHECK",
        "response": "Verifies 130-part CAD tolerances and cross-checks plunger travel against mass balance",
        "mat": "Mat_AnodizedBlue",
        "short_title": "R05: 138-PART RIG",
        "short_sub": "IITP METROLOGY LAB",
    },
    "ROOM_06": {
        "patient": "SOC-06: Central Nursing & Cyber-Physical Command Center",
        "code": "WARD_SOC_PTP_TELEMETRY_FUSION",
        "name": "12-Cubicle Telemetry Aggregation, PTP Clock Sync & Root-Cause Attribution",
        "category": "Ward-Wide Supervisory Control & Audit Logging",
        "tested": "IEEE1588_PTP_SYNC | MULTI_PATIENT_RISK_RANKING | PHYSICAL_VS_CYBER_SEPARATION | PAPER_REPORT_EXPORT",
        "response": "100% separation between mechanical occlusions (A/B) and cyber-attacks (C)",
        "mat": "Mat_SimplexShield",
        "short_title": "R06: SOC + PTP GM",
        "short_sub": "IEEE-1588 + WALL",
    },
    "ROOM_07": {
        "patient": "P05: Adult T1D (68 kg, ISF=45 mg/dL/U)",
        "code": "A2_DISLODGED_WET_CANNULA_SITE",
        "name": "Dislodged Subcutaneous Cannula & Zero-Pressure Skin Leakage (A2)",
        "category": "Category A: Fluidic & Subcutaneous Path Failures",
        "tested": "A2_DISLODGED_WET_CANNULA | SUBCUTANEOUS_LEAKAGE_70PCT | EKF_POSITIVE_INNOVATION_DRIFT",
        "response": "Normal line pressure + rising EKF BG residual flags wet infusion site (A2)",
        "mat": "Mat_DebrisAmber",
        "short_title": "R07: WET SITE LEAK",
        "short_sub": "A2: 0.14KPA CANNULA",
    },
    "ROOM_08": {
        "patient": "P06: Adult T1D (71 kg, ISF=44 mg/dL/U)",
        "code": "A4_PISA_COMPRESSION_DROPOUT",
        "name": "Pressure-Induced Sensor Attenuation (PISA) Sleep Compression Low (A4)",
        "category": "Category A: Fluidic & Subcutaneous Path Failures",
        "tested": "A4_PISA_SLEEP_COMPRESSION | FALSE_LOW_CGM_DROPOUT | STEP_RATE_GATE_REJECTION",
        "response": "Physiological rate-of-change gate rejects non-physiological -28 mg/dL/5min step drop",
        "mat": "Mat_DebrisAmber",
        "short_title": "R08: PISA SLEEP LOW",
        "short_sub": "A4: COMP ARTIFACT",
    },
    "ROOM_09": {
        "patient": "P07: Dawn-Phenomenon T1D (79 kg, ISF=36 mg/dL/U)",
        "code": "C4_RTC_CLOCK_SKEW_ATTACK",
        "name": "RTC Time-Shift (+3h) Circadian Basal Desynchronization Attack (C4)",
        "category": "Category C: Adversarial Cyber-Physical Attacks",
        "tested": "C4_RTC_CLOCK_SKEW_PLUS_3H | DAWN_BASAL_MISMATCH | PTP_GRANDMASTER_DRIFT_ALARM",
        "response": "MasterClock PTP Hub detects >10 ms clock offset and restores circadian basal schedule",
        "mat": "Mat_CyberRed",
        "short_title": "R09: CLOCK SKEW +3H",
        "short_sub": "C4: PTP DRIFT BLOCK",
    },
    "ROOM_10": {
        "patient": "P08: Insulin-Sensitive T1D (62 kg, ISF=55 mg/dL/U)",
        "code": "C3_STEALTH_CUSUM_DRIP_INJECTION",
        "name": "Low-and-Slow Stealthy +0.35 U/hr Micro-Basal Drift Attack (C3)",
        "category": "Category C: Adversarial Cyber-Physical Attacks",
        "tested": "C3_STEALTHY_MICRO_BOLUS_DRIP | SUB_SINGLE_STEP_THRESHOLD | TWO_SIDED_CUSUM_DETECTION",
        "response": "Two-sided CUSUM accumulator crosses h=4.5 threshold before BG drops below 70 mg/dL",
        "mat": "Mat_CyberRed",
        "short_title": "R10: CUSUM DRIP",
        "short_sub": "C3: STEALTH ATTACK",
    },
    "ROOM_11": {
        "patient": "P09: Brittle T1D (55 kg, ISF=60 mg/dL/U)",
        "code": "C1_RF_2X_BOLUS_REPLAY_MITIGATION",
        "name": "Adversarial 2x RF Meal Bolus Replay & Nonce Verification (C1)",
        "category": "Category C: Adversarial Cyber-Physical Attacks",
        "tested": "C1_RF_PACKET_REPLAY | CRYPTO_NONCE_REJECTION | IOB_CEILING_CLAMP",
        "response": "Duplicate sequence nonce rejected; Simplex kernel clamps delivery to safe basal",
        "mat": "Mat_CyberRed",
        "short_title": "R11: 2X RF REPLAY",
        "short_sub": "C1: NONCE REJECTED",
    },
    "ROOM_12": {
        "patient": "P10: Adult T1D (73 kg, ISF=40 mg/dL/U)",
        "code": "A1_UNPRIMED_68UL_CATHETER_DEFICIT",
        "name": "Unprimed 68.05 uL Catheter Dead-Volume Startup Delay (A1)",
        "category": "Category A: Fluidic & Subcutaneous Path Failures",
        "tested": "A1_UNPRIMED_68UL_DEADSPACE | ZERO_TISSUE_DELIVERY_LAG | AUTOMATED_PRIME_PROMPT",
        "response": "Tracks 68.05 uL F01 hold-up volume until meniscus reaches subcutaneous tip",
        "mat": "Mat_DebrisAmber",
        "short_title": "R12: UNPRIMED 68UL",
        "short_sub": "A1: DEADSPACE LAG",
    },
}


ROOM_ORIGINS: Dict[str, Tuple[float, float, float]] = {
    "ROOM_01": (-6.0, -3.0, 0.0),
    "ROOM_02": (0.0, -3.0, 0.0),
    "ROOM_03": (6.0, -3.0, 0.0),
    "ROOM_04": (-6.0, 3.0, 0.0),
    "ROOM_05": (0.0, 3.0, 0.0),
    "ROOM_06": (6.0, 3.0, 0.0),
    "ROOM_07": (-6.0, 9.0, 0.0),
    "ROOM_08": (0.0, 9.0, 0.0),
    "ROOM_09": (6.0, 9.0, 0.0),
    "ROOM_10": (-6.0, 15.0, 0.0),
    "ROOM_11": (0.0, 15.0, 0.0),
    "ROOM_12": (6.0, 15.0, 0.0),
}


def emit_room_shell(indent: str, room_id: str, room_title: str, origin: Tuple[float, float, float]) -> str:
    """Emit architectural floor slab, walls, glass observation partition, door frame, ceiling RectLight, 3D CubicleScenarioBoard, and 3D Rooftop FloatingRoomSign_3D."""
    ox, oy, oz = origin
    meta = CUBICLE_USD_SCENARIOS.get(room_id, {
        "patient": room_title,
        "code": "NOMINAL",
        "name": room_title,
        "category": "Clinical Scenario",
        "tested": "NOMINAL",
        "response": "Nominal monitoring",
        "mat": "Mat_BatteryHealthy",
        "short_title": room_id,
        "short_sub": "NOMINAL",
    })
    roof_title_mesh = emit_3d_text_mesh(
        f"{indent}    ",
        "FloatingText_Title",
        meta["short_title"],
        (0.0, -0.055, 0.16),
        0.040,
        0.048,
        0.045,
        "Mat_NeonWhiteText",
    )
    roof_sub_mesh = emit_3d_text_mesh(
        f"{indent}    ",
        "FloatingText_Subtitle",
        meta["short_sub"],
        (0.0, -0.055, -0.28),
        0.034,
        0.038,
        0.040,
        "Mat_NeonGoldText",
    )
    inner_title_mesh = emit_3d_text_mesh(
        f"{indent}    ",
        "InnerBoardText_Title",
        meta["short_title"],
        (0.0, -0.042, 0.18),
        0.015,
        0.016,
        0.018,
        "Mat_NeonWhiteText",
    )
    return f"""{indent}double3 xformOp:translate = ({ox:.3f}, {oy:.3f}, {oz:.3f})
{indent}uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}custom string geco:room_id = "{room_id}"
{indent}custom string geco:room_title = "{room_title}"
{indent}custom string geco:active_scenario_code = "{meta['code']}"
{indent}custom string geco:active_scenario_name = "{meta['name']}"
{indent}custom string geco:scenario_category = "{meta['category']}"
{indent}custom string geco:scenarios_tested = "{meta['tested']}"

{indent}def Xform "FloatingRoomSign_3D" (
{indent}    doc = "3D Rooftop Floating Room & Scenario Identification Sign Above {room_id}"
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (0.0, 1.55, 3.38)
{indent}    float3 xformOp:rotateXYZ = (-34.0, 0.0, 0.0)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    custom string geco:sign_title = "{meta['short_title']}"
{indent}    custom string geco:sign_subtitle = "{meta['short_sub']}"

{indent}    def Cube "SignBackingBoard" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        float3 xformOp:scale = (4.95, 0.07, 1.15)
{indent}        uniform token[] xformOpOrder = ["xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_MatteDark>
{indent}    }}
{indent}    def Cube "SignCategoryStripe" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, -0.042, 0.50)
{indent}        float3 xformOp:scale = (4.88, 0.02, 0.11)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/{meta['mat']}>
{indent}    }}
{roof_title_mesh}
{roof_sub_mesh}
{indent}}}

{indent}def Xform "CubicleScenarioBoard" (
{indent}    doc = "3D Overhead Cubicle Scenario & Telemetry Signage Board Showing Active Scenario and Test Matrix"
{indent})
{indent}{{
{indent}    double3 xformOp:translate = (-0.35, 1.65, 1.58)
{indent}    uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    custom string geco:cubicle_id = "{room_id}"
{indent}    custom string geco:patient_cohort = "{meta['patient']}"
{indent}    custom string geco:active_scenario_code = "{meta['code']}"
{indent}    custom string geco:active_scenario_name = "{meta['name']}"
{indent}    custom string geco:scenario_category = "{meta['category']}"
{indent}    custom string geco:scenarios_tested_list = "{meta['tested']}"
{indent}    custom string geco:expected_safety_response = "{meta['response']}"

{indent}    def Cube "BoardFrame" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        float3 xformOp:scale = (2.10, 0.05, 0.56)
{indent}        uniform token[] xformOpOrder = ["xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_MatteDark>
{indent}    }}
{indent}    def Cube "BoardScreenSurface" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, -0.028, 0.0)
{indent}        float3 xformOp:scale = (2.02, 0.01, 0.48)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ScreenTelemetry>
{indent}    }}
{indent}    def Cube "ScenarioStatusBanner" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, -0.034, 0.18)
{indent}        float3 xformOp:scale = (1.96, 0.010, 0.14)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/{meta['mat']}>
{indent}    }}
{inner_title_mesh}
{indent}    def Cube "Bar_BG" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (-0.55, -0.036, -0.05)
{indent}        float3 xformOp:scale = (0.28, 0.015, 0.22)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_SalineTeal>
{indent}    }}
{indent}    def Cube "Bar_Pressure" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, -0.036, -0.05)
{indent}        float3 xformOp:scale = (0.28, 0.015, 0.18)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_AnodizedBlue>
{indent}    }}
{indent}    def Cube "Bar_Safety" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.55, -0.036, -0.05)
{indent}        float3 xformOp:scale = (0.28, 0.015, 0.24)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/{meta['mat']}>
{indent}    }}
{indent}}}

{indent}def Xform "Architecture"
{indent}{{
{indent}    def Cube "FloorSlab" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, 0.0, -0.05)
{indent}        float3 xformOp:scale = (5.6, 4.6, 0.10)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalFloor>
{indent}    }}
{indent}    def Cube "BackWall" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (-2.75, 0.0, 1.45)
{indent}        float3 xformOp:scale = (0.10, 4.6, 2.90)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalWall>
{indent}    }}
{indent}    def Cube "NorthPartitionWall" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, 2.25, 1.45)
{indent}        float3 xformOp:scale = (5.6, 0.10, 2.90)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_HospitalWall>
{indent}    }}
{indent}    def Cube "SouthGlassPartition" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (0.0, -2.25, 1.45)
{indent}        float3 xformOp:scale = (5.6, 0.04, 2.90)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ObservationGlass>
{indent}    }}
{indent}    def Cube "SlidingGlassDoor" (
{indent}        prepend apiSchemas = ["MaterialBindingAPI"]
{indent}    )
{indent}    {{
{indent}        double size = 1.0
{indent}        double3 xformOp:translate = (2.75, -0.80, 1.15)
{indent}        float3 xformOp:scale = (0.04, 1.35, 2.30)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
{indent}        rel material:binding = </World/Looks/Mat_ObservationGlass>
{indent}    }}
{indent}    def RectLight "CeilingSurgicalLight"
{indent}    {{
{indent}        float inputs:intensity = 1800.0
{indent}        float inputs:width = 1.4
{indent}        float inputs:height = 0.8
{indent}        color3f inputs:color = (0.96, 0.98, 1.0)
{indent}        double3 xformOp:translate = (0.0, 0.0, 2.82)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate"]
{indent}    }}
{indent}}}"""


def emit_all_ward_cameras(indent: str = "    ") -> str:
    """Emit ward-wide and per-room multi-angle (PERSP, TOP, SIDE, FRONT, ORTHO_TOP, ORTHO_SIDE, MACRO) cameras."""
    cam_lines = [
        f'{indent}def Scope "Cameras"',
        f"{indent}{{",
        f"""{indent}    def Camera "Cam_Ward_Overview"
{indent}    {{
{indent}        float focalLength = 17.5
{indent}        double3 xformOp:translate = (8.2, -13.8, 12.6)
{indent}        float3 xformOp:rotateXYZ = (52.0, 0.0, 18.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_Ward_Top"
{indent}    {{
{indent}        float focalLength = 16.0
{indent}        double3 xformOp:translate = (3.8, 5.8, 26.5)
{indent}        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_Ward_Ortho_Top"
{indent}    {{
{indent}        uniform token projection = "orthographic"
{indent}        float horizontalAperture = 330.0
{indent}        float verticalAperture = 240.0
{indent}        double3 xformOp:translate = (3.8, 5.8, 25.0)
{indent}        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_Ward_Side"
{indent}    {{
{indent}        float focalLength = 18.0
{indent}        double3 xformOp:translate = (19.5, 4.2, 7.8)
{indent}        float3 xformOp:rotateXYZ = (68.0, 0.0, 90.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_Ward_Front"
{indent}    {{
{indent}        float focalLength = 17.0
{indent}        double3 xformOp:translate = (3.2, -13.5, 6.4)
{indent}        float3 xformOp:rotateXYZ = (70.0, 0.0, 6.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_LargeDashboardWall"
{indent}    {{
{indent}        float focalLength = 14.0
{indent}        double3 xformOp:translate = (7.6, 0.55, 1.55)
{indent}        float3 xformOp:rotateXYZ = (88.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}""",
    ]

    legacy_names = {
        "ROOM_01": "Cam_Room01_Nominal",
        "ROOM_02": "Cam_Room02_PipeDebris",
        "ROOM_03": "Cam_Room03_BatteryBrownout",
        "ROOM_04": "Cam_Room04_CyberMITM",
        "ROOM_05": "Cam_Room05_MetrologyRig",
        "ROOM_06": "Cam_Room06_SOC",
        "ROOM_07": "Cam_Room07_WetSite",
        "ROOM_08": "Cam_Room08_PISA",
        "ROOM_09": "Cam_Room09_ClockSkew",
        "ROOM_10": "Cam_Room10_StealthCUSUM",
        "ROOM_11": "Cam_Room11_BrittleReplay",
        "ROOM_12": "Cam_Room12_Unprimed",
    }

    for r_id, (ox, oy, oz) in ROOM_ORIGINS.items():
        leg_name = legacy_names[r_id]
        cam_lines.append(f"""{indent}    def Camera "{leg_name}"
{indent}    {{
{indent}        float focalLength = 15.0
{indent}        double3 xformOp:translate = ({ox + 2.65:.2f}, {oy - 2.25:.2f}, 1.92)
{indent}        float3 xformOp:rotateXYZ = (72.0, 0.0, 34.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_PERSP"
{indent}    {{
{indent}        float focalLength = 15.0
{indent}        double3 xformOp:translate = ({ox + 2.65:.2f}, {oy - 2.25:.2f}, 1.92)
{indent}        float3 xformOp:rotateXYZ = (72.0, 0.0, 34.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_TOP"
{indent}    {{
{indent}        float focalLength = 18.0
{indent}        double3 xformOp:translate = ({ox + 0.85:.2f}, {oy + 0.15:.2f}, 6.60)
{indent}        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_SIDE"
{indent}    {{
{indent}        float focalLength = 17.0
{indent}        double3 xformOp:translate = ({ox + 3.25:.2f}, {oy - 0.35:.2f}, 1.48)
{indent}        float3 xformOp:rotateXYZ = (84.0, 0.0, 90.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_FRONT"
{indent}    {{
{indent}        float focalLength = 15.5
{indent}        double3 xformOp:translate = ({ox + 0.65:.2f}, {oy - 3.10:.2f}, 1.68)
{indent}        float3 xformOp:rotateXYZ = (82.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_ORTHO_TOP"
{indent}    {{
{indent}        uniform token projection = "orthographic"
{indent}        float horizontalAperture = 82.0
{indent}        float verticalAperture = 54.0
{indent}        double3 xformOp:translate = ({ox + 0.95:.2f}, {oy + 0.15:.2f}, 8.00)
{indent}        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_ORTHO_SIDE"
{indent}    {{
{indent}        uniform token projection = "orthographic"
{indent}        float horizontalAperture = 68.0
{indent}        float verticalAperture = 42.0
{indent}        double3 xformOp:translate = ({ox + 3.80:.2f}, {oy - 0.25:.2f}, 1.65)
{indent}        float3 xformOp:rotateXYZ = (90.0, 0.0, 90.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}
{indent}    def Camera "Cam_{r_id}_MACRO"
{indent}    {{
{indent}        float focalLength = 26.0
{indent}        double3 xformOp:translate = ({ox + 1.15:.2f}, {oy - 0.95:.2f}, 1.30)
{indent}        float3 xformOp:rotateXYZ = (75.0, 0.0, 38.0)
{indent}        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
{indent}    }}""")
    cam_lines.append(f"{indent}}}")
    return "\n".join(cam_lines)


def generate_smart_hospital_ward_usda() -> Path:
    lines: List[str] = []
    lines.append("""#usda 1.0
(
    defaultPrim = "World"
    doc = "GECO v6 Max: 12-Cubicle Multi-Patient Smart Hospital ICU, Fluidic Debris, Battery Brownout, Cyber-MITM, Large Dashboard Wall & 130-Part IIT Patna Metrology Ward"
    metersPerUnit = 1.0
    upAxis = "Z"
    timeCodesPerSecond = 24
    startTimeCode = 0
    endTimeCode = 240
)

def Xform "World" (
    kind = "assembly"
)
{
    def PhysicsScene "WardPhysicsScene"
    {
        vector3f physics:gravityDirection = (0.0, 0.0, -1.0)
        float physics:gravityMagnitude = 9.81
    }

    def DistantLight "HospitalSunKeyLight"
    {
        float inputs:intensity = 1500.0
        float inputs:angle = 1.0
        color3f inputs:color = (0.98, 0.97, 0.95)
        float3 xformOp:rotateXYZ = (-48.0, 28.0, -20.0)
        uniform token[] xformOpOrder = ["xformOp:rotateXYZ"]
    }

    def DomeLight "HospitalEnvironmentDome"
    {
        float inputs:intensity = 450.0
        color3f inputs:color = (0.86, 0.91, 0.96)
    }
""")

    # Emit shared PBR Materials
    lines.append(emit_pbr_materials(indent="    "))
    lines.append("")

    # Emit Ward & Per-Room Multi-Angle / Orthographic Cameras
    lines.append(emit_all_ward_cameras(indent="    "))
    lines.append("")

    # Start /World/Ward
    lines.append('    def Xform "Ward" (')
    lines.append('        kind = "assembly"')
    lines.append("    )")
    lines.append("    {")

    # -----------------------------------------------------------------------
    # ROOM 01: Nominal Adult (75 kg)
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_01_Nominal_Adult" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_01", "Room 01 — Nominal Adult ICU (75 kg)", (-6.0, -3.0, 0.0)))
    lines.append(
        emit_patient_and_bed(
            "            ",
            "Patient_01_Adult_75kg",
            "Bed_01",
            "Monitor_01",
            "Pump_01",
            "Patient 01: Nominal Adult T1D (75 kg, ISF=42 mg/dL/U)",
            75.0,
            include_standard_pump=True,
            staff_asset="Human_Doctor.usd",
            staff_prim_name="Attending_Endocrinologist_3D",
            include_second_staff=True,
        )
    )
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOM 02: Fluidic Debris & Occlusion Microbore Pipe
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_02_Fluidic_Debris_And_Occlusion" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_02", "Room 02 — Fluidic Debris, Air Bubble & Occlusion Physics", (0.0, -3.0, 0.0)))
    lines.append(
        emit_patient_and_bed(
            "            ",
            "Patient_02_Adolescent_58kg",
            "Bed_02",
            "Monitor_02",
            "Pump_02",
            "Patient 02: Adolescent T1D (58 kg) — Microbore Pipe Debris & Occlusion",
            58.0,
            include_standard_pump=True,
            staff_asset="Human_Nurse.usd",
            staff_prim_name="Infusion_Care_Nurse_3D",
            include_second_staff=False,
        )
    )
    lines.append("""
            def Xform "InfusionPipe" (
                doc = "High-Detail Microbore Infusion Pipe with Fibril Debris, Air Bubbles, Cannula Kink & Inline Pressure Transducer"
            )
            {
                double3 xformOp:translate = (0.15, -0.05, 0.96)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                custom double geco:debris_fraction = 0.0
                custom double geco:air_bubble_ul = 0.0
                custom double geco:cannula_kink_ratio = 0.0
                custom double geco:line_pressure_kpa = 14.2
                custom double geco:effective_flow_u_hr = 1.0
                custom bool geco:relief_valve_open = false

                def Cylinder "OuterLumen" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "X"
                    double radius = 0.018
                    double height = 0.48
                    double3 xformOp:translate = (0.0, 0.0, 0.0)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_BorosilicateGlass>
                }

                def Cylinder "FluidColumn" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "X"
                    double radius = 0.013
                    double height = 0.46
                    double3 xformOp:translate = (0.0, 0.0, 0.0)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SalineTeal>
                }

                def Xform "DebrisParticles" (
                    doc = "Insulin Fibril & Isoelectric Micro-Precipitate Debris Particles Inside Microbore Lumen"
                )
                {
                    def Sphere "Debris_01" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.0055
                        double3 xformOp:translate = (-0.16, 0.002, 0.001)
                        float3 xformOp:scale = (1.0, 1.0, 1.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_DebrisAmber>
                    }
                    def Sphere "Debris_02" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.0062
                        double3 xformOp:translate = (-0.08, -0.003, -0.001)
                        float3 xformOp:scale = (1.0, 1.0, 1.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_DebrisAmber>
                    }
                    def Sphere "Debris_03" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.0070
                        double3 xformOp:translate = (0.01, 0.001, 0.002)
                        float3 xformOp:scale = (1.0, 1.0, 1.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_DebrisAmber>
                    }
                    def Sphere "Debris_04" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.0058
                        double3 xformOp:translate = (0.09, -0.002, 0.001)
                        float3 xformOp:scale = (1.0, 1.0, 1.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_DebrisAmber>
                    }
                    def Sphere "Debris_05" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.0065
                        double3 xformOp:translate = (0.16, 0.0, -0.001)
                        float3 xformOp:scale = (1.0, 1.0, 1.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_DebrisAmber>
                    }
                }

                def Xform "AirBubbles" (
                    doc = "Compressible Gas Pockets Increasing Line Compliance and Delaying Bolus Wavefronts"
                )
                {
                    def Sphere "Bubble_01" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.008
                        double3 xformOp:translate = (-0.12, 0.0, 0.003)
                        float3 xformOp:scale = (1.4, 0.9, 0.9)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_AirBubble>
                    }
                    def Sphere "Bubble_02" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double radius = 0.007
                        double3 xformOp:translate = (0.05, 0.0, 0.003)
                        float3 xformOp:scale = (1.3, 0.9, 0.9)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_AirBubble>
                    }
                }

                def Cylinder "LuerRestriction" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "X"
                    double radius = 0.022
                    double height = 0.036
                    double3 xformOp:translate = (-0.22, 0.0, 0.0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_AnodizedBlue>
                }

                def Cylinder "CannulaKinkZone" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "X"
                    double radius = 0.019
                    double height = 0.045
                    double3 xformOp:translate = (0.21, 0.0, 0.0)
                    float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SafetyOrange>
                }

                def Cube "InlinePressureTransducer" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-0.14, 0.0, 0.026)
                    float3 xformOp:scale = (0.044, 0.032, 0.022)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_PCB_FR4>
                }

                def Cylinder "BackPressureReliefValve" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.012
                    double height = 0.035
                    double3 xformOp:translate = (0.12, 0.0, 0.024)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_SafetyOrange>
                }
            }""")
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOM 03: Battery Brownout & Electromechanical Malfunction
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_03_Battery_Brownout_And_Malfunction" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_03", "Room 03 — Li-Ion Battery Brownout, Supercap Holdup & Actuator Stiction", (6.0, -3.0, 0.0)))
    lines.append(
        emit_patient_and_bed(
            "            ",
            "Patient_03_Elderly_82kg",
            "Bed_03",
            "Monitor_03",
            "Pump_03",
            "Patient 03: Elderly T1D (82 kg) — Battery Die-Down & Motor Stiction Cut-Away",
            82.0,
            include_standard_pump=False,
            staff_asset="Human_Doctor.usd",
            staff_prim_name="Bedside_Physician_3D",
            include_second_staff=False,
        )
    )
    lines.append("""
            def Xform "Pump_03" (
                doc = "Engineering Cut-Away Insulin Pump Exposing Battery Pack, Supercap Holdup, Motor Backlash & Fail-Safe Relay"
            )
            {
                double3 xformOp:translate = (0.35, -0.15, 0.94)
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Cube "CutawayChassis" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    float3 xformOp:scale = (0.28, 0.18, 0.065)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_BorosilicateGlass>
                }

                def Xform "BatteryPack"
                {
                    double3 xformOp:translate = (-0.08, -0.04, 0.0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]

                    def Cylinder "LiIon_Cell" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        uniform token axis = "X"
                        double radius = 0.018
                        double height = 0.085
                        double3 xformOp:translate = (0.0, 0.0, 0.0)
                        uniform token[] xformOpOrder = ["xformOp:translate"]
                        rel material:binding = </World/Looks/Mat_BatteryHealthy>
                        custom double geco:soc = 0.92
                        custom double geco:v_ocv = 4.08
                        custom double geco:v_term = 3.98
                        custom double geco:r_int_ohm = 0.18
                        custom double geco:temp_c = 28.4
                        custom string geco:power_state = "NOMINAL"
                    }
                }

                def Xform "PowerRegulation"
                {
                    double3 xformOp:translate = (-0.06, 0.04, 0.0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]

                    def Cylinder "SupercapHoldup" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        uniform token axis = "Z"
                        double radius = 0.014
                        double height = 0.036
                        double3 xformOp:translate = (-0.02, 0.0, 0.0)
                        uniform token[] xformOpOrder = ["xformOp:translate"]
                        rel material:binding = </World/Looks/Mat_AnodizedBlue>
                        custom double geco:holdup_energy_mj = 420.0
                    }

                    def Cube "BrownoutWatchdog" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double size = 1.0
                        double3 xformOp:translate = (0.03, 0.0, 0.0)
                        float3 xformOp:scale = (0.038, 0.032, 0.012)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_PCB_FR4>
                        custom bool geco:brownout_tripped = false
                        custom double geco:v_cutoff_threshold = 3.05
                    }
                }

                def Xform "Actuator"
                {
                    double3 xformOp:translate = (0.04, 0.0, 0.0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]

                    def Cube "StepperMotor_M03" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double size = 1.0
                        double3 xformOp:translate = (-0.03, 0.0, 0.0)
                        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                        float3 xformOp:scale = (0.042, 0.042, 0.042)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_MatteDark>
                        custom double geco:motor_current_ma = 185.0
                        custom bool geco:stiction_fault = false
                    }

                    def Cylinder "LeadScrew_BacklashZone" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        uniform token axis = "X"
                        double radius = 0.006
                        double height = 0.075
                        double3 xformOp:translate = (0.03, 0.0, 0.0)
                        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
                        rel material:binding = </World/Looks/Mat_StainlessSteel>
                        custom double geco:backlash_mm = 0.02
                    }

                    def Cylinder "OpticalEncoder" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        uniform token axis = "X"
                        double radius = 0.016
                        double height = 0.006
                        double3 xformOp:translate = (-0.058, 0.0, 0.0)
                        float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
                        rel material:binding = </World/Looks/Mat_GoldCalibration>
                    }
                }

                def Xform "Safety"
                {
                    double3 xformOp:translate = (0.10, -0.04, 0.0)
                    uniform token[] xformOpOrder = ["xformOp:translate"]

                    def Cube "FailSafeRelay" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        double size = 1.0
                        double3 xformOp:translate = (-0.015, 0.0, 0.0)
                        float3 xformOp:scale = (0.024, 0.018, 0.020)
                        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                        rel material:binding = </World/Looks/Mat_SafetyOrange>
                        custom bool geco:relay_closed = true
                    }

                    def Cylinder "PinchValve" (
                        prepend apiSchemas = ["MaterialBindingAPI"]
                    )
                    {
                        uniform token axis = "Z"
                        double radius = 0.012
                        double height = 0.032
                        double3 xformOp:translate = (0.02, 0.0, 0.0)
                        uniform token[] xformOpOrder = ["xformOp:translate"]
                        rel material:binding = </World/Looks/Mat_SafetyOrange>
                        custom bool geco:pinch_engaged = false
                    }
                }
            }""")
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOM 04: Cyber-Physical MITM & Simplex Safe-Basal Clamp
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_04_Cyber_MITM_And_Simplex_Clamp" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_04", "Room 04 — Cyber-Physical MITM Spoofing & GECO v6.1+ Simplex Safe-Basal Clamp", (-6.0, 3.0, 0.0)))
    lines.append(
        emit_patient_and_bed(
            "            ",
            "Patient_04_Brittle_64kg",
            "Bed_04",
            "Monitor_04",
            "Pump_04",
            "Patient 04: Brittle T1D (64 kg, ISF=55 mg/dL/U) — Adversarial MITM Defense",
            64.0,
            include_standard_pump=True,
            staff_asset="Human_Engineer.usd",
            staff_prim_name="Simplex_Security_Engineer_3D",
            include_second_staff=True,
        )
    )
    lines.append("""
            def Xform "CGM_04" (
                doc = "Target Wireless BLE CGM Transmitter Node"
            )
            {
                double3 xformOp:translate = (0.04, 0.14, 1.00)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                def Cube "CGMTransmitterBody" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    float3 xformOp:scale = (0.042, 0.026, 0.012)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_AnodizedBlue>
                }
            }

            def Xform "Rogue_MITM_Transceiver" (
                doc = "Adversarial Software-Defined Radio (SDR) Injecting +40 mg/dL CGM Bias, 2x Overdelivery & Truth Masking"
            )
            {
                double3 xformOp:translate = (1.35, -1.10, 1.15)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                custom bool geco:attack_active = false
                custom string geco:attack_mode = "NONE"

                def Cube "SDR_Enclosure" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    float3 xformOp:scale = (0.22, 0.16, 0.06)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_MatteDark>
                }
                def Cylinder "WhipAntenna" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.006
                    double height = 0.34
                    double3 xformOp:translate = (0.0, 0.0, 0.20)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
                def Cylinder "RF_WaveRing_01" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.18
                    double height = 0.008
                    double3 xformOp:translate = (-0.25, 0.22, 0.10)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
                def Cylinder "RF_WaveRing_02" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.28
                    double height = 0.008
                    double3 xformOp:translate = (-0.48, 0.42, 0.06)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
                def Cylinder "RF_WaveRing_03" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.38
                    double height = 0.008
                    double3 xformOp:translate = (-0.72, 0.62, 0.02)
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
            }

            def Xform "GECO_v61_Security_Gateway" (
                doc = "GECO v6.1+ 4-Channel EKF + CUSUM + Impedance + Power Supervisor Appliance"
            )
            {
                double3 xformOp:translate = (-0.55, -0.78, 1.12)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                custom double geco:ekf_innovation_score = 0.12
                custom double geco:cusum_drift_score = 0.08
                custom bool geco:simplex_clamp_engaged = false

                def Cube "GatewayApplianceBox" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    float3 xformOp:scale = (0.24, 0.18, 0.08)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_AnodizedBlue>
                }
            }

            def Xform "SimplexSafeBasalClamp" (
                doc = "Hardware-Enforced Simplex Safe-Basal Clamp & Protective Isolation Dome"
            )
            {
                double3 xformOp:translate = (0.38, -0.18, 0.94)
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Sphere "SimplexShieldDome" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double radius = 0.14
                    float3 xformOp:scale = (1.0, 1.0, 1.0)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SimplexShield>
                }
                def Cylinder "ClampStatusBeacon" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.020
                    double height = 0.045
                    double3 xformOp:translate = (0.0, 0.0, 0.16)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_BatteryHealthy>
                }
            }""")
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOM 05: IIT Patna 130-Part Gravimetric Metrology Lab
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_05_IITP_Metrology_Lab" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_05", "Room 05 — IIT Patna 130-Part Gravimetric Saline Metrology Lab", (0.0, 3.0, 0.0)))
    lines.append("""
            def SkelRoot "IITP_Metrology_Lead_Engineer_3D" (
                doc = "IIT Patna Biomedical Metrology Lead Engineer Calibrating 130-Part Gravimetric Rig"
                prepend references = @./Characters/Human_Engineer.usd@
            )
            {
                double3 xformOp:translate = (-0.25, -0.95, 0.0)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 180.0)
                float3 xformOp:scale = (0.01, 0.01, 0.01)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }

            def SkelRoot "Clinical_Calibration_Physician_3D" (
                doc = "Attending Physician Reviewing Gravimetric Micro-Bolus Accuracy"
                prepend references = @./Characters/Human_Doctor.usd@
            )
            {
                double3 xformOp:translate = (0.72, -0.82, 0.0)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 145.0)
                float3 xformOp:scale = (0.01, 0.01, 0.01)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }

            def Xform "OpticalIsolationTable"
            {
                double3 xformOp:translate = (0.0, 0.0, 0.0)
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Cube "GraniteBenchTop" (
                    prepend apiSchemas = ["MaterialBindingAPI", "PhysicsCollisionAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, 0.0, 0.82)
                    float3 xformOp:scale = (1.60, 1.05, 0.08)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_MatteDark>
                }
                def Cylinder "PneumaticLeg_FL" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.055
                    double height = 0.78
                    double3 xformOp:translate = (-0.68, -0.42, 0.39)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_StainlessSteel>
                }
                def Cylinder "PneumaticLeg_FR" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.055
                    double height = 0.78
                    double3 xformOp:translate = (0.68, -0.42, 0.39)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_StainlessSteel>
                }
                def Cylinder "PneumaticLeg_BL" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.055
                    double height = 0.78
                    double3 xformOp:translate = (-0.68, 0.42, 0.39)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_StainlessSteel>
                }
                def Cylinder "PneumaticLeg_BR" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.055
                    double height = 0.78
                    double3 xformOp:translate = (0.68, 0.42, 0.39)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_StainlessSteel>
                }
            }

            def Xform "MetrologyRig_130Part_Assembly" (
                doc = "Direct OpenUSD Reference to the 130-Part GECO v6 Gravimetric Saline Metrology Rig"
                prepend references = @./geco_v6_metrology_rig.usda@
            )
            {
                double3 xformOp:translate = (-0.40, -0.27, 0.872)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
            }""")
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOM 06: Central Nursing & Cybersecurity Operations Center (SOC)
    # -----------------------------------------------------------------------
    lines.append('        def Xform "Room_06_SOC_Command_Center" (')
    lines.append('            kind = "component"')
    lines.append("        )")
    lines.append("        {")
    lines.append(emit_room_shell("            ", "ROOM_06", "Room 06 — Central Nursing & Cyber-Physical SOC Command Center", (6.0, 3.0, 0.0)))
    lines.append("""
            def SkelRoot "SOC_Cyber_Security_Operator_3D" (
                doc = "Cyber-Physical Security Operator Monitoring EKF & CUSUM Telemetry Wall"
                prepend references = @./Characters/Human_Engineer.usd@
            )
            {
                double3 xformOp:translate = (-0.65, -1.05, 0.0)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 180.0)
                float3 xformOp:scale = (0.01, 0.01, 0.01)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }

            def SkelRoot "Chief_Medical_Officer_3D" (
                doc = "Chief Medical Officer Overseeing 10-Patient Smart Ward Safety"
                prepend references = @./Characters/Human_Doctor.usd@
            )
            {
                double3 xformOp:translate = (0.45, -1.05, 0.0)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 172.0)
                float3 xformOp:scale = (0.01, 0.01, 0.01)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }

            def SkelRoot "Charge_ICU_Nurse_3D" (
                doc = "Charge ICU Nurse Coordinating Ward Alarms & PTP Sync"
                prepend references = @./Characters/Human_Nurse.usd@
            )
            {
                double3 xformOp:translate = (1.35, -0.75, 0.0)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 145.0)
                float3 xformOp:scale = (0.0096, 0.0096, 0.0096)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
            }

            def Xform "OperatorConsoleDesk"
            {
                double3 xformOp:translate = (0.0, -0.35, 0.0)
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Cube "ConsoleDeskTop" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, 0.0, 0.76)
                    float3 xformOp:scale = (2.80, 0.95, 0.06)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_MatteDark>
                }
                def Cube "ConsolePedestalLeft" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-1.15, 0.0, 0.37)
                    float3 xformOp:scale = (0.18, 0.82, 0.74)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_Aluminum>
                }
                def Cube "ConsolePedestalRight" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (1.15, 0.0, 0.37)
                    float3 xformOp:scale = (0.18, 0.82, 0.74)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_Aluminum>
                }
            }

            def Xform "CurvedTelemetryWall" (
                doc = "4-Panel Curved Clinical & Cyber-Physical Telemetry Wall Monitoring Rooms 1-4"
            )
            {
                double3 xformOp:translate = (0.0, 1.45, 1.55)
                uniform token[] xformOpOrder = ["xformOp:translate"]

                def Cube "Screen_Room01" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-1.35, -0.18, 0.0)
                    float3 xformOp:rotateXYZ = (0.0, 0.0, 14.0)
                    float3 xformOp:scale = (0.85, 0.04, 0.56)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                    custom string geco:monitored_room = "ROOM_01"
                }
                def Cube "Screen_Room02" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-0.45, 0.0, 0.0)
                    float3 xformOp:rotateXYZ = (0.0, 0.0, 5.0)
                    float3 xformOp:scale = (0.85, 0.04, 0.56)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                    custom string geco:monitored_room = "ROOM_02"
                }
                def Cube "Screen_Room03" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.45, 0.0, 0.0)
                    float3 xformOp:rotateXYZ = (0.0, 0.0, -5.0)
                    float3 xformOp:scale = (0.85, 0.04, 0.56)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                    custom string geco:monitored_room = "ROOM_03"
                }
                def Cube "Screen_Room04" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (1.35, -0.18, 0.0)
                    float3 xformOp:rotateXYZ = (0.0, 0.0, -14.0)
                    float3 xformOp:scale = (0.85, 0.04, 0.56)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                    custom string geco:monitored_room = "ROOM_04"
                }
            }

            def Xform "LargeWallDashboardScreen" (
                doc = "Large 3.8m x 2.1m Central Ward Telemetry & Scenario Matrix Dashboard Wall Screen"
            )
            {
                double3 xformOp:translate = (0.0, 2.08, 1.50)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                custom string geco:dashboard_title = "GECO v6 SMART HOSPITAL WARD: 12-CUBICLE SCENARIO MATRIX & BENCHMARK DASHBOARD"
                custom string geco:highlight_1 = "31-Participant EKF Forecast RMSE: 16.82 mg/dL vs 25.77 mg/dL (p < 0.0001)"
                custom string geco:highlight_2 = "Hovorka 8-State RK4 Domain Integrity: 100.0% Across All 20 Fault & Cyber Scenarios"
                custom string geco:highlight_3 = "Physical vs Cyber Root-Cause Separation: 100% Accuracy (0% False Cyber Lockouts)"
                custom string geco:highlight_4 = "Simplex Hardware Pinch-Valve V01 Clamp Latency: < 50 ms on 10U Overdose Replay"

                def Cube "DashboardChassis" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    float3 xformOp:scale = (3.80, 0.06, 2.10)
                    uniform token[] xformOpOrder = ["xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_MatteDark>
                }
                def Cube "DashboardGlassSurface" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, -0.034, 0.0)
                    float3 xformOp:scale = (3.68, 0.01, 1.98)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                }
                def Cube "HeaderStatusStrip" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, -0.042, 0.86)
                    float3 xformOp:scale = (3.56, 0.014, 0.14)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SimplexShield>
                }
                def Cube "KPI_31Participant_RMSE" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-1.32, -0.042, 0.56)
                    float3 xformOp:scale = (0.82, 0.014, 0.32)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_AnodizedBlue>
                }
                def Cube "KPI_Hovorka_Domain" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-0.44, -0.042, 0.56)
                    float3 xformOp:scale = (0.82, 0.014, 0.32)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_BatteryHealthy>
                }
                def Cube "KPI_RootCause_Separation" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.44, -0.042, 0.56)
                    float3 xformOp:scale = (0.82, 0.014, 0.32)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_DebrisAmber>
                }
                def Cube "KPI_Simplex_Clamp" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (1.32, -0.042, 0.56)
                    float3 xformOp:scale = (0.82, 0.014, 0.32)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
                def Cube "Bar_WardMeanBG" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-1.35, -0.045, -0.32)
                    float3 xformOp:scale = (0.34, 0.02, 0.72)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SalineTeal>
                }
                def Cube "Bar_WardTIR" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-0.81, -0.045, -0.25)
                    float3 xformOp:scale = (0.34, 0.02, 0.86)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_BatteryHealthy>
                }
                def Cube "Bar_MaxLinePressure" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (-0.27, -0.045, -0.45)
                    float3 xformOp:scale = (0.34, 0.02, 0.46)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_DebrisAmber>
                }
                def Cube "Bar_MinBatteryV" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.27, -0.045, -0.28)
                    float3 xformOp:scale = (0.34, 0.02, 0.80)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_SafetyOrange>
                }
                def Cube "Bar_MaxCUSUM" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.81, -0.045, -0.52)
                    float3 xformOp:scale = (0.34, 0.02, 0.32)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_CyberRed>
                }
                def Cube "Bar_ActiveAlarms" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (1.35, -0.045, -0.58)
                    float3 xformOp:scale = (0.34, 0.02, 0.22)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_GoldCalibration>
                }
            }

            def Cylinder "MasterAlarmBeacon" (
                prepend apiSchemas = ["MaterialBindingAPI"]
            )
            {
                uniform token axis = "Z"
                double radius = 0.09
                double height = 0.22
                double3 xformOp:translate = (0.0, 1.45, 2.35)
                float3 xformOp:rotateXYZ = (0.0, 0.0, 0.0)
                uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateXYZ"]
                rel material:binding = </World/Looks/Mat_BatteryHealthy>
                custom string geco:ward_alarm_state = "NORMAL"
            }

            def Xform "MasterClock_PTP_Hub" (
                doc = "IEEE-1588v2 Precision Time Protocol Grandmaster Clock & Optical Sync Strobe (Part_A05 / Part_A06)"
            )
            {
                double3 xformOp:translate = (-1.85, 1.10, 0.0)
                uniform token[] xformOpOrder = ["xformOp:translate"]
                custom string geco:grandmaster_id = "IITP-GECOv6-PTP-GM-A05"
                custom string geco:sync_protocol = "IEEE-1588v2_PTP_Plus_Optical_Strobe_10Hz"

                def Cube "Part_A05_Grandmaster_Rack" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, 0.0, 0.95)
                    float3 xformOp:scale = (0.62, 0.58, 1.90)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_MatteDark>
                }
                def Cylinder "Part_A06_Optical_Sync_Strobe" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    uniform token axis = "Z"
                    double radius = 0.11
                    double height = 0.26
                    double3 xformOp:translate = (0.0, 0.0, 2.03)
                    uniform token[] xformOpOrder = ["xformOp:translate"]
                    rel material:binding = </World/Looks/Mat_GoldCalibration>
                }
                def Cube "PTP_Epoch_Display" (
                    prepend apiSchemas = ["MaterialBindingAPI"]
                )
                {
                    double size = 1.0
                    double3 xformOp:translate = (0.0, -0.30, 1.45)
                    float3 xformOp:scale = (0.50, 0.03, 0.28)
                    uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]
                    rel material:binding = </World/Looks/Mat_ScreenTelemetry>
                }
            }""")
    lines.append("        }")
    lines.append("")

    # -----------------------------------------------------------------------
    # ROOMS 07 - 12: Patients P05 through P10 (Complete 10-Patient Cohort)
    # -----------------------------------------------------------------------
    extra_patients = [
        ("Room_07_Wet_Site_Adult_P05", "ROOM_07", "Room 07 — Patient P05 (68kg Adult, Dislodged Wet Cannula Site A2)", (-6.0, 9.0, 0.0), "Patient_05_Adult_68kg", "Bed_05", "Monitor_05", "Pump_05", 68.0, "Human_Nurse.usd", "Bedside_Nurse_3D", False),
        ("Room_08_PISA_Compression_P06", "ROOM_08", "Room 08 — Patient P06 (71kg Adult, PISA Sleep Compression Low A4)", (0.0, 9.0, 0.0), "Patient_06_Adult_71kg", "Bed_06", "Monitor_06", "Pump_06", 71.0, "Human_Doctor.usd", "Bedside_Doctor_3D", False),
        ("Room_09_Clock_Skew_Dawn_P07", "ROOM_09", "Room 09 — Patient P07 (79kg Dawn T1D, +3h RTC Clock-Skew Attack C4)", (6.0, 9.0, 0.0), "Patient_07_Dawn_79kg", "Bed_07", "Monitor_07", "Pump_07", 79.0, "Human_Engineer.usd", "Security_Auditor_3D", True),
        ("Room_10_Stealth_CUSUM_P08", "ROOM_10", "Room 10 — Patient P08 (62kg Sensitive, Stealthy CUSUM Drip C3)", (-6.0, 15.0, 0.0), "Patient_08_Sensitive_62kg", "Bed_08", "Monitor_08", "Pump_08", 62.0, "Human_Doctor.usd", "Bedside_Doctor_3D", False),
        ("Room_11_Brittle_Variable_P09", "ROOM_11", "Room 11 — Patient P09 (55kg Brittle T1D, RF 2x Overdose Replay C1)", (0.0, 15.0, 0.0), "Patient_09_Brittle_55kg", "Bed_09", "Monitor_09", "Pump_09", 55.0, "Human_Nurse.usd", "Bedside_Nurse_3D", True),
        ("Room_12_Unprimed_Line_P10", "ROOM_12", "Room 12 — Patient P10 (73kg Adult, Unprimed 68uL Catheter Deficit A1)", (6.0, 15.0, 0.0), "Patient_10_Adult_73kg", "Bed_10", "Monitor_10", "Pump_10", 73.0, "Human_Doctor.usd", "Bedside_Doctor_3D", False),
    ]
    for r_prim, r_code, r_doc, r_pos, p_prim, b_prim, m_prim, pump_prim, w_kg, st_asset, st_prim, st_second in extra_patients:
        lines.append(f'        def Xform "{r_prim}" (')
        lines.append('            kind = "component"')
        lines.append("        )")
        lines.append("        {")
        lines.append(emit_room_shell("            ", r_code, r_doc, r_pos))
        lines.append(
            emit_patient_and_bed(
                "            ",
                p_prim,
                b_prim,
                m_prim,
                pump_prim,
                r_doc,
                w_kg,
                include_standard_pump=True,
                staff_asset=st_asset,
                staff_prim_name=st_prim,
                include_second_staff=st_second,
            )
        )
        lines.append("        }")
        lines.append("")

    lines.append("    }")
    lines.append("}")

    WARD_USDA_PATH.write_text("\n".join(lines), encoding="utf-8")
    return WARD_USDA_PATH


def main() -> None:
    count, rig_path = generate_metrology_rig_usda()
    ward_path = generate_smart_hospital_ward_usda()
    print(f"[GECO v6 Max USD Builder] Emitted {count} parts -> {rig_path} ({rig_path.stat().st_size:,} bytes)")
    print(f"[GECO v6 Max USD Builder] Emitted 12-Bay (10-Patient + Rig + MasterClock) ward -> {ward_path} ({ward_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
