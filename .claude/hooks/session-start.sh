#!/bin/bash
# Install the vendored plugin and the pinned tools before a cloud session starts.
#
# Synchronous on purpose: plugin state binds at session start, so the install
# has to finish first. Local clones are left alone; a developer runs the same
# commands once by hand (see README.md).
set -uo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}" || exit 1

# Each step runs whatever the others did; the hook still fails if any failed.
status=0

{ claude plugin marketplace add ./ && claude plugin install superpowers@vendored; } || status=$?

npm ci --ignore-scripts --no-audit --no-fund || status=$?

{ python3 -m venv .venv && .venv/bin/pip install -q -r requirements-dev.txt; } || status=$?

if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
  line="export PATH=\"$PWD/.venv/bin:$PWD/node_modules/.bin:\$PATH\""
  grep -qxF -- "$line" "$CLAUDE_ENV_FILE" 2>/dev/null || printf '%s\n' "$line" >>"$CLAUDE_ENV_FILE"
fi

exit "$status"
