// Renders the animated graphics from overlay.html into transparent PNG frames.
//   node render-overlays.js <outDir>                 -> every frame (30 fps)
//   node render-overlays.js <outDir> 1.5,20,57       -> only these times (for quick previews)
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const FPS = 30, TOTAL = 109.75;
const outDir = path.resolve(process.argv[2] || 'overlay-frames');
const only = process.argv[3] ? process.argv[3].split(',').map(Number) : null;

const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const file = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!file.startsWith(__dirname) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
  fs.createReadStream(file).pipe(res);
});

(async () => {
  await new Promise(r => server.listen(8766, r));
  fs.rmSync(outDir, { recursive: true, force: true });
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
  page.on('pageerror', e => console.error('page error:', e.message));
  page.on('console', m => m.type() === 'error' && console.error('console:', m.text()));
  await page.goto('http://localhost:8766/overlay.html');
  await page.evaluate(() => window.ready);

  const times = only || Array.from({ length: Math.round(TOTAL * FPS) }, (_, i) => i / FPS);
  let saved = 0;
  for (let n = 0; n < times.length; n++) {
    const t = times[n];
    const data = await page.evaluate(t => window.renderAt(t) ? document.getElementById('c').toDataURL('image/png') : null, t);
    if (data) {
      const name = only ? `t${t}.png` : `o${String(n).padStart(5, '0')}.png`;
      fs.writeFileSync(path.join(outDir, name), Buffer.from(data.split(',')[1], 'base64'));
      saved++;
    }
    if (!only && n % 300 === 0) console.log(`overlay ${n}/${times.length}`);
  }
  console.log(`saved ${saved} overlay frames -> ${outDir}`);
  await browser.close(); server.close();
})();
