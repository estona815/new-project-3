# Deep Reference Mix Analysis

## 중요한 정정
현재 자료는 mastered reference WAV뿐입니다. 그래서 stem별 보컬/비트/리버브를 실제로 분리 측정했다고 말할 수 없습니다.
이번 deep 분석은 full-mix reference에서 가능한 EQ, dynamic EQ, M/S EQ, saturation, transient, high-end hash proxy를 최대한 세분화한 것입니다.

## 분석 파일
- `Estona,Nib-Broken_MASTER_24-48.wav`: reference, 101.4s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Dough_MASTER_24-48.wav`: reference, 139.3s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-IMnK_MASTER_24-48.wav`: reference, 183.1s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Lovee_MASTER_24-48.wav`: reference, 152.1s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Missu_MASTER_24-48.wav`: reference, 114.1s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Phobia_MASTER_24-48.wav`: reference, 88.2s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Stuck in Seoul_MASTER_24-48.wav`: reference, 185.7s, 48000 Hz, 2 ch, PCM_24
- `Estona,Nib-Why_MASTER_24-48.wav`: reference, 163.9s, 48000 Hz, 2 ch, PCM_24

## Reference Master Targets
- LUFS: -6.04 LUFS (IQR -6.11 to -6.03 LUFS)
- Crest factor: 7.74 dB (IQR 7.60 to 8.03 dB)
- Density proxy: 0.48 (IQR 0.41 to 0.51)
- Transient density: 1.42/sec (IQR 1.35 to 1.49/sec)
- Ambient/reverb tail proxy: -0.17 dB (IQR -2.11 to 0.26 dB)

## EQ Target Bands
- `sub_weight_40_60` (808/kick fundamental weight): static -5.23 dB share (IQR -6.70 to -4.76 dB share), dynamic range 54.33 dB (IQR 33.45 to 64.54 dB), side-mid -31.95 dB (IQR -39.90 to -27.04 dB)
- `bass_punch_90_120` (kick/808 punch): static -12.05 dB share (IQR -13.49 to -11.22 dB share), dynamic range 28.26 dB (IQR 24.77 to 32.38 dB), side-mid -15.34 dB (IQR -19.77 to -12.83 dB)
- `mud_120_180` (low-mid mud start): static -11.06 dB share (IQR -12.59 to -10.86 dB share), dynamic range 22.19 dB (IQR 19.56 to 24.41 dB), side-mid -10.32 dB (IQR -15.82 to -9.17 dB)
- `box_250_350` (boxiness/mud): static -14.72 dB share (IQR -15.66 to -12.98 dB share), dynamic range 17.26 dB (IQR 14.80 to 20.05 dB), side-mid -7.73 dB (IQR -9.98 to -6.42 dB)
- `presence_2000_3500` (vocal lead presence): static -16.71 dB share (IQR -17.82 to -15.22 dB share), dynamic range 15.82 dB (IQR 13.36 to 18.75 dB), side-mid -7.95 dB (IQR -10.28 to -4.76 dB)
- `bite_3500_5000` (bite/edge): static -20.40 dB share (IQR -21.33 to -19.72 dB share), dynamic range 18.65 dB (IQR 15.92 to 23.16 dB), side-mid -7.51 dB (IQR -9.65 to -4.39 dB)
- `harsh_5000_6500` (harshness): static -21.54 dB share (IQR -22.26 to -21.17 dB share), dynamic range 18.84 dB (IQR 16.85 to 28.82 dB), side-mid -7.85 dB (IQR -10.31 to -4.68 dB)
- `sibilance_6500_8000` (sibilance): static -21.54 dB share (IQR -22.60 to -21.40 dB share), dynamic range 18.42 dB (IQR 16.94 to 31.69 dB), side-mid -9.18 dB (IQR -10.92 to -4.58 dB)
- `air_edge_8000_10000` (air edge/hash): static -22.67 dB share (IQR -23.05 to -22.44 dB share), dynamic range 19.77 dB (IQR 18.26 to 35.28 dB), side-mid -8.79 dB (IQR -9.93 to -4.56 dB)
- `fizz_12000_16000` (fizz/noise): static -26.37 dB share (IQR -26.86 to -25.03 dB share), dynamic range 21.19 dB (IQR 19.86 to 32.94 dB), side-mid -8.08 dB (IQR -10.56 to -2.62 dB)

## What This Enables
- ReaEQ: current mix가 들어오면 band target 대비 과한 대역을 broad cut/boost로 계산 가능.
- ReaXcomp/dynamic EQ: p90/burstiness가 높은 mud/presence/harsh/air band를 자동 후보로 지정 가능.
- M/S EQ: side-minus-mid target으로 저역 side 위험과 고역 side hash를 판단 가능.
- Saturation: crest/flatness/high-ratio 기반으로 drive 부족과 과한 bright drive 위험을 분리 가능.
- Reverb: stem이 없으므로 tail proxy까지만 가능. 실제 vocal reverb 판단은 vocal stem 필요.
