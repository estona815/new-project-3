# Plugin Equivalent Chain

The user reference chain mentions paid plugins. The harness maps each role to local/free REAPER-compatible equivalents.

| Reference Role | Paid Example | Harness Equivalent |
| --- | --- | --- |
| Surgical harshness cleanup | Soothe2 | `TDR Nova`, `ReaXcomp`, dynamic high-band tame in Python |
| Surgical EQ / dynamic EQ | FabFilter Pro-Q 4 | `ReaEQ`, `TDR Nova`, Python dynamic-band carve |
| Tube density / air | Black Box HG-2MS | `JS: Saturation`, `JS: Exciter`, subtle Python saturation |
| Parallel aggression | Decapitator | `JS: Saturation`, soft clipper texture, low mix amount |
| De-ess | FabFilter Pro-DS | `TDR Nova`, `ReaXcomp`, Python de-ess dynamic band |
| Fast vocal control | UAD 1176 Rev E | Fast `ReaComp` |
| Master stabilizer/exciter | Ozone Stabilizer / Exciter | `TDR Nova`, `ReaXcomp`, `JS: Exciter` |
| True-peak limiting | Pro-L 2 | `ReaLimit`, `JS: Event Horizon` or soft clipper fallback |
| Delay send | EchoBoy | `ReaDelay` send bus with high/low cuts |
| Reverb send | Altiverb / Seventh Heaven | `ReaVerbate` or `ReaVerb` send bus |
| Ducked wetness | Sidechained reverb bus | `ReaComp` on delay/reverb bus, with conservative send levels |

## Implemented Stages

1. **Cleanup**: HPF, low-mid mud control, 2-8 kHz dynamic harshness control.
2. **Saturate**: light saturation on main vocal, melody, drums, bass/808, and instrumental bus.
3. **Control**: ReaComp-style vocal and bus compression; no aggressive tuning.
4. **Polish**: print bus dynamic stabilizer, exciter, and limiter/clip safety.
5. **Wetness**: endpoint-only female reverb throw plus delay/reverb sends in REAPER.
