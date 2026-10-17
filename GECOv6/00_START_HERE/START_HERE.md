# GECOv6  -  complete research and saline-twin package

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
| IIT Patna protocol, M01-M16 fields and blank acquisition templates | `07_IIT_PATNA_HANDOFF/` and `04_PAPER/IIT_PATNA_PENDING_MEASUREMENTS.md` |
| All frozen studies, raw traces, tables and independent checks | `03_EXPERIMENTS/`, `08_REVIEW_AND_QA/` |
| Portable restoration and reproduction guide | `09_REPRODUCIBILITY/REPRODUCE_EXPERIMENTS.md` |
| Preserved prior complete private release | `10_PRIOR_RELEASE/` |
| User-provided reference protocols and adaptation records | `11_USER_REFERENCE_PROTOCOLS/` |

## Presenting the work

In PowerPoint Slide Show, navigate to a video slide, press **Tab**, then **Enter** to activate its embedded video. Videos are configured for full-screen playback. If a viewer does not support embedded media, use the identically sourced standalone MP4. The PDF contains static posters. The full tour has a real synthetic-speech audio track and optional embedded English subtitles; result movies have no narration. Scripts and separate subtitle files are included.

Use the 10-minute route for decisions: slides 1-5, 8-10, 17-22, 38, 41-43; select rather than rush every slide. Use the 30-minute route for a methods seminar: slides 1-23, one result movie, rig slides 28 and 30-40, then conclusions. For a laboratory briefing, play the full tour on slide 29 and walk through the M01-M16 checklist. The routes are suggested running orders, not pre-recorded talk durations. Detailed speaker notes explain each slide.

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
