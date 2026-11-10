# Hassan — 3D Video

A 12-second 3D animated video (1280x720, 30fps): a glowing torus knot, neon rings,
orbiting cubes, stars, and floating 3D text, with a camera that flies in and circles around.

Ready video: `output/3d-video.mp4`

## Make it yourself
```bash
npm install                 # installs three.js
node render.js              # makes output/3d-video.mp4 with "HASSAN"
node render.js "SIBTAIN" 15 # your own text, 15 seconds
```
Requires Node.js, ffmpeg, and Playwright (Chromium).

To watch it live in a browser: `npx serve .` and open `scene.html`.

## How it works
1. `scene.html` builds the 3D world with three.js (camera, lights, objects, bloom glow).
2. `renderAt(t)` positions everything for time `t` (in seconds).
3. `render.js` opens the page in a headless browser, calls `renderAt` for every frame,
   saves each frame as a PNG, then ffmpeg joins them into an MP4.
