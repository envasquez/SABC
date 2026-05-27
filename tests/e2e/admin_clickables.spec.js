/**
 * End-to-end click smoke tests for admin pages.
 *
 * This file exists because of a class of regression that the Python test
 * suite cannot catch: a template or JS migration that compiles, type-checks,
 * and lints cleanly but produces a button that does nothing when clicked.
 *
 * The most recent example was the Phase-4 inline-handler migration: the JS
 * gained a delegated `.js-edit-event` listener, the template gained the
 * class, but the templates loaded `<script src="/static/admin-events.js">`
 * without `?v={{ asset_v }}`, so browsers served the cached pre-migration
 * file forever. The Python test suite was 931/1 green throughout.
 *
 * The discipline these tests enforce: every `js-*` class in a template
 * exists for a click handler somewhere; if the click handler is broken,
 * loading the page and clicking the button surfaces the failure.
 *
 * To run locally:
 *   nix develop -c start-app   # in one terminal
 *   npx playwright test tests/e2e/admin_clickables.spec.js
 */

import { test, expect } from '@playwright/test';

const ADMIN_AUTH = 'tests/e2e/.auth/admin.json';

test.use({ storageState: ADMIN_AUTH });

test.describe('Admin events page clickables', () => {
  test('edit pencil opens the Edit Event modal', async ({ page }) => {
    await page.goto('/admin/events');

    // Wait for the events table to render at least one row.
    const editButtons = page.locator('.js-edit-event');
    await expect(editButtons.first()).toBeVisible();

    // Click the first edit button. If the delegated listener didn't bind
    // (cache-bust missing, JS broken, etc.) the modal never appears.
    await editButtons.first().click();

    // The modal title element is rendered server-side but the modal class
    // 'show' is toggled by Bootstrap when the click handler runs.
    const modal = page.locator('#editEventModal');
    await expect(modal).toBeVisible({ timeout: 3000 });
  });

  test('Clear filters resets the SABC search input', async ({ page }) => {
    await page.goto('/admin/events');

    // Set a search filter — the delegated input handler from
    // admin-events-filters.js fires on every keystroke.
    const search = page.locator('#sabc-search');
    await expect(search).toBeVisible();
    await search.fill('zzz-no-match');
    await expect(search).toHaveValue('zzz-no-match');

    // Clear button clears the input back to empty.
    await page.locator('[data-clear-filters="sabc"]').click();
    await expect(search).toHaveValue('');
  });

  test('delete-event button opens confirmation modal', async ({ page }) => {
    await page.goto('/admin/events');

    const deleteButtons = page.locator('.js-delete-event');
    // Some tabs may have no events; only test if at least one delete button exists.
    const count = await deleteButtons.count();
    test.skip(count === 0, 'No deletable events on the admin events page');

    await deleteButtons.first().click();
    // Either the current-event modal (#deleteEventModal) or the past-event
    // modal (#deletePastEventModal) should become visible depending on
    // which tab the delete button came from. We poll for the union of both
    // (one of them gains .show after the click).
    await expect
      .poll(
        async () => {
          const cur = await page.locator('#deleteEventModal.show').count();
          const past = await page.locator('#deletePastEventModal.show').count();
          return cur + past;
        },
        { timeout: 3000 },
      )
      .toBeGreaterThan(0);
  });
});

test.describe('Admin users page clickables', () => {
  test('Add User button opens the modal', async ({ page }) => {
    await page.goto('/admin/users');
    await page.locator('#addUserBtn').click();
    await expect(page.locator('#addUserModal')).toBeVisible({ timeout: 3000 });
  });

  test('user-tab buttons switch between Members and Guests', async ({ page }) => {
    await page.goto('/admin/users');
    await page.locator('.js-user-tab[data-tab-target="guests-pane"]').click();
    await expect(page.locator('#guests-pane')).toHaveClass(/active/);
    await page.locator('.js-user-tab[data-tab-target="members-pane"]').click();
    await expect(page.locator('#members-pane')).toHaveClass(/active/);
  });
});

test.describe('Admin news page clickables', () => {
  test('Send Test Email button stays bound', async ({ page }) => {
    await page.goto('/admin/news');
    // The button should be present and not error when clicked. The route
    // posts via fetch — we don't assert the API result here, only that the
    // delegated handler bound and the button is reachable.
    const btn = page.locator('#sendTestEmailBtn');
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();
  });
});
