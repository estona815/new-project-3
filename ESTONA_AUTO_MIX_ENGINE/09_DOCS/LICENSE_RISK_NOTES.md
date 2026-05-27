# License Risk Notes

## High Risk / Study Only

- `sergree/matchering`: GPL-3.0. Useful architecture, but direct code merge could impose GPL obligations.
- `blueff/Matchering`: GPL-3.0 and MATLAB-oriented. Excluded.
- `X-Raym/REAPER-ReaScripts`: GPL-3.0. Use only API patterns, not code.
- `spotify/pedalboard`: cloned license is GPL-3.0. Optional inventory/experiments only until license review.
- `jatinchowdhury18/AnalogTapeModel`: GPL-3.0. Theory/reference only.

## Medium Risk / Verify Per File

- `ReaTeam/JSFX`, `ReaTeam/ReaScripts`, `ReaTeam/ReaScripts-Templates`: GitHub API reports NOASSERTION and cloned roots did not expose a single clear LICENSE. Because these are community collections, check individual file headers before reuse.
- `michaelbriggsaudio/mbriggs-reaper`: not cloned; GitHub API returned NOASSERTION. Check `LICENSE.txt` before any use.
- `Chowdhury-DSP/chowdsp_utils`, `iPlug2/iPlug2`, `juce-framework/JUCE`, `pyFFTW/pyFFTW`: GitHub API returned NOASSERTION/Other. Manual review needed before direct integration.
- `Sonic-Anomaly/Sonic-Anomaly-JSFX`: license API unavailable. Excluded.

## Lower Risk / Still Attribute

- `librosa/librosa`: ISC.
- `csteinmetz1/pyloudnorm`: MIT.
- `airwindows/airwindows`: MIT.
- `scipy/scipy`: BSD-3-Clause.
- `bastibe/python-soundfile`: BSD-3-Clause.
- `facebookresearch/demucs`: MIT.
- `sigsep/open-unmix-pytorch`: MIT.
- `DISTRHO/DPF`: ISC.
- `free-audio/clap`: MIT.
- `webprofusion/OpenAudio`: CC0-1.0.
- `jpcima/ysfx`: Apache-2.0.
- `twardoch/pedalboard-pluginary`: Apache-2.0.
- `Wamphyre/oXygen`: BSD-3-Clause.

## ESTONA Policy

- Do not copy GPL code into ESTONA source files.
- Do not import optional GPL tools into the default pipeline.
- Do not make paid/commercial plugin presence a success condition.
- Keep all reference matching abstract: loudness, spectrum, stereo, dynamics, masking, saturation proxies only.
- Never copy melody, lyrics, vocal lines, chord progressions, arrangement, or proprietary sonic identity from a reference.
