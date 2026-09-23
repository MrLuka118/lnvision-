// Targeted interaction flows: forms, dialogs, HTMX swaps, the client gallery.
// Each flow reports PASS/FAIL plus console errors. Creates and removes its own test data.
// Usage: node scripts/ui_flows.mjs [flow-names]
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');
const BASE = process.env.BASE_URL || 'http://localhost:8000';
const GALLERY = '/g/ShccpVTsuS2Y3WknINeQnfnaErqJ4LpCswklRp4ZI2w/';
const only = process.argv[2]?.split(',');

const browser = await chromium.launch({ channel: process.env.PW_CHANNEL || 'chrome' });
const results = [];

async function context(auth, viewport = { width: 1440, height: 900 }) {
  const ctx = await browser.newContext({ viewport, colorScheme: 'dark' });
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

async function flow(name, auth, fn, viewport) {
  if (only && !only.includes(name)) return;
  const ctx = await context(auth, viewport);
  const page = await ctx.newPage();
  const errors = [];
  page.on('console', (m) => m.type() === 'error' && errors.push(m.text()));
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`));
  page.on('response', (r) => r.status() >= 400 && errors.push(`${r.status()} ${r.request().method()} ${r.url().replace(BASE, '')}`));
  const checks = [];
  const check = (label, ok, detail = '') => checks.push({ label, ok: !!ok, detail });
  try {
    await fn(page, check);
  } catch (e) {
    checks.push({ label: 'exception', ok: false, detail: e.message.split('\n')[0] });
  }
  results.push({ name, checks, errors: [...new Set(errors)] });
  await page.screenshot({ path: `screenshots/flows/${name}.png` }).catch(() => {});
  await ctx.close();
}

const visible = (page, sel) => page.locator(sel).first().isVisible().catch(() => false);
const text = (page, sel) => page.locator(sel).first().innerText().catch(() => '');
const dialogOpen = (page, id) => page.evaluate((id) => document.getElementById(id)?.open ?? false, id);

import fs from 'fs';
fs.mkdirSync('screenshots/flows', { recursive: true });

await flow('account-menu', true, async (page, check) => {
  await page.goto(`${BASE}/`);
  await page.click('.account-button');
  check('desktop popover opens', await page.evaluate(() => document.querySelector('#account-menu').matches(':popover-open')));
  await page.keyboard.press('Escape');
  check('Esc closes popover', !(await page.evaluate(() => document.querySelector('#account-menu').matches(':popover-open'))));
  await page.click('.account-button');
  const before = await page.evaluate(() => document.documentElement.dataset.theme || '');
  const light = page.locator('#account-menu input[value="light"], #account-menu [value="light"]').first();
  if (await light.count()) {
    await light.check({ force: true });
    await page.waitForTimeout(200);
    const after = await page.evaluate(() => document.documentElement.dataset.theme || '');
    check('theme switch changes theme', after !== before, `${before} -> ${after}`);
    await page.locator('#account-menu [value="dark"]').first().check({ force: true });
  } else check('theme switch present', false);
});

await flow('account-fab-mobile', true, async (page, check) => {
  await page.goto(`${BASE}/`);
  await page.click('.account-fab-button');
  await page.waitForTimeout(300);
  check('fab opens', await visible(page, '#account-fab-panel'));
  await page.mouse.click(200, 500);
  await page.waitForTimeout(300);
  check('click outside closes', !(await visible(page, '#account-fab-panel')));
  const tab = page.locator('.app-tabbar .tab', { hasText: 'Stranke' });
  await tab.click();
  await page.waitForURL('**/stranke/');
  check('tab bar navigates', page.url().endsWith('/stranke/'));
}, { width: 390, height: 844 });

await flow('client-search', true, async (page, check) => {
  await page.goto(`${BASE}/stranke/`);
  const count = () => page.locator('#client-results a[href*="/stranke/"]').count();
  const before = await count();
  await page.fill('#client-search', 'Novak');
  await page.waitForTimeout(900);
  const after = await count();
  check('search filters results', after > 0 && after < before, `${before} -> ${after}`);
  await page.fill('#client-search', 'zzzxxq');
  await page.waitForTimeout(900);
  check('empty search shows empty state', (await text(page, '#client-results')).trim().length > 0, (await text(page, '#client-results')).slice(0, 80));
  check('url reflects query', page.url().includes('q='), page.url());
});

await flow('client-crud', true, async (page, check) => {
  await page.goto(`${BASE}/stranke/nova/`);
  await page.locator('main form button[type="submit"], main form button:not([type])').last().click();
  await page.waitForLoadState('networkidle');
  check('empty submit shows errors', await page.locator('.field-error, .errorlist, [aria-invalid="true"], .form-errors').count() > 0 || (await page.evaluate(() => [...document.querySelectorAll('input')].some((i) => !i.validity.valid))), page.url());
  const name = page.locator('input[name="name"], input[name="first_name"]').first();
  await name.fill('UI Test Stranka');
  const email = page.locator('input[name="email"]').first();
  if (await email.count()) await email.fill('ui-test@example.si');
  await Promise.all([page.waitForLoadState('networkidle'), page.locator('main form button[type="submit"], main form button:not([type])').last().click()]);
  check('create redirects to detail', /\/stranke\/\d+\/$/.test(page.url()), page.url());
  check('success message shown', await page.locator('.toast, .message, [role="status"]').count() > 0);
  const detail = page.url();
  await page.goto(`${detail}izbrisi/`);
  check('delete confirm page exists', page.url().endsWith('/izbrisi/'));
  await Promise.all([page.waitForLoadState('networkidle'), page.locator('main form button').last().click()]);
  check('delete redirects to list', page.url().endsWith('/stranke/'), page.url());
});

await flow('shoot-status', true, async (page, check) => {
  await page.goto(`${BASE}/fotografiranja/162/`);
  const current = () => page.locator('.pipeline-step[aria-current="step"]').innerText().catch(() => '');
  const before = await current();
  await page.locator('.pipeline-step', { hasText: 'Potrjeno' }).click();
  await page.waitForTimeout(1000);
  const after = await current();
  check('status step advances via HTMX', after.includes('Potrjeno'), `${before} -> ${after}`);
  check('status change gives feedback', await page.locator('.toast, [role="status"], .message').count() > 0);
  await page.locator('.pipeline-step', { hasText: 'Povpraševanje' }).click();
  await page.waitForTimeout(1000);
  check('status reverts', (await current()).includes('Povpraševanje'));
  let confirmed = false;
  page.once('dialog', (d) => { confirmed = true; d.dismiss(); });
  const cancel = page.locator('button', { hasText: 'Odpovej fotografiranje' });
  check('cancel is a 44px target', ((await cancel.boundingBox())?.height ?? 0) >= 44);
});

await flow('calendar', true, async (page, check) => {
  await page.goto(`${BASE}/koledar/`, { waitUntil: 'networkidle' });
  const title = () => text(page, '#cal-title');
  const t0 = await title();
  await page.click('[data-cal="next"]');
  await page.waitForTimeout(500);
  check('next changes period', (await title()) !== t0, `${t0} -> ${await title()}`);
  await page.click('[data-cal="today"]');
  await page.waitForTimeout(500);
  check('today returns', (await title()) === t0);
  await page.locator('.segmented label, .segmented button, [name="cal-view"]').filter({ hasText: 'Teden' }).first().click().catch(async () => page.locator('text=Teden').first().click());
  await page.waitForTimeout(500);
  check('week view switch', (await page.evaluate(() => document.querySelector('input[name="cal-view"]:checked')?.value)) === 'timeGridWeek');
  await page.locator('text=Mesec').first().click();
  await page.waitForTimeout(500);
  const ev = page.locator('.fc-event, [data-event-id], .cal-event').first();
  await ev.click();
  await page.waitForTimeout(900);
  const popOpen = await page.evaluate(() => document.getElementById('event-popover')?.matches(':popover-open') || document.getElementById('event-dialog')?.open);
  check('clicking event shows details', popOpen || page.url().includes('/fotografiranja/'), page.url());
  await page.keyboard.press('Escape');
  await page.goto(`${BASE}/koledar/`, { waitUntil: 'networkidle' });
  await page.click('[data-cal="new"]');
  await page.waitForTimeout(900);
  check('new event dialog opens', await dialogOpen(page, 'event-dialog'));
  check('dialog has form', await page.locator('#event-dialog-body form').count() > 0);
  const submit = page.locator('#event-dialog-body form button[type="submit"], #event-dialog-body form button:not([type])').last();
  await submit.click();
  await page.waitForTimeout(900);
  check('empty submit keeps dialog with errors', await dialogOpen(page, 'event-dialog'));
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);
  check('Esc closes dialog', !(await dialogOpen(page, 'event-dialog')));
  await page.locator('button', { hasText: 'Naroči se' }).click();
  await page.waitForTimeout(300);
  check('subscribe dialog opens', await dialogOpen(page, 'ics-dialog'));
  await page.mouse.click(20, 20);
  await page.waitForTimeout(300);
  check('backdrop click closes dialog', !(await dialogOpen(page, 'ics-dialog')));
});

await flow('gallery-editor', true, async (page, check) => {
  await page.goto(`${BASE}/galerije/5/`, { waitUntil: 'networkidle' });
  await page.locator('button', { hasText: 'Deli' }).click();
  await page.waitForTimeout(300);
  check('share dialog opens', await dialogOpen(page, 'share-dialog'));
  await page.keyboard.press('Escape');
  const menuBtn = page.locator('[popovertarget^="photo-menu-"]').first();
  await menuBtn.hover();
  await menuBtn.click();
  await page.waitForTimeout(300);
  check('photo menu opens', await page.evaluate(() => !!document.querySelector('[id^="photo-menu-"]:popover-open')));
  const del = page.locator('[id^="photo-menu-"]:popover-open button', { hasText: /Izbriši/ });
  check('delete photo asks for confirmation', (await del.getAttribute('hx-confirm').catch(() => null)) !== null);
  await page.keyboard.press('Escape');
  await page.fill('input[name="title"]', 'UI test poglavje');
  await page.locator('button', { hasText: 'Dodaj' }).click();
  await page.waitForTimeout(1000);
  check('add section appears', (await page.content()).includes('UI test poglavje'));
  // Clean up through the confirmation dialog (plain form with data-confirm).
  const remove = page.locator('section.grid', { has: page.locator('h2', { hasText: 'UI test poglavje' }) }).locator('form[data-confirm] button').first();
  await remove.click();
  await page.waitForTimeout(300);
  check('remove section asks first', await dialogOpen(page, 'confirm-dialog'));
  await Promise.all([page.waitForLoadState('networkidle'), page.locator('#confirm-dialog [data-confirm-ok]').click()]);
  await page.waitForTimeout(500);
  check('section removed after confirming', !(await page.content()).includes('UI test poglavje'));
});

await flow('client-gallery', false, async (page, check) => {
  await page.goto(`${BASE}${GALLERY}`, { waitUntil: 'networkidle' });
  const count = () => text(page, '[data-favorite-count]');
  const c0 = await count();
  await page.locator('[data-heart]').first().click();
  await page.waitForTimeout(600);
  const identify = await dialogOpen(page, 'g-identify');
  if (identify) {
    await page.fill('#g-name', 'UI Test');
    await page.locator('#g-identify button[type="submit"], #g-identify form button').last().click();
    await page.waitForTimeout(800);
  }
  const c1 = await count();
  check('heart toggles favourite', c1 !== c0, `${c0} -> ${c1} (identify dialog: ${identify})`);
  await page.locator('[data-heart]').first().click();
  await page.waitForTimeout(600);
  check('heart untoggles', (await count()) === c0, `${await count()}`);
  await page.locator('.g-tile a, [data-pswp-width]').first().click();
  await page.waitForTimeout(800);
  check('lightbox opens', await visible(page, '.pswp'));
  await page.keyboard.press('ArrowRight');
  await page.waitForTimeout(400);
  await page.keyboard.press('Escape');
  await page.waitForTimeout(600);
  check('lightbox closes', !(await visible(page, '.pswp--open')));
  await page.locator('button', { hasText: 'Prenesi vse' }).click();
  await page.waitForTimeout(300);
  check('download dialog opens', await dialogOpen(page, 'g-zip'));
  await page.keyboard.press('Escape');
  await page.locator('[data-show-favorites]').click();
  await page.waitForTimeout(400);
  check('favourites filter toggles', (await page.locator('[data-show-favorites]').getAttribute('aria-pressed')) === 'true');
});

await flow('client-gallery-mobile', false, async (page, check) => {
  await page.goto(`${BASE}${GALLERY}`, { waitUntil: 'networkidle' });
  await page.locator('.g-tile a, [data-pswp-width]').first().tap().catch(() => page.locator('[data-pswp-width]').first().click());
  await page.waitForTimeout(800);
  check('lightbox opens on tap', await visible(page, '.pswp'));
}, { width: 390, height: 844 });

await flow('portfolio-inquiry', false, async (page, check) => {
  await page.goto(`${BASE}/p/studio-svetloba/`, { waitUntil: 'networkidle' });
  const form = page.locator('form[action*="povprasevanje"], form[hx-post*="povprasevanje"]').first();
  await form.locator('button').last().click();
  await page.waitForTimeout(800);
  check('empty inquiry blocked or shows errors', page.url().endsWith('/studio-svetloba/') || (await page.locator('.errorlist, .field-error').count()) > 0, page.url());
  await form.locator('input[name="name"]').fill('UI Test');
  await form.locator('input[name="email"]').fill('ui-test@example.si');
  await form.locator('textarea').first().fill('Test povpraševanja iz UI pregleda.');
  await page.waitForTimeout(3500); // the form rejects submissions faster than 3 s (spam guard)
  await form.locator('button').last().click();
  await page.waitForTimeout(1500);
  check('inquiry shows thank-you', await page.locator('.pf-form[role="status"]').count() > 0, page.url());
  check('no raw 405/500 page', !/405|500|Server Error/.test(await page.title()), await page.title());
});

await flow('settings-save', true, async (page, check) => {
  await page.goto(`${BASE}/galerije/5/nastavitve/`);
  await Promise.all([page.waitForLoadState('networkidle'), page.locator('button', { hasText: 'Shrani nastavitve' }).click()]);
  check('gallery settings save gives feedback', await page.locator('.toast, [role="status"], .message').count() > 0, page.url());
  await page.goto(`${BASE}/nastavitve/studio/`);
  await Promise.all([page.waitForLoadState('networkidle'), page.locator('main form button', { hasText: 'Shrani' }).last().click()]);
  check('studio settings save gives feedback', await page.locator('.toast, [role="status"], .message').count() > 0, page.url());
});

await browser.close();
let fails = 0;
for (const r of results) {
  const bad = r.checks.filter((c) => !c.ok);
  fails += bad.length;
  console.log(`${bad.length ? 'FAIL' : 'PASS'} ${r.name}`);
  for (const c of r.checks) if (!c.ok || process.env.VERBOSE) console.log(`   ${c.ok ? 'ok ' : 'XX '} ${c.label} ${c.detail}`);
  if (r.errors.length) console.log(`   console: ${r.errors.join(' | ').slice(0, 300)}`);
}
process.exitCode = fails ? 1 : 0;
