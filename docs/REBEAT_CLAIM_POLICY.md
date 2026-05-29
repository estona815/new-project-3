# Rebeat Claim Policy

This policy connects the rebeat harness to the repo-wide PASS/WARN/FAIL/BLOCKER reporting system.

## Claim Gate

`true_rebeat` is allowed only when:

- drum reconstruction exists
- bass reconstruction exists
- music/chord/lead reconstruction or equivalent stem support exists
- grid confidence is PASS or a justified WARN
- separate role bus renders exist
- RPP and MIDI audits pass
- QC has no FAIL or BLOCKER
- fullmix is not the only primary sound source

Otherwise, the classifier must downgrade.

## Downgrade Rules

- Drums only with fullmix active: `drum_reinforcement`.
- Drums only without enough bass/music: `partial_rebeat: drums only`.
- Bass only: `partial_rebeat: bass only`.
- Stems active but no reconstruction: `stem_assisted_rebuild`.
- Machine-separated stems: `stem_assisted_rebuild` with WARN and source-separation label.
- Fullmix plus mastering only: `fullmix_rescue` or `master_only`.

## WARN+ Behavior

If WARN or higher occurs, do not claim final success. Report:

- severity
- affected file
- failed assumption
- evidence
- exact next patch
- exact command to rerun
- whether human listening is required

## Evidence Required For `비트를 다 새로 찍음`

This phrase requires the same evidence as `true_rebeat`: drums, bass, and music reconstructed as auditable MIDI/audio items, separate bus renders, RPP audit, tempo/grid report, QC, and final report. Without that, use precise Korean such as:

- `킥/스네어 보강 MIDI는 생성했지만 true rebeat는 아닙니다.`
- `베이스와 음악 파트 재구성이 없어 partial rebeat입니다.`
- `원본 fullmix가 주 소스라서 fullmix rescue + drum reinforcement입니다.`
