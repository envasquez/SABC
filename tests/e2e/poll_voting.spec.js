/**
 * End-to-End Tests for Poll Voting
 *
 * These tests verify JavaScript interactions that backend tests cannot catch:
 * - Lake/ramp dropdown population
 * - PollVotingHandler class initialization
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

  test('PollVotingHandler class is loaded', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Check if the PollVotingHandler class is defined
    const classExists = await page.evaluate(() => {
      return typeof PollVotingHandler === 'function';
    });

    expect(classExists).toBe(true);
    console.log('✅ PollVotingHandler class is loaded');
  });

  test('lake dropdown populates on page load', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();

    // Check if lake select exists (may not exist if no active tournament polls)
    if (await lakeSelect.count() === 0) {
      console.log('⏭️  No tournament poll lake select found - skipping');
      test.skip();
      return;
    }

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

    // Check if lake select exists
    if (await lakeSelect.count() === 0) {
      console.log('⏭️  No tournament poll found - skipping');
      test.skip();
      return;
    }

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

  test('console shows correct initialization messages', async ({ page }) => {
    const consoleMessages = [];

    page.on('console', msg => {
      if (msg.text().includes('[SABC]')) {
        consoleMessages.push(msg.text());
      }
    });

    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Wait for DOMContentLoaded
    await page.waitForTimeout(1000);

    // Select a lake if available
    const lakeSelect = page.locator('select[id^="lake_select_nonadmin_"]').first();
    if (await lakeSelect.count() > 0) {
      await lakeSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);
    }

    // Verify we got expected console messages from the new architecture
    expect(consoleMessages.some(msg => msg.includes('DOMContentLoaded fired'))).toBe(true);
    expect(consoleMessages.some(msg => msg.includes('Lakes data loaded'))).toBe(true);
    expect(consoleMessages.some(msg => msg.includes('Poll voting handler initialized'))).toBe(true);

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

  test('admin own vote: lake dropdown works', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    const lakeSelect = page.locator('select[id^="lake_select_admin_own_"]').first();

    // Check if admin own vote section exists
    if (await lakeSelect.count() === 0) {
      console.log('⏭️  No admin own vote section found - skipping');
      test.skip();
      return;
    }

    const rampSelect = page.locator('select[id^="ramp_select_admin_own_"]').first();

    // Initially, ramp should be disabled
    await expect(rampSelect).toBeDisabled();

    // Select a lake
    await lakeSelect.selectOption({ index: 1 });
    await page.waitForTimeout(500);

    // Ramp dropdown should now be enabled
    await expect(rampSelect).toBeEnabled();

    const rampOptions = await rampSelect.locator('option:not([value=""])').count();
    expect(rampOptions).toBeGreaterThan(0);

    console.log(`✅ Admin own vote: Lake/ramp selection works with ${rampOptions} ramp options`);
  });

  test('admin proxy vote: lake dropdown works', async ({ page }) => {
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Click "Cast Vote For Member" tab
    const proxyTab = page.locator('button:has-text("Cast Vote For Member")').first();
    if (await proxyTab.count() === 0) {
      console.log('⏭️  No proxy vote tab found - skipping');
      test.skip();
      return;
    }

    await proxyTab.click();
    await page.waitForTimeout(500);

    const lakeSelect = page.locator('select[id^="admin_lake_select_"]').first();
    const rampSelect = page.locator('select[id^="admin_ramp_select_"]').first();

    if (await lakeSelect.count() === 0) {
      console.log('⏭️  No admin proxy lake select found - skipping');
      test.skip();
      return;
    }

    // Initially, ramp should be disabled
    await expect(rampSelect).toBeDisabled();

    // Select a lake
    await lakeSelect.selectOption({ index: 1 });
    await page.waitForTimeout(500);

    // Ramp dropdown should now be enabled
    await expect(rampSelect).toBeEnabled();

    const rampOptions = await rampSelect.locator('option:not([value=""])').count();
    expect(rampOptions).toBeGreaterThan(0);

    console.log(`✅ Admin proxy vote: Lake/ramp selection works with ${rampOptions} ramp options`);
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

    // Check if lake select exists
    if (await lakeSelect.count() === 0) {
      console.log('⏭️  No tournament poll found - skipping mobile test');
      test.skip();
      return;
    }

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
 * TEST SUITE: Regression Tests - External JS Architecture
 */
test.describe('Regression: External JS Architecture', () => {
  test('verifies PollVotingHandler class is available globally', async ({ page }) => {
    await login(page, MEMBER_USER.email, MEMBER_USER.password);
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Check that PollVotingHandler class is available
    const classAvailable = await page.evaluate(() => {
      return typeof PollVotingHandler === 'function' &&
             typeof PollVotingHandler.prototype.initialize === 'function' &&
             typeof PollVotingHandler.prototype.handleLakeChange === 'function' &&
             typeof PollVotingHandler.prototype.validateVoteForm === 'function';
    });

    expect(classAvailable).toBe(true);
    console.log('✅ PollVotingHandler class is available with all expected methods');
  });

  test('verifies lakes-data element contains valid JSON', async ({ page }) => {
    await login(page, MEMBER_USER.email, MEMBER_USER.password);
    await page.goto(`${BASE_URL}/polls?tab=tournament`);

    // Check that lakes-data element exists and contains valid JSON
    const lakesDataValid = await page.evaluate(() => {
      const lakesDataElement = document.getElementById('lakes-data');
      if (!lakesDataElement) return { valid: false, reason: 'Element not found' };

      const dataAttr = lakesDataElement.dataset.lakes;
      if (!dataAttr) return { valid: false, reason: 'data-lakes attribute not found' };

      try {
        const lakes = JSON.parse(dataAttr);
        return {
          valid: Array.isArray(lakes),
          count: lakes.length,
          hasStructure: lakes.length > 0 ? ('id' in lakes[0] && 'name' in lakes[0] && 'ramps' in lakes[0]) : true
        };
      } catch (e) {
        return { valid: false, reason: 'JSON parse error: ' + e.message };
      }
    });

    expect(lakesDataValid.valid).toBe(true);
    console.log(`✅ Lakes data is valid JSON with ${lakesDataValid.count} lakes`);
  });
});
