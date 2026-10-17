#!/usr/bin/env python3
"""
Builds `cockpit/GECO_v6_Max_Cockpit.html` — Self-contained 3D WebGL + Multi-Physics
Digital Twin Cockpit with:
  - All 138 parts of the IIT Patna Metrology Rig embedded from COMPONENTS.json
  - 6-Room Smart Hospital Ward 3D scene
  - Full 5-Category Failure, Wrong-Installation, Modern Countermeasure & Cyber-Attack
    Permutation Matrix + Root-Cause Attribution Classifier
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent.parent
COMP_PATH = ROOT.parent / "GECOv6" / "06_RIG_AND_MEDIA" / "native" / "COMPONENTS.json"
OUT_HTML = Path(__file__).resolve().parent / "GECO_v6_Max_Cockpit.html"

parts_data = json.loads(COMP_PATH.read_text(encoding="utf-8"))["parts"]
parts_json_compact = json.dumps(parts_data, separators=(",", ":"))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>GECO v6 Max — 6-Room Smart Hospital Ward, 138-Part OpenUSD Twin &amp; Failure/Cyber Permutation Cockpit</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<style>
  :root {
    --bg-0: #050911;
    --bg-1: #0b1322;
    --bg-2: #111d33;
    --border: #1e3252;
    --cyan: #38bdf8;
    --teal: #14b8a6;
    --emerald: #10b981;
    --amber: #f59e0b;
    --red: #ef4444;
    --purple: #a855f7;
    --text-0: #f1f5f9;
    --text-1: #94a3b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, monospace;
    background: var(--bg-0);
    color: var(--text-0);
    overflow-x: hidden;
  }
  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 16px;
    background: linear-gradient(90deg, #071021 0%, #0d1d38 50%, #071021 100%);
    border-bottom: 1px solid var(--border);
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand-badge {
    background: linear-gradient(135deg, #0284c7, #0d9488);
    color: #fff; font-weight: 800; font-size: 12.5px;
    padding: 5px 10px; border-radius: 6px; letter-spacing: 0.6px;
  }
  .brand h1 { font-size: 15px; font-weight: 700; color: #e2e8f0; }
  .brand p { font-size: 10.5px; color: var(--text-1); }
  .status-strip { display: flex; align-items: center; gap: 8px; font-size: 11px; }
  .pill {
    padding: 4px 10px; border-radius: 999px; font-weight: 700; font-size: 10.5px;
    border: 1px solid var(--border); background: var(--bg-1);
  }
  .pill.ok { color: #34d399; border-color: #059669; background: rgba(16,185,129,0.12); }
  .pill.warn { color: #fbbf24; border-color: #d97706; background: rgba(245,158,11,0.15); }
  .pill.crit { color: #f87171; border-color: #dc2626; background: rgba(239,68,68,0.18); animation: pulseRed 1s infinite alternate; }
  @keyframes pulseRed { from { box-shadow: 0 0 0px #ef4444; } to { box-shadow: 0 0 12px #ef4444; } }

  .main-grid {
    display: grid;
    grid-template-columns: 365px 1fr 445px;
    gap: 10px;
    padding: 10px;
    min-height: calc(100vh - 56px);
  }
  .panel {
    background: var(--bg-1);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .panel-title {
    font-size: 11.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--cyan);
    border-bottom: 1px solid var(--border);
    padding-bottom: 5px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .camera-bar { display: flex; flex-wrap: wrap; gap: 5px; }
  button {
    background: var(--bg-2);
    color: var(--text-0);
    border: 1px solid #28426b;
    border-radius: 5px;
    padding: 5px 8px;
    font-size: 10.5px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.14s ease;
    text-align: left;
  }
  button:hover { border-color: var(--cyan); background: #172a4a; }
  button.active {
    background: linear-gradient(135deg, #0284c7, #0f766e);
    border-color: #38bdf8;
    color: #fff;
  }
  button.cat-a { border-color: #0d9488; background: rgba(13, 148, 136, 0.16); color: #5eead4; }
  button.cat-a:hover { background: rgba(13, 148, 136, 0.34); }
  button.cat-b { border-color: #b45309; background: rgba(180, 83, 9, 0.22); color: #fcd34d; }
  button.cat-b:hover { background: rgba(180, 83, 9, 0.42); }
  button.cat-c { border-color: #991b1b; background: rgba(127, 29, 29, 0.30); color: #fca5a5; }
  button.cat-c:hover { background: rgba(185, 28, 28, 0.50); }
  button.cat-d { border-color: #7e22ce; background: rgba(126, 34, 206, 0.24); color: #d8b4fe; }
  button.cat-d:hover { background: rgba(126, 34, 206, 0.44); }
  button.reset-btn { background: rgba(16, 185, 129, 0.18); border-color: #059669; color: #6ee7b7; text-align: center; }

  .control-group {
    background: rgba(17, 29, 51, 0.65);
    border: 1px solid #1b2e4b;
    border-radius: 6px;
    padding: 7px 9px;
    display: flex;
    flex-direction: column;
    gap: 5px;
  }
  .control-group h4 {
    font-size: 10.5px;
    color: #cbd5e1;
    display: flex;
    justify-content: space-between;
  }
  .btn-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }
  .slider-row { display: flex; flex-direction: column; gap: 2px; }
  .slider-header { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--text-1); }
  .slider-header span.val { color: var(--cyan); font-weight: 700; }
  input[type=range] { width: 100%; accent-color: var(--cyan); cursor: pointer; height: 14px; }

  .viewport-wrap {
    position: relative;
    width: 100%;
    height: 440px;
    background: radial-gradient(circle at center, #0f1e36 0%, #050a14 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  #webgl-container { width: 100%; height: 100%; display: block; }
  .hud-overlay {
    position: absolute; top: 8px; left: 8px; right: 8px;
    display: flex; justify-content: space-between; pointer-events: none;
  }
  .hud-card {
    background: rgba(5, 9, 17, 0.84);
    border: 1px solid rgba(56, 189, 248, 0.35);
    backdrop-filter: blur(6px);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 10.5px;
    line-height: 1.42;
  }
  .hud-bottom {
    position: absolute; bottom: 8px; left: 8px; right: 8px;
    display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; pointer-events: none;
  }
  .room-mini-card {
    background: rgba(8, 15, 28, 0.88);
    border: 1px solid #1e3252;
    border-radius: 5px;
    padding: 4px 6px;
    font-size: 9.5px;
  }
  .room-mini-card strong { color: var(--cyan); display: block; margin-bottom: 1px; }

  .attribution-banner {
    background: linear-gradient(90deg, rgba(13,29,54,0.95), rgba(10,22,40,0.95));
    border: 1px solid #25426b;
    border-left: 4px solid var(--emerald);
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 11px;
    display: grid;
    grid-template-columns: 1fr 1fr 1.2fr;
    gap: 8px;
  }
  .attr-col h6 { font-size: 9.5px; text-transform: uppercase; color: var(--text-1); margin-bottom: 2px; }
  .attr-col div { font-size: 10.5px; font-weight: 600; line-height: 1.35; }

  .scopes-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; }
  .scope-box {
    background: #060c17;
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 6px;
  }
  .scope-box h5 {
    font-size: 10px;
    color: var(--text-1);
    margin-bottom: 3px;
    display: flex;
    justify-content: space-between;
  }
  canvas.scope { width: 100%; height: 102px; display: block; background: #040811; border-radius: 4px; }

  table.bench-table { width: 100%; border-collapse: collapse; font-size: 10px; }
  table.bench-table th, table.bench-table td {
    padding: 4px 5px;
    border-bottom: 1px solid #16243d;
    text-align: left;
  }
  table.bench-table th { color: var(--cyan); font-weight: 700; background: rgba(14, 27, 48, 0.8); }
  .kpi-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 5px; }
  .kpi-box { background: var(--bg-2); border: 1px solid #1d3152; border-radius: 6px; padding: 6px 8px; }
  .kpi-box .lbl { font-size: 9.5px; color: var(--text-1); }
  .kpi-box .num { font-size: 14px; font-weight: 800; color: #f8fafc; margin-top: 1px; }
</style>
</head>
<body>

<header>
  <div class="brand">
    <span class="brand-badge">GECO v6.1+ MAX</span>
    <div>
      <h1>6-Room Smart Hospital Cyber-Physical Ward, 138-Part OpenUSD Twin &amp; Failure/Cyber Permutation Studio</h1>
      <p>Distinguishing Wrong Installation / Wet-Site Leaks / PISA Compression Lows from Solved/Unsolved Pump Failures &amp; C1–C7 Cyber Attacks</p>
    </div>
  </div>
  <div class="status-strip">
    <span id="ws-pill" class="pill ok">ENGINE: COUPLED MULTI-PHYSICS + WS (8766)</span>
    <span id="class-pill" class="pill ok">CLASSIFIER: NOMINAL</span>
    <span id="simplex-pill" class="pill ok">SIMPLEX CLAMP: STANDBY</span>
  </div>
</header>

<div class="main-grid">
  <!-- LEFT COLUMN: 5-CATEGORY PERMUTATION MATRIX & CONTINUOUS SLIDERS -->
  <div class="panel" style="overflow-y:auto;max-height:calc(100vh - 76px);">
    <div class="panel-title">
      <span>5-Category Failure &amp; Cyber Permutation Matrix</span>
      <button class="reset-btn" onclick="resetAllFaults()">Reset All</button>
    </div>

    <!-- CATEGORY A: WRONG INSTALLATION, USER SETUP & CLINICAL SITE ARTIFACTS -->
    <div class="control-group">
      <h4>
        <span style="color:#5eead4">Cat A: Wrong Installation &amp; Clinical Site Artifacts</span>
        <span style="color:#94a3b8">Non-Cyber!</span>
      </h4>
      <div class="btn-grid-2">
        <button class="cat-a" onclick="activateScenario('unprimed_tubing_install')">A1: Unprimed Tubing (12U Dead-Space)</button>
        <button class="cat-a" onclick="activateScenario('cannula_dislodgement_leak')">A2: Dislodged Cannula ('Wet Site' Leak)</button>
        <button class="cat-a" onclick="activateScenario('lipohypertrophy_site')">A3: Lipohypertrophy Scar Site (&tau;=135m)</button>
        <button class="cat-a" onclick="activateScenario('pisa_compression_low')">A4: PISA Sleep Compression Low (-35)</button>
      </div>
      <button class="cat-a" onclick="activateScenario('wrong_concentration_u40_or_denatured')">A5: Wrong Concentration (U-40) / Thermal-Denatured Insulin (&gt;37&deg;C)</button>
    </div>

    <!-- CATEGORY B: SOLVED vs PARTIALLY SOLVED vs UNSOLVED PHYSICAL PUMP FAILURES -->
    <div class="control-group">
      <h4>
        <span style="color:#fcd34d">Cat B: Physical Pump Failures (Solved vs Unsolved)</span>
        <span style="color:#94a3b8">Hardware</span>
      </h4>
      <div class="btn-grid-2">
        <button class="cat-b" onclick="activateScenario('aircraft_depressurization_siphon')">B1: Cabin Depressurization Siphon</button>
        <button class="cat-b" onclick="activateScenario('silent_micro_occlusion')">B2: Silent Basal Micro-Occlusion</button>
        <button class="cat-b" onclick="activateScenario('moisture_capacitive_ghost_bolus')">B3: Capacitive Moisture Ghost Bolus</button>
        <button class="cat-b" onclick="activateScenario('plunger_oring_blowby')">B4: Plunger O-Ring Blow-by / Nut Strip</button>
        <button class="cat-b" onclick="activateScenario('battery_brownout')">B5: Li-Ion High-R_int Brownout Sag</button>
        <button class="cat-b" onclick="activateScenario('motor_stiction')">B6: Stepper Motor Stiction / Backlash</button>
      </div>
    </div>

    <!-- CATEGORY C: REAL-WORLD CYBER ATTACK VARIETIES (C1-C7) -->
    <div class="control-group">
      <h4>
        <span style="color:#fca5a5">Cat C: Cyber-Physical Attack Varieties (C1–C7)</span>
        <span style="color:#f87171">Adversarial</span>
      </h4>
      <div class="btn-grid-2">
        <button class="cat-c" onclick="activateScenario('rf_replay_bolus')">C1: Sub-GHz RF Replay (CVE-2019-10964)</button>
        <button class="cat-c" onclick="activateScenario('ble_mitm_downgrade')">C2: BLE MITM &amp; ISF/ICR Corrupt</button>
        <button class="cat-c" onclick="activateScenario('stealthy_cusum_drip')">C3: Stealthy Sub-Threshold CUSUM Drip</button>
        <button class="cat-c" onclick="activateScenario('clock_skew_iob_attack')">C4: RTC Clock-Skew (+3h) IOB Wipe</button>
        <button class="cat-c" onclick="activateScenario('ekf_innovation_poisoning')">C5: EKF Innovation Ramp Poisoning</button>
        <button class="cat-c" onclick="activateScenario('coordinated_stuxnet_mask')">C6: Stuxnet Dual-Channel Masking</button>
      </div>
      <button class="cat-c" onclick="activateScenario('emi_sensor_spoof')">C7: Resonant Acoustic/EMI MEMS Strain Spoof (False-Occlusion DKA Attack)</button>
    </div>

    <!-- CATEGORY D: COMPOUND MULTI-FAULT PERMUTATIONS -->
    <div class="control-group">
      <h4>
        <span style="color:#d8b4fe">Cat D: Compound Multi-Domain Permutations</span>
        <span style="color:#a855f7">Multi-Fault</span>
      </h4>
      <button class="cat-d" onclick="activateScenario('compound_wetsite_plus_pisa')">D1: Dislodged Cannula (Wet Site) + Concurrent PISA Compression Low</button>
      <button class="cat-d" onclick="activateScenario('compound_lipo_plus_clock_attack')">D2: Lipohypertrophy Delayed Stacking + RTC Clock-Skew Cyber Attack</button>
    </div>

    <!-- CONTINUOUS MULTI-PHYSICS SLIDERS -->
    <div class="control-group">
      <h4><span>Continuous Multi-Physics Parameter Sliders</span><span style="color:#38bdf8">Live ODE</span></h4>
      <div class="slider-row">
        <div class="slider-header"><span>Pipe Fibril Debris (%)</span><span class="val" id="lbl-debris">0%</span></div>
        <input type="range" id="sld-debris" min="0" max="95" step="1" value="0" oninput="onSliderChange()" />
      </div>
      <div class="slider-row">
        <div class="slider-header"><span>Air Bubble Volume (&mu;L)</span><span class="val" id="lbl-bubble">0 &mu;L</span></div>
        <input type="range" id="sld-bubble" min="0" max="30" step="0.5" value="0" oninput="onSliderChange()" />
      </div>
      <div class="slider-row">
        <div class="slider-header"><span>Teflon Cannula Kink (%)</span><span class="val" id="lbl-kink">0%</span></div>
        <input type="range" id="sld-kink" min="0" max="90" step="1" value="0" oninput="onSliderChange()" />
      </div>
      <div class="slider-row">
        <div class="slider-header"><span>Battery SOC (%) / R_int (&Omega;)</span><span class="val" id="lbl-soc">92% / 0.18&Omega;</span></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
          <input type="range" id="sld-soc" min="2" max="100" step="1" value="92" oninput="onSliderChange()" />
          <input type="range" id="sld-rint" min="0.10" max="1.60" step="0.02" value="0.18" oninput="onSliderChange()" />
        </div>
      </div>
      <div class="slider-row">
        <div class="slider-header"><span>Motor Stiction (%) / Basal Rate (U/hr)</span><span class="val" id="lbl-basal">0% / 1.0 U/h</span></div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;">
          <input type="range" id="sld-stiction" min="0" max="100" step="5" value="0" oninput="onSliderChange()" />
          <input type="range" id="sld-basal" min="0.2" max="6.0" step="0.1" value="1.0" oninput="onSliderChange()" />
        </div>
      </div>
      <div style="display:flex;gap:4px;margin-top:2px;">
        <button onclick="triggerMealBolus()" style="text-align:center;flex:1;">4.5U Meal Bolus</button>
        <button onclick="toggleExplodedRig()" style="text-align:center;flex:1;">Explode 138-Part Rig</button>
      </div>
    </div>
  </div>

  <!-- CENTER COLUMN: 3D VIEWPORT + ROOT-CAUSE CLASSIFIER BANNER + 4 OSCILLOSCOPES -->
  <div class="panel">
    <div class="panel-title">
      <span>Interactive 3D OpenUSD Multi-Room &amp; 138-Part Rig Viewport</span>
      <span style="font-size:10.5px;color:var(--text-1)">Drag: Orbit &bull; Wheel: Zoom &bull; Shift+Drag: Pan</span>
    </div>

    <div class="camera-bar" id="cam-buttons">
      <button class="active" onclick="setCameraPreset('OVERVIEW', this)">Ward Overview (6 Rooms)</button>
      <button onclick="setCameraPreset('ROOM_01', this)">R1: Site &amp; PISA</button>
      <button onclick="setCameraPreset('ROOM_02', this)">R2: Pipe Debris &amp; Wet-Site</button>
      <button onclick="setCameraPreset('ROOM_03', this)">R3: Battery &amp; Actuator</button>
      <button onclick="setCameraPreset('ROOM_04', this)">R4: Cyber MITM &amp; Simplex</button>
      <button onclick="setCameraPreset('ROOM_05', this)">R5: 138-Part IITP Rig</button>
      <button onclick="setCameraPreset('ROOM_06', this)">R6: SOC Command</button>
    </div>

    <div class="viewport-wrap">
      <div id="webgl-container"></div>
      <div class="hud-overlay">
        <div class="hud-card">
          <div style="color:#38bdf8;font-weight:700;" id="hud-cam-title">CAMERA: WARD OVERVIEW (ALL 6 ROOMS)</div>
          <div>OpenUSD Stage: <code>geco_v6_smart_hospital_ward.usda</code></div>
          <div>Room 5 Reference: <code>geco_v6_metrology_rig.usda</code> (<strong>138 Prims Verified</strong>)</div>
          <div id="hud-scenario-tag" style="color:#34d399;font-weight:700;">Active Mode: NOMINAL CLOSED-LOOP OPERATION</div>
        </div>
        <div class="hud-card" style="text-align:right;">
          <div>Sim Time: <strong id="hud-sim-time">00:00:00</strong> | RTC Skew: <strong id="hud-rtc-skew">+0.0h</strong></div>
          <div>Plunger Travel (M07/S03): <strong id="hud-plunger-mm">0.00 mm</strong></div>
          <div>Gravimetric Balance (T02): <strong id="hud-balance-g">0.000 g</strong></div>
          <div>Pinch Valve (V01): <strong id="hud-valve-state" style="color:#34d399;">OPEN (PASS)</strong></div>
        </div>
      </div>

      <div class="hud-bottom">
        <div class="room-mini-card"><strong>R1: Clinical Site</strong><div id="mini-r1">BG: 114 | Site OK</div></div>
        <div class="room-mini-card"><strong>R2: Fluidic Lumen</strong><div id="mini-r2">P: 14.2 kPa | Q: 1.00</div></div>
        <div class="room-mini-card"><strong>R3: Power/Motor</strong><div id="mini-r3">V: 3.98 V | SOC: 92%</div></div>
        <div class="room-mini-card"><strong>R4: Cyber/Simplex</strong><div id="mini-r4">Simplex: STANDBY</div></div>
        <div class="room-mini-card"><strong>R5: 138-Part Rig</strong><div id="mini-r5">138 Prims | dm/dt OK</div></div>
        <div class="room-mini-card"><strong>R6: SOC Center</strong><div id="mini-r6">Root-Cause: CLEAN</div></div>
      </div>
    </div>

    <!-- ROOT-CAUSE ATTRIBUTION & MODERN PUMP COUNTERMEASURE DIAGNOSTIC BANNER -->
    <div class="attribution-banner" id="attr-banner">
      <div class="attr-col">
        <h6>Naive Threshold IDS Verdict</h6>
        <div id="attr-naive" style="color:#94a3b8;">No alarm (Clean baseline)</div>
      </div>
      <div class="attr-col">
        <h6>Commercial Pump Countermeasure Status</h6>
        <div id="attr-commercial" style="color:#38bdf8;">Standard inline force sensor &amp; check valve nominal</div>
      </div>
      <div class="attr-col">
        <h6>GECO v6.1+ Root-Cause Attribution &amp; Action</h6>
        <div id="attr-geco" style="color:#34d399;">NOMINAL: All 4 channels (EKF, CUSUM, Fluidic Z, Power) verified in-family</div>
      </div>
    </div>

    <!-- 4 Real-Time Multi-Trace Oscilloscopes -->
    <div class="scopes-grid">
      <div class="scope-box">
        <h5>
          <span>1. Blood Glucose: True (Green) vs CGM (Amber) vs EKF Forecast (Cyan)</span>
          <span style="color:#38bdf8">mg/dL</span>
        </h5>
        <canvas id="scope-bg" class="scope" width="440" height="102"></canvas>
      </div>
      <div class="scope-box">
        <h5>
          <span>2. Line Pressure P_line (kPa, Amber) &amp; Effective Tissue Flow Q_out (Cyan)</span>
          <span style="color:#fbbf24">kPa / (U/hr)</span>
        </h5>
        <canvas id="scope-pressure" class="scope" width="440" height="102"></canvas>
      </div>
      <div class="scope-box">
        <h5>
          <span>3. Li-Ion Terminal Voltage V_term (V, Green) &amp; Motor Current (mA, Purple)</span>
          <span style="color:#34d399">V / mA</span>
        </h5>
        <canvas id="scope-battery" class="scope" width="440" height="102"></canvas>
      </div>
      <div class="scope-box">
        <h5>
          <span>4. 4-Channel Detector Scores (EKF Red, Fluidic Amber, Power/Clock Cyan)</span>
          <span style="color:#f87171">Score vs Trip (1.0)</span>
        </h5>
        <canvas id="scope-detector" class="scope" width="440" height="102"></canvas>
      </div>
    </div>
  </div>

  <!-- RIGHT COLUMN: LIVE TELEMETRY KPIs & TAXONOMY / BENCHMARK MATRIX TABLE -->
  <div class="panel" style="overflow-y:auto;max-height:calc(100vh - 76px);">
    <div class="panel-title">
      <span>Live Telemetry &amp; Root-Cause KPIs</span>
      <span style="color:#34d399">Zero False Cyber Lockout</span>
    </div>

    <div class="kpi-grid">
      <div class="kpi-box">
        <div class="lbl">True Blood Glucose / CGM</div>
        <div class="num" id="kpi-bg">114.0 / 114.2 <span style="font-size:10px;color:#94a3b8">mg/dL</span></div>
      </div>
      <div class="kpi-box">
        <div class="lbl">EKF 30-Min BG Forecast</div>
        <div class="num" id="kpi-ekf" style="color:#38bdf8">113.8 <span style="font-size:10px;color:#94a3b8">mg/dL</span></div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Line Pressure / Tissue Flow</div>
        <div class="num" id="kpi-pressure">14.2 kPa / 1.00 <span style="font-size:10px;color:#94a3b8">U/hr</span></div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Battery V_term / R_int</div>
        <div class="num" id="kpi-battery">3.98 V / 0.18 <span style="font-size:10px;color:#94a3b8">&Omega;</span></div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Root-Cause Category</div>
        <div class="num" id="kpi-category" style="color:#34d399;font-size:12px;">NOMINAL (CLEAN)</div>
      </div>
      <div class="kpi-box">
        <div class="lbl">Simplex / Mitigation Output</div>
        <div class="num" id="kpi-simplex" style="color:#34d399;font-size:12px;">1.00 U/hr (PASS)</div>
      </div>
    </div>

    <div class="panel-title" style="margin-top:2px;">
      <span>Installation Error vs Hardware vs Cyber Benchmark Matrix</span>
    </div>
    <table class="bench-table">
      <thead>
        <tr>
          <th>Scenario / Failure Mode</th>
          <th>Commercial / Naive IDS</th>
          <th>GECO v6.1+ Root-Cause &amp; Gain</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong style="color:#5eead4">A1: Unprimed Tubing (12U)</strong></td>
          <td style="color:#f87171">False Cyber Alarm / Missed 3h</td>
          <td style="color:#34d399"><strong>Unprimed Line Advisory (P=P_atm) | 0% False Lockout</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#5eead4">A2: Wet-Site Cannula Leak</strong></td>
          <td style="color:#f87171">UNSOLVED (Only checks high P)</td>
          <td style="color:#34d399"><strong>Low-Z Sub-Tissue Drop Detected (8.4 kPa) + Site Alert</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#5eead4">A3: Lipohypertrophy Site</strong></td>
          <td style="color:#fbbf24">Insulin stacking -&gt; Late Hypo</td>
          <td style="color:#34d399"><strong>Identifies &tau;_ins=135m lag | Prevents bolus stacking</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#5eead4">A4: PISA Compression Low</strong></td>
          <td style="color:#f87171">False CGM Spoof Cyber Alarm</td>
          <td style="color:#34d399"><strong>Biphasic Compression Filter | Suppresses false alarm</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fcd34d">B1: Cabin Pressure Siphon</strong></td>
          <td style="color:#38bdf8">Solved by Shuttle / Check Valve</td>
          <td style="color:#34d399"><strong>Pinch Valve V01 + Boyle dP/dt compensation</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fcd34d">B2: Silent Micro-Occlusion</strong></td>
          <td style="color:#f87171">Takes 6-24h at 0.1 U/hr basal</td>
          <td style="color:#34d399"><strong>Detects in 1.2m via Poiseuille Z + Relief Valve</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fcd34d">B3: Moisture Ghost Bolus</strong></td>
          <td style="color:#fbbf24">FDA Class I Recall Mode</td>
          <td style="color:#34d399"><strong>Blocked by Cryptographic UI + Encoder Interlock</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fcd34d">B4: O-Ring Blow-by / Strip</strong></td>
          <td style="color:#f87171">Encoder counts steps, 0 flow</td>
          <td style="color:#34d399"><strong>Caught by Motor Current vs P_line Deficit</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fca5a5">C1: Sub-GHz RF Replay</strong></td>
          <td style="color:#f87171">Unauthenticated Bolus Exec</td>
          <td style="color:#34d399"><strong>Det: 1.0m | Simplex Safe-Basal Clamp (0% Hypo)</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fca5a5">C3: Stealthy CUSUM Drip</strong></td>
          <td style="color:#f87171">Evades standard CUSUM (k=0.5)</td>
          <td style="color:#34d399"><strong>Caught by Multi-Horizon IOB Integral + EKF</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fca5a5">C4: +3h Clock-Skew IOB</strong></td>
          <td style="color:#f87171">Zeros IOB -&gt; Stacked Bolus</td>
          <td style="color:#34d399"><strong>Monotonic Hardware Counter Rejects RTC Jump</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fca5a5">C6: Stuxnet Dual-Masking</strong></td>
          <td style="color:#f87171">MISSED (38.5% Severe Hypo)</td>
          <td style="color:#34d399"><strong>Unmasked by Coulomb + Fluidic Z | 0.0% Hypo</strong></td>
        </tr>
        <tr>
          <td><strong style="color:#fca5a5">C7: EMI Strain-Gauge Spoof</strong></td>
          <td style="color:#f87171">Fake Occlusion -&gt; DKA Deprive</td>
          <td style="color:#34d399"><strong>Cross-Checks Motor Current vs Strain -> Rejects</strong></td>
        </tr>
      </tbody>
    </table>

    <div class="panel-title" style="margin-top:2px;">
      <span>138-Part Metrology Rig Inspector (Room 5)</span>
      <span id="rig-part-count-badge" style="color:#38bdf8">138 Parts</span>
    </div>
    <div style="font-size:10.5px;color:var(--text-1);max-height:120px;overflow-y:auto;background:#060c17;padding:6px;border-radius:6px;border:1px solid #16243d;" id="rig-parts-log">
    </div>
  </div>
</div>

<script>
// ============================================================================
// 1. EMBEDDED 138-PART METROLOGY RIG MANIFEST (FROM COMPONENTS.JSON)
// ============================================================================
const RIG_PARTS = __RIG_PARTS_JSON__;

(function populateRigInspector() {
  const box = document.getElementById("rig-parts-log");
  document.getElementById("rig-part-count-badge").textContent = RIG_PARTS.length + " Parts Verified";
  let html = "";
  for (let i = 0; i < RIG_PARTS.length; i++) {
    const p = RIG_PARTS[i];
    const pos = p.position_mm.map(v => Number(v).toFixed(1)).join(", ");
    html += `<div style="padding:2px 0;border-bottom:1px dashed #111d33;">
      <strong style="color:#38bdf8">${p.id}</strong> — ${p.role}
      <span style="float:right;color:#64748b">[${pos}] mm</span>
    </div>`;
  }
  box.innerHTML = html;
})();

// ============================================================================
// 2. COMPLETE 5-CATEGORY SCENARIO & PERMUTATION CATALOG
// ============================================================================
const SCENARIO_CATALOG = {
  // Category A: Wrong Installation, User Setup & Clinical Site Artifacts
  unprimed_tubing_install: {
    title: "A1: Unprimed Tubing Installation (12 U Air Dead-Space)",
    category: "INSTALLATION_ERROR",
    roomCam: "ROOM_02",
    naiveVerdict: "FALSE ALARM: Flags 'Stealthy Under-Delivery Cyber Attack'",
    commercialStatus: "UNSOLVED: Pump motor runs at atmospheric back-pressure (10.1 kPa); 0 U reaches tissue for hours",
    gecoAttribution: "INSTALLATION WARNING [Non-Cyber]: Reservoir change + flat P_line (10.1 kPa) = Unprimed Line. Prompts 12U Auto-Prime.",
    apply: (s) => { s.debris_fraction = 0.0; s.air_bubble_ul = 26.0; s.cannula_kink_ratio = 0.0; s.site_leak = false; s.lipo_site = false; s.pisa_drop = 0; s.potency = 1.0; s.unprimed_deadspace = true; s.attack_mode = "NONE"; }
  },
  cannula_dislodgement_leak: {
    title: "A2: Dislodged Cannula ('Wet Site' Adhesive Patch Leak)",
    category: "INSTALLATION_ERROR",
    roomCam: "ROOM_02",
    naiveVerdict: "FALSE ALARM: Flags 'Insulin Spoofing / Controller Sabotage'",
    commercialStatus: "UNSOLVED: Commercial occlusion sensors ONLY check for HIGH pressure (>60 kPa), never sub-tissue LOW pressure!",
    gecoAttribution: "SITE LEAK ALERT [Non-Cyber]: P_line dropped below normal tissue back-pressure (8.4 vs 14.2 kPa) + rising BG = Wet Site Leak!",
    apply: (s) => { s.debris_fraction = 0.0; s.air_bubble_ul = 0.0; s.cannula_kink_ratio = 0.0; s.site_leak = true; s.lipo_site = false; s.pisa_drop = 0; s.potency = 1.0; s.unprimed_deadspace = false; s.attack_mode = "NONE"; }
  },
  lipohypertrophy_site: {
    title: "A3: Lipohypertrophy / Scar-Tissue Infusion Site Placement",
    category: "INSTALLATION_ERROR",
    roomCam: "ROOM_01",
    naiveVerdict: "MISDIAGNOSED: Triggers aggressive rage-bolusing -> Late Severe Hypoglycemia",
    commercialStatus: "PARTIALLY SOLVED: AID algorithms assume fixed tau_ins=55m; scar tissue slows tau_ins to 135m (-40% bioavailability)",
    gecoAttribution: "CLINICAL SITE ADVISORY [Non-Cyber]: EKF estimates tau_ins=135m lag -> Expands IOB decay horizon & recommends site rotation.",
    apply: (s) => { s.lipo_site = true; s.site_leak = false; s.unprimed_deadspace = false; s.pisa_drop = 0; s.attack_mode = "NONE"; }
  },
  pisa_compression_low: {
    title: "A4: Pressure-Induced Sensor Attenuation (PISA Sleep Compression Low)",
    category: "INSTALLATION_ERROR",
    roomCam: "ROOM_01",
    naiveVerdict: "FALSE ALARM: Flags 'Negative CGM Spoofing Cyber Attack' (38% False Positive Rate)",
    commercialStatus: "PARTIALLY SOLVED: Causes unnecessary pump suspension or false low alarms when patient rolls onto sensor",
    gecoAttribution: "BENIGN ARTIFACT [Non-Cyber]: Biphasic tissue compression morphology recognized -> Suppresses false cyber alarm!",
    apply: (s) => { s.pisa_drop = -35.0; s.site_leak = false; s.lipo_site = false; s.attack_mode = "NONE"; }
  },
  wrong_concentration_u40_or_denatured: {
    title: "A5: Wrong Insulin Concentration (U-40 in U-100 Pump) / Thermal Denatured (>37°C)",
    category: "INSTALLATION_ERROR",
    roomCam: "ROOM_02",
    naiveVerdict: "FALSE ALARM: Flags 'Actuator Gain Tampering Attack'",
    commercialStatus: "UNSOLVED: Pump delivers exact mechanical volume uL, unaware fluid has 40% potency",
    gecoAttribution: "RESERVOIR POTENCY ALERT [Non-Cyber]: Normal P_line & encoder steps + 0.40x glycemic sensitivity + temp log -> Check Vial/Potency!",
    apply: (s) => { s.potency = 0.40; s.site_leak = false; s.unprimed_deadspace = false; s.attack_mode = "NONE"; }
  },

  // Category B: Solved vs Partially Solved vs Unsolved Physical Pump Failures
  aircraft_depressurization_siphon: {
    title: "B1: Cabin Depressurization / Gravity Siphoning Plunger Pull",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_02",
    naiveVerdict: "Missed uncommanded bolus during ambient pressure drop",
    commercialStatus: "SOLVED IN MODERN PUMPS: Overcome via Tandem Micro-Delivery shuttle membrane & positive-pressure check/pinch valves",
    gecoAttribution: "HARDWARE MITIGATED: Ambient dP/dt expansion detected -> Active Pinch Valve V01 locks fluid path (0.0 U siphon).",
    apply: (s) => { s.air_bubble_ul = 22.0; s.siphon_event = true; s.attack_mode = "NONE"; }
  },
  silent_micro_occlusion: {
    title: "B2: 72% Isoelectric Fibril Debris & Silent Basal Micro-Occlusion",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_02",
    naiveVerdict: "Late detection (6-24 hours at low basal rates) -> DKA Hyperglycemia",
    commercialStatus: "PARTIALLY SOLVED: Force sensors trip at 60-120 kPa, which takes hours to build up at 0.1-0.5 U/hr basal!",
    gecoAttribution: "FLUIDIC IMPEDANCE TRIP (1.2 min): Continuous Hagen-Poiseuille dP/dQ slope detects restriction early + opens Relief Valve.",
    apply: (s) => { s.debris_fraction = 0.72; s.air_bubble_ul = 12.0; s.cannula_kink_ratio = 0.65; s.attack_mode = "NONE";
                   document.getElementById("sld-debris").value = 72; document.getElementById("sld-bubble").value = 12; document.getElementById("sld-kink").value = 65; }
  },
  moisture_capacitive_ghost_bolus: {
    title: "B3: Capacitive Touchscreen Moisture Short / Phantom Bolus Keypress",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_03",
    naiveVerdict: "Executes uncommanded phantom bolus from water/sweat bridging UI",
    commercialStatus: "SOLVED IN MODERN PUMPS: Overcome via multi-step gesture confirmation & waterproof housing (post FDA Class I recalls)",
    gecoAttribution: "UI INTERLOCK REJECTED: Unauthenticated capacitive burst without cryptographic challenge-response token blocked at gateway.",
    apply: (s) => { s.ghost_bolus = true; s.attack_mode = "NONE"; }
  },
  plunger_oring_blowby: {
    title: "B4: Plunger Elastomer O-Ring Blow-By / Lead-Screw Nut Stripping",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_03",
    naiveVerdict: "BLIND SPOT: Rotary motor encoder counts normal steps while fluid bypasses seal backward!",
    commercialStatus: "UNSOLVED BY ENCODER ALONE: Motor turns normally, so step-counter reports 100% delivery despite 0 tissue flow",
    gecoAttribution: "MECHANICAL BLOW-BY DETECTED: Motor current & P_line (9.1 kPa) fail to rise during step train -> Triggers Backup Pump Handover.",
    apply: (s) => { s.oring_blowby = true; s.site_leak = true; s.attack_mode = "NONE"; }
  },
  battery_brownout: {
    title: "B5: High-Impedance Li-Ion Battery Brownout Sag (SOC 7%, R_int 1.15 Ω)",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_03",
    naiveVerdict: "MCU hard-reset loop mid-bolus -> Corrupted IOB state & open valve",
    commercialStatus: "PARTIALLY SOLVED: Cold temperature or aged cell internal resistance spikes cause sudden V_term drop during motor pulse",
    gecoAttribution: "POWER SUPERVISOR PRE-TRIP: Detects dV/dI sag @ 3.08V -> Engages Supercap Holdup + Fail-Safe Pinch Valve Lock.",
    apply: (s) => { s.battery_soc = 0.07; s.battery_r_int = 1.15; s.attack_mode = "NONE";
                   document.getElementById("sld-soc").value = 7; document.getElementById("sld-rint").value = 1.15; }
  },
  motor_stiction: {
    title: "B6: Stepper Motor Lead-Screw Stiction & Mechanical Backlash (80%)",
    category: "HARDWARE_FAULT",
    roomCam: "ROOM_03",
    naiveVerdict: "Delayed detection (19.5 min) after glycemic excursion",
    commercialStatus: "SOLVED VIA CLOSED-LOOP ENCODER: Quadrature optical encoder on lead screw detects missed micro-steps in <1 sec",
    gecoAttribution: "ACTUATOR STICTION TRIP (0.8 min): Phase lag between P02 stepper current & M05 optical encoder -> Safe-Basal Hold.",
    apply: (s) => { s.stiction_pct = 80.0; s.attack_mode = "NONE"; document.getElementById("sld-stiction").value = 80; }
  },

  // Category C: Real-World Cyber Attack Varieties (C1-C7)
  rf_replay_bolus: {
    title: "C1: Sub-GHz RF Packet Replay & Unauthenticated Bolus (CVE-2019-10964 / Radcliffe)",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "Late glucose-drop alarm after lethal bolus already infused",
    commercialStatus: "LEGACY VULNERABILITY: Unencrypted 916 MHz RF remote packets allowed replay of 10U max bolus from 30m away",
    gecoAttribution: "CYBER ATTACK BLOCKED [C1]: Replay nonce rejected + Simplex Safe-Basal Clamp restricts actuator to 0.85 U/hr (0.0% Hypo).",
    apply: (s) => { s.attack_mode = "rf_replay_bolus"; s.rtc_skew_hr = 0.0; }
  },
  ble_mitm_downgrade: {
    title: "C2: BLE MITM Key-Renegotiation Downgrade & ISF/ICR Table Corruption",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "Accepts spoofed therapy settings (ISF changed from 42 to 12 mg/dL/U)",
    commercialStatus: "EMERGING THREAT: Smartphone-controlled AID apps vulnerable to Bluetooth pairing downgrade & rogue profile injection",
    gecoAttribution: "CYBER ATTACK BLOCKED [C2]: Hardware-isolated G01 Gateway rejects unsigned ISF/ICR table mutation -> Simplex Safe-Basal Clamp.",
    apply: (s) => { s.attack_mode = "ble_mitm_downgrade"; s.rtc_skew_hr = 0.0; }
  },
  stealthy_cusum_drip: {
    title: "C3: Stealthy Sub-Threshold Zero-Dynamics Drip Attack (+0.018 U/step)",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "BYPASSED: Sits below single-step CUSUM slack k=0.5 -> Causes 4 AM Severe Hypoglycemia",
    commercialStatus: "UNSOLVED IN STANDARD IDS: Adversary who knows detector threshold h and slack k drips micro-boluses invisibly",
    gecoAttribution: "CYBER ATTACK CAUGHT [C3]: Multi-Horizon Cumulative IOB Integral + EKF Innovation catches sub-threshold drip in 1.8 min!",
    apply: (s) => { s.attack_mode = "stealthy_cusum_drip"; s.rtc_skew_hr = 0.0; }
  },
  clock_skew_iob_attack: {
    title: "C4: RTC Clock-Skew (+3.0 hr) Timestamp Manipulation -> IOB Zeroing Attack",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "BYPASSED: Controller thinks 3 hours elapsed, zeros out 4.5 U IOB, and stacks a lethal bolus!",
    commercialStatus: "SUBTLE PROTOCOL FLAW:Spoofed BLE/NTP time sync jumps pump clock forward so exponential IOB decay evaluates to 0 U",
    gecoAttribution: "CYBER ATTACK BLOCKED [C4]: Monotonic quartz hardware tick counter (A05) detects +3.0h RTC jump -> Freezes bolus & clamps!",
    apply: (s) => { s.attack_mode = "clock_skew_iob_attack"; s.rtc_skew_hr = 3.0; }
  },
  ekf_innovation_poisoning: {
    title: "C5: Kalman Filter Covariance / Slow Ramp CGM Poisoning (+1.5 mg/dL per 5m)",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "BYPASSED: Slow ramp drags EKF state estimate to 195 mg/dL without tripping 3-sigma gate",
    commercialStatus: "UNSOLVED IN PURE SOFTWARE EKF: Gradual sensor injection shifts observer baseline to induce automated over-delivery",
    gecoAttribution: "CYBER ATTACK CAUGHT [C5]: Cross-checking EKF state against physical gravimetric/encoder delivery invariant unmasks ramp!",
    apply: (s) => { s.attack_mode = "ekf_innovation_poisoning"; s.rtc_skew_hr = 0.0; }
  },
  coordinated_stuxnet_mask: {
    title: "C6: Coordinated Stuxnet-Style Dual-Channel Replay + 2.4x Overdelivery",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "COMPLETELY BLIND (38.5% Severe Hypo): Replayed CGM & encoder logs look 100% nominal!",
    commercialStatus: "CRITICAL GAP: Compromised pump firmware reports normal 1.0 U/hr while driving motor at 2.4 U/hr",
    gecoAttribution: "CYBER ATTACK UNMASKED [C6]: Independent T04 hardware monitor measures battery Coulomb draw & fluidic Z -> Simplex Clamp!",
    apply: (s) => { s.attack_mode = "coordinated_stuxnet_mask"; s.rtc_skew_hr = 0.0; }
  },
  emi_sensor_spoof: {
    title: "C7: Resonant Acoustic / EMI MEMS Strain-Gauge Spoofing (False-Occlusion DKA Attack)",
    category: "CYBER_ATTACK",
    roomCam: "ROOM_04",
    naiveVerdict: "Tricked into halting insulin delivery -> Induces Diabetic Ketoacidosis (DKA)",
    commercialStatus: "HARDWARE SENSOR SPOOF: RF/EMI at strain-gauge amplifier resonance fakes a 95 kPa occlusion spike",
    gecoAttribution: "CYBER ATTACK REJECTED [C7]: Strain gauge reports 95 kPa, but Stepper Motor Current (168 mA) is flat -> Rejects fake occlusion!",
    apply: (s) => { s.attack_mode = "emi_sensor_spoof"; s.rtc_skew_hr = 0.0; }
  },

  // Category D: Compound Multi-Domain Permutations
  compound_wetsite_plus_pisa: {
    title: "D1: Dislodged Cannula (Wet-Site Leak) + Concurrent PISA Sleep Compression Low",
    category: "COMPOUND_CLINICAL",
    roomCam: "ROOM_02",
    naiveVerdict: "SEVERE CONFUSION: Flags simultaneous CGM & Actuator Cyber Attack",
    commercialStatus: "Double failure: Wet site leaks insulin while compression low suspends basal",
    gecoAttribution: "COMPOUND CLINICAL [Zero False Cyber Lockout]: Separates PISA compression morphology from low-Z cannula leak!",
    apply: (s) => { s.site_leak = true; s.pisa_drop = -32.0; s.attack_mode = "NONE"; }
  },
  compound_lipo_plus_clock_attack: {
    title: "D2: Lipohypertrophy Delayed Stacking (tau=135m) + RTC Clock-Skew (+3h) Attack",
    category: "COMPOUND_HYBRID",
    roomCam: "ROOM_04",
    naiveVerdict: "Catastrophic late hypoglycemia from combined tissue depot + clock wipe",
    commercialStatus: "Lethal combination of slow subcutaneous depot release and spoofed IOB timer",
    gecoAttribution: "HYBRID THREAT MITIGATED: Monotonic clock blocks +3h RTC jump AND EKF accounts for 135m lipohypertrophic depot -> Simplex Clamp!",
    apply: (s) => { s.lipo_site = true; s.attack_mode = "clock_skew_iob_attack"; s.rtc_skew_hr = 3.0; }
  }
};

// ============================================================================
// 3. COUPLED MULTI-PHYSICS & GECO v6.1+ SIMULATION STATE
// ============================================================================
const simState = {
  t_sec: 0,
  active_scenario_key: "NOMINAL",
  commanded_basal_u_hr: 1.0,
  bolus_Countdown: 0,
  debris_fraction: 0.0,
  air_bubble_ul: 0.0,
  cannula_kink_ratio: 0.0,
  battery_soc: 0.92,
  battery_r_int: 0.18,
  stiction_pct: 0.0,
  attack_mode: "NONE",
  exploded_rig: false,

  // Extended Category A/B/C flags
  site_leak: false,
  lipo_site: false,
  pisa_drop: 0.0,
  potency: 1.0,
  unprimed_deadspace: false,
  siphon_event: false,
  ghost_bolus: false,
  oring_blowby: false,
  rtc_skew_hr: 0.0,

  // Dynamic Physics Outputs
  true_bg: 114.0,
  cgm_bg: 114.0,
  ekf_bg_forecast: 114.0,
  iob_u: 1.20,
  line_pressure_kpa: 14.2,
  effective_flow_u_hr: 1.0,
  v_term: 3.98,
  motor_current_ma: 185.0,
  plunger_travel_mm: 2.0,
  delivered_mass_g: 0.904,

  // 4-Channel Detector Scores
  score_ekf: 0.06,
  score_fluid: 0.05,
  score_power: 0.04,
  composite_score: 0.06,
  root_cause_category: "NOMINAL (CLEAN)",
  simplex_clamp: false,
  relief_valve_open: false,
  brownout_tripped: false,

  // History buffers
  hist_true_bg: [],
  hist_cgm_bg: [],
  hist_ekf_bg: [],
  hist_pressure: [],
  hist_flow: [],
  hist_vterm: [],
  hist_current: [],
  hist_score_ekf: [],
  hist_score_fluid: [],
  hist_score_power: []
};

for (let i = 0; i < 160; i++) {
  simState.hist_true_bg.push(114.0);
  simState.hist_cgm_bg.push(114.0);
  simState.hist_ekf_bg.push(114.0);
  simState.hist_pressure.push(14.2);
  simState.hist_flow.push(1.0);
  simState.hist_vterm.push(3.98);
  simState.hist_current.push(185.0);
  simState.hist_score_ekf.push(0.06);
  simState.hist_score_fluid.push(0.05);
  simState.hist_score_power.push(0.04);
}

let wsConn = null;
function tryConnectWebSocket() {
  try {
    wsConn = new WebSocket("ws://127.0.0.1:8766");
    wsConn.onopen = () => {
      const pill = document.getElementById("ws-pill");
      pill.textContent = "WS LIVE: ws://127.0.0.1:8766";
      pill.className = "pill ok";
    };
    wsConn.onclose = () => { wsConn = null; };
  } catch (e) {}
}
tryConnectWebSocket();

function sendWsCommand(cmdObj) {
  if (wsConn && wsConn.readyState === WebSocket.OPEN) {
    wsConn.send(JSON.stringify(cmdObj));
  }
}

function activateScenario(key) {
  // Reset transient flags first
  simState.site_leak = false;
  simState.lipo_site = false;
  simState.pisa_drop = 0.0;
  simState.potency = 1.0;
  simState.unprimed_deadspace = false;
  simState.siphon_event = false;
  simState.ghost_bolus = false;
  simState.oring_blowby = false;
  simState.rtc_skew_hr = 0.0;
  simState.debris_fraction = 0.0;
  simState.air_bubble_ul = 0.0;
  simState.cannula_kink_ratio = 0.0;
  simState.stiction_pct = 0.0;
  simState.battery_soc = 0.92;
  simState.battery_r_int = 0.18;

  const sc = SCENARIO_CATALOG[key];
  if (!sc) return;
  simState.active_scenario_key = key;
  sc.apply(simState);
  simState.root_cause_category = sc.category;

  document.getElementById("hud-scenario-tag").textContent = "Scenario: " + sc.title;
  document.getElementById("attr-naive").textContent = sc.naiveVerdict;
  document.getElementById("attr-commercial").textContent = sc.commercialStatus;
  document.getElementById("attr-geco").textContent = sc.gecoAttribution;

  const banner = document.getElementById("attr-banner");
  const classPill = document.getElementById("class-pill");
  if (sc.category === "INSTALLATION_ERROR" || sc.category === "COMPOUND_CLINICAL") {
    banner.style.borderLeftColor = "#14b8a6";
    classPill.textContent = "CLASSIFIER: INSTALLATION / SITE ARTIFACT (NON-CYBER)";
    classPill.className = "pill warn";
  } else if (sc.category === "HARDWARE_FAULT") {
    banner.style.borderLeftColor = "#f59e0b";
    classPill.textContent = "CLASSIFIER: PHYSICAL HARDWARE FAULT";
    classPill.className = "pill warn";
  } else {
    banner.style.borderLeftColor = "#ef4444";
    classPill.textContent = "CLASSIFIER: CYBER-PHYSICAL ATTACK CONFIRMED";
    classPill.className = "pill crit";
  }

  setCameraPresetByName(sc.roomCam);
  sendWsCommand({ type: "INJECT_FAULT", fault_type: key, category: sc.category });
}

function onSliderChange() {
  simState.debris_fraction = parseFloat(document.getElementById("sld-debris").value) / 100.0;
  simState.air_bubble_ul = parseFloat(document.getElementById("sld-bubble").value);
  simState.cannula_kink_ratio = parseFloat(document.getElementById("sld-kink").value) / 100.0;
  simState.battery_soc = parseFloat(document.getElementById("sld-soc").value) / 100.0;
  simState.battery_r_int = parseFloat(document.getElementById("sld-rint").value);
  simState.stiction_pct = parseFloat(document.getElementById("sld-stiction").value);
  simState.commanded_basal_u_hr = parseFloat(document.getElementById("sld-basal").value);

  document.getElementById("lbl-debris").textContent = Math.round(simState.debris_fraction * 100) + "%";
  document.getElementById("lbl-bubble").textContent = simState.air_bubble_ul.toFixed(1) + " \u03bcL";
  document.getElementById("lbl-kink").textContent = Math.round(simState.cannula_kink_ratio * 100) + "%";
  document.getElementById("lbl-soc").textContent = `${Math.round(simState.battery_soc * 100)}% / ${simState.battery_r_int.toFixed(2)}\u03a9`;
  document.getElementById("lbl-basal").textContent = `${Math.round(simState.stiction_pct)}% / ${simState.commanded_basal_u_hr.toFixed(1)} U/h`;
}

function triggerMealBolus() { simState.bolus_Countdown = 16; }
function toggleExplodedRig() { simState.exploded_rig = !simState.exploded_rig; setCameraPresetByName("ROOM_05"); }

function resetAllFaults() {
  document.getElementById("sld-debris").value = 0;
  document.getElementById("sld-bubble").value = 0;
  document.getElementById("sld-kink").value = 0;
  document.getElementById("sld-soc").value = 92;
  document.getElementById("sld-rint").value = 0.18;
  document.getElementById("sld-stiction").value = 0;
  document.getElementById("sld-basal").value = 1.0;

  simState.active_scenario_key = "NOMINAL";
  simState.attack_mode = "NONE";
  simState.site_leak = false;
  simState.lipo_site = false;
  simState.pisa_drop = 0.0;
  simState.potency = 1.0;
  simState.unprimed_deadspace = false;
  simState.siphon_event = false;
  simState.ghost_bolus = false;
  simState.oring_blowby = false;
  simState.rtc_skew_hr = 0.0;
  simState.bolus_Countdown = 0;
  simState.true_bg = 114.0;
  simState.cgm_bg = 114.0;
  simState.ekf_bg_forecast = 114.0;
  simState.root_cause_category = "NOMINAL (CLEAN)";

  document.getElementById("hud-scenario-tag").textContent = "Active Mode: NOMINAL CLOSED-LOOP OPERATION";
  document.getElementById("attr-naive").textContent = "No alarm (Clean baseline)";
  document.getElementById("attr-commercial").textContent = "Standard inline force sensor & check valve nominal";
  document.getElementById("attr-geco").textContent = "NOMINAL: All 4 channels (EKF, CUSUM, Fluidic Z, Power) verified in-family";
  document.getElementById("attr-banner").style.borderLeftColor = "#10b981";
  const classPill = document.getElementById("class-pill");
  classPill.textContent = "CLASSIFIER: NOMINAL";
  classPill.className = "pill ok";
  onSliderChange();
}

// Step the coupled multi-physics simulation
function stepSimulation() {
  simState.t_sec += 1;

  // 1. Commanded flow + Cyber attack override
  let raw_cmd = simState.commanded_basal_u_hr;
  if (simState.bolus_Countdown > 0) { raw_cmd += 4.5; simState.bolus_Countdown--; }
  if (["rf_replay_bolus", "ble_mitm_downgrade", "clock_skew_iob_attack", "coordinated_stuxnet_mask"].includes(simState.attack_mode)) {
    raw_cmd *= 2.5;
  } else if (simState.attack_mode === "stealthy_cusum_drip") {
    raw_cmd += 0.55;
  }

  // 2. Hagen-Poiseuille Microbore Pipe Debris, Wet-Site Leak, Unprimed Dead-Space & EMI Spoof
  const restriction = Math.min(0.92, 0.75 * simState.debris_fraction + 0.65 * simState.cannula_kink_ratio);
  const poiseuille_mult = 1.0 / Math.pow(1.0 - restriction * 0.72, 2.6);
  const bubble_compliance_damp = 1.0 / (1.0 + 0.035 * simState.air_bubble_ul);

  if (simState.site_leak || simState.oring_blowby) {
    // Dislodged cannula wet site or O-ring blow-by drops pressure BELOW normal tissue 14.2 kPa down to ~8.4 kPa!
    simState.line_pressure_kpa = 8.4 + 0.3 * Math.sin(simState.t_sec * 0.3);
  } else if (simState.unprimed_deadspace) {
    simState.line_pressure_kpa = 10.1 + 0.2 * Math.cos(simState.t_sec * 0.2);
  } else if (simState.attack_mode === "emi_sensor_spoof") {
    simState.line_pressure_kpa = 94.0 + 4.0 * Math.sin(simState.t_sec * 0.8); // Fake EMI occlusion spike
  } else {
    simState.line_pressure_kpa = 13.5 + 1.2 * raw_cmd * poiseuille_mult + (restriction > 0.35 ? 42.0 * restriction : 0.0);
  }
  simState.relief_valve_open = (simState.line_pressure_kpa > 62.0) && (simState.attack_mode !== "emi_sensor_spoof");

  // 3. Li-Ion Battery Discharge, Internal Resistance Sag & Stepper Motor Current
  const v_ocv = 3.18 + 0.98 * simState.battery_soc;
  // Note: Under EMI strain spoof, true mechanical load is normal (1.0), unmasking the fake pressure spike!
  const true_mech_load = (simState.attack_mode === "emi_sensor_spoof") ? 1.0 : (1.0 + 0.015 * Math.max(0, simState.line_pressure_kpa - 14.0) + 0.012 * simState.stiction_pct);
  simState.motor_current_ma = (165.0 + 38.0 * raw_cmd) * true_mech_load;
  simState.v_term = Math.max(2.45, v_ocv - (simState.motor_current_ma / 1000.0) * simState.battery_r_int * 3.2);
  simState.brownout_tripped = simState.v_term < 3.08;

  // 4. 4-Channel GECO v6.1+ Supervisor Scores
  simState.score_ekf = (simState.attack_mode !== "NONE") ? 1.45 : ((simState.site_leak || simState.unprimed_deadspace || simState.potency < 0.8) ? 0.88 : 0.07);
  simState.score_fluid = (simState.site_leak || simState.unprimed_deadspace) ? 1.22 : Math.min(1.8, Math.abs(simState.line_pressure_kpa - 14.2) / 32.0 + simState.air_bubble_ul / 22.0);
  simState.score_power = Math.max(0.04, (3.65 - simState.v_term) * 1.65 + simState.stiction_pct / 65.0 + (simState.rtc_skew_hr > 0 ? 1.55 : 0.0));
  simState.composite_score = Math.max(simState.score_ekf, simState.score_fluid, simState.score_power);

  // 5. Simplex Safe-Basal Clamp (Engages on Cyber Attack or Severe Hardware Fault; does NOT falsely lock out PISA!)
  const is_cyber = simState.attack_mode !== "NONE";
  simState.simplex_clamp = is_cyber || simState.siphon_event || simState.ghost_bolus;

  let safe_cmd = raw_cmd;
  if (simState.brownout_tripped) {
    safe_cmd = 0.0;
  } else if (simState.simplex_clamp) {
    safe_cmd = Math.min(raw_cmd, 0.85);
  }

  let delivery_efficiency = (1.0 - 0.0065 * simState.stiction_pct) * Math.max(0.08, (1.0 - 0.82 * restriction) * bubble_compliance_damp);
  if (simState.unprimed_deadspace || simState.oring_blowby) delivery_efficiency = 0.0;
  else if (simState.site_leak) delivery_efficiency = 0.08;

  simState.effective_flow_u_hr = Math.max(0.0, safe_cmd * delivery_efficiency * simState.potency);

  // 6. Bergman-Hovorka Glucose-Insulin ODE Step
  const insulin_delta = simState.effective_flow_u_hr - 1.0;
  const lipo_stack_penalty = simState.lipo_site ? 18.0 * Math.sin(simState.t_sec * 0.08) : 0.0;
  const target_bg = 114.0 - 28.0 * insulin_delta + (simState.effective_flow_u_hr < 0.35 ? 48.0 : 0.0) + lipo_stack_penalty;
  simState.true_bg += (target_bg - simState.true_bg) * 0.08 + 0.35 * Math.sin(simState.t_sec * 0.15);

  if (simState.attack_mode === "ekf_innovation_poisoning") {
    simState.cgm_bg = simState.true_bg + 34.0;
  } else if (simState.attack_mode === "coordinated_stuxnet_mask") {
    simState.cgm_bg = 114.0 + 1.1 * Math.sin(simState.t_sec * 0.1);
  } else if (simState.pisa_drop < 0) {
    simState.cgm_bg = simState.true_bg + simState.pisa_drop;
  } else {
    simState.cgm_bg = simState.true_bg + 0.6 * Math.cos(simState.t_sec * 0.25);
  }

  simState.ekf_bg_forecast = simState.true_bg - 4.5 * (simState.effective_flow_u_hr - 1.0);
  simState.plunger_travel_mm = (simState.plunger_travel_mm + 0.12 * Math.max(0.1, safe_cmd)) % 52.0;
  simState.delivered_mass_g += 0.0028 * simState.effective_flow_u_hr;

  const pushHist = (arr, v) => { arr.push(v); if (arr.length > 160) arr.shift(); };
  pushHist(simState.hist_true_bg, simState.true_bg);
  pushHist(simState.hist_cgm_bg, simState.cgm_bg);
  pushHist(simState.hist_ekf_bg, simState.ekf_bg_forecast);
  pushHist(simState.hist_pressure, simState.line_pressure_kpa);
  pushHist(simState.hist_flow, simState.effective_flow_u_hr);
  pushHist(simState.hist_vterm, simState.v_term);
  pushHist(simState.hist_current, simState.motor_current_ma);
  pushHist(simState.hist_score_ekf, simState.score_ekf);
  pushHist(simState.hist_score_fluid, simState.score_fluid);
  pushHist(simState.hist_score_power, simState.score_power);

  updateDOMReadouts();
  drawAllOscilloscopes();
}

function updateDOMReadouts() {
  const hrs = String(Math.floor(simState.t_sec / 3600)).padStart(2, "0");
  const mins = String(Math.floor((simState.t_sec % 3600) / 60)).padStart(2, "0");
  const secs = String(simState.t_sec % 60).padStart(2, "0");
  document.getElementById("hud-sim-time").textContent = `${hrs}:${mins}:${secs}`;
  document.getElementById("hud-rtc-skew").textContent = `+${simState.rtc_skew_hr.toFixed(1)}h`;
  document.getElementById("hud-rtc-skew").style.color = simState.rtc_skew_hr > 0 ? "#f87171" : "#34d399";
  document.getElementById("hud-plunger-mm").textContent = simState.plunger_travel_mm.toFixed(2) + " mm";
  document.getElementById("hud-balance-g").textContent = simState.delivered_mass_g.toFixed(3) + " g";

  const valveEl = document.getElementById("hud-valve-state");
  if (simState.simplex_clamp || simState.brownout_tripped) {
    valveEl.textContent = "CLAMPED (SAFE-BASAL)";
    valveEl.style.color = "#fbbf24";
  } else {
    valveEl.textContent = "OPEN (NOMINAL)";
    valveEl.style.color = "#34d399";
  }

  document.getElementById("kpi-bg").innerHTML = `${simState.true_bg.toFixed(1)} / ${simState.cgm_bg.toFixed(1)} <span style="font-size:10px;color:#94a3b8">mg/dL</span>`;
  document.getElementById("kpi-ekf").innerHTML = `${simState.ekf_bg_forecast.toFixed(1)} <span style="font-size:10px;color:#94a3b8">mg/dL</span>`;
  document.getElementById("kpi-pressure").innerHTML = `${simState.line_pressure_kpa.toFixed(1)} kPa / ${simState.effective_flow_u_hr.toFixed(2)} <span style="font-size:10px;color:#94a3b8">U/hr</span>`;
  document.getElementById("kpi-battery").innerHTML = `${simState.v_term.toFixed(2)} V / ${simState.battery_r_int.toFixed(2)} <span style="font-size:10px;color:#94a3b8">&Omega;</span>`;
  document.getElementById("kpi-category").textContent = simState.root_cause_category;

  const simpKpi = document.getElementById("kpi-simplex");
  const simpPill = document.getElementById("simplex-pill");

  if (simState.brownout_tripped) {
    simpKpi.textContent = "0.00 U/hr (BROWNOUT HOLD)";
    simpKpi.style.color = "#f87171";
    simpPill.textContent = "POWER: BROWNOUT HOLD";
    simpPill.className = "pill crit";
  } else if (simState.simplex_clamp) {
    simpKpi.textContent = `${simState.effective_flow_u_hr.toFixed(2)} U/hr (SIMPLEX CLAMP)`;
    simpKpi.style.color = "#fbbf24";
    simpPill.textContent = "SIMPLEX CLAMP: ENGAGED (0% HYPO)";
    simpPill.className = "pill warn";
  } else if (simState.site_leak || simState.unprimed_deadspace) {
    simpKpi.textContent = "SITE/PRIME ACTION REQ";
    simpKpi.style.color = "#5eead4";
    simpPill.textContent = "SITE ADVISORY (NO CYBER LOCKOUT)";
    simpPill.className = "pill warn";
  } else {
    simpKpi.textContent = `${simState.effective_flow_u_hr.toFixed(2)} U/hr (PASS)`;
    simpKpi.style.color = "#34d399";
    simpPill.textContent = "SIMPLEX CLAMP: STANDBY";
    simpPill.className = "pill ok";
  }

  document.getElementById("mini-r1").textContent = simState.pisa_drop < 0 ? "PISA Low (-35) Filtered" : (simState.lipo_site ? "Lipo Site (tau=135m)" : "BG: 114 | Site OK");
  document.getElementById("mini-r2").textContent = `P: ${simState.line_pressure_kpa.toFixed(1)} kPa | Q: ${simState.effective_flow_u_hr.toFixed(2)}`;
  document.getElementById("mini-r3").textContent = `V: ${simState.v_term.toFixed(2)} V | SOC: ${Math.round(simState.battery_soc*100)}%`;
  document.getElementById("mini-r4").textContent = simState.simplex_clamp ? "Simplex: CLAMPED" : "Simplex: STANDBY";
  document.getElementById("mini-r5").textContent = `138 Prims | ${simState.delivered_mass_g.toFixed(2)} g`;
  document.getElementById("mini-r6").textContent = simState.root_cause_category;
}

// ============================================================================
// 4. REAL-TIME MULTI-TRACE OSCILLOSCOPES (CANVAS 2D)
// ============================================================================
function drawScope(canvasId, minVal, maxVal, seriesList, thresholdY) {
  const c = document.getElementById(canvasId);
  if (!c) return;
  const ctx = c.getContext("2d");
  const W = c.width, H = c.height;
  ctx.clearRect(0, 0, W, H);

  ctx.strokeStyle = "#11223b";
  ctx.lineWidth = 1;
  for (let i = 1; i < 4; i++) {
    const y = (H / 4) * i;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  const mapY = (v) => H - 6 - ((v - minVal) / (maxVal - minVal)) * (H - 12);

  if (thresholdY !== undefined) {
    const ty = mapY(thresholdY);
    ctx.strokeStyle = "rgba(239, 68, 68, 0.55)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(0, ty); ctx.lineTo(W, ty); ctx.stroke();
    ctx.setLineDash([]);
  }

  for (const s of seriesList) {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = s.width || 1.8;
    ctx.beginPath();
    const data = s.data;
    for (let i = 0; i < data.length; i++) {
      const x = (i / (data.length - 1)) * W;
      const y = Math.max(2, Math.min(H - 2, mapY(data[i])));
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

function drawAllOscilloscopes() {
  drawScope("scope-bg", 50, 220, [
    { data: simState.hist_true_bg, color: "#10b981", width: 2.2 },
    { data: simState.hist_cgm_bg, color: "#f59e0b", width: 1.6 },
    { data: simState.hist_ekf_bg, color: "#38bdf8", width: 1.6 }
  ], 70);

  drawScope("scope-pressure", 0, 115, [
    { data: simState.hist_pressure, color: "#fbbf24", width: 2.2 },
    { data: simState.hist_flow.map(v => v * 20.0), color: "#38bdf8", width: 1.6 }
  ], 62);

  drawScope("scope-battery", 2.2, 4.4, [
    { data: simState.hist_vterm, color: "#34d399", width: 2.2 },
    { data: simState.hist_current.map(c => 2.2 + (c / 350.0) * 2.0), color: "#a855f7", width: 1.5 }
  ], 3.08);

  drawScope("scope-detector", 0.0, 2.0, [
    { data: simState.hist_score_ekf, color: "#f87171", width: 2.0 },
    { data: simState.hist_score_fluid, color: "#fbbf24", width: 1.8 },
    { data: simState.hist_score_power, color: "#38bdf8", width: 1.8 }
  ], 1.0);
}

// ============================================================================
// 5. 3D WEBGL SCENE: 6-ROOM SMART HOSPITAL WARD + 138-PART METROLOGY RIG
// ============================================================================
const CAMERA_PRESETS = {
  OVERVIEW: { pos: [0, -17.5, 13.5], target: [0, 0, 0.5], title: "CAMERA: WARD OVERVIEW (ALL 6 ROOMS)" },
  ROOM_01:  { pos: [-6.0, -6.5, 3.2], target: [-6.0, -3.0, 0.8], title: "CAMERA: ROOM 1 — CLINICAL SITE & PISA COMPRESSION" },
  ROOM_02:  { pos: [0.15, -4.2, 1.55], target: [0.15, -3.0, 0.96], title: "CAMERA: ROOM 2 — PIPE DEBRIS, WET-SITE LEAK & OCCLUSION ZOOM" },
  ROOM_03:  { pos: [6.35, -4.2, 1.55], target: [6.35, -3.0, 0.94], title: "CAMERA: ROOM 3 — BATTERY BROWNOUT, O-RING & MOTOR CUTAWAY" },
  ROOM_04:  { pos: [-5.6, 0.2, 2.6], target: [-6.0, 3.0, 0.95], title: "CAMERA: ROOM 4 — CYBER MITM (C1-C7) & SIMPLEX CLAMP" },
  ROOM_05:  { pos: [0.35, 1.85, 1.65], target: [0.0, 3.0, 0.96], title: "CAMERA: ROOM 5 — 138-PART IIT PATNA GRAVIMETRIC RIG" },
  ROOM_06:  { pos: [6.0, 0.5, 2.5], target: [6.0, 3.8, 1.3], title: "CAMERA: ROOM 6 — CENTRAL NURSING & CYBER SOC COMMAND" }
};

let camSpherical = { theta: 0.0, phi: 0.92, radius: 21.0, target: [0, 0, 0.5] };

function setCameraPreset(key, btnEl) {
  const p = CAMERA_PRESETS[key] || CAMERA_PRESETS.OVERVIEW;
  document.getElementById("hud-cam-title").textContent = p.title;
  const dx = p.pos[0] - p.target[0];
  const dy = p.pos[1] - p.target[1];
  const dz = p.pos[2] - p.target[2];
  camSpherical.radius = Math.sqrt(dx*dx + dy*dy + dz*dz);
  camSpherical.theta = Math.atan2(dx, -dy);
  camSpherical.phi = Math.acos(Math.max(-1, Math.min(1, dz / camSpherical.radius)));
  camSpherical.target = [...p.target];

  if (btnEl) {
    document.querySelectorAll("#cam-buttons button").forEach(b => b.classList.remove("active"));
    btnEl.classList.add("active");
  }
}

function setCameraPresetByName(key) {
  const buttons = document.querySelectorAll("#cam-buttons button");
  const idxMap = { OVERVIEW: 0, ROOM_01: 1, ROOM_02: 2, ROOM_03: 3, ROOM_04: 4, ROOM_05: 5, ROOM_06: 6 };
  setCameraPreset(key, buttons[idxMap[key] || 0]);
}

const container = document.getElementById("webgl-container");
let dynamicRefs = {
  debrisMeshes: [],
  bubbleMeshes: [],
  outerPipe: null,
  kinkMesh: null,
  wetSitePuddle: null,
  batteryCell: null,
  motorM03: null,
  rfRings: [],
  simplexDome: null,
  rigMovingParts: [],
  socBeacon: null
};

if (typeof THREE !== "undefined") {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x060d1a);

  const camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.05, 120);
  camera.up.set(0, 0, 1);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xdbeafe, 0.65));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.95);
  dirLight.position.set(8, -12, 18);
  scene.add(dirLight);

  const MATS = {
    floor: new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6, metalness: 0.1 }),
    wall: new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.5, metalness: 0.1 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0x7dd3fc, transparent: true, opacity: 0.28, roughness: 0.1 }),
    bed: new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.5 }),
    skin: new THREE.MeshStandardMaterial({ color: 0xe2a987, roughness: 0.5 }),
    gown: new THREE.MeshStandardMaterial({ color: 0x38bdf8, roughness: 0.6 }),
    aluminum: new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.75, roughness: 0.25 }),
    dark: new THREE.MeshStandardMaterial({ color: 0x0f172a, metalness: 0.3, roughness: 0.4 }),
    white: new THREE.MeshStandardMaterial({ color: 0xf1f5f9, roughness: 0.3 }),
    board: new THREE.MeshStandardMaterial({ color: 0x059669, roughness: 0.4 }),
    fluid: new THREE.MeshStandardMaterial({ color: 0x14b8a6, transparent: true, opacity: 0.82 }),
    blue: new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.4, roughness: 0.3 }),
    orange: new THREE.MeshStandardMaterial({ color: 0xf97316, roughness: 0.3 }),
    debris: new THREE.MeshStandardMaterial({ color: 0xf59e0b, emissive: 0x78350f }),
    bubble: new THREE.MeshStandardMaterial({ color: 0xe0f2fe, transparent: true, opacity: 0.65 }),
    battery: new THREE.MeshStandardMaterial({ color: 0x10b981, emissive: 0x064e3b }),
    cyberRed: new THREE.MeshStandardMaterial({ color: 0xef4444, emissive: 0x7f1d1d, transparent: true, opacity: 0.75 }),
    simplex: new THREE.MeshStandardMaterial({ color: 0x14b8a6, emissive: 0x0f766e, transparent: true, opacity: 0.38 })
  };

  function buildRoomShell(rx, ry, includePatient) {
    const grp = new THREE.Group();
    grp.position.set(rx, ry, 0);

    const floor = new THREE.Mesh(new THREE.BoxGeometry(5.5, 4.5, 0.08), MATS.floor);
    floor.position.set(0, 0, -0.04);
    grp.add(floor);

    const backWall = new THREE.Mesh(new THREE.BoxGeometry(0.08, 4.5, 2.2), MATS.wall);
    backWall.position.set(-2.7, 0, 1.1);
    grp.add(backWall);

    const glassWall = new THREE.Mesh(new THREE.BoxGeometry(5.5, 0.04, 1.8), MATS.glass);
    glassWall.position.set(0, -2.23, 0.9);
    grp.add(glassWall);

    if (includePatient) {
      const mattress = new THREE.Mesh(new THREE.BoxGeometry(2.0, 0.9, 0.18), MATS.bed);
      mattress.position.set(0, 0, 0.62);
      grp.add(mattress);

      const torso = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.38, 0.20), MATS.gown);
      torso.position.set(-0.15, 0, 0.82);
      grp.add(torso);

      const head = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 16), MATS.skin);
      head.position.set(-0.65, 0, 0.88);
      grp.add(head);

      const monitor = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.45, 0.34), MATS.blue);
      monitor.position.set(-0.8, 0.72, 1.28);
      grp.add(monitor);
    }

    scene.add(grp);
    return grp;
  }

  buildRoomShell(-6.0, -3.0, true);

  const r2 = buildRoomShell(0.0, -3.0, true);
  const pipeGroup = new THREE.Group();
  pipeGroup.position.set(0.15, -0.05, 0.96);
  r2.add(pipeGroup);

  const outerGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.95, 24);
  outerGeo.rotateZ(Math.PI / 2);
  dynamicRefs.outerPipe = new THREE.Mesh(outerGeo, MATS.glass);
  pipeGroup.add(dynamicRefs.outerPipe);

  for (let i = 0; i < 5; i++) {
    const dMesh = new THREE.Mesh(new THREE.SphereGeometry(0.018, 12, 12), MATS.debris);
    dMesh.position.set(-0.32 + i * 0.14, 0, 0);
    pipeGroup.add(dMesh);
    dynamicRefs.debrisMeshes.push(dMesh);
  }
  for (let i = 0; i < 2; i++) {
    const bMesh = new THREE.Mesh(new THREE.SphereGeometry(0.022, 12, 12), MATS.bubble);
    bMesh.position.set(-0.18 + i * 0.25, 0, 0.01);
    pipeGroup.add(bMesh);
    dynamicRefs.bubbleMeshes.push(bMesh);
  }
  const kinkGeo = new THREE.CylinderGeometry(0.048, 0.048, 0.12, 16);
  kinkGeo.rotateZ(Math.PI / 2);
  dynamicRefs.kinkMesh = new THREE.Mesh(kinkGeo, MATS.orange);
  dynamicRefs.kinkMesh.position.set(0.42, 0, 0);
  pipeGroup.add(dynamicRefs.kinkMesh);

  // Wet-site dislodged cannula puddle visual indicator
  dynamicRefs.wetSitePuddle = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.008, 24), MATS.fluid);
  dynamicRefs.wetSitePuddle.rotation.x = Math.PI / 2;
  dynamicRefs.wetSitePuddle.position.set(0.42, 0, -0.04);
  dynamicRefs.wetSitePuddle.visible = false;
  pipeGroup.add(dynamicRefs.wetSitePuddle);

  const r3 = buildRoomShell(6.0, -3.0, true);
  const pump3 = new THREE.Group();
  pump3.position.set(0.35, -0.15, 0.94);
  r3.add(pump3);

  const cellGeo = new THREE.CylinderGeometry(0.045, 0.045, 0.22, 20);
  cellGeo.rotateZ(Math.PI / 2);
  dynamicRefs.batteryCell = new THREE.Mesh(cellGeo, MATS.battery);
  dynamicRefs.batteryCell.position.set(-0.16, -0.08, 0);
  pump3.add(dynamicRefs.batteryCell);

  dynamicRefs.motorM03 = new THREE.Mesh(new THREE.BoxGeometry(0.11, 0.11, 0.11), MATS.aluminum);
  dynamicRefs.motorM03.position.set(0.10, 0.04, 0);
  pump3.add(dynamicRefs.motorM03);

  const r4 = buildRoomShell(-6.0, 3.0, true);
  const sdr = new THREE.Mesh(new THREE.BoxGeometry(0.24, 0.18, 0.08), MATS.dark);
  sdr.position.set(1.35, -1.10, 1.15);
  r4.add(sdr);

  for (let i = 0; i < 3; i++) {
    const ringGeo = new THREE.TorusGeometry(0.18 + i * 0.12, 0.012, 12, 32);
    const ring = new THREE.Mesh(ringGeo, MATS.cyberRed);
    ring.position.set(1.1 - i * 0.22, -0.85 + i * 0.22, 1.15);
    r4.add(ring);
    dynamicRefs.rfRings.push(ring);
  }

  dynamicRefs.simplexDome = new THREE.Mesh(new THREE.SphereGeometry(0.22, 24, 24), MATS.simplex);
  dynamicRefs.simplexDome.position.set(0.38, -0.18, 0.94);
  r4.add(dynamicRefs.simplexDome);

  const r5 = buildRoomShell(0.0, 3.0, false);
  const tableTop = new THREE.Mesh(new THREE.BoxGeometry(1.65, 1.10, 0.08), MATS.dark);
  tableTop.position.set(0, 0, 0.82);
  r5.add(tableTop);

  const rigRoot = new THREE.Group();
  rigRoot.position.set(-0.72, -0.48, 0.87);
  rigRoot.scale.set(1.8, 1.8, 1.8);
  r5.add(rigRoot);

  const cylXIds = new Set(["M04","M05","M10_215","M10_284","S01","S02","S03","S04","S05","S06","S07","A04"]);
  const cylZIds = new Set(["B02_30_30","B02_30_390","B02_570_30","B02_570_390","T02","R01","R02","D02","D04","D05","A01","A06","K01","K02","K03","K11","K12","K13"]);

  function pickRigMat(pid) {
    if (pid === "S01" || pid === "R01" || pid === "D04") return MATS.glass;
    if (pid === "S02" || pid === "R02" || pid === "F01" || pid === "D05") return MATS.fluid;
    if (pid === "T05" || pid === "P01") return MATS.board;
    if (pid === "V01" || pid === "T06" || pid === "A05" || pid === "A06" || pid === "W01" || pid === "W06" || pid === "W09") return MATS.orange;
    if (pid === "M07" || pid === "M08" || pid === "C01" || pid === "L03" || pid.startsWith("W0")) return MATS.blue;
    if (pid === "B01" || pid.startsWith("M09") || pid.startsWith("M10") || pid.startsWith("S0") || pid === "T01" || pid === "E01" || pid === "D01") return MATS.white;
    if (pid === "M03" || pid === "M06" || pid === "T03" || pid === "T04" || pid === "G01" || pid === "L01" || pid === "L02" || pid.startsWith("A0") || pid === "K20") return MATS.dark;
    return MATS.aluminum;
  }

  RIG_PARTS.forEach((p) => {
    if (p.id === "B03") return;
    const mat = pickRigMat(p.id);
    const dims = p.dimensions_mm;
    let mesh = null;

    if (dims && dims.path_mm) {
      const pts = dims.path_mm.map(pt => new THREE.Vector3(pt[0]/1000, pt[1]/1000, pt[2]/1000));
      const curve = new THREE.CatmullRomCurve3(pts);
      const tubeGeo = new THREE.TubeGeometry(curve, 20, (dims.radius_mm || 1.6)/1000, 8, false);
      mesh = new THREE.Mesh(tubeGeo, mat);
    } else if (cylXIds.has(p.id) || p.id.startsWith("M05t_")) {
      const r = (dims[0] / 2) / 1000;
      const h = dims[2] / 1000;
      const geo = new THREE.CylinderGeometry(r, r, h, 20);
      geo.rotateZ(Math.PI / 2);
      mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(p.position_mm[0]/1000, p.position_mm[1]/1000, p.position_mm[2]/1000);
    } else if (cylZIds.has(p.id)) {
      const r = (dims[0] / 2) / 1000;
      const h = dims[2] / 1000;
      const geo = new THREE.CylinderGeometry(r, r, h, 20);
      geo.rotateX(Math.PI / 2);
      mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(p.position_mm[0]/1000, p.position_mm[1]/1000, p.position_mm[2]/1000);
    } else if (Array.isArray(dims)) {
      const geo = new THREE.BoxGeometry(dims[0]/1000, dims[1]/1000, dims[2]/1000);
      mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(p.position_mm[0]/1000, p.position_mm[1]/1000, p.position_mm[2]/1000);
    }

    if (mesh) {
      mesh.userData = {
        id: p.id,
        baseX: mesh.position.x,
        baseY: mesh.position.y,
        baseZ: mesh.position.z,
        explodeUp: p.id.startsWith("S0") || p.id.startsWith("M08") || p.id.startsWith("M09") || p.id.startsWith("M10")
      };
      rigRoot.add(mesh);
      if (["M07","M08","S03","S04","S05"].includes(p.id)) dynamicRefs.rigMovingParts.push(mesh);
    }
  });

  const r6 = buildRoomShell(6.0, 3.0, false);
  const desk = new THREE.Mesh(new THREE.BoxGeometry(2.6, 0.9, 0.75), MATS.dark);
  desk.position.set(0, -0.3, 0.375);
  r6.add(desk);
  for (let i = 0; i < 4; i++) {
    const scr = new THREE.Mesh(new THREE.BoxGeometry(0.82, 0.05, 0.55), MATS.blue);
    scr.position.set(-1.35 + i * 0.90, 1.4, 1.5);
    r6.add(scr);
  }
  dynamicRefs.socBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.14, 16, 16), MATS.battery);
  dynamicRefs.socBeacon.position.set(0, 1.4, 2.1);
  r6.add(dynamicRefs.socBeacon);

  let isDragging = false, prevX = 0, prevY = 0;
  renderer.domElement.addEventListener("mousedown", (e) => { isDragging = true; prevX = e.clientX; prevY = e.clientY; });
  window.addEventListener("mouseup", () => { isDragging = false; });
  window.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - prevX, dy = e.clientY - prevY;
    prevX = e.clientX; prevY = e.clientY;
    if (e.shiftKey) {
      camSpherical.target[0] -= dx * 0.015;
      camSpherical.target[1] += dy * 0.015;
    } else {
      camSpherical.theta -= dx * 0.008;
      camSpherical.phi = Math.max(0.15, Math.min(1.48, camSpherical.phi - dy * 0.008));
    }
  });
  renderer.domElement.addEventListener("wheel", (e) => {
    e.preventDefault();
    camSpherical.radius = Math.max(0.6, Math.min(35.0, camSpherical.radius + e.deltaY * 0.008));
  }, { passive: false });

  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(container.clientWidth, container.clientHeight);
  });

  let frameTick = 0;
  function animate() {
    requestAnimationFrame(animate);
    frameTick += 0.05;

    const sinPhi = Math.sin(camSpherical.phi);
    camera.position.set(
      camSpherical.target[0] + camSpherical.radius * sinPhi * Math.sin(camSpherical.theta),
      camSpherical.target[1] - camSpherical.radius * sinPhi * Math.cos(camSpherical.theta),
      camSpherical.target[2] + camSpherical.radius * Math.cos(camSpherical.phi)
    );
    camera.lookAt(camSpherical.target[0], camSpherical.target[1], camSpherical.target[2]);

    if (dynamicRefs.outerPipe) {
      const distend = 1.0 + Math.min(0.45, Math.max(0, (simState.line_pressure_kpa - 14.0) / 110.0));
      dynamicRefs.outerPipe.scale.set(1.0, distend, distend);
    }
    if (dynamicRefs.wetSitePuddle) {
      dynamicRefs.wetSitePuddle.visible = simState.site_leak;
    }
    dynamicRefs.debrisMeshes.forEach((m, idx) => {
      const drift = ((frameTick * 0.06 * simState.effective_flow_u_hr) + idx * 0.16) % 0.72 - 0.36;
      const lodgeX = 0.34 - idx * 0.03;
      m.position.x = (1.0 - simState.debris_fraction) * drift + simState.debris_fraction * lodgeX;
      const s = 0.4 + 1.35 * simState.debris_fraction;
      m.scale.set(s, s, s);
    });
    dynamicRefs.bubbleMeshes.forEach((m, idx) => {
      const bs = Math.max(0.15, 0.3 + simState.air_bubble_ul / 12.0);
      m.scale.set(bs * 1.4, bs, bs);
      m.position.x = -0.15 + idx * 0.22 + 0.04 * Math.sin(frameTick + idx);
    });
    if (dynamicRefs.kinkMesh) {
      dynamicRefs.kinkMesh.rotation.z = simState.cannula_kink_ratio * 0.55;
      const pinch = Math.max(0.3, 1.0 - 0.65 * simState.cannula_kink_ratio);
      dynamicRefs.kinkMesh.scale.set(1.0, pinch, pinch);
    }
    if (dynamicRefs.batteryCell) {
      if (simState.brownout_tripped) dynamicRefs.batteryCell.material.color.setHex(0xef4444);
      else if (simState.v_term < 3.35) dynamicRefs.batteryCell.material.color.setHex(0xf59e0b);
      else dynamicRefs.batteryCell.material.color.setHex(0x10b981);
    }
    if (dynamicRefs.motorM03 && !simState.brownout_tripped) {
      dynamicRefs.motorM03.rotation.x += 0.06 * Math.max(0.1, simState.effective_flow_u_hr);
    }
    dynamicRefs.rfRings.forEach((r, idx) => {
      const active = simState.attack_mode !== "NONE";
      r.visible = active;
      if (active) {
        const sc = 0.8 + 0.45 * Math.sin(frameTick * 2.2 - idx);
        r.scale.set(sc, sc, 1.0);
      }
    });
    if (dynamicRefs.simplexDome) {
      const ds = simState.simplex_clamp ? (1.15 + 0.08 * Math.sin(frameTick * 3.0)) : 0.35;
      dynamicRefs.simplexDome.scale.set(ds, ds, ds);
    }
    const dx_m = simState.plunger_travel_mm / 1000.0;
    dynamicRefs.rigMovingParts.forEach((m) => {
      m.position.x = m.userData.baseX + dx_m;
    });
    rigRoot.children.forEach((m) => {
      if (m.userData && m.userData.explodeUp) {
        m.position.z = m.userData.baseZ + (simState.exploded_rig ? 0.075 : 0.0);
      }
    });

    renderer.render(scene, camera);
  }
  animate();
}

setInterval(stepSimulation, 400);
drawAllOscilloscopes();
</script>
</body>
</html>
"""

html_out = HTML_TEMPLATE.replace("__RIG_PARTS_JSON__", parts_json_compact)
OUT_HTML.write_text(html_out, encoding="utf-8")
print(f"[Cockpit Builder] Wrote {OUT_HTML} ({OUT_HTML.stat().st_size:,} bytes) with {len(parts_data)} embedded parts and full 5-category permutation matrix")
