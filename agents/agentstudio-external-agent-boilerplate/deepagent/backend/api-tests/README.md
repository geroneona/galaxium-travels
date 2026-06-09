# API-Level Tests for DeepAgent

This directory contains API-level tests for the DeepAgent project, verifying that the product requirements defined in `docs/PRD.md` are met.

## Running Tests

### Prerequisites

Ensure the server is running. You can start it with:

```bash
make dev
```

In another terminal, run the tests:

### Run all API tests

```bash
make api-test
```

Or manually:

```bash
# From the deepagent directory
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/ -v
```

### Run specific test file

```bash
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/test_prd_requirements.py -v
```

### Run single test
```bash
uv run pytest api-tests/test_candidate_evaluation.py::TestCandidateEvaluationAgent::test_agent_evaluates_candidate_for_position -v
```

### Run with coverage

```bash
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/ -v --cov=src --cov-report=html
```

## Dependencies (Already Available)

- pytest >= 9.0
- httpx >= 0.28
- Python >= 3.13

## Notes

- Tests use `httpx` and `pytest` (already a project dependency)
- Tests are designed to catch regressions in core functionality
