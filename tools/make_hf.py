"""Graphics shots (method HF) rendered with Pillow + ffmpeg -> renders/clips/<ID>.mp4 (1920x1080, 24 fps).
Usage: uv run --with pillow --with numpy python tools/make_hf.py [S01-07 S02-07 S09-04]
Palette: gold #d9a441 on night #1b1f3a (bible/style.md). The dot-game symbols (two dots, circle, line) are drawn by
`dot_symbols()` — reuse it in S14/S15 so they stay identical (AGENTS.md §5.6).
Tifinagh of the hero's name uses the Tuareg (Ahaggar) consonantal spelling ⴰⵎⵎⵍⵏ — NEEDS A NATIVE-SPEAKER CHECK.
A future agent may rebuild these in HyperFrames; keep timing and layout."""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H, FPS = 1920, 1080, 24
GOLD, NIGHT = (217, 164, 65), (27, 31, 58)
F = "/usr/share/fonts/truetype/noto/"
KUFI, NASKH, TIFI = F + "NotoKufiArabic-Bold.ttf", F + "NotoNaskhArabic-Bold.ttf", F + "NotoSansTifinaghAhaggar-Regular.ttf"
NAME_TIFI = "ⴰⵎⵎⵍⵏ"
rng = np.random.default_rng(11)


def ease(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def writer(sid):
    out = ROOT / f"renders/clips/{sid}.mp4"; out.parent.mkdir(parents=True, exist_ok=True)
    return out, subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                                  "-i", "-", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)


def glow(img, r=8, k=1.6):
    g = img.filter(ImageFilter.GaussianBlur(r)); a = np.asarray(img, float) + k * np.asarray(g, float)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def dot_symbols(cx, cy, s=1.0):
    """Canonical dot-game symbols: two dots (water), circle (camp), line (road). Returns list of (x, y) points."""
    pts = [(cx - 330 * s, cy - 18 * s), (cx - 270 * s, cy + 18 * s)]                                   # two dots
    pts += [(cx + 60 * s * np.cos(a), cy + 60 * s * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 22, endpoint=False)]   # circle
    pts += [(x, cy) for x in np.linspace(cx + 200 * s, cx + 380 * s, 12)]                               # line
    return pts


def text_points(text, font, size, cx, cy, step=9, rtl=False):
    m = Image.new("L", (W, H)); d = ImageDraw.Draw(m); f = ImageFont.truetype(font, size)
    d.text((cx, cy), text, font=f, fill=255, anchor="mm", **({"direction": "rtl"} if rtl else {}))
    a = np.asarray(m); ys, xs = np.nonzero(a[::step, ::step] > 128)
    return list(zip(xs * step, ys * step))


def stars_to(points, n_stars, t, start):
    """Interpolate n_stars from `start` positions to target points (extra stars fade out)."""
    k = len(points); tgt = np.array(points + [tuple(start[i]) for i in range(k, n_stars)], float)
    e = ease(t); pos = start * (1 - e) + tgt * e
    alpha = np.ones(n_stars); alpha[k:] = 1 - e
    return pos, alpha


def draw_points(pos, alpha, size=3.0, bg=None):
    img = bg.copy() if bg is not None else Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(img)
    for (x, y), a in zip(pos, alpha):
        if a <= 0.02: continue
        c = tuple(int(v * a) for v in GOLD) if a < 1 else GOLD
        d.ellipse([x - size, y - size, x + size, y + size], fill=c)
    return img


def S01_07():
    out, p = writer("S01-07"); n = 600; start = np.c_[rng.uniform(0, W, n), rng.uniform(0, H, n)]
    tw = np.c_[rng.uniform(0.5, 1, n)]; pts = dot_symbols(W / 2, H / 2, 1.4)
    for i in range(7 * FPS):
        t = i / FPS
        pos, al = stars_to(pts, n, (t - 1.0) / 3.5, start)
        al = al * (0.6 + 0.4 * np.sin(t * 3 + tw[:, 0] * 20)) if t < 1.0 else al
        img = glow(draw_points(pos, np.clip(al, 0, 1), 2.6 + 1.2 * ease((t - 3) / 2)), 10, 1.8)
        fade = 1 - ease((t - 5.6) / 1.4)                               # dissolve to S02
        p.stdin.write((np.asarray(img, float) * fade).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); return out


def S02_07(plate):
    out, pr = writer("S02-07")
    bg = Image.open(plate).convert("RGB"); w, h = bg.size; ch = int(w * 9 / 16); bg = bg.crop((0, (h - ch) // 3, w, (h - ch) // 3 + ch)).resize((W, H))
    dark = Image.fromarray((np.asarray(bg, float) * 0.45 + np.array(NIGHT) * 0.25).astype(np.uint8))
    n = 900; start = np.c_[rng.uniform(0, W, n), rng.uniform(0, H, n)]
    tif = text_points(NAME_TIFI, TIFI, 300, W / 2, H / 2 - 120, step=10)
    title = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(title)
    d.text((W / 2, H / 2 + 150), "أمامّلن", font=ImageFont.truetype(KUFI, 150), fill=GOLD + (255,), anchor="mm", direction="rtl")
    d.text((W / 2, H / 2 + 310), "حين تصلّبت الحجارة", font=ImageFont.truetype(NASKH, 72), fill=(240, 226, 196, 255), anchor="mm", direction="rtl")
    for i in range(12 * FPS):
        t = i / FPS
        z = 1 + 0.04 * t / 12; bgz = dark.resize((int(W * z), int(H * z))).crop((int(W * (z - 1) / 2), int(H * (z - 1) / 2), int(W * (z - 1) / 2) + W, int(H * (z - 1) / 2) + H))
        bgz = Image.fromarray((np.asarray(bgz, float) * ease(t / 1.5)).astype(np.uint8))
        pos, al = stars_to(tif, n, (t - 0.5) / 4.0, start)
        frame = draw_points(pos, al, 3.2, Image.new("RGB", (W, H)))
        frame = glow(frame, 9, 1.6)
        img = Image.fromarray(np.clip(np.asarray(bgz, float) + np.asarray(frame, float), 0, 255).astype(np.uint8))
        a = ease((t - 5.0) / 2.0)
        if a > 0:
            tl = title.copy(); tl.putalpha(Image.fromarray((np.asarray(title.split()[3], float) * a).astype(np.uint8)))
            img.paste(glow(tl.convert("RGB"), 6, 0.6), (0, 0), tl)
        img = Image.fromarray((np.asarray(img, float) * (1 - ease((t - 11.2) / 0.8))).astype(np.uint8))
        pr.stdin.write(img.tobytes())
    pr.stdin.close(); pr.wait(); return out


def S09_04():
    out, pr = writer("S09-04")
    card = Image.new("RGB", (W, H), NIGHT); d = ImageDraw.Draw(card)
    d.text((W / 2, H / 2 - 90), "نهاية الجزء الأول", font=ImageFont.truetype(KUFI, 110), fill=GOLD, anchor="mm", direction="rtl")
    d.text((W / 2, H / 2 + 80), "يتبع: الحجر الصلب", font=ImageFont.truetype(NASKH, 76), fill=(240, 226, 196), anchor="mm", direction="rtl")
    for x, y in dot_symbols(W / 2, H / 2 + 230, 0.55):
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=GOLD)
    card = glow(card, 6, 0.5)
    for i in range(8 * FPS):
        t = i / FPS; a = ease(t / 1.5) * (1 - ease((t - 6.8) / 1.2))
        pr.stdin.write((np.asarray(card, float) * a).astype(np.uint8).tobytes())
    pr.stdin.close(); pr.wait(); return out


if __name__ == "__main__":
    ids = sys.argv[1:] or ["S01-07", "S02-07", "S09-04"]
    plate = next((ROOT / f"renders/keyframes/S02-07_plate.{e}" for e in ("jpg", "png") if (ROOT / f"renders/keyframes/S02-07_plate.{e}").exists()),
                 ROOT / "assets/refs/key_art.png")
    for sid in ids:
        print(sid, {"S01-07": S01_07, "S02-07": lambda: S02_07(plate), "S09-04": S09_04}[sid]())
