"""Scratch/final voice track for a part: one ElevenLabs TTS clip per `vo`/`dlg` line, placed on the timeline.
Usage (from /work):  uv run --with pyyaml python repos/story/tools/make_voice.py --part 1 [--redo S03-02 ...]
Writes renders/audio/lines/<SHOT>.mp3 (one per line, cached) and renders/audio/lines/part<N>_lines.json
(shot, speaker, text, start, duration, overrun warnings). tools/mix_part.py turns these into the voice stem.
Speaker -> voice map lives in SPEAKERS below (derived from bible/characters.yaml `voice`). Keep it fixed for the film.
TTS calls are SEQUENTIAL (parallel calls collide on the output filename)."""
import asyncio, argparse, json, re, shutil, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, parts, iter_shots
from sdk.tools.utils_tools import text_to_speech

# speaker prefix in the shot list (Arabic) -> (voice, stability, pitch_semitones, audio tag)
SPEAKERS = {
    "NARRATOR": ("matilda", 0.35, 0, ""),      # the grandmother narrates all `vo`
    "الجدّة": ("matilda", 0.35, 0, ""),
    "أمامّلن": ("george", 0.6, 0, ""),
    "أدلاسغ": ("liam", 0.5, 0, ""),
    "أدلاسغ_طفل": ("liam", 0.5, 3, ""),       # child Adelasegh: liam pitched up
    "إيلياس": ("lily", 0.5, 3, ""),           # 8-year-old boy: lily pitched up
    "تانفوست": ("matilda", 0.6, 0, ""),
    "تافوكت": ("lily", 0.5, 0, ""),
    "شيخ": ("bill", 0.6, 0, ""),
    "قارئة الرمل": ("charlotte", 0.4, 0, "[mysterious] "),
    "أرواح": ("laura", 0.3, -2, "[whispers] "),
    "أجبّار": ("bill", 0.6, -2, ""),
    "أغ إزمي": ("roger", 0.5, 0, ""),
    "زعيم": ("callum", 0.5, 0, ""),
}
# Pronunciation overrides: same words as the screenplay, only tashkeel added where TTS misread (verify with speech_to_text)
SAY = {"S04-06": "الظِّلُّ! يا خالي، الظِّلُّ!"}
LEAD = 0.4  # seconds after shot start before a line begins
LINES = ROOT / "renders/audio/lines"


def parse(sh):
    """Return (speaker_key, clean_text) for a shot, or None."""
    if sh.get("vo"):
        return "NARRATOR", sh["vo"]
    if not sh.get("dlg"):
        return None
    who, txt = sh["dlg"].split(":", 1)
    who = who.strip(); paren = re.search(r"\((.*?)\)", who); base = re.sub(r"\s*\(.*?\)", "", who).strip()
    if base == "أدلاسغ" and paren and re.search(r"\d", paren.group(1)) and int(re.search(r"\d+", paren.group(1)).group()) < 16:
        base = "أدلاسغ_طفل"
    if base not in SPEAKERS:
        base = next((k for k in SPEAKERS if base.startswith(k)), base)
    return base, txt.strip()


def dur_of(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


async def tts(spk, text, dst, prev, nxt):
    voice, stab, pitch, tag = SPEAKERS[spk]
    r = await text_to_speech(text=tag + text, model="eleven_v4", voice=voice, stability=stab, language_code="ar",
                             previous_text=prev, next_text=nxt)
    src = Path(r.local_path) if getattr(r, "local_path", None) else None
    if not src or not src.exists():
        raise RuntimeError(f"tts failed: {r}")
    if pitch:  # pitch shift without changing tempo (rubberband if present, else asetrate+atempo)
        sr = 44100; f = 2 ** (pitch / 12)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(src), "-af",
                        f"aresample={sr},asetrate={sr*f:.0f},aresample={sr},atempo={1/f:.4f}", str(dst)], check=True)
    else:
        shutil.copy(src, dst)


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, default=1); ap.add_argument("--redo", nargs="*", default=[])
    a = ap.parse_args(); LINES.mkdir(parents=True, exist_ok=True)
    items, t = [], 0.0
    for sc, sh in iter_shots(parts()[a.part]):
        pr = parse(sh)
        if pr: items.append({"shot": sh["id"], "scene": sc["scene"], "speaker": pr[0], "text": pr[1], "start": round(t + LEAD, 2), "shot_end": t + sh["dur"]})
        t += sh["dur"]
    for i, it in enumerate(items):
        dst = LINES / f"{it['shot']}.mp3"
        if not dst.exists() or it["shot"] in a.redo:
            prev = items[i - 1]["text"] if i else None; nxt = items[i + 1]["text"] if i + 1 < len(items) else None
            await tts(it["speaker"], SAY.get(it["shot"], it["text"]), dst, prev, nxt)
            print("tts", it["shot"], it["speaker"], flush=True)
        it["duration"] = round(dur_of(dst), 2)
    warn = []
    for i, it in enumerate(items):
        end = it["start"] + it["duration"]
        nxt_start = items[i + 1]["start"] if i + 1 < len(items) else 1e9
        if end > nxt_start - 0.2:
            warn.append(f"{it['shot']}: line ends {end:.1f}s, overlaps next line at {nxt_start:.1f}s")
        elif end > it["shot_end"]:
            it["note"] = f"runs {end - it['shot_end']:.1f}s into next shot (ok for VO)"
    out = LINES / f"part{a.part}_lines.json"
    out.write_text(json.dumps({"lines": items, "warnings": warn}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(items)} lines -> {out}"); [print("WARN", w) for w in warn]


asyncio.run(main())
