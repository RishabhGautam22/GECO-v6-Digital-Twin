from pathlib import Path
import json,hashlib,html,csv
R=Path(__file__).resolve().parents[1];O=R/'00_START_HERE';O.mkdir(exist_ok=True)
readme='''# GECOv6 — complete research and saline-twin package

Start with **OPEN_PACKAGE.html** for the paper, presentation, narrated rig tour, measured-data handoff and reproducibility records. This is a private working research release dated 7 September 2026. Earlier releases remain preserved.

## What changed and what the findings mean

The prediction/filter and calibration implementation has been repaired and tested. The fresh comparison uses 31 evaluable participants and 77,110 matched thirty-minute prediction pairs from the supplied records. A trend or persistence forecast selected before final testing was more accurate than the mechanistic candidate on these records. This is an internal evaluation of previously exposed data, not new external validation. Two records were excluded under declared rules and one failed explicitly because supplied insulin entries were negative.

The intervention experiments contain **7,232 completed simulations**: 4,608 primary fixed-request runs, 576 feedback/stop-model sensitivity runs, and 2,048 separately declared exploratory fasting runs. Calibration and clean-reference attempts are recorded separately. No failed attempt was silently removed. The full monitor did not show consistent superiority over simpler alternatives. Extra stopping can create extra withheld delivery. The original Hovorka branch exceeded its physiological domain in many primary runs; those outcomes remain visible. The fasting supplement passed the declared domain screens but retained action clamps, nuisance stops and condition-dependent benefits and costs.

The defensible paper direction is a **simulation and methods contribution**: an auditable evidence chain, fair intervention comparisons, explicit model limits and an objective water/saline measurement protocol. The work does not establish a physically accurate flowmeter, physical flow cessation or clinical safety. Hardware is not automatically required to submit a simulation paper; physical claims require physical evidence.

## Main deliverables

| Deliverable | Location |
|---|---|
| IEEE-style manuscript, 10 pages | `04_PAPER/GECOv6_Manuscript.pdf` |
| Editable Word companion, 15 rendered pages | `04_PAPER/GECOv6_Manuscript.docx` |
| Manuscript, LaTeX, bibliography, three figures | `04_PAPER/` |
| 49-slide editable presentation, nine embedded movies | `05_PRESENTATION/GECOv6_Research_Seminar.pptx` |
| Static presentation PDF and presenter script | `05_PRESENTATION/` |
| Eight-minute narrated rig tour and fourteen chapter clips | `06_RIG_AND_MEDIA/videos/` |
| Ten corrected, fixed-example simulation movies | `06_RIG_AND_MEDIA/videos/results/` |
| Ten high-resolution rig views; Blender/GLB/OpenSCAD sources | `06_RIG_AND_MEDIA/stills/`, `native/` |
| Interactive rig and exact trace players | `06_RIG_AND_MEDIA/Interactive_Rig/`, `Result_Player/` |
| IIT Patna protocol, M01–M16 fields and blank acquisition templates | `07_IIT_PATNA_HANDOFF/` and `04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md` |
| All frozen studies, raw traces, tables and independent checks | `03_EXPERIMENTS/`, `08_REVIEW_AND_QA/` |
| Portable restoration and reproduction guide | `09_REPRODUCIBILITY/REPRODUCE_EXPERIMENTS.md` |
| Preserved prior complete private release | `10_PRIOR_RELEASE/` |
| User-provided reference protocols and adaptation records | `11_USER_REFERENCE_PROTOCOLS/` |

## Presenting the work

In PowerPoint Slide Show, navigate to a video slide, press **Tab**, then **Enter** to activate its embedded video. Videos are configured for full-screen playback. If a viewer does not support embedded media, use the identically sourced standalone MP4. The PDF contains static posters. The full tour has a real synthetic-speech audio track and optional embedded English subtitles; result movies have no narration. Scripts and separate subtitle files are included.

Use the 10-minute route for decisions: slides 1–5, 8–10, 17–22, 38, 41–43; select rather than rush every slide. Use the 30-minute route for a methods seminar: slides 1–23, one result movie, rig slides 28 and 30–40, then conclusions. For a laboratory briefing, play the full tour on slide 29 and walk through the M01–M16 checklist. The routes are suggested running orders, not pre-recorded talk durations. Detailed speaker notes explain each slide.

## What IIT Patna will fill

The manuscript and presentation place pale-amber **IIT Patna measurement pending** blocks beside the physical claims. The team must supply the as-built apparatus, outlet/measurand definition, calibration and reference evidence, signed mass reconstruction, temperature/density and environmental corrections, clock alignment, stop latency, residual flow, nuisance/missed events and recovery. Replace pending values only after the raw record, method, uncertainty and independent review exist. Blank templates contain no fabricated measurements.

The acquisition validator checks an offline data contract. It neither validates instrument accuracy nor operates a pump. The native 3D geometry is illustrative, not a vendor drawing or fabrication-ready certified design. Physical reconstruction remains to be fitted and independently validated using the team's measurements.

## Publication and provenance

The paper is prepared for team review in IEEE style. Authors, affiliations, contributions, funding/conflicts and final human approval remain for the actual team. A selected IEEE venue can impose additional requirements; no publication acceptance, IEEE/MIT endorsement or affiliation is claimed.

AI-assisted research, code, text and visual production are disclosed. Narration uses the local macOS Aman synthetic voice. The supplied protocols were applied in scientific-first order, preserving numerical and citation integrity. A bounded local exact-overlap check is included; it is not a comprehensive plagiarism certification. No AI-free, SynthID-free or detector-evasion guarantee is claimed.

The prior release and supplied participant/reference material are retained for the requested private all-in-one handoff. Their inclusion does not grant new redistribution rights. Consult the bundled source/license records before public release; submit only the authorized manuscript and appropriate supplement, not the entire private archive by default.

## Reproducibility and integrity

The package contains exact primary and supplemental source snapshots, portable restoration tools, configurations, parameter vectors, seeds, failure/disposition records and raw traces. The current legacy entry points received additional causal timing repairs after the completed study; preserved campaign sources reproduce the exact executed studies. **103 implementation tests** and **7 offline acquisition-contract tests** passed in their recorded environments. Independent review checked all 7,232 simulation traces and core outcomes.

The final manifest lists every shipped payload file and SHA-256. The ZIP is verified against that manifest. Build scratch folders, caches and temporary render masters are excluded. Native source projects plus final media are retained. See `09_REPRODUCIBILITY/REPRODUCE_ARTIFACTS.md` for rebuilding documents and media.
'''
(O/'START_HERE.md').write_text(readme)
(R/'README.md').write_text('# GECOv6\n\nOpen [the package guide](00_START_HERE/START_HERE.md) or [the visual index](00_START_HERE/OPEN_PACKAGE.html).\n\nIEEE-style simulation/methods release. Physical IIT Patna measurements are visibly pending.\n')
parts=json.loads((R/'06_RIG_AND_MEDIA/native/COMPONENTS.json').read_text())['parts']
chapter=json.loads((R/'06_RIG_AND_MEDIA/Interactive_Rig/chapters.json').read_text())
header='''# Rig components and direction for the presentation

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
'''
rows='\n'.join('| '+str(p['id'])+' | '+str(p['role']).replace('|','/')+' |' for p in parts)
chap='\n\n## Narrated chapter map\n\n| Chapter | Start | Topic | Objective check |\n|---|---|---|---|\n'+'\n'.join(f"| {c['id']} | {int(c['start_seconds'])//60:02}:{int(c['start_seconds'])%60:02} | {c['title']} | {c['measured_quantity']} |" for c in chapter)
(R/'06_RIG_AND_MEDIA/COMPONENT_HANDBOOK_AND_DIRECTION.md').write_text(header+rows+chap+'\n')
(R/'06_RIG_AND_MEDIA/README.md').write_text('''# Media and native players

The full narrated film is `videos/GECOv6_Rig_Explained.mp4` (1920×1080, 24fps, approximately8min). Fourteen exact narrated chapter excerpts are in `videos/chapters`. Ten fixed-example48h simulation playbacks are in `videos/results`, each55.04s. All are separately viewable, without PowerPoint or a 3D application.

The full rig film contains AAC audio and an optional English subtitle track. `narration/FINAL_TRANSCRIPT.md`, `.srt` and the lossless `.wav` preserve the spoken material. Subtitle timing is sentence-weighted and approximate. The voice is macOS Aman; there is no claim of human narration. Result movies have no audio by design. Their plots use saved five-minute observations and a complete576-sample horizon; no intermediate measurements are synthesized.

`native/GECOv6_Rig_Concept.blend` is the Blender source, `.glb` is the exchange scene, `.scad` is illustrative geometry, and COMPONENTS.json binds parts to names and coordinates. Ten final stills are included. The conceptual feet in OpenSCAD were aligned to the expanded base after an independent export consistency check; native Blender and GLB placements already matched it. This is not a fabrication drawing.

Open `Interactive_Rig/project.godot` or `Result_Player/project.godot` in Godot4.7.2 (Compatibility renderer). Import local assets when prompted, then run the project. Rig controls: chapter selector, Space play/pause, Left/Right chapters, Home restart. Result controls: case selector, sample slider, Space play/pause, Left/Right five-minute steps, Home restart. All ten result examples and raw arrays are bundled locally. These are offline viewers, not pump-control software.

Each evidence claim has a boundary: a render illustrates geometry; a replay displays numerical results; only future calibrated physical records support actual measurement and stopping estimates. Refer to COMPONENT_HANDBOOK_AND_DIRECTION.md and the IIT Patna handoff.
''')
(R/'05_PRESENTATION/README.md').write_text('''# Presentation

Open GECOv6_Research_Seminar.pptx:49 slides,19 editable native tables, one editable chart with an embedded numerical workbook, six editable flow diagrams, complete speaker notes and nine embedded movies. The Static.pptx and PDF are poster editions. The base.pptx is retained as a reproducible intermediate before media packaging.

In Slide Show, select a video slide and press Tab, then Enter. Full-screen playback is configured. Use standalone MP4 files if a viewer lacks media support. The four example result movies, full narrated tour and four narrated chapter clips are embedded with byte-identical standalone files. The eight-minute tour is slide29; detailed script and route guidance are in PRESENTER_SCRIPT.md and the package guide.

All physical sections carry the text “IIT Patna measurement pending” with amber fill. Forecast and intervention estimates are simulation/internal-data findings with explicit source paths and hashes in notes. Main paper results are reproduced without converting domain failures to favorable outcomes.
''')
(R/'09_REPRODUCIBILITY/REPRODUCE_ARTIFACTS.md').write_text('''# Rebuild the paper, presentation and media

Run rebuilds in a copy of GECOv6 so the released hashes remain immutable. Sources and final artifacts are bundled; platform runtimes are prerequisites rather than copied applications.

## Paper

`04_PAPER/paper_build.py` builds the IEEEtran manuscript and editable Word companion from the markdown, bibliography and figure sources. The delivered environment used TeXLive2025 (IEEEtran), Pandoc, ReportLab, python-docx, pypdf and the bundled LibreOffice. Read the script's explicit runtime paths and set them for the local installation before running. This is an artifact-production script, not an experimental result generator. Re-render every page and compare numerical/reference checks in `08_REVIEW_AND_QA/paper` after a change.

## Presentation

`tools/prepare_presentation.py` reads exact source result files and creates SLIDE_CONTENT.json and the presenter script. The chart values are rounded to6decimalplaces for the editable workbook; source estimates remain unrounded. `09_REPRODUCIBILITY/build_presentation.mjs` builds native content with @oai/artifact-tool, native tables/charts and editable flow shapes. Set RUNTIME_NODE_MODULES to that dependency installation and GECO_PRESENTATION_SKILL_DIR to the installed presentation skill directory containing its finalization helpers. The delivered build used the application's bundled Node runtime and Arial.

After the base file passes structural/native-chart checks, run `tools/embed_presentation_media.py` to package the existing MP4 bytes and full-screen media timing. Run `tools/export_static_presentation.py --soffice /path/to/soffice` for the static PDF. Final packaging checks are separate from native PowerPoint playback. The full-screen OOXML property is documented by Microsoft: https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.presentation.video.fullscreen?view=openxml-3.0.1 .

## Rig and motion

`tools/rig_foundation.py` and `tools/build_rig.py` create native concept geometry and stills under Blender5.1.1. The delivered stills used Cycles40samples, denoising and Metal. Paths are derived from the package, but Blender/Godot/ffmpeg executable paths in production helpers must be adapted for another platform. The `.blend`, `.glb`, `.scad`, component inventory and exact camera receipt are retained.

`tools/build_rig_narration.py` creates synthetic speech with macOS say/Aman155words/min; voice availability is platform-specific. The measured final narration, transcript, subtitles and all chapter WAV files are already included. `tools/build_rig_player.py` creates the Godot rig viewer, and `tools/build_result_player.py` creates the numerical viewer from frozen compressed traces.

For deterministic movie creation, use Godot4.7.2 Compatibility with `--fixed-fps 24 --write-movie` and the project's `--movie` option. Produce only one native movie writer at a time. The result helper `tools/render_result_movies.py` renders all ten cases, or selected zero-based case indices. It encodes H264 MP4 and extracts start/fault/end images. Duration alone is insufficient: inspect the actual final frame for sample576. `tools/finalize_media.py` validates the rig movie streams and makes fourteen chapter clips.

Record new output hashes and run visual checks after a rebuild. Do not report byte-identical media across machines unless actually verified; GPU rendering, fonts and speech runtimes can differ. Numerical source arrays are immutable inputs, and movie interpolation creates no new measurements.
''')
# Browser index uses relative file links and native video controls; no external scripts or network requests.
links=[('Read the IEEE paper','04_PAPER/GECOv6_Manuscript.pdf','10 pages · methods, findings and pending measurements'),('Edit the manuscript','04_PAPER/GECOv6_Manuscript.docx','Editable Word companion · equations and tables'),('Present the study','05_PRESENTATION/GECOv6_Research_Seminar.pptx','49 slides · nine embedded videos'),('Read the slide PDF','05_PRESENTATION/GECOv6_Research_Seminar.pdf','Static posters · portable reading'),('Use the laboratory handoff','07_IIT_PATNA_HANDOFF/ACQUISITION_AND_MEASUREMENT_PROTOCOL.md','Objective measurements and data contract'),('Reproduce the experiments','09_REPRODUCIBILITY/REPRODUCE_EXPERIMENTS.md','Frozen sources, inputs, seeds and exact commands')]
cards=''.join(f'<a class="card" href="../{p}"><b>{t}</b><span>{d}</span></a>' for t,p,d in links)
opts=''.join(f'<option value="../06_RIG_AND_MEDIA/videos/chapters/GECOv6_Rig_{c["id"]}.mp4">{c["id"]} — {html.escape(c["title"])}</option>' for c in chapter)
cases=json.loads((R/'06_RIG_AND_MEDIA/Result_Player/cases.json').read_text())
family_labels={'geco_original':'Original model','hovorka_2004':'Hovorka model'}
condition_labels={'clean':'No injected fault','excess_2x':'Doubled actuator command','stuck_on':'Stuck-on delivery','cgm_missing':'Missing glucose report','excess_bias_report_mask':'Excess delivery, biased glucose and masked mass report'}
ropts=''.join(f'<option value="../06_RIG_AND_MEDIA/videos/results/GECOv6_{c["id"]}.mp4">{html.escape(family_labels[c["family"]]+" / "+condition_labels[c["condition"]])}</option>' for c in cases)
page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>GECOv6 research package</title><style>body{margin:0;background:#f1f5f6;color:#142f40;font:17px/1.55 Arial,sans-serif}main{max-width:1120px;margin:auto;padding:45px 24px}h1{font-size:46px;line-height:1.1;margin:12px 0}h2{margin-top:40px}p{max-width:940px}.eyebrow{letter-spacing:.12em;color:#147b7c;font-size:13px;font-weight:bold}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}.card{background:white;border:1px solid #ccdadd;border-radius:9px;padding:20px;color:inherit;text-decoration:none;display:block}.card b{display:block;font-size:22px}.card span{color:#526a76;display:block;margin-top:7px}.pending{background:#fff2cc;border-left:5px solid #b28719;padding:15px 20px}.stats{display:flex;gap:25px;flex-wrap:wrap;margin:25px 0}.stats b{font-size:32px;display:block}.stats span{font-size:14px;color:#526a76}video{width:100%;background:#081623;border-radius:6px;max-height:670px}select{font:inherit;width:100%;padding:10px;margin:8px 0 15px}a{color:#08787a}.muted{font-size:14px;color:#526a76}footer{border-top:1px solid #ccdadd;margin-top:40px;padding-top:20px;font-size:14px}</style><main><div class="eyebrow">GECOv6 / COMPLETE RESEARCH RELEASE / 7 SEPTEMBER 2026</div><h1>From permission to delivery evidence</h1><p>A corrected simulation study, an IEEE-style manuscript and a detailed plan for the IIT Patna saline twin. Start with the findings, then inspect how each claim is supported.</p><div class="stats"><div><b>7,232</b><span>completed intervention simulations</span></div><div><b>31</b><span>evaluated participant records</span></div><div><b>49</b><span>presentation slides</span></div><div><b>8 min</b><span>narrated rig explanation</span></div></div><div class="pending"><b>IIT Patna measurement pending</b><br>The rig is conceptual. Actual delivery accuracy, clock alignment, physical stopping, residual fluid and recovery await calibrated laboratory records.</div><h2>Choose your starting point</h2><div class="grid">'''+cards+'''</div><h2>The findings in ordinary language</h2><p>Simpler forecast choices performed better on the supplied records. A more complex monitor was not consistently better at balancing extra delivery against withheld delivery. The primary second-model branch had important physiological-domain failures. A separate fasting study removed those declared failures but still found benefits, costs and false stops. The paper makes a bounded simulation and methods claim.</p><p><a href="START_HERE.md">Read the complete release guide</a> · <a href="../08_REVIEW_AND_QA/FIX_COMPLETION_MATRIX.md">See the fix completion matrix</a></p><h2>Watch the complete rig explanation</h2><video controls preload="metadata" poster="../06_RIG_AND_MEDIA/stills/rig_overview.png" src="../06_RIG_AND_MEDIA/videos/GECOv6_Rig_Explained.mp4"></video><p class="muted">Concept render with disclosed synthetic narration. Use the full-screen control for component labels. English subtitles are available in the MP4 and as a separate SRT.</p><h2>Explore individual chapters</h2><select id="chapter" aria-label="Choose a narrated chapter">'''+opts+'''</select><video id="chapterPlayer" controls preload="none" src="../06_RIG_AND_MEDIA/videos/chapters/GECOv6_Rig_C01.mp4"></video><h2>Inspect the fixed simulation examples</h2><p>These cases were selected before outcome inspection. Each movie retains the full 48-hour numerical follow-up, excess, deficit, recovery state and domain flags. They are illustrative cases, not aggregate evidence.</p><select id="result" aria-label="Choose a result movie">'''+ropts+'''</select><video id="resultPlayer" controls preload="none" src="../06_RIG_AND_MEDIA/videos/results/GECOv6_geco_original__clean.mp4"></video><p><a href="../06_RIG_AND_MEDIA/COMPONENT_HANDBOOK_AND_DIRECTION.md">Component handbook and video direction</a> · <a href="../05_PRESENTATION/PRESENTER_SCRIPT.md">Presenter script</a> · <a href="../04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md">M01–M16 measurement matrix</a></p><footer>Private working handoff. AI assistance and synthetic voice are disclosed. No clinical validation, publication acceptance, AI-free or watermark certification is asserted. Source/license and review receipts are included. This index uses local files only.</footer></main><script>for(const [s,v]of [['chapter','chapterPlayer'],['result','resultPlayer']])document.getElementById(s).addEventListener('change',e=>{const p=document.getElementById(v);p.pause();p.src=e.target.value;p.load()});</script></html>'''
(O/'OPEN_PACKAGE.html').write_text(page)
print('Release guide, local media index, complete component handbook and artifact rebuild notes written')
