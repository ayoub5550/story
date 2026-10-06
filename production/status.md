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
| Part 2 shot list (98 shots, 720 s) | ✅ validated |
| Owner decisions | ✅ MSA · music generated in-sandbox or from free libraries · ❓ video-clip budget pending |

## Part 1 production
| Scene | Shots | Keyframes | Clips | Audio | Notes |
|---|---|---|---|---|---|
| S01 | 7 | 6/6 + HF ✅ | 1/7 (HF) | ✅ vo+score+sfx in mix | animatic ✅ |
| S02 | 7 | 6/6 + HF ✅ | 1/7 (HF) | ✅ vo+score+sfx in mix | animatic ✅ |
| S03 | 10 | 10/10 ✅ | 0/10 | ✅ vo+score+sfx in mix | animatic ✅ |
| S04 | 9 | 9/9 ✅ | 0/9 | ✅ vo+score+sfx in mix | animatic ✅ |
| S05 | 11 | 11/11 ✅ | 1/11 (S05-01) | ✅ vo+score+sfx in mix | animatic ✅ |
| S06 | 11 | 11/11 ✅ | 0/11 | ✅ vo+score+sfx in mix | animatic ✅ |
| S07 | 12 | 12/12 ✅ | 0/12 | ✅ vo+score+sfx in mix | animatic ✅ |
| S08 | 8 | 8/8 ✅ | 1/8 (S08-01) | ✅ vo+score+sfx in mix | animatic ✅ |
| S09 | 4 | 3/3 + HF ✅ | 1/4 (HF) | ✅ vo+score+sfx in mix | animatic ✅ |

## Part 2 production
| Scene | Time | Shots | Keyframes | Clips | Audio | Notes |
|---|---|---|---|---|---|---|
| S10 | 10:00–11:20 | 14 | 14/14 ✅ | 0/14 | ✅ in mix | animatic ✅ |
| S11 | 11:20–12:30 | 9 | 9/9 ✅ | 0/9 | ✅ in mix | animatic ✅ |
| S12 | 12:30–14:30 | 15 | 15/15 ✅ | 0/15 | ✅ in mix | animatic ✅ |
| S13 | 14:30–16:00 | 13 | 13/13 ✅ | 0/13 | ✅ in mix | animatic ✅ |
| S14 | 16:00–17:30 | 13 | 12/12 + HF ✅ | 1/13 (HF) | ✅ in mix | animatic ✅ |
| S15 | 17:30–19:00 | 12 | 11/11 + HF ✅ | 1/12 (HF) | ✅ in mix | animatic ✅ |
| S16 | 19:00–20:30 | 11 | 11/11 ✅ | 0/11 | ✅ in mix | animatic ✅ |
| S17 | 20:30–21:30 | 7 | 7/7 ✅ | 0/7 | ✅ in mix | animatic ✅ |
| S18 | 21:30–22:00 | 4 | 3/3 + HF ✅ | 1/4 (HF) | ✅ in mix | animatic ✅ |

## Pilot results (2026-10-06)
- S08-01 (seedance-2.5, 10 s, 720p, ≈$4.73): excellent. Matches the refs, both veils stay on, a natural pre-dawn to sunrise light change, the 2D painted look is held. → `clip_done`.
- S05-01: seedance-2.5 returned HTTP 422 twice (it likely rejects medium shots with visible faces). kling-video-v3-pro worked first try (9 s, ≈$1.51): stable designs, veils on, natural hand gesture. Kling returned 3:2 because the keyframe was 3:2, so it was cropped to 16:9 in post. `viktor_produce.py` now pre-crops keyframes to 16:9 and falls back to kling automatically. → `clip_done`.
- Pilot spend: ≈$6.24 for 2 clips. Projection for all 79 Part 1 clips: ≈$120 with kling, ≈$370 with seedance.

## 2026-10-06 — Part 1 keyframes, audio and animatic
- All Part 1 keyframes generated and QC'd. Redos: S01-04, S02-05, S02-06, S04-03, S04-09, S05-08 (x2), S05-11, S06-03 (text2im collision).
- Audio: 29 MSA lines (ElevenLabs v4), original synthesized score + SFX, mix ≈ −17.5 LUFS.
- Animatic 10:00 with Arabic subtitles: GitHub Release `part1-animatic-v1`.
- Map of every shot with its position: [`shot_index.md`](shot_index.md). Contact sheets: `renders/sheets/`.
- Open: budget for 72 video clips (≈$120 kling / ≈$370 seedance). Tifinagh spelling `ⴰⵎⵎⵍⵏ` needs a native-speaker check.

## 2026-10-06 — Part 2 keyframes, audio, animatic + full 22:00 animatic
- 95 keyframes generated and QC'd. Redos: S10-03, S10-14, S11-07, S13-09, S15-01 + S16-02 (text2im duplicates of S15-06/S16-07).
- HF: S14-06 (first carved signs + Tifinagh row), S15-03 (reading the signs), S18-04 (end credit).
- Audio: 31 MSA lines, score + SFX, mix −17.7 LUFS.
- Release `part2-animatic-v1`: Part 2 animatic (720p + 1080p), `part2.srt`, full film animatic 22:00 + `film.srt`.
- Accepted as-is: model-drawn Tifinagh-like marks in some S14–S16 keyframes, extra background figures in S12-04/S12-13.
- Open: clip budget (167 clips ≈ $255 kling / ≈ $780 seedance); Tifinagh `ⴰⵎⵎⵍⵏ` check.
