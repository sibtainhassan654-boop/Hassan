"""
Documentary-style edit of the Codex Gigas short.

Steps
  1. Sound design: build a music bed + whooshes, booms, clicks, stamps (numpy),
     and mix it under the original voice-over.
  2. Picture: upscale to 1080x1920, colour grade, vignette, punch-in zooms,
     camera shake, flashes, and the animated graphics from overlay.html.
  3. Encode: film grain, loudness normalised for social media (-14 LUFS).

Usage:  python3 edit.py <source.mp4> <overlay_frames_dir> <output.mp4>
"""
import os, subprocess, sys, wave
import numpy as np
from PIL import Image

SRC, OVL, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
W, H, FPS = 1080, 1920, 30
SRC_DUR, END_CARD = 106.25, 3.5
TOTAL = SRC_DUR + END_CARD
SR = 48000
WORK = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_work")
os.makedirs(WORK, exist_ok=True)

# ---------------------------------------------------------------------------
# Edit decision list (seconds on the original timeline)
# ---------------------------------------------------------------------------
PUNCH = [5.0, 15.0, 17.4, 24.3, 38.5, 50.0, 54.2, 57.0, 59.6, 73.0, 77.0, 85.6, 97.3, 101.6]
BOOMS = PUNCH + [63.9, 78.3, 106.4]
STAMPS = [14.5, 23.75, 76.85, 101.45]
WHOOSH = [0.1, 3.05, 6.3, 8.4, 15.9, 21.0, 25.7, 26.4, 36.6, 40.9, 44.6, 50.8, 53.6, 58.6, 63.8,
          66.8, 77.7, 78.2, 82.2, 87.6, 97.8, 98.2, 103.2]
FLASH = [17.4, 38.5, 54.2, 63.9, 78.3]
SHAKE = STAMPS + [54.2, 57.0, 73.0]
TICKS = [(3.2, 4.3), (8.8, 11.0), (41.0, 42.7), (83.0, 85.6), (6.75, 7.1)]
TYPING = [(1.45, 2.95), (21.0 + 2.0, 21.0 + 3.2), (26.6, 27.3), (27.8, 28.35), (29.15, 29.7), (30.2, 30.75),
          (31.4, 31.95), (54.7, 55.8), (64.0, 64.5), (67.2, 67.8), (67.9, 68.5), (70.2, 70.8), (72.6, 73.2),
          (78.4, 78.9)]
MARKER = [(19.7, 20.3), (45.5, 46.1), (46.6, 47.2), (73.3, 73.9), (86.25, 86.55)]

# ---------------------------------------------------------------------------
# 1. SOUND DESIGN
# ---------------------------------------------------------------------------
rng = np.random.default_rng(3)
N = int(TOTAL * SR)
tt = np.arange(N) / SR

def smooth(x, k):                       # cheap low-pass: moving average
    c = np.cumsum(np.concatenate([[0], x]))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([y, np.zeros(len(x) - len(y))])

def place(buf, snd, at, gain=1.0):
    i = int(at * SR)
    if i < 0: snd, i = snd[-i:], 0
    if i >= len(buf): return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n] * gain

def env(n, a, d):                        # attack + exponential decay
    x = np.arange(n) / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.exp(-x / d)

# music bed: dark D-minor drone with slow movement
bed = np.zeros(N)
for f, g in [(36.71, .55), (73.42, .5), (110.0, .28), (146.83, .22), (174.61, .16), (220.0, .1)]:
    for det in (-.6, .6):
        lfo = .6 + .4 * np.sin(2 * np.pi * (0.05 + f / 9000) * tt + f)
        bed += g * lfo * np.sin(2 * np.pi * (f + det) * tt)
air = smooth(rng.standard_normal(N), 60) * 2.2 * (0.6 + 0.4 * np.sin(2 * np.pi * .07 * tt))
bed += air
# tension pulse (heartbeat) during the legend
hb = np.zeros(N); beat = np.sin(2 * np.pi * 52 * np.arange(int(.25 * SR)) / SR) * env(int(.25 * SR), .005, .07)
for s in np.arange(64.0, 78.0, 0.85):
    place(hb, beat, s, 1.0); place(hb, beat, s + .22, .6)
bed += hb * 1.6
# swell + fades
lvl = np.interp(tt, [0, 1.5, 63, 64, 78, 79, 98, 103, SRC_DUR, SRC_DUR + .5, TOTAL - 1, TOTAL],
                    [0, .8, .8, 1, 1, .75, .75, 1, 1, 1.25, 1.25, 0])
bed *= lvl / np.max(np.abs(bed)) * 0.16

sfx = np.zeros(N)
def boom():
    n = int(2.2 * SR); x = np.arange(n) / SR
    f = 30 + 55 * np.exp(-x * 9)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, .004, .55)
    s += smooth(rng.standard_normal(n), 25) * env(n, .002, .12) * 2.5
    return s
def whoosh(dur=.6):
    n = int(dur * SR); x = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    k = (4 + 40 * (1 - np.sin(np.pi * x))).astype(int)        # sweep: dull -> bright -> dull
    out = np.zeros(n); c = np.cumsum(np.concatenate([[0], noise]))
    idx = np.arange(n); lo = np.maximum(idx - k, 0)
    out = (c[idx + 1] - c[lo]) / (idx + 1 - lo)
    return out * np.sin(np.pi * x) ** 2 * 3.0
def click(f=2400, d=.012):
    n = int(.04 * SR); x = np.arange(n) / SR
    return (rng.standard_normal(n) * .5 + np.sin(2 * np.pi * f * x)) * env(n, .0005, d)
def stamp_snd():
    n = int(.5 * SR); x = np.arange(n) / SR
    return (np.sin(2 * np.pi * (60 + 80 * np.exp(-x * 30)) * x) * env(n, .001, .09) * 1.4
            + smooth(rng.standard_normal(n), 6) * env(n, .001, .03) * 2)
def marker_snd(dur):
    n = int(dur * SR); x = np.arange(n) / SR
    s = smooth(rng.standard_normal(n), 3) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * x) ** 2)
    return s * np.minimum(1, np.minimum(x, dur - x) / .03) * .5

for b in BOOMS: place(sfx, boom(), b - .02, .9)
for w in WHOOSH: place(sfx, whoosh(), w - .3, .35)
for s in STAMPS: place(sfx, stamp_snd(), s + .1, 1.0)
for a, b in TICKS:
    for s in np.arange(a, b, .065): place(sfx, click(3200, .006), s, .25)
for a, b in TYPING:
    s = a
    while s < b:
        place(sfx, click(1500 + rng.random() * 900, .01), s, .35); s += .045 + rng.random() * .05
for a, b in MARKER: place(sfx, marker_snd(b - a), a, .5)

# original voice-over
voice_wav = os.path.join(WORK, "voice.wav")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-vn", "-ac", "1", "-ar", str(SR), voice_wav], check=True)
with wave.open(voice_wav) as wf:
    voice = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float64) / 32768
v = np.zeros(N); v[:min(N, len(voice))] = voice[:N]

# duck music + sfx a little while someone is speaking
spk = smooth(np.abs(v), int(.25 * SR)); spk = np.clip(spk / (np.percentile(spk, 90) + 1e-9), 0, 1)
duck = 1 - .35 * spk
mix = v * 1.0 + (bed + sfx * .5) * duck
mix = np.tanh(mix * 1.1) / np.tanh(1.1)                    # soft limiter
mix_wav = os.path.join(WORK, "mix.wav")
with wave.open(mix_wav, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
print("audio mixed")

# ---------------------------------------------------------------------------
# 2. PICTURE
# ---------------------------------------------------------------------------
def punch(t):
    z = 1.0 + 0.012 * ((t % 10) / 10)                         # slow constant push-in
    for h in PUNCH:
        d = t - h
        if -0.12 < d < 1.6:
            a = (d + .12) / .12 if d < 0 else np.exp(-d / .7)
            z += 0.075 * min(1, a)
    return z

def shake(t):
    dx = dy = 0.0
    for s in SHAKE:
        d = t - s
        if 0 <= d < .35:
            k = (1 - d / .35) * 14
            dx += np.sin(d * 95) * k; dy += np.cos(d * 77) * k
    return dx, dy

def flash(t):
    a = 0.0
    for f in FLASH:
        d = t - f
        if -0.03 < d < .25: a = max(a, (1 - max(d, 0) / .25) * .55)
    return a

grade = ("scale=1080:1920:flags=lanczos,"
         "eq=contrast=1.07:saturation=1.06:gamma=0.97,"
         "colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.04,"
         "unsharp=5:5:0.5,vignette=angle=PI/4.5,"
         f"tpad=stop_mode=add:stop_duration={END_CARD}:color=black")
dec = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", SRC, "-vf", grade, "-r", str(FPS),
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-i", mix_wav,
                        "-vf", "noise=alls=4:allf=t,format=yuv420p",
                        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                        "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "6M", "-bufsize", "12M", "-profile:v", "high",
                        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", OUT],
                       stdin=subprocess.PIPE)

fsize = W * H * 3
total_frames = int(round(TOTAL * FPS))
for i in range(total_frames):
    raw = dec.stdout.read(fsize)
    if len(raw) < fsize: break
    t = i / FPS
    img = Image.frombuffer("RGB", (W, H), raw)
    z = punch(t); dx, dy = shake(t)
    if z > 1.001 or dx or dy:
        if dx or dy: z = max(z, 1.03)                      # zoom in a bit so shaking never shows edges
        cw, ch = W / z, H / z
        x0 = min(max((W - cw) / 2 + dx / z, 0), W - cw); y0 = min(max((H - ch) / 2 + dy / z, 0), H - ch)
        img = img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
    frame = np.asarray(img, dtype=np.float32)
    fa = flash(t)
    if fa > 0: frame = frame + (np.array([255, 240, 215], np.float32) - frame) * fa
    ov = os.path.join(OVL, f"o{i:05d}.png")
    if os.path.exists(ov):
        o = np.asarray(Image.open(ov).convert("RGBA"), dtype=np.float32)
        a = o[..., 3:4] / 255.0
        frame = frame * (1 - a) + o[..., :3] * a
    enc.stdin.write(np.clip(frame, 0, 255).astype(np.uint8).tobytes())
    if i % 300 == 0: print(f"frame {i}/{total_frames}", flush=True)

enc.stdin.close(); enc.wait(); dec.wait()
print("done ->", OUT)
