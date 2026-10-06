"""Original synthesized score + ambience/SFX for Part 1 (deterministic, seeded; no external samples, no licensing).
Usage: uv run --with numpy --with scipy --with soundfile python tools/make_score.py --part 1|2   (Part 2 cues: build2())
Writes renders/audio/part1_music.wav and renders/audio/part1_sfx.wav (48 kHz stereo, not committed: regenerate).
Palette (bible/style.md): imzad (one-string bowed fiddle) in D Dorian, drone, tende mortar drum, tehardent-like plucks,
Adelasegh's reed-flute motif, desert wind, fire. The CUES table below is the spotting sheet: edit times there.
Times are absolute seconds on the Part 1 timeline (see validate_shots.py for shot timecodes).
Leitmotifs (keep identical across the film):
  THEME_A  "Amamellen / clarity"   A4 G4 F4 E4 D4 . D4 F4 G4 A4 C5 A4
  DOTS     "the dot game"          D4 F4 A4 A4 . A4 G4 F4 D4   (plucked)
  FLUTE    "Adelasegh"             D5 E5 F5 A5 G5 F5 E5 D5    (reed flute)"""
import argparse
from pathlib import Path
import numpy as np, soundfile as sf
from scipy import signal

SR = 48000
ROOT = Path(__file__).resolve().parents[1]
rng = np.random.default_rng(7)


def m2f(m): return 440.0 * 2 ** ((m - 69) / 12)


def env_adsr(n, a=0.05, r=0.2):
    e = np.ones(n); na, nr = min(int(a * SR), n // 2), min(int(r * SR), n // 2)
    if na: e[:na] = np.linspace(0, 1, na) ** 1.5
    if nr: e[-nr:] *= np.linspace(1, 0, nr) ** 1.5
    return e


def lpnoise(n, cutoff, order=2):
    b, a = signal.butter(order, cutoff / (SR / 2)); return signal.lfilter(b, a, rng.standard_normal(n))


def bp(x, lo, hi, order=2):
    sos = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos"); return signal.sosfilt(sos, x)


def lp(x, fc, order=2):
    sos = signal.butter(order, fc / (SR / 2), output="sos"); return signal.sosfilt(sos, x)


def hp(x, fc, order=2):
    sos = signal.butter(order, fc / (SR / 2), btype="high", output="sos"); return signal.sosfilt(sos, x)


# ---------------- instruments ----------------
def imzad(notes, vib_cents=22, legato=True):
    """notes: [(midi, dur_s), ...] (midi=None -> rest). Bowed one-string fiddle: additive saw + bow noise + body formants."""
    total = sum(d for _, d in notes); n = int(total * SR) + 1
    f = np.zeros(n); amp = np.zeros(n); i = 0; prev = None
    for m, d in notes:
        k = int(d * SR)
        if m is None:
            prev = None; i += k; continue
        tgt = m2f(m); seg = np.full(k, tgt)
        if prev is not None:   # glide from previous note (characteristic imzad slide)
            g = min(int(0.09 * SR), k // 3); seg[:g] = np.exp(np.linspace(np.log(prev), np.log(tgt), g))
        t = np.arange(k) / SR
        depth = np.clip((t - 0.25) / 0.5, 0, 1) * vib_cents           # delayed vibrato
        seg *= 2 ** (depth * np.sin(2 * np.pi * 5.3 * t + rng.uniform(0, 6)) / 1200)
        f[i:i + k] = seg
        e = env_adsr(k, 0.07, 0.12 if legato else 0.25)
        if legato and prev is not None: e = np.maximum(e, 0.55)          # bow keeps contact
        amp[i:i + k] = e * (0.85 + 0.15 * np.sin(np.linspace(0, np.pi, k)))
        prev = tgt; i += k
    amp = lp(amp, 30) * (1 + 0.12 * lpnoise(n, 8) / 0.3)                 # bow pressure jitter
    ph = 2 * np.pi * np.cumsum(f) / SR; out = np.zeros(n)
    fmax = np.max(f) if np.max(f) > 0 else 400
    for h in range(1, int(9000 / fmax) + 1):
        out += np.sin(h * ph) / h ** 1.05
    out *= amp
    out = 0.5 * out + 0.9 * bp(out, 450, 900) + 0.7 * bp(out, 1300, 1900) + 0.4 * bp(out, 2600, 3600)   # gourd body
    out = hp(out, 230) + 0.05 * bp(rng.standard_normal(n), 2500, 7000) * amp                           # bow hair noise
    return out / (np.max(np.abs(out)) + 1e-9)


def pad(midis, dur, bright=900, a=3.0, r=3.0):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for m in midis:
        for det in (-7, 0, 6):
            fr = m2f(m) * 2 ** (det / 1200)
            out += signal.sawtooth(2 * np.pi * fr * t + rng.uniform(0, 6))
    out = lp(out, bright, 4) * (1 + 0.15 * np.sin(2 * np.pi * 0.07 * t))
    return out / (np.max(np.abs(out)) + 1e-9) * env_adsr(n, a, r)


def shimmer(midis, dur):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for m in midis:
        out += np.sin(2 * np.pi * m2f(m) * t) * (0.5 + 0.5 * np.sin(2 * np.pi * rng.uniform(0.05, 0.2) * t + rng.uniform(0, 6)))
    return out / len(midis) * env_adsr(n, 4, 4)


def tende_hit(acc=1.0):
    n = int(0.5 * SR); t = np.arange(n) / SR
    fr = 58 + 90 * np.exp(-t * 28); body = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-t * 9)
    slap = bp(rng.standard_normal(n), 350, 1800) * np.exp(-t * 45)
    return (body + 0.5 * slap * acc) * acc


def clap():
    n = int(0.15 * SR); x = np.zeros(n)
    for o in (0, 0.011, 0.023):
        k = int(o * SR); m = n - k; x[k:] += bp(rng.standard_normal(m), 900, 3500) * np.exp(-np.arange(m) / SR * 60)
    return x * 0.5


def pluck(m, dur=1.2):
    n = int(dur * SR); t = np.arange(n) / SR; f0 = m2f(m); out = np.zeros(n)
    for h in range(1, int(7000 / f0)):
        out += np.sin(2 * np.pi * f0 * h * t) / h * np.exp(-t * (2.5 + 1.8 * h)) * (1 if h % 4 else 0.4)
    out[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return out / (np.max(np.abs(out)) + 1e-9)


def flute(notes):
    total = sum(d for _, d in notes); n = int(total * SR) + 1; f = np.zeros(n); amp = np.zeros(n); i = 0
    for m, d in notes:
        k = int(d * SR)
        if m is not None:
            t = np.arange(k) / SR
            f[i:i + k] = m2f(m) * 2 ** (np.clip(t - 0.2, 0, 1) * 12 * np.sin(2 * np.pi * 5 * t) / 1200)
            amp[i:i + k] = env_adsr(k, 0.04, 0.1)
        i += k
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    breath = bp(rng.standard_normal(n), 1500, 6000) * 0.12
    return (tone + breath) * lp(amp, 40)


# ---------------- ambience / sfx ----------------
def wind(dur, gusty=0.5, bright=1.0):
    n = int(dur * SR); x = rng.standard_normal(n)
    lo, hi = bp(x, 150 * bright, 600 * bright), bp(x, 500 * bright, 2200 * bright)
    lfo = 0.5 + 0.5 * np.clip(lpnoise(n, 0.3) * 3, -1, 1)
    out = lo * (1 - lfo) + hi * lfo * 0.6
    gust = 1 + gusty * np.clip(lpnoise(n, 0.15) * 4, -0.8, 1.5)
    return out * gust / (np.max(np.abs(out * gust)) + 1e-9) * env_adsr(n, 2, 2)


def fire(dur):
    n = int(dur * SR); out = lp(rng.standard_normal(n), 300) * 0.5
    for t0 in np.cumsum(rng.exponential(1 / 9, int(dur * 12))):
        k = int(t0 * SR)
        if k >= n - 2000: break
        L = int(rng.uniform(0.002, 0.012) * SR); out[k:k + L] += bp(rng.standard_normal(L), 1500, 7000) * rng.uniform(0.3, 1.5)
    return out / (np.max(np.abs(out)) + 1e-9) * env_adsr(n, 1.5, 1.5)


def boom(dur=4.0):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * (40 + 30 * np.exp(-t * 3)) * t) * np.exp(-t * 1.2) + 0.6 * lp(rng.standard_normal(n), 120) * np.exp(-t * 1.5))


def crackle(dur):
    n = int(dur * SR); out = np.zeros(n); t = np.linspace(0, 1, n); dens = np.sin(np.pi * t) ** 0.7
    for _ in range(int(dur * 120)):
        k = rng.integers(0, n - 3000)
        if rng.random() > dens[k]: continue
        L = int(rng.uniform(0.001, 0.02) * SR); out[k:k + L] += bp(rng.standard_normal(L), 800, 6000) * rng.uniform(0.2, 1)
    return out / (np.max(np.abs(out)) + 1e-9)


def snap():
    n = int(0.4 * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 1200) * np.exp(-t * 30) + np.sin(2 * np.pi * 180 * t) * np.exp(-t * 25)


def whine(dur):
    n = int(dur * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 3150 * t) + 0.5 * np.sin(2 * np.pi * 3163 * t)) * env_adsr(n, 3, 2) * 0.5


def whispers(dur):
    n = int(dur * SR); x = bp(rng.standard_normal(n), 1800, 6500)
    syl = np.clip(lpnoise(n, 6) * 5, 0, 1) ** 2
    return x * syl * env_adsr(n, 2, 2) / (np.max(np.abs(x * syl)) + 1e-9)


def rumble(dur):
    n = int(dur * SR); return lp(rng.standard_normal(n), 90, 4) * env_adsr(n, dur / 2, 1) * 8


def heartbeat(t0, t1, bpm0, bpm1):
    ev, t = [], t0
    while t < t1:
        ev.append(t); bpm = bpm0 + (bpm1 - bpm0) * (t - t0) / (t1 - t0); t += 60 / bpm
    return ev


# ---------------- themes ----------------
THEME_A = [(69, 1.6), (67, 0.7), (65, 0.7), (64, 0.9), (62, 2.2), (None, 0.6), (62, 0.6), (65, 0.6), (67, 0.7), (69, 1.0), (72, 0.8), (69, 2.4)]
THEME_A_MIN = [(69, 1.8), (67, 0.9), (65, 0.9), (64, 1.2), (62, 2.8), (None, 0.8), (65, 1.0), (64, 1.0), (62, 3.0)]
DOTS = [(62, .45), (65, .45), (69, .45), (69, .9), (69, .45), (67, .45), (65, .45), (62, .9)]
FLUTE = [(74, .3), (76, .3), (77, .3), (81, .6), (79, .3), (77, .3), (76, .3), (74, .9)]
PHRASES = [  # sparse improvisation material (D Dorian, narrow range like real imzad playing)
    [(62, 2.5), (64, 0.6), (62, 1.8)],
    [(65, 1.2), (64, 0.5), (62, 0.5), (60, 0.6), (62, 2.2)],
    [(69, 1.5), (67, 0.6), (65, 1.6)],
    [(62, 0.8), (65, 0.8), (64, 0.6), (62, 2.4)],
    [(67, 1.0), (69, 1.8), (67, 0.5), (65, 0.5), (64, 1.6)],
]


class Bus:
    def __init__(self, dur): self.L = np.zeros(int(dur * SR) + SR); self.R = np.zeros_like(self.L)

    def add(self, t0, x, gain=1.0, pan=0.0):
        k = int(t0 * SR); x = np.asarray(x) * gain; m = min(len(x), len(self.L) - k)
        if m <= 0: return
        self.L[k:k + m] += x[:m] * np.sqrt((1 - pan) / 2) * 1.414; self.R[k:k + m] += x[:m] * np.sqrt((1 + pan) / 2) * 1.414


def reverb(L, R, secs=2.8, wet=0.3):
    n = int(secs * SR); t = np.arange(n) / SR; envl = np.exp(-t * 6.9 / secs)
    irl, irr = lp(rng.standard_normal(n), 6000) * envl, lp(rng.standard_normal(n), 6000) * envl
    irl[: int(0.02 * SR)] = 0; irr[: int(0.027 * SR)] = 0
    wl, wr = signal.fftconvolve(L, irl)[: len(L)], signal.fftconvolve(R, irr)[: len(R)]
    s = np.max(np.abs(wl)) / (np.max(np.abs(L)) + 1e-9) + 1e-9
    return L + wet * wl / s, R + wet * wr / s


def sparse_imzad(bus, t0, t1, gain, seed=0):
    r = np.random.default_rng(seed); t = t0
    while t < t1 - 3:
        ph = PHRASES[r.integers(len(PHRASES))]; x = imzad(ph)
        if t + len(x) / SR > t1: break
        bus.add(t, x, gain, r.uniform(-0.3, 0.3)); t += len(x) / SR + r.uniform(1.5, 4.0)


def tende(bus, t0, t1, bpm, gain, claps=False, accel_to=None):
    pattern = [1.0, 0, 0, 0.6, 0, 0.8, 1.0, 0, 0, 0.6, 0, 0.5]   # 12/8 tende feel
    t, i = t0, 0
    while t < t1:
        b = bpm if accel_to is None else bpm + (accel_to - bpm) * (t - t0) / (t1 - t0)
        a = pattern[i % 12]
        if a: bus.add(t, tende_hit(a), gain * a, -0.15)
        if claps and i % 3 == 0: bus.add(t + 0.005, clap(), gain * 0.35, 0.3)
        t += 60 / b / 3; i += 1


def build(dur=600.0):
    M, X = Bus(dur), Bus(dur)   # music, sfx
    D2, A2, D3, F3, A3, E4, A4, D5 = 38, 45, 50, 53, 57, 64, 69, 74
    # S01 frame (0-50)
    X.add(0, wind(50, 0.4), 0.22); X.add(8, fire(36), 0.35, -0.2)
    M.add(1.0, imzad([(62, 6.5)]), 0.30)
    M.add(14, pad([D2, A2], 30, 500, 4, 4), 0.12); sparse_imzad(M, 16, 34, 0.18, 1)
    M.add(35, imzad(THEME_A[:5]), 0.30); M.add(34, pad([D3, A3, E4], 18, 1400, 3, 5), 0.16)
    M.add(43, shimmer([A4, D5, 76, 81], 10), 0.10)
    # S02 mythic (50-98) + title (98-110)
    M.add(48, pad([D3, A3, E4, A4], 52, 1800, 5, 6), 0.14); M.add(50, shimmer([D5, 76, 81, 86], 48), 0.08)
    for t in np.arange(58.5, 66, 1.7): X.add(t, boom(2.5), 0.28)
    sparse_imzad(M, 66, 88, 0.14, 2)
    X.add(89, wind(10, 0.2, 1.4), 0.12)
    M.add(98, tende_hit(1.2), 0.9); X.add(98, boom(4), 0.35)
    M.add(98.3, imzad(THEME_A), 0.38); M.add(98, pad([D2, A2, D3], 13, 800, 0.5, 3), 0.18)
    # S03 camp day (110-180)
    X.add(110, wind(70, 0.3), 0.08)
    tende(M, 110, 150, 96, 0.22)
    for t in np.arange(126, 132, 60 / 96 / 3 * 3): M.add(t, clap(), 0.25, 0.3)
    M.add(110, pad([D2, A2], 40, 600, 3, 3), 0.10)
    M.add(150, imzad(THEME_A), 0.26); M.add(150, pad([D3, F3, A3], 9, 900, 2, 3), 0.12)
    M.add(158, pad([D2, 39], 22, 400, 3, 2), 0.14); M.add(158, shimmer([75, 81], 22), 0.06)
    X.add(172, wind(6, 1.5, 1.2), 0.30)
    # S04 childhood (180-250)
    M.add(180, imzad([(69, 2.0), (72, 1.2), (74, 3.0)]), 0.28); M.add(180, pad([D3, A3, 66], 8, 1600, 1, 3), 0.14)
    t = 187
    for rep in range(9):
        for m, d in DOTS:
            M.add(t, pluck(m, 1.4), 0.17, -0.25 + 0.05 * (rep % 3)); t += d
        t += 0.4
    M.add(187, pad([D2, A2, D3], 43, 700, 3, 3), 0.09)
    M.add(230, pad([D2, 39, A2], 9, 450, 1, 2), 0.20)              # D + Eb: the cold look
    X.add(238, wind(4, 1.2, 1.3), 0.30)
    M.add(240.5, flute(FLUTE), 0.20, 0.25); M.add(244.5, flute(FLUTE[:4] + [(74, 1.2)]), 0.18, 0.25)
    # S05 the well (250-330)
    M.add(250, pad([D2, A2], 20, 500, 2, 3), 0.12); sparse_imzad(M, 252, 268, 0.12, 3)
    X.add(270, whine(15), 0.05)
    M.add(285, shimmer([86, 87, 93, 94], 30), 0.10); X.add(285, whispers(22), 0.12, 0.3); X.add(287, whispers(20), 0.10, -0.4)
    M.add(285, pad([D2, 39], 30, 350, 4, 3), 0.12)
    tende(M, 315, 322, 104, 0.20); M.add(315, imzad(THEME_A[6:]), 0.22)
    M.add(323, pad([D2, 39], 8, 400, 1, 2), 0.18)
    # S06 thirst (330-410)
    for t in heartbeat(330, 344, 50, 54): M.add(t, tende_hit(0.6), 0.25)
    X.add(344, wind(22, 0.5, 0.8), 0.18); M.add(344, pad([D2, A2], 21, 380, 3, 3), 0.10); sparse_imzad(M, 348, 364, 0.12, 4)
    X.add(365, wind(15, 0.2, 0.6), 0.14); M.add(365, shimmer([74, 81, 86], 15), 0.07)
    t = 380
    for m, d in DOTS[:4]: M.add(t, pluck(m, 1.4), 0.16); t += d * 1.3
    tende(M, 388, 396, 108, 0.24, claps=False); M.add(388, flute(FLUTE), 0.18, 0.25)
    M.add(396, pad([D2, A2], 14, 400, 1, 3), 0.10)
    # S07 Assekrem (410-500)
    X.add(410, wind(27, 1.0, 1.5), 0.25)
    for t in heartbeat(418, 431, 60, 96): M.add(t, tende_hit(0.7), 0.25)
    M.add(418, pad([D2, 39], 13, 500, 3, 0.3), 0.14)
    X.add(431, snap(), 0.6, 0.1)
    M.add(443, pad([D2, A2, D3], 22, 450, 4, 3), 0.12); sparse_imzad(M, 446, 462, 0.14, 5)
    for t in heartbeat(465, 480, 70, 84): M.add(t, tende_hit(0.5), 0.18)
    M.add(465, pad([D3, 51, A3], 15, 900, 3, 2), 0.12)
    M.add(480.5, imzad(THEME_A_MIN), 0.30); M.add(480, pad([D3, F3, A3], 20, 900, 3, 4), 0.14)
    # S08 reconciliation & hardening (500-570)
    M.add(500, pad([D3, A3, E4], 25, 1100, 5, 4), 0.12); M.add(500, shimmer([A4, D5, 76], 25), 0.06)
    M.add(525, imzad(THEME_A), 0.38); M.add(524, pad([D2, A2, D3, F3, A3], 19, 1500, 3, 4), 0.20); tende(M, 525, 541, 80, 0.16)
    X.add(542, boom(6), 0.55); X.add(542, crackle(9), 0.35); M.add(542, shimmer([62, 69, 74], 10), 0.12)
    M.add(552, imzad(THEME_A[6:]), 0.28); M.add(552, pad([D3, A3, 66], 18, 1200, 3, 5), 0.14)
    # S09 dust on the horizon (570-600)
    tende(M, 570, 586, 70, 0.26, accel_to=120); X.add(578, rumble(8), 0.4); M.add(570, pad([D2, 39], 16, 400, 3, 0.2), 0.16)
    M.add(586.5, tende_hit(1.3), 0.9); X.add(586.5, boom(5), 0.4)
    M.add(592, imzad(THEME_A[:5]), 0.30); M.add(592, pad([D2, A2, D3], 8, 700, 1, 3), 0.14)
    return M, X


# ---------------- Part 2 extras ----------------
def chisel():
    """Iron chisel on stone: bright click + short metallic ring."""
    n = int(0.35 * SR); t = np.arange(n) / SR
    click = hp(rng.standard_normal(n), 2500) * np.exp(-t * 90)
    ring = sum(np.sin(2 * np.pi * f * t) * np.exp(-t * d) for f, d in ((2950, 18), (4410, 26), (6120, 34))) * 0.25
    return (click + ring) * 0.8


def rain(dur):
    n = int(dur * SR); x = hp(lpnoise(n, 7000), 900) * 0.5
    drops = np.zeros(n); k = rng.integers(0, n, int(dur * 40)); drops[k] = rng.uniform(0.3, 1, len(k))
    drops = signal.lfilter([1], [1, -0.97], drops) * 0.15
    return (x + drops) * env_adsr(n, 1.5, 1.5)


def build2(dur=720.0):
    """Part 2 spotting sheet. Times are seconds on the Part 2 timeline (0 = 10:00 of the film)."""
    M, X = Bus(dur), Bus(dur)
    D2, A2, D3, F3, A3, E4, A4, D5 = 38, 45, 50, 53, 57, 64, 69, 74
    # S10 raid (0-80): calm night -> war drums -> ashes at dawn
    X.add(0, wind(12, 0.3), 0.18); M.add(0, pad([D2, A2], 9, 450, 3, 2), 0.12)
    M.add(7.5, tende_hit(1.3), 0.8); X.add(8, boom(3), 0.3)
    tende(M, 8, 53, 132, 0.30, claps=False, accel_to=150)
    M.add(8, pad([D2, 39, A2], 45, 600, 1, 3), 0.16)
    for t in (12.2, 13.0, 21.3, 37.4, 42.2): X.add(t, boom(1.5), 0.25)
    for t in (17.2, 26.2, 47): X.add(t, fire(5), 0.4, 0.2)
    X.add(42.3, snap(), 0.4)
    X.add(53, fire(13), 0.35); X.add(53, rumble(6), 0.3)
    M.add(59, pad([D2, 39], 21, 380, 3, 4), 0.14); X.add(59, wind(21, 0.6), 0.22)
    M.add(66.5, imzad(THEME_A_MIN[:5]), 0.26)
    # S11 no trace (80-150)
    X.add(80, wind(23, 0.4, 0.8), 0.2); M.add(80, pad([D2, A2], 22, 420, 3, 3), 0.10); sparse_imzad(M, 82, 100, 0.12, 21)
    X.add(103, wind(14, 1.6, 1.6), 0.45); X.add(103, rumble(12), 0.25); M.add(103, pad([D2, 39], 14, 350, 2, 3), 0.12)
    M.add(117.3, imzad(PHRASES[0] + PHRASES[3] + PHRASES[1]), 0.34, -0.1)    # Tanfust's imzad solo
    M.add(117, pad([D3, A3], 18, 700, 3, 3), 0.08)
    M.add(135, pad([D2, A2, D3], 15, 600, 2, 3), 0.12); M.add(142.5, imzad(THEME_A[:5]), 0.26)
    # S12 last giant (150-270)
    tende(M, 150, 174, 84, 0.16); M.add(150, flute(FLUTE), 0.12, 0.3); M.add(150, pad([D2, A2, D3], 24, 900, 3, 3), 0.10)
    X.add(150, wind(31, 0.3), 0.12); M.add(174, shimmer([A4, D5], 7), 0.06)
    M.add(181, pad([26, 33, D2], 65, 300, 5, 4), 0.20)                # cave: sub drone
    X.add(203, rumble(7), 0.45); X.add(203, crackle(4), 0.2)
    M.add(210, shimmer([62, 69, 74], 26), 0.05)
    M.add(246, pad([D3, A3, E4, A4], 24, 1600, 4, 5), 0.16); M.add(246, shimmer([A4, D5, 76, 81], 24), 0.08)
    X.add(254, crackle(9), 0.35); X.add(254, boom(5), 0.3)
    M.add(256, imzad(THEME_A), 0.32)
    # S13 riddle duel & escape (270-360)
    X.add(270, fire(67), 0.3, 0.2); M.add(270, pad([D2, 39], 29, 400, 3, 2), 0.12)
    t = 299
    for m, d in DOTS: M.add(t, pluck(m, 1.4), 0.12); t += d * 1.5        # riddle game: dots motif, playful
    for t0 in (312.5, 325.5): M.add(t0, tende_hit(0.9), 0.4)
    M.add(331, pad([D2, A2], 6, 500, 1, 1), 0.12)
    tende(M, 337, 350, 150, 0.30, accel_to=168); M.add(337, flute(FLUTE), 0.18, 0.3); M.add(343, flute(FLUTE), 0.16, 0.3)
    X.add(344, wind(6, 1.0, 1.4), 0.2)
    M.add(350, pad([D2, A2, D3], 10, 500, 2, 3), 0.14); X.add(350, wind(10, 0.3), 0.18)
    # S14 invention of letters (360-450): full imzad montage
    for t in np.arange(360.5, 366.5, 0.62): X.add(t, chisel(), 0.45, 0.1)
    X.add(367.3, lp(rng.standard_normal(int(2.5 * SR)), 3000) * env_adsr(int(2.5 * SR), 0.01, 2.0), 0.25)
    M.add(373, pad([D2, A2, D3], 15, 700, 3, 2), 0.10)
    t = 381
    for m, d in DOTS: M.add(t, pluck(m, 1.4), 0.16); t += d
    M.add(388, shimmer([A4, D5, 76], 8), 0.08)
    M.add(396, imzad(THEME_A + [(None, 0.8)] + THEME_A_MIN), 0.34); M.add(396, pad([D2, A2, D3, F3, A3], 41, 1300, 4, 4), 0.16)
    tende(M, 396, 437, 88, 0.18)
    for t in list(np.arange(397, 403, 0.8)) + list(np.arange(405, 410, 0.9)) + list(np.arange(412, 417, 1.0)) + list(np.arange(419, 424, 1.1)) + [432.5]:
        X.add(t, chisel(), 0.32, 0.15)
    X.add(425, rain(7), 0.35)
    M.add(437, imzad(THEME_A[6:]), 0.26); M.add(437, pad([D3, A3, E4], 13, 1000, 3, 4), 0.12)
    # S15 reading the signs (450-540)
    X.add(450, wind(14, 0.5), 0.2); M.add(450, pad([D2, 39], 14, 380, 3, 2), 0.10)
    M.add(464, shimmer([A4, D5, 76, 81], 7), 0.10)
    t = 464.3
    for m, d in DOTS: M.add(t, pluck(m, 1.4), 0.2); t += d          # DOTS sting on the sign
    M.add(471, tende_hit(1.0), 0.5); M.add(478, pad([D3, A3, 66], 8, 1400, 1, 3), 0.12)
    tende(M, 486, 501, 104, 0.18, claps=True); M.add(494, flute(FLUTE), 0.18, 0.3)
    M.add(501, pad([D2, 39, A2], 8, 450, 1, 2), 0.16)
    t = 508.5
    for m, d in DOTS[:4]: M.add(t, pluck(m, 1.2), 0.15); t += d * 1.4
    tende(M, 516, 523, 120, 0.22); X.add(518, boom(2.5), 0.25)
    M.add(523, flute(FLUTE), 0.2, 0.3); M.add(531, flute(FLUTE[:4] + [(74, 1.5)]), 0.18, 0.3); M.add(523, pad([D3, A3, E4], 17, 1300, 2, 4), 0.12)
    # S16 last rock (540-630): gold returns
    X.add(540, wind(23, 0.3), 0.14); M.add(540, pad([D2, A2], 23, 500, 4, 3), 0.10); sparse_imzad(M, 542, 562, 0.12, 16)
    M.add(563, pad([D3, F3, A3], 18, 900, 3, 3), 0.12)
    M.add(589.5, pad([D2, A2, D3, F3, A3], 40, 1500, 4, 6), 0.18)
    M.add(598, imzad(THEME_A), 0.40); tende(M, 598, 621, 80, 0.15)
    M.add(613, shimmer([A4, D5, 76], 17), 0.07)
    M.add(621, imzad(THEME_A[6:]), 0.30)
    # S17 words remain (630-690)
    t = 630.5
    for rep in range(3):
        for m, d in DOTS: M.add(t, pluck(m, 1.4), 0.12, 0.2); t += d
        t += 0.5
    M.add(639, imzad(PHRASES[2] + PHRASES[4]), 0.30); M.add(630, pad([D3, A3, E4], 34, 1300, 3, 4), 0.12)
    for t in np.arange(647.5, 653, 0.9): X.add(t, chisel(), 0.25)
    M.add(664, imzad(THEME_A), 0.36); M.add(664, pad([D2, A2, D3, F3, A3], 18, 1600, 3, 5), 0.18); M.add(664, shimmer([A4, D5, 76, 81], 18), 0.08)
    X.add(672, wind(18, 0.4, 0.8), 0.15); M.add(682, pad([D2, A2], 10, 500, 3, 3), 0.12)
    # S18 epilogue (690-720)
    X.add(690, fire(21), 0.35, -0.2); X.add(690, wind(30, 0.3), 0.12)
    t = 698.6
    for m, d in DOTS: M.add(t, pluck(m, 1.4), 0.12); t += d * 1.2
    M.add(705, shimmer([A4, D5, 76, 81], 15), 0.09)
    M.add(711, tende_hit(1.2), 0.7); M.add(711.3, imzad(THEME_A), 0.38); M.add(711, pad([D2, A2, D3], 9, 900, 1, 4), 0.18)
    return M, X


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--part", type=int, default=1); a = ap.parse_args()
    length = {1: 600, 2: 720}[a.part]
    M, X = build() if a.part == 1 else build2()
    out = ROOT / "renders/audio"; out.mkdir(parents=True, exist_ok=True)
    for name, bus, wet in (("music", M, 0.35), ("sfx", X, 0.12)):
        L, R = reverb(bus.L, bus.R, 3.2 if name == "music" else 1.2, wet)
        peak = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
        sf.write(out / f"part{a.part}_{name}.wav", np.stack([L, R], 1)[: int(length * SR)] / peak * 0.89, SR, subtype="PCM_24")
        print("wrote", name, "peak_raw", round(peak, 2))


if __name__ == "__main__":
    main()
