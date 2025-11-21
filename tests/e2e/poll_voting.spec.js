/**
 * End-to-End Tests for Poll Voting
 *
 * These tests verify JavaScript interactions that backend tests cannot catch:
 * - Lake/ramp dropdown population
 * - JavaScript function existence
 * - Event handlers firing correctly
 * - Form validation
 *
 * Run with: npx playwright test
 */

import { test, expect } from '@playwright/test';

// Test configuration
const BASE_URL = process.env.BASE_URL || 'http://localhost:8000';

// Test users (configure these in your test database)
const ADMIN_USER = {
  email: process.env.TEST_ADMIN_EMAIL || 'admin@saustinbc.com',
  password: process.env.TEST_ADMIN_PASSWORD || 'admin123'
};

const MEMBER_USER = {
  email: process.env.TEST_MEMBER_EMAIL || 'member@saustinbc.com',
  password: process.env.TEST_MEMBER_PASSWORD || 'member123'
};

/**
 * Helper: Login as a user
 */
async function login(page, email, password) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');

  // Wait for redirect after login
  await page.waitForURL(/.*\/(home|polls|dashboard).*/);
}

/**
 * Helper: Get poll ID from lake select element
 */
async function getPollId(page, selectorPrefix) {
  const lakeSelect = await page.locator(`select[id^="${selectorPrefix}"]`).first();
  const id = await lakeSelect.getAttribute('id');
  return id.replace(selectorPrefix, '');
}

/**
 * TEST SUITE: Non-Admin Member Tournament Poll Voting
 */
test.describe('Non-Admin Member Tournament Poll Voting', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, MEMBER_USER.email, MEMBER_USER.password);
  });

  test('can see tournament polls page', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);
    await expect(page.locator('h1:has-text("Polls")')).toBeVisible();
  });

  test('JavaScript function updateRampsNonAdmin exists', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Check if the JavaScript function is defined
    const functionExists = await page.evaluate(() => {
      const lakeSelect = document.querySelector('select[id^="lake_select_nonadmin_"]');
      if (!lakeSelect) return { found: false, reason: 'Lake select not found' };

      const pollId = lakeSelect.id.replace('lake_select_nonadmin_', '');
      const functionName = `updateRampsNonAdmin${pollId}`;

      return {
        found: typeof window[functionName] === 'function',
        functionName: functionName,
        pollId: pollId
      };
    });

    expect(functionExists.found).toBe(true);
    console.log(`✅ Function ${functionExists.functionName} exists for poll ${functionExists.pollId}`);
  });

  test('lake dropdown populates on page load', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    await expect(lakeSelect).toBeVisible();

    // Should have more than just the placeholder option
    const lakeOptions = await lakeSelect.locator('option:not([value=""])').count();
    expect(lakeOptions).toBeGreaterThan(0);
    console.log(`✅ Lake dropdown has ${lakeOptions} options`);
  });

  test('selecting lake populates ramp dropdown', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    const rampSelect = page.locator('select[id^="ramp_select_nonadmin_"]').first();

    // Initially, ramp should be disabled
    await expect(rampSelect).toBeDisabled();

    // Select a lake (first available option)
    await lakeSelect.selectOption({ index: 1 });

    // Wait for JavaScript to populate ramps
    await page.waitForTimeout(500);

    // Ramp dropdown should now be enabled
    await expect(rampSelect).toBeEnabled();

    // Should have ramp options
    const rampOptions = await rampSelect.locator('option:not([value=""])').count();
    expect(rampOptions).toBeGreaterThan(0);
    console.log(`✅ Ramp dropdown enabled with ${rampOptions} options`);
  });

  test('can complete full voting flow', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Check if there's an active poll we can vote on
    const hasActiveForm = await page.locator('form[action*="/vote"]').count() > 0;

    if (!hasActiveForm) {
      console.log('⏭️  No active tournament poll to vote on - skipping full voting test');
      test.skip();
      return;
    }

    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    const rampSelect = page.locator('select[id^="ramp_select_nonadmin_"]').first();
    const startTimeSelect = page.locator('select[id^="start_time_nonadmin_"]').first();
    const endTimeSelect = page.locator('select[id^="end_time_nonadmin_"]').first();

    // Select lake
    await lakeSelect.selectOption({ index: 1 });
    await page.waitForTimeout(500);

    // Select ramp
    await rampSelect.selectOption({ index: 1 });

    // Select times (should have defaults, but let's be explicit)
    await startTimeSelect.selectOption('05:00');
    await endTimeSelect.selectOption('15:00');

    // Submit vote
    await page.click('button[type="submit"]:has-text("Cast Vote")');

    // Wait for response
    await page.waitForTimeout(1000);

    // Should see success message or "already voted" message
    const hasSuccess = await page.locator('.alert-success, .toast-success').count() > 0;
    const hasAlreadyVoted = await page.locator('text=/already voted/i').count() > 0;

    expect(hasSuccess || hasAlreadyVoted).toBe(true);
    console.log(`✅ Vote submitted successfully or user has already voted`);
  });

  test('console shows correct debug messages', async ({ page }) => {
    const consoleMessages = [];

    page.on('console', msg => {
      if (msg.text().includes('[SABC]')) {
        consoleMessages.push(msg.text());
      }
    });

    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Wait for DOMContentLoaded
    await page.waitForTimeout(1000);

    // Select a lake
    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    if (await lakeSelect.count() > 0) {
      await lakeSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);
    }

    // Verify we got expected console messages
    expect(consoleMessages.some(msg => msg.includes('DOMContentLoaded fired'))).toBe(true);
    expect(consoleMessages.some(msg => msg.includes('Lakes data loaded'))).toBe(true);
    expect(consoleMessages.some(msg => msg.includes('non-admin lake selects'))).toBe(true);

    console.log('📋 Console messages:');
    consoleMessages.forEach(msg => console.log(`   ${msg}`));
  });
});

/**
 * TEST SUITE: Admin Tournament Poll Voting
 */
test.describe('Admin Tournament Poll Voting', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, ADMIN_USER.email, ADMIN_USER.password);
  });

  test('admin own vote: JavaScript function updateRampsAdminOwn exists', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const functionExists = await page.evaluate(() => {
      const lakeSelect = document.querySelector('select[id^="lake_select_admin_own_"]');
      if (!lakeSelect) return { found: false, reason: 'Admin lake select not found' };

      const pollId = lakeSelect.id.replace('lake_select_admin_own_', '');
      const functionName = `updateRampsAdminOwn${pollId}`;

      return {
        found: typeof window[functionName] === 'function',
        functionName: functionName,
        pollId: pollId
      };
    });

    expect(functionExists.found).toBe(true);
    console.log(`✅ Admin function ${functionExists.functionName} exists`);
  });

  test('admin proxy vote: JavaScript function updateAdminRamps exists', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Click "Cast Vote For Member" tab
    const proxyTab = page.locator('button:has-text("Cast Vote For Member")').first();
    if (await proxyTab.count() > 0) {
      await proxyTab.click();
      await page.waitForTimeout(500);
    }

    const functionExists = await page.evaluate(() => {
      const lakeSelect = document.querySelector('select[id^="admin_lake_select_"]');
      if (!lakeSelect) return { found: false, reason: 'Admin proxy lake select not found' };

      const pollId = lakeSelect.id.replace('admin_lake_select_', '');
      const functionName = `updateAdminRamps${pollId}`;

      return {
        found: typeof window[functionName] === 'function',
        functionName: functionName,
        pollId: pollId
      };
    });

    expect(functionExists.found).toBe(true);
    console.log(`✅ Admin proxy function ${functionExists.functionName} exists`);
  });
});

/**
 * TEST SUITE: Mobile Browser Compatibility
 */
test.describe('Mobile Browser Compatibility', () => {
  test.use({
    // Emulate mobile device
    viewport: { width: 375, height: 667 },
    userAgent: 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
  });

  test.beforeEach(async ({ page }) => {
    await login(page, MEMBER_USER.email, MEMBER_USER.password);
  });

  test('mobile: lake/ramp selection works', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    const rampSelect = page.locator('select[id^="ramp_select_nonadmin_"]').first();

    // Select lake
    await lakeSelect.selectOption({ index: 1 });
    await page.waitForTimeout(500);

    // Ramp should be enabled
    await expect(rampSelect).toBeEnabled();

    const rampOptions = await rampSelect.locator('option:not([value=""])').count();
    expect(rampOptions).toBeGreaterThan(0);

    console.log(`✅ Mobile: Ramp dropdown works with ${rampOptions} options`);
  });
});

/**
 * TEST SUITE: Regression Tests for the Bug Fix
 */
test.describe('Regression: Non-Admin Function Scope Bug', () => {
  test('verifies non-admin functions are in correct Jinja2 block', async ({ page }) => {
    await login(page, MEMBER_USER.email, MEMBER_USER.password);
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Get the page source
    const pageSource = await page.content();

    // Check that non-admin functions are defined for tournament polls
    const hasUpdateRampsNonAdmin = pageSource.includes('window.updateRampsNonAdmin');
    const hasValidateVoteNonAdmin = pageSource.includes('window.validateVoteNonAdmin');

    expect(hasUpdateRampsNonAdmin).toBe(true);
    expect(hasValidateVoteNonAdmin).toBe(true);

    console.log('✅ Non-admin voting functions are defined in page source');
  });
});
