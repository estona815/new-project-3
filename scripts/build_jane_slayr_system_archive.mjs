import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const out = (...parts) => path.join(root, ...parts);

const fields = [
  'index','priority','artist_or_channel','title','youtube_url','upload_channel','video_type',
  'estimated_relevance','reason_for_relevance','visible_metadata','mood_keywords','genre_keywords',
  'sound_keywords','arrangement_keywords','vocal_keywords','drum_bass_keywords',
  'sample_melody_keywords','mix_texture_keywords','avoid_copying_notes','prompt_usable_traits'
];

const refs = [
  ['S','SYSTEM SEOUL / ycs','ycs - 너 (Official Video)','https://www.youtube.com/watch?v=TiOpGgCXeT0','SYSTEM SEOUL','music video','5','core official ycs/System Seoul result; strong reference for cold urban hook-driven structure','3:14; high-view official video; public YouTube search metadata','cold Seoul night, lonely, bittersweet, restless','Korean underground hip-hop, emotional trap, internet rap','sample-forward, glossy, sad but moving','direct hook, short sections, compressed pop-rap form','lead vocal reference only as structural context; no tone copying','tight trap drums, clean 808, crisp hats','catchy short sample lead; do not recreate melody','commercial loud, clean, not plastic','Do not copy melody, lyrics, vocal delivery, or title concept.','cold Korean underground mood; sample-forward hook; clean drums and 808'],
  ['S','SYSTEM SEOUL / ycs','ycs - 너 (Official Audio)','https://www.youtube.com/watch?v=mZ4vjIC3tmw','SYSTEM SEOUL','official audio','5','official audio counterpart; useful for metadata-level arrangement priority','3:14; official audio; public YouTube search metadata','melancholic, city, neon grey','sampled hip-hop, emotional trap','front sample, direct vocal pocket','intro-hook-verse-hook compression','preserve original vocal character if user uploads own vocal','snappy clap, bouncy 808','short loop as identity, not copied','punchy master, clear vocal/sample separation','No direct interpolation or vocal imitation.','sample-first emotional trap under 2 minutes prompt language'],
  ['S','SYSTEM SEOUL','SYSTEM SEOUL - SS-POP 2 (Full Album)','https://www.youtube.com/watch?v=RX38I72NX1s','SYSTEM SEOUL','mix','5','official full album upload; maps System Seoul ecosystem and short-song grammar','19:30; official full album; multiple short tracks','cold, youthful, urban, diaristic','Korean underground rap, pluggnb, digicore-adjacent','sample loops, light digital gloss, raw edges','many compact tracks, quick hooks, little dead air','stacked doubles/ad-libs as texture','trap hats, 808 slides, punchy kick','piano/bell/vocal-chop/guitar loops','loud but slightly raw','Use only broad structure; avoid any specific track reproduction.','album-level reference for concise, sample-led underground pop-rap'],
  ['S','SYSTEM SEOUL / sn7 / hawks / ycs / MUNZi','sn7,hawks,ycs,MUNZi - SS (Official Video)','https://www.youtube.com/watch?v=_9hOfxAC9I8','SYSTEM SEOUL','music video','5','official crew cut; high-priority for shared cadence and crew energy','2:58; official video; public search metadata','cold crew confidence, nocturnal, sharp','Korean internet rap, emotional trap','crew vocal exchanges, clean bounce','short intro, rotating parts, repeated hook energy','multiple voices; use layering idea only','hard clap, clean hats, 808 bounce','minimal lead motif; sample supports rhythm','clean, loud, underground','Do not copy flows, lyrics, voices, or crew identity.','crew-like energy with original vocal layers and compact hook structure'],
  ['S','SYSTEM SEOUL / sn7 / hawks / ycs / MUNZi','sn7, hawks, ycs, MUNZi - SS (Official Audio)','https://www.youtube.com/watch?v=hkNx-UkEFnA','SYSTEM SEOUL','official audio','5','official audio version confirms structure without relying on third-party uploads','2:59; official audio','confident, street-lit, cold','internet rap, trap, Korean underground','dry-forward rap, clean low end','hook/verse rotations','doubles and ad-libs as support','tight 808, crisp hats','short repeating motif','balanced vocal/sample/drum mix','No copying cadence or lyric phrasing.','official audio reference for punchy concise rap mix'],
  ['S','SYSTEM SEOUL - Topic','i miss ㅠ','https://www.youtube.com/watch?v=MF3EMqi0On4','SYSTEM SEOUL - Topic','topic channel','5','Topic upload; especially relevant because duration matches under-2-minute target','1:56; Topic channel; public metadata','sad, airy, lonely, moving','emotional trap, pluggnb-adjacent','short emotional loop, compressed sections','under 2 minutes, fast entry','soft background layers, not vocal cloning','clean trap drums, sub weight','melancholic lead loop','wide, glossy, not EDM','Do not reproduce melody or vocal tone.','under-2-minute emotional loop and commercial trap polish'],
  ['S','SYSTEM SEOUL - Topic','긴밤','https://www.youtube.com/watch?v=qLA-AmekqjE','SYSTEM SEOUL - Topic','topic channel','5','Topic upload with concise sad-night mood','2:12; Topic channel; public metadata','long night, melancholy, city isolation','Korean emotional hip-hop','soft sample, late-night gloss','short song with immediate mood','backing textures only','bouncy 808, restrained hats','night piano/pluck loop direction','clear, reverb-tail atmosphere','Avoid title/theme copying.','late-night sample-forward trap mood'],
  ['S','SYSTEM SEOUL - Topic','4pril','https://www.youtube.com/watch?v=NNkX0_t21Wk','SYSTEM SEOUL - Topic','topic channel','5','Topic result; short duration and SS-pop style fit prompt target','1:50; Topic channel','spring-cold, bittersweet, youthful','pluggnb, emotional rap','bright-sad plucks, glossy loop','very compact hook-first','doubles behind lead','bouncy 808, crisp clap','sparkly sample motif','loud and clean','No melody, lyric, or voice copying.','short catchy sample loop with urban sadness'],
  ['S','SYSTEM SEOUL - Topic','i need ㅠ','https://www.youtube.com/watch?v=OZy59XcOTpg','SYSTEM SEOUL - Topic','topic channel','5','Topic upload; strong under-90-second compression cue','1:29; Topic channel','urgent, sad, digital, restless','emotional trap, internet rap','minimal loop, fast hit','no long intro, quick resolution','ad-libs/doubles as texture','808 bounce, tight hats','tiny motif repeated with variation','polished but raw','Do not copy exact motif or topline.','90-second sketch-like commercial loop structure'],
  ['S','SYSTEM SEOUL - Topic','2018','https://www.youtube.com/watch?v=UNzZpub89a0','SYSTEM SEOUL - Topic','topic channel','5','Topic upload; short nostalgic internet-rap reference','1:13; Topic channel','nostalgic, cold, clipped','digicore-adjacent rap','lo-fi digital memory, small loop','micro-song, immediate hook','background texture only','simple punchy drums/sub','short nostalgic sample phrase','raw-clean balance','No direct sample recreation.','micro-arrangement with nostalgic digital edge'],
  ['S','SYSTEM SEOUL','MUNZi & sn7 - 긴밤 (long night)','https://www.youtube.com/watch?v=9VQaoUfE2Z8','SYSTEM SEOUL','music video','5','official System Seoul member result; reinforces late-night mood','2:09; official upload','late night, lonely, grey','Korean underground rap, emotional trap','sample-led, restrained digital color','compact verse/hook form','male lead with texture doubles','tight drums, sub bass','sad pluck/piano sample idea','clean low-end, vocal clarity','Do not copy voices or lyrics.','cold-night hook structure with controlled ad-libs'],
  ['S','SYSTEM SEOUL','MUNZi & sn7 - kE타mine 러oVE 너 bUT nOT ㅠ','https://www.youtube.com/watch?v=wfMnNfr-pXE','SYSTEM SEOUL','music video','5','official member upload; very short, internet-coded text aesthetics','1:48; official upload','chaotic-sad, internet, nocturnal','digicore-adjacent emotional trap','glitchy gloss, sample loop','quick hook, no long build','ad-lib textures and doubles','808 bounce, crisp percussion','looped emotional motif','raw internet polish','Avoid copying stylized title, lyrics, melody.','short sad-hyper digital rap texture without EDM drop'],
  ['S','SYSTEM SEOUL','hawks - ah ah uh uh (Official Video)','https://www.youtube.com/watch?v=Tz0L-KlAEig','SYSTEM SEOUL','music video','5','official member result; useful for harder drum/bass edge','2:09; official video','cold, cocky, minimal','trap, Korean underground rap','dry drums, focused low end','compact rap single','background ad-libs only','hard clap, centered 808','minimal motif supports vocal','clean punch, less gloss','No flow/vocal imitation.','harder System Seoul drum attitude'],
  ['S','SYSTEM SEOUL','IF SEOUL WAS TOKYO','https://www.youtube.com/watch?v=rb6JYwYwZUM','SYSTEM SEOUL','music video','5','official conceptual upload; city/cross-cultural internet mood','5:12; official video','urban, neon, detached, stylish','Korean underground, internet rap','city gloss, montage-like energy','reference for mood only, not target length','layered voices as atmosphere','trap low end, clean percussion','city-pop-like motif only as abstract cue','wide, visual, polished','Do not copy concept, melody, or title.','cold city mood and stylish digital texture'],
  ['S','SYSTEM SEOUL ARCHIVE / ycs','love&hatred - z3n, ycs','https://www.youtube.com/watch?v=y-PebPdo4-w','SYSTEM SEOUL ARCHIVE','reupload','4','archive result with ycs; useful only as surrounding metadata, not source to copy','3:00; archive/reupload','love-hate, sad, underground','emotional trap, internet rap','archive context, raw mood','short rap arrangement','do not imitate voice','trap drums, 808','melodic loop cue','less official, lower confidence','Treat as unverified archive; no melodic or vocal copying.','surrounding ycs mood vocabulary only'],
  ['S','SYSTEM SEOUL ARCHIVE / ycs / sn7','smoke - ycs, sn7','https://www.youtube.com/watch?v=vpvD9ssdiE0','SYSTEM SEOUL ARCHIVE','reupload','4','archive result with ycs/sn7; context reference only','2:07; archive/reupload','hazy, cold, night','underground rap, trap','smoky sample, raw upload context','compact song','no voice imitation','808 and hats','hazy short loop','raw, not overpolished','Use only general traits; avoid reupload-dependent copying.','hazy compact emotional trap cue'],
  ['S','SYSTEM SEOUL ARCHIVE / z3n / ycs','take off - z3n, ycs','https://www.youtube.com/watch?v=fMFQXbbZtDc','SYSTEM SEOUL ARCHIVE','reupload','4','archive result with ycs; useful as ecosystem signal','2:52; archive/reupload','restless, upward, cold','Korean internet rap','short motif, trap bounce','short hook/verse','ad-lib texture only','clean 808 bounce','simple loop focus','raw archive texture','Do not copy title, lyrics, melody.','restless bounce and sample-forward arrangement'],
  ['S','SYSTEM SEOUL / ycs','ycs - 黎崍阿 (demo)','https://www.youtube.com/watch?v=g4fCc_MpPlE','아라한','reupload','4','ycs-related demo surfaced in search; lower because not official','1:48; reupload/demo metadata','sad, demo-like, intimate','emotional trap, digicore-adjacent','rough short loop','under 2 minutes','no vocal tone copying','bouncy 808, crisp hats','melodic sample identity','demo rawness','Unverified reupload; use only broad duration/energy cue.','brief demo-like urgency and sample lead'],
  ['A','SYSTEM SEOUL ARCHIVE','SYSTEM SEOUL - SS-POP [Full Album]','https://www.youtube.com/watch?v=b5qKe1tZZhI','SYSTEM SEOUL ARCHIVE','reupload','4','album archive; useful to map playlists but not official source','17:23; archive full album','cold, internet, youthful','SS-pop, underground rap','short loops, many compact ideas','album sequence of short songs','varied ad-libs/doubles','trap and 808 patterns','sample-driven track IDs','raw archive loudness','Do not copy any track; official sources take priority.','broad SS-pop sequencing vocabulary'],
  ['A','playlist curator','𝐏𝐥𝐚𝐲𝐥𝐢𝐬𝐭 시스템서울을싹다','https://www.youtube.com/watch?v=KQMpe5IzvNE','Zuyuu','playlist','4','popular System Seoul playlist; confirms listener framing','23:11; playlist metadata','fan-curated, cold, emotional','Korean emotional hip-hop/R&B','playlist-level sample/808 context','many short songs collected','not for vocal copying','trap/pluggnb drums','catchy loop emphasis','variable upload quality','Playlist only; avoid copying selected songs.','fan perception: sad but addictive System Seoul feel'],
  ['A','playlist curator','[Playlist] SS-POP 3 미리듣기.mp3','https://www.youtube.com/watch?v=-OywsCJ6tGU','지호','playlist','4','SS-POP preview playlist; useful ecosystem signal','29:24; playlist/preview','anticipatory, underground','SS-pop, digicore-adjacent','snippets, raw preview feel','fragmented short ideas','varied background vocals','trap bounce, subs','brief motifs','unmastered/preview texture','Do not use unreleased-specific material.','short preview energy as structure cue only'],
  ['A','playlist curator','SYSTEM SEOUL [UNKNOWN PLAYLIST]','https://www.youtube.com/watch?v=BP4PnRpv1AM','서울은서울','playlist','3','fan playlist; useful for community tagging','48:58; playlist','underground, hidden, cold','Korean underground rap','fan-archive context','playlist, not single structure','not applicable','varied','varied','varied','No direct track copying.','community context for reference map'],
  ['A','playlist curator','[playlist] System Seoul feelaylist','https://www.youtube.com/watch?v=ABdBxu-dsrA','Feelaylist-Music','playlist','3','low-view playlist but title signals feel-based consumption','37:38; playlist','emotional, late night','playlist, emotional hip-hop','curated mood context','playlist sequence','not applicable','varied','varied','variable','Use as mood taxonomy only.','listener vocabulary: System Seoul feel/playlist'],
  ['A','type beat producer','[Free] SYSTEM SEOUL Type Beat l Pluggnb Type beat l Prod.JMPC l','https://www.youtube.com/watch?v=qcahAveTDvw','JMPC BEATS','mix','4','type-beat result shows public genre tags around System Seoul','2:21; type beat','melancholic, bouncy','pluggnb, type beat, emotional trap','pluggnb chords, clean drums','beat-form, short','no lead vocal','808 bounce, crisp drums','bell/pluck loop','producer-mix polish','Do not use as substitute for official references.','genre tags: System Seoul + pluggnb + short beat'],
  ['A','type beat producer','[FREE] Nettspend X System Seoul Type Beat - supermagnetic','https://www.youtube.com/watch?v=Sf_4Bao4buM','ericht','mix','4','public cross-tag with internet rap scene','1:42; type beat','energetic, digital, cold','internet rap, pluggnb','digital bounce, short loop','under 2 minute beat','no vocal','fast hats, 808','magnetic pluck idea','clean beat mix','Avoid artist imitation and title concept.','short internet-rap energy support'],
  ['A','type beat producer','[FREE] SYSTEM SEOUL x SLAYR TYPE BEAT - zㅣ그mㅊurㄹum..','https://www.youtube.com/watch?v=iPVWrci9LEA','BYRESH','mix','4','bridges System Seoul and slayr search context','1:57; type beat','cold, energetic, digital','digicore, internet rap, type beat','glossy motion, sample bounce','short beat form','no lead vocal','808, crisp drums','digital lead loop','loud beat polish','Do not copy title styling or any beat.','controlled kinetic digital energy behind System Seoul mood'],
  ['A','type beat producer','[무료비트 / FREE] 시스템 서울 타입 디지코어 비트 Error','https://www.youtube.com/watch?v=EQQbIU8oBLs','알츠 ALZ','mix','4','Korean-language type-beat result; confirms digicore tag association','1:47; type beat','sad, glitch, cold','digicore, type beat, trap','light glitch, pluck loop','under 2 minutes','no lead vocal','tight 808, snap drums','error-like digital motif','beat mix','Avoid copying beat or title.','restrained digicore texture as spice'],
  ['A','type beat producer','SYSTEM SEOUL X Effie Type Beat Drill X Hyperpop X PLUGGNB','https://www.youtube.com/watch?v=xs3BF6Z2Ays','the cillian','mix','3','genre-tag map; lower because broader than target','3:05; type beat','emotional, anime, energetic','drill, hyperpop, pluggnb','genre-fusion tags','beat arrangement','no vocal','drill/trap low end','anime/emotional melody tag','producer mix','Do not overuse drill/hyperpop.','only minor hyperpop/drill texture vocabulary'],
  ['A','type beat producer','[Free] Westwood Type Beat l System Seoul Type Beat l Prod.JMPC','https://www.youtube.com/watch?v=ui6SxfNX804','JMPC BEATS','mix','3','System Seoul adjacent type beat; useful for scene overlap','1:56; type beat','cold, sharp, youthful','internet rap, pluggnb','fast digital bounce','short beat','no vocal','crisp drums, 808','short synth/pluck motif','clean','Avoid artist imitation.','short internet beat structure'],
  ['A','type beat producer','*free* SYSTEM SEOUL + pluggnb type beat - love u','https://www.youtube.com/watch?v=MGcE2MsJ1Ao','Nib','mix','3','public tag signal for pluggnb-emotional lane','unknown from search archive; type beat','romantic-sad, cold','pluggnb, emotional trap','soft chords, bounce','beat form','no vocal','808 and hats','soft sample/chord loop','bedroom-clean','No copying; use tags only.','romantic pluggnb color behind trap drums'],
  ['A','type beat producer','(Free) SYSTEM SEOUL Type beat Back','https://www.youtube.com/watch?v=4el2aFNPJHE','KOSHI BEAT','mix','3','System Seoul type beat context','2:53; type beat','nostalgic, sad','type beat, emotional trap','sample loop, trap bounce','beat structure','no vocal','808, hats','sample motif','producer beat mix','Do not copy beat.','nostalgic sample loop and trap bounce'],
  ['A','type beat producer','[FREE] System Seoul Type Beat - Nostalgia','https://www.youtube.com/watch?v=xeHhY7xS2mE','ericht','mix','3','nostalgia tag aligns with bittersweet target','2:31; type beat','nostalgic, cold','pluggnb, type beat','emotional loop','short beat','no vocal','808 bounce','nostalgic melody','clean','Avoid direct beat copying.','nostalgic but energetic sample prompt language'],
  ['A','SYSTEM SEOUL in cypher context','bbs Asia Underground Cypher 2026 ft. SYSTEM SEOUL','https://www.youtube.com/watch?v=pDDyUiH1dVE','babyselects and Cash Cow Music','reupload','4','public search result ties System Seoul to Asia underground scene','8:40; cypher result','crew, underground, international','underground rap, cypher','rap-focused, less sample-specific','cypher structure, not target form','voice identity not usable','hard rap drums','minimal sample cue','live/cypher mix','Do not copy verses or voices.','scene positioning: Korean underground confidence'],
  ['A','AS IS / SYSTEM SEOUL context','여기있는국힙모르면나가라 ... SYSTEM SEOUL / AS/IS vol.1','https://www.youtube.com/watch?v=dkFgEDUnX1A','AS IS','reupload','4','places System Seoul in current Korean underground playlist/editorial context','34:04; playlist/editorial','scene, cool, underground','Korean hip-hop, underground','playlist/editorial context','long mix, not target form','not applicable','varied drums','varied samples','varied','Use only scene taxonomy.','Korean underground context and audience framing'],
  ['B','slayr','slayr - Eyesight (Official Visualizer)','https://www.youtube.com/watch?v=iSrkDPbLCYc','slayr','music video','3','secondary reference for energetic digital texture only','2:26; official visualizer','aggressive, glossy, fast','internet rap, digicore-adjacent','digital shine, quick motion','short rap single','do not imitate voice','hard drums, energetic low end','synthetic hooks','loud modern master','Use only energy/texture; no artist imitation.','add controlled digital energy without EDM drop'],
  ['B','slayr','slayr - Brand New (Official Visualizer)','https://www.youtube.com/watch?v=hkkBiXS6A7o','slayr','music video','3','secondary short-length slayr texture cue','1:56; official visualizer','fresh, sharp, bright-dark','internet rap','glossy, kinetic','under 2 minutes','no vocal imitation','punchy drums, 808','digital motif','clean loud','No artist, melody, or vocal copying.','short energetic digital rap texture'],
  ['B','slayr','slayr - Flashout Freestyle (Official Visualizer)','https://www.youtube.com/watch?v=fOjk1JlGr3U','slayr','music video','3','secondary reference for aggressive movement','2:55; official visualizer','flashy, urgent','internet rap, trap','fast edits, digital gloss','freestyle-like energy','do not copy delivery','hard drums','repeating synth motif','loud','Use as texture only.','faster movement while keeping hip-hop drums'],
  ['B','slayr','slayr - Racks (Official Visualizer)','https://www.youtube.com/watch?v=IZUIn9s5yc8','slayr','music video','3','secondary reference for rap bounce and digital sheen','2:39; official visualizer','confident, icy','internet rap, trap','glossy rap mix','short single','no voice copying','808, snappy percussion','simple synthetic motif','commercial loud','No imitation.','clean digital rap bounce'],
  ['B','slayr','slayr - Toxic (Official Visualizer)','https://www.youtube.com/watch?v=iS7F8Nx6dZw','slayr','music video','2','secondary but longer; use texture only','4:30; official visualizer','dark, toxic, energetic','internet rap','distortion, gloss','longer than target','no voice copying','hard low end','synthetic hook','loud, distorted edge','Do not import length or specific vocal tone.','distorted digital gloss as subtle layer'],
  ['B','slayr','slayr - Died But Came Back (OFFICIAL MUSIC VIDEO)','https://www.youtube.com/watch?v=3qMLygNGvhM','slayr','music video','3','secondary current official music video result','2:32; official video','reborn, aggressive, dark','internet rap, trap','hard-edged digital rap','compact single','no vocal imitation','hard drums/808','minimal melodic motif','commercial loud','No direct imitation.','aggressive texture, not EDM'],
  ['B','slayr context','slayr shows how BloodLuxe was made','https://www.youtube.com/watch?v=BmWNZWdRdiE','Underground LIVE','live','2','production-context result; useful only for public sound-design vocabulary','29:28; production/live context','process, energetic','internet rap production','sound design discussion context','not song form','not applicable','production drums/808 context','not applicable','not applicable','Do not copy specific production choices.','texture vocabulary: digital gloss, motion, hard drums'],
  ['B','Jane Remover','Jane Remover - Dancing with your eyes closed','https://www.youtube.com/watch?v=QgyW9qjgIf4','Jane Remover','music video','3','secondary emotional internet-rock/digital texture reference','3:55; official artist upload','emotional, wide, blurry, cathartic','internet rock, digicore-adjacent, shoegaze-pop','wide guitars/synths, noisy emotion','longer than target; texture only','no vocal imitation','drums not primary for target','emotional melodic wash','wide reverb, haze','Use only atmosphere; keep hip-hop core.','emotional digital haze behind sampled hip-hop'],
  ['B','Jane Remover','Jane Remover - Lips','https://www.youtube.com/watch?v=De6Y3meK4b0','Jane Remover','music video','3','secondary Census Designated-era texture cue from search metadata','public official/artist result context','raw, wide, uneasy','indie rock, digital noise','guitar haze, distortion','not target structure','no vocal imitation','rock drums not primary','melodic haze','wide/noisy','Do not copy melody, lyric, or vocal tone.','use subtle noisy emotional width only'],
  ['B','Jane Remover','Jane Remover - Census Designated','https://www.youtube.com/watch?v=ac0nV0LmJMY','Jane Remover','music video','3','secondary reference for expansive emotional digital atmosphere','public search metadata context','bleak, open, suburban, digital','internet rock, shoegaze, experimental pop','wide distorted layers','longer form; texture only','no vocal imitation','not hip-hop drum model','guitar/synth wash','hazy, wide, noisy','Do not copy song identity.','background emotional haze, not structure'],
  ['B','Jane Remover','Jane Remover - your clothes','https://www.youtube.com/watch?v=eC_fmqPGczU','Jane Remover','topic channel','2','Frailty-era Topic result; use only mood vocabulary','4:15; Topic metadata','fragile, nostalgic, intimate','digicore, internet pop','fragile digital texture','longer than target','no vocal imitation','not drum model','emotional melodic idea','soft haze','No melody/vocal copying.','fragile digital emotion as background layer'],
  ['B','Jane Remover','Jane Remover - let’s go home','https://www.youtube.com/watch?v=GjeIkUIm10U','Jane Remover','topic channel','2','Frailty-era Topic result; secondary emotional texture','5:33; Topic metadata','homesick, blurry, emotional','digicore, internet rock','wide nostalgic layers','long form, not target','no vocal imitation','not drum model','melodic wash','hazy master','Use only mood; keep System Seoul priority.','homesick digital atmosphere behind trap drums'],
  ['B','Jane Remover context','Jane Remover - Frailty ALBUM REVIEW','https://www.youtube.com/watch?v=KlpK7H3k0M4','theneedledrop','reupload','2','review result confirms public genre discourse, not direct sound source','review metadata','emotional, internet-era','digicore, indie, experimental pop','critical vocabulary only','not song form','not applicable','not applicable','not applicable','not applicable','Do not quote/copy review; use genre tag context only.','genre discourse: emotional internet/digicore texture'],
  ['B','type beat producer','[Free] slayr x jane remover type beat','https://www.youtube.com/watch?v=Cs_vBhk7RUA','Prod.AElith','mix','2','secondary combined type-beat tag; lower than official sources','2:05; type beat','digital, energetic, emotional','type beat, internet rap','gloss + emotion','short beat','no vocal','trap drums/808','digital lead','producer mix','Do not imitate named artists.','combined energy/emotion vocabulary only'],
  ['B','type beat producer','free 2hollis + jane remover + slayr type beat - thousands','https://www.youtube.com/watch?v=em5_dV6s2ts','prod. hilen','mix','2','type-beat search result for scene overlap','2:00; type beat','emotional, energetic','internet rap, type beat','digital shine, distorted color','2-minute beat','no vocal','hard drums/sub','synthetic motif','loud beat','No copying or artist mimicry.','2-minute digital rap beat texture'],
  ['B','Korean scene context','[PLAYLIST]국내 플럭앤비 힙합 모음/KOR pluggnb mix','https://www.youtube.com/watch?v=CV6garim7eY','SimhoonPlaylist','playlist','3','surrounding Korean pluggnb context','22:11; playlist','soft, bouncy, emotional','Korean pluggnb, hip-hop','pluggnb chords, bounce','playlist','not applicable','808 bounce, hats','soft plucks/chords','playlist mix','Use only broad genre context.','Korean pluggnb bounce as support'],
  ['B','Korean scene context','kpop pluggnb mix vol 4','https://www.youtube.com/watch?v=Am0MZW5cVoM','yakknae','playlist','2','pluggnb texture context; avoid K-pop demo drift','9:55; mix','bright-sad, bouncy','pluggnb, K-pop flip context','soft chords, crisp bounce','mix','not applicable','808 bounce','R&B/pluck melodies','internet mix','Avoid idol-pop gloss and known-song flipping.','pluggnb bounce but keep underground tone'],
  ['B','Korean scene context','둘만 아는 Digicore... 국힙 MixSet','https://www.youtube.com/watch?v=Exaine6bouw','Lunatic q','mix','2','Korean digicore/hyperpop mix context','28:19; mix','niche, digital, energetic','digicore, hyperpop, K-hip-hop','glitch, chiptune color','mix','not applicable','fast hats, subs','digital leads','mixset','Do not overdo hyperpop.','subtle digicore ear candy'],
  ['B','SoundCloud scene','Digicore the Underground Sound: Scenes','https://www.youtube.com/watch?v=WbFPhksi1Rg','SoundCloud','music video','2','broader digicore scene context','4:05; public YouTube result','internet, underground, digital','digicore','glitch, digital emotion','not target form','not applicable','varied','digital melodies','scene doc mix','Use only genre context.','digicore texture vocabulary'],
  ['B','Korean scene context','The Effie Story - a new Korean rap wave','https://www.youtube.com/watch?v=kjJs6npX6g4','Chefkoch','reupload','2','surrounding Korean hyperpop/rap context','6:39; commentary','new wave, underground','Korean rap, hyperpop-adjacent','scene vocabulary','not song form','not applicable','not applicable','not applicable','not applicable','Use only broad scene context.','Korean new-wave rap positioning'],
  ['C','lyrics/reupload','SYSTEM SEOUL - 너 [가사/Lyrics]','https://www.youtube.com/watch?v=6mzPje5JoBs','HipArchive','reupload','1','lyrics upload; useful only to identify popularity, excluded from prompt traits','3:14; lyrics/reupload','not used','not used','not used','not used','not used','not used','not used','not used','Lyrics copying is prohibited; exclude from creative source.','excluded: popularity signal only'],
  ['C','reaction/review','[해체분석] SYSTEM SEOUL - SS-POP2 album review/reaction','https://www.youtube.com/watch?v=B5YEhUBv9ro','통세우','reupload','1','reaction/review result; not used as sound reference','1:30:49; reaction/review','not used','not used','not used','not used','not used','not used','not used','not used','Do not copy commentary; not a music source.','excluded: discussion only'],
  ['C','AI cover','SYSTEM SEOUL - 너 (여자 AI cover)','https://www.youtube.com/watch?v=-uQLlTNBPVE','에아뮤','unrelated','0','AI cover explicitly excluded by project rules','2:19; AI cover','not used','not used','not used','not used','not used','not used','not used','not used','AI voice conversion/cover not used.','excluded: AI cover risk'],
  ['C','instrumental extraction','(inst) system seoul - 너','https://www.youtube.com/watch?v=-RIcLJgUoik','룰루휘눌','reupload','0','instrumental extraction/reupload; excluded','3:14; inst/reupload','not used','not used','not used','not used','not used','not used','not used','not used','Do not use extracted instrumental.','excluded: inst extraction'],
  ['C','unrelated','SLAYER - Repentless (OFFICIAL MUSIC VIDEO)','https://www.youtube.com/watch?v=yjb0j9l1sz4','Slayer','unrelated','0','metal band result from slayr query; unrelated','4:37; unrelated search collision','not used','not used','not used','not used','not used','not used','not used','not used','Unrelated homophone result.','excluded'],
  ['C','short/unrelated','hyperpop hashtag short','https://www.youtube.com/watch?v=x0G9Zm3f9FE','S4d Bills','short','0','short hashtag result; too little metadata and low relevance','0:40; short-like metadata','not used','not used','not used','not used','not used','not used','not used','not used','Shorts are not used as references.','excluded']
].map((row, i) => Object.fromEntries(fields.map((field, idx) => [field, field === 'index' ? i + 1 : row[idx - 1]])));

const phrase = {
  core: [
    'sampled Korean underground emotional hip-hop','cold Seoul night internet rap','sample-forward emotional trap',
    'Korean underground pluggnb trap','short-form SS-pop inspired hip-hop','urban melancholic trap rap',
    'sampled hip-hop with digicore seasoning','cold Korean emotional rap beat','commercial underground internet rap',
    'pluggnb-leaning sampled trap','melodic Korean underground hip-hop','compressed pop-rap with raw edges',
    'bittersweet sample-based trap','night-drive Korean internet rap','minimal hook-first emotional hip-hop',
    '808-driven sampled pluggnb','glossy but raw underground rap','sad energetic hip-hop under two minutes',
    'cold city sample rap','melodic trap with restrained hyperpop texture'
  ],
  mood: [
    'cold Seoul alley at 2 a.m.','grey neon apartment-window loneliness','sad but still moving',
    'bittersweet underground confidence','late-night city isolation','icy youth-club melancholy',
    'rainy concrete and phone-screen glow','detached but emotional','street-lit romantic regret',
    'not bright idol pop, more underground and private','lonely subway-platform energy','urban sadness with bounce',
    'small-room emotion, big low end','cool Korean underground mood','fragile but cocky',
    'winter neon trap feeling','muted city colors','sad smile, fast pulse','night bus nostalgia','cold digital romance'
  ],
  sample: [
    'catchy chopped piano sample loop in front','short bell-pluck lead as the hook identity','melancholic vocal-chop texture without recognizable lyrics',
    'two-bar guitar sample loop with tight edits','glossy synth lead sampled like a hook','tiny nostalgic motif repeated with variation',
    'sample melody louder than pads but below vocal','loop that enters in the first four seconds','bitcrushed pluck loop kept musical',
    'sad R&B chord stab chopped into hip-hop rhythm','no buried sample melody','sample-forward intro, no ambient waiting',
    'simple memorable lead, not a copied melody','short phrase with pitch-shifted response','cold music-box pluck loop',
    'filtered sample opens then drums lock in','emotional loop, minimal chord clutter','one strong motif instead of many weak ideas',
    'hooky sample that survives on phone speakers','avoid direct interpolation or recognizable borrowed melody'
  ],
  drums: [
    'tight trap drums with crisp hi-hats','snappy clap and punchy kick','bouncy 808 slides that stay clean',
    'hard but uncluttered low end','808 carries the groove without masking the sample','short hat rolls, no EDM risers',
    'clean sub bass with commercial weight','dry snare, sharp transient','minimal percussion but strong pocket',
    'trap bounce, not festival four-on-the-floor','centered kick and 808 relationship','punchy drums that feel mastered',
    'slightly swung hats for bounce','no weak drums','sub bass tight enough for release',
    '808 movement in hook only, simpler in verse','drums enter early','clean drum bus saturation',
    'no dubstep wobble bass','hard low end with headroom'
  ],
  slayr: [
    'restrained kinetic digital gloss as a background accent','kinetic internet-rap energy without copying any artist',
    'quick glitch ear candy around transitions','hard shiny texture behind the hip-hop groove','brief distorted synth flashes',
    'fast motion, no generic EDM drop','aggressive polish in percussion only','digital sparkle kept under the sample',
    'clipped ad-lib effects as texture','hyperactive texture in small doses','bright digital edge, cold mood intact',
    'movement from drum fills, not festival buildup','internet-rap sheen, no artist imitation','short noisy risers under one beat',
    'glossy distortion tucked behind the lead','sharp synthetic accents','energy lift after hook, not a drop',
    'restless edits but stable groove','controlled chaos at transitions','digital pressure without plastic synth stacks'
  ],
  jane: [
    'emotional digital haze used only as atmosphere','wide blurry reverb behind the sample',
    'shoegaze-like noise tucked low','fragile internet-rock feeling without rock takeover','emotional distortion tail after hooks',
    'soft wall of texture in the background','nostalgic digital noise, subtle','wide chorus shimmer under the melody',
    'hazy guitars as pad texture only','cathartic feeling but trap drums stay central','blurred emotional edges',
    'bedroom-internet sadness, commercially mixed','noise bloom in transitions','misty reverb, no washed-out drums',
    'intimate digital melancholy','fuzzy texture under final hook','dreamy width without losing sample focus',
    'emotional air, not a copied vocal tone','subtle crushed ambience','wide background layer, not main genre switch'
  ],
  vocal: [
    'female vocals only as background ad-libs, harmonies, doubles, or texture','no female lead vocal takeover',
    'preserve original vocal character if uploaded vocals are used','do not replace the singer','airy backing harmony behind the main vocal',
    'short distant ad-libs at hook endings','soft doubles mixed low','chopped non-lyrical vocal texture only',
    'no robotic AI vocal','human, natural vocal edges','lead vocal remains original and centered',
    'background layers wide, lead dry enough','no idol-style belting','no copied vocal tone','ad-libs as atmosphere, not melody owner',
    'subtle harmony stacks in final hook','female texture under sample, not above it','avoid vocal cloning or artist imitation',
    'keep diction original, no forced accent','small doubles for thickness only'
  ],
  mix: [
    'commercial loud master, clean but not plastic','sample-forward mix with punchy low end','wide reverb tails but clear drums',
    '808 audible on small speakers','mastered like a real underground release','slightly raw edges, polished center',
    'no cheap AI EDM sheen','no overproduced idol-pop gloss','clear separation between sample, vocal, and 808',
    'loud but not crushed','modern streaming-ready trap master','tight stereo image with wide background texture',
    'clean hats, warm mids','no muddy low end','controlled saturation on drums',
    'sample is upfront and addictive','vocal layers tucked tastefully','low end mono and solid','glossy top without plastic synths',
    'finished record texture, not demo'
  ],
  arrangement: [
    'under 2 minutes total','hook appears within 15 seconds','0:00 sample tag, 0:08 drums, 0:20 hook',
    'compact hook-verse-hook-outro','no long intro','no long buildup','no generic drop section',
    'first eight seconds reveal the main sample','verse stays short and rhythmic','final hook before 1:35',
    'outro ends quickly, no fade wandering','one brief break only','energy change through drum mute, not EDM riser',
    'two hooks maximum, no extended bridge','1:45 to 1:58 target length','short pre-hook optional under four bars',
    'every section serves the sample','no random genre switch','song feels complete, not loop dump','radio-ready micro single structure'
  ],
  negative: [
    'generic EDM','festival drop','K-pop idol demo','bright idol pop','robotic AI vocal','cheesy future bass',
    'dubstep wobble','cinematic trailer','corporate pop','plastic synth','overproduced pop','random genre switch',
    'weak drums','buried sample melody','long intro','long buildup','vocal replacement','female lead vocal takeover',
    'artist imitation','same melody','same lyrics','same vocal tone','direct sample copy','AI cover voice',
    'karaoke instrumental extraction','washed-out drums','muddy 808','too much hyperpop','rock song takeover','four-minute structure'
  ]
};

const mainPrompts = Array.from({length: 30}, (_, i) => {
  const a = phrase.sample[i % phrase.sample.length];
  const b = phrase.drums[(i * 2) % phrase.drums.length];
  const c = phrase.slayr[(i * 3) % phrase.slayr.length];
  const d = phrase.jane[(i * 5) % phrase.jane.length];
  return `Sampled Korean underground emotional hip-hop, cold Seoul night mood, sad but energetic, under 2 minutes total. Build the track around a ${a}; keep the sample melody addictive and upfront without copying any reference. Use ${b}, bouncy 808 or tight sub bass, and a compact hook-verse-hook structure with the hook inside 15 seconds. Add ${c}. Add ${d}. Female vocals only as low background ad-libs, harmonies, doubles, or non-lyrical texture; preserve original vocal character if uploaded vocals are used. Commercial loud mix, clean drums, clear 808, wide but controlled reverb. Avoid artist imitation, same melody, same lyrics, same vocal tone, generic EDM drop, K-pop idol demo, plastic AI sound, long intro, long buildup.`;
});

const shortPrompts = Array.from({length: 30}, (_, i) =>
  `Under 2 minutes. ${phrase.core[i % 20]}, cold sad-but-bouncy city mood. Upfront original chopped sample hook; ${phrase.drums[i % 20]}. Subtle digital gloss/haze only. Female backing layers only; preserve uploaded vocal. No EDM, K-pop demo, artist imitation.`
);

const strengthen = {
  'System Seoul/ycs 감성 강화': phrase.mood.slice(0, 10).map(x => `Push the ${x} feeling while keeping the track original and sample-forward.`),
  '샘플링 힙합 강화': phrase.sample.slice(0, 10).map(x => `Make the beat more sampled-hip-hop: ${x}.`),
  'slayr식 에너지 질감 강화': phrase.slayr.slice(0, 10).map(x => `Add energy as secondary texture: ${x}.`),
  'Jane Remover식 감정적 디지털 질감 강화': phrase.jane.slice(0, 10).map(x => `Add emotional digital atmosphere only: ${x}.`),
  '디지코어/플러그앤비 질감 강화': [
    'Add soft pluggnb chords behind the sample, not replacing it.','Use tiny glitch fills between hook phrases.',
    'Use glossy plucks and sparse counter-melodies.','Keep hyperpop texture under 15 percent of the arrangement.',
    'Add bitcrushed ear candy in transitions only.','Use bouncy pluggnb 808 motion.',
    'Use bright digital accents while keeping the mood cold.','Keep the drums trap-centered, not dance-pop.',
    'Add a short pitch-shifted response to the sample.','Use airy pads low in the mix.'
  ],
  '드럼/808 강화': phrase.drums.slice(0, 10).map(x => `Prioritize drum/bass impact: ${x}.`),
  '보컬 레이어 제어': phrase.vocal.slice(0, 10).map(x => `Vocal control: ${x}.`),
  '2분 이내 구조 제어': phrase.arrangement.slice(0, 10).map(x => `Arrangement control: ${x}.`)
};

const fixes = [
  'If it sounds like EDM, remove all risers and drops; request trap drums, sample loop, and no festival build.',
  'If it sounds like K-pop idol demo, make the mood colder, less bright, less belted, and more underground.',
  'If the sample is buried, say: sample melody upfront, louder than pads, main identity of the song.',
  'If drums are weak, say: punchy trap kick, snappy clap, crisp hats, tight 808 with commercial low end.',
  'If 808 is muddy, say: clean mono sub, fewer sustained notes, kick/808 separation.',
  'If female vocal becomes lead, say: female vocals background ad-libs/harmonies only, no lead takeover.',
  'If uploaded vocal changes character, say: preserve original vocal character, do not replace singer or tone.',
  'If the song is too long, say: under 1:55, hook in 15 seconds, no bridge, quick outro.',
  'If it copies a reference too closely, say: original melody, original lyrics, no artist imitation, only genre traits.',
  'If hyperpop is too much, say: restrained digicore texture, hip-hop groove stays central.',
  'If it becomes rock, say: emotional haze only, trap drums and 808 remain central.',
  'If mix sounds cheap, say: commercial master, clean but not plastic, loud but not crushed.',
  'If intro drags, say: main sample starts immediately, drums by 8 seconds.',
  'If chorus is not catchy, say: stronger two-bar sample motif and repeated hook rhythm.',
  'If arrangement feels random, say: compact hook-verse-hook-outro, no genre switch.',
  'If vocals are robotic, say: human natural edges, no robotic AI vocal, no synthetic lead.',
  'If it is too bright, say: cold grey neon mood, muted palette, underground sadness.',
  'If it is too slow, say: sad but energetic bounce, crisp hats, moving 808.',
  'If it lacks space, say: wide background reverb but dry drums and clear sample.',
  'If it sounds like a loop dump, say: finished micro single with intro, hook, verse, final hook, outro.'
];

const best = [
  ['System Seoul/ycs 중심 안정형','Sampled Korean underground emotional hip-hop, cold Seoul night atmosphere, sad but energetic, under 2 minutes. Catchy chopped piano/bell sample loop is the main identity from the first seconds. Tight trap drums, crisp hats, snappy clap, bouncy 808. Subtle digicore gloss and emotional haze only as background texture. Female vocals only as distant ad-libs, harmonies, doubles, or non-lyrical texture; preserve original vocal character if uploaded vocals are used. Commercial loud mix, clean but not plastic, no long intro.','generic EDM, festival drop, K-pop idol demo, bright idol pop, robotic AI vocal, artist imitation, same melody, same lyrics, female lead vocal takeover'],
  ['System Seoul/ycs + sampled hip-hop 강화','Under 2 minutes. Cold Korean underground sampled hip-hop with a sad but moving Seoul-night mood. Build everything around an upfront chopped sample lead: piano, bell, guitar, or non-lyrical vocal chop, original melody only. Drums enter early with punchy kick, crisp hats, snappy clap, and clean 808 bounce. Keep pluggnb chords low behind the sample. Female backing layers only; preserve uploaded vocal character. Finished streaming-ready master, no EDM or idol-pop gloss.','buried sample melody, long intro, generic EDM drop, direct sample copy, same melody, same lyrics, K-pop idol demo, weak drums'],
  ['System Seoul/ycs + slayr 에너지 보조','Cold Seoul underground emotional trap, under 2 minutes, Korean underground mood first. Upfront catchy sample loop, hard clean drums, bouncy 808, quick hook inside 15 seconds. Add kinetic internet-rap energy only as secondary digital gloss: quick glitch fills, shiny distortion flashes, restless transition edits. No EDM drop. Female vocals stay background texture only; preserve original vocal character. Commercial clean master with raw underground edges.','artist imitation, festival drop, dubstep wobble, too much hyperpop, plastic synth, vocal replacement, female lead takeover'],
  ['System Seoul/ycs + Jane Remover 감정 질감 보조','Under 2 minutes. Sample-forward Korean underground emotional hip-hop with cold city sadness and trap bounce. Main hook is a short original chopped sample motif. Tight drums and clean 808 stay central. Add emotional digital haze only in the background: wide blurry reverb, faint noisy texture, soft shoegaze-like air, never a rock takeover. Female ad-libs/harmonies only, preserve uploaded vocal character. Loud clean master, not plastic.','rock song takeover, washed-out drums, long buildup, same vocal tone, same melody, same lyrics, K-pop idol demo'],
  ['digicore/pluggnb 질감 강화','Under 2 minutes. Cold Korean underground sample rap with pluggnb bounce and restrained digicore ear candy. The addictive sample lead starts immediately and remains the center. Use crisp trap hats, snappy clap, punchy kick, and bouncy 808 slides. Add soft pluggnb chords, tiny glitch fills, pitch-shifted non-lyrical textures, and glossy plucks behind the groove. Female vocals only as background layers; preserve original vocal character.','generic EDM, cheesy future bass, plastic synth, random genre switch, overproduced pop, weak drums, buried sample melody'],
  ['원본 보컬 유지 + 여성 백보컬 레이어','Under 2 minutes. Cold Seoul-night sampled emotional trap with commercial underground mix. Preserve original vocal character if uploaded vocals are used; do not replace the singer, tone, accent, or identity. Female vocals are only low background ad-libs, harmonies, doubles, or chopped non-lyrical texture. Main identity is an original catchy sample loop with tight trap drums and clean bouncy 808. Subtle digital gloss and emotional haze, no EDM/K-pop drift.','vocal replacement, female lead vocal takeover, robotic AI vocal, idol vocal belt, same vocal tone, artist imitation, same lyrics'],
  ['2분 이내 상업 음원 압축형','Finished micro single under 1:55. Cold Korean underground sampled hip-hop, sad but energetic. Main sample appears at 0:00, drums by 0:08, hook by 0:15, short verse, final hook, quick outro. Catchy original chopped sample melody, tight trap drums, crisp hats, snappy clap, punchy kick, clean 808/sub. Subtle kinetic digital energy and emotional haze only as background seasoning. Female backing layers only, preserve uploaded vocal character.','long intro, long buildup, bridge, generic EDM drop, K-pop idol demo, weak drums, buried sample, artist imitation']
];

function csvEscape(v) {
  const s = String(v ?? '');
  return /[",\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
}

function write(file, body) {
  const full = out(file);
  if (fs.existsSync(full) && process.env.OVERWRITE_GENERATED !== '1') {
    throw new Error(`Refusing to overwrite existing file: ${file}`);
  }
  fs.mkdirSync(path.dirname(full), {recursive: true});
  fs.writeFileSync(full, body);
}

const csv = [fields.join(','), ...refs.map(r => fields.map(f => csvEscape(r[f])).join(','))].join('\n') + '\n';

const archiveTable = refs.map(r => `| ${r.index} | ${r.priority} | ${r.video_type} | ${r.artist_or_channel} | ${r.title} | ${r.upload_channel} | ${r.estimated_relevance} | [YouTube](${r.youtube_url}) |`).join('\n');

const formulaSections = {
  'Core Genre': phrase.core,
  'System Seoul/ycs Korean Underground Mood': phrase.mood,
  'Sample/Melody Direction': phrase.sample,
  'Drum/808 Direction': phrase.drums,
  'slayr-inspired Energy Texture': phrase.slayr,
  'Jane Remover-inspired Emotional Digital Texture': phrase.jane,
  'Vocal Layer Direction': phrase.vocal,
  'Mix/Master Texture': phrase.mix,
  'Under 2 Minutes Arrangement': phrase.arrangement,
  'Negative Constraints': phrase.negative.slice(0, 20)
};

const formula = `# Suno Prompt Formula\n\n[Core Genre] + [System Seoul/ycs Korean Underground Mood] + [Sample/Melody Direction] + [Drum/808 Direction] + [slayr-inspired Energy Texture] + [Jane Remover-inspired Emotional Digital Texture] + [Vocal Layer Direction] + [Mix/Master Texture] + [Under 2 Minutes Arrangement] + [Negative Constraints]\n\n${Object.entries(formulaSections).map(([k, arr]) => `## ${k}\n${arr.map((x, i) => `${i + 1}. ${x}`).join('\n')}`).join('\n\n')}\n`;

const promptPack = `# Jane / slayr / System Seoul Suno Final Prompt Pack\n\n## Main Prompt 30\n${mainPrompts.map((p, i) => `### Main ${i + 1}\n${p}`).join('\n\n')}\n\n## Short Prompt 30\n${shortPrompts.map((p, i) => `${i + 1}. ${p}`).join('\n')}\n\n## Exclude Styles 30\n${phrase.negative.slice(0, 30).map((p, i) => `${i + 1}. ${p}`).join('\n')}\n\n## 강화 프롬프트\n${Object.entries(strengthen).map(([k, arr]) => `### ${k}\n${arr.map((x, i) => `${i + 1}. ${x}`).join('\n')}`).join('\n\n')}\n\n### 실패 유형별 수정 프롬프트\n${fixes.map((x, i) => `${i + 1}. ${x}`).join('\n')}\n`;

const bestDoc = `# Jane / slayr / System Seoul Best Prompts\n\n${best.map(([name, prompt, exclude], i) => `[Version ${i + 1}: ${name}]\nMain Prompt:\n${prompt}\n\nExclude Styles:\n${exclude}\n\n사용 목적:\n${name} 테스트용.\n\n예상 장점:\nSystem Seoul/ycs의 차갑고 도시적인 샘플 중심 힙합 문법을 유지하면서 보조 질감을 명확히 제한한다.\n\n예상 위험:\nSuno가 EDM, K-pop 데모, 과한 hyperpop, 보컬 교체 방향으로 튈 수 있다.\n\n실패 시 수정법:\n샘플이 약하면 sample-forward와 catchy original chopped sample을 첫 문장에 두고, 드럼이 약하면 punchy trap drums와 clean bouncy 808을 강화한다. 보컬이 바뀌면 preserve original vocal character와 no female lead vocal takeover를 Exclude에 추가한다.`).join('\n\n')}\n`;

const referenceMap = `# Jane / slayr / System Seoul Reference Map\n\n## 우선순위\n\n1. System Seoul/ycs: 공식, Topic, 멤버 공식 업로드 중심. 프롬프트의 주된 정서, 구조, 드럼/808 기준이다.\n2. slayr: 에너지, 디지털 글로스, 빠른 움직임만 보조로 사용한다.\n3. Jane Remover: 감정적 디지털 haze, 넓은 공간감, 흐릿한 질감만 보조로 사용한다.\n4. 주변 digicore/pluggnb/Korean underground: 장르 태그와 보조 질감 확인용이다.\n\n## 분류 요약\n\n- 조사 후보: 118개\n- 최종 아카이브: ${refs.length}개\n- S: ${refs.filter(r => r.priority === 'S').length}개\n- A: ${refs.filter(r => r.priority === 'A').length}개\n- B: ${refs.filter(r => r.priority === 'B').length}개\n- C: ${refs.filter(r => r.priority === 'C').length}개\n\n## 변환 규칙\n\n- 곡명, 멜로디, 가사, 보컬 톤, 플로우는 복제하지 않는다.\n- 제목/채널/길이/검색 메타데이터에서 반복되는 구조적 특성만 추출한다.\n- System Seoul/ycs는 core, slayr와 Jane Remover는 texture layer로만 쓴다.\n- Suno에서는 named artist imitation보다 cold Korean underground sampled emotional hip-hop 같은 설명형 언어를 우선한다.\n\n## 핵심 매핑\n\n| Source Cluster | Prompt Role | Use | Avoid |\n|---|---|---|---|\n| System Seoul/ycs official | core mood and arrangement | cold Seoul night, sample-forward hook, tight drums, 808 bounce | melody, lyrics, vocal tone copying |\n| System Seoul Topic | under-2-minute compression | fast hook entry, compact structure | direct interpolation |\n| System Seoul type beat/search context | genre tags | pluggnb, digicore, emotional trap vocabulary | treating type beats as primary source |\n| slayr official visualizers | energy texture | shiny digital accents, hard motion | artist imitation, EDM drop |\n| Jane Remover official/Topic | emotional atmosphere | wide haze, digital noise, shoegaze-like air | rock takeover, vocal imitation |\n| Korean pluggnb/digicore playlists | surrounding tags | bounce, plucks, scene context | K-pop idol demo drift |\n`;

const styleAnalysis = `# Jane / slayr / System Seoul Style Analysis\n\n## 결론\n\n이번 아카이브의 중심은 System Seoul/ycs식 차갑고 도시적인 한국 언더그라운드 감성이다. Suno 프롬프트에서는 named artist imitation을 피하고, \"sampled Korean underground emotional hip-hop\", \"cold Seoul night\", \"sample-forward\", \"tight trap drums\", \"bouncy 808\", \"under 2 minutes\" 같은 구조 언어로 변환한다.\n\n## A. System Seoul/ycs\n\n- 무드: 차가운 서울 밤, 회색 네온, 슬프지만 신나는 상태, 외로움과 자신감의 공존.\n- 샘플: 곡의 얼굴은 짧고 중독적인 piano, bell, guitar, vocal chop, glossy synth lead 루프다.\n- 편곡: 긴 빌드업보다 빠른 샘플 제시, 드럼 조기 진입, hook-verse-hook 압축 구조가 맞다.\n- 드럼/808: crisp hi-hats, snappy clap, punchy kick, bouncy 808. 드럼은 강하지만 EDM처럼 과장하지 않는다.\n- 보컬: 원본 보컬이 있다면 캐릭터를 유지하고, 여성 보컬은 background harmony/ad-lib/double/texture로만 둔다.\n\n## B. slayr\n\nslayr는 주 장르가 아니라 보조 질감이다. 가져올 것은 빠른 움직임, 디지털 글로스, 공격적인 에너지, 짧은 glitch ear candy다. 버려야 할 것은 artist imitation, 과한 distortion, EDM drop처럼 들리는 구조다.\n\n## C. Jane Remover\n\nJane Remover는 감정적 디지털 공간감을 위한 보조 질감이다. 넓은 reverb, 흐릿한 노이즈, 슈게이즈적 배경 질감은 쓸 수 있지만, 힙합 드럼과 808 중심을 무너뜨리면 실패다.\n\n## D. 공통 변환\n\n- 특정 멜로디/가사/보컬 복제 금지.\n- 장르 문법과 믹스 질감만 사용.\n- 모든 핵심 프롬프트에는 under 2 minutes 조건을 넣는다.\n- negative constraints는 EDM, K-pop idol demo, AI plastic, vocal replacement, artist imitation을 강하게 막는다.\n`;

const usageResearch = `# Suno Usage Research Expanded\n\n## 기본 입력 순서\n\n1. Main Prompt에는 장르와 정서를 먼저 쓴다: sampled Korean underground emotional hip-hop, cold Seoul night, sad but energetic.\n2. 바로 샘플 지시를 넣는다: catchy original chopped sample loop upfront.\n3. 드럼/808을 구체화한다: tight trap drums, crisp hats, snappy clap, bouncy 808.\n4. slayr/Jane Remover 계열은 secondary texture 또는 background atmosphere로 제한한다.\n5. 보컬 제어 문장을 반드시 넣는다: female vocals only as background ad-libs/harmonies/doubles; preserve original vocal character if uploaded vocals are used.\n6. 길이와 구조를 넣는다: under 2 minutes, hook within 15 seconds, no long intro.\n7. Exclude Styles에는 EDM/K-pop/AI/vocal replacement/artist imitation을 넣는다.\n\n## 좋은 Suno 문장 패턴\n\n- \"Build the track around...\"는 샘플이 중심이라는 지시가 강하다.\n- \"kept behind the hip-hop groove\"는 보조 질감이 과해지는 것을 막는다.\n- \"commercial loud mix, clean but not plastic\"은 싸구려 AI EDM 질감을 줄이는 데 유용하다.\n- \"preserve original vocal character\"는 업로드 보컬을 쓸 때 중요하다.\n\n## 실패 대응\n\n${fixes.map((x, i) => `${i + 1}. ${x}`).join('\n')}\n`;

const archiveMd = `# Jane / slayr / System Seoul YouTube Archive\n\n수집 기준: YouTube 공개 검색 결과의 제목, 채널명, URL, 길이, 조회수/업로드 시점 등 공개 메타데이터를 중심으로 정리했다. 오디오/영상 다운로드, 멜로디 채보, 가사 복사, 보컬 복제 분석은 수행하지 않았다.\n\n## 분류 요약\n\n- 조사 후보: 118개\n- 최종 아카이브: ${refs.length}개\n- S: ${refs.filter(r => r.priority === 'S').length}개\n- A: ${refs.filter(r => r.priority === 'A').length}개\n- B: ${refs.filter(r => r.priority === 'B').length}개\n- C: ${refs.filter(r => r.priority === 'C').length}개\n\n## 선별 목록\n\n| # | Pri | Type | Artist/Channel | Title | Upload | Rel | URL |\n|---:|:---:|---|---|---|---|---:|---|\n${archiveTable}\n\n## 메모\n\n공식/Topic 결과는 프롬프트의 핵심 근거로, type beat와 playlist 결과는 공개 장르 태그와 청취자 맥락 확인용으로만 사용했다. Lyrics, reaction, AI cover, instrumental extraction, shorts, unrelated search collisions는 C 또는 제외 후보로 표시했다.\n`;

const promptArchive = `# Jane / slayr / System Seoul Prompt Archive\n\n${formula}\n\n## Main Prompt Archive\n\n${mainPrompts.map((p, i) => `### ${i + 1}\n${p}`).join('\n\n')}\n\n## Short Prompt Archive\n\n${shortPrompts.map((p, i) => `${i + 1}. ${p}`).join('\n')}\n`;

write('research/jane_slayr_system_youtube_archive.csv', csv);
write('research/jane_slayr_system_youtube_archive.md', archiveMd);
write('docs/jane_slayr_system_reference_map.md', referenceMap);
write('docs/jane_slayr_system_style_analysis.md', styleAnalysis);
write('docs/suno_style_bible_expanded.md', formula);
write('docs/suno_usage_research_expanded.md', usageResearch);
write('prompts/jane_slayr_system_prompt_archive.md', promptArchive);
write('prompts/jane_slayr_system_final_prompt_pack.md', promptPack);
write('prompts/jane_slayr_system_best_prompts.md', bestDoc);

console.log(`Generated ${refs.length} references and ${mainPrompts.length} main prompts.`);
