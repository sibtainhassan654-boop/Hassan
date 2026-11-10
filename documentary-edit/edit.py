"""
Documentary-style edit of the Codex Gigas short.

Steps
  1. Sound design: build a music bed + whooshes, booms, clicks, stamps (numpy),
     and mix it under the original voice-over.
  2. Picture: upscale to 1080x1920, colour grade, vignette, punch-in zooms,
     camera shake, flashes, and the animated graphics from overlay.html.
  3. Encode: film grain, loudness normalised for social media (-14 LUFS).

Usage:  python3 edit.py <source.mp4> <overlay_frames_dir> <output.mp4> [--audio-only]
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
STAMPS = [14.5, 23.75, 76.85, 101.45]
FLASH = [17.4, 38.5, 54.2, 63.9, 78.3]
SHAKE = STAMPS + [54.2, 57.0, 73.0]

# Sound design rules used by trailer / documentary editors:
#   - few hits, only on the biggest story beats
#   - every hit is "built up" by a riser, so it feels earned
#   - no tonal beeps, clicks or squeaks: only low, dark, reverberant sounds
IMPACTS = [15.0, 17.4, 54.2, 57.0, 63.9, 73.0, 78.3, 101.6, 106.35]   # big cinematic hits
RISERS = [(13.2, 15.0), (52.4, 54.2), (62.1, 63.9), (104.6, 106.35)]  # tension build-ups (start, hit)
SOFT_HITS = [5.0, 24.3, 38.5, 85.6, 97.3]                            # smaller sub "thumps"
WHOOSH = [0.1, 8.4, 21.0, 26.4, 66.8, 98.2]                          # soft air for paper cards
STAMP_THUD = STAMPS

# ---------------------------------------------------------------------------
# 1. SOUND DESIGN  (stereo, everything goes through a big hall reverb)
# ---------------------------------------------------------------------------
rng = np.random.default_rng(3)
N = int(TOTAL * SR)
tt = np.arange(N) / SR

def lp(x, k):                            # low-pass (moving average of k samples)
    k = max(1, int(k)); c = np.cumsum(np.concatenate([[0], x]))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([y, np.zeros(len(x) - len(y))])
def lp2(x, k): return lp(lp(x, k), k)    # smoother low-pass
def place(buf, snd, at, gain=1.0):
    i = int(at * SR)
    if i < 0: snd, i = snd[-i:], 0
    if i >= len(buf): return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n] * gain
def env(n, a, d):
    x = np.arange(n) / SR
    return np.minimum(1, x / max(a, 1e-4)) * np.exp(-x / d)

def impact():
    n = int(3.0 * SR); x = np.arange(n) / SR
    sub = np.sin(2 * np.pi * np.cumsum(38 + 14 * np.exp(-x * 4)) / SR) * env(n, .006, .55)   # deep sub, tiny drop
    body = lp2(rng.standard_normal(n), 30) * env(n, .002, .18) * 3                           # dark thud
    crack = (rng.standard_normal(n) - lp(rng.standard_normal(n), 4)) * env(n, .0005, .012) * .35  # short transient
    return sub * 1.0 + body + crack
def soft_hit():
    n = int(1.6 * SR); x = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(46 + 8 * np.exp(-x * 6)) / SR) * env(n, .01, .45) + lp2(rng.standard_normal(n), 40) * env(n, .003, .1) * 6
def riser(dur):
    n = int(dur * SR); x = np.linspace(0, 1, n)
    noise = rng.standard_normal(n)
    out = np.zeros(n); seg = n // 40                  # filter opens up over time (dark -> airy)
    for i in range(40):
        a, b = i * seg, (i + 1) * seg if i < 39 else n
        out[a:b] = lp(noise, 120 - 110 * (i / 39) ** 1.5)[a:b]
    tone = sum(np.sin(2 * np.pi * f * (1 + .03 * x) * np.arange(n) / SR) for f in (73.4, 110.0, 146.8)) * .08
    return (out * 4 + tone) * x ** 2.5
def whoosh(dur=.9):
    n = int(dur * SR); x = np.linspace(0, 1, n); noise = rng.standard_normal(n)
    band = lp(noise, 14) - lp(noise, 60)              # band-pass "air"
    return band * np.sin(np.pi * x) ** 3 * 3.5
def thud():
    n = int(.8 * SR); x = np.arange(n) / SR
    return lp2(rng.standard_normal(n), 25) * env(n, .001, .05) * 10 + np.sin(2 * np.pi * 62 * x) * env(n, .002, .12) * .6

dry = np.zeros(N); send = np.zeros(N)                # send = amount going into reverb
for t0 in IMPACTS:  s = impact();  place(dry, s, t0 - .01, .9); place(send, s, t0 - .01, .3)
for a, b in RISERS: s = riser(b - a); place(dry, s, a, .35);  place(send, s, a, .25)
for t0 in SOFT_HITS: s = soft_hit(); place(dry, s, t0 - .01, .55); place(send, s, t0, .3)
for t0 in WHOOSH:   s = whoosh();  place(dry, s, t0 - .35, .25); place(send, s, t0 - .35, .3)
for t0 in STAMP_THUD: s = thud(); place(dry, s, t0 + .1, .7); place(send, s, t0 + .1, .4)

# music bed: soft dark pad (sines + breathy noise), very low, smeared by reverb
pad = np.zeros(N)
for f, g in [(36.71, .5), (73.42, .45), (110.0, .2), (174.61, .1)]:
    for det in (-.35, .35):
        pad += g * (.55 + .45 * np.sin(2 * np.pi * (.03 + f / 15000) * tt + f)) * np.sin(2 * np.pi * (f + det) * tt)
pad += lp2(rng.standard_normal(N), 90) * 6 * (.6 + .4 * np.sin(2 * np.pi * .05 * tt))
# low pulse during the legend (felt more than heard)
beat = lp2(rng.standard_normal(int(.3 * SR)), 60) * env(int(.3 * SR), .004, .06) * 25
for s0 in np.arange(64.3, 78.0, 1.0): place(pad, beat, s0); place(pad, beat, s0 + .24, .55)
lvl = np.interp(tt, [0, 2, 63, 64, 78, 79, 98, 103, SRC_DUR, SRC_DUR + .5, TOTAL - 1.2, TOTAL],
                    [0, .7, .7, 1, 1, .65, .65, .9, .9, 1.1, 1.1, 0])
pad *= lvl / np.max(np.abs(pad)) * .05   # quiet: the original already has music

# stereo hall reverb: convolve with two decaying-noise impulse responses
def reverb_ir(seed, dur=3.2):
    r = np.random.default_rng(seed); n = int(dur * SR); x = np.arange(n) / SR
    ir = r.standard_normal(n) * np.exp(-x / .55)
    ir = lp(ir, 3); ir[:int(.02 * SR)] = 0                 # 20 ms pre-delay
    return ir / np.sqrt(np.sum(ir ** 2))
def conv(x, ir):
    L = 1 << int(np.ceil(np.log2(len(x) + len(ir))))
    return np.fft.irfft(np.fft.rfft(x, L) * np.fft.rfft(ir, L), L)[:len(x)]
wet_in = send + pad * 1.2
wet_in = wet_in - lp2(wet_in, 160)              # keep the bass out of the reverb (no mud)
wetL, wetR = conv(wet_in, reverb_ir(1)), conv(wet_in, reverb_ir(2))
padL = pad + wetL * .5; padR = pad + wetR * .5
fx = dry * .85
musicL = padL + fx + wetL * .45; musicR = padR + fx + wetR * .45

# original voice-over (centre)
voice_wav = os.path.join(WORK, "voice.wav")
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", SRC, "-vn", "-ac", "1", "-ar", str(SR), voice_wav], check=True)
with wave.open(voice_wav) as wf:
    voice = np.frombuffer(wf.readframes(wf.getnframes()), np.int16).astype(np.float64) / 32768
v = np.zeros(N); v[:min(N, len(voice))] = voice[:N]

# duck the bed under the voice (sidechain-style)
spk = lp(np.abs(v), int(.3 * SR)); spk = np.clip(spk / (np.percentile(spk, 90) + 1e-9), 0, 1)
duck = 1 - .4 * spk
L = v + musicL * duck; R = v + musicR * duck
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
L, R = (np.tanh(c / peak * 1.05) / np.tanh(1.05) * .95 for c in (L, R))
mix_wav = os.path.join(WORK, "mix.wav")
with wave.open(mix_wav, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((np.stack([L, R], 1) * 32767).astype(np.int16).tobytes())
print("audio mixed")

# --audio-only: put the new sound on an already rendered video (picture untouched)
if len(sys.argv) > 4 and sys.argv[4] == "--audio-only":
    tmp = OUT + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", OUT, "-i", mix_wav, "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, OUT); print("audio replaced ->", OUT); sys.exit(0)

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
