"""Assemble a part into one continuous cut with ffmpeg.
Per shot, the best available source is used:  clip (renders/clips/<ID>.mp4)  >  keyframe still with a slow camera move
(renders/keyframes/<ID>.jpg|png, = animatic)  >  labelled slate. So the cut always has the exact timing.
Usage: python tools/assemble.py --part 1 [--out renders/part1_cut.mp4] [--audio renders/audio/part1_mix.wav] [--subs] [--preview]
  --subs     burn Arabic subtitles from renders/audio/lines/part<N>_lines.json (also writes renders/part<N>.srt)
  --preview  1280x720 output (fast, small; for Slack/review)
Shots are rendered in parallel (all cores)."""
import argparse, json, os, subprocess, tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from common import ROOT, parts, iter_shots

W, H = 1920, 1080
VF = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p"


def norm(src, dur, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-stream_loop", "-1", "-i", str(src), "-t", str(dur), "-vf", VF,
                    "-an", "-c:v", "libx264", "-crf", "18", "-threads", "2", str(dst)], check=True)


def move_for(camera):
    """Pick a gentle camera move for a still from the shot's `camera` text."""
    c = camera.lower()
    if "tilt up" in c: return "up"
    if "tilt down" in c: return "down"
    if "pan" in c or "tracking" in c or "glide" in c: return "pan"
    if "static" in c or "locked" in c: return "hold"
    return "push"


def still(src, dur, camera, dst):
    """Keyframe -> 16:9 crop (same 30%-from-top headroom rule as the clip stage) -> slow move."""
    n = int(dur * 24); mv = move_for(camera)
    z = {"push": f"1+0.10*on/{n}", "hold": f"1+0.03*on/{n}", "pan": "1.12", "up": "1.12", "down": "1.12"}[mv]
    x = {"pan": f"(iw-iw/zoom)*on/{n}"}.get(mv, "iw/2-(iw/zoom/2)")
    y = {"up": f"(ih-ih/zoom)*(1-on/{n})", "down": f"(ih-ih/zoom)*on/{n}"}.get(mv, "ih/2-(ih/zoom/2)")
    vf = (f"crop=iw:trunc(iw*9/16/2)*2:(ih-trunc(iw*9/16/2)*2)*0.3,scale=3840:2160,"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps=24,format=yuv420p")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(src), "-vf", vf, "-frames:v", str(n),
                    "-c:v", "libx264", "-crf", "18", "-threads", "2", str(dst)], check=True)


def slate(text, dur, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=0x1b1f3a:s={W}x{H}:r=24:d={dur}",
                    "-vf", f"drawtext=text='{text}':fontcolor=0xd9a441:fontsize=64:x=(w-tw)/2:y=(h-th)/2",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(dst)], check=True)


def source_of(sh):
    clip = ROOT / f"renders/clips/{sh['id']}.mp4"
    if clip.exists(): return "clip", clip
    for e in ("jpg", "png"):
        kf = ROOT / f"renders/keyframes/{sh['id']}.{e}"
        if kf.exists(): return "still", kf
    return "slate", None


def srt(part):
    meta = json.loads((ROOT / f"renders/audio/lines/part{part}_lines.json").read_text())
    def ts(s): h, r = divmod(s, 3600); m, s2 = divmod(r, 60); return f"{int(h):02d}:{int(m):02d}:{int(s2):02d},{int((s2 % 1) * 1000):03d}"
    rows = []
    for i, it in enumerate(meta["lines"], 1):
        st = it.get("placed", it["start"]); who = "" if it["speaker"] == "NARRATOR" else it["speaker"].replace("_طفل", "") + ": "
        rows.append(f"{i}\n{ts(st)} --> {ts(st + it['duration'])}\n\u200f{who}{it['text']}\u200f\n")
    p = ROOT / f"renders/part{part}.srt"; p.write_text("\n".join(rows), encoding="utf-8"); return p


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, required=True)
    ap.add_argument("--out"); ap.add_argument("--audio"); ap.add_argument("--subs", action="store_true"); ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    out = Path(a.out or ROOT / f"renders/part{a.part}_cut.mp4"); out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp()); jobs, report = [], {"clip": 0, "still": 0, "slate": 0}
    for i, (sc, sh) in enumerate(iter_shots(parts()[a.part])):
        kind, src = source_of(sh); dst = tmp / f"{i:04d}.mp4"; report[kind] += 1
        jobs.append((kind, src, sh, dst))
    def run(j):
        kind, src, sh, dst = j
        if kind == "clip": norm(src, sh["dur"], dst)
        elif kind == "still": still(src, sh["dur"], sh["camera"], dst)
        else: slate(f"{sh['id']}  {sh['method']}  {sh['dur']}s", sh["dur"], dst)
    with ThreadPoolExecutor(max(1, (os.cpu_count() or 4) // 2)) as ex: list(ex.map(run, jobs))
    (tmp / "list.txt").write_text("\n".join(f"file '{j[3]}'" for j in jobs))
    video = tmp / "video.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(video)], check=True)
    vf = []
    if a.subs:
        s = srt(a.part)
        vf.append(f"subtitles={s}:force_style='FontName=Noto Naskh Arabic,FontSize=20,PrimaryColour=&H00F0F0F0,OutlineColour=&H80000000,BorderStyle=1,Outline=1.5,Shadow=0,MarginV=28,Encoding=-1'")
    if a.preview: vf.append("scale=1280:720")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(video)] + (["-i", a.audio] if a.audio else [])
    cmd += (["-vf", ",".join(vf), "-c:v", "libx264", "-crf", "23" if a.preview else "18", "-preset", "medium"] if vf else ["-c:v", "copy"])
    cmd += (["-c:a", "aac", "-b:a", "192k", "-shortest"] if a.audio else []) + ["-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    print("wrote", out, report)


if __name__ == "__main__":
    main()
