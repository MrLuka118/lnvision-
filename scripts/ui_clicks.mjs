// Interaction audit: clicks every non-destructive button on every page (fresh load each time)
// and reports buttons that do nothing, console errors, and broken internal links.
// Usage: node scripts/ui_clicks.mjs [out.json] [page-names]
import { createRequire } from 'module';
import fs from 'fs';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const BASE = process.env.BASE_URL || 'http://localhost:8000';
const out = process.argv[2] || 'screenshots/clicks-report.json';
const only = process.argv[3];

const GALLERY_TOKEN = 'ShccpVTsuS2Y3WknINeQnfnaErqJ4LpCswklRp4ZI2w';
const PAGES = [
  ['dashboard', '/'], ['styleguide', '/stil/'], ['settings', '/nastavitve/'], ['settings-studio', '/nastavitve/studio/'],
  ['packages', '/nastavitve/paketi/'], ['package-edit', '/nastavitve/paketi/16/uredi/'], ['locations', '/nastavitve/lokacije/'],
  ['clients', '/stranke/'], ['client-new', '/stranke/nova/'], ['client-detail', '/stranke/74/'],
  ['shoots', '/fotografiranja/'], ['shoot-new', '/fotografiranja/novo/'], ['shoot-detail', '/fotografiranja/162/'],
  ['calendar', '/koledar/'], ['event-detail', '/koledar/dogodki/389/'], ['event-new', '/koledar/dogodki/nov/'],
  ['galleries', '/galerije/'], ['gallery-new', '/galerije/nova/'], ['gallery-editor', '/galerije/5/'], ['gallery-settings', '/galerije/5/nastavitve/'],
  ['portfolio', '/portfolio/'], ['portfolio-profile', '/portfolio/profil/'], ['portfolio-categories', '/portfolio/kategorije/'],
  ['portfolio-stories', '/portfolio/zgodbe/'], ['portfolio-story-edit', '/portfolio/zgodbe/1/uredi/'], ['portfolio-story-photos', '/portfolio/zgodbe/1/fotografije/'],
  ['client-gallery', `/g/${GALLERY_TOKEN}/`, 'anon'], ['portfolio-home', '/p/studio-svetloba/', 'anon'],
  ['portfolio-story', '/p/studio-svetloba/poroke/poroka-bozic-in-mrak/', 'anon'], ['login', '/racun/login/', 'anon'],
];
// Never click these: they destroy data or end the session.
const DESTRUCTIVE = /izbri|odjav|sign out|delete|odstrani|odpovej|nov naslov|nov-naslov|rotate/i;

const browser = await chromium.launch({ channel: process.env.PW_CHANNEL || 'chrome' });
const results = { pages: {}, links: {} };

async function newCtx(vp, auth) {
  const ctx = await browser.newContext({ viewport: vp, colorScheme: 'dark' });
  if (auth) {
    const p = await ctx.newPage();
    await p.goto(`${BASE}/racun/login/`);
    await p.fill('input[name="login"]', 'demo@aperture.local');
    await p.fill('input[name="password"]', 'demo-geslo-2026');
    await Promise.all([p.waitForNavigation(), p.locator('form button[type="submit"]').first().click()]);
    await p.close();
  }
  return ctx;
}

async function openPage(ctx, path) {
  const page = await ctx.newPage();
  const log = { errors: [], requests: [] };
  page.on('console', (m) => m.type() === 'error' && log.errors.push(m.text()));
  page.on('pageerror', (e) => log.errors.push(`pageerror: ${e.message}`));
  page.on('request', (r) => !/\.(avif|webp|jpg|png|woff2|css|js)(\?|$)/.test(r.url()) && log.requests.push(`${r.method()} ${r.url().replace(BASE, '')}`));
  page.on('response', (r) => r.status() >= 400 && log.errors.push(`${r.status()} ${r.request().method()} ${r.url().replace(BASE, '')}`));
  page.on('dialog', (d) => { log.requests.push(`dialog: ${d.message()}`); d.dismiss(); });
  await page.goto(`${BASE}${path}`, { waitUntil: 'networkidle' });
  await page.evaluate(() => {
    window.__mut = 0;
    new MutationObserver((l) => (window.__mut += l.length)).observe(document.body, { subtree: true, childList: true, attributes: true, characterData: true });
  });
  return { page, log };
}

// Describes clickable controls that act in place (links with real hrefs are checked separately).
function listControls(destructive) {
  const re = new RegExp(destructive, 'i');
  const els = [...document.querySelectorAll('button, [role=button], summary, a[href="#"], a:not([href]), [x-on\\:click], [\\@click], [hx-get], [hx-post]')];
  return els.map((el, i) => {
    const r = el.getBoundingClientRect();
    const name = (el.getAttribute('aria-label') || el.textContent || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 40);
    const form = el.closest('form');
    const submit = el.tagName === 'BUTTON' && (el.type === 'submit') && form;
    return {
      i, name, tag: el.tagName.toLowerCase(),
      visible: r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden',
      disabled: el.disabled || el.getAttribute('aria-disabled') === 'true',
      submit: !!submit, formMethod: submit ? (form.method || 'get') : null,
      destructive: re.test(name) || re.test(el.getAttribute('hx-post') || '') || re.test(form?.action || ''),
    };
  });
}

for (const [vpName, vp] of Object.entries({ desktop: { width: 1440, height: 900 }, mobile: { width: 390, height: 844 } })) {
  const auth = await newCtx(vp, true);
  const anon = await newCtx(vp, false);
  for (const [name, path, who] of PAGES) {
    if (only && !only.split(',').includes(name)) continue;
    const ctx = who === 'anon' ? anon : auth;
    const key = `${name}@${vpName}`;
    const { page, log } = await openPage(ctx, path);
    const controls = await page.evaluate(listControls, DESTRUCTIVE.source);
    const loadErrors = [...log.errors];
    // Link check (desktop only): every internal href must resolve.
    if (vpName === 'desktop') {
      const hrefs = await page.$$eval('a[href]', (as) => as.map((a) => a.getAttribute('href')));
      for (const h of new Set(hrefs)) {
        if (!h.startsWith('/') || h.startsWith('//') || results.links[h] !== undefined) continue;
        const r = await ctx.request.get(`${BASE}${h}`, { maxRedirects: 0 }).catch((e) => ({ status: () => e.message }));
        results.links[h] = { status: r.status(), from: name };
      }
    }
    await page.close();
    const clicks = [];
    for (const c of controls) {
      if (!c.visible || c.disabled) continue;
      if (c.destructive) { clicks.push({ ...c, outcome: 'skipped (destructive)' }); continue; }
      if (c.submit && c.formMethod === 'post') { clicks.push({ ...c, outcome: 'skipped (form submit, tested in flows)' }); continue; }
      const { page: p, log: l } = await openPage(ctx, path);
      l.requests.length = 0;
      const before = p.url();
      let outcome = 'ok';
      try {
        const handle = (await p.$$('button, [role=button], summary, a[href="#"], a:not([href]), [x-on\\:click], [\\@click], [hx-get], [hx-post]'))[c.i];
        await handle.click({ timeout: 2000 });
        await p.waitForTimeout(700);
        const mut = await p.evaluate(() => window.__mut).catch(() => -1);
        const nav = p.url() !== before;
        if (!nav && mut === 0 && l.requests.length === 0) outcome = 'NO EFFECT';
        else outcome = nav ? `navigated ${p.url().replace(BASE, '')}` : `mutations=${mut} req=${l.requests.slice(0, 3).join(',')}`;
      } catch (e) {
        outcome = `CLICK FAILED: ${e.message.split('\n')[0].slice(0, 120)}`;
      }
      clicks.push({ name: c.name, tag: c.tag, outcome, errors: [...l.errors] });
      await p.close();
    }
    results.pages[key] = { loadErrors, clicks };
    process.stdout.write('.');
  }
  await auth.close();
  await anon.close();
}
await browser.close();
fs.writeFileSync(out, JSON.stringify(results, null, 2));
console.log(`\nwrote ${out}`);
