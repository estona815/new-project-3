from __future__ import annotations

from pathlib import Path
from typing import Any

from paths import PROJECT_ROOT
from reference_profile import build_reference_target_profile, write_reference_profile
from web_reference_research import collect_web_reference_sources, write_web_reference_outputs


def render_style_translation(profile: dict[str, Any]) -> str:
    style = profile["style_targets"]
    drums = profile["drum_targets"]
    bass = profile["bass_808_targets"]
    vocals = profile["vocal_targets"]
    arrangement = profile["arrangement_targets"]
    traits = profile.get("reference_traits", {})
    web_research = profile.get("web_reference_research", {})
    copying_policy = profile.get("copying_policy", {})
    parsed = profile.get("parsed_intent", {})
    requests = parsed.get("reference_requests", [])
    web_limitations = []
    for source in web_research.get("sources", []):
        web_limitations.extend(str(item) for item in source.get("limitations", []))
    web_limitations.extend(str(item) for item in web_research.get("source_limitations", []))
    web_limitations_text = "; ".join(dict.fromkeys(web_limitations)) or "not provided"
    request_lines = "\n".join(
        [
            f"- {item['target_element']}: {item['action']} from {item['reference_title']} "
            f"(confidence: {item['confidence']}; needs reference audio: {str(item['requires_reference_audio_for_accuracy']).lower()})"
            for item in requests
        ]
    ) or "- no specific reference target parsed"
    explicit = parsed.get("explicit_targets", {})
    bass_explicit = explicit.get("bass_808", {})
    drum_explicit = explicit.get("drums", {})
    vocal_explicit = explicit.get("vocal", {})
    processing_explicit = explicit.get("processing", {})
    arrangement_explicit = explicit.get("arrangement", {})
    return f"""# Style Translation

## User Request
- original user phrase: {parsed.get('raw_text') or profile['source']['reference_text'] or 'not provided'}
- reference audio: {profile['source']['reference_audio_path'] or 'not provided'}
- mode: {profile['source']['mode']}
- confidence: {profile['source'].get('confidence', profile['source'].get('reference_confidence', 'low'))}
- reference support: {profile['source'].get('support', 'text-only' if profile['source'].get('reference_text') else 'not provided')}
- creative brief used: {str(profile['source'].get('creative_brief_used', False)).lower()}

## Evidence Used
- source priority: user-provided reference audio first, web text second, user phrase fallback last
- web access available: {str(bool(web_research.get('web_access_available'))).lower()}
- web_reference_research_unavailable: {str(bool(web_research.get('web_reference_research_unavailable'))).lower()}
- web combined confidence: {web_research.get('combined_confidence', 'low')}
- web trait inference allowed: {str(bool(web_research.get('trait_inference_allowed'))).lower()}
- evidence summary: {'; '.join(traits.get('evidence_summary', [])) or 'text-only prompt interpretation'}
- web source limitations: {web_limitations_text}

## Parsed Reference Requests
{request_lines}
- parsed target elements: {', '.join(parsed.get('target_elements', [])) or 'not provided'}
- parsed reference titles: {', '.join(parsed.get('reference_titles', [])) or 'not provided'}
- parsed priority: {parsed.get('priority', 'not provided')}
- trait target elements: {', '.join(traits.get('target_elements', [])) or 'not provided'}

## What The System Will Try To Match
- genre family: {', '.join(style['genre_family'])}
- energy/brightness/low-end: {style['energy']}/{style['brightness']}/{style['low_end_weight']}
- emotional descriptors: broad mood only, not melody or lyric copying
- parsed bass/808: tone {bass_explicit.get('tone')}, movement {bass_explicit.get('movement')}, priority {bass_explicit.get('priority')}, glide {bass_explicit.get('glide')}/5
- parsed drums: density {drum_explicit.get('density')}/5, transient sharpness {drum_explicit.get('transient_sharpness')}/5, swing {drum_explicit.get('swing')}, fills {drum_explicit.get('fill_amount')}/5
- parsed vocal: forwardness {vocal_explicit.get('forwardness')}/5, tuning {vocal_explicit.get('tuning')}, brightness {vocal_explicit.get('brightness')}/5
- parsed processing: autotune {processing_explicit.get('autotune')}, saturation {processing_explicit.get('saturation_style')}, plugin reference {processing_explicit.get('plugin_style_reference') or 'not provided'}
- parsed arrangement: hook early {str(arrangement_explicit.get('hook_early')).lower()}, target hook seconds {arrangement_explicit.get('target_hook_seconds')}

## Drum Target
- kick: {drums['kick']}
- snare/clap: {drums['snare_or_clap']}
- hats: {drums['hats']}
- percussion: {drums['percussion']}
- swing/fills: {drums['swing']} / {drums['fills']}
- manual notes: {'; '.join(drums.get('manual_logic_notes', []))}

## 808 Target
- tone: {bass['tone']}
- sub weight: {bass.get('sub_weight')}/5
- distortion: {bass.get('distortion')}/5
- glide: {bass.get('glide')}/5
- movement: {bass['movement']}
- rhythmic density: {bass.get('rhythmic_density')}/5
- mono sub required: {str(traits.get('bass_808', {}).get('mono_sub_required', True)).lower()}
- wide upper harmonics allowed: {str(traits.get('bass_808', {}).get('wide_upper_harmonics_allowed', True)).lower()}
- priority: {bass['priority']}
- manual notes: {'; '.join(bass.get('manual_logic_notes', []))}

## Synth Width / Panning Target
- pan motion: {traits.get('synth_width', {}).get('pan_motion', 'none')}
- stereo width: {traits.get('synth_width', {}).get('stereo_width', 2)}/5
- mid/side approach: {traits.get('synth_width', {}).get('mid_side_approach', 'unknown')}
- low-frequency mono cutoff: {traits.get('synth_width', {}).get('low_frequency_mono_cutoff_hz', 120)} Hz
- mono compatibility required: {str(traits.get('synth_width', {}).get('mono_compatibility_required', True)).lower()}

## Melody Target
- Use high-level melodic color only: bright/digicore-compatible if requested.
- Do not recreate protected melodies, samples, lyrics, or unique sound recordings.

## Vocal Target
- lead position: {vocals['lead_position']}
- tuning: {vocals['tuning']}
- texture: {vocals['texture']}
- adlib width: {vocals['adlib_width']}
- identity clone allowed: {str(traits.get('vocal', {}).get('identity_clone_allowed', False)).lower()}
- compression: {traits.get('vocal', {}).get('compression', 'medium')}
- saturation: {traits.get('vocal', {}).get('saturation', 'subtle')}
- reverb/delay: {traits.get('vocal', {}).get('reverb_space', 'plate')} / {traits.get('vocal', {}).get('delay_style', 'throw_only')}
- user voice identity preserve: {str(traits.get('vocal', {}).get('identity_preserve', False)).lower()}
- plugin-style note: {traits.get('vocal', {}).get('plugin_style_reference') or 'not provided'}

## Arrangement Target
- hook entrance: around {arrangement['hook_entrance_seconds']} seconds
- intro length: {arrangement['intro_length']}
- drop style: {arrangement['drop_style']}
- variation every {arrangement['variation_frequency_bars']} bars

## Mix/Master Target
- transient sharpness should follow the drum target without clipping.
- loudness should fit the requested energy while preserving headroom.

## What Will Not Be Copied
- No exact copyrighted track recreation.
- No protected melody, sample, lyric, or unique recording extraction.
- No exact artist/producer clone.
- No living artist vocal identity clone or impersonation.
- No exact reference bass sound, drum pattern, vocal chain, sample, mix, or master is claimed.
- Korean `따와라` means use licensed/owned user-provided samples or translate safely to production traits; it does not authorize unlicensed sample extraction.
{chr(10).join(f'- {item}' for item in profile.get('legal_and_accuracy_notes', []))}

## Copying Policy
- copying requested: {str(bool(copying_policy.get('copying_requested'))).lower()}
- exact copy allowed: {str(bool(copying_policy.get('exact_copy_allowed'))).lower()}
- reason: {copying_policy.get('reason', 'not evaluated')}
- allowed actions: {', '.join(copying_policy.get('allowed_actions', [])) or 'not provided'}
- disallowed actions: {', '.join(copying_policy.get('disallowed_actions', [])) or 'not provided'}
- requires user owned source: {str(bool(copying_policy.get('requires_user_owned_source'))).lower()}
- note: {copying_policy.get('report_note', 'No exact copying is performed or claimed.')}

## Reference Audio Need
- reference audio needed for accurate matching: {str(any(item.get('requires_reference_audio_for_accuracy') for item in requests)).lower()}
- source support class: {profile['source'].get('support', 'text-only' if profile['source'].get('reference_text') else 'not provided')}
- source limitations: {'; '.join(traits.get('source_limitations', [])) or web_limitations_text}
- safety note: {parsed.get('safety_note', 'Reference is used for high-level production attributes only, not exact copying.')}

## Production Targets For Logic / Manual Editing
- Use these targets as a checklist for drum replacement, hat programming, 808 tone, vocal bus choices, and arrangement edits.
- Compare by feel and broad frequency/energy balance only.
- For synth width, keep sub/fundamental low-end centered, widen high-passed layers or upper harmonics, and check mono compatibility.
- If only a stereo file is available, fallback processing is limited to broad EQ, dynamics, gain, fade, and heuristic listening cues.
- Stem-level drum, 808, or vocal matching requires stems, MIDI, or manual Logic editing.

## Avoid
{chr(10).join(f'- {item}' for item in profile['avoid'])}
"""


def run_reference_targeting(options: dict[str, Any], project_root: Path = PROJECT_ROOT) -> dict[str, Path]:
    ref_dir = project_root / "08_REFERENCE_MATCH"
    ref_dir.mkdir(parents=True, exist_ok=True)
    brief = options.get("creative_brief") or {}
    reference_text = options.get("reference_text") or brief.get("creative_target")
    reference_audio = options.get("reference_audio") or brief.get("input_files", {}).get("reference_audio")
    web_research = options.get("web_reference_research")
    if not web_research:
        web_research = collect_web_reference_sources(
            reference_text,
            web_access_available=bool(options.get("web_access_available") or options.get("web_reference_web_access")),
            source_candidates=options.get("web_reference_sources"),
            reference_audio_available=bool(reference_audio),
        )
    web_paths = write_web_reference_outputs(web_research, ref_dir)
    profile = build_reference_target_profile(
        reference_text,
        reference_audio,
        options.get("creative_brief"),
        web_research,
    )
    profile_path = ref_dir / "reference_target_profile.json"
    translation_path = ref_dir / "style_translation.md"
    write_reference_profile(profile, profile_path)
    translation_path.write_text(render_style_translation(profile), encoding="utf-8")
    return {"reference_target_profile": profile_path, "style_translation": translation_path, **web_paths}
