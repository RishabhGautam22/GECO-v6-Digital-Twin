# Media and native players

The full narrated film is `videos/GECOv6_Rig_Explained.mp4` (1920×1080, 24fps, approximately8min). Fourteen exact narrated chapter excerpts are in `videos/chapters`. Ten fixed-example48h simulation playbacks are in `videos/results`, each55.04s. All are separately viewable, without PowerPoint or a 3D application.

The full rig film contains AAC audio and an optional English subtitle track. `narration/FINAL_TRANSCRIPT.md`, `.srt` and the lossless `.wav` preserve the spoken material. Subtitle timing is sentence-weighted and approximate. The voice is macOS Aman; there is no claim of human narration. Result movies have no audio by design. Their plots use saved five-minute observations and a complete576-sample horizon; no intermediate measurements are synthesized.

`native/GECOv6_Rig_Concept.blend` is the Blender source, `.glb` is the exchange scene, `.scad` is illustrative geometry, and COMPONENTS.json binds parts to names and coordinates. Ten final stills are included. The conceptual feet in OpenSCAD were aligned to the expanded base after an independent export consistency check; native Blender and GLB placements already matched it. This is not a fabrication drawing.

Open `Interactive_Rig/project.godot` or `Result_Player/project.godot` in Godot4.7.2 (Compatibility renderer). Import local assets when prompted, then run the project. Rig controls: chapter selector, Space play/pause, Left/Right chapters, Home restart. Result controls: case selector, sample slider, Space play/pause, Left/Right five-minute steps, Home restart. All ten result examples and raw arrays are bundled locally. These are offline viewers, not pump-control software.

Each evidence claim has a boundary: a render illustrates geometry; a replay displays numerical results; only future calibrated physical records support actual measurement and stopping estimates. Refer to COMPONENT_HANDBOOK_AND_DIRECTION.md and the IIT Patna handoff.
