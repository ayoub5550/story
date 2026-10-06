"""Viktor-sandbox adapter: produce keyframes and clips for shots (uses Viktor SDK; other agents: port this to your provider).
Usage (from /work):  uv run --with pyyaml python repos/story/tools/viktor_produce.py [S05-01 ...] [--scene S05 ...] [--stage kf|clip|both] [--model kling-video-v3-pro]
  clip stage: resumable (skips shots that already have renders/clips/<ID>.mp4), CLIP_PAR env = parallel jobs (default 4),
  md5 de-dup + 3 retries, writes raw master to renders/raw/ and compressed copy to renders/clips/, sets status clip_done.
- KF2V: keyframe via coworker_text2im(image_paths=ref sheets) -> renders/keyframes/<ID>.png, then image-to-video -> renders/clips/<ID>.mp4
- T2V : text_to_video with character refs (if any) -> renders/clips/<ID>.mp4
- PX/HF: skipped (built with ffmpeg / HyperFrames, see AGENTS.md)
Every generation is appended to production/gen_log.jsonl (id, stage, model, prompt hash, cost, path)."""
import subprocess
import asyncio, argparse, json, shutil, hashlib, time, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, parts, iter_shots
from build_prompt import build
from sdk.tools.utils_tools import coworker_text2im, text_to_video

FORCE = False
KF_LOCK = asyncio.Lock()  # text2im calls run one at a time: parallel calls were seen returning the SAME local file
KF, CL, LOG = ROOT / "renders/keyframes", ROOT / "renders/clips", ROOT / "production/gen_log.jsonl"


def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


async def keyframe(p):
    KF.mkdir(parents=True, exist_ok=True)
    async with KF_LOCK:
        r = await coworker_text2im(prompt=p["keyframe_prompt"], image_paths=p["ref_images"] or None, aspect_ratio="3:2", output_format="png")
    # keyframes are stored as high-quality JPEG (q92) to keep git small (~0.5 MB vs 2.5 MB PNG)
    dst = KF / f"{p['id']}.jpg"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", r.local_path, "-q:v", "2", str(dst)], check=True)
    log({"id": p["id"], "stage": "kf", "model": "gpt-image-2.5-sunburst", "path": str(dst.relative_to(ROOT)),
         "prompt_sha": hashlib.sha1(p["keyframe_prompt"].encode()).hexdigest()[:10]})
    return dst


CLIP_SEM = asyncio.Semaphore(int(__import__("os").environ.get("CLIP_PAR", "4")))  # parallel video jobs
SEEN = {}  # md5 of raw clips produced in this process -> shot id (guards against provider/local-path collisions)
RAW = ROOT / "renders/raw"      # full-quality provider output (gitignored; goes to a Release as clip masters)
DEFAULT_CLIP_MODEL = "kling-video-v3-pro"  # owner-approved production default (2026-10-06): ~$0.17/s, 1080p, handles faces


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def compress(src, dst):
    """AGENTS §6.6: git copy = 1280 wide, H.264 crf 24, no audio (native model audio is discarded)."""
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-an", "-vf", "scale=1280:-2,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-movflags", "+faststart", str(dst)], check=True)


def set_status(sid, new):
    """Shots are one-line YAML maps -> safe in-place edit of `status:` on the shot's line."""
    import re
    for f in (ROOT / "production").glob("shots_part*.yaml"):
        t = f.read_text(encoding="utf-8")
        t2 = re.sub(r"(\{id: %s,.*status: )(\w+)(\})" % re.escape(sid), lambda m: m.group(1) + new + m.group(3), t)
        if t2 != t:
            f.write_text(t2, encoding="utf-8"); return True
    return False


async def clip(p, model):
    """Image-to-video from the shot keyframe (KF2V *and* T2V: the T2V still is the start frame -> matches the animatic).
    Writes renders/raw/<ID>.mp4 (master) + renders/clips/<ID>.mp4 (compressed, committed) and sets status clip_done."""
    CL.mkdir(parents=True, exist_ok=True); RAW.mkdir(parents=True, exist_ok=True)
    kf = next((KF / f"{p['id']}.{e}" for e in ("jpg", "png") if (KF / f"{p['id']}.{e}").exists()), None)
    imgs = None
    if kf:
        # keyframes are 3:2 (text2im limit). Crop to 16:9 first (keep headroom: 30% of the excess from top),
        # otherwise kling returns a 3:2 clip. See AGENTS.md §6.4.
        kf169 = CL / f".{p['id']}_kf169.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(kf), "-vf", "crop=iw:trunc(iw*9/16/2)*2:(ih-trunc(iw*9/16/2)*2)*0.3", str(kf169)], check=True)
        imgs = [str(kf169)]
    elif p["ref_images"]:
        imgs = p["ref_images"]
    dur = max(4, min(int(p["dur"]) + 1, 15))  # +1 s handle for trimming
    r, err = None, None
    async with CLIP_SEM:
        for attempt in range(3):
            m = model
            r = await text_to_video(prompt=p["motion_prompt"], model=m, image_paths=imgs, aspect_ratio="16:9", duration_seconds=dur)
            if (r.error or not r.local_path) and m == "seedance-2.5":
                # seedance-2.5 sometimes rejects close/medium shots with visible faces (HTTP 422) -> fall back to kling
                print(f"{p['id']}: seedance failed ({r.error}); falling back to kling-video-v3-pro", flush=True)
                m = "kling-video-v3-pro"
                r = await text_to_video(prompt=p["motion_prompt"], model=m, image_paths=imgs[:1] if imgs else None, aspect_ratio="16:9", duration_seconds=dur)
            if r.error or not r.local_path:
                err = r.error or r.response_text; print(f"{p['id']}: clip attempt {attempt+1} failed: {err}", flush=True); continue
            h = md5(r.local_path)
            if h in SEEN and SEEN[h] != p["id"]:
                err = f"duplicate of {SEEN[h]}"; print(f"{p['id']}: {err}, retrying", flush=True); continue
            SEEN[h] = p["id"]; break
        else:
            raise RuntimeError(f"{p['id']}: {err}")
    if kf: kf169.unlink(missing_ok=True)
    raw = RAW / f"{p['id']}.mp4"; shutil.copy(r.local_path, raw)
    dst = CL / f"{p['id']}.mp4"; compress(raw, dst)
    set_status(p["id"], "clip_done")
    log({"id": p["id"], "stage": "clip", "model": m, "dur": r.duration_seconds, "res": r.resolution,
         "cost_usd": r.usd_cost_estimate, "path": str(dst.relative_to(ROOT))})
    print(f"{p['id']} clip ok ({m}, {r.duration_seconds}s, ${r.usd_cost_estimate})", flush=True)
    return dst


async def run(sid, stage, model):
    shots = {sh["id"]: (sc, sh) for d in parts().values() for sc, sh in iter_shots(d)}
    p = build(*shots[sid])
    if p["method"] in ("PX", "HF"):
        return sid, "skipped (PX/HF built manually)"
    out = []
    # T2V shots also get a still in --stage kf: it is the animatic frame and can be used as an I2V start frame later
    if p["method"] in ("KF2V", "T2V") and stage in ("kf", "both"):
        if any((KF / f"{sid}.{e}").exists() for e in ("jpg", "png")) and not FORCE:
            out.append("kf exists (use --force to redo)")
        else:
            for attempt in range(3):
                try:
                    out.append(str(await keyframe(p))); break
                except Exception as e:  # transient API errors: retry
                    print(f"{sid}: kf attempt {attempt+1} failed: {e}", flush=True)
            else:
                return sid, "kf FAILED"
        print(sid, "kf ok", flush=True)
    if stage in ("clip", "both"):
        if (CL / f"{sid}.mp4").exists() and not FORCE:
            out.append("clip exists (use --force to redo)")
        else:
            out.append(str(await clip(p, model)))
    return sid, out


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="*")
    ap.add_argument("--stage", default="both", choices=["kf", "clip", "both"]); ap.add_argument("--model", default=DEFAULT_CLIP_MODEL)
    ap.add_argument("--force", action="store_true", help="regenerate keyframes/clips that already exist")
    ap.add_argument("--scene", action="append", default=[], help="add every shot of a scene, e.g. --scene S03 (repeatable)")
    a = ap.parse_args(); global FORCE; FORCE = a.force
    for sc_id in a.scene:
        a.ids += [sh["id"] for d in parts().values() for sc, sh in iter_shots(d) if sc["scene"] == sc_id]
    res = await asyncio.gather(*[run(i, a.stage, a.model) for i in a.ids], return_exceptions=True)
    for r in res: print(r)

asyncio.run(main())
