/**
 * E2E test: authenticate (if Keycloak is configured), send a weather forecast
 * query and verify a non-error response is returned.
 *
 * Environment variables:
 *   E2E_BASE_URL      – app URL, defaults to http://localhost:5173
 *   E2E_KC_USERNAME   – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD   – Keycloak password (required when auth is enabled)
 */
import { test, expect } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

test('send weather forecast query and receive a response', async ({ page }) => {
  await loginIfNeeded(page);

  // ── Send the query ─────────────────────────────────────────────────────────
  const textarea = page.getByPlaceholder(/Send a message to your agent/i);
  await expect(textarea).toBeVisible({ timeout: 10_000 });
  await textarea.fill('weather forecast for tomorrow in Prague please');

  await page.getByRole('button', { name: 'Send message' }).click();

  // ── Wait for and verify the response ──────────────────────────────────────
  const answerBubble = page.locator('[data-testid="answer-bubble"]').first();

  await expect(answerBubble).toBeVisible({ timeout: 60_000 });

  const responseText = (await answerBubble.textContent()) ?? '';
  expect(responseText.trim().length, 'Expected a non-empty response').toBeGreaterThan(0);
  expect(responseText, 'Response should not contain a technical error').not.toMatch(/error|technical issue|unable/i);

  if (process.env.PAUSE) await page.pause();
});
