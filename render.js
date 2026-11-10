// Renders scene.html frame-by-frame and joins the frames into an MP4 with ffmpeg.
// Usage: node render.js [TEXT] [seconds]
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const TEXT = process.argv[2] || 'HASSAN';
const SECONDS = Number(process.argv[3] || 12);
const FPS = 30;
const FRAMES_DIR = path.join(__dirname, 'frames');
const OUT = path.join(__dirname, 'output', '3d-video.mp4');

// 1. Tiny static web server (browsers block ES modules from file://)
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json' };
const server = http.createServer((req, res) => {
  const file = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(__dirname) || !fs.existsSync(file)) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8765, r));
  fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  fs.mkdirSync(FRAMES_DIR, { recursive: true });
  fs.mkdirSync(path.dirname(OUT), { recursive: true });

  // 2. Open the scene in a headless browser with GPU emulation
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(`http://localhost:8765/scene.html?text=${encodeURIComponent(TEXT)}`);
  await page.waitForFunction(() => window.ready);
  await page.evaluate(() => window.ready);

  // 3. Render each frame at an exact time and save it as PNG
  const total = SECONDS * FPS;
  for (let i = 0; i < total; i++) {
    const dataUrl = await page.evaluate(t => { window.renderAt(t); return document.querySelector('canvas').toDataURL('image/png'); }, i / FPS);
    fs.writeFileSync(path.join(FRAMES_DIR, `f${String(i).padStart(5, '0')}.png`), Buffer.from(dataUrl.split(',')[1], 'base64'));
    if (i % 30 === 0) console.log(`frame ${i}/${total}`);
  }
  await browser.close();
  server.close();

  // 4. Join frames into a video
  execSync(`ffmpeg -y -loglevel error -framerate ${FPS} -i "${FRAMES_DIR}/f%05d.png" -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart "${OUT}"`, { stdio: 'inherit' });
  fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  console.log('Done ->', OUT);
})();
