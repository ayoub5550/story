"""Expand a shot into final generation prompts + reference image list (JSON).
Usage: python tools/build_prompt.py S03-04 [S03-05 ...]   |   --scene S03   |   --all"""
import json, argparse
from common import ROOT, STYLE_PREFIX, NEGATIVE, characters, locations, parts, iter_shots

TOD = {"night": "night, moonlight and firelight, deep indigo shadows", "day": "bright midday desert light",
       "sunset": "warm sunset golden-orange light, long shadows", "dawn": "dawn, cool blue turning to gold",
       "morning": "clear morning light", "mythic": "dreamlike pastel glowing light"}


def build(sc, sh):
    chars, locs = characters(), locations()
    ch_desc, refs = [], []
    kids = set(sh.get("child", []))          # tokens to render at child age (no adult ref sheet)
    for t in sh["chars"]:
        c = chars[t]
        if t in kids and c.get("child_prompt"):
            ch_desc.append(c["child_prompt"])
        else:
            ch_desc.append(c["prompt"])
            if c.get("ref"): refs.append(str(ROOT / c["ref"]))
    loc_src = sh.get("loc", sc["loc"])          # per-shot override wins
    loc_tokens = [loc_src] if isinstance(loc_src, str) else loc_src
    loc = " / ".join(locs[l]["prompt"] for l in loc_tokens)
    tod_key = str(sh.get("tod", sc.get("tod", "")))
    tod = next((v for k, v in TOD.items() if k in tod_key), "")
    light = f" Lighting: {tod}." if tod else ""
    subject = (" Characters: " + "; ".join(ch_desc) + ".") if ch_desc else ""
    keyframe = f"{STYLE_PREFIX} Setting: {loc}.{light}{subject} Shot: {sh['camera']}. Action: {sh['action']}. Avoid: {NEGATIVE}."
    motion = f"{STYLE_PREFIX} {sh['camera']}. {sh['action']}. Keep character designs exactly as in the reference images. Smooth hand-drawn animation, subtle natural motion, no new characters, no text. Avoid: {NEGATIVE}."
    return {"id": sh["id"], "dur": sh["dur"], "method": sh["method"], "keyframe_prompt": keyframe,
            "motion_prompt": motion, "ref_images": refs, "audio": {k: sh[k] for k in ("vo", "dlg", "sfx") if k in sh}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ids", nargs="*"); ap.add_argument("--scene"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args(); out = []
    for doc in parts().values():
        for sc, sh in iter_shots(doc):
            if a.all or sh["id"] in a.ids or sc["scene"] == a.scene:
                out.append(build(sc, sh))
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
