/**
 * Visual regression baseline for the CSS / Bootstrap-adoption work.
 *
 * Captures full-page screenshots of every major page across the three
 * auth contexts (anonymous / member / admin). The first run writes the
 * baseline; later runs diff against it so the Bootstrap migration can be
 * verified pixel-for-pixel.
 *
 *   Capture baseline:   npx playwright test visual-baseline --update-snapshots
 *   Diff after a change: npx playwright test visual-baseline
 *
 * Charts render to <canvas> (non-deterministic) and are masked.
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

async function shot(page, url, name) {
  await page.goto(`${BASE_URL}${url}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500); // let charts/lazy content settle
  await expect(page).toHaveScreenshot(`${name}.png`, {
    fullPage: true,
    animations: 'disabled',
    mask: [page.locator('canvas')],
    maxDiffPixelRatio: 0.01,
    timeout: 20000,
  });
}

// Fixed viewport so screenshots are stable across runs/machines.
test.use({ viewport: { width: 1280, height: 900 } });

test.describe('anonymous pages', () => {
  const pages = [
    ['/', 'home'],
    ['/login', 'login'],
    ['/register', 'register'],
    ['/about', 'about'],
    ['/bylaws', 'bylaws'],
    ['/roster', 'roster'],
    ['/awards', 'awards'],
    ['/calendar', 'calendar'],
    ['/data', 'data'],
    ['/tournaments/1', 'tournament-results'],
  ];
  for (const [url, name] of pages) {
    test(`anon ${name}`, async ({ page }) => {
      await shot(page, url, `anon-${name}`);
    });
  }
});

test.describe('member pages', () => {
  test.use({ storageState: 'tests/e2e/.auth/member.json' });

  test('member polls (club)', async ({ page }) => {
    await shot(page, '/polls?tab=club&p=1', 'member-polls-club');
  });
  test('member polls (tournament)', async ({ page }) => {
    await shot(page, '/polls?tab=tournament&p=1', 'member-polls-tournament');
  });
});

test.describe('admin pages', () => {
  test.use({ storageState: 'tests/e2e/.auth/admin.json' });

  const pages = [
    ['/admin', 'admin-dashboard'],
    ['/admin/events', 'admin-events'],
    ['/admin/users', 'admin-users'],
    ['/polls?tab=tournament&p=1', 'admin-polls-tournament'],
  ];
  for (const [url, name] of pages) {
    test(`admin ${name}`, async ({ page }) => {
      await shot(page, url, `admin-${name}`);
    });
  }
});
