"""Graphics shots (method HF) rendered with Pillow + ffmpeg -> renders/clips/<ID>.mp4 (1920x1080, 24 fps).
Usage: uv run --with pillow --with numpy python tools/make_hf.py [S01-07 S02-07 S09-04 S14-06 S15-03 S18-04]
Part 2 HF shots S14-06 / S15-03 composite carved symbols on plates renders/keyframes/<ID>_plate.jpg (generate the plate first).
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


# ---------------- Part 2 ----------------
def symbol_mask(cx, cy, s=1.0, parts=("dots", "circle", "line"), width=12):
    """Solid mask of the canonical dot-game symbols, same geometry as dot_symbols(): carve-able shapes."""
    m = Image.new("L", (W, H)); d = ImageDraw.Draw(m); w = int(width * s)
    if "dots" in parts:
        for x, y in ((cx - 330 * s, cy - 18 * s), (cx - 270 * s, cy + 18 * s)):
            r = 17 * s; d.ellipse([x - r, y - r, x + r, y + r], fill=255)
    if "circle" in parts:
        r = 60 * s; d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=255, width=w)
    if "line" in parts:
        d.line([(cx + 200 * s, cy), (cx + 380 * s, cy)], fill=255, width=w)
    return m


def plate_img(path, dim=1.0):
    bg = Image.open(path).convert("RGB"); w, h = bg.size; ch = int(w * 9 / 16)
    bg = bg.crop((0, int((h - ch) * 0.3), w, int((h - ch) * 0.3) + ch)).resize((W, H))
    return Image.fromarray((np.asarray(bg, float) * dim).astype(np.uint8)) if dim != 1.0 else bg


def carve(bg, mask, depth=1.0, glow_amt=0.0):
    """Composite a pecked/carved groove (shadow up-left, pale floor, light rim down-right) + optional gold glow."""
    a = np.asarray(bg, float); m = np.asarray(mask, float)[..., None] / 255 * depth
    sh = np.asarray(mask.transform(mask.size, Image.AFFINE, (1, 0, 3, 0, 1, 3)).filter(ImageFilter.GaussianBlur(2)), float)[..., None] / 255 * depth
    rim = np.asarray(mask.transform(mask.size, Image.AFFINE, (1, 0, -3, 0, 1, -3)).filter(ImageFilter.GaussianBlur(2)), float)[..., None] / 255 * depth
    pale = np.array([214, 196, 160]); noise = rng.normal(0, 14, a.shape[:2])[..., None]
    out = a * (1 - 0.55 * sh) + rim * 30
    out = out * (1 - m) + (pale + noise) * m * 0.85 + out * m * 0.15
    if glow_amt > 0:
        g = np.asarray(mask.filter(ImageFilter.GaussianBlur(14)), float)[..., None] / 255
        out = out + glow_amt * (np.array(GOLD) * g * 1.4 + np.array(GOLD) * m * 0.9)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def push(img, t, T, amt=0.06):
    z = 1 + amt * t / T; w, h = int(W * z), int(H * z); x, y = (w - W) // 2, (h - H) // 2
    return img.resize((w, h)).crop((x, y, x + W, y + H))


def S14_06(plate):
    """Carving montage beat: symbols appear one by one, glow gold, then a short row of tifinagh letters."""
    out, pr = writer("S14-06"); bg = plate_img(plate, 0.92); T = 8.0
    cx, cy, s = W / 2, H / 2 - 60, 1.25
    seq = [("dots",), ("dots", "circle"), ("dots", "circle", "line")]
    row = Image.new("L", (W, H)); ImageDraw.Draw(row).text((W / 2, H / 2 + 190), "ⵣ ⵎ ⵏ ⵜ ⵍ", font=ImageFont.truetype(TIFI, 120), fill=255, anchor="mm")
    for i in range(int(T * FPS)):
        t = i / FPS; k = min(2, int(t / 1.4)); pr_ = ease((t - k * 1.4) / 0.6)
        prev = symbol_mask(cx, cy, s, seq[k - 1]) if k else Image.new("L", (W, H))
        cur = symbol_mask(cx, cy, s, seq[k]); m = Image.fromarray(np.maximum(np.asarray(prev), (np.asarray(cur, float) * pr_).astype(np.uint8)))
        if t > 4.6: m = Image.fromarray(np.maximum(np.asarray(m), (np.asarray(row, float) * ease((t - 4.6) / 1.2)).astype(np.uint8)))
        g = 0.35 + 0.45 * ease((t - 3.8) / 1.5) * (1 - 0.3 * np.sin(t * 5) ** 2)
        img = carve(bg, m, 1.0, g)
        img = Image.fromarray((np.asarray(push(img, t, T), float) * ease(t / 0.5) * (1 - ease((t - 7.4) / 0.6))).astype(np.uint8))
        pr.stdin.write(img.tobytes())
    pr.stdin.close(); pr.wait(); return out


def S15_03(plate):
    """The first sign Tafukt finds: same symbols, already carved and weathered; a faint gold glint sweeps across."""
    out, pr = writer("S15-03"); bg = plate_img(plate, 0.95); T = 7.0
    m = symbol_mask(W / 2, H / 2 - 20, 1.35); base = carve(bg, m, 0.9, 0.0)
    gm = np.asarray(m.filter(ImageFilter.GaussianBlur(10)), float) / 255
    xs = np.arange(W)[None, :]
    for i in range(int(T * FPS)):
        t = i / FPS; sweep = np.exp(-((xs - (-300 + (W + 600) * ease((t - 1.5) / 3.5))) / 160.0) ** 2)
        a = np.asarray(base, float) + (gm * sweep)[..., None] * np.array(GOLD) * 0.9
        img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        img = Image.fromarray((np.asarray(push(img, t, T, 0.08), float) * ease(t / 0.4) * (1 - ease((t - 6.5) / 0.5))).astype(np.uint8))
        pr.stdin.write(img.tobytes())
    pr.stdin.close(); pr.wait(); return out


def S18_04(plate):
    """Epilogue: stars -> dot symbols -> tifinagh name, Arabic title, short end credit (mirror of S01-07 + S02-07)."""
    out, pr = writer("S18-04"); T = 9.0
    n = 900; start = np.c_[rng.uniform(0, W, n), rng.uniform(0, H * 0.75, n)]
    sym = dot_symbols(W / 2, H / 2 - 40, 1.4); tif = text_points(NAME_TIFI, TIFI, 260, W / 2, H / 2 - 170, step=10)
    title = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(title)
    d.text((W / 2, H / 2 + 110), "أمامّلن", font=ImageFont.truetype(KUFI, 130), fill=GOLD + (255,), anchor="mm", direction="rtl")
    d.text((W / 2, H / 2 + 250), "حين تصلّبت الحجارة", font=ImageFont.truetype(NASKH, 64), fill=(240, 226, 196, 255), anchor="mm", direction="rtl")
    cred = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(cred)
    d.text((W / 2, H - 120), "مستوحى من أسطورة أمامّلن وأدلاسغ، من تراث الطوارق في الهقار وطاسيلي ناجر", font=ImageFont.truetype(NASKH, 38), fill=(220, 205, 175, 255), anchor="mm", direction="rtl")
    bg = plate_img(plate, 0.35) if plate and Path(plate).exists() else Image.new("RGB", (W, H), NIGHT)
    for i in range(int(T * FPS)):
        t = i / FPS
        if t < 3.0: pos, al = stars_to(sym, n, (t - 0.4) / 2.2, start)
        else:
            s0 = np.array(sym + [tuple(start[j]) for j in range(len(sym), n)], float); pos, al = stars_to(tif, n, (t - 3.0) / 1.8, s0)
            al = np.clip(al, 0, 1); al[len(tif):] = 0
        frame = glow(draw_points(pos, np.clip(al, 0, 1), 3.0, Image.new("RGB", (W, H))), 9, 1.6)
        b = np.asarray(bg, float) * ease((t - 4.0) / 1.5)
        img = Image.fromarray(np.clip(b + np.asarray(frame, float), 0, 255).astype(np.uint8))
        for layer, t0 in ((title, 4.8), (cred, 6.4)):
            a = ease((t - t0) / 1.0)
            if a > 0:
                tl = layer.copy(); tl.putalpha(Image.fromarray((np.asarray(layer.split()[3], float) * a).astype(np.uint8)))
                img.paste(glow(tl.convert("RGB"), 6, 0.5) if layer is title else tl.convert("RGB"), (0, 0), tl)
        img = Image.fromarray((np.asarray(img, float) * (1 - ease((t - 8.2) / 0.8))).astype(np.uint8))
        pr.stdin.write(img.tobytes())
    pr.stdin.close(); pr.wait(); return out


if __name__ == "__main__":
    ids = sys.argv[1:] or ["S01-07", "S02-07", "S09-04"]
    plate = next((ROOT / f"renders/keyframes/S02-07_plate.{e}" for e in ("jpg", "png") if (ROOT / f"renders/keyframes/S02-07_plate.{e}").exists()),
                 ROOT / "assets/refs/key_art.png")
    pl = lambda sid: ROOT / f"renders/keyframes/{sid}_plate.jpg"
    for sid in ids:
        print(sid, {"S01-07": S01_07, "S02-07": lambda: S02_07(plate), "S09-04": S09_04,
                    "S14-06": lambda: S14_06(pl("S14-06")), "S15-03": lambda: S15_03(pl("S15-03")),
                    "S18-04": lambda: S18_04(plate)}[sid]())
