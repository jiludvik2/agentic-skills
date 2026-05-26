#!/usr/bin/env bash
#
# setup.sh — one-command installer for the code-review skill.
#
# Run once, OUTSIDE the Claude Code sandbox (it needs network access to install
# dependencies and prefetch offline caches). After it completes, the skill is
# self-contained and runs inside the sandbox with no network egress.
#
# Steps, in order: Python deps -> Node deps (if a JS toolchain is present) ->
# offline-cache prefetch. (Installing the scope-aware Reviewer sub-agent into the
# host project lands in s1-t4.) Any failed step aborts non-zero and names the step.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

step() { echo "==> $1"; }
fail() {
  echo "ERROR: setup.sh failed at step: $1" >&2
  exit 1
}

# 1. Python dependencies (pinned, reproducible).
step "Python dependencies"
uv sync --frozen || fail "uv sync --frozen"

# 2. Node dependencies for JS/TS analyzers — guarded; the JS toolchain lands in s3.
if [[ -f "${SKILL_ROOT}/package.json" && -f "${SKILL_ROOT}/package-lock.json" ]]; then
  step "Node dependencies"
  npm ci || fail "npm ci"
else
  step "Node dependencies (skipped — no package.json/package-lock.json yet)"
fi

# 3. Prefetch offline caches (Trivy DB, Semgrep rule packs in s3). Idempotent.
step "Prefetch offline caches"
( cd "${SKILL_ROOT}" && python "${SCRIPT_DIR}/prefetch_caches.py" ) || fail "prefetch_caches.py"

# 4. Install the Reviewer sub-agent into the host project — added in s1-t4, which owns
#    the scope-aware reviewer.md source and a verified walk-up-to-.claude host-root
#    resolution (fail-loud, no fragile fixed-depth traversal).

step "Done. The code-review skill is installed and ready."
