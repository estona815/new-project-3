# Suno Studio Autopilot Brief

Date: 2026-05-25
Status: ready_for_suno_studio_session

## Mission

Use Suno Studio to generate and export usable stems for a REAPER mix/master pass while avoiding obvious AI vocal artifacts.

The user specifically wants the operator to handle Suno Studio directly, make judgment calls, reject bad takes, generate a usable female vocal layer, and export stems for later REAPER work.

## Non-Negotiables

- Remove or reject exaggerated AI greeting phrases such as "아아아아안녕", stretched hello sounds, fake spoken intros, random "ahh/ooh/yeah", moans, or filler adlibs.
- Reject generations with robotic syllable endings, hard vocal cuts, formant tearing, chipmunk tone, baby/anime tone, random vocal chops, or loud female takeover.
- Do not use a generated full master as the production source when stems are available.
- Export stems before REAPER rebuild.
- Keep full mix exports as reference only.
- Keep reference/full-mix tracks muted and out of the active REAPER premaster bus.

## Vocal Direction

Main vocal:

- Keep the male vocal as the main lead when an acceptable male lead stem is available.
- Tone: modern Korean emo rap / digicore / hyperpop, natural but tuned, clean consonants, emotionally bright, not shouted.
- Timing: tight to the beat, no loose AI pickup before phrases, no unnatural long intro.

Female vocal:

- Generate a separate female support vocal candidate when possible.
- Use as quiet panned backing, phrase-end double, harmony tail, soft adlib, or hook reinforcement.
- Do not let it become the lead unless the user explicitly asks for a female-lead version.
- Reject if it sounds like a random intro chop, off-grid phrase, off-pitch layer, or synthetic greeting.

## Suno Prompt

Korean emo rap, digicore, hyperpop, trap, future bass, electropop energy. Fast melodic short-form song with an immediate hook, clean vocal-forward arrangement, punchy drums, controlled 808, bright synth/pluck melody, smooth transitions, polished Seoul underground pop finish.

Main vocal should sound like a real studio singer: centered, natural low-mid to mid register, clean consonants, emotionally tuned, stable pitch, intelligible Korean phrasing, no robotic syllable tails, no fake spoken intro, no random greeting.

Female vocal layer should be soft, wide, low-volume, supportive only: backing doubles, harmony tails, phrase-end adlibs, and hook reinforcement. It must never become the main lead or introduce random words.

## Exclude Prompt

아아아아안녕, 안녕 spoken intro, stretched hello, fake greeting, random ahh, random ooh, random yeah, moaning vocal, weird vocal chop, vocal chop intro, chopped vocal hook, pitched-up chipmunk vocal, anime voice, baby voice, harsh female lead takeover, loud female hook, random female adlib, hard vocal splice, abrupt vocal cut, sudden AI cutoff, robotic syllable ending, formant tearing, noisy glitch burst, harsh white noise, metallic digital noise, excessive bitcrush, unmusical stutter, phasey stereo, anti-phase widening, muddy bass, buried main vocal, muffled vocal, washed-out vocal, excessive reverb, messy delay, over-compression, clipping, long ambient intro, slow buildup, weak hook, random chord drift, generic AI demo, amateur demo

## Starting Settings

- Custom Mode: ON
- Instrumental: OFF for vocal generation
- Weirdness: 6-10% first; lower if vocals get strange
- Style Influence: 84-88%
- Audio Influence: 0-15% unless using a clean instrumental reference only
- Vocal Gender: male for main candidate, female for support candidate
- Generate in small batches and audition before spending more credits

## Candidate Selection

Accept only if:

- No obvious AI greeting or filler intro.
- Main phrase starts musically and quickly.
- Vocal timing locks to the instrumental.
- Korean consonants are clear enough for REAPER treatment.
- Female support can be tucked low without fighting the lead.
- Stem export is available and the stem sounds usable when soloed.

Reject if:

- The first seconds contain "아아아아안녕" or similar stretched hello behavior.
- Female vocal becomes the hook lead without request.
- Vocal has hard cuts, chopped words, or random syllable extensions.
- The stem has too much bleed/noise to repair cleanly.
- The generation only works as a mastered full mix and not as stems.

## Export Checklist

- Export 12-track WAV stems or multitracks if available.
- Export vocal stems separately.
- Export male lead vocal stem if available.
- Export female BGV/adlib/double stem if available.
- Export instrumental, drums, bass/808, music/synth, FX stems when available.
- Export MIDI for useful melodic/vocal-support material when available.
- Export full mix WAV only for reference.
- Avoid MP3 as a production source; MP3 is reference/QC only.

## Local Filing

Place downloads under a new versioned folder:

- `audio_work/suno_studio_<slug>_vNN/raw_exports`
- `audio_work/suno_studio_<slug>_vNN/selected_stems`
- `reports/suno_studio_<slug>_vNN`

After export, create a manifest with:

- generation prompt used
- excluded terms used
- accepted/rejected candidate notes
- downloaded filenames
- stem roles
- tempo/key if known
- observed issues

## REAPER Handoff

After stems are downloaded:

1. Audit stem length, sample rate, channels, peak, and silence.
2. Align stems against the approved timing base.
3. Keep female support muted or low until alignment is verified.
4. Build a new REAPER version folder.
5. Render premaster and print.
6. Run loudness, true-peak, and MP3 QC before delivery.

