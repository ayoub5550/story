"""Assemble approved clips into a continuous cut with ffmpeg.
Expects clips at renders/clips/<SHOT_ID>.mp4 (any res; normalised to 1920x1080@24, trimmed/padded to `dur`).
Missing clips become a labelled slate so the cut always has the exact timing (animatic mode).
Usage: python tools/assemble.py --part 1 [--out renders/part1_cut.mp4] [--audio renders/audio/part1_mix.wav]"""
import argparse, subprocess, tempfile
from pathlib import Path
from common import ROOT, parts, iter_shots

VF = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p"


def norm(src, dur, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-t", str(dur), "-vf", VF,
                    "-an", "-c:v", "libx264", "-crf", "18", str(dst)], check=True)


def slate(text, dur, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x1b1f3a:s=1920x1080:r=24:d={dur}",
                    "-vf", f"drawtext=text='{text}':fontcolor=0xd9a441:fontsize=64:x=(w-tw)/2:y=(h-th)/2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dst)], check=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, required=True)
    ap.add_argument("--out"); ap.add_argument("--audio"); a = ap.parse_args()
    out = Path(a.out or ROOT / f"renders/part{a.part}_cut.mp4"); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp()); lst = []
    for i, (sc, sh) in enumerate(iter_shots(parts()[a.part])):
        src = ROOT / f"renders/clips/{sh['id']}.mp4"; dst = tmp / f"{i:04d}.mp4"
        norm(src, sh["dur"], dst) if src.exists() else slate(f"{sh['id']}  {sh['method']}  {sh['dur']}s", sh["dur"], dst)
        lst.append(f"file '{dst}'")
    (tmp / "list.txt").write_text("\n".join(lst))
    video = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(video)], check=True)
    if a.audio:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", a.audio, "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-shortest", str(out)], check=True)
    else:
        video.replace(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
