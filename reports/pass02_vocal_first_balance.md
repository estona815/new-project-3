# Pass 02 Vocal First Balance

The lead vocal is treated as the anchor. Instrumental elements were trimmed around it instead of mastering over the problem.

- 12_Vocals: {'index': 43, 'volume_db': -4.2, 'pan': 0.0, 'mute': False}
- MALE_LEAD_VOX_BUS: {'index': 4, 'volume_db': 1.7, 'pan': 0.0, 'mute': False}
- MUSIC_BUS: {'index': 3, 'volume_db': 0.0, 'pan': 0.0, 'mute': False}
- BASS_808_BUS: {'index': 2, 'volume_db': -2.0, 'pan': 0.0, 'mute': False}

## BGV Timing Reanalysis
- 11_Backing_Vocals: {'exists': True, 'reference': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/12_Vocals.wav', 'candidate': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/11_Backing_Vocals.wav', 'lag_s': 0.0, 'correlation': 0.101, 'note': 'positive lag means the candidate envelope trails the male lead'}
- female_vocal_candidate_clean: {'exists': True, 'reference': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/12_Vocals.wav', 'candidate': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/female_vocal_candidate_clean.wav', 'lag_s': 0.03, 'correlation': 0.092, 'note': 'positive lag means the candidate envelope trails the male lead'}
- external 0 Lead Vocals: {'exists': True, 'reference': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/raw_stems/12_Vocals.wav', 'candidate': '/Users/hantaeheuk/Documents/New project 3/suno_studio_extract/external_female_v20_stems/0 Lead Vocals.wav', 'lag_s': 1.26, 'correlation': 0.111, 'note': 'positive lag means the candidate envelope trails the male lead'}

The external female lead candidate was muted because it behaves like a second lead and trails the male lead by about 1.26s. The clean candidate was also muted because prior QC flagged hard-cut/dropout risk. This is the core fix for the unclear two-vocal timing problem.
