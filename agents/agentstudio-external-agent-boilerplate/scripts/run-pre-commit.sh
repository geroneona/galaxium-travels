#!/usr/bin/env bash
set -euo pipefail

# Run the repository pre-commit hook manually. Pass --all to run all checks.
ROOT_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "${PWD}")
cd "${ROOT_DIR}"

HOOK=.githooks/pre-commit
if [ ! -f "${HOOK}" ]; then
  echo "Hook not found at ${HOOK}" >&2
  exit 2
fi

bash "${HOOK}" "$@"
