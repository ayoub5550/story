# Production status

Update this file after every scene (AGENTS.md §8).

## Pre-production
| Item | Status |
|---|---|
| Synopsis + Gilgamesh mapping | ✅ done |
| Screenplay Part 1 (S01–S09) | ✅ done |
| Treatment Part 2 (S10–S18) | ✅ done (needs full screenplay pass) |
| Character / location / style bible | ✅ done |
| Ref sheets (9 characters + key art) | ✅ done |
| Part 1 shot list (79 shots, 600 s) | ✅ validated |
| Part 2 shot list | ⏳ skeleton only (target_dur / target_shots) |
| Owner decisions: dialect (MSA vs darja), music source, 22 vs 10 min | ❓ pending |

## Part 1 production
| Scene | Shots | Keyframes | Clips | Audio | Notes |
|---|---|---|---|---|---|
| S01 | 7 | 0/7 | 0/7 | – | |
| S02 | 7 | 0/7 | 0/7 | – | |
| S03 | 10 | 0/10 | 0/10 | – | |
| S04 | 9 | 0/9 | 0/9 | – | |
| S05 | 11 | 1/11 (pilot S05-01) | 1/11 (S05-01 ✅ QC) | – | |
| S06 | 11 | 0/11 | 0/11 | – | |
| S07 | 12 | 0/12 | 0/12 | – | |
| S08 | 8 | 1/8 (pilot S08-01) | 1/8 (S08-01 ✅ QC) | – | |
| S09 | 4 | 0/4 | 0/4 | – | |

## Pilot results (2026-10-06)
- S08-01 (seedance-2.5, 10 s, 720p, ≈$4.73): excellent. Matches the refs, both veils stay on, a natural pre-dawn to sunrise light change, the 2D painted look is held. → `clip_done`.
- S05-01: seedance-2.5 returned HTTP 422 twice (it likely rejects medium shots with visible faces). kling-video-v3-pro worked first try (9 s, ≈$1.51): stable designs, veils on, natural hand gesture. Kling returned 3:2 because the keyframe was 3:2, so it was cropped to 16:9 in post. `viktor_produce.py` now pre-crops keyframes to 16:9 and falls back to kling automatically. → `clip_done`.
- Pilot spend: ≈$6.24 for 2 clips. Projection for all 79 Part 1 clips: ≈$120 with kling, ≈$370 with seedance.
