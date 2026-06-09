#!/usr/bin/env bash
set -euo pipefail

# Install repository-local git hooks by setting core.hooksPath
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "${PWD}")
cd "${REPO_ROOT}"

echo "Setting git hooks path to .githooks"
git config core.hooksPath .githooks

echo "Done. To revert: git config --unset core.hooksPath"
