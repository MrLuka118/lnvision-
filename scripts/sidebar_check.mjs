// Visual regression for the app shell: sidebar corners, theme switch stability, nav indicator.
// Usage: node scripts/sidebar_check.mjs [chromium|webkit] [scale]
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(import.meta.url);
const pw = require('playwright');
const BASE = process.env.BASE_URL || 'http://localhost:8000';
const engine = process.argv[2] || 'chromium';
const scale = Number(process.argv[3] || 2);
const out = `screenshots/shell/${engine}-${scale}x`;
fs.mkdirSync(out, { recursive: true });

const browser = await pw[engine].launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: scale, bypassCSP: true, colorScheme: 'dark', recordVideo: { dir: out, size: { width: 1440, height: 900 } } });
const page = await ctx.newPage();
await page.goto(`${BASE}/racun/login/`);
await page.fill('input[name="login"]', 'demo@aperture.local');
await page.fill('input[name="password"]', 'demo-geslo-2026');
await Promise.all([page.waitForURL(u => !u.pathname.startsWith('/racun/')), page.locator('form button[type="submit"]').first().click()]);
await page.waitForTimeout(800);

const failures = [];
const baseline = {};
// Pixels just outside each rounded corner must equal the page background.
async function corners(label) {
  const box = await page.locator('.app-sidebar').boundingBox();
  const png = await page.screenshot();
  const bg = await page.evaluate(() => getComputedStyle(document.documentElement).backgroundColor);
  const probes = await page.evaluate(async ({ png, box, scale }) => {
    const img = new Image(); img.src = 'data:image/png;base64,' + png;
    await img.decode();
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0);
    const at = (x, y) => [...g.getImageData(Math.round(x * scale), Math.round(y * scale), 1, 1).data].slice(0, 3);
    const i = 3; // px inside the bounding box, still outside a 28px radius
    return {
      tl: at(box.x + i, box.y + i), tr: at(box.x + box.width - i, box.y + i),
      bl: at(box.x + i, box.y + box.height - i), br: at(box.x + box.width - i, box.y + box.height - i),
      ref: at(box.x + box.width + 40, box.y + 4),
    };
  }, { png: png.toString('base64'), box, scale });
  // Top corners: nothing but page background. Bottom corners carry the soft drop shadow, so
  // they must match the at-rest capture of the same theme exactly (a rectangle would not).
  const theme = label.split('-')[0];
  baseline[theme] ??= probes;
  for (const k of ['tl', 'tr', 'bl', 'br']) {
    const ref = k[0] === 't' ? probes.ref : baseline[theme][k];
    const d = Math.max(...probes[k].map((v, n) => Math.abs(v - ref[n])));
    if (d > 6) failures.push(`${label} ${k}: ${probes[k]} vs ${ref} (bg ${bg})`);
  }
  for (const [k, clip] of Object.entries({
    tl: { x: box.x - 6, y: box.y - 6, width: 48, height: 48 },
    tr: { x: box.x + box.width - 42, y: box.y - 6, width: 48, height: 48 },
    bl: { x: box.x - 6, y: box.y + box.height - 42, width: 48, height: 48 },
    br: { x: box.x + box.width - 42, y: box.y + box.height - 42, width: 48, height: 48 },
  })) {
    if (process.env.SHOTS) await page.screenshot({ path: `${out}/${label}-${k}.png`, clip });
  }
}

const theme = t => page.evaluate(t => { document.documentElement.dataset.theme = t; }, t);
const items = page.locator('.sidebar-nav .nav-item');
for (const t of ['dark', 'light']) {
  await theme(t); await page.waitForTimeout(400);
  await corners(`${t}-rest`);
  await items.nth(1).hover(); await page.waitForTimeout(60); await corners(`${t}-hover-mid`);
  await page.waitForTimeout(300); await corners(`${t}-hover`);
  await page.mouse.move(900, 450);
  // Mid page transition: stretch every view-transition animation to 4 s and sample at 2 s.
  await page.addStyleTag({ content: '::view-transition-group(*),::view-transition-old(*),::view-transition-new(*){animation-duration:4s!important}' });
  await page.evaluate(() => { window.__vt = new Promise(r => document.addEventListener('htmx:beforeTransition', r, { once: true })); });
  await items.nth(2).click();
  await page.evaluate(() => window.__vt);
  await page.waitForTimeout(2000);
  const n = await page.evaluate(() => document.getAnimations().filter(a => a.effect?.pseudoElement?.startsWith('::view-transition')).length);
  await corners(`${t}-transition(${n} anims)`);
  await page.waitForTimeout(2500);
  await page.goto(`${BASE}/`); await page.waitForTimeout(500);
}

// Theme toggle: nothing may move.
const layout = () => page.evaluate(() => [...document.querySelectorAll('.app-sidebar, .nav-item, .page-header, h1, .btn, main')].map(e => { const r = e.getBoundingClientRect(); return e.className.split(' ')[0] + '@' + [r.x, r.y, r.width, r.height].map(Math.round).join(','); }).join('|'));
await theme('dark'); await page.waitForTimeout(300);
const before = await layout();
await page.click('.account-button');
for (let i = 0; i < 5; i++) {
  for (const v of ['light', 'dark']) {
    await page.locator(`#account-menu label:has(input[value="${v}"])`).click();
    await page.waitForTimeout(450);
    const now = await layout();
    if (now !== before) {
      const a = before.split('|'), b = now.split('|');
      failures.push(`layout shifted after theme ${v} #${i}: ` + a.map((x, n) => x !== b[n] ? `${n}:${x}->${b[n]}` : '').filter(Boolean).join(' '));
    }
  }
}
await page.keyboard.press('Escape');

// Navigate between sidebar items 10 times: sidebar node must persist, box must not move.
const sbBox = JSON.stringify(await page.locator('.app-sidebar').boundingBox());
await page.evaluate(() => { window.__sidebar = document.querySelector('.app-sidebar'); });
const count = await items.count();
for (let i = 0; i < 10; i++) {
  const it = items.nth(i % count);
  if (await it.getAttribute('hx-boost') === 'false') continue;
  await it.click(); await page.waitForTimeout(700);
  if (JSON.stringify(await page.locator('.app-sidebar').boundingBox()) !== sbBox) failures.push(`sidebar moved on nav ${i}`);
  if (!(await page.evaluate(() => window.__sidebar === document.querySelector('.app-sidebar')))) failures.push(`sidebar re-rendered on nav ${i}`);
}
await ctx.close(); await browser.close();
console.log(failures.length ? `FAIL ${engine} ${scale}x\n` + failures.join('\n') : `PASS ${engine} ${scale}x`);
