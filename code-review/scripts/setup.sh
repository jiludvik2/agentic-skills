#!/usr/bin/env bash
#
# setup.sh — one-command installer for the code-review skill.
#
# Run once, OUTSIDE the Claude Code sandbox (it needs network access to install
# dependencies and prefetch offline caches). After it completes, the skill is
# self-contained and runs inside the sandbox with no network egress.
#
# Steps, in order: Python deps -> Node deps (if a JS toolchain is present) ->
# offline-cache prefetch -> install the scope-aware Reviewer sub-agent into the
# host project. Any failed step aborts non-zero and names the step.
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

# 4. Install the Reviewer sub-agent into the host project — guarded; the skill's
#    scope-aware reviewer.md is provided in s1-t4. Host root is three levels up
#    from the skill dir (.claude/skills/code-review -> host root).
SKILL_AGENT="${SKILL_ROOT}/agents/reviewer.md"
HOST_AGENTS_DIR="$(cd "${SKILL_ROOT}/../../.." 2>/dev/null && pwd)/.claude/agents"
if [[ -f "${SKILL_AGENT}" ]]; then
  step "Install Reviewer sub-agent"
  mkdir -p "${HOST_AGENTS_DIR}" || fail "create ${HOST_AGENTS_DIR}"
  cp "${SKILL_AGENT}" "${HOST_AGENTS_DIR}/reviewer.md" || fail "copy reviewer.md"
else
  step "Install Reviewer sub-agent (skipped — skill reviewer.md not present yet)"
fi

step "Done. The code-review skill is installed and ready."
