# Cloud & Local Launch Guide

This guide covers running both Insulin Pump Digital Twin projects on a cloud GPU instance (Runpod, AWS EC2 G5/G6, Azure, or GCP) or a local Linux workstation with NVIDIA Isaac Sim 6.1.0.

---

## 1. Repositories

- **Project 1 (IIT Patna Single-Patient Insulin Pump Digital Twin)**
  `https://github.com/RishabhGautam22/Insulin-Pump-Digital-Twin`
- **Project 2 (GECO v6 12-Cubicle Smart Hospital Ward Digital Twin)**
  `https://github.com/RishabhGautam22/GECO-v6-Digital-Twin`

---

## 2. Cloud GPU Instance Requirements

- **GPU**: NVIDIA RTX A6000 (48 GB), RTX 4090 (24 GB), L40S (48 GB), or A40 (48 GB) with RT Cores enabled.
- **OS & Driver**: Ubuntu 22.04 or 24.04 LTS with NVIDIA Driver `>= 535.x`.
- **Exposed Ports**:
  - `6080` (TCP): Browser-accessible XFCE4 + VirtualGL desktop (`noVNC`) for full 3D Isaac Sim RTX rendering.
  - `8080` (TCP): Browser-accessible HTML dashboards (`iitp_dashboard.html` and `GECO_v6_Max_Cockpit.html`).
  - `8765` (TCP): Project 1 WebSocket telemetry server.
  - `8766` (TCP): Project 2 WebSocket telemetry server.

---

## 3. Deploying on Runpod or Cloud GPU

### Step 1: Clone the Repositories
```bash
mkdir -p /workspace/insulin_twins && cd /workspace/insulin_twins
git clone https://github.com/RishabhGautam22/Insulin-Pump-Digital-Twin.git
git clone https://github.com/RishabhGautam22/GECO-v6-Digital-Twin.git
```

### Step 2: Install Dependencies & Isaac Sim
```bash
pip install numpy scipy pandas matplotlib websockets torch pytest
```
If Isaac Sim is not yet installed on the cloud volume, install it into `/workspace/isaacsim` using the official NVIDIA package or `cloud_deployment/deploy_runpod_cloud.sh`.

### Step 3: Start the Telemetry Servers, Dashboards & Paper Export Pipelines

#### Project 1 (IIT Patna Digital Twin)
```bash
cd /workspace/insulin_twins/Insulin-Pump-Digital-Twin
python3 -m reporting.paper_report_generator
python3 digital_twin_server.py &
```

#### Project 2 (GECO v6 12-Cubicle Ward Digital Twin)
```bash
cd /workspace/insulin_twins/GECO-v6-Digital-Twin/GECO_v6_Max_Omniverse_Twin
python3 omniverse_usd/build_usd_stages.py
python3 -m geco_v6_max.paper_report_generator
python3 -m geco_v6_max.ward_telemetry_server &
```

#### Serve the Large-Screen Web Dashboards on Port 8080
```bash
cd /workspace/insulin_twins
python3 -m http.server 8080 --bind 0.0.0.0 &
```
- **Project 1 Dashboard**: `http://<CLOUD_IP_OR_PROXY>:8080/Insulin-Pump-Digital-Twin/dashboard/iitp_dashboard.html`
- **Project 2 Dashboard**: `http://<CLOUD_IP_OR_PROXY>:8080/GECO-v6-Digital-Twin/GECO_v6_Max_Omniverse_Twin/cockpit/GECO_v6_Max_Cockpit.html`

---

## 4. Staging & Publishing OpenUSD Models to Omniverse Nucleus

Both repositories include automated OpenUSD asset packagers that resolve relative paths (`@./...@`) and stage self-contained USD bundles ready for `omniverse://<nucleus-host>/Projects/...`:

```bash
# Stage Project 1 USD bundle
cd /workspace/insulin_twins/Insulin-Pump-Digital-Twin
python3 cloud_deployment/upload_to_nucleus.py --mode stage-only

# Stage Project 2 USD bundle (138-part rig + 12-cubicle ward + BRep CAD)
cd /workspace/insulin_twins/GECO-v6-Digital-Twin
python3 cloud_deployment/upload_geco_v6_to_nucleus.py --mode stage-only
```
To push directly to an active Omniverse Nucleus server, replace `--mode stage-only` with `--mode nucleus --nucleus-server omniverse://<YOUR_NUCLEUS_HOST>/Projects/IITPatna/InsulinPumpDT`.
