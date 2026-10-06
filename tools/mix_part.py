"""Mix a part: voice lines (make_voice.py) + music & sfx stems (make_score.py) -> renders/audio/part<N>_mix.wav
Usage: uv run --with numpy --with scipy --with soundfile python tools/mix_part.py --part 1
- Lines start at shot start + LEAD; a line that would overlap the previous one is pushed after it (+0.35 s) and reported.
- Music is ducked under voice (sidechain), then the whole mix is loudness-normalised to -16 LUFS / -1.5 dBTP (ffmpeg loudnorm).
- Final placements are written back to renders/audio/lines/part<N>_lines.json (`placed`), used for subtitles."""
import argparse, json, subprocess, tempfile
from pathlib import Path
import numpy as np, soundfile as sf
from scipy import signal

SR = 48000
ROOT = Path(__file__).resolve().parents[1]
GAIN = {"voice": 1.0, "music": 0.30, "sfx": 0.35}   # relative stem levels before loudnorm


def load(path):
    with tempfile.NamedTemporaryFile(suffix=".wav") as t:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), t.name], check=True)
        x, _ = sf.read(t.name)
    return x


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, default=1); a = ap.parse_args()
    A = ROOT / "renders/audio"; meta_p = A / f"lines/part{a.part}_lines.json"; meta = json.loads(meta_p.read_text())
    music, _ = sf.read(A / f"part{a.part}_music.wav"); sfx, _ = sf.read(A / f"part{a.part}_sfx.wav")
    n = len(music); voice = np.zeros((n, 2)); prev_end = 0; pushed = []
    for it in meta["lines"]:
        x = load(A / f"lines/{it['shot']}.mp3"); x = x / (np.sqrt(np.mean(x ** 2)) + 1e-9) * 0.08   # RMS-match lines
        start = it["start"]
        if start < prev_end + 0.35:
            pushed.append(f"{it['shot']}: pushed {prev_end + 0.35 - start:.1f}s"); start = prev_end + 0.35
        it["placed"] = round(start, 2); prev_end = start + len(x) / SR
        pan = 0.0 if it["speaker"] == "NARRATOR" else (-0.12 if it["speaker"] == "أمامّلن" else 0.12)
        if it["speaker"] == "أرواح":   # spirits: doubled, wide, delayed
            k = int(start * SR); m = min(len(x), n - k - 9000)
            voice[k:k + m, 0] += x[:m] * 0.8; voice[k + 7000:k + 7000 + m, 1] += x[:m] * 0.8; continue
        k = int(start * SR); m = min(len(x), n - k)
        voice[k:k + m, 0] += x[:m] * np.sqrt(1 - pan); voice[k:k + m, 1] += x[:m] * np.sqrt(1 + pan)
    # light room on dialogue/narration
    ir = np.random.default_rng(3).standard_normal(int(0.6 * SR)) * np.exp(-np.arange(int(0.6 * SR)) / SR * 11)
    for c in range(2):
        wet = signal.fftconvolve(voice[:, c], ir)[:n]; voice[:, c] += 0.08 * wet / (np.max(np.abs(wet)) + 1e-9) * np.max(np.abs(voice[:, c]))
    # sidechain duck: music/sfx -8 dB under voice
    env = np.abs(voice).max(1); b, aa = signal.butter(1, 4 / (SR / 2)); env = signal.filtfilt(b, aa, env)
    env = np.clip(env / (np.percentile(env[env > 1e-4], 90) + 1e-9), 0, 1)
    duck = 1 - 0.6 * env
    mix = GAIN["voice"] * voice + (GAIN["music"] * music + GAIN["sfx"] * sfx) * duck[:, None]
    mix /= np.max(np.abs(mix)) + 1e-9
    raw = A / f"part{a.part}_mix_raw.wav"; out = A / f"part{a.part}_mix.wav"
    sf.write(raw, mix * 0.9, SR, subtype="PCM_24")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-af", "loudnorm=I=-16:TP=-1.5:LRA=14", "-ar", str(SR), str(out)], check=True)
    raw.unlink()
    meta["pushed"] = pushed; meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", out); [print("PUSH", p) for p in pushed]


if __name__ == "__main__":
    main()
