"""GECO v6.1+ Max Cyber-Physical Digital Twin Package.

Enhances the baseline GECO v6 study and GECO v4 core with:
1. Physiology v6.1 (`physiology_v61.py`):
   - 7-state Second-Order Absorption + Latent Metabolic Flux Velocity EKF (`EnhancedPhysiologyTwinV61`)
   - Regularized interior-point participant calibration (`calibrate_participant_v61`) eliminating boundary pinning
   - Physiologically valid saturating-EGP Hovorka plant (`ValidHovorkaPlant`) & IOB-aware controller (`IOBAwareController`)
2. Multi-Physics Fault Simulation (`multiphysics_faults.py`):
   - Microbore pipe Hagen-Poiseuille fluidics, insulin fibril debris accumulation, air-bubble Boyle's law compliance, cannula kinking, inline back-pressure transducer
   - Li-Ion / Li-SOCl2 electro-thermal battery discharge, internal resistance aging, bolus voltage sag, brownout watchdog, supercapacitor hold-up
   - Stepper motor torque/current vs back-pressure stiction, lead-screw backlash, optical encoder discrepancy, pinch valve mechanics, CGM membrane fouling
3. Security Kernel v6.1 (`security_kernel_v61.py`):
   - Orthogonal 4-channel anomaly detector (Cyber-CGM, Fluidic-Mass/Pressure, Electromechanical/Battery, Cross-Domain Corroboration)
   - Graded Simplex Safety Kernel (Safe-Basal Clamp for cyber attacks, <50ms Pinch-Valve/Relay Cut-Off for physical over-delivery, Occlusion Pressure Relief, Battery Safe-Basal Hold, and 15-min Micro-Pulse Supervised Recovery)
4. Multi-Room Telemetry Server (`ward_telemetry_server.py`):
   - Real-time 6-room smart hospital ICU & 130-part metrology lab WebSocket server (`ws://127.0.0.1:8766`)
"""

from .physiology_v61 import (
    EnhancedTwinParamsV61,
    EnhancedGlucoseModelV61,
    EnhancedPhysiologyTwinV61,
    ValidHovorkaPlant,
    IOBAwareController,
    evaluate_causal_forecasts_v61,
    fit_participant_v61,
    calibrate_participant_v61,
)
from .multiphysics_faults import (
    PipeDebrisAndFluidicsModel,
    BatteryElectroThermalModel,
    ElectromechanicalPumpModel,
    MultiPhysicsPumpRig,
)
from .security_kernel_v61 import (
    OrthogonalDetectorV61,
    SimplexSafetyKernelV61,
    run_v61_intervention_trial,
)
from .permutation_taxonomy import (
    ScenarioSpec,
    REAL_WORLD_PERMUTATION_CATALOG,
    RootCauseAttributionEngineV61,
)

__version__ = "6.1.0-max"
__all__ = [
    "EnhancedTwinParamsV61",
    "EnhancedGlucoseModelV61",
    "EnhancedPhysiologyTwinV61",
    "ValidHovorkaPlant",
    "IOBAwareController",
    "evaluate_causal_forecasts_v61",
    "fit_participant_v61",
    "calibrate_participant_v61",
    "PipeDebrisAndFluidicsModel",
    "BatteryElectroThermalModel",
    "ElectromechanicalPumpModel",
    "MultiPhysicsPumpRig",
    "OrthogonalDetectorV61",
    "SimplexSafetyKernelV61",
    "run_v61_intervention_trial",
    "ScenarioSpec",
    "REAL_WORLD_PERMUTATION_CATALOG",
    "RootCauseAttributionEngineV61",
]
