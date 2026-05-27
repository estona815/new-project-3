# REAPER SETUP

1. Open REAPER resource path: `Options > Show REAPER resource path`.
2. Copy `05_JSFX/*.jsfx` into the `Effects` folder.
3. Restart REAPER or rescan JSFX.
4. Open the project to process.
5. Name tracks clearly: `lead vocal`, `female adlib`, `beat`, `drums`, `808`, `melody`.
6. Run `04_REAPER_AUTOMATION/apply_policy_to_reaper.lua`.
7. Render with `04_REAPER_AUTOMATION/render_versions.lua` or your existing deterministic render wrapper.

Reference/full-mix tracks must stay muted and out of the active premaster bus.
