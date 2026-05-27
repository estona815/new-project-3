# REAPER Runner Blueprint

This is a main-computer-only execution plan. Do not run REAPER automation on a public PC.

Future steps:

1. Detect REAPER path.
2. Detect REAPER resource path.
3. Back up REAPER settings and resource folder.
4. Verify SWS, ReaPack, js_ReaScriptAPI, ReaImGui, and plugin availability.
5. Scan plugins manually in REAPER.
6. Load or create the Suno vocal repair project template.
7. Create source, candidate, parallel blend, metering, and render tracks.
8. Apply FX chain from approved plugin capability matrix.
9. Render candidates A/B/C/D to `local_only/renders/`.
10. Export render manifest and QC reports.
11. Stop before real final export unless the user approves the winning candidate.

