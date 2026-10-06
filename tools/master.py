"""Join the assembled parts into the full 22-minute film + one merged Arabic .srt.
Usage: python tools/master.py [--preview]
  reads  renders/part1_cut.mp4 + renders/part2_cut.mp4   (or *_animatic_preview.mp4 with --preview)
         renders/part1.srt + renders/part2.srt           (written by assemble.py --subs)
  writes renders/film_master.mp4 (or film_preview.mp4) + renders/film.srt
Both parts must be assembled with the same settings (assemble.py --audio ... --subs [--preview])."""
import argparse, re, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def shift_srt(text, offset, start_index):
    def ts(m):
        h, mi, s, ms = map(int, m.groups())
        t = round((h * 3600 + mi * 60 + s) * 1000 + ms + offset * 1000)  # integer ms, no float carry bugs
        h, r = divmod(t, 3_600_000); mi, r = divmod(r, 60_000); s, ms = divmod(r, 1000)
        return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"
    blocks, out = [b for b in text.strip().split("\n\n") if b.strip()], []
    for i, b in enumerate(blocks):
        lines = b.split("\n"); lines[0] = str(start_index + i)
        lines[1] = re.sub(r"(\d+):(\d+):(\d+),(\d+)", ts, lines[1]); out.append("\n".join(lines))
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--preview", action="store_true"); a = ap.parse_args()
    R = ROOT / "renders"
    vids = [R / ("part1_animatic_preview.mp4" if a.preview else "part1_cut.mp4"), R / ("part2_animatic_preview.mp4" if a.preview else "part2_cut.mp4")]
    out = R / ("film_preview.mp4" if a.preview else "film_master.mp4")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("\n".join(f"file '{v}'" for v in vids))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f.name, "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
    blocks, off = [], 0.0
    for p, v in zip((R / "part1.srt", R / "part2.srt"), vids):
        if p.exists(): blocks += shift_srt(p.read_text(encoding="utf-8"), off, len(blocks) + 1)
        off += dur(v)
    (R / "film.srt").write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    print("wrote", out, f"{dur(out):.1f}s", "+ film.srt", len(blocks), "subs")


if __name__ == "__main__":
    main()
