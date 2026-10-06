# AGENTS.md — Production Bible for «أمامّلن: حين تصلّبت الحجارة»

You are joining an **in-progress animated film production**. Read this file completely before touching anything.
It outranks any habit you bring. If something here is wrong or outdated, fix it **and** add a line to §9 Changelog.

---

## 1. The project in 30 seconds
- **Film:** *Amamellen — When the Stone Hardened*. A 22-minute hand-painted-2D-style animated epic based on the Tuareg (Algerian Ahaggar/Ajjer) myth of **Amamellen/Aniguran** and his nephew **Adelasegh**. It is the Algerian counterpart of *Gilgamesh*.
- **Structure:** two **continuous** parts.
  - **Part 1 «الحجر الليّن»** runs 00:00–10:00 (600 s). It is the first deliverable and must work as a standalone 10-minute film.
  - **Part 2 «الحجر الصلب»** runs 10:00–22:00 (720 s).
- **Format:** 1920×1080, 16:9, 24 fps. Arabic (simple MSA) narration and dialogue, with Tamahaq words.
- **Owner:** freedy (GitHub `ayoub5550`). Decisions that change the story, characters or length need the owner's OK.

## 2. Source of truth (canon hierarchy)
When files disagree, the higher one wins:
1. `story/01_synopsis.md`: story, themes, and what is traditional vs. invented.
2. `story/02_screenplay_part1.md` and `story/03_screenplay_part2.md`: scenes, exact Arabic lines, and scene timecodes.
3. `bible/characters.yaml`, `bible/locations.yaml`, `bible/style.md`: the visual canon. The images in `assets/refs/` are the canonical designs.
4. `production/shots_part*.yaml`: shot-by-shot plan, derived from 2 and 3.
5. `production/status.md`: progress tracker.

**Never** change dialogue in a shot list without changing the screenplay first. **Never** redesign a character without regenerating its ref sheet, updating `characters.yaml`, and logging it in §9.

## 3. Repository map
```
AGENTS.md                  ← you are here
README.md                  ← human overview (Arabic)
story/                     ← synopsis + screenplays (Arabic)
bible/                     ← characters.yaml, locations.yaml, style.md (STYLE PREFIX + NEGATIVE live here)
assets/refs/               ← canonical model sheets (char_*.png) + key_art.png (mood only, NOT canon for proportions)
production/
  shots_part1.yaml         ← 79 shots, fully specified (600 s)
  shots_part2.yaml         ← 98 shots, fully specified (720 s, film time 10:00–22:00)
  scenes.md                ← scene table: timecodes, production method mix, difficulty
  status.md                ← progress tracker (update every session)
  gen_log.jsonl            ← append-only log of every generation (auto-written by tools)
tools/
  common.py                ← loaders, STYLE_PREFIX, NEGATIVE
  validate_shots.py        ← MUST pass before every commit
  build_prompt.py          ← expands a shot -> keyframe prompt, motion prompt, ref images, audio lines
  viktor_produce.py        ← Viktor-sandbox generator (keyframe -> clip). Port it if you use other providers
  viktor_produce.py kf     ← stills for KF2V *and* T2V shots (skips existing; --force to redo; 3 retries)
  make_voice.py            ← TTS for every vo/dlg line -> renders/audio/lines/<SHOT>.mp3 + part1_lines.json (SAY dict = tashkeel overrides)
  make_score.py            ← original synthesized score + SFX (seeded numpy; CUES spotting sheet per scene)
  mix_part.py              ← places lines (auto-pushes overlaps), ducks music/SFX, loudnorm -> renders/audio/part1_mix.wav
  make_hf.py               ← HF graphics shots via PIL+ffmpeg: S01-07 stars->glyphs, S02-07 title, S09-04 end card,
                             S14-06 first letters carved, S15-03 reading the signs, S18-04 end credit (plates: renders/keyframes/<SHOT>_plate.jpg)
                             NOTE: the Naskh font has no em dash (—) → use «،» in on-screen Arabic text
  assemble.py              ← ffmpeg cut: clip > keyframe still w/ zoompan from `camera` > slate. --subs burns RTL Arabic subs + writes .srt, --preview = 720p
  contact_sheet.py         ← renders/sheets/<SCENE>.jpg (id, timecode, dur, method per shot)
  shot_index.py            ← production/shot_index.md: every shot with its position in the film, thumbnail, line, links, status
  master.py                ← joins part1 + part2 into the 22:00 film + merged film.srt (--preview = 720p animatic parts)
renders/
  keyframes/<SHOT>.jpg     ← approved keyframes (JPG q2; S02-07_plate.jpg = title background)
  thumbs/<SHOT>.jpg        ← 320×180 thumbs for shot_index.md (auto)
  sheets/<SCENE>.jpg       ← per-scene contact sheets (auto)
  clips/<SHOT>.mp4         ← approved clips (compressed, see §6.6)
  audio/lines/             ← per-line TTS mp3 + part<N>_lines.json (placed times). *.wav stems are gitignored (regenerate)
  part<N>.srt              ← Arabic subtitles (auto, from assemble.py --subs)
production/shot_index.md   ← THE map of the film for humans: open it to see every shot and where it sits
```

## 4. Shot spec (the format every agent must follow)
Each shot in `production/shots_partN.yaml` is a one-line YAML map:

| field | required | meaning |
|---|---|---|
| `id` | ✔ | `S<scene>-<nn>`, e.g. `S07-11`. Never renumber after a shot is approved; insert as `S07-11a`. |
| `dur` | ✔ | seconds (integer, 2–15). Each scene's shots must sum to that scene's duration in `scenes.md`. |
| `method` | ✔ | `KF2V` keyframe→video (default for characters) · `T2V` text/ref→video (landscapes, crowds, VFX) · `PX` painted still + camera move · `HF` HyperFrames graphics (titles, Tifinagh glyphs, credits) |
| `chars` | ✔ | list of character tokens from `characters.yaml` (empty list allowed) |
| `child` | – | tokens to render at child age (uses `child_prompt`, no adult ref sheet) |
| `loc` / `tod` | – | per-shot override of scene location / time of day |
| `camera` | ✔ | framing + movement in plain English |
| `action` | ✔ | what is visible, in English (model-facing). One action per shot. |
| `vo` / `dlg` / `sfx` | – | exact Arabic narration / dialogue (copied from the screenplay) / sound notes |
| `notes` | – | staging rules, overlays, warnings |
| `status` | ✔ | `todo` → `kf_done` → `clip_done` → `approved` |

Timecodes are **derived** from cumulative `dur`, so never write them by hand. `python tools/validate_shots.py` prints them.

## 5. Non-negotiable creative rules
1. **Style:** every image/video prompt starts with the exact `STYLE_PREFIX` (in `tools/common.py` and `bible/style.md`) and ends with the `NEGATIVE` list. Do not paraphrase either.
2. **Character consistency:** always pass the ref sheet(s) from `assets/refs/` as reference images. One shot should hold no more than 3 named characters.
3. **Lip-sync avoidance (core production trick):** adult Tuareg men are **always veiled**, so their mouths are never visible and no lip-sync is needed. Unveiled characters (women, children, grandmother) speak only in profile, from behind, in wide shots, or as voice-over.
4. **Screen direction:** through S07, AMAMELLEN is screen-left looking right and ADELASEGH is screen-right looking left. From S08 on they sit **side by side, facing the same way**. Keep this unless a shot note says otherwise.
5. **Signature colours:** Amamellen = deep indigo. Adelasegh = light sky-indigo veil with a sand-coloured robe. Raiders = black. Giant = red sandstone.
6. **Tifinagh glyphs are never trusted to the video model.** Render glyphs as crisp HyperFrames/vector overlays composited on the rock. The **dot-game symbols** (two dots = water, circle = camp, line = road) introduced in S04-03 must look identical in S14 and S15.
7. **Cultural accuracy:**
   - No horses, guns, mosques or modern objects.
   - Camels, leather tents, takouba swords, spears and the imzad are correct.
   - Women are unveiled with headscarves and silver jewellery.
   - Succession passes to the **sister's son**; this is the climax of S16.
8. **Pacing:** average shot 6–9 s with slow camera moves. Fast cutting only in S10, S13 and S15.

## 6. Production pipeline (per shot)
1. **Prep:** run `python tools/build_prompt.py <SHOT_ID>`. It gives the keyframe prompt, the motion prompt, the ref images and the audio lines.
2. **Keyframe (KF2V):**
   - Generate the image with the refs attached. Viktor: `coworker_text2im(image_paths=refs, aspect_ratio="3:2")`.
   - Keyframe generation must be **sequential**: parallel calls were observed returning the same file.
   - Save to `renders/keyframes/<ID>.jpg` (JPG q2 — `viktor_produce.py kf` does this). After any parallel batch, check `md5sum renders/keyframes/*.jpg | sort | uniq -w32 -d` for collisions.
   - Write `action` as **one single continuous image**; the model sometimes produces comic panels/storyboard grids (now in NEGATIVE).
3. **Keyframe QC** (all must pass, else regenerate; budget 3 tries, then simplify the shot and note it):
   - The character matches the ref sheet: veil colour, robe, amulet, sword, eye colour.
   - Veiled men show no mouth.
   - No text or garbled glyphs.
   - Correct time of day and screen direction.
   - Hands look acceptable, or are hidden.
4. **Clip:**
   - Image-to-video from the keyframe. Default model `seedance-2.5`, 16:9, duration = `dur + 1` s (a 1 s trim handle).
   - **Model choice (from the pilot):** `seedance-2.5` is best for wide/landscape/from-behind shots (S08-01: excellent, but ≈$0.47/s). It **rejected (HTTP 422) a medium two-shot with visible faces** (S05-01) twice. `kling-video-v3-pro` handled that shot first try at 1080p for ≈$0.17/s. **Use kling as the default for character medium/close shots**, and seedance for wides, T2V landscapes and VFX. `viktor_produce.py` falls back to kling automatically.
   - **Aspect:** text2im only makes 3:2 keyframes. Kling copies the input aspect, so `viktor_produce.py` crops each keyframe to 16:9 (keeping 30% of the excess on top for headroom) before sending it. **Compose keyframes with headroom**: keep heads and turbans out of the top 8% of the frame.
   - The video model's native audio is **discarded**. The audio is built separately (6.7).
5. **Clip QC:**
   - No morphing faces or extra limbs.
   - The veil stays on.
   - The style stays 2D-painted, not 3D.
   - The motion matches `camera`.
   - The first frame matches the keyframe.
   - Then set `status: clip_done`. The director or owner sets `approved`.
6. **Storage:**
   - Re-encode approved clips before committing: `ffmpeg -i in.mp4 -an -vf scale=1280:-2 -c:v libx264 -crf 23 renders/clips/<ID>.mp4`. Target under 8 MB each.
   - Full-quality masters and final cuts go to **GitHub Releases**, never into git history.
7. **Audio** (per scene, after its clips are approved):
   - Narration and dialogue: ElevenLabs `eleven_v4`, `language_code="ar"`, using the voices in `characters.yaml`. Pass `previous_text`/`next_text` for continuity. Save to `renders/audio/<SCENE>_vo.wav`.
   - **Owner decision (2026-10-06): language = Modern Standard Arabic (فصحى); music = generated by us or taken from free libraries.**
   - Pipeline (all scripted, re-runnable): `make_voice.py` → `make_score.py` → `mix_part.py`.
     - `make_voice.py`: ElevenLabs `eleven_v4`, `ar`, voices in its `SPEAKERS` table. Child/spirit voices are pitch-shifted, which can garble words — add tashkeel through the `SAY` dict and STT-check.
     - `make_score.py`: original score synthesized in-sandbox (imzad-like bowed fiddle in D Dorian, pad, tende 12/8, reed flute, plucks) + SFX. Leitmotifs THEME_A / DOTS / FLUTE. Edit the `CUES` sheet to re-spot a scene.
     - If the owner wants real instruments: use CC-BY music (e.g. Kevin MacLeod / incompetech) and record title, author, licence, URL in `production/music_credits.md`.
   - Mix: `mix_part.py` → about −17 LUFS integrated (target −16 to −18), music/SFX ducked under speech.
8. **Assembly:** `uv run --with pyyaml python tools/assemble.py --part 1 --audio renders/audio/part1_mix.wav --subs [--preview --out renders/part1_animatic_preview.mp4]`. Each shot uses its clip if present, else its keyframe animated with a zoompan inferred from `camera`, else a slate — so the animatic always plays at final timing. Subtitles use `Encoding=-1` + RLM marks so Arabic renders right-to-left (without this the word order flips).
9. **Index:** after every session run `tools/shot_index.py` and `tools/contact_sheet.py S01 … S09`, commit them, and post the sheets to the owner. **The owner wants every produced shot uploaded with its exact position in the film.**

**PX shots:** generate a still with text2im, then animate it with an ffmpeg `zoompan` push/pan.
**HF shots:** build with HyperFrames (`hyperframes` CLI). Use the palette from `bible/style.md`, with gold glyphs `#d9a441` on night `#1b1f3a`.

## 7. Current state and next tasks (keep this section updated)
**Done** (see `production/status.md` for detail):
- Story, both screenplays, character/location/style bible.
- 9 character ref sheets plus key art.
- Part 1 shot list (79 shots, 600 s, validated).
- Part 2 scene skeleton with locked durations.
- Tools.
- Pilot clips for S05-01 (kling) and S08-01 (seedance), both `clip_done`. Pilot spend ≈$6.24.
- **All 74 remaining Part 1 keyframes** generated and QC'd (`kf_done`). HF shots S01-07, S02-07, S09-04 rendered (`clip_done`).
- **Full Part 1 audio:** 29 MSA voice lines, original score, SFX, final mix (600 s).
- **Part 1 animatic** (stills + motion + final audio + Arabic subtitles) rendered and published as a GitHub Release asset, not in git.
- `production/shot_index.md` and contact sheets for S01–S09.
- **Waiting on owner:** budget approval for the 72 remaining video clips, ≈$120 (kling) to ≈$370 (seedance). Native-speaker check of the Tifinagh title `ⴰⵎⵎⵍⵏ`.

**Part 2 (2026-10-06):**
- Part 2 shot list written: 98 shots, 720 s, validated (KF2V×78, T2V×17, HF×3). New location `HAMADA` (stony plateau, S10/S11).
- All 95 Part 2 keyframes generated + QC'd (`kf_done`). HF shots S14-06, S15-03, S18-04 rendered (`clip_done`).
- Part 2 audio: 31 MSA lines, score, SFX, mix `part2_mix.wav` (−17.7 LUFS).
- Part 2 animatic + the full **22:00 film animatic** (`master.py`) published as GitHub Release `part2-animatic-v1`.
- Screenplay lines marked ⁺ in Part 2 were added during shot-listing; the owner may delete them (re-run make_voice/mix_part after).
- **Waiting on owner:** budget for video clips. Remaining: 72 (Part 1) + 95 (Part 2) = 167 clips ≈ $255 (kling) to ≈ $780 (seedance). Tifinagh check of `ⴰⵎⵎⵍⵏ` (used in S02-07, S18-04).

**Next, in order:**
1. ~~Animatic~~ ✔. ~~All keyframes (both parts)~~ ✔. ~~Audio (both parts)~~ ✔. ~~22:00 animatic~~ ✔.
2. Once the owner approves the budget: **clips** scene by scene (`viktor_produce.py clip`; kling for medium/close, seedance for wides), QC, commit per scene. Re-run `assemble.py --part N`, `master.py`, `shot_index.py`. Re-time lines with `mix_part.py` if clip lengths change. New release per part.
3. Deliver `film_master.mp4` (1080p) as the final release.

**Gotcha:** never run two `viktor_produce.py kf` processes on overlapping IDs; parallel image calls can return the same file. After any batch, md5-check `renders/keyframes/*.jpg` for duplicates.

## 8. Session protocol (every agent, every session)
1. `git pull`. Read this file and `production/status.md`.
2. Pick the **next unfinished item** from §7. Do not jump ahead or redesign.
3. Work scene by scene. After each scene:
   - Run `validate_shots.py`.
   - Update `status` fields and `production/status.md`.
   - Commit with the message `S0X: <what> (<n> shots)`.
   - Push.
4. Before ending: update §7 and add a one-line entry to §9.
5. Never force-push, never rewrite history, never delete approved assets.

## 9. Changelog
- 2026-10-06 — v1 by Viktor:
  - Wrote the story, screenplays and bible.
  - Generated 9 ref sheets and the key art.
  - Wrote the Part 1 shot list (79 shots) and the Part 2 skeleton.
  - Wrote the tools.
  - Made pilot keyframes for S05-01 and S08-01.
- 2026-10-06 — Pilot clips by Viktor:
  - S08-01 was made with seedance-2.5 and S05-01 with kling-video-v3-pro, after seedance returned 422.
  - Added to `viktor_produce.py`: 16:9 pre-crop of keyframes and an automatic kling fallback.
  - Added model-choice guidance to §6.4.
  - Added README.md, production/status.md and .gitignore.
- 2026-10-06 — Part 1 keyframes, audio and animatic by Viktor:
  - Generated 74 keyframes (JPG). Converted S05-01/S08-01 to JPG too.
  - Rewrote `action`/`camera` for S01-04, S02-05, S02-06, S04-03, S04-09, S05-08, S05-11, S06-03 after QC. No dialogue changes.
  - Added "comic panels, split screen, collage, multiple frames, storyboard grid" to NEGATIVE (common.py + style.md).
  - New tools: make_voice, make_score, mix_part, make_hf, contact_sheet, shot_index. Rewrote assemble.py (stills + zoompan, RTL subtitles).
  - Owner decisions: MSA; music generated or from free libraries.
- 2026-10-06 — Part 2 by Viktor:
  - Wrote `shots_part2.yaml` (98 shots, 720 s) and generated 95 keyframes; 6 redone after QC (S10-03, S10-14, S11-07, S13-09, S15-01, S16-02; two were text2im duplicates).
  - Rewrote `action` for 4 shots after QC. No dialogue changes beyond the ⁺ lines noted in §7.
  - HF shots S14-06, S15-03, S18-04 (make_hf.py). Credit text uses «،» (font lacks em dash).
  - 31 voice lines, score, mix. Part 2 animatic + full 22:00 animatic via new `master.py`. Release `part2-animatic-v1`.
