# Pass 04 All-Info Mix Report

Generated: 2026-05-24T18:42:42

## Executed
- Imported downloaded Suno `000000` all-detected stems into the REAPER session as muted candidate tracks.
- Kept references, quarantine, guide MIDI, and candidate Suno stems muted for render safety.
- Lowered the main vocal further than PASS03 and brought music/beat melody up.
- Tightened vocal FX returns and delay throws so the beat reads more clearly.
- Kept dynamic EQ strategy active on lead, music, bass, drums, and mix bus through the existing stock/fallback chain.
- Saved progressed project as `reaper/FRESH_MIX_MASTER_PASS_04_SUNO_000000_ALL_INFO.rpp`.

## Session Validation
PASS
- Session validation passed: routing, mute states, and item positions match pass 01 rules.
- PASS04 validation passed: references, quarantine, guide MIDI, and Suno 000000 candidate tracks are muted.

## Key Track Levels
| Track | Volume dB | Pan | Muted |
| --- | ---: | ---: | --- |
| 12_Vocals | -6.7 | 0.0 | False |
| MALE_LEAD_VOX_BUS | -0.4 | 0.0 | False |
| MUSIC_BUS | 1.9 | 0.0 | False |
| DRUM_BUS | -0.4 | 0.0 | False |
| BASS_808_BUS | -1.0 | 0.0 | False |
| VOCAL_FX_BUS | -9.5 | 0.0 | False |
| SUNO_000000_CANDIDATE_BUS | -18.0 | 0.0 | True |

## Why Suno Stems Are Muted
- The selected voice requirement was satisfied: `000000` appears on the Suno candidate.
- But the downloaded candidate is short and not a full aligned vocal take.
- It also contains incomplete lyric input caused by Chrome text-entry stripping Korean characters.
- Using it as an active production layer would risk fake/unmatched phrasing. It is preserved for manual audition only.
