#!/usr/bin/env bash
#
# setup.sh — one-command installer for the code-review skill.
#
# Run once, OUTSIDE the Claude Code sandbox (it needs network access to install
# dependencies and prefetch offline caches). After it completes, the skill is
# self-contained and runs inside the sandbox with no network egress.
#
# Steps, in order: Python deps -> Node deps (if a JS toolchain is present) ->
# offline-cache prefetch -> reviewer.md state report (read-only, no writes).
# Any failed step aborts non-zero and names the step.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

step() { echo "==> $1"; }
note() { echo "    $1"; }
fail() {
  echo "ERROR: setup.sh failed at step: $1" >&2
  exit 1
}

# Locate the host project root: the nearest ancestor of the skill dir that contains a
# .claude/ directory. Used only for read-only state inspection; setup.sh never writes
# outside SKILL_ROOT. Returns empty string if no ancestor has .claude/ (skill is the
# repo itself, or installed in an unexpected layout).
find_host_root() {
  local d="$1"
  while [[ "${d}" != "/" && -n "${d}" ]]; do
    if [[ -d "${d}/.claude" ]]; then
      echo "${d}"
      return 0
    fi
    d="$(dirname "${d}")"
  done
  return 1
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

# 4. Reviewer.md state report. The code-review skill is a pure deterministic analyzer
#    (no LLM inside; no sub-agent installed). The SDLC's Review verb dispatches a
#    .claude/agents/reviewer.md in the host project — that file's lifecycle is owned
#    by the SDLC skill (or the operator), not by us. This step reads its state and
#    reports; it never writes.
step "Reviewer sub-agent state"
if HOST_ROOT="$(find_host_root "${SKILL_ROOT}")"; then
  HOST_REVIEWER="${HOST_ROOT}/.claude/agents/reviewer.md"
  if [[ -f "${HOST_REVIEWER}" ]]; then
    note "found: ${HOST_REVIEWER}"
    note "left untouched — code-review does not manage reviewer.md."
  else
    note "missing: ${HOST_REVIEWER}"
    note "the SDLC Review verb needs one to dispatch. Install via the SDLC skill"
    note "(bootstrap re-run) or copy your own. code-review does not install a reviewer."
  fi
else
  note "no .claude/ ancestor found above ${SKILL_ROOT}"
  note "skipping reviewer.md state check — skill appears to be the repo itself"
  note "(developer layout) rather than installed under <host>/.claude/skills/code-review."
fi

step "Done. The code-review skill is installed and ready."
