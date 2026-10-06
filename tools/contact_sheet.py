"""Contact sheet of a scene's keyframes, labelled with shot id, film timecode, duration and method.
Usage: uv run --with pyyaml --with pillow python tools/contact_sheet.py S03 [S04 ...]  -> renders/sheets/<SCENE>.jpg"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).parent))
from common import ROOT, parts, iter_shots, tc

FONT = "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
W, H, COLS, PAD = 480, 270, 4, 14


def timeline():
    out, t = {}, 0
    for p in (1, 2):
        for sc, sh in iter_shots(parts()[p]):
            out.setdefault(sc["scene"], {"title": sc["title"], "shots": []})["shots"].append((sh, t)); t += sh["dur"]
    return out


def thumb(sid):
    for ext in ("jpg", "png"):
        p = ROOT / f"renders/keyframes/{sid}.{ext}"
        if p.exists():
            im = Image.open(p).convert("RGB"); w, h = im.size; ch = int(w * 9 / 16); top = int((h - ch) * 0.3)
            return im.crop((0, top, w, top + ch)).resize((W, H))   # same 16:9 crop the clip stage uses
    return None


def sheet(scene, tl):
    s = tl[scene]; shots = s["shots"]; rows = (len(shots) + COLS - 1) // COLS
    img = Image.new("RGB", (COLS * (W + PAD) + PAD, 90 + rows * (H + 44 + PAD)), (27, 31, 58))
    d = ImageDraw.Draw(img); f_ar = ImageFont.truetype(FONT, 40); f_m = ImageFont.truetype(MONO, 20)
    t0, t1 = shots[0][1], shots[-1][1] + shots[-1][0]["dur"]
    d.text((img.width - PAD, 18), s["title"], font=f_ar, fill=(217, 164, 65), anchor="ra", direction="rtl")
    d.text((PAD, 8), scene, font=ImageFont.truetype(MONO, 24), fill=(217, 164, 65))
    d.text((PAD, 46), f"{tc(t0)}–{tc(t1)}  ({t1 - t0}s, {len(shots)} shots)", font=f_m, fill=(230, 220, 200))
    for i, (sh, t) in enumerate(shots):
        x, y = PAD + (i % COLS) * (W + PAD), 90 + (i // COLS) * (H + 44 + PAD)
        th = thumb(sh["id"])
        if th: img.paste(th, (x, y))
        else:
            d.rectangle([x, y, x + W, y + H], outline=(217, 164, 65), width=2)
            d.text((x + W // 2, y + H // 2), f"{sh['method']}\n(graphics)" if sh["method"] == "HF" else "no keyframe", font=f_m, fill=(217, 164, 65), anchor="mm", align="center")
        d.text((x, y + H + 8), f"{sh['id']}  {tc(t)}–{tc(t + sh['dur'])}  {sh['dur']}s  {sh['method']}", font=f_m, fill=(230, 220, 200))
    out = ROOT / f"renders/sheets/{scene}.jpg"; out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, quality=85); return out


if __name__ == "__main__":
    tl = timeline()
    for sc in sys.argv[1:]: print(sheet(sc, tl))
