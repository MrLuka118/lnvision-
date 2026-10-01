// UI audit: screenshots every page at 390px and 1440px and records console errors,
// failed requests, horizontal overflow and tap targets under 44px.
// Usage: node scripts/ui_audit.mjs <label>   (writes screenshots/<label>/ and <label>-report.json)
import { createRequire } from 'module';
import fs from 'fs';

const require = createRequire(import.meta.url);
const PW = process.env.PLAYWRIGHT_PATH || 'playwright';
const { chromium } = require(PW);

const BASE = process.env.BASE_URL || 'http://localhost:8000';
const label = process.argv[2] || 'before';
const only = process.argv[3];
const outDir = `screenshots/${label}`;
fs.mkdirSync(outDir, { recursive: true });

const GALLERY_TOKEN = 'ShccpVTsuS2Y3WknINeQnfnaErqJ4LpCswklRp4ZI2w';
const PAGES = {
  public: [
    ['login', '/racun/login/'],
    ['signup', '/racun/signup/'],
    ['password-reset', '/racun/password/reset/'],
    ['client-gallery', `/g/${GALLERY_TOKEN}/`],
    ['portfolio-home', '/p/studio-svetloba/'],
    ['portfolio-category', '/p/studio-svetloba/poroke/'],
    ['portfolio-story', '/p/studio-svetloba/poroke/poroka-bozic-in-mrak/'],
    ['404', '/ne-obstaja/'],
  ],
  app: [
    ['dashboard', '/'],
    ['finance', '/finance/'],
    ['income', '/finance/prihodki/'],
    ['expense', '/finance/stroski/'],
    ['income-new', '/finance/prihodki/nov/'],
    ['expense-new', '/finance/stroski/nov/'],
    ['styleguide', '/stil/'],
    ['settings', '/nastavitve/'],
    ['profile', '/nastavitve/profil/'],
    ['security', '/racun/password/change/'],
    ['email', '/racun/email/'],
    ['recurring', '/finance/ponavljajoci/'],
    ['categories', '/finance/kategorije/'],
    ['settings-studio', '/nastavitve/studio/'],
    ['packages', '/nastavitve/paketi/'],
    ['package-new', '/nastavitve/paketi/nov/'],
    ['package-edit', '/nastavitve/paketi/16/uredi/'],
    ['locations', '/nastavitve/lokacije/'],
    ['location-new', '/nastavitve/lokacije/nova/'],
    ['clients', '/stranke/'],
    ['client-new', '/stranke/nova/'],
    ['client-detail', '/stranke/74/'],
    ['client-edit', '/stranke/74/uredi/'],
    ['client-delete', '/stranke/74/izbrisi/'],
    ['shoots', '/fotografiranja/'],
    ['shoot-new', '/fotografiranja/novo/'],
    ['shoot-detail', '/fotografiranja/162/'],
    ['shoot-edit', '/fotografiranja/162/uredi/'],
    ['calendar', '/koledar/'],
    ['event-new', '/koledar/dogodki/nov/'],
    ['event-detail', '/koledar/dogodki/389/'],
    ['event-edit', '/koledar/dogodki/389/uredi/'],
    ['galleries', '/galerije/'],
    ['gallery-new', '/galerije/nova/'],
    ['gallery-editor', '/galerije/5/'],
    ['gallery-settings', '/galerije/5/nastavitve/'],
    ['portfolio', '/portfolio/'],
    ['portfolio-profile', '/portfolio/profil/'],
    ['portfolio-categories', '/portfolio/kategorije/'],
    ['portfolio-category-new', '/portfolio/kategorije/nova/'],
    ['portfolio-stories', '/portfolio/zgodbe/'],
    ['portfolio-story-new', '/portfolio/zgodbe/nova/'],
    ['portfolio-story-edit', '/portfolio/zgodbe/1/uredi/'],
  ],
};

const VIEWPORTS = { mobile: { width: 390, height: 844, touch: true }, desktop: { width: 1440, height: 900 } };

async function login(context) {
  const page = await context.newPage();
  await page.goto(`${BASE}/racun/login/`);
  await page.fill('input[name="login"]', 'demo@aperture.local');
  await page.fill('input[name="password"]', 'demo-geslo-2026');
  await Promise.all([page.waitForNavigation(), page.locator('form button[type="submit"]').first().click()]);
  await page.close();
}

// Runs in the page: layout problems that are hard to spot on a screenshot.
function inspect() {
  const doc = document.documentElement;
  const overflowX = doc.scrollWidth > window.innerWidth + 1;
  const wide = [];
  if (overflowX) {
    for (const el of document.querySelectorAll('body *')) {
      const r = el.getBoundingClientRect();
      if (r.right > window.innerWidth + 1 && r.width > 0 && getComputedStyle(el).position !== 'fixed') {
        wide.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${[...el.classList].slice(0, 3).join('.')} (${Math.round(r.right)}px)`);
        if (wide.length >= 5) break;
      }
    }
  }
  const small = [];
  for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, [role=button], summary')) {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    if (r.width === 0 || r.height === 0 || s.visibility === 'hidden') continue;
    if (el.closest('p, li p, td') && el.tagName === 'A') continue; // inline text links are exempt
    if (el.matches('.segmented input, label input')) continue; // the label is the target
    if (r.height < 44 || r.width < 24) {
      const name = (el.getAttribute('aria-label') || el.textContent || el.getAttribute('name') || '').trim().replace(/\s+/g, ' ').slice(0, 30);
      small.push(`${el.tagName.toLowerCase()} "${name}" ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
  }
  const imgsNoAlt = [...document.querySelectorAll('img:not([alt])')].length;
  const unlabeled = [...document.querySelectorAll('input:not([type=hidden]):not([type=submit]), select, textarea')].filter(
    (el) => !el.labels?.length && !el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby'),
  ).map((el) => el.name || el.id);
  return { overflowX, wide, smallTargets: small, imgsNoAlt, unlabeled, title: document.title };
}

const browser = await chromium.launch({ channel: process.env.PW_CHANNEL || 'chrome' });
const report = {};
for (const [vpName, vp] of Object.entries(VIEWPORTS)) {
  const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, hasTouch: !!vp.touch, isMobile: !!vp.touch, colorScheme: process.env.THEME || 'dark' });
  await context.addCookies([{name:'theme', value:process.env.THEME || 'dark', url:BASE}]);
  await login(context);
  const anon = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, hasTouch: !!vp.touch, isMobile: !!vp.touch, colorScheme: process.env.THEME || 'dark' });
  for (const [group, pages] of Object.entries(PAGES)) {
    for (const [name, path] of pages) {
      if (only && !only.split(',').includes(name)) continue;
      const ctx = group === 'app' ? context : anon;
      const page = await ctx.newPage();
      const errors = [];
      page.on('console', (m) => m.type() === 'error' && errors.push(`console: ${m.text()}`));
      page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
      page.on('response', (r) => r.status() >= 400 && !r.url().endsWith('/ne-obstaja/') && errors.push(`${r.status()} ${r.url()}`));
      const resp = await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' }).catch((e) => ({ status: () => e.message }));
      // Scroll through so lazy images and scroll-reveal content render before the full-page shot.
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 500) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 120));
        }
        window.scrollTo(0, 0);
      }).catch(() => {});
      await page.waitForTimeout(400);
      const info = await page.evaluate(inspect).catch((e) => ({ error: e.message }));
      await page.screenshot({ path: `${outDir}/${name}-${vpName}.png`, fullPage: true });
      report[`${name}@${vpName}`] = { path, status: resp.status(), url: page.url().replace(BASE, ''), errors, ...info };
      await page.close();
      process.stdout.write('.');
    }
  }
  await context.close();
  await anon.close();
}
await browser.close();
fs.writeFileSync(`${outDir}/report.json`, JSON.stringify(report, null, 2));
console.log(`\nwrote ${outDir}/report.json`);
