import { chromium } from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import fs from 'node:fs';
const base=process.env.BASE_URL || 'http://localhost:8000';
const browser=await chromium.launch();
const results=[];
for (const theme of ['dark','light']) {
  const context=await browser.newContext({viewport:{width:1440,height:900}});
  await context.addCookies([{name:'theme',value:theme,url:base}]);
  const page=await context.newPage();
  await page.goto(base+'/racun/login/');
  await page.fill('[name=login]','demo@aperture.local');
  await page.fill('[name=password]','demo-geslo-2026');
  await page.locator('form button[type=submit]').first().click();
  await page.waitForURL(base+'/');
  for (const path of ['/', '/stranke/', '/koledar/', '/galerije/', '/finance/', '/nastavitve/']) {
    await page.goto(base+path,{waitUntil:'networkidle'});
    const {violations}=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21aa']).analyze();
    results.push({theme,path,violations:violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))});
  }
  await context.close();
}
await browser.close();
fs.writeFileSync('screenshots/accessibility.json',JSON.stringify(results,null,2));
for (const r of results) console.log(r.theme,r.path,r.violations.map(v=>v.id));
process.exitCode=results.some(r=>r.violations.length)?1:0;
