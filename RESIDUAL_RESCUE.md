# Residual Rescue Policy

Residual rescue may use a full mix reference only as source material for a newly written processed asset. The raw full mix must never be routed to the active master path.

## Allowed Algorithm

1. Read the full mix reference as a source-only file.
2. Sum instrument stems.
3. Prepare vocal candidate stems.
4. Fit and subtract instrument and vocal candidates from the full mix.
5. Extract the remaining residual.
6. Keep only voice-like energy.
7. Write a new processed residual asset.
8. Route that processed asset only to `09 MALE_HOOK_RESIDUAL_CENTER`.
9. Keep the raw full mix/reference muted and unrouted.

## Default Bands

- Voice band: 95 Hz to 4800 Hz
- Low body: 105 Hz to 360 Hz
- Chest: 170 Hz to 720 Hz
- Consonant: 900 Hz to 2700 Hz
- High fizz/noise watch band: 3600 Hz to 7600 Hz

If fitting or subtraction is not reliable, write the report and keep status `UNVERIFIED`.
