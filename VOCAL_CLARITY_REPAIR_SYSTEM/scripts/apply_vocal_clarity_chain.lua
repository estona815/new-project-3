local root = [[/Users/hantaeheuk/Documents/New project 3]]
local rpp = [[/Users/hantaeheuk/Documents/New project 3/reaper/mesi_1_v44_louder_more_audible_master/mesi_1_v44_LOUDER_MORE_AUDIBLE_MASTER.rpp]]
local render_dir = [[/Users/hantaeheuk/Documents/New project 3/renders/mesi_1_v44_louder_more_audible_master]]
local trace_path = [[/Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v44_louder_more_audible_master/actual_reaper_plugin_trace.json]]
local log_path = [[/Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v44_louder_more_audible_master/build_reaper.log]]
local rows = {}
local function q(s) return string.format("%q", s) end
local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s) s=tostring(s or ""); return s:gsub("\\","\\\\"):gsub('"','\\"'):gsub("\n","\\n") end
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\n"); f:close() end end
local function add_row(track, stage, status, plugin, idx, wet, reason)
  rows[#rows+1]=string.format('{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"reason":"%s"}', esc(track), esc(stage), esc(status), esc(plugin), tonumber(idx or -1), wet and tostring(wet) or "null", esc(reason))
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end
local function write_trace()
  local f=assert(io.open(trace_path,"w"))
  f:write('{\n  "slug": "mesi_1_v44_louder_more_audible_master",\n  "rows": [\n')
  for i,row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\n" or ",\n")) end
  f:write("  ]\n}\n"); f:close()
end
local function make_track(name, db, pan, mute)
  local idx=reaper.CountTracks(0); reaper.InsertTrackAtIndex(idx,true)
  local tr=reaper.GetTrack(0,idx)
  reaper.GetSetMediaTrackInfo_String(tr,"P_NAME",name,true)
  reaper.SetMediaTrackInfo_Value(tr,"D_VOL",lin(db or 0))
  reaper.SetMediaTrackInfo_Value(tr,"D_PAN",pan or 0)
  reaper.SetMediaTrackInfo_Value(tr,"B_MUTE",mute and 1 or 0)
  return tr
end
local function insert_media(tr, path)
  local src=reaper.PCM_Source_CreateFromFile(path); if not src then error("source failed " .. path) end
  local item=reaper.AddMediaItemToTrack(tr); local take=reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item,"D_POSITION",0)
  reaper.SetMediaItemInfo_Value(item,"D_LENGTH",reaper.GetMediaSourceLength(src))
end
local function add_fx(tr, label, stage, candidates, wet, reason)
  for _,name in ipairs(candidates) do
    local idx=reaper.TrackFX_AddByName(tr,name,false,-1)
    if idx and idx >= 0 then
      if wet and reaper.TrackFX_SetWetDryMix then pcall(reaper.TrackFX_SetWetDryMix,tr,idx,wet,0,0) end
      add_row(label,stage,"loaded",name,idx,wet,reason); return idx,name
    end
  end
  add_row(label,stage,"missing_all_candidates",table.concat(candidates," | "),-1,wet,reason); return -1,nil
end
local function add_required(tr,label,stage,name,wet,reason)
  local idx,loaded=add_fx(tr,label,stage,{name},wet,reason)
  if idx < 0 or loaded ~= name then write_trace(); error("required FX missing " .. name) end
  return idx
end
local function send(src,dst,db) local s=reaper.CreateTrackSend(src,dst); reaper.SetTrackSendInfo_Value(src,0,s,"D_VOL",lin(db or 0)); return s end
os.execute("mkdir -p " .. q(render_dir)); os.execute("mkdir -p " .. q([[/Users/hantaeheuk/Documents/New project 3/reports/mesi_1_v44_louder_more_audible_master]])); os.remove(log_path); os.remove(trace_path)
reaper.Main_OnCommand(40023,0)
local ref=make_track("SOURCE full mix reference muted",-99,0,true); insert_media(ref,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/source_full_mix_reference.wav]])
local music=make_track("V43 INSTRUMENTAL BUS v42 reference balance",-0.20,0,false); insert_media(music,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/instrumental_vocal_pocket.wav]])
local lead=make_track("V44 LEAD main vocal louder more audible",-0.72,0,false); insert_media(lead,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/lead_vocal_clarity_processed.wav]])
local backing=make_track("V43 FEMALE LAYER double harmony only",-7.2,0,false); insert_media(backing,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/female_vocal_lr_support.wav]])
local chops=make_track("V43 VOCAL CHOP gap fill support only",-2.8,0,false); insert_media(chops,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/vocal_chop_gap_fill.wav]])
local printed_verb=make_track("V43 PRINTED VOCAL REVERB tucked",-6.3,0,false); insert_media(printed_verb,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/vocal_reverb_send_print.wav]])
local printed_delay=make_track("V43 PRINTED VOCAL DELAY tucked",-6.5,0,false); insert_media(printed_delay,[[/Users/hantaeheuk/Documents/New project 3/audio_work/mesi_1_v44_louder_more_audible_master/processed_stems/vocal_delay_send_print.wav]])
local verb_return=make_track("V43 RETURN ReaVerbate dark send",-45,0,false)
local delay_return=make_track("V43 RETURN ReaDelay filtered throw",-46,0,false)
send(lead,verb_return,-45); send(lead,delay_return,-47)
add_fx(music,"music_bus","instrumental vocal pocket EQ",{"VST: ReaEQ (Cockos)"},1.0,"free EQ pocket at mud/presence masks")
add_fx(music,"music_bus","instrumental dynamic pocket",{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaXcomp (Cockos)"},0.74,"free dynamic EQ instead of Ozone")
add_required(lead,"vocal_anchor","Codex Suno/AI artifact tamer FIRST SLOT clarity","JS: Codex Vocal AI Artifact Split Tamer",1.0,"mandatory Mesi first-slot clean vocal guard on main vocal")
add_fx(lead,"vocal_anchor","corrective EQ HPF de-mud box presence",{"VST: ReaEQ (Cockos)"},1.0,"HPF, de-mud, box control, guarded presence")
add_fx(lead,"vocal_anchor","Vocal Clarity De-Mud Dynamic EQ JSFX",{"JS: Vocal Clarity De-Mud Dynamic EQ"},1.0,"project JSFX for dynamic 180-350 Hz cleanup")
add_fx(lead,"vocal_anchor","TDR Nova dynamic presence/fizz guard",{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaEQ (Cockos)"},1.0,"free dynamic EQ, no paid iZotope")
add_fx(lead,"vocal_anchor","primary de-esser",{"JS: De-esser","VST3: TDR Nova (Tokyo Dawn Labs)"},1.0,"6-9 kHz consonant control")
add_fx(lead,"vocal_anchor","Vocal Clarity Presence Enhancer JSFX",{"JS: Vocal Clarity Presence Enhancer"},0.62,"guarded articulation enhancer")
add_fx(lead,"vocal_anchor","light clean compression",{"VST: ReaComp (Cockos)"},0.38,"lighter leveling so vocal stays clear without pumping noise")
add_fx(lead,"vocal_anchor","weak OTT density only",{"VST3: OTT (Xfer Records)","VST: OTT (Xfer Records)"},0.055,"reduced OTT to avoid lifting AI noise")
add_fx(lead,"vocal_anchor","Vocal Clarity Air Guard JSFX",{"JS: Vocal Clarity Air Guard"},1.0,"stronger air/fizz guard instead of blind air boost")
add_required(lead,"vocal_anchor","post OTT Codex Suno/AI artifact guard clarity","JS: Codex Vocal AI Artifact Split Tamer",1.0,"post-density AI fizz guard")
add_fx(lead,"vocal_anchor","Vocal Clarity Output Guard JSFX",{"JS: Vocal Clarity Output Guard"},1.0,"output peak guard")
add_fx(backing,"female_support_lr","support EQ",{"VST: ReaEQ (Cockos)"},1.0,"female voice is layer/double/harmony only, tucked and panned L/R")
add_fx(backing,"female_support_lr","support de-esser",{"JS: De-esser","VST3: TDR Nova (Tokyo Dawn Labs)"},1.0,"avoid side sibilance")
add_fx(chops,"vocal_chop_gap_fill","chop EQ",{"VST: ReaEQ (Cockos)"},1.0,"short support-vocal chops fill empty spots without taking lead")
add_fx(chops,"vocal_chop_gap_fill","chop de-esser guard",{"JS: De-esser","VST3: TDR Nova (Tokyo Dawn Labs)"},1.0,"keep chops tucked and non-spitty")
add_fx(printed_verb,"printed_reverb","printed reverb dark EQ",{"VST: ReaEQ (Cockos)"},1.0,"low cut/high cut so reverb does not cloud words")
add_fx(printed_delay,"printed_delay","printed delay dark EQ",{"VST: ReaEQ (Cockos)"},1.0,"filtered throw behind vocal")
add_fx(verb_return,"reverb_return","stock reverb send",{"VST: ReaVerbate (Cockos)","VST: ReaVerbate (Cockos)"},0.36,"short tucked reverb send")
add_fx(verb_return,"reverb_return","reverb low/high cut",{"VST: ReaEQ (Cockos)"},1.0,"250-350 Hz low cut, 7-9 kHz high cut target")
add_fx(delay_return,"delay_return","stock delay send",{"VST: ReaDelay (Cockos)","ReaDelay (Cockos)"},0.34,"filtered phrase-end style delay")
add_fx(delay_return,"delay_return","delay low/high cut",{"VST: ReaEQ (Cockos)"},1.0,"delay behind vocal")
local master=reaper.GetMasterTrack(0)
add_fx(master,"master","master free tonal EQ",{"VST: ReaEQ (Cockos)"},1.0,"no Ozone or paid iZotope")
add_fx(master,"master","master dynamic guard",{"VST3: TDR Nova (Tokyo Dawn Labs)","VST: ReaXcomp (Cockos)"},0.82,"low-mid/fizz guard")
add_fx(master,"master","master clean limiter",{"VST: ReaLimit (Cockos)","VST: Event Horizon Limiter/Clipper"},1.0,"clean ceiling, no saturation")
reaper.GetSetProjectInfo(0,"RENDER_SETTINGS",0,true)
reaper.GetSetProjectInfo(0,"RENDER_BOUNDSFLAG",2,true)
reaper.GetSetProjectInfo(0,"RENDER_SRATE",48000,true)
reaper.GetSetProjectInfo(0,"RENDER_CHANNELS",2,true)
reaper.GetSetProjectInfo(0,"RENDER_STARTPOS",0,true)
reaper.GetSetProjectInfo(0,"RENDER_ENDPOS",106.171000,true)
reaper.GetSetProjectInfo_String(0,"RENDER_FILE",render_dir,true)
reaper.GetSetProjectInfo_String(0,"RENDER_PATTERN","mesi_1_v44_REAPERPRINT_louder_audible_24-48",true)
reaper.GetSetProjectInfo_String(0,"RENDER_FORMAT","evaw",true)
reaper.GetSetProjectInfo_String(0,"PROJECT_NOTES","v44 louder more audible master: keep the v43 centered lead and tucked support structure, raise the main vocal slightly, and lift final loudness for easier audibility without replacing the lead or widening the support excessively.",true)
reaper.Main_SaveProjectEx(0,rpp,0)
write_trace()
log("wrapper ok")
reaper.defer(function() reaper.Main_OnCommand(40004,0) end)
