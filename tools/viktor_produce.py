"""Viktor-sandbox adapter: produce keyframes and clips for shots (uses Viktor SDK; other agents: port this to your provider).
Usage (from /work):  uv run --with pyyaml python repos/story/tools/viktor_produce.py S05-01 [S05-02 ...] [--stage kf|clip|both] [--model seedance-2.5]
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
    dst = KF / f"{p['id']}.png"; shutil.copy(r.local_path, dst)
    log({"id": p["id"], "stage": "kf", "model": "gpt-image-2.5-sunburst", "path": str(dst.relative_to(ROOT)),
         "prompt_sha": hashlib.sha1(p["keyframe_prompt"].encode()).hexdigest()[:10]})
    return dst


async def clip(p, model):
    CL.mkdir(parents=True, exist_ok=True)
    kf = KF / f"{p['id']}.png"
    if p["method"] == "KF2V":
        # keyframes are 3:2 (text2im limit). Crop to 16:9 first (keep headroom: 30% of the excess from top),
        # otherwise kling returns a 3:2 clip. See AGENTS.md §6.4.
        kf169 = CL / f".{p['id']}_kf169.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(kf), "-vf", "crop=iw:trunc(iw*9/16/2)*2:(ih-trunc(iw*9/16/2)*2)*0.3", str(kf169)], check=True)
        imgs = [str(kf169)]
    else:
        imgs = p["ref_images"]
    dur = max(4, min(int(p["dur"]) + 1, 15))  # +1 s handle for trimming
    r = await text_to_video(prompt=p["motion_prompt"], model=model, image_paths=imgs or None, aspect_ratio="16:9", duration_seconds=dur)
    if (r.error or not r.local_path) and model == "seedance-2.5":
        # seedance-2.5 sometimes rejects close/medium shots with visible faces (HTTP 422) -> fall back to kling
        print(f"{p['id']}: seedance failed ({r.error}); falling back to kling-video-v3-pro", flush=True)
        model = "kling-video-v3-pro"
        r = await text_to_video(prompt=p["motion_prompt"], model=model, image_paths=imgs[:1] if imgs else None, aspect_ratio="16:9", duration_seconds=dur)
    if p["method"] == "KF2V":
        kf169.unlink(missing_ok=True)
    if r.error or not r.local_path:
        raise RuntimeError(f"{p['id']}: {r.error or r.response_text}")
    dst = CL / f"{p['id']}.mp4"; shutil.copy(r.local_path, dst)
    log({"id": p["id"], "stage": "clip", "model": model, "dur": r.duration_seconds, "res": r.resolution,
         "cost_usd": r.usd_cost_estimate, "path": str(dst.relative_to(ROOT))})
    return dst


async def run(sid, stage, model):
    shots = {sh["id"]: (sc, sh) for d in parts().values() for sc, sh in iter_shots(d)}
    p = build(*shots[sid])
    if p["method"] in ("PX", "HF"):
        return sid, "skipped (PX/HF built manually)"
    out = []
    if p["method"] == "KF2V" and stage in ("kf", "both"):
        out.append(str(await keyframe(p)))
    if stage in ("clip", "both"):
        out.append(str(await clip(p, model)))
    return sid, out


async def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="+")
    ap.add_argument("--stage", default="both", choices=["kf", "clip", "both"]); ap.add_argument("--model", default="seedance-2.5")
    a = ap.parse_args()
    res = await asyncio.gather(*[run(i, a.stage, a.model) for i in a.ids], return_exceptions=True)
    for r in res: print(r)

asyncio.run(main())
