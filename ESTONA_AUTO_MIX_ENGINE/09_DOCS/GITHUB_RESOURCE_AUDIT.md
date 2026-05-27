# GitHub Resource Audit

Audit date: 2026-05-25
Search method: GitHub CLI search/repo metadata plus shallow clone for selected repos.
Repos searched/reviewed: 29. Repos cloned: 9. Clone root: `00_EXTERNAL_REFS/`.

No external code is copied into ESTONA by default. GPL/LGPL repos are study-only unless a separate license review approves integration.

## Clone Summary

- `ReaTeam/JSFX` -> `00_EXTERNAL_REFS/reaper_jsfx/ReaTeam_JSFX`
- `ReaTeam/ReaScripts` -> `00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts`
- `ReaTeam/ReaScripts-Templates` -> `00_EXTERNAL_REFS/reaper_lua/ReaTeam_ReaScripts_Templates`
- `X-Raym/REAPER-ReaScripts` -> `00_EXTERNAL_REFS/reaper_lua/X-Raym_REAPER_ReaScripts`
- `sergree/matchering` -> `00_EXTERNAL_REFS/reference_matching/sergree_matchering`
- `librosa/librosa` -> `00_EXTERNAL_REFS/python_audio_analysis/librosa`
- `csteinmetz1/pyloudnorm` -> `00_EXTERNAL_REFS/python_audio_analysis/pyloudnorm`
- `spotify/pedalboard` -> `00_EXTERNAL_REFS/python_audio_analysis/pedalboard`
- `airwindows/airwindows` -> `00_EXTERNAL_REFS/dsp_reference/airwindows`

## Repo Notes

### ReaTeam/JSFX
- repo_name: ReaTeam/JSFX
- purpose: Community JSFX examples for REAPER.
- url: https://github.com/ReaTeam/JSFX
- license: NOASSERTION at repo level; per-file provenance must be checked.
- language: JSFX/Ruby index
- last_updated: 2026-05-12
- relevance_score: 5
- use_type: study_only
- useful_files: `Dynamic/*Clipper*.jsfx`, `Distortion/*`, JSFX `slider/@init/@slider/@sample/@gfx` patterns.
- applicable_to_estona_engine: JSFX slider naming, meter UI, soft clipper structure, sub/bass split examples.
- risks: no single root LICENSE found; do not copy DSP code directly.
- next_action: keep ESTONA JSFX original, borrow only packaging/style conventions.

### ReaTeam/ReaScripts
- repo_name: ReaTeam/ReaScripts
- purpose: REAPER Lua/EEL automation examples.
- url: https://github.com/ReaTeam/ReaScripts
- license: NOASSERTION at repo level; per-script license review needed.
- language: Lua
- last_updated: 2026-05-24
- relevance_score: 5
- use_type: study_only
- useful_files: envelope scripts showing `Undo_BeginBlock`, `PreventUIRefresh`, `defer`, ExtState patterns.
- applicable_to_estona_engine: safer REAPER script transaction style and state persistence.
- risks: mixed contributor scripts, unclear repo-level license.
- next_action: use API patterns only.

### ReaTeam/ReaScripts-Templates
- repo_name: ReaTeam/ReaScripts-Templates
- purpose: ReaScript templates and boilerplates.
- url: https://github.com/ReaTeam/ReaScripts-Templates
- license: NOASSERTION at repo level.
- language: Lua
- last_updated: 2026-05-13
- relevance_score: 5
- use_type: study_only
- useful_files: Lua template structure, ReaPack metadata examples.
- applicable_to_estona_engine: standard script headers, error handling, package organization.
- risks: no detected root license.
- next_action: document ReaPack-ready headers later, no code copy.

### X-Raym/REAPER-ReaScripts
- repo_name: X-Raym/REAPER-ReaScripts
- purpose: Mature REAPER Lua scripts.
- url: https://github.com/X-Raym/REAPER-ReaScripts
- license: GPL-3.0 from cloned `LICENSE`.
- language: Lua
- last_updated: 2026-05-21
- relevance_score: 5
- use_type: study_only
- useful_files: marker/region/item scripts, `PreventUIRefresh`, `Undo_BeginBlock`, track/item traversal idioms.
- applicable_to_estona_engine: render region creation and marker/report writing approach.
- risks: GPL-3.0; no direct code merge.
- next_action: keep our Lua implementation original.

### cfillion/reapack
- repo_name: cfillion/reapack
- purpose: REAPER package manager and packaging conventions.
- url: https://github.com/cfillion/reapack
- license: LGPL-3.0
- language: C++
- last_updated: 2026-05-23
- relevance_score: 3
- use_type: optional
- useful_files: `index.xml`, package metadata conventions.
- applicable_to_estona_engine: future ReaPack distribution layout.
- risks: LGPL tooling; not needed for MVP.
- next_action: study later if publishing JSFX/ReaScripts.

### michaelbriggsaudio/mbriggs-reaper
- repo_name: michaelbriggsaudio/mbriggs-reaper
- purpose: mastering-oriented REAPER scripts/tools.
- url: https://github.com/michaelbriggsaudio/mbriggs-reaper
- license: NOASSERTION from GitHub API; repo has `LICENSE.txt` but not cloned.
- language: Lua
- last_updated: 2026-05-21
- relevance_score: 3
- use_type: optional
- useful_files: mastering workflow scripts.
- applicable_to_estona_engine: possible render/QC workflow inspiration.
- risks: license must be checked before use.
- next_action: optional later clone, not needed now.

### sergree/matchering
- repo_name: sergree/matchering
- purpose: reference matching / mastering.
- url: https://github.com/sergree/matchering
- license: GPL-3.0 from cloned `LICENSE`.
- language: Python
- last_updated: 2026-05-25
- relevance_score: 5
- use_type: study_only
- useful_files: `matchering/core.py`, `stage_helpers/match_levels.py`, `stage_helpers/match_frequencies.py`, `preview_creator.py`.
- applicable_to_estona_engine: reference/target comparison stages, preview output concept, profile architecture.
- risks: GPL-3.0; direct code copy or default integration is license-risky.
- next_action: keep optional `matchering_reference_experiment.py` as study-only placeholder.

### blueff/Matchering
- repo_name: blueff/Matchering
- purpose: older MATLAB matchering implementation.
- url: https://github.com/blueff/Matchering
- license: GPL-3.0
- language: MATLAB
- last_updated: 2026-01-16
- relevance_score: 2
- use_type: reject
- useful_files: none for current Python MVP.
- applicable_to_estona_engine: historical context only.
- risks: GPL and MATLAB dependency.
- next_action: exclude.

### Wamphyre/oXygen
- repo_name: Wamphyre/oXygen
- purpose: open mastering plugin.
- url: https://github.com/Wamphyre/oXygen
- license: BSD-3-Clause
- language: C++
- last_updated: 2026-05-25
- relevance_score: 3
- use_type: optional
- useful_files: mastering plugin architecture.
- applicable_to_estona_engine: future plugin route concepts.
- risks: C++/JUCE complexity beyond MVP.
- next_action: revisit after JSFX stabilizes.

### librosa/librosa
- repo_name: librosa/librosa
- purpose: Python audio/music analysis.
- url: https://github.com/librosa/librosa
- license: ISC from cloned `LICENSE.md`.
- language: Python
- last_updated: 2026-05-25
- relevance_score: 5
- use_type: clone_and_use
- useful_files: spectral feature functions, onset detection, `pyin`.
- applicable_to_estona_engine: stronger spectral centroid/rolloff/flatness, transient proxy, pitch analyzer.
- risks: optional dependency; avoid hard failure when absent.
- next_action: keep optional backend in `audio_utils.py` and `vocal_pitch_analyzer.py`.

### csteinmetz1/pyloudnorm
- repo_name: csteinmetz1/pyloudnorm
- purpose: BS.1770 loudness meter.
- url: https://github.com/csteinmetz1/pyloudnorm
- license: MIT from cloned `LICENSE`.
- language: Python
- last_updated: 2026-05-20
- relevance_score: 5
- use_type: clone_and_use
- useful_files: `pyloudnorm/meter.py`, loudness range API.
- applicable_to_estona_engine: integrated LUFS and future LRA measurement.
- risks: optional dependency; true peak still proxy in MVP.
- next_action: keep pyloudnorm backend with explicit fallback.

### spotify/pedalboard
- repo_name: spotify/pedalboard
- purpose: Python audio processing and plugin hosting.
- url: https://github.com/spotify/pedalboard
- license: GPL-3.0 from cloned `LICENSE`.
- language: C++/Python
- last_updated: 2026-05-24
- relevance_score: 4
- use_type: optional
- useful_files: plugin hosting docs/API.
- applicable_to_estona_engine: optional VST3/AU batch processing possibility.
- risks: GPL-3.0 and paid plugin temptation; not default.
- next_action: inventory-only scanner added; no automatic loading.

### twardoch/pedalboard-pluginary
- repo_name: twardoch/pedalboard-pluginary
- purpose: VST3/AU plugin management for pedalboard.
- url: https://github.com/twardoch/pedalboard-pluginary
- license: Apache-2.0
- language: Python
- last_updated: 2026-04-26
- relevance_score: 3
- use_type: optional
- useful_files: plugin path scanning concepts.
- applicable_to_estona_engine: plugin inventory report design.
- risks: young project, optional only.
- next_action: study later if inventory scanner needs richer metadata.

### pyFFTW/pyFFTW
- repo_name: pyFFTW/pyFFTW
- purpose: FFT acceleration.
- url: https://github.com/pyFFTW/pyFFTW
- license: NOASSERTION/Other by GitHub API.
- language: Python/C
- last_updated: 2026-05-20
- relevance_score: 2
- use_type: optional
- useful_files: FFTW integration.
- applicable_to_estona_engine: future speedup for large batch analysis.
- risks: binary dependency friction.
- next_action: exclude from MVP.

### scipy/scipy
- repo_name: scipy/scipy
- purpose: scientific signal processing.
- url: https://github.com/scipy/scipy
- license: BSD-3-Clause
- language: Python/C/Fortran
- last_updated: 2026-05-25
- relevance_score: 4
- use_type: clone_and_use via dependency
- useful_files: `scipy.signal` APIs.
- applicable_to_estona_engine: resampling, filtering, medfilt/transient proxy.
- risks: dependency install weight.
- next_action: keep dependency, no repo clone needed.

### bastibe/python-soundfile
- repo_name: bastibe/python-soundfile
- purpose: libsndfile wrapper.
- url: https://github.com/bastibe/python-soundfile
- license: BSD-3-Clause
- language: Python
- last_updated: 2026-05-22
- relevance_score: 4
- use_type: clone_and_use via dependency
- useful_files: audio read/write API.
- applicable_to_estona_engine: WAV/AIFF/FLAC loading when installed.
- risks: libsndfile runtime dependency.
- next_action: keep optional fallback.

### facebookresearch/demucs
- repo_name: facebookresearch/demucs
- purpose: source separation.
- url: https://github.com/facebookresearch/demucs
- license: MIT
- language: Python
- last_updated: 2026-05-25
- relevance_score: 3
- use_type: optional
- useful_files: stem separation pipeline.
- applicable_to_estona_engine: emergency stem estimates when user lacks stems.
- risks: separation artifacts; never use as final release source without warning.
- next_action: future optional module only.

### sigsep/open-unmix-pytorch
- repo_name: sigsep/open-unmix-pytorch
- purpose: open source source separation.
- url: https://github.com/sigsep/open-unmix-pytorch
- license: MIT
- language: Python
- last_updated: 2026-05-22
- relevance_score: 3
- use_type: optional
- useful_files: separation inference design.
- applicable_to_estona_engine: fallback stem analysis.
- risks: artifacts and PyTorch dependency.
- next_action: future optional module only.

### airwindows/airwindows
- repo_name: airwindows/airwindows
- purpose: open DSP code collection.
- url: https://github.com/airwindows/airwindows
- license: MIT from cloned `LICENSE`.
- language: C++
- last_updated: 2026-05-23
- relevance_score: 4
- use_type: study_only
- useful_files: saturation/console/clipper processors.
- applicable_to_estona_engine: saturation policy vocabulary and conservative drive limits.
- risks: no direct code copy; algorithms should be reauthored for JSFX.
- next_action: use as conceptual DSP reference.

### jatinchowdhury18/AnalogTapeModel
- repo_name: jatinchowdhury18/AnalogTapeModel
- purpose: analog tape physical modeling.
- url: https://github.com/jatinchowdhury18/AnalogTapeModel
- license: GPL-3.0
- language: C++
- last_updated: 2026-05-18
- relevance_score: 3
- use_type: study_only
- useful_files: tape saturation architecture.
- applicable_to_estona_engine: future theory reference only.
- risks: GPL-3.0 and complex DSP.
- next_action: do not merge.

### Chowdhury-DSP/chowdsp_utils
- repo_name: Chowdhury-DSP/chowdsp_utils
- purpose: JUCE DSP utility module.
- url: https://github.com/Chowdhury-DSP/chowdsp_utils
- license: NOASSERTION/Other by GitHub API.
- language: C++
- last_updated: 2026-05-23
- relevance_score: 2
- use_type: optional
- useful_files: utility architecture.
- applicable_to_estona_engine: future C++ plugin engineering patterns.
- risks: license must be manually checked; C++ plugin scope too large.
- next_action: defer.

### DISTRHO/DPF
- repo_name: DISTRHO/DPF
- purpose: plugin framework.
- url: https://github.com/DISTRHO/DPF
- license: ISC
- language: C++
- last_updated: 2026-05-20
- relevance_score: 3
- use_type: optional
- useful_files: plugin framework examples.
- applicable_to_estona_engine: future VST/LV2 route.
- risks: not needed before JSFX proves policy sound.
- next_action: later framework comparison.

### iPlug2/iPlug2
- repo_name: iPlug2/iPlug2
- purpose: cross-platform plugin framework.
- url: https://github.com/iPlug2/iPlug2
- license: NOASSERTION/Other by GitHub API.
- language: C/C++
- last_updated: 2026-05-25
- relevance_score: 3
- use_type: optional
- useful_files: plugin build architecture.
- applicable_to_estona_engine: future plugin packaging route.
- risks: manual license review and build complexity.
- next_action: later only.

### juce-framework/JUCE
- repo_name: juce-framework/JUCE
- purpose: C++ application/audio plugin framework.
- url: https://github.com/juce-framework/JUCE
- license: NOASSERTION/Other by GitHub API; known dual/commercial-style review required.
- language: C++
- last_updated: 2026-05-25
- relevance_score: 2
- use_type: optional
- useful_files: plugin framework architecture.
- applicable_to_estona_engine: future commercial-grade plugin route.
- risks: licensing/build complexity; not for MVP.
- next_action: defer.

### free-audio/clap
- repo_name: free-audio/clap
- purpose: audio plugin API.
- url: https://github.com/free-audio/clap
- license: MIT
- language: C
- last_updated: 2026-05-25
- relevance_score: 2
- use_type: optional
- useful_files: CLAP API spec.
- applicable_to_estona_engine: future plugin format.
- risks: lower immediate REAPER/Python relevance.
- next_action: defer.

### webprofusion/OpenAudio
- repo_name: webprofusion/OpenAudio
- purpose: open audio project index.
- url: https://github.com/webprofusion/OpenAudio
- license: CC0-1.0
- language: TypeScript/data
- last_updated: 2026-05-25
- relevance_score: 2
- use_type: optional
- useful_files: curated project list.
- applicable_to_estona_engine: future discovery.
- risks: index, not implementation.
- next_action: use only for later research.

### JoepVanlier/JSFX
- repo_name: JoepVanlier/JSFX
- purpose: advanced JSFX bundle.
- url: https://github.com/JoepVanlier/JSFX
- license: MIT
- language: Lua/JSFX
- last_updated: 2026-05-22
- relevance_score: 3
- use_type: optional
- useful_files: advanced JSFX architecture.
- applicable_to_estona_engine: UI/meters and DSP organization reference.
- risks: advanced/large; not needed before ESTONA JSFX stabilize.
- next_action: optional later clone.

### Sonic-Anomaly/Sonic-Anomaly-JSFX
- repo_name: Sonic-Anomaly/Sonic-Anomaly-JSFX
- purpose: JSFX collection.
- url: https://github.com/Sonic-Anomaly/Sonic-Anomaly-JSFX
- license: no GitHub license API result.
- language: JSFX
- last_updated: 2026-03-30
- relevance_score: 2
- use_type: reject
- useful_files: compressor/limiter examples.
- applicable_to_estona_engine: none until license verified.
- risks: license unclear.
- next_action: exclude.

### jpcima/ysfx
- repo_name: jpcima/ysfx
- purpose: JSFX hosting library.
- url: https://github.com/jpcima/ysfx
- license: Apache-2.0
- language: C++
- last_updated: 2026-05-21
- relevance_score: 3
- use_type: optional
- useful_files: JSFX host architecture.
- applicable_to_estona_engine: future offline JSFX test harness.
- risks: C++ integration not MVP.
- next_action: later, if automated JSFX testing becomes necessary.
