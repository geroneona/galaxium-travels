/**
 * E2E happy-path test (demo):
 *   1. Authenticate (if Keycloak is configured)
 *   2. Add 3 CVs (Alice Smith – frontend, Bob Johnson – backend, Carol Rivera – full-stack)
 *   3. Add 1 job description (Senior Frontend Developer)
 *   4. Ask which candidate is the top match for the Senior Frontend Developer role
 *   5. Assert a non-empty, named response is received
 *
 * Environment variables:
 *   E2E_BASE_URL      – app URL, defaults to http://localhost:5174
 *   E2E_KC_USERNAME   – Keycloak username (required when auth is enabled)
 *   E2E_KC_PASSWORD   – Keycloak password (required when auth is enabled)
 */
import { test, expect, type Page, type Locator } from '@playwright/test';
import { loginIfNeeded } from './helpers/auth';

const INTERACTION_DELAY = 1000
const DEBUG_TIMEOUT = process.env.PAUSE ? 3_600_000 : undefined;

// ── Test data ──────────────────────────────────────────────────────────────────

const CVS = [
  {
    name: 'Alice Smith',
    content: `Alice Smith – Senior Frontend Engineer

SUMMARY
Frontend engineer with 6 years of experience building scalable, accessible web applications. Deep expertise in React, TypeScript, and design systems.

EXPERIENCE
Senior Frontend Engineer – Acme Corp (2022 – present)
• Led migration from Angular 8 to React 18 + TypeScript, reducing bundle size by 42% and cutting Time-to-Interactive by 1.8 s.
• Architected the company-wide design system (50+ components) across 12 product teams, documented with Storybook.
• Drove WCAG 2.1 AA accessibility adoption; introduced automated a11y checks into CI.
• Mentored 3 junior engineers; shipped responsive interfaces to 200 k+ monthly active users.

SKILLS
React 18, TypeScript, Next.js 14, Tailwind CSS, Playwright, Vitest, Storybook, GitHub Actions, WCAG 2.1 AA

EDUCATION
BSc Computer Science – University of Edinburgh (2018) | First-Class Honours`,
  },
  {
    name: 'Bob Johnson',
    content: `Bob Johnson – Senior Backend Engineer

SUMMARY
Backend engineer with 8 years of experience designing distributed systems at scale. Specialises in Python microservices, cloud-native architectures, and data-intensive APIs.

EXPERIENCE
Senior Backend Engineer – CloudScale Inc (2021 – present)
• Built event-driven pipeline (Kafka + Python, 50 k events/s), cutting batch processing time from 6 h to 25 min.
• Re-architected REST API from Flask to FastAPI: 3× throughput improvement, p99 latency below 120 ms.
• Managed zero-downtime migration of 2 TB PostgreSQL dataset to AWS RDS Aurora.

SKILLS
Python 3.12, FastAPI, Django, PostgreSQL, Redis, Kafka, Docker, Kubernetes, AWS, Terraform

EDUCATION
MEng Software Engineering – University of Manchester (2016) | 2:1 Honours`,
  },
  {
    name: 'Carol Rivera',
    content: `Carol Rivera – Full-Stack Engineer

SUMMARY
Full-stack engineer with 5 years of experience delivering end-to-end features across React frontends and Node.js/Python backends. Comfortable owning a feature from database schema to polished UI, with a strong focus on developer tooling and CI/CD.

EXPERIENCE
Full-Stack Engineer – Streamline SaaS (2022 – present)
• Delivered full-stack features for a B2B workflow platform: React + TypeScript frontend, Node.js/Express API, and PostgreSQL data layer.
• Rebuilt the onboarding flow (React, React Hook Form, Zod), reducing drop-off rate by 28%.
• Introduced GraphQL (Apollo Server) to replace 15 ad-hoc REST endpoints, cutting client-side over-fetching by 60%.
• Set up GitHub Actions CI/CD pipeline with automated unit, integration, and Playwright E2E tests; reduced deploy cycle from 2 days to 2 hours.

SKILLS
Frontend: React 18, TypeScript, Next.js 14, Tailwind CSS, GraphQL (Apollo)
Backend: Node.js, Express, FastAPI, PostgreSQL, Redis, Prisma ORM
Tooling: Docker, GitHub Actions, Playwright, Vitest, Storybook

EDUCATION
BSc Software Engineering – University of Bristol (2020) | 2:1 Honours`,
  },
];

const JOBS = [
  {
    title: 'Senior Frontend Developer',
    description: `Senior Frontend Developer – Product Engineering (Remote)

ABOUT THE ROLE
We are looking for a Senior Frontend Developer to join our Product Engineering team and help build the next generation of our SaaS platform used by 500 000+ users. You will own large areas of the UI, drive architectural decisions, and set the quality bar for the frontend.

REQUIREMENTS
• 5+ years of professional frontend development experience.
• Expert-level knowledge of React and TypeScript.
• Strong command of modern CSS and responsive design.
• Experience with design systems and component libraries (Storybook or equivalent).
• Hands-on experience with testing tools (Playwright, Vitest, React Testing Library).
• Familiarity with CI/CD pipelines and web performance optimisation (Core Web Vitals).
• Commitment to accessibility (WCAG 2.1 AA).`,
  },
];

// ── Helpers ────────────────────────────────────────────────────────────────────

/** Expand a textarea to show its full content (no scroll). */
async function resizeTextareaToFit(locator: Locator): Promise<void> {
  await locator.evaluate((el: HTMLTextAreaElement) => {
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  });
}

async function addCV(page: Page, name: string, content: string): Promise<void> {
  await page.getByRole('button', { name: 'Add CV' }).click(); await page.waitForTimeout(INTERACTION_DELAY);
  // Each new CV is appended collapsed; click the last "Expand CV" button
  await page.getByRole('button', { name: 'Expand CV' }).last().click(); await page.waitForTimeout(INTERACTION_DELAY);
  await page.getByPlaceholder("Person's name").last().fill(name); await page.waitForTimeout(INTERACTION_DELAY);
  await page.getByPlaceholder(/Paste CV content here/i).last().fill(content);
  await resizeTextareaToFit(page.getByPlaceholder(/Paste CV content here/i).last()); await page.waitForTimeout(INTERACTION_DELAY);
}

async function addJob(page: Page, title: string, description: string): Promise<void> {
  await page.getByRole('button', { name: 'Add Job' }).click(); await page.waitForTimeout(INTERACTION_DELAY);
  // Each new job is appended collapsed; click the last "Expand job description" button
  await page.getByRole('button', { name: 'Expand job description' }).last().click(); await page.waitForTimeout(INTERACTION_DELAY);
  await page.getByPlaceholder('Position title').last().fill(title); await page.waitForTimeout(INTERACTION_DELAY);
  await page.getByPlaceholder(/Paste job description here/i).last().fill(description); 
  await resizeTextareaToFit(page.getByPlaceholder(/Paste job description here/i).last());await page.waitForTimeout(INTERACTION_DELAY);
}

// ── Test ───────────────────────────────────────────────────────────────────────

test('full happy path – 3 CVs, 1 job, ask for top match (demo)', async ({ page }) => {
  // This test submits significant context so the agent may take longer to respond.
  test.setTimeout(DEBUG_TIMEOUT || 180_000);

  // ── 1. Authenticate ──────────────────────────────────────────────────────
  await loginIfNeeded(page, INTERACTION_DELAY);

  // ── 2. Add CVs ───────────────────────────────────────────────────────────
  for (const cv of CVS) {
    await addCV(page, cv.name, cv.content);
  }

  // Verify all three CV names are visible in the sidebar
  await expect(page.getByPlaceholder("Person's name").nth(0)).toHaveValue(CVS[0].name);
  await expect(page.getByPlaceholder("Person's name").nth(1)).toHaveValue(CVS[1].name);
  await expect(page.getByPlaceholder("Person's name").nth(2)).toHaveValue(CVS[2].name);

  // ── 3. Add job description ───────────────────────────────────────────────
  for (const job of JOBS) {
    await addJob(page, job.title, job.description);
  }

  // Verify the job title is visible in the sidebar
  await expect(page.getByPlaceholder('Position title').nth(0)).toHaveValue(JOBS[0].title);

  // ── 4. Ask about the top match ───────────────────────────────────────────
  const question = 'Which candidate is the top match for the Senior Frontend Developer role and why?';
  const textarea = page.getByPlaceholder(/Ask a question/i);
  await textarea.fill(question); await page.waitForTimeout(INTERACTION_DELAY);
  await page.getByRole('button', { name: 'Send' }).click(); await page.waitForTimeout(INTERACTION_DELAY);

  // ── 5. Verify response ───────────────────────────────────────────────────
  const answerBubble = page.locator('[data-testid="answer-bubble"]').first();
  await expect(answerBubble).toBeVisible({ timeout: DEBUG_TIMEOUT || 15_000 });
  // Wait for the loading flag to be cleared (stream complete) rather than text-matching
  await expect(answerBubble).toHaveAttribute('data-loading', 'false', { timeout: DEBUG_TIMEOUT || 120_000 });

  const responseText = (await answerBubble.textContent()) ?? '';
  expect(responseText.trim().length, 'Expected a non-empty response from the agent').toBeGreaterThan(0);

  // The answer should mention at least one of the candidates
  const mentionsCandidates =
    responseText.includes('Alice') || responseText.includes('Bob') || responseText.includes('Carol');
  expect(mentionsCandidates, 'Response should mention at least one candidate by name').toBe(true);

  if (process.env.PAUSE) await page.pause();
});
