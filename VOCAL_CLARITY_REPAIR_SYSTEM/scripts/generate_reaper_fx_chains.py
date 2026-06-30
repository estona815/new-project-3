#!/usr/bin/env python3
from pathlib import Path
root = Path(__file__).resolve().parents[1]
for name in ['Vocal_Clear_Forward','Vocal_DeMud_Only','Vocal_Raw_Digicore_Forward','Vocal_Background_Double_Support']:
    (root/'FXChains'/f'{name}.RfxChain').write_text('<FXCHAIN\n  SHOW 0\n>\n')
print('FXChains refreshed')
