# Source/Reverb/Plugin Trace Analysis

이 보고서는 플러그인 흔적을 확정하지 않습니다. 오디오에서 관찰되는 기술적 흔적을 REAPER 최후검수 후보로 코드화한 것입니다.

- Files analyzed: 8
- Mode: `reference_only_trace_mode`

## Aggregate Trace Targets
- Loudness target: -6.041 LUFS (IQR -6.112 to -6.028 LUFS)
- Crest target: 7.739 dB (IQR 7.598 to 8.035 dB)
- Reverb early reflection ratio: 0.883 (IQR 0.796 to 0.903)
- Reverb tail 180-900ms ratio: 0.774 (IQR 0.763 to 0.816)
- Tail width lift: 8.808 dB (IQR 7.086 to 10.762 dB)
- High damping tail-attack: -0.333 dB (IQR -0.578 to -0.138 dB)

## Per File Trace Summary
### Estona,Nib-Broken_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.65; delay score 0.67.
- Tail: early 0.902, tail 0.808, slope -0.53 dB/sec, width lift 8.59 dB.
- Delay candidates: 740ms/0.62, 570ms/0.60, 930ms/0.56, 380ms/0.54
- Plugin traces: limiter 0.10, clipper 0.98, saturation/exciter 0.72, widener 0.04, high hash 0.64.
### Estona,Nib-Dough_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.62; delay score 0.91.
- Tail: early 0.904, tail 0.776, slope 0.07 dB/sec, width lift 9.03 dB.
- Delay candidates: 190ms/0.75, 430ms/0.73, 650ms/0.63, 870ms/0.59
- Plugin traces: limiter 0.22, clipper 1.00, saturation/exciter 0.73, widener 0.41, high hash 0.65.
### Estona,Nib-IMnK_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.70; delay score 0.87.
- Tail: early 0.907, tail 0.857, slope 0.10 dB/sec, width lift 7.53 dB.
- Delay candidates: 560ms/0.73, 380ms/0.70, 290ms/0.70, 750ms/0.69
- Plugin traces: limiter 0.00, clipper 0.84, saturation/exciter 0.83, widener 0.55, high hash 0.73.
### Estona,Nib-Lovee_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.47; delay score 0.79.
- Tail: early 0.734, tail 0.772, slope -1.04 dB/sec, width lift 5.75 dB.
- Delay candidates: 460ms/0.69, 690ms/0.68, 230ms/0.68, 920ms/0.66
- Plugin traces: limiter 0.38, clipper 1.00, saturation/exciter 0.67, widener 0.49, high hash 0.62.
### Estona,Nib-Missu_MASTER_24-48.wav
- Reverb proxy: long_hall_or_washy_tail_proxy score 0.62; delay score 0.70.
- Tail: early 0.869, tail 0.753, slope 0.57 dB/sec, width lift 11.71 dB.
- Delay candidates: 630ms/0.63, 420ms/0.61, 850ms/0.58
- Plugin traces: limiter 0.00, clipper 0.86, saturation/exciter 0.63, widener 0.14, high hash 0.60.
### Estona,Nib-Phobia_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.47; delay score 0.69.
- Tail: early 0.776, tail 0.678, slope 1.39 dB/sec, width lift 10.69 dB.
- Delay candidates: 390ms/0.63, 780ms/0.52, 190ms/0.21, 580ms/0.17
- Plugin traces: limiter 0.04, clipper 0.83, saturation/exciter 0.73, widener 0.08, high hash 0.66.
### Estona,Nib-Stuck in Seoul_MASTER_24-48.wav
- Reverb proxy: long_hall_or_washy_tail_proxy score 0.61; delay score 0.46.
- Tail: early 0.897, tail 0.839, slope 0.20 dB/sec, width lift 2.87 dB.
- Delay candidates: 400ms/0.50, 800ms/0.46, 130ms/0.29, 280ms/0.24
- Plugin traces: limiter 0.08, clipper 0.69, saturation/exciter 0.75, widener 0.11, high hash 0.69.
### Estona,Nib-Why_MASTER_24-48.wav
- Reverb proxy: wide_bright_plate_or_shimmer_proxy score 0.59; delay score 0.90.
- Tail: early 0.803, tail 0.766, slope 0.85 dB/sec, width lift 10.98 dB.
- Delay candidates: 460ms/0.75, 680ms/0.73, 910ms/0.72
- Plugin traces: limiter 0.11, clipper 0.51, saturation/exciter 0.66, widener 0.14, high hash 0.60.
