---
name: testing
description: This skill provides instructions for testing. Use this skill always after doing any changes to the codebase to ensure everything works as expected.
---


# Skill Instructions

The frontend includes Playwright end-to-end tests. The tests are located in the `e2e` folder and can be executed using the Playwright test runner.
This frontend is used by multiple backends: `langgraph` `crewai_2a2` and `rlm`. Some tests work with only one or two backends byt not all of them.
However there is one test that works with all three backends: `e2e/send-hello.spec.ts`. This is a "hello world" test that should be passing ALWAYS.


## Testing scope
The testing scope depends on the scope of the changes.
Cases:
- When Frontend code is changed, run the hello world in sequence with all three backends.
- When any of the backends code is changed, run all tests listed for the respective backend.
Ofcourse, the rules stack.
As all backends run on the same port 8000, tests with different backends need run in sequence. Also frontend needs to be restarted when moving on to another backend test with respective backend mode.


## Prerequisites

Frontend and backend set up accordin to the README instructions.

The tests need backend running on `http://localhost:8000` and frontend running on `http://localhost:5173`, these port numbers are always the defaults.

Install Playwright browser (if needed).From the `frontend` folder:
```bash
npx playwright install chromium
```


## Starting frontend
From the `frontend` folder:
```bash
npm run dev -- --mode {backend}
```
{backend} is one of `langgraph`, `crewai_2a2` or `rlm` and it makes Vite load the respective `.env.{backend}` file.


## Starting LangGraph backend

From the `langgraph` folder:
```bash
make dev
```

## Starting Crewai backend

From the `crewai_2a2` folder:
```bash
make dev
```

## Starting RLM backend

From the `rlm` folder:
```bash
make dev
```


## Running the tests

From the `frontend` folder:
```bash
npx playwright test {test-file}
```
Expected result:
- `1 passed`


## Backend test mapping
The following tests should be working with the respective backends:

- `langgraph`
  - `e2e/send-hello.spec.ts`
  - `e2e/weather-forecast.spec.ts`
  - `e2e/graceful-degradation.spec.ts`
- `crewai_2a2`
  - `e2e/send-hello.spec.ts`
  - `e2e/weather-forecast.spec.ts`
- `rlm`
  - `e2e/send-hello.spec.ts`

