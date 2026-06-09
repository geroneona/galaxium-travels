/**
 * E2E test: authenticate (if Keycloak is configured), send "Hello", verify a response.
 *
 * Environment variables:
 *   E2E_BASE_URL      – app URL, defaults to http://localhost:5173
 *   E2E_KC_USERNAME   – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD   – Keycloak password (required when auth is enabled)
 */
import { test, expect } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

test('send Hello and receive a response', async ({ page }) => {
  await loginIfNeeded(page);

  // ── Send "Hello" ──────────────────────────────────────────────────────────
  const textarea = page.getByPlaceholder(/Ask a question/i);
  await expect(textarea).toBeVisible({ timeout: 10_000 });
  await textarea.fill('Hello');

  await page.getByRole('button', { name: 'Send' }).click();

  // ── Wait for and verify the response ──────────────────────────────────────
  // The answer bubble appears immediately with a "Thinking…" / "Finalizing…"
  // placeholder while the agent is streaming. We wait until that loading text
  // is gone and the bubble contains a real answer.
  const answerBubble = page.locator('[data-testid="answer-bubble"]').first();

  await expect(answerBubble).toBeVisible({ timeout: 10_000 });

  await expect(answerBubble).not.toContainText(/Thinking…|Finalizing…/, { timeout: 60_000 });

  const responseText = (await answerBubble.textContent()) ?? '';
  expect(responseText.trim().length, 'Expected a non-empty response').toBeGreaterThan(0);

  if (process.env.PAUSE) await page.pause();
});
