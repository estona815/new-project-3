# REAPER Plugin Inventory Scanner

This scanner is the first safe layer for the Reaper-based AutoMix / Auto-FX
Orchestrator. It inventories available tools and existing track FX, then writes a
report for later decision making. It does not mix, tune, render, save, or change user audio.

## Files

- `automix/scan_reaper_plugin_inventory.lua`: REAPER ReaScript scanner.
- `automix/plugin_aliases.lua`: user-editable alias list for local plugin names.
- `automix/plugin_capability_catalog.json`: static reference catalog of target
  families, capability categories, and fallback options.
- `automix/plugin_inventory.json`: generated machine-readable scan output.
- `automix/plugin_inventory_report.md`: generated readable report.

## How To Run

1. Open the target project in REAPER.
2. In REAPER, open `Actions > Show action list...`.
3. Choose `New Action > Load ReaScript...`.
4. Select `automix/scan_reaper_plugin_inventory.lua`.
5. Run the script.
6. Review `automix/plugin_inventory_report.md` before using any result for
   automation.

The generated JSON and Markdown report are overwritten on each scan.

## Safety Model

The script is inventory-only by design:

- It scans all project tracks and marks which tracks are selected.
- It reads existing FX names, enabled/offline state, FX GUID when available,
  channel count, volume, pan, sends, and receives.
- It does not insert FX into original tracks.
- It does not change plugin parameters.
- It does not assume any plugin parameter indexes.
- It does not load presets.
- It does not render.
- It does not save the project.
- It wraps the scan in an undo block.

To check whether a plugin can be inserted, the script creates one temporary muted hidden test track named `__AUTOMIX_PLUGIN_INVENTORY_TEMP_DO_NOT_USE__`,
tries candidate plugin names on that track, records success or failure, deletes
the inserted test FX, then deletes the test track. Original track selection is
restored after probing. If probing fails, cleanup still attempts to delete the
temporary track before reporting the error.

## Fuzzy Matching

Plugin names differ between systems because REAPER may expose formats and vendor
prefixes differently, for example `VST3: MAutoPitch`, `MAutoPitch`, or
`MeldaProduction MAutoPitch`. The scanner normalizes names by:

- stripping common format prefixes such as `VST3:`, `VST:`, `AU:`, and `JS:`;
- comparing case-insensitively;
- checking normalized exact matches;
- checking compact matches with spaces and punctuation removed;
- assigning a confidence score;
- marking close competing matches as ambiguous.

Fuzzy matches are not treated as proof of product identity. Ambiguous or
manual-only plugins must be verified before any later automation uses them.

## Capability Categories

The scanner classifies plugins into these capability buckets:

- `pitch_correction`
- `static_eq`
- `dynamic_eq`
- `resonance_suppressor`
- `compressor`
- `limiter`
- `saturator`
- `multiband_compressor`
- `deesser`
- `reverb`
- `delay`
- `stereo_width`
- `noise_reduction`
- `analyzer`
- `utility`
- `unknown`

Known examples include MAutoPitch, ReaPitch, ReaEQ, TDR Nova, Melda dynamic EQ
variants, Soothe-like and DSEQ-like resonance suppressors, Decapitator,
Saturn-type saturators, ReaComp, ReaXcomp, LA-2A/opto-type compressors,
1176-type compressors, OTT, Valhalla plugins, ReaVerbate, ReaDelay, stock JS
utilities, meters, and limiters.

## User Aliases

Edit `automix/plugin_aliases.lua` to add local names. Keep aliases broad but
honest. Do not place license keys, private paths, account names, or machine
secrets in the alias file.

Alias records support:

- `id`
- `display_name`
- `capabilities`
- `aliases`
- `probe_names`
- `fallback`
- `manual_only`

For unclear product families such as Kolin/Koliv/Kiive/opto-style compressors,
use `manual_only` or treat the match as a capability hint rather than a fixed
plugin identity.

## Generated Output

`plugin_inventory.json` includes:

- scan date in UTC;
- REAPER version when available;
- project name and path;
- project track count and selected track count;
- full per-track FX lists;
- existing detected plugins;
- insertable probe results;
- capability inventory;
- missing recommended capabilities;
- ambiguous matches;
- fallback options;
- explicit safety flags.

`plugin_inventory_report.md` summarizes the same information for review.

## Current Limits

- The scanner cannot enumerate every installed plugin without using REAPER's
  plugin browser internals, so it safely probes a curated candidate list instead.
- A successful insertability probe only means REAPER accepted the queried plugin
  name on the temporary track. It does not mean the plugin is licensed,
  parameter-safe, automatable, or musically appropriate.
- Melodyne-type, Auto-Tune-type, Soothe-like, DSEQ-like, LA-2A-type, 1176-type,
  and vendor-alias matches are detection/manual review signals only unless a
  later safe controller is written and tested.
- This scan is not an audio-quality claim and does not validate any chain.

## Next Safe Step

The next layer may read `plugin_inventory.json` and decide which capabilities
are available, but it should still remain dry-run only until separate automation
scripts prove that every proposed FX insertion and parameter change is safe,
reviewable, and reversible.
