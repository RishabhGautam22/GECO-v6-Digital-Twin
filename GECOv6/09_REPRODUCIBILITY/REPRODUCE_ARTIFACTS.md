# Rebuild the paper, presentation and media

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
