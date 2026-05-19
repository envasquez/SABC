/**
 * Mobile visual-regression coverage for the Bootstrap migration.
 *
 * The desktop baseline (visual-baseline.spec.js) runs at 1280px and never
 * exercises the responsive navbar — the hamburger toggler, the collapsed
 * menu, and the expanded mobile menu only exist below the lg breakpoint.
 * This spec captures those states so navbar CSS can be deleted safely.
 *
 *   Capture baseline:   npx playwright test visual-mobile --update-snapshots
 *   Diff after a change: npx playwright test visual-mobile
 */

import { test, expect, devices } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

test.use({ ...devices['Pixel 5'] });

async function shot(page, name) {
  await expect(page).toHaveScreenshot(`${name}.png`, {
    fullPage: true,
    animations: 'disabled',
    mask: [page.locator('canvas')],
    maxDiffPixelRatio: 0.01,
    timeout: 20000,
  });
}

test('mobile home — navbar collapsed', async ({ page }) => {
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await shot(page, 'mobile-home-navbar-collapsed');
});

test('mobile home — navbar expanded', async ({ page }) => {
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  await page.click('button.navbar-toggler');
  await expect(page.locator('#nav')).toBeVisible();
  await page.waitForTimeout(800); // collapse animation settle
  await shot(page, 'mobile-home-navbar-expanded');
});

test('mobile login', async ({ page }) => {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot(page, 'mobile-login');
});

test('mobile about', async ({ page }) => {
  await page.goto(`${BASE_URL}/about`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  await shot(page, 'mobile-about');
});
