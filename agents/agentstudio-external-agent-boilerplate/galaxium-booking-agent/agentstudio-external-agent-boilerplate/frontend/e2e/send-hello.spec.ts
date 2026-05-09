/**
 * E2E test: authenticate (if Keycloak is configured), send "Hello" to the
 * CrewAI agent via the shared frontend, and verify a response is returned.
 *
 * Environment variables:
 *   E2E_BASE_URL      – app URL, defaults to http://localhost:5173
 *   E2E_KC_USERNAME   – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD   – Keycloak password (required when auth is enabled)
 */
import { test, expect } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

test('send Hello to the agent and receive a response', async ({ page }) => {
  await loginIfNeeded(page);

  // ── Send "Hello" ──────────────────────────────────────────────────────────
  const textarea = page.getByPlaceholder(/Send a message to your agent/i);
  await expect(textarea).toBeVisible({ timeout: 10_000 });
  await textarea.fill('Hello');

  await page.getByRole('button', { name: 'Send message' }).click();

  // ── Wait for and verify the response ──────────────────────────────────────
  // The answer bubble is rendered only after the agent fully responds
  // (the streaming spinner is a separate element). We just wait for it
  // to appear and contain a non-empty reply.
  const answerBubble = page.locator('[data-testid="answer-bubble"]').first();

  await expect(answerBubble).toBeVisible({ timeout: 60_000 });

  const responseText = (await answerBubble.textContent()) ?? '';
  expect(responseText.trim().length, 'Expected a non-empty response from the CrewAI agent').toBeGreaterThan(0);
  expect(responseText, 'Response should not contain a technical error').not.toMatch(/error|technical issue|unable|Technical problem/i);

  if (process.env.PAUSE) await page.pause();
});
