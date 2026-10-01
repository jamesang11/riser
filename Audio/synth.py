#!/usr/bin/env python3
"""
Riser sound generator.

Every sound in Riser/Resources/Sounds is synthesized here from scratch:
additive instruments (kalimba, marimba, glockenspiel, bells, music box),
spectrally shaped noise (wind, rain) and procedural animals (birds, crickets).
All melodies are original. Seeds are fixed, so a run is fully reproducible.

Usage:
    python3 Audio/synth.py            # regenerate everything
    python3 Audio/synth.py sfx_coin   # regenerate only the named file(s)

Requires numpy, scipy, soundfile. Converts to CAF with macOS `afconvert`.

Loops (alarms, ambiences, music) are rendered *circularly*: note tails, reverb
tails and noise beds wrap around the loop point (noise is shaped in the FFT
domain over exactly the loop length), so the end flows sample-continuously
into the start with no crossfade seam.
"""
import os
import sys
import subprocess
import tempfile

import numpy as np
from scipy import signal
from scipy.ndimage import maximum_filter1d
import soundfile as sf

SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.normpath(os.path.join(HERE, "..", "Riser", "Resources", "Sounds"))

RNG = np.random.default_rng(2026)  # instrument micro-randomness (phases, clicks)
REPORT = []

# --------------------------------------------------------------------------
# Pitch helpers
# --------------------------------------------------------------------------
_NOTE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(n):
    if isinstance(n, (int, float, np.integer, np.floating)):
        return float(n)
    v = _NOTE[n[0]]
    i = 1
    while i < len(n) and n[i] in "#b":
        v += 1 if n[i] == "#" else -1
        i += 1
    return float(v + 12 * (int(n[i:]) + 1))


def hz(n):
    return 440.0 * 2 ** ((midi(n) - 69) / 12)


# --------------------------------------------------------------------------
# DSP helpers
# --------------------------------------------------------------------------
def tvec(n):
    return np.arange(n) / SR


def fade(y, fin=0.002, fout=0.012):
    y = y.copy()
    a, b = int(fin * SR), int(fout * SR)
    if a > 0:
        y[:a] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    if b > 0 and b < len(y):
        y[-b:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(b) / b)
    return y


def bump(n, peak=0.3):
    """Smooth 0→1→0 envelope with its maximum at `peak` (0..1)."""
    x = (np.arange(n) + 0.5) / n
    p = np.log(0.5) / np.log(peak)
    return np.sin(np.pi * x ** p) ** 2


def sos_filter(x, kind, fc, order=2):
    sos = signal.butter(order, fc, btype=kind, fs=SR, output="sos")
    return signal.sosfilt(sos, x)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-20))


def db(v):
    return 20 * np.log10(max(v, 1e-12))


# Frequency-domain magnitude shapes (for periodic / circular filtering)
def lp_mag(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (f / fc) ** (2 * order))


def hp_mag(fc, order=2):
    return lambda f: 1 / np.sqrt(1 + (fc / np.maximum(f, 1e-3)) ** (2 * order))


def pink_mag(f):
    return 1 / np.sqrt(np.maximum(f, 15.0))


def brown_mag(f):
    return 1 / np.maximum(f, 15.0)


def mags(*fns):
    return lambda f: np.prod([fn(f) for fn in fns], axis=0)


def fft_filter(x, mag):
    """Circular (zero-phase) filtering: keeps loops perfectly periodic."""
    n = len(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    return np.fft.irfft(np.fft.rfft(x) * mag(f), n)


def shaped_noise(n, rng, mag):
    """Periodic noise of length n with the given magnitude spectrum, unit RMS."""
    y = fft_filter(rng.standard_normal(n), mag)
    return y / rms(y)


def periodic_lfo(n, rng, max_hz):
    """Smooth random control signal in [-1, 1] that loops over n samples."""
    k = max(1, int(max_hz * n / SR))
    spec = np.zeros(n // 2 + 1, complex)
    w = 1 / np.sqrt(np.arange(1, k + 1))
    spec[1:k + 1] = (rng.standard_normal(k) + 1j * rng.standard_normal(k)) * w
    y = np.fft.irfft(spec, n)
    return y / np.max(np.abs(y))


def pf(f, n):
    """Snap a frequency so it completes an integer number of cycles in n samples."""
    L = n / SR
    return max(1, round(f * L)) / L


# --------------------------------------------------------------------------
# Reverb: convolution with a synthesized, exponentially decaying noise IR
# --------------------------------------------------------------------------
def make_ir(rt60=1.2, predelay=0.012, bright=6000, dark=1600, seed=7):
    r = np.random.default_rng(seed)
    n = int(rt60 * 1.15 * SR)
    t = tvec(n)
    nz = r.standard_normal(n)
    b1 = sos_filter(nz, "lowpass", bright)
    b2 = sos_filter(nz, "lowpass", dark)
    mix = np.exp(-t / (rt60 * 0.22))  # high frequencies die first
    ir = (b1 * mix + b2 * (1 - mix)) * np.exp(-6.91 * t / rt60)
    ir = fade(ir, 0.004, 0.05)
    # a handful of soft early reflections
    er = np.zeros(int(0.08 * SR))
    for d, g in [(0.011, 0.5), (0.019, -0.35), (0.027, 0.3), (0.041, -0.22), (0.057, 0.16)]:
        er[int(d * SR)] += g
    ir[: len(er)] += er * np.max(np.abs(ir)) * 0.6
    ir = np.concatenate([np.zeros(int(predelay * SR)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


def reverb(x, ir, wet=0.2, circular=False, hp=180):
    if circular:
        n = len(x)
        y = np.fft.irfft(np.fft.rfft(x) * np.fft.rfft(ir, n), n)
        y = fft_filter(y, hp_mag(hp, 1))
    else:
        y = signal.fftconvolve(x, ir)[: len(x)]
        y = sos_filter(y, "highpass", hp, 1)
    return x + wet * y


# --------------------------------------------------------------------------
# Instruments (all additive, per-partial exponential decays)
# --------------------------------------------------------------------------
def additive(f, dur, partials, attack=0.003):
    n = int(dur * SR)
    t = tvec(n)
    y = np.zeros(n)
    for ratio, amp, dec in partials:
        fr = f * ratio
        if amp == 0 or fr >= 0.45 * SR:
            continue
        ph = RNG.uniform(0, 2 * np.pi)
        y += amp * np.sin(2 * np.pi * fr * t + ph) * np.exp(-t / dec)
    return fade(y, attack, 0.015)


def click(dur, center, amp):
    """Tiny band-limited noise transient (mallet / thumb / strike)."""
    n = max(8, int(dur * SR))
    nz = RNG.standard_normal(n) * np.exp(-tvec(n) / (dur / 4))
    lo, hi = center / 1.8, min(center * 1.8, 0.45 * SR)
    nz = signal.sosfilt(signal.butter(2, [lo, hi], btype="band", fs=SR, output="sos"), nz)
    return fade(nz / (np.max(np.abs(nz)) + 1e-9) * amp, 0.0005, 0.001)


def mix_in(y, z):
    k = min(len(y), len(z))
    y = y.copy()
    y[:k] += z[:k]
    return y


def kalimba(f, vel=1.0):
    f = hz(f) if isinstance(f, str) else f
    d = 1.5 * (523.0 / f) ** 0.4
    b = 0.55 + 0.45 * vel
    parts = [(1, 1.0, d), (2.0, 0.035, d * 0.3), (5.4, 0.20 * b, 0.10), (13.2, 0.06 * b, 0.025)]
    y = additive(f, min(5.0, d * 5.5), parts, attack=0.0025)
    y = mix_in(y, click(0.004, 3200, 0.07 * b))
    return y * vel


def marimba(f, vel=1.0):
    f = hz(f) if isinstance(f, str) else f
    d = 0.75 * (262.0 / f) ** 0.45
    b = 0.5 + 0.5 * vel
    parts = [(1, 1.0, d), (2.0, 0.02, d * 0.3), (3.93, 0.28 * b, d * 0.14), (9.2, 0.07 * b, d * 0.05)]
    y = additive(f, min(4.0, d * 6), parts, attack=0.002)
    y = mix_in(y, click(0.008, 900, 0.05 * b))
    return y * vel


def glock(f, vel=1.0):
    f = hz(f) if isinstance(f, str) else f
    d = 1.8 * (1000.0 / f) ** 0.5
    parts = [(1, 1.0, d), (2.76, 0.25, d * 0.3), (5.40, 0.08, d * 0.12), (8.93, 0.03, d * 0.06)]
    y = additive(f, min(5.0, d * 5), parts, attack=0.0012)
    y = mix_in(y, click(0.002, 6000, 0.05))
    return y * vel


def handbell(f, vel=1.0):
    f = hz(f) if isinstance(f, str) else f
    d = 2.2 * (800.0 / f) ** 0.45
    parts = [(1, 1.0, d), (1 + 0.9 / f, 0.35, d * 0.9), (2.0, 0.08, d * 0.5), (3.0, 0.32, d * 0.35),
             (4.18, 0.10, d * 0.18), (5.43, 0.07, d * 0.1), (6.79, 0.04, d * 0.07)]
    y = additive(f, min(6.0, d * 5), parts, attack=0.0015)
    y = mix_in(y, click(0.003, 4000, 0.05))
    return y * vel


def bell(f, vel=1.0, T=3.0):
    """Soft tuned bell: strong prime + nominal, with Risset-style inharmonic colour."""
    f = hz(f) if isinstance(f, str) else f
    parts = [(0.5, 0.25, T * 0.9), (0.56, 0.08, T * 0.8), (0.92, 0.10, T * 0.5), (1.0, 1.0, T * 0.6),
             (1.0 + 1.3 / f, 0.4, T * 0.55), (1.19, 0.22, T * 0.35), (1.5, 0.12, T * 0.3),
             (1.71, 0.10, T * 0.25), (2.0, 0.45, T * 0.25), (2.74, 0.15, T * 0.15), (3.0, 0.14, T * 0.12),
             (3.76, 0.06, T * 0.08), (4.07, 0.06, T * 0.07)]
    return additive(f, min(7.0, T * 2.5), parts, attack=0.002) * vel / 1.6


def chime(f, vel=1.0, T=3.2):
    """Tubular wind chime (free-free bar partials) with a slow beat."""
    f = hz(f) if isinstance(f, str) else f
    parts = [(1, 1.0, T), (1 + 0.7 / f, 0.3, T), (2.76, 0.35, T * 0.4), (5.40, 0.14, T * 0.18),
             (8.93, 0.05, T * 0.08)]
    return additive(f, min(7.0, T * 2.2), parts, attack=0.004) * vel / 1.3


def musicbox(f, vel=1.0):
    f = hz(f) if isinstance(f, str) else f
    d = 1.2 * (1000.0 / f) ** 0.35
    parts = [(1, 1.0, d), (2.0, 0.06, d * 0.4), (6.27, 0.16, 0.05), (17.55, 0.05, 0.012)]
    y = additive(f, min(5.0, d * 5), parts, attack=0.0012)
    y = mix_in(y, click(0.002, 7000, 0.04))
    return y * vel


def bass(f, dur, vel=1.0, decay=0.9):
    f = hz(f) if isinstance(f, str) else f
    rel = 0.1
    n = int((dur + rel) * SR)
    t = tvec(n)
    y = np.zeros(n)
    for k, a in [(1, 1.0), (2, 0.45), (3, 0.22), (4, 0.08)]:
        y += a * np.sin(2 * np.pi * k * f * t) * np.exp(-t / (decay / k ** 0.7))
    env = np.ones(n)
    a = int(0.006 * SR)
    env[:a] = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    r0 = int(dur * SR)
    env[r0:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(n - r0) / (n - r0))
    return y * env * vel


def pad(freqs, dur, vel=1.0, attack=0.9, release=1.2, bright=0.8, harmonics=6):
    freqs = [hz(f) if isinstance(f, str) else hz(f) if f < 128 else f for f in freqs]
    n = int((dur + release) * SR)
    t = tvec(n)
    y = np.zeros(n)
    for f in freqs:
        for cents in (-6, 0, 6):
            ff = f * 2 ** (cents / 1200)
            for k in range(1, harmonics + 1):
                y += (bright ** (k - 1) / k ** 1.6) * np.sin(2 * np.pi * k * ff * t + RNG.uniform(0, 6.28))
    env = np.ones(n)
    a = int(attack * SR)
    env[:a] = 0.5 - 0.5 * np.cos(np.pi * np.arange(a) / a)
    r0 = int(dur * SR)
    env[r0:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(n - r0) / (n - r0))
    env *= 1 + 0.08 * np.sin(2 * np.pi * 0.23 * t)
    return y * env * vel / (3 * len(freqs) * 1.6)


def kick(vel=1.0):
    n = int(0.35 * SR)
    t = tvec(n)
    f = 52 + 110 * np.exp(-t / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.14)
    return fade(y, 0.001, 0.02) * vel


def shaker(vel=1.0):
    n = int(0.09 * SR)
    t = tvec(n)
    nz = sos_filter(sos_filter(RNG.standard_normal(n), "highpass", 5000), "lowpass", 10500)
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.025)
    return fade(nz * env / 2.5, 0.0005, 0.01) * vel


def woodblock(f=1650, vel=1.0):
    y = additive(f, 0.12, [(1, 1.0, 0.035), (2.31, 0.35, 0.012), (4.1, 0.1, 0.005)], attack=0.0006)
    return y * vel


# --------------------------------------------------------------------------
# Birds, crickets
# --------------------------------------------------------------------------
def bird_syllable(f0, f1, dur, shape="exp", fm=0.0, fmdev=0.0, peak=0.35, am=0.0):
    n = max(16, int(dur * SR))
    x = np.linspace(0, 1, n)
    if shape == "lin":
        f = f0 + (f1 - f0) * x
    elif shape == "arch":
        f = f0 + (f1 - f0) * np.sin(np.pi * x)
    else:
        f = f0 * (f1 / f0) ** x
    if fm:
        f = f + fmdev * np.sin(2 * np.pi * fm * x * dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = bump(n, peak)
    if am:
        env = env * (0.55 + 0.45 * np.sin(2 * np.pi * am * x * dur))
    return env * (np.sin(ph) + 0.05 * np.sin(2 * ph + 0.4))


def gap(s):
    return np.zeros(int(s * SR))


def call_tweets(r, base):
    out, f = [], base * r.uniform(1.0, 1.12)
    for _ in range(r.integers(3, 7)):
        out += [bird_syllable(f, f * r.uniform(1.25, 1.6), r.uniform(0.045, 0.075), "exp", peak=0.65),
                gap(r.uniform(0.05, 0.1))]
        f *= r.uniform(0.9, 0.98)
    return np.concatenate(out)


def call_trill(r, base):
    fm = r.uniform(20, 32)
    return bird_syllable(base * 1.05, base * 0.95, r.uniform(0.35, 0.75), "lin", fm=fm,
                         fmdev=base * r.uniform(0.07, 0.13), peak=0.25, am=fm)


def call_whistle(r, base):
    out = []
    ratios = r.choice([1.0, 1.26, 0.84, 1.12, 1.5, 1.33], size=r.integers(2, 4))
    for q in ratios:
        f = base * q
        out += [bird_syllable(f * 0.98, f * 1.02, r.uniform(0.14, 0.26), "lin", fm=6, fmdev=f * 0.008, peak=0.3),
                gap(r.uniform(0.04, 0.1))]
    return np.concatenate(out)


def call_chips(r, base):
    out = []
    for _ in range(r.integers(2, 5)):
        out += [bird_syllable(base * 1.55, base * 0.8, r.uniform(0.028, 0.045), "exp", peak=0.2),
                gap(r.uniform(0.05, 0.09))]
    return np.concatenate(out)


def call_song(r, base):
    out = []
    for _ in range(r.integers(5, 10)):
        kind = r.integers(0, 4)
        f = base * r.uniform(0.8, 1.35)
        d = r.uniform(0.04, 0.11)
        if kind == 0:
            s = bird_syllable(f, f * 1.4, d, "exp", peak=0.6)
        elif kind == 1:
            s = bird_syllable(f * 1.3, f, d, "exp", peak=0.3)
        elif kind == 2:
            s = bird_syllable(f, f * 1.35, d * 1.3, "arch", peak=0.5)
        else:
            s = bird_syllable(f, f, d * 1.6, "lin", fm=40, fmdev=f * 0.1, peak=0.4)
        out += [s, gap(r.uniform(0.015, 0.06))]
    return np.concatenate(out)


SPECIES = [  # (call, base Hz, loudness)
    (call_tweets, 3400, 1.0),
    (call_song, 3900, 0.8),
    (call_whistle, 2700, 0.85),
    (call_trill, 4600, 0.55),
    (call_chips, 3600, 0.6),
]


def bird_call(r, species=None):
    fn, base, loud = SPECIES[species if species is not None else r.integers(0, len(SPECIES))]
    y = fn(r, base * r.uniform(0.92, 1.08))
    dist = r.uniform(0.35, 1.0)
    if dist < 0.6:  # far away: darker and softer
        y = sos_filter(y, "lowpass", 3500)
    y = sos_filter(y, "highpass", 1200)
    return fade(y, 0.002, 0.01) * loud * dist


# --------------------------------------------------------------------------
# Timeline
# --------------------------------------------------------------------------
class Track:
    def __init__(self, dur, loop=False):
        self.N = int(round(dur * SR))
        self.buf = np.zeros(self.N)
        self.loop = loop

    def add(self, t, y, gain=1.0):
        y = y * gain
        i = int(round(t * SR))
        if self.loop:
            i %= self.N
            pos = 0
            while pos < len(y):
                k = min(len(y) - pos, self.N - i)
                self.buf[i:i + k] += y[pos:pos + k]
                pos += k
                i = 0
        else:
            if i < 0:
                y, i = y[-i:], 0
            if i >= self.N:
                return
            k = min(len(y), self.N - i)
            self.buf[i:i + k] += y[:k]


# --------------------------------------------------------------------------
# Mastering
# --------------------------------------------------------------------------
def compress(x, thr_db, ratio=3.0, knee_db=8.0, att=0.004, rel=0.16, block=64, circular=False):
    n = len(x)
    nb = -(-n // block)
    pad_n = nb * block - n
    a = np.abs(np.concatenate([x, x[:pad_n] if circular else np.zeros(pad_n)]))
    lvl = 20 * np.log10(a.reshape(nb, block).max(1) + 1e-9)
    over = lvl - thr_db
    s = 1 - 1 / ratio
    gr = np.where(over <= -knee_db / 2, 0.0,
                  np.where(over >= knee_db / 2, s * over, s * (over + knee_db / 2) ** 2 / (2 * knee_db)))
    gr = maximum_filter1d(gr, size=5, mode="wrap" if circular else "nearest")  # ~3 ms lookahead
    ca, cr = np.exp(-block / (att * SR)), np.exp(-block / (rel * SR))
    out = np.empty(nb)
    g = 0.0
    for _ in range(2 if circular else 1):
        for i in range(nb):
            v = gr[i]
            c = ca if v > g else cr
            g = c * g + (1 - c) * v
            out[i] = g
    grs = np.interp(np.arange(n), (np.arange(nb) + 0.5) * block, out)
    return x * 10 ** (-grs / 20)


def soft_limit(x, ceiling_db=-1.0, knee=0.8):
    c = 10 ** (ceiling_db / 20)
    k = knee * c
    ax = np.abs(x)
    y = x.copy()
    o = ax > k
    y[o] = np.sign(x[o]) * (k + (c - k) * np.tanh((ax[o] - k) / (c - k)))
    return y


def build_env(n, starts, levels_db, ramp=0.35, loop_drop=0.3):
    """Section-level automation for the alarms' crescendo. `starts` are section
    start times (s); each level is reached by a smooth ramp ending at that start.
    The loop point drops back to the first level over the final `loop_drop` s."""
    t = tvec(n)
    g = np.full(n, float(levels_db[0]))
    for st, lv, prev in zip(starts[1:], levels_db[1:], levels_db[:-1]):
        x = np.clip((t - (st - ramp)) / ramp, 0, 1)
        g += (lv - prev) * (0.5 - 0.5 * np.cos(np.pi * x))
    x = np.clip((t - (n / SR - loop_drop)) / loop_drop, 0, 1)
    g += (levels_db[0] - levels_db[-1]) * (0.5 - 0.5 * np.cos(np.pi * x))
    return 10 ** (g / 20)


def master(x, target_rms_db=None, ceiling_db=-1.0, circular=False, drive_db=1.0, max_comp_db=-12.0,
           post_env=None):
    x = fft_filter(x, hp_mag(28, 2)) if circular else sos_filter(x, "highpass", 28)
    c = 10 ** (ceiling_db / 20)
    env = 1.0 if post_env is None else post_env

    def finish(y, drive=drive_db):
        y = y * env
        y = y / np.max(np.abs(y)) * c * 10 ** (drive / 20)
        return soft_limit(y, ceiling_db) if drive > 0 else y  # drive 0: clean peak normalize

    if target_rms_db is None:
        return finish(x)
    if db(rms(finish(x))) >= target_rms_db:  # quiet material (ambient): just set level
        y = x * env / rms(x * env) * 10 ** (target_rms_db / 20)
        return soft_limit(y, ceiling_db) if np.max(np.abs(y)) > 0.8 * c else y
    xn = x / np.max(np.abs(x))
    lo, hi = max_comp_db, 0.0
    for _ in range(16):
        mid = (lo + hi) / 2
        if db(rms(finish(compress(xn, mid, circular=circular)))) < target_rms_db:
            hi = mid
        else:
            lo = mid
    comp = compress(xn, lo, circular=circular)
    gr = db(np.max(np.abs(xn))) - db(np.max(np.abs(comp)))
    print(f"    [master] comp threshold {lo:.1f} dB, peak gain reduction {gr:.1f} dB", flush=True)
    return finish(comp)


def write(name, x, target_rms_db=None, loop=False, drive_db=1.0, tail_fade=0.0, post_env=None):
    if tail_fade:
        x = fade(x, 0.0, tail_fade)
    y = master(x, target_rms_db, circular=loop, drive_db=drive_db, post_env=post_env)
    if not loop:
        y = fade(y, 0.0005, 0.004)
    tpdf = (np.random.default_rng(1).random(len(y)) - np.random.default_rng(2).random(len(y)))
    pcm = np.clip(np.round(y * 32767 + tpdf), -32768, 32767).astype(np.int16)
    wav = os.path.join(TMP, name + ".wav")
    sf.write(wav, pcm, SR, subtype="PCM_16")
    caf = os.path.join(OUT_DIR, name + ".caf")
    subprocess.run(["afconvert", "-f", "caff", "-d", "LEI16@44100", wav, caf], check=True)
    seam = ""
    if loop:
        jump = abs(y[0] - y[-1])
        typical = np.percentile(np.abs(np.diff(y)), 99.9)
        seam = f"seam jump {jump:.4f} (99.9% step {typical:.4f}) {'OK' if jump <= typical else 'CHECK'}"
    REPORT.append((name, len(y) / SR, db(np.max(np.abs(y))), db(rms(y)), seam))
    print(f"  {name:18s} {len(y)/SR:6.2f}s  peak {db(np.max(np.abs(y))):6.2f} dBFS  "
          f"RMS {db(rms(y)):6.2f} dBFS  {seam}", flush=True)


def hum(r, s=0.004):
    return r.normal(0, s)


# ==========================================================================
# ALARMS
# ==========================================================================
def alarm_sunrise():
    """D major, 110 bpm, 12 bars (3 x 4-bar cycles that build)."""
    r = np.random.default_rng(101)
    B = 60 / 110
    L = 12 * 4 * B
    tr = Track(L, loop=True)

    # Original 4-bar hook: bouncy call (bar 1) / answer (bar 2), repeat, resolving run (bar 4).
    mel = [(0, "A4", .5), (0.5, "D5", .5), (1, "F#5", .5), (1.5, "A5", 1), (2.5, "F#5", .5), (3, "G5", .5),
           (3.5, "A5", .5),
           (4, "B5", 1), (5, "A5", .5), (5.5, "F#5", .5), (6, "E5", 1.5),
           (8, "A4", .5), (8.5, "D5", .5), (9, "F#5", .5), (9.5, "A5", 1), (10.5, "F#5", .5), (11, "G5", .5),
           (11.5, "A5", .5),
           (12, "D6", .75), (12.75, "C#6", .25), (13, "B5", .5), (13.5, "A5", .5), (14, "F#5", .5),
           (14.5, "E5", .5), (15, "D5", 1)]
    chords = {  # arp tones, bass root, bass fifth
        "D": (["D4", "F#4", "A4", "D5"], "D3", "A3"),
        "G": (["D4", "G4", "B4", "D5"], "G2", "D3"),
        "Bm": (["D4", "F#4", "B4", "D5"], "B2", "F#3"),
        "A": (["C#4", "E4", "A4", "C#5"], "A2", "E3"),
    }

    def chord_at(beat):
        b = beat % 16
        if b < 4:
            return "D"
        if b < 8:
            return "G"
        if b < 12:
            return "Bm"
        return "G" if b < 14 else "A"

    for sec in range(3):
        base = sec * 16
        ramp = lambda b: (b % 16) / 16  # crescendo inside each cycle
        # --- melody
        mv = [0.5, 0.75, 0.95][sec]
        for b, n, d in mel:
            t = (base + b) * B + hum(r)
            v = mv * (0.92 + 0.12 * ramp(b)) * r.uniform(0.93, 1.03)
            tr.add(t, kalimba(n, v), 0.9)
            if sec >= 1:
                tr.add(t, marimba(n, v), 0.45 if sec == 1 else 0.55)
            if sec == 2:
                tr.add(t, glock(hz(n) * 2, 0.5), 0.32)
        # --- accompaniment
        for beat in range(16):
            ch = chord_at(beat)
            arp, root, fifth = chords[ch]
            t0 = (base + beat) * B
            if sec == 0:
                if beat % 2 == 0:
                    tr.add(t0 + hum(r), kalimba(arp[0] if beat % 4 == 0 else arp[2], 0.32), 0.8)
            elif sec == 1:
                order = [0, 1, 2, 3, 2, 1, 3, 2]
                for k in range(2):
                    idx = order[(beat * 2 + k) % 8]
                    acc = 0.42 if k == 0 else 0.32
                    tr.add(t0 + k * B / 2 + hum(r, 0.003), marimba(arp[idx], acc), 0.6)
                if beat % 4 == 0:
                    tr.add(t0, bass(root, 1.4 * B, 0.6), 0.55)
                elif beat % 4 == 2:
                    tr.add(t0, bass(fifth, 0.9 * B, 0.5), 0.55)
                elif beat % 4 == 3:
                    tr.add(t0 + B / 2, bass(root, 0.4 * B, 0.45), 0.55)
                tr.add(t0 + B / 2, shaker(0.5), 0.35)
            else:
                order = [0, 2, 1, 3, 2, 1, 3, 2, 0, 2, 1, 3, 2, 3, 1, 2]
                for k in range(4):
                    idx = order[(beat * 4 + k) % 16]
                    acc = [0.42, 0.26, 0.33, 0.26][k]
                    tr.add(t0 + k * B / 4 + hum(r, 0.002), marimba(hz(arp[idx]) * 2, acc), 0.42)
                    tr.add(t0 + k * B / 4, shaker([0.6, 0.3, 0.45, 0.3][k]), 0.25)
                for k in range(2):
                    n = [root, midi(root) + 12][k] if beat % 2 == 0 else [fifth, midi(root) + 12][k]
                    tr.add(t0 + k * B / 2, bass(n, 0.45 * B, 0.65 if k == 0 else 0.5), 0.6)
                if beat % 2 == 0:
                    tr.add(t0, kick(0.8), 0.5)
                else:
                    tr.add(t0, woodblock(1650, 0.5), 0.35)
                if beat % 4 == 0:
                    tr.add(t0, bell(hz(arp[0]) * 2, 0.55, T=2.2), 0.45)
        if sec == 1:  # lift into the full section: quick glock run
            for k, n in enumerate(["F#6", "G6", "A6", "B6", "C#7", "D7"]):
                tr.add((base + 15.25 + k * 0.125) * B, glock(n, 0.35 + 0.05 * k), 0.4)
        if sec == 2:  # big resolving bell on the final D
            tr.add((base + 15) * B, bell("D6", 0.9, T=3.0), 0.5)

    y = reverb(tr.buf, make_ir(1.4, seed=11), wet=0.2, circular=True)
    env = build_env(len(y), [0, 16 * B, 32 * B], [-6.0, -3.0, 0.0], ramp=B)
    write("alarm_sunrise", y, target_rms_db=-12.0, loop=True, post_env=env, drive_db=2.0)


def alarm_meadow():
    """G major waltz, 104 bpm, 16 bars of 3/4: music box + chimes + birdsong, slow build."""
    r = np.random.default_rng(202)
    B = 60 / 104
    L = 16 * 3 * B
    tr = Track(L, loop=True)
    mel = [(0, "B5", 1), (1, "D6", 1), (2, "G6", 1),
           (3, "F#6", 1.5), (4.5, "E6", .5), (5, "D6", 1),
           (6, "E6", 1), (7, "C6", 1), (8, "G5", 1),
           (9, "A5", 2), (11, "B5", .5), (11.5, "C6", .5),
           (12, "B5", 1), (13, "E6", 1), (14, "G6", 1),
           (15, "E6", 1.5), (16.5, "D6", .5), (17, "C6", 1),
           (18, "C6", 1), (19, "A5", 1), (20, "F#5", 1),
           (21, "G5", 2), (23, "D5", 1)]
    prog = ["G", "D", "C", "D", "Em", "C", "D7", "G"]
    acc = {"G": ("G4", ["B4", "D5"], "G3"), "D": ("D4", ["F#4", "A4"], "D3"), "C": ("C4", ["E4", "G4"], "C3"),
           "Em": ("E4", ["G4", "B4"], "E3"), "D7": ("D4", ["F#4", "C5"], "D3")}
    pads = {"G": ["G3", "B3", "D4"], "D": ["F#3", "A3", "D4"], "C": ["G3", "C4", "E4"],
            "Em": ["G3", "B3", "E4"], "D7": ["F#3", "C4", "D4"]}

    for half in range(2):
        for b, n, d in mel:
            beat = half * 24 + b
            bar = int(beat // 3)
            prog_t = beat / 48
            v = 0.5 + 0.4 * prog_t
            t = beat * B + hum(r)
            tr.add(t, musicbox(n, v * r.uniform(0.94, 1.04)), 0.9)
            if bar >= 8 and (b % 3 == 0 or d >= 1.5):
                tr.add(t, chime(hz(n) / 2, 0.55 + 0.3 * (bar >= 12)), 0.5)
    for bar in range(16):
        ch = prog[bar % 8]
        low, dy, bs = acc[ch]
        t0 = bar * 3 * B
        if bar >= 4:
            v = 0.3 + 0.2 * (bar >= 8) + 0.1 * (bar >= 12)
            tr.add(t0 + hum(r), musicbox(low, v), 0.8)
            for k in (1, 2):
                for n in dy:
                    tr.add(t0 + k * B + hum(r, 0.003), musicbox(n, v * 0.6), 0.7)
        if bar >= 12:
            tr.add(t0, marimba(bs, 0.5), 0.7)
            arp = [low, dy[0], dy[1], hz(low) * 2, dy[1], dy[0]]
            for k, n in enumerate(arp):
                tr.add(t0 + k * B / 2 + hum(r, 0.003), kalimba(hz(n) if isinstance(n, str) else n, 0.3), 0.55)
            tr.add(t0, pad(pads[ch], 3 * B, 0.5, attack=0.4, release=0.8), 0.35)
    # wind-chime cascades marking the build
    for start, cnt in [(8 * 3 * B - 0.4, 6), (12 * 3 * B - 0.5, 9)]:
        for k in range(cnt):
            n = r.choice(["G6", "A6", "B6", "D7", "E7", "G7"])
            tr.add(start + k * r.uniform(0.07, 0.12), chime(n, r.uniform(0.2, 0.4), T=2.0), 0.35)
    # birdsong, getting busier
    t = 0.6
    while t < L - 0.5:
        prog_t = t / L
        tr.add(t, bird_call(r), 0.07 + 0.05 * prog_t)
        t += r.uniform(2.2, 4.0) * (1 - 0.55 * prog_t)
    y = reverb(tr.buf, make_ir(1.8, seed=12, bright=7000), wet=0.26, circular=True)
    env = build_env(len(y), [0, 12 * B, 24 * B, 36 * B], [-7.0, -4.5, -2.0, 0.0], ramp=1.5 * B)
    write("alarm_meadow", y, target_rms_db=-13.0, loop=True, post_env=env, drive_db=2.0)


def plain_hunt(n=6, rows=12):
    row, out = list(range(n)), []
    for i in range(rows):
        out.append(row[:])
        start = 0 if i % 2 == 0 else 1
        for j in range(start, n - 1, 2):
            row[j], row[j + 1] = row[j + 1], row[j]
    return out


def alarm_bells():
    """A major, 136 bpm, 16 bars: glock ostinato -> handbell tune -> full peal."""
    r = np.random.default_rng(303)
    B = 60 / 136
    L = 16 * 4 * B
    tr = Track(L, loop=True)
    prog = ["A", "C#m", "D", "E"]
    ost = {"A": ("A5", "C#6", "E6"), "C#m": ("G#5", "C#6", "E6"), "D": ("A5", "D6", "F#6"),
           "E": ("G#5", "B5", "E6")}
    bassn = {"A": ("A2", "E3"), "C#m": ("C#3", "G#3"), "D": ("D3", "A3"), "E": ("E3", "B3")}
    tune = [[(0, "E6", 1.5), (1.5, "C#6", .5), (2, "E6", 1), (3, "A6", 1)],
            [(0, "G#6", 1.5), (1.5, "E6", .5), (2, "C#6", 1), (3, "E6", 1)],
            [(0, "F#6", 1.5), (1.5, "D6", .5), (2, "A5", 1), (3, "D6", 1)],
            [(0, "E6", 1), (1, "F#6", .5), (1.5, "G#6", .5), (2, "B6", 2)]]
    peal_bells = ["A5", "F#5", "E5", "C#5", "B4", "A4"]  # treble..tenor
    peal = [peal_bells[i] for row in plain_hunt(6, 12) for i in row]
    pi = 0
    for bar in range(16):
        sec = bar // 4
        ch = prog[bar % 4]
        lo, mid, hi = ost[ch]
        t0 = bar * 4 * B
        ramp = bar / 15
        # glock ostinato: 8ths, then 16ths
        if sec == 0:
            pat = [lo, mid, hi, mid] * 2
            for k, n in enumerate(pat):
                tr.add(t0 + k * B / 2 + hum(r, 0.002), glock(n, 0.5 + 0.12 * (k % 2 == 0) + 0.1 * ramp), 0.5)
            tr.add(t0, handbell(lo, 0.55), 0.5)
        else:
            pat = [lo, hi, mid, hi] * 4
            for k, n in enumerate(pat):
                acc = 0.55 if k % 4 == 0 else 0.38
                tr.add(t0 + k * B / 4 + hum(r, 0.0015), glock(n, acc + 0.1 * ramp), 0.42)
        # handbell tune
        if sec >= 1:
            for b, n, d in tune[bar % 4]:
                v = 0.7 + 0.1 * sec
                tr.add(t0 + b * B + hum(r), handbell(n, v), 0.75)
                if sec == 3:
                    tr.add(t0 + b * B, glock(hz(n) * 2, 0.45), 0.35)
        # bass
        root, fifth = bassn[ch]
        if sec == 1:
            for k in range(4):
                tr.add(t0 + k * B, bass(root if k % 2 == 0 else fifth, 0.8 * B, 0.6), 0.6)
        elif sec >= 2:
            for k in range(8):
                n = [root, root, fifth, midi(root) + 12][k % 4]
                tr.add(t0 + k * B / 2, bass(n, 0.42 * B, 0.7 if k % 2 == 0 else 0.5), 0.6)
        # peal of low handbells and drums
        if sec >= 2:
            for k in range(8):
                tr.add(t0 + k * B / 2 + hum(r, 0.003), handbell(peal[pi % len(peal)], 0.42 + 0.1 * (sec == 3)), 0.5)
                pi += 1
            for k in range(4):
                tr.add(t0 + k * B, kick(0.8) if k % 2 == 0 else woodblock(1900, 0.6), 0.5 if k % 2 == 0 else 0.4)
                for s in range(4):
                    tr.add(t0 + (k + s / 4) * B, shaker([0.6, 0.3, 0.45, 0.3][s]), 0.35)
        if sec == 3 and bar % 2 == 1:  # insistent "ding-ding-ding" on the top bell
            for k in range(3):
                tr.add(t0 + (3 + k / 3) * B, handbell("A6", 0.5), 0.4)
    y = reverb(tr.buf, make_ir(1.2, seed=13, bright=8000), wet=0.18, circular=True)
    env = build_env(len(y), [0, 16 * B, 32 * B, 48 * B], [-6.0, -4.0, -2.0, 0.0], ramp=B)
    write("alarm_bells", y, target_rms_db=-12.0, loop=True, post_env=env, drive_db=2.0)


# ==========================================================================
# UI SOUND EFFECTS
# ==========================================================================
def sfx_ir():
    return make_ir(0.8, predelay=0.006, seed=21, bright=9000)


def bubble(f0, f1, dur, tau, n_harm=0.1):
    n = int(dur * SR)
    t = tvec(n)
    f = f0 * (f1 / f0) ** np.clip(t / (dur * 0.5), 0, 1)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return fade((np.sin(ph) + n_harm * np.sin(2 * ph)) * np.exp(-t / tau), 0.001, 0.01)


def sfx_tap():
    tr = Track(0.1)
    tr.add(0, bubble(520, 1150, 0.1, 0.018))
    tr.add(0, click(0.0015, 5000, 0.05))
    write("sfx_tap", reverb(tr.buf, sfx_ir(), 0.06), drive_db=0, tail_fade=0.02)


def sfx_rep():
    tr = Track(0.25)
    tr.add(0, bubble(420, 1400, 0.08, 0.02), 0.45)
    tr.add(0.004, kalimba("E6", 1.0))
    tr.add(0.004, marimba("E6", 0.5), 0.4)
    write("sfx_rep", reverb(tr.buf, sfx_ir(), 0.1), drive_db=0, tail_fade=0.08)


def sfx_coin():
    r = np.random.default_rng(404)
    tr = Track(0.6)
    for k, n in enumerate(["G6", "B6", "D7"]):
        tr.add(k * 0.045, glock(n, 0.9 - 0.1 * k))
        tr.add(k * 0.045, kalimba(n, 0.5), 0.5)
    pent = ["G7", "A7", "B7", "D8", "E8"]
    t = 0.13
    for k in range(7):
        tr.add(t, glock(r.choice(pent), 0.35 * (1 - k / 9)), 0.8)
        t += r.uniform(0.03, 0.055)
    write("sfx_coin", reverb(tr.buf, sfx_ir(), 0.18), drive_db=0, tail_fade=0.15)


def sfx_complete():
    r = np.random.default_rng(405)
    tr = Track(2.0)
    for k, n in enumerate(["D5", "F#5", "A5", "D6"]):
        tr.add(k * 0.075, marimba(n, 0.8), 0.9)
        tr.add(k * 0.075, kalimba(n, 0.7), 0.7)
    for n in ["A5", "C#6", "E6"]:
        tr.add(0.32, marimba(n, 0.55), 0.6)
    for n in ["D6", "F#6", "A6"]:
        tr.add(0.46, glock(n, 0.6), 0.55)
        tr.add(0.46, kalimba(n, 0.8), 0.6)
    tr.add(0.46, marimba("D4", 0.8), 0.8)
    tr.add(0.46, bass("D3", 0.6, 0.6), 0.5)
    tr.add(0.46, bell("D6", 0.9, T=2.0), 0.7)
    t = 0.58
    for k, n in enumerate(["D7", "E7", "F#7", "A7", "B7", "D8", "E8", "F#8"]):
        tr.add(t, glock(n, 0.35 * (1 - k / 12)), 0.7)
        t += r.uniform(0.045, 0.07)
    write("sfx_complete", reverb(tr.buf, make_ir(1.2, seed=22), 0.2), drive_db=0.5, tail_fade=0.5)


def sfx_build():
    r = np.random.default_rng(406)
    tr = Track(1.2)
    n = int(0.5 * SR)
    t = tvec(n)
    nz = r.standard_normal(n)
    bright = sos_filter(nz, "lowpass", 3500)
    dark = sos_filter(nz, "lowpass", 700)
    x = np.exp(-t / 0.07)
    poof = (bright * x + dark * (1 - x)) * (1 - np.exp(-t / 0.008)) * np.exp(-t / 0.11)
    tr.add(0, fade(poof / np.max(np.abs(poof)), 0.001, 0.05), 0.55)
    thud = np.sin(2 * np.pi * np.cumsum(60 + 70 * np.exp(-t / 0.05)) / SR) * np.exp(-t / 0.09)
    tr.add(0, fade(thud, 0.002, 0.05), 0.45)
    tr.add(0.17, glock("A5", 0.75))
    tr.add(0.17, kalimba("A5", 0.6), 0.6)
    tr.add(0.29, glock("D6", 0.85))
    tr.add(0.29, kalimba("D6", 0.7), 0.6)
    tr.add(0.29, bell("D6", 0.5, T=1.4), 0.5)
    tr.add(0.42, glock("F#7", 0.25), 0.6)
    write("sfx_build", reverb(tr.buf, sfx_ir(), 0.2), drive_db=0.5, tail_fade=0.35)


def sfx_levelup():
    r = np.random.default_rng(407)
    tr = Track(2.5)
    run = ["D5", "E5", "F#5", "A5", "B5", "D6", "E6", "F#6", "A6", "B6", "D7"]
    for k, n in enumerate(run):
        tr.add(k * 0.042, kalimba(n, 0.45 + 0.04 * k), 0.8)
    hits = [(0.52, ["G5", "B5", "D6"], "G3"), (0.70, ["A5", "C#6", "E6"], "A3"),
            (0.88, ["D6", "F#6", "A6", "D7"], "D3")]
    for t0, notes, root in hits:
        final = notes[-1] == "D7"
        for n in notes:
            tr.add(t0, marimba(n, 0.75), 0.6)
            tr.add(t0, glock(n, 0.5 if final else 0.35), 0.45)
            tr.add(t0, kalimba(n, 0.6), 0.5)
        tr.add(t0, bass(root, 0.9 if final else 0.15, 0.6), 0.5)
    tr.add(0.88, bell("D6", 0.9, T=2.6), 0.6)
    tr.add(0.88, bell("A5", 0.5, T=2.4), 0.4)
    tr.add(0.7, pad(["D4", "F#4", "A4", "D5"], 1.1, 1.0, attack=0.25, release=0.6, bright=0.9), 0.5)
    t = 0.95
    dust = ["D7", "E7", "F#7", "A7", "B7", "D8", "E8"]
    while t < 2.1:
        tr.add(t, glock(r.choice(dust), 0.28 * (1 - (t - 0.95) / 1.4)), 0.7)
        t += r.uniform(0.05, 0.11)
    write("sfx_levelup", reverb(tr.buf, make_ir(1.6, seed=23), 0.24), drive_db=0.5, tail_fade=0.5)


def sfx_pet():
    tr = Track(0.4)
    dur = 0.3
    n = int(dur * SR)
    t = tvec(n)
    contour = 520 * (1 + 0.75 * (t / dur) ** 1.5)  # happy upward glide
    wobble = 1 + 0.11 * np.sin(2 * np.pi * 17 * t) * np.exp(-t / 0.12)  # springy "boing"
    f = contour * wobble
    ph = 2 * np.pi * np.cumsum(f) / SR
    env = (1 - np.exp(-t / 0.006)) * np.exp(-t / 0.16)
    voice = (np.sin(ph) + 0.28 * np.sin(2 * ph) + 0.1 * np.sin(3 * ph)) * env
    tr.add(0, fade(voice, 0.004, 0.04))
    tr.add(0.2, bird_syllable(1300, 2100, 0.07, "exp", peak=0.5), 0.35)  # tiny happy chirp
    tr.add(0.24, glock("E7", 0.2), 0.5)
    write("sfx_pet", reverb(tr.buf, sfx_ir(), 0.1), drive_db=0, tail_fade=0.08)


def sfx_nope():
    tr = Track(0.3)
    for t0, n in [(0, "C5"), (0.13, "A4")]:
        f = hz(n)
        m = int(0.16 * SR)
        t = tvec(m)
        ff = f * (1 - 0.03 * t / 0.16)
        ph = 2 * np.pi * np.cumsum(ff) / SR
        y = (np.sin(ph) + 0.12 * np.sin(3 * ph) + 0.05 * np.sin(2 * ph)) * np.exp(-t / 0.06)
        tr.add(t0, fade(y, 0.004, 0.03), 1.0 if t0 == 0 else 0.85)
    write("sfx_nope", reverb(sos_filter(tr.buf, "lowpass", 3000), sfx_ir(), 0.08), drive_db=0, tail_fade=0.05)


# ==========================================================================
# AMBIENT LOOPS
# ==========================================================================
def amb_day():
    r = np.random.default_rng(505)
    L = 40.0
    tr = Track(L, loop=True)
    N = tr.N
    base = shaped_noise(N, r, mags(brown_mag, hp_mag(50), lp_mag(650)))
    gust = shaped_noise(N, r, mags(pink_mag, hp_mag(350), lp_mag(2000)))
    leaves = shaped_noise(N, r, mags(hp_mag(2500), lp_mag(7000)))
    e1 = 0.6 + 0.4 * periodic_lfo(N, r, 0.07)
    g = np.clip(periodic_lfo(N, r, 0.1), 0, 1) ** 1.5
    wind = base * e1 * 0.55 + gust * (0.12 + g) * 0.3 + leaves * g * 0.06
    t = r.uniform(0.5, 2)
    species_here = [0, 1, 2, 4]
    while t < L - 0.2:
        tr.add(t, bird_call(r, int(r.choice(species_here))), 0.5)
        t += r.uniform(1.8, 5.5)
    birds = reverb(tr.buf, make_ir(0.7, seed=31, bright=8000), wet=0.25, circular=True)
    write("amb_day", wind * 0.35 + birds, target_rms_db=-24.0, loop=True)


def amb_night():
    r = np.random.default_rng(606)
    L = 40.0
    tr = Track(L, loop=True)
    N = tr.N
    for c in range(5):
        fc = r.uniform(4250, 4850)
        period = r.uniform(0.5, 0.85)
        pulses = int(r.integers(3, 5))
        plen, pgap = r.uniform(0.012, 0.018), r.uniform(0.028, 0.034)
        amp = [1.0, 0.7, 0.5, 0.35, 0.25][c]
        m = int(plen * SR)
        tt = tvec(m)
        pulse = np.sin(2 * np.pi * fc * tt) * bump(m, 0.4) + 0.04 * np.sin(4 * np.pi * fc * tt) * bump(m, 0.4)
        chirp = np.zeros(int(((pulses - 1) * pgap + plen) * SR) + 1)
        for p in range(pulses):
            i = int(p * pgap * SR)
            chirp[i:i + m] += pulse * (0.8 + 0.2 * (p == 1))
        t = r.uniform(0, period)
        on = True
        while t < L:
            if r.random() < 0.04:
                on = not on
            if on:
                tr.add(t, chirp, amp * r.uniform(0.85, 1.0))
            t += period * r.uniform(0.96, 1.04)
    t = tvec(N)
    chorus_fc, chorus_am = pf(4100, N), pf(38, N)
    swell = 0.6 + 0.4 * periodic_lfo(N, r, 0.05)
    chorus = np.sin(2 * np.pi * chorus_fc * t) * (0.5 + 0.5 * np.sin(2 * np.pi * chorus_am * t)) ** 2 * swell
    crickets = tr.buf + 0.06 * chorus
    crickets = reverb(crickets, make_ir(1.1, seed=32, bright=9000), wet=0.3, circular=True)
    wind = shaped_noise(N, r, mags(brown_mag, hp_mag(40), lp_mag(380))) * (0.55 + 0.45 * periodic_lfo(N, r, 0.05))
    write("amb_night", crickets * 0.5 + wind * 0.09, target_rms_db=-24.0, loop=True)


def amb_rain():
    r = np.random.default_rng(707)
    L = 40.0
    tr = Track(L, loop=True)
    N = tr.N
    bed = shaped_noise(N, r, mags(pink_mag, hp_mag(250), lp_mag(2800, 2)))
    rumble = shaped_noise(N, r, mags(brown_mag, hp_mag(40), lp_mag(260)))
    swell = 0.85 + 0.15 * periodic_lfo(N, r, 0.06)
    # dense patter: random impulses shaped into soft ticks
    imp = np.zeros(N)
    k = int(900 * L)
    idx = r.integers(0, N, k)
    np.add.at(imp, idx, r.lognormal(0, 0.6, k) * r.choice([-1, 1], k))
    patter = fft_filter(imp, mags(hp_mag(900), lp_mag(4200)))
    patter /= rms(patter)
    # bubbles and plinks (Minnaert-style rising sine drops)
    for _ in range(int(14 * L)):
        f0 = np.exp(r.uniform(np.log(1200), np.log(3600)))
        tr.add(r.uniform(0, L), bubble(f0, f0 * r.uniform(1.3, 1.9), 0.05, r.uniform(0.005, 0.014)),
               r.lognormal(-1.2, 0.6) * 0.5)
    for _ in range(int(0.7 * L)):
        f0 = r.uniform(700, 1500)
        tr.add(r.uniform(0, L), bubble(f0, f0 * 1.5, 0.12, 0.035), r.uniform(0.2, 0.5))
    t = 0.3
    while t < L - 0.1:  # a cozy drip from the eaves
        tr.add(t, bubble(950, 1450, 0.1, 0.03), 0.45)
        t += r.uniform(1.4, 2.4)
    drops = fft_filter(tr.buf, lp_mag(4500))
    mix = bed * swell * 1.0 + rumble * 0.7 + patter * 0.25 * swell + drops * 0.45
    mix = reverb(mix, make_ir(0.9, seed=33, bright=6000), wet=0.2, circular=True)
    write("amb_rain", mix, target_rms_db=-24.0, loop=True)


# ==========================================================================
# MUSIC
# ==========================================================================
def music_island():
    """F major lo-fi, 80 bpm swing, 16 bars = 48 s loop."""
    r = np.random.default_rng(808)
    B = 60 / 80
    L = 16 * 4 * B
    tr = Track(L, loop=True)
    SW = 0.62

    def sw(b):
        frac = b % 1
        return b - frac + (SW if abs(frac - 0.5) < 1e-6 else frac)

    prog = [[("Fmaj7", 4)], [("Em7", 2), ("A7", 2)], [("Dm9", 4)], [("Cm7", 2), ("F7", 2)],
            [("Bbmaj7", 4)], [("Bbm6", 4)], [("Am7", 2), ("D7", 2)], [("Gm7", 2), ("C7", 2)]]
    V = {"Fmaj7": ["F3", "A3", "C4", "E4"], "Em7": ["E3", "G3", "B3", "D4"], "A7": ["G3", "C#4", "E4", "A4"],
         "Dm9": ["F3", "A3", "C4", "E4"], "Cm7": ["G3", "Bb3", "C4", "Eb4"], "F7": ["A3", "C4", "Eb4", "F4"],
         "Bbmaj7": ["F3", "A3", "Bb3", "D4"], "Bbm6": ["F3", "G3", "Bb3", "Db4"], "Am7": ["G3", "A3", "C4", "E4"],
         "D7": ["F#3", "A3", "C4", "D4"], "Gm7": ["F3", "G3", "Bb3", "D4"], "C7": ["E3", "G3", "Bb3", "D4"]}
    ROOT = {"Fmaj7": ("F2", "C3"), "Em7": ("E2", "B2"), "A7": ("A2", "E3"), "Dm9": ("D3", "A2"),
            "Cm7": ("C3", "G2"), "F7": ("F2", "C3"), "Bbmaj7": ("Bb2", "F2"), "Bbm6": ("Bb2", "F2"),
            "Am7": ("A2", "E3"), "D7": ("D3", "A2"), "Gm7": ("G2", "D3"), "C7": ("C3", "G2")}
    A = [[(0, "C5", 1), (1, "A4", .5), (1.5, "C5", .5), (2, "E5", 1.5), (3.5, "D5", .5)],
         [(0, "D5", 1), (1, "B4", .5), (1.5, "D5", .5), (2, "C#5", 1), (3, "E5", .5), (3.5, "G5", .5)],
         [(0, "F5", 1.5), (1.5, "E5", .5), (2, "D5", .5), (2.5, "A4", .5), (3, "C5", 1)],
         [(0, "Bb4", .5), (0.5, "C5", .5), (1, "Eb5", 1), (2, "C5", .5), (2.5, "A4", .5), (3, "Eb5", .5),
          (3.5, "D5", .5)],
         [(0, "D5", 2), (2, "F5", .5), (2.5, "A5", .5), (3, "G5", .5), (3.5, "F5", .5)],
         [(0, "F5", 1.5), (1.5, "Db5", .5), (2, "C5", 1), (3, "Bb4", .5), (3.5, "Db5", .5)],
         [(0, "C5", 1), (1, "E5", .5), (1.5, "G5", .5), (2, "F#5", 1), (3, "A5", .5), (3.5, "F#5", .5)],
         [(0, "G5", 1), (1, "F5", .5), (1.5, "D5", .5), (2, "E5", 1.5)]]
    Bend = [[(0, "A5", 1), (1, "F5", .5), (1.5, "D5", .5), (2, "C5", 1), (3, "D5", .5), (3.5, "F5", .5)],
            [(0, "G5", 1.5), (1.5, "F5", .5), (2, "Db5", 1.5), (3.5, "C5", .5)],
            [(0, "E5", 1), (1, "C5", .5), (1.5, "A4", .5), (2, "A5", 1), (3, "F#5", .5), (3.5, "D5", .5)],
            [(0, "F5", 1), (1, "D5", .5), (1.5, "Bb4", .5), (2, "Bb4", 1), (3, "G4", .5), (3.5, "A4", .5)]]
    melody = A + A[:4] + Bend

    for bar in range(16):
        t0 = bar * 4 * B
        # chords: pad + soft marimba comp + bass
        pos = 0
        for name, ln in prog[bar % 8]:
            cs = t0 + pos * B
            tr.add(cs, pad(V[name], ln * B, 1.0, attack=0.5, release=0.9, bright=0.7), 0.22)
            root, fifth = ROOT[name]
            tr.add(cs + hum(r, 0.005), bass(root, (1.4 if ln == 4 else 1.2) * B, 0.7, decay=1.2), 0.42)
            if ln == 4:
                tr.add(cs + 2 * B + hum(r, 0.005), bass(fifth, 1.0 * B, 0.55, decay=1.0), 0.42)
                tr.add(cs + sw(3.5) * B, bass(root, 0.3 * B, 0.4), 0.42)
            else:
                tr.add(cs + sw(1.5) * B, bass(midi(root) + 12, 0.3 * B, 0.4), 0.42)
            for cb in ([1.5, 3] if ln == 4 else [1.5]):
                for n in V[name][1:]:
                    tr.add(cs + sw(cb) * B + hum(r, 0.006), marimba(hz(n) * 2, 0.22), 0.4)
            pos += ln
        # melody
        for b, n, d in melody[bar]:
            t = t0 + sw(b) * B + hum(r, 0.006)
            v = r.uniform(0.62, 0.74) * (1.08 if d >= 1 else 1.0)
            tr.add(t, kalimba(n, v), 0.9)
            if 8 <= bar < 12 and d >= 1.5:
                tr.add(t + 0.01, glock(hz(n) * 2, 0.22), 0.5)
        # soft drums
        for beat in range(4):
            tb = t0 + beat * B
            if beat in (0, 2):
                tr.add(tb, kick(0.6), 0.32)
            else:
                tr.add(tb + hum(r, 0.004), woodblock(1250, 0.35), 0.18)
            tr.add(tb, shaker(0.35), 0.28)
            tr.add(t0 + sw(beat + 0.5) * B, shaker(0.55), 0.28)
        if bar % 4 == 3:
            tr.add(t0 + sw(2.5) * B, kick(0.45), 0.25)

    y = reverb(tr.buf, make_ir(1.7, seed=41, bright=5500), wet=0.24, circular=True)
    y = fft_filter(y, lp_mag(7500, 2))  # lo-fi softening
    # gentle tape wow, periodic over the loop
    N = len(y)
    d = (0.0018 + 0.0007 * np.sin(2 * np.pi * pf(0.55, N) * tvec(N))) * SR
    idx = (np.arange(N) - d) % N
    y = np.interp(idx, np.arange(N + 1), np.concatenate([y, y[:1]]))
    write("music_island", y, target_rms_db=-18.0, loop=True)


# ==========================================================================
ALL = [alarm_sunrise, alarm_meadow, alarm_bells,
       sfx_rep, sfx_complete, sfx_coin, sfx_build, sfx_levelup, sfx_tap, sfx_pet, sfx_nope,
       amb_day, amb_night, amb_rain, music_island]

if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    wanted = set(sys.argv[1:])
    with tempfile.TemporaryDirectory() as TMP:
        print(f"Writing to {OUT_DIR}")
        for fn in ALL:
            if not wanted or fn.__name__ in wanted:
                fn()
    print("\nSummary")
    for name, dur, pk, rm, seam in REPORT:
        print(f"  {name:18s} {dur:6.2f}s  peak {pk:6.2f}  RMS {rm:6.2f}")
