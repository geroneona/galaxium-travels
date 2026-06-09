/**
 * E2E tests: graceful degradation of the weather agent when the MCP stub
 * server toggles tool endpoints off.
 *
 * Test 1 – tools/call unavailable:
 *   Toggle tools/call off, send a weather query, assert the response degrades
 *   gracefully (no "error", "exception", or raw JSON characters).
 *
 * Test 2 – tools/list unavailable then restored:
 *   Toggle tools/list off, wait 1 minute, assert graceful degradation.
 *   Toggle tools/list back on, wait 1 minute, assert a fully successful
 *   response (no "error"/"exception"/JSON chars AND no "issue"/"problem"/"available").
 *
 * Environment variables:
 *   E2E_BASE_URL            – app URL, defaults to http://localhost:5173
 *   E2E_WEATHER_STUB_URL    – weather stub base URL, defaults to http://localhost:8020
 *   E2E_KC_USERNAME         – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD         – Keycloak password (required when auth is enabled)
 */
import { test, expect } from '@playwright/test';
import type { APIRequestContext, Page } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

const STUB_URL = process.env.E2E_WEATHER_STUB_URL ?? 'http://localhost:8020';
const WEATHER_QUERY = 'weather forecast for tomorrow in Prague please';

async function setStubEndpoint(
  request: APIRequestContext,
  key: 'tools/list' | 'tools/call',
  enabled: boolean,
): Promise<void> {
  const stateResp = await request.get(`${STUB_URL}/state`);
  const currentState = (await stateResp.json()) as Record<string, boolean>;
  if (currentState[key] !== enabled) {
    await request.post(`${STUB_URL}/toggle`, { data: { key }});
  }
}

function assertGracefulDegradationIsOn(responseText: string): void {
  expect(responseText.trim().length, 'Expected a non-empty response').toBeGreaterThan(0);
  expect(responseText, 'Response should not mention "error"').not.toMatch(/error/i);
  expect(responseText, 'Response should not mention "exception"').not.toMatch(/exception/i);
  expect(responseText, 'Response should not contain stringified JSON characters').not.toMatch(/[{}\[\]]/);
}
function assertGracefulDegradationIsOff(responseText: string): void {
  assertGracefulDegradationIsOn(responseText)
    expect(responseText, 'Recovered response should not mention "issue"').not.toMatch(/issue/i);
    expect(responseText, 'Recovered response should not mention "problem"').not.toMatch(/problem/i);
    expect(responseText, 'Recovered response should not mention "available"').not.toMatch(/available/i);
}

async function sendQueryAndGetLatestResponse(page: Page): Promise<string> {
  const existingBubbleCount = await page.locator('[data-testid="answer-bubble"]').count();

  const textarea = page.getByPlaceholder(/Send a message to your agent/i);
  await expect(textarea).toBeVisible({ timeout: 10_000 });
  await textarea.fill(WEATHER_QUERY);
  await page.getByRole('button', { name: 'Send message' }).click();

  const answerBubbles = page.locator('[data-testid="answer-bubble"]');
  await expect(answerBubbles).toHaveCount(existingBubbleCount + 1, { timeout: 60_000 });

  return (await answerBubbles.last().textContent()) ?? '';
}

test('graceful degradation when tools/call is unavailable', async ({ page, request }) => {
  await setStubEndpoint(request, 'tools/call', false);
  await setStubEndpoint(request, 'tools/list', true);

  try {
    await loginIfNeeded(page);
    const responseText = await sendQueryAndGetLatestResponse(page);
    assertGracefulDegradationIsOn(responseText);
  } finally {
    await setStubEndpoint(request, 'tools/call', true);
  }

    await setStubEndpoint(request, 'tools/call', true);
    await page.waitForTimeout(10_000);
    const responseText2 = await sendQueryAndGetLatestResponse(page);
    assertGracefulDegradationIsOn(responseText2);

    await page.waitForTimeout(51_000);
    const responseText3 = await sendQueryAndGetLatestResponse(page);
    assertGracefulDegradationIsOff(responseText3);

  if (process.env.PAUSE) await page.pause();
});

test('graceful degradation and recovery when tools/list is toggled off then on', async ({ page, request }) => {
  await setStubEndpoint(request, 'tools/call', true);
  await setStubEndpoint(request, 'tools/list', false);

  try {
    await loginIfNeeded(page);
    // ── Degraded phase ──────────────────────────────────────────────────────
    // Wait 1 minute so the agent detects that tool listing is unavailable
    await page.waitForTimeout(60_000);
    const degradedResponse = await sendQueryAndGetLatestResponse(page);
    assertGracefulDegradationIsOn(degradedResponse);
  } finally {
    await setStubEndpoint(request, 'tools/list', true);
  }

  // ── Recovery phase ──────────────────────────────────────────────────────
  await setStubEndpoint(request, 'tools/list', true);

  // Wait 1 minute for the agent to re-discover tools
  await page.waitForTimeout(60_000);
  const recoveredResponse = await sendQueryAndGetLatestResponse(page);
  assertGracefulDegradationIsOff(recoveredResponse);

  if (process.env.PAUSE) await page.pause();
});
