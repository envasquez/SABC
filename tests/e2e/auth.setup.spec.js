/**
 * Auth setup for the visual-regression suite.
 *
 * Logs in once per role and saves the browser storage state to disk so the
 * screenshot tests can reuse it without hitting the login endpoint (which is
 * rate-limited to 5/min). Runs before visual-baseline.spec.js because
 * Playwright executes spec files alphabetically with a single worker.
 */

import { test as setup } from '@playwright/test';
import { mkdirSync } from 'fs';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';
const AUTH_DIR = 'tests/e2e/.auth';

const ADMIN = { email: 'admin@sabc.com', password: 'admin123' };
const MEMBER = { email: 'aaron.bailey@sabc.test', password: 'password123' };

async function authenticate(page, user, file) {
  // Visit a page first so the csrf_token cookie is set; the login form's
  // CSRF field is empty on a cookie-less first request (known app bug).
  await page.goto(`${BASE_URL}/`);
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="email"]', user.email);
  await page.fill('input[name="password"]', user.password);
  await Promise.all([
    page.waitForURL((url) => !url.pathname.endsWith('/login')),
    page.click('button[type="submit"]'),
  ]);
  await page.context().storageState({ path: file });
}

setup('authenticate as admin', async ({ page }) => {
  mkdirSync(AUTH_DIR, { recursive: true });
  await authenticate(page, ADMIN, `${AUTH_DIR}/admin.json`);
});

setup('authenticate as member', async ({ page }) => {
  mkdirSync(AUTH_DIR, { recursive: true });
  await authenticate(page, MEMBER, `${AUTH_DIR}/member.json`);
});
