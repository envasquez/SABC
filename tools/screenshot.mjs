// Usage: node tools/screenshot.mjs <role|anon> <url=outfile> [<url=outfile> ...]
// role: anon | member | admin. Logs in once, then screenshots each page full-page.
import { chromium } from 'playwright';

const [role, ...pairs] = process.argv.slice(2);
const CREDS = {
  admin:  { e: 'admin@sabc.com', p: 'admin123' },
  member: { e: 'aaron.bailey@sabc.test', p: 'password123' },
};
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1100 } });
const page = await ctx.newPage();

if (role === 'admin' || role === 'member') {
  const c = CREDS[role];
  await page.goto('http://localhost:8000/');           // set csrf cookie
  await page.goto('http://localhost:8000/login');
  await page.fill('input[name="email"]', c.e);
  await page.fill('input[name="password"]', c.p);
  await Promise.all([
    page.waitForURL(u => !u.pathname.endsWith('/login'), { timeout: 15000 }).catch(() => {}),
    page.click('button[type="submit"]'),
  ]);
}

for (const pair of pairs) {
  const i = pair.lastIndexOf('=');
  const url = pair.slice(0, i), out = pair.slice(i + 1);
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1200);
    await page.screenshot({ path: out, fullPage: true });
    console.log('OK  ' + url + ' -> ' + out);
  } catch (e) {
    console.log('ERR ' + url + ': ' + e.message);
  }
}
await browser.close();
