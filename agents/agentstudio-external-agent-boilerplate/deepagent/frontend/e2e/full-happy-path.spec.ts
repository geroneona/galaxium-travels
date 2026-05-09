/**
 * E2E happy-path test:
 *   1. Authenticate (if Keycloak is configured)
 *   2. Add 2 CVs with names and content
 *   3. Add 2 job descriptions with titles and content
 *   4. Ask "Which candidate is the top match for the Frontend Developer role?"
 *   5. Assert a non-empty response is received
 *
 * Environment variables:
 *   E2E_BASE_URL      – app URL, defaults to http://localhost:5174
 *   E2E_KC_USERNAME   – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD   – Keycloak password (required when auth is enabled)
 */
import { test, expect, type Page } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

const DEBUG_TIMEOUT = process.env.PAUSE ? 3_600_000 : undefined;

// ── Test data ──────────────────────────────────────────────────────────────────

const CVS = [
  {
    name: 'Alice Smith',
    content: '5 years React/TypeScript frontend. Led design-system migration. BSc CS.',
  },
  {
    name: 'Bob Johnson',
    content: '7 years Python/FastAPI backend. Microservices, Docker, AWS. Limited frontend.',
  },
];

const JOBS = [
  {
    title: 'Frontend Developer',
    description: 'Senior frontend role. Requires 4+ years React, TypeScript, CSS, accessibility.',
  },
  {
    title: 'Backend Engineer',
    description: 'Backend role. Requires Python, FastAPI, SQL, Docker/K8s.',
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

async function addCV(page: Page, name: string, content: string): Promise<void> {
  await page.getByRole('button', { name: 'Add CV' }).click();
  // Each new CV is appended collapsed; click the last "Expand CV" button
  await page.getByRole('button', { name: 'Expand CV' }).last().click();
  await page.getByPlaceholder("Person's name").last().fill(name);
  await page.getByPlaceholder(/Paste CV content here/i).last().fill(content);
}

async function addJob(page: Page, title: string, description: string): Promise<void> {
  await page.getByRole('button', { name: 'Add Job' }).click();
  // Each new job is appended collapsed; click the last "Expand job description" button
  await page.getByRole('button', { name: 'Expand job description' }).last().click();
  await page.getByPlaceholder('Position title').last().fill(title);
  await page.getByPlaceholder(/Paste job description here/i).last().fill(description);
}

// ── Test ───────────────────────────────────────────────────────────────────────

test('full happy path – 2 CVs, 2 jobs, ask for top match', async ({ page }) => {
  // This test submits significant context so the agent may take longer to respond.
  test.setTimeout(DEBUG_TIMEOUT || 180_000);

  // ── 1. Authenticate ──────────────────────────────────────────────────────
  await loginIfNeeded(page);

  // ── 2. Add CVs ───────────────────────────────────────────────────────────
  for (const cv of CVS) {
    await addCV(page, cv.name, cv.content);
  }

  // Verify both CV names are visible in the sidebar
  await expect(page.getByPlaceholder("Person's name").nth(0)).toHaveValue(CVS[0].name);
  await expect(page.getByPlaceholder("Person's name").nth(1)).toHaveValue(CVS[1].name);

  // ── 3. Add job descriptions ──────────────────────────────────────────────
  for (const job of JOBS) {
    await addJob(page, job.title, job.description);
  }

  // Verify both job titles are visible in the sidebar
  await expect(page.getByPlaceholder('Position title').nth(0)).toHaveValue(JOBS[0].title);
  await expect(page.getByPlaceholder('Position title').nth(1)).toHaveValue(JOBS[1].title);

  // ── 4. Ask about the top match ───────────────────────────────────────────
  const question = 'Which candidate is the top match for the Frontend Developer role and why?';
  const textarea = page.getByPlaceholder(/Ask a question/i);
  await textarea.fill(question);
  await page.getByRole('button', { name: 'Send' }).click();

  // ── 5. Verify response ───────────────────────────────────────────────────
  const answerBubble = page.locator('[data-testid="answer-bubble"]').first();
  await expect(answerBubble).toBeVisible({ timeout: DEBUG_TIMEOUT || 15_000 });
  // Wait for the loading flag to be cleared (stream complete) rather than text-matching
  await expect(answerBubble).toHaveAttribute('data-loading', 'false', { timeout: DEBUG_TIMEOUT || 120_000 });

  const responseText = (await answerBubble.textContent()) ?? '';
  expect(responseText.trim().length, 'Expected a non-empty response from the agent').toBeGreaterThan(0);

  // The answer should mention at least one of the candidates
  const mentionsCandidates =
    responseText.includes('Alice') || responseText.includes('Bob');
  expect(mentionsCandidates, 'Response should mention at least one candidate by name').toBe(true);

  if (process.env.PAUSE) await page.pause();
});
