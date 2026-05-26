-- Auto-generated local import for cleaned Suno Studio stems and guide MIDI.
-- Harness fresh_mix_rebuild.v0.6: fresh zero-state rebuild from raw Suno Studio WAV stems and guide MIDI.
-- MP3/master/fullmix/reference files are muted analysis references only.
local bpm = 180
local buses = {
  "REF_BUS",
  "DRUM_BUS",
  "BASS_808_BUS",
  "MUSIC_BUS",
  "MALE_LEAD_VOX_BUS",
  "FEMALE_BGV_BUS",
  "VOCAL_FX_BUS",
  "FX_BUS",
  "ARTIFACT_QUARANTINE_BUS",
  "MIX_BUS",
  "MASTER_PREMIX_BUS",
  "PRINT_MASTER_BUS",
  "VOCAL_PLATE_SEND",
  "VOCAL_DELAY_SEND",
  "SHORT_ROOM_SEND",
  "OPTIONAL_WIDE_THROW_SEND",
}
local musical_buses = {
  "DRUM_BUS",
  "BASS_808_BUS",
  "MUSIC_BUS",
  "MALE_LEAD_VOX_BUS",
  "FEMALE_BGV_BUS",
  "VOCAL_FX_BUS",
  "FX_BUS",
}
local media = {
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/external_female_v20_stems/0 Lead Vocals.wav", name="Female BGV L - 0 Lead Vocals", category="female_bgv", bus="FEMALE_BGV_BUS", vol=0.08912509, pan=-0.400, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/external_female_v20_stems/1 Instrumental.wav", name="1 Instrumental", category="reference_only", bus="REF_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/01_Woodwinds_woodwinds.mid", name="Guide MIDI - 01_Woodwinds_woodwinds", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/02_Brass_brass.mid", name="Guide MIDI - 02_Brass_brass", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/03_FX_fx.mid", name="Guide MIDI - 03_FX_fx", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/04_Synth_synth.mid", name="Guide MIDI - 04_Synth_synth", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/05_Strings_strings.mid", name="Guide MIDI - 05_Strings_strings", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/06_Percussion_percussion.mid", name="Guide MIDI - 06_Percussion_percussion", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/07_Keyboard_keyboard.mid", name="Guide MIDI - 07_Keyboard_keyboard", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/08_Guitar_guitar.mid", name="Guide MIDI - 08_Guitar_guitar", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/09_Bass_bass.mid", name="Guide MIDI - 09_Bass_bass", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/10_Drums_drums.mid", name="Guide MIDI - 10_Drums_drums", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/11_Backing_Vocals_female_vocal_candidate.mid", name="Guide MIDI - 11_Backing_Vocals_female_vocal_candidate", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/12_Vocals_lead_vocal.mid", name="Guide MIDI - 12_Vocals_lead_vocal", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/midi_guides/combined_suno_audio_derived_guides.mid", name="Guide MIDI - combined_suno_audio_derived_guides", category="guide_midi", bus="MUSIC_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/00_REF_Full_Mix.wav", name="00_REF_Full_Mix", category="reference_only", bus="REF_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/01_Woodwinds.wav", name="01_Woodwinds", category="music_or_synth", bus="MUSIC_BUS", vol=0.22387211, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/02_Brass.wav", name="02_Brass", category="music_or_synth", bus="MUSIC_BUS", vol=0.22387211, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/03_FX.wav", name="QUARANTINE - 03_FX", category="vocal_artifact_quarantine", bus="ARTIFACT_QUARANTINE_BUS", vol=0.06309573, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/04_Synth.wav", name="04_Synth", category="music_or_synth", bus="MUSIC_BUS", vol=0.22387211, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/05_Strings.wav", name="05_Strings", category="music_or_synth", bus="MUSIC_BUS", vol=0.22387211, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/06_Percussion.wav", name="06_Percussion", category="drums", bus="DRUM_BUS", vol=0.31622777, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/07_Keyboard.wav", name="07_Keyboard", category="music_or_synth", bus="MUSIC_BUS", vol=0.22387211, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/08_Guitar.wav", name="QUARANTINE - 08_Guitar", category="vocal_artifact_quarantine", bus="ARTIFACT_QUARANTINE_BUS", vol=0.06309573, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/09_Bass.wav", name="09_Bass", category="bass_or_808", bus="BASS_808_BUS", vol=0.29853826, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/10_Drums.wav", name="10_Drums", category="drums", bus="DRUM_BUS", vol=0.31622777, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/11_Backing_Vocals.wav", name="Female BGV R - 11_Backing_Vocals", category="female_bgv", bus="FEMALE_BGV_BUS", vol=0.08912509, pan=0.400, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/12_Vocals.wav", name="12_Vocals", category="male_lead_vocal", bus="MALE_LEAD_VOX_BUS", vol=0.50118723, pan=0.000, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/female_vocal_candidate_clean.wav", name="Female BGV L - female_vocal_candidate_clean", category="female_bgv", bus="FEMALE_BGV_BUS", vol=0.08912509, pan=-0.400, mute=false},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav", name="PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48", category="problem_reference", bus="REF_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/v11_precision_mix/renders/hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3", name="PROBLEM REF - hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k", category="problem_reference", bus="REF_BUS", vol=0.12589254, pan=0.000, mute=true},
  {path="/Users/hantaeheuk/Downloads/발매곡 완성본/동반자살 완성본/동반자살 WAV.wav", name="TECH REF - 동반자살 WAV", category="technical_mix_reference", bus="REF_BUS", vol=0.12589254, pan=0.000, mute=true},
}
local qc_markers = {
  {time=0.000, name="QC critical: phase_or_stereo_width_anomaly (08_Guitar.wav)"},
  {time=0.000, name="QC critical: excessive_high_frequency_harshness (08_Guitar.wav)"},
  {time=0.020, name="QC critical: local_dropout_or_abrupt_cut (female_vocal_candidate_clean.wav)"},
  {time=1.840, name="QC critical: local_dropout_or_abrupt_cut (10_Drums.wav)"},
  {time=2.580, name="QC critical: local_dropout_or_abrupt_cut (10_Drums.wav)"},
  {time=3.320, name="QC critical: local_dropout_or_abrupt_cut (10_Drums.wav)"},
  {time=3.720, name="QC critical: local_dropout_or_abrupt_cut (0 Lead Vocals.wav)"},
  {time=7.800, name="QC critical: local_dropout_or_abrupt_cut (0 Lead Vocals.wav)"},
  {time=10.380, name="QC critical: local_dropout_or_abrupt_cut (09_Bass.wav)"},
  {time=11.100, name="QC critical: local_dropout_or_abrupt_cut (03_FX.wav)"},
  {time=11.660, name="QC critical: local_dropout_or_abrupt_cut (04_Synth.wav)"},
  {time=13.320, name="QC critical: local_dropout_or_abrupt_cut (09_Bass.wav)"},
  {time=14.800, name="QC critical: local_dropout_or_abrupt_cut (09_Bass.wav)"},
  {time=29.920, name="QC critical: local_dropout_or_abrupt_cut (08_Guitar.wav)"},
  {time=34.060, name="QC critical: local_dropout_or_abrupt_cut (09_Bass.wav)"},
  {time=0.000, name="QC high: excessive_high_frequency_harshness (03_FX.wav)"},
  {time=0.000, name="QC high: low_end_mud_or_vocal_masking (09_Bass.wav)"},
  {time=1.040, name="QC high: sudden_energy_spike (03_FX.wav)"},
  {time=1.200, name="QC high: sudden_energy_spike (04_Synth.wav)"},
  {time=1.200, name="QC high: sudden_energy_spike (11_Backing_Vocals.wav)"},
  {time=1.200, name="QC high: sudden_energy_spike (female_vocal_candidate_clean.wav)"},
  {time=1.280, name="QC high: sudden_energy_spike (04_Synth.wav)"},
  {time=1.280, name="QC high: sudden_energy_spike (female_vocal_candidate_clean.wav)"},
  {time=1.560, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=1.760, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=1.940, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=2.480, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=2.700, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=3.200, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=3.280, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=3.400, name="QC high: near_silence_hole (04_Synth.wav)"},
  {time=3.440, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=3.440, name="QC high: sudden_energy_spike (11_Backing_Vocals.wav)"},
  {time=3.520, name="QC high: local_dropout_or_abrupt_cut (11_Backing_Vocals.wav)"},
  {time=3.600, name="QC high: sudden_energy_spike (04_Synth.wav)"},
  {time=3.680, name="QC high: local_dropout_or_abrupt_cut (04_Synth.wav)"},
  {time=4.000, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=4.180, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=4.720, name="QC high: sudden_energy_spike (10_Drums.wav)"},
  {time=4.920, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=5.660, name="QC high: near_silence_hole (10_Drums.wav)"},
  {time=5.840, name="QC high: sudden_energy_spike (female_vocal_candidate_clean.wav)"},
  {time=6.480, name="QC high: local_dropout_or_abrupt_cut (04_Synth.wav)"},
  {time=6.500, name="QC high: local_dropout_or_abrupt_cut (female_vocal_candidate_clean.wav)"},
  {time=6.720, name="QC high: sudden_energy_spike (03_FX.wav)"},
  {time=6.880, name="QC high: local_dropout_or_abrupt_cut (0 Lead Vocals.wav)"},
  {time=7.100, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=8.720, name="QC high: local_dropout_or_abrupt_cut (0 Lead Vocals.wav)"},
  {time=8.720, name="QC high: local_dropout_or_abrupt_cut (11_Backing_Vocals.wav)"},
  {time=10.160, name="QC high: sudden_energy_spike (03_FX.wav)"},
  {time=10.320, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=10.620, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=10.620, name="QC high: near_silence_hole (09_Bass.wav)"},
  {time=10.680, name="QC high: near_silence_hole (04_Synth.wav)"},
  {time=11.040, name="QC high: sudden_energy_spike (03_FX.wav)"},
  {time=11.040, name="QC high: sudden_energy_spike (04_Synth.wav)"},
  {time=11.340, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=11.600, name="QC high: sudden_energy_spike (04_Synth.wav)"},
  {time=12.300, name="QC high: near_silence_hole (04_Synth.wav)"},
  {time=12.560, name="QC high: sudden_energy_spike (0 Lead Vocals.wav)"},
  {time=13.200, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=13.280, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=13.440, name="QC high: sudden_energy_spike (08_Guitar.wav)"},
  {time=14.320, name="QC high: near_silence_hole (09_Bass.wav)"},
  {time=14.360, name="QC high: near_silence_hole (04_Synth.wav)"},
  {time=14.720, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=15.680, name="QC high: local_dropout_or_abrupt_cut (12_Vocals.wav)"},
  {time=16.560, name="QC high: sudden_energy_spike (08_Guitar.wav)"},
  {time=16.660, name="QC high: local_dropout_or_abrupt_cut (08_Guitar.wav)"},
  {time=18.020, name="QC high: near_silence_hole (09_Bass.wav)"},
  {time=18.020, name="QC high: local_dropout_or_abrupt_cut (09_Bass.wav)"},
  {time=18.960, name="QC high: sudden_energy_spike (03_FX.wav)"},
  {time=19.060, name="QC high: local_dropout_or_abrupt_cut (03_FX.wav)"},
  {time=19.520, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=21.040, name="QC high: sudden_energy_spike (0 Lead Vocals.wav)"},
  {time=22.460, name="QC high: near_silence_hole (03_FX.wav)"},
  {time=30.640, name="QC high: sudden_energy_spike (08_Guitar.wav)"},
  {time=31.040, name="QC high: sudden_energy_spike (08_Guitar.wav)"},
  {time=31.680, name="QC high: sudden_energy_spike (08_Guitar.wav)"},
  {time=34.000, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=34.420, name="QC high: near_silence_hole (09_Bass.wav)"},
  {time=34.720, name="QC high: sudden_energy_spike (09_Bass.wav)"},
  {time=38.640, name="QC high: sudden_energy_spike (12_Vocals.wav)"},
}
local fx = {
  pitch_correction="ReaTune",
  surgical_eq="ReaEQ",
  dynamic_eq="ReaXcomp",
  deesser="ReaXcomp",
  compressor_clean="ReaComp",
  compressor_character="ReaComp",
  saturation="JS: Saturation",
  stereo_imager="JS: Stereo Width",
  mid_side_eq="ReaEQ",
  reverb_plate="ReaVerbate",
  reverb_room="ReaVerbate",
  delay="ReaDelay",
  limiter="ReaLimit",
  loudness_meter="JS: Loudness Meter Peak/RMS/LUFS",
}

local function safe_add_fx(track, name, label)
  local index = reaper.TrackFX_AddByName(track, name, false, -1)
  if index < 0 and label ~= nil then
    reaper.GetSetMediaTrackInfo_String(track, "P_EXT:missing_fx_" .. label, name, true)
  end
  return index
end

local function log_step(message)
  local f = io.open("/tmp/codex_fresh_reaper/build_fresh_mix.log", "a")
  if f then
    f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(message), "\n")
    f:close()
  end
end

local function add_fx(track, category)
  if category == "male_lead_vocal" then
    safe_add_fx(track, fx.surgical_eq, "lead_cleanup_eq")
    safe_add_fx(track, fx.pitch_correction, "lead_pitch_correction")
    safe_add_fx(track, fx.dynamic_eq, "lead_dynamic_eq")
    safe_add_fx(track, fx.deesser, "lead_deesser")
    safe_add_fx(track, fx.compressor_clean, "lead_clean_compressor")
    safe_add_fx(track, fx.compressor_character, "lead_character_compressor")
    safe_add_fx(track, fx.surgical_eq, "lead_tone_eq")
    safe_add_fx(track, fx.saturation, "lead_light_saturation")
  elseif category == "female_bgv" then
    safe_add_fx(track, fx.surgical_eq, "bgv_hpf_soften_eq")
    safe_add_fx(track, fx.deesser, "bgv_deesser")
    safe_add_fx(track, fx.compressor_clean, "bgv_compressor")
    safe_add_fx(track, fx.stereo_imager, "bgv_width_control")
  elseif category == "drums" then
    safe_add_fx(track, fx.surgical_eq, "drum_cleanup_eq")
    safe_add_fx(track, fx.compressor_clean, "drum_punch_compressor")
  elseif category == "bass_or_808" then
    safe_add_fx(track, fx.surgical_eq, "bass_mono_low_eq")
    safe_add_fx(track, fx.dynamic_eq, "bass_kick_vocal_dynamic_control")
  elseif category == "music_or_synth" then
    safe_add_fx(track, fx.dynamic_eq, "music_vocal_pocket_dynamic_eq")
    safe_add_fx(track, fx.mid_side_eq, "music_ms_eq")
    safe_add_fx(track, fx.stereo_imager, "music_stereo_control")
  elseif category == "fx" then
    safe_add_fx(track, fx.surgical_eq, "fx_harshness_eq")
  elseif category == "vocal_artifact_quarantine" then
    safe_add_fx(track, fx.surgical_eq, "quarantine_inspection_eq")
  end
end

log_step("build script start")
reaper.Undo_BeginBlock()
log_step("undo begin")
if reaper.CountTracks and reaper.DeleteTrack then
  for track_index = reaper.CountTracks(0) - 1, 0, -1 do
    local tr = reaper.GetTrack(0, track_index)
    if tr then reaper.DeleteTrack(tr) end
  end
end
log_step("existing tracks cleared")
if reaper.SetTempoTimeSigMarker then
  reaper.SetTempoTimeSigMarker(0, -1, 0, -1, -1, bpm, 4, 4, false)
end
log_step("tempo set")

local bus_tracks = {}
for i, bus_name in ipairs(buses) do
  log_step("create bus " .. tostring(bus_name))
  reaper.InsertTrackAtIndex(i - 1, true)
  local tr = reaper.GetTrack(0, i - 1)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", bus_name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", 1.0)
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", 0.0)
  bus_tracks[bus_name] = tr
end

for _, bus_name in ipairs(buses) do
  reaper.SetMediaTrackInfo_Value(bus_tracks[bus_name], "B_MAINSEND", 0)
end
reaper.SetMediaTrackInfo_Value(bus_tracks["REF_BUS"], "B_MAINSEND", 1)
reaper.SetMediaTrackInfo_Value(bus_tracks["PRINT_MASTER_BUS"], "B_MAINSEND", 1)
for _, bus_name in ipairs(musical_buses) do
  reaper.CreateTrackSend(bus_tracks[bus_name], bus_tracks["MIX_BUS"])
end
reaper.CreateTrackSend(bus_tracks["VOCAL_PLATE_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["VOCAL_DELAY_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["SHORT_ROOM_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["OPTIONAL_WIDE_THROW_SEND"], bus_tracks["VOCAL_FX_BUS"])
reaper.CreateTrackSend(bus_tracks["MIX_BUS"], bus_tracks["MASTER_PREMIX_BUS"])
reaper.CreateTrackSend(bus_tracks["MASTER_PREMIX_BUS"], bus_tracks["PRINT_MASTER_BUS"])
reaper.SetMediaTrackInfo_Value(bus_tracks["REF_BUS"], "B_MUTE", 1)
reaper.SetMediaTrackInfo_Value(bus_tracks["ARTIFACT_QUARANTINE_BUS"], "B_MUTE", 1)
log_step("bus routing complete")
safe_add_fx(bus_tracks["VOCAL_PLATE_SEND"], fx.reverb_plate, "vocal_plate_send_predelay_20_35ms_decay_0_8_1_6s")
safe_add_fx(bus_tracks["VOCAL_DELAY_SEND"], fx.delay, "vocal_delay_send_dotted_eighth_or_quarter_filtered_ducked")
safe_add_fx(bus_tracks["SHORT_ROOM_SEND"], fx.reverb_room, "short_room_send_low_level_glue")
safe_add_fx(bus_tracks["MIX_BUS"], fx.dynamic_eq, "mix_bus_dynamic_mud_harshness_control")
safe_add_fx(bus_tracks["MIX_BUS"], fx.mid_side_eq, "mix_bus_ms_eq_low_side_control")
safe_add_fx(bus_tracks["MASTER_PREMIX_BUS"], fx.compressor_clean, "master_premix_glue_1_2db_max")
safe_add_fx(bus_tracks["PRINT_MASTER_BUS"], fx.limiter, "print_master_true_peak_minus_1db")
safe_add_fx(bus_tracks["PRINT_MASTER_BUS"], fx.loudness_meter, "print_master_loudness_meter")

local start_index = #buses
for i, entry in ipairs(media) do
  log_step("create media track " .. tostring(i) .. " " .. tostring(entry.name) .. " category=" .. tostring(entry.category))
  reaper.InsertTrackAtIndex(start_index + i - 1, true)
  local tr = reaper.GetTrack(0, start_index + i - 1)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", entry.name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", entry.vol)
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", entry.pan)
  reaper.SetMediaTrackInfo_Value(tr, "B_MAINSEND", 0)
  if entry.mute then reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1) end
  if entry.category == "guide_midi" then
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:guide_midi_path", entry.path, true)
    reaper.GetSetMediaTrackInfo_String(tr, "P_EXT:guide_midi_note", "Guide MIDI placeholder only; import manually if needed to avoid REAPER MIDI import modal prompts.", true)
    log_step("guide MIDI placeholder only " .. tostring(entry.path))
  else
    reaper.SetOnlyTrackSelected(tr)
    if reaper.SetEditCurPos then reaper.SetEditCurPos(0.0, false, false) end
    log_step("insert media start " .. tostring(entry.path))
    reaper.InsertMedia(entry.path, 0)
    if reaper.CountSelectedMediaItems and reaper.GetSelectedMediaItem and reaper.SetMediaItemInfo_Value then
      local selected_count = reaper.CountSelectedMediaItems(0)
      for selected_index = 0, selected_count - 1 do
        local item = reaper.GetSelectedMediaItem(0, selected_index)
        if item then reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0) end
      end
    end
    log_step("insert media done " .. tostring(entry.path))
  end
  if bus_tracks[entry.bus] then
    reaper.CreateTrackSend(tr, bus_tracks[entry.bus])
  else
    reaper.CreateTrackSend(tr, bus_tracks["ARTIFACT_QUARANTINE_BUS"])
    reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", 1)
  end
  add_fx(tr, entry.category)
  if entry.category == "male_lead_vocal" then
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_PLATE_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_DELAY_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["SHORT_ROOM_SEND"])
  elseif entry.category == "female_bgv" then
    reaper.CreateTrackSend(tr, bus_tracks["VOCAL_PLATE_SEND"])
    reaper.CreateTrackSend(tr, bus_tracks["SHORT_ROOM_SEND"])
  end
end

reaper.AddProjectMarker(0, false, 0.0, 0.0, "0s immediate hook check", -1)
reaper.AddProjectMarker(0, false, 8.0, 8.0, "8s arrangement continuity", -1)
reaper.AddProjectMarker(0, false, 16.0, 16.0, "16s hook/transition QC", -1)
reaper.AddProjectMarker(0, false, 28.0, 28.0, "28s short-form checkpoint", -1)
for _, marker in ipairs(qc_markers) do
  reaper.AddProjectMarker(0, false, marker.time, marker.time, marker.name, -1)
end
log_step("markers added")

reaper.UpdateArrange()

local project_save_path = "/Users/hantaeheuk/Documents/New project 3/reaper/FRESH_MIX_REBUILD.rpp"
if reaper.Main_SaveProjectEx then
  pcall(function()
    reaper.Main_SaveProjectEx(0, project_save_path, 0)
  end)
end
log_step("project save attempted")
reaper.Undo_EndBlock("Build fresh Suno to REAPER mix/master rebuild", -1)
log_step("build script done")
