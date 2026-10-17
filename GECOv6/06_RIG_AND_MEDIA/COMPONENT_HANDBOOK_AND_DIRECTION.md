# Rig components and direction for the presentation

All physical components are conceptual. **IIT Patna measurement pending.** Part IDs in the 3D scene (for example mechanical part M03) and measurement-task IDs M01–M16 are separate namespaces: a part label is not a completed measurement task.

The mechanism begins with a motor, coupling and lead screw. The carriage and rails guide the illustrated pusher toward the syringe plunger. The syringe barrel, plunger, outlet connector and tubing define a proposed fluid path through a proposed stop element to a receiver. The drawing does not establish an achievable pressure, displacement, flow, capacity or stop time.

The receiver and balance form the proposed indication path. Tubing support, wetting forces and probe loading can disturb this path; the handoff protocol requires force-isolation tests. Temperature is represented by a separate sample vial, probe and acquisition module. Reference masses have a separate tray. No class, serial number, calibration certificate or accuracy has been invented.

The CGM replay source, gateway, pump endpoint, local monitor, proposed stop/power electronics and independent acquisition computer have different information and authority roles. Blue paths illustrate data, teal illustrates the proposed fluid route, and orange illustrates stop/timing. Animated tokens encode connection direction only. The camera and common event marker support synchronization and observable event recording; they do not automatically produce ground truth flow.

## Direction and audience pacing

Begin with the evidence question, then follow one requested amount through authorization and emission. Pause at the balance to ask what it actually indicates. Introduce calibration, density, temperature and uncertainty before displaying a physical accuracy claim. In the stop chapter, separate detection, electrical disable and outlet cessation. End with recovery and the evidence the laboratory will produce.

Keep the narration and component labels synchronized. Do not add artificial live readings to the scene. Replace the concept view with dated as-built photographs when the team has an actual apparatus. The result movies are a separate evidence class and must retain their simulation/domain labels.

## Complete part inventory

Dimensions and positions are illustrative and available in COMPONENTS.json. The inventory names every modeled part, including supports and repeated components; it is not a purchasing bill of materials.

| Part ID | Modeled role |
|---|---|
| B01 | Bench base |
| B02_30_30 | Isolating foot |
| B02_30_390 | Isolating foot |
| B02_570_30 | Isolating foot |
| B02_570_390 | Isolating foot |
| M01 | Syringe pump base |
| M02_105 | Linear rail |
| M02_183 | Linear rail |
| M03 | Motor |
| M04 | Flexible coupling |
| M05 | Lead screw |
| M05t_114 | Illustrative screw ridge |
| M05t_118 | Illustrative screw ridge |
| M05t_122 | Illustrative screw ridge |
| M05t_126 | Illustrative screw ridge |
| M05t_130 | Illustrative screw ridge |
| M05t_134 | Illustrative screw ridge |
| M05t_138 | Illustrative screw ridge |
| M05t_142 | Illustrative screw ridge |
| M05t_146 | Illustrative screw ridge |
| M05t_150 | Illustrative screw ridge |
| M05t_154 | Illustrative screw ridge |
| M05t_158 | Illustrative screw ridge |
| M05t_162 | Illustrative screw ridge |
| M05t_166 | Illustrative screw ridge |
| M05t_170 | Illustrative screw ridge |
| M05t_174 | Illustrative screw ridge |
| M05t_178 | Illustrative screw ridge |
| M05t_182 | Illustrative screw ridge |
| M05t_186 | Illustrative screw ridge |
| M05t_190 | Illustrative screw ridge |
| M05t_194 | Illustrative screw ridge |
| M05t_198 | Illustrative screw ridge |
| M05t_202 | Illustrative screw ridge |
| M05t_206 | Illustrative screw ridge |
| M05t_210 | Illustrative screw ridge |
| M05t_214 | Illustrative screw ridge |
| M05t_218 | Illustrative screw ridge |
| M05t_222 | Illustrative screw ridge |
| M05t_226 | Illustrative screw ridge |
| M05t_230 | Illustrative screw ridge |
| M05t_234 | Illustrative screw ridge |
| M05t_238 | Illustrative screw ridge |
| M05t_242 | Illustrative screw ridge |
| M05t_246 | Illustrative screw ridge |
| M05t_250 | Illustrative screw ridge |
| M05t_254 | Illustrative screw ridge |
| M05t_258 | Illustrative screw ridge |
| M05t_262 | Illustrative screw ridge |
| M05t_266 | Illustrative screw ridge |
| M05t_270 | Illustrative screw ridge |
| M05t_274 | Illustrative screw ridge |
| M05t_278 | Illustrative screw ridge |
| M05t_282 | Illustrative screw ridge |
| M05t_286 | Illustrative screw ridge |
| M05t_290 | Illustrative screw ridge |
| M05t_294 | Illustrative screw ridge |
| M05t_298 | Illustrative screw ridge |
| M05t_302 | Illustrative screw ridge |
| M05t_306 | Illustrative screw ridge |
| M05t_310 | Illustrative screw ridge |
| M05t_314 | Illustrative screw ridge |
| M06 | Lead screw end bearing |
| M07 | Carriage |
| M08 | Plunger pusher |
| M09_215 | Syringe cradle |
| M10_215 | Cradle top saddle |
| M09_284 | Syringe cradle |
| M10_284 | Cradle top saddle |
| S01 | Syringe barrel |
| S02 | Fluid inside barrel |
| S03 | Plunger seal |
| S04 | Plunger rod |
| S05 | Plunger flange |
| S06 | Syringe finger flange |
| S07 | Outlet fitting |
| S08_198 | Illustrative graduation |
| S08_206 | Illustrative graduation |
| S08_214 | Illustrative graduation |
| S08_222 | Illustrative graduation |
| S08_230 | Illustrative graduation |
| S08_238 | Illustrative graduation |
| S08_246 | Illustrative graduation |
| S08_254 | Illustrative graduation |
| S08_262 | Illustrative graduation |
| S08_270 | Illustrative graduation |
| S08_278 | Illustrative graduation |
| V01 | Proposed pinch valve |
| V02 | Valve mounting foot |
| T01 | Balance enclosure |
| T02 | Balance pan |
| T03 | Balance display |
| R01 | Receiving vessel |
| R02 | Saline in receiver |
| F01 | Continuous saline path |
| T04 | Independent monitor |
| T05 | Monitor PCB |
| T06 | Trip driver |
| G01 | Gateway host |
| P01 | Pump endpoint PCB |
| P02 | Stepper driver |
| C01 | CGM emulator |
| E01 | Isolated supply concept |
| W01 | Conceptual electrical connection |
| W02 | Conceptual electrical connection |
| W03 | Conceptual electrical connection |
| W04 | Conceptual electrical connection |
| W05 | Conceptual electrical connection |
| W06 | Conceptual electrical connection |
| L01 | Independent acquisition computer |
| L02 | Acquisition screen frame |
| L03 | Acquisition screen |
| L04_0 | Keyboard row |
| L04_1 | Keyboard row |
| L04_2 | Keyboard row |
| L04_3 | Keyboard row |
| D01 | Temperature acquisition module |
| D02 | Temperature probe in separate sample |
| D04 | Separate temperature sample vial |
| D05 | Temperature sample fluid |
| D03 | Probe lead |
| A01 | Reference camera post |
| A02 | Reference camera foot |
| A03 | Reference camera body |
| A04 | Reference camera lens |
| A05 | Clock marker module |
| A06 | Clock marker light |
| K01 | Reference mass selection pending |
| K11 | Reference mass handle |
| K02 | Reference mass selection pending |
| K12 | Reference mass handle |
| K03 | Reference mass selection pending |
| K13 | Reference mass handle |
| K20 | Reference mass tray |
| W07 | Replay data connection |
| W08 | Measurement record connection |
| W09 | Timestamp reference connection |
| B03 | Render backdrop |

## Narrated chapter map

| Chapter | Start | Topic | Objective check |
|---|---|---|---|
| C01 | 00:00 | What this bench is meant to establish | Outlet mass or volume over a defined interval; pending |
| C02 | 00:31 | Follow the command and the evidence | Requested/authorized/accepted model amount and timestamp; physical delivery pending |
| C03 | 01:06 | What the gateway can and cannot establish | Command acceptance, message timing and policy state; device tests pending |
| C04 | 01:39 | From motor motion to carriage motion | Carriage displacement and repeatability; pending |
| C05 | 02:16 | The syringe and the fluid path | Outlet-delivery profile versus displacement; pending |
| C06 | 02:50 | The receiver and balance | Balance indication in g, blank drift and settling; pending |
| C07 | 03:23 | Calibration before comparison | Calibration response, repeatability and uncertainty; pending |
| C08 | 03:59 | Temperature and mass-to-volume conversion | Temperature, density and corrected volume; pending |
| C09 | 04:33 | One synchronized record | Synchronization offset, jitter, latency and missing samples; pending |
| C10 | 05:07 | Reconstruct delivery without an oracle | Reconstruction error, zero-flow bias and temporal uncertainty; pending |
| C11 | 05:39 | Detection and the proposed stop path | Detection delay, stop latency and post-stop flow; pending |
| C12 | 06:15 | Recovery belongs in the experiment | Withheld delivery, restart delay, nuisance stops and overshoot; pending |
| C13 | 06:49 | Compare methods under the same conditions | Matched excess, deficit, interruption and recovery in simulation |
| C14 | 07:24 | The next evidence comes from the laboratory | All M01–M16 fields remain unmeasured |
