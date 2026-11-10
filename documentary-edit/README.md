# Codex Gigas — Documentary-Style Edit

Final video: `output/codex-gigas-documentary-edit.mp4` (1080x1920, 30fps, 1:50, -14 LUFS)

## What the edit adds
- **Colour grade**: contrast, warm highlights / cool shadows, vignette, film grain, upscale to 1080p
- **Animated graphics** (`overlay.html`): paper maps (Stockholm, Bohemia), stat counters
  (74.8 kg, 92 cm, ~160 hides, 620 pages, 20–30 years), LEGEND stamp, title card,
  checklist note, marker circles and arrows, chapter cards, case file, missing-pages grid,
  call to action and end card
- **Camera moves**: punch-in zooms on key words, shake on impacts, light flashes
- **Sound design** (cinematic, no cartoon sounds): risers into big moments, deep impacts,
  soft air whooshes, stamp thuds, low pulse in the legend, stereo hall reverb, ducked under the voice

## Rebuild
```bash
npm install
node render-overlays.js /tmp/ovl          # graphics -> transparent PNG frames
python3 edit.py "../The Codex Gigas_ The Giant Medieval Book They Call the Devil's Bible.mp4" /tmp/ovl output/codex-gigas-documentary-edit.mp4
# only rebuild the sound on an existing render:
# python3 edit.py <source.mp4> none output/codex-gigas-documentary-edit.mp4 --audio-only
```
Needs Node.js, Playwright (Chromium), Python 3 with numpy + Pillow, and ffmpeg.
