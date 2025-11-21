# End-to-End Testing with Playwright

This document explains how to set up and run end-to-end (E2E) tests for the SABC application using Playwright.

## Why E2E Tests?

Backend tests (pytest) are great, but they **cannot test JavaScript interactions**:
- ❌ Cannot verify dropdown population
- ❌ Cannot test event handlers (onclick, onchange)
- ❌ Cannot verify browser console errors
- ❌ Cannot test mobile browser compatibility

**End-to-end tests solve this** by running a real browser and simulating user interactions.

## Critical Test Cases Covered

### 1. **Non-Admin Member Poll Voting** (CRITICAL)
Tests the bug fix for non-admin members unable to vote:
- Verifies `updateRampsNonAdmin{{ poll.id }}()` function exists
- Tests lake dropdown population on page load
- Tests ramp dropdown population when lake is selected
- Verifies full voting flow (lake → ramp → times → submit)
- Checks browser console for debug messages

### 2. **Admin Poll Voting**
Tests both admin voting interfaces:
- "Your Vote" tab (admin's own vote)
- "Cast Vote For Member" tab (proxy voting)
- Verifies both JavaScript functions exist

### 3. **Mobile Browser Compatibility**
Tests on emulated mobile devices:
- iPhone 12 (Mobile Safari)
- Pixel 5 (Mobile Chrome)
- Verifies dropdown interactions work on touch devices

### 4. **Regression Tests**
Prevents the bug from happening again:
- Verifies non-admin functions are defined for tournament polls
- Checks page source for function definitions

## Setup

### 1. Install Playwright

```bash
npm init playwright@latest
```

This will:
- Install Playwright and browsers
- Create `playwright.config.js`
- Add scripts to `package.json`

### 2. Install Browsers

```bash
npx playwright install
```

This downloads Chromium, Firefox, and WebKit.

### 3. Configure Test Users

Create a `.env.test` file with test user credentials:

```bash
# Test user credentials
TEST_ADMIN_EMAIL=admin@saustinbc.com
TEST_ADMIN_PASSWORD=admin123

TEST_MEMBER_EMAIL=member@saustinbc.com
TEST_MEMBER_PASSWORD=member123
```

**IMPORTANT**: These users must exist in your test database!

### 4. Seed Test Database

```bash
nix develop -c python scripts/seed_test_data.py
```

This creates:
- Test admin user
- Test member user (non-admin)
- Active tournament poll for testing

## Running Tests

### Run All Tests

```bash
npx playwright test
```

### Run Specific Test File

```bash
npx playwright test tests/e2e/poll_voting.spec.js
```

### Run Tests in UI Mode (Interactive)

```bash
npx playwright test --ui
```

This opens a browser where you can:
- Watch tests run in real-time
- Pause and inspect at any point
- See console logs and network requests
- Debug failures

### Run Tests in Headed Mode (See Browser)

```bash
npx playwright test --headed
```

### Run Tests for Specific Browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
npx playwright test --project="Mobile Chrome"
```

### Debug Specific Test

```bash
npx playwright test --debug tests/e2e/poll_voting.spec.js
```

## Test Reports

After running tests, view the HTML report:

```bash
npx playwright show-report
```

This shows:
- ✅ Passed tests
- ❌ Failed tests
- Screenshots of failures
- Videos of failures
- Console logs
- Network requests

## Writing New Tests

### Test Structure

```javascript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Setup before each test
    await page.goto('/polls');
  });

  test('should do something', async ({ page }) => {
    // Test steps
    await page.click('button#submit');

    // Assertions
    await expect(page.locator('.success')).toBeVisible();
  });
});
```

### Common Selectors

```javascript
// By ID
page.locator('#lake_select_nonadmin_12')

// By CSS class
page.locator('.form-select')

// By text content
page.locator('text=Cast Vote')

// By attribute prefix (for dynamic IDs)
page.locator('select[id^="lake_select_nonadmin_"]')

// By role (accessibility)
page.getByRole('button', { name: 'Submit' })

// Combination
page.locator('form button.btn-primary')
```

### Common Actions

```javascript
// Navigation
await page.goto('/polls?tab=tournament');

// Click
await page.click('button#submit');
await page.locator('button').click();

// Fill input
await page.fill('input[name="email"]', 'test@example.com');

// Select dropdown
await page.selectOption('select#lake', { label: 'Lake Buchanan' });
await page.selectOption('select#lake', { index: 1 });
await page.selectOption('select#lake', { value: '3' });

// Type text
await page.type('input[name="comment"]', 'Hello world');

// Wait
await page.waitForTimeout(500); // Time-based (use sparingly!)
await page.waitForSelector('.result'); // Wait for element
await page.waitForURL(/.*\/success.*/); // Wait for URL pattern

// Check visibility
const isVisible = await page.locator('.alert').isVisible();

// Get text
const text = await page.locator('h1').textContent();

// Count elements
const count = await page.locator('.poll-card').count();
```

### Common Assertions

```javascript
// Visibility
await expect(page.locator('.success')).toBeVisible();
await expect(page.locator('.error')).not.toBeVisible();

// Text content
await expect(page.locator('h1')).toHaveText('Polls');
await expect(page.locator('.message')).toContainText('success');

// Attributes
await expect(page.locator('select')).toBeEnabled();
await expect(page.locator('select')).toBeDisabled();
await expect(page.locator('input')).toHaveValue('test');

// Count
await expect(page.locator('.option')).toHaveCount(5);

// URL
await expect(page).toHaveURL(/.*\/polls.*/);

// Custom
expect(await page.locator('.items').count()).toBeGreaterThan(0);
```

### Testing JavaScript Functions

```javascript
test('JavaScript function exists', async ({ page }) => {
  await page.goto('/polls');

  // Execute JavaScript in browser context
  const result = await page.evaluate(() => {
    // This code runs in the browser
    const functionExists = typeof window.updateRampsNonAdmin12 === 'function';
    return { exists: functionExists };
  });

  expect(result.exists).toBe(true);
});
```

### Capturing Console Logs

```javascript
test('console shows debug messages', async ({ page }) => {
  const messages = [];

  page.on('console', msg => {
    if (msg.text().includes('[SABC]')) {
      messages.push(msg.text());
    }
  });

  await page.goto('/polls');
  // ... interact with page ...

  expect(messages.length).toBeGreaterThan(0);
  console.log('Console messages:', messages);
});
```

## CI/CD Integration

### GitHub Actions

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-node@v3
        with:
          node-version: 18

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npx playwright test
        env:
          BASE_URL: http://localhost:8000
          TEST_ADMIN_EMAIL: ${{ secrets.TEST_ADMIN_EMAIL }}
          TEST_ADMIN_PASSWORD: ${{ secrets.TEST_ADMIN_PASSWORD }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
```

## Debugging Tips

### 1. Use UI Mode

```bash
npx playwright test --ui
```

This is the BEST way to debug tests interactively.

### 2. Use Debug Mode

```bash
npx playwright test --debug
```

Opens browser with DevTools and pauses at each step.

### 3. Add Screenshots

```javascript
await page.screenshot({ path: 'screenshot.png' });
await page.screenshot({ path: 'screenshot.png', fullPage: true });
```

### 4. Add Console Logging

```javascript
console.log('Current URL:', page.url());
const text = await page.locator('h1').textContent();
console.log('Page title:', text);
```

### 5. Slow Down Tests

```javascript
test.use({ launchOptions: { slowMo: 1000 } }); // 1 second delay between actions
```

### 6. Keep Browser Open on Failure

```bash
PWDEBUG=1 npx playwright test
```

### 7. Check Test Artifacts

After test failure, check:
- `test-results/` folder for screenshots/videos
- `playwright-report/` for HTML report

## Best Practices

### ✅ DO

- **Use data-testid attributes** for stable selectors
  ```html
  <button data-testid="submit-vote">Cast Vote</button>
  ```
  ```javascript
  await page.locator('[data-testid="submit-vote"]').click();
  ```

- **Wait for elements** before interacting
  ```javascript
  await page.waitForSelector('.results');
  await page.locator('.results').click();
  ```

- **Use accessibility selectors** when possible
  ```javascript
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.getByLabel('Email').fill('test@example.com');
  ```

- **Test error cases** not just happy paths
  ```javascript
  test('shows error when lake not selected', async ({ page }) => {
    await page.click('button[type="submit"]');
    await expect(page.locator('.error')).toContainText('select a lake');
  });
  ```

- **Keep tests independent** - each test should clean up after itself

### ❌ DON'T

- **Don't use fixed timeouts** unless absolutely necessary
  ```javascript
  // ❌ BAD
  await page.waitForTimeout(3000);

  // ✅ GOOD
  await page.waitForSelector('.results');
  ```

- **Don't rely on exact text matches** (use contains instead)
  ```javascript
  // ❌ BAD - breaks if text changes slightly
  await expect(page.locator('h1')).toHaveText('Welcome to Polls Page');

  // ✅ GOOD
  await expect(page.locator('h1')).toContainText('Polls');
  ```

- **Don't test backend logic in E2E tests** - use pytest for that

- **Don't make tests depend on each other** - each should be runnable in isolation

## Maintenance

### Update Browsers

```bash
npx playwright install
```

### Update Playwright

```bash
npm update @playwright/test
npx playwright install
```

### Clean Test Artifacts

```bash
rm -rf test-results/ playwright-report/
```

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check environment variables
- Verify database state
- Check timing issues (add explicit waits)

### Browser Not Found

```bash
npx playwright install
```

### Port Already in Use

Another dev server is running. Stop it:

```bash
lsof -ti:8000 | xargs kill -9
```

### Tests Are Slow

- Use `test.describe.serial()` for tests that must run in order
- Reduce retries: `retries: 0`
- Use `workers: 1` to avoid database conflicts

## Further Reading

- [Playwright Documentation](https://playwright.dev)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Test Selectors](https://playwright.dev/docs/selectors)
- [API Reference](https://playwright.dev/docs/api/class-test)

---

**Questions?** See the example tests in `tests/e2e/poll_voting.spec.js`
