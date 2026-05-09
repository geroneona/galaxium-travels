import { type Page, expect } from '@playwright/test';

const KC_USERNAME = process.env.E2E_KC_USERNAME ?? 'testuser';
const KC_PASSWORD = process.env.E2E_KC_PASSWORD ?? 'testuser';

/**
 * Navigates to the app and completes Keycloak login if the sign-in overlay
 * is shown. Safe to call even when auth is disabled.
 *
 * After this function resolves the main question textarea is guaranteed to
 * be visible.
 */
export async function loginIfNeeded(page: Page, interactionDelay: number = 0): Promise<void> {
  await page.goto('/', { waitUntil: 'domcontentloaded' });

  const signInBtn = page.getByRole('button', { name: 'Sign in' });
  const textarea = page.getByPlaceholder(/Ask a question/i);

  const authRequired = await Promise.race([
    expect(signInBtn).toBeVisible({ timeout: 10_000 }).then(() => true).catch(() => false),
    expect(textarea).toBeVisible({ timeout: 10_000 }).then(() => false).catch(() => false),
  ]);

  if (!authRequired) {
    return;
  }

  if (!KC_USERNAME || !KC_PASSWORD) {
    throw new Error(
      'Login overlay is visible but E2E_KC_USERNAME / E2E_KC_PASSWORD are not set.',
    );
  }
  if (interactionDelay > 0) await page.waitForTimeout(interactionDelay);
  await signInBtn.click(); if (interactionDelay > 0) await page.waitForTimeout(interactionDelay);
  await page.waitForURL(/\/realms\//, { timeout: 20_000 });
  await page.locator('#username').fill(KC_USERNAME); if (interactionDelay > 0) await page.waitForTimeout(interactionDelay);
  await page.locator('#password').fill(KC_PASSWORD); if (interactionDelay > 0) await page.waitForTimeout(interactionDelay);
  await page.locator('#kc-login').click(); if (interactionDelay > 0) await page.waitForTimeout(interactionDelay);
  await page.waitForURL((url) => !url.href.includes('/realms/'), { timeout: 30_000 });
  await expect(textarea).toBeVisible({ timeout: 10_000 });
}
