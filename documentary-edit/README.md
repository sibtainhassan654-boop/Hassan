# Codex Gigas — Documentary-Style Edit

Final video: `output/codex-gigas-documentary-edit.mp4` (1080x1920, 30fps, 1:50, -14 LUFS)

## What the edit adds
- **Colour grade**: contrast, warm highlights / cool shadows, vignette, film grain, upscale to 1080p
- **Animated graphics** (`overlay.html`): paper maps (Stockholm, Bohemia), stat counters
  (74.8 kg, 92 cm, ~160 hides, 620 pages, 20–30 years), LEGEND stamp, title card,
  checklist note, marker circles and arrows, chapter cards, case file, missing-pages grid,
  call to action and end card
- **Camera moves**: punch-in zooms on key words, shake on impacts, light flashes
- **Sound design**: dark music bed, heartbeat during the legend, booms, whooshes,
  typewriter and counter clicks, stamp hits, all mixed under the original voice-over

## Rebuild
```bash
npm install
node render-overlays.js /tmp/ovl          # graphics -> transparent PNG frames
python3 edit.py "../The Codex Gigas_ The Giant Medieval Book They Call the Devil's Bible.mp4" /tmp/ovl output/codex-gigas-documentary-edit.mp4
```
Needs Node.js, Playwright (Chromium), Python 3 with numpy + Pillow, and ffmpeg.
