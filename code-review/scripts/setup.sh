#!/usr/bin/env bash
#
# setup.sh — one-command installer for the code-review skill.
#
# Run once, OUTSIDE the Claude Code sandbox (it needs network access to install
# dependencies and prefetch offline caches). After it completes, the skill is
# self-contained and runs inside the sandbox with no network egress.
#
# Steps, in order: Python deps -> Node deps (if a JS toolchain is present) ->
# offline-cache prefetch -> reviewer.md state report (read-only) ->
# starter config template hint (read-only). Any failed step aborts non-zero
# and names the step.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# BUNDLE_DIR points at the skill bundle itself — the directory containing
# SKILL.md and code-review.toml.example. In developer/source layout it lives
# under <SKILL_ROOT>/.claude/skills/code-review/; in installed layouts where
# the bundle and SKILL_ROOT coincide we fall back to SKILL_ROOT. Used only by
# the read-only "starter config" report step; nothing here writes to it.
if [[ -f "${SKILL_ROOT}/.claude/skills/code-review/SKILL.md" ]]; then
  BUNDLE_DIR="${SKILL_ROOT}/.claude/skills/code-review"
elif [[ -f "${SKILL_ROOT}/SKILL.md" ]]; then
  BUNDLE_DIR="${SKILL_ROOT}"
else
  BUNDLE_DIR=""
fi

step() { echo "==> $1"; }
note() { echo "    $1"; }
fail() {
  echo "ERROR: setup.sh failed at step: $1" >&2
  exit 1
}

# Locate the host project root: the nearest ancestor of the skill dir that contains a
# .claude/ directory. Used for read-only reviewer.md state inspection AND (s0-t6/ADR-0015)
# to select the cache-write anchor in the production-nested layout, so the producer writes
# where the CWD-anchored consumers read. Returns empty string if no ancestor has .claude/
# (skill is the repo itself, or installed in an unexpected layout).
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

# The producer must write caches where the consumers (trivy/js_base, via
# code_review.paths.cache_root) read them. cache_root() honours
# $POLYREVIEW_CACHE_DIR, else resolves CWD-relative to ./.claude/skills/code-review.
# Run the producer from the host root (nearest .claude/ ancestor) when present so the
# production-nested layout aligns; fall back to SKILL_ROOT for the developer layout.
# An explicit $POLYREVIEW_CACHE_DIR wins regardless of CWD. ADR-0015.
if [[ -n "${POLYREVIEW_CACHE_DIR:-}" ]]; then
  CACHE_CWD="${SKILL_ROOT}"
elif CACHE_CWD="$(find_host_root "${SKILL_ROOT}")" && [[ -n "${CACHE_CWD}" ]]; then
  :
else
  CACHE_CWD="${SKILL_ROOT}"
fi
note "cache anchor: ${CACHE_CWD} (export POLYREVIEW_CACHE_DIR to override; the CLI must run from the same anchor)"

# 2. Node dependencies for JS/TS analyzers — guarded; the JS toolchain lands in s3.
if [[ -f "${SKILL_ROOT}/package.json" && -f "${SKILL_ROOT}/package-lock.json" ]]; then
  step "Node dependencies"
  # Pass SKILL_ROOT via env, not string-interpolated into the Python source, so paths
  # with spaces/quotes don't break the resolution.
  CACHE_ROOT="$(cd "${CACHE_CWD}" && POLYREVIEW_SKILL_ROOT="${SKILL_ROOT}" python -c \
    'import os, sys; sys.path.insert(0, os.environ["POLYREVIEW_SKILL_ROOT"]); from code_review.paths import node_modules_dir; print(node_modules_dir().parent)')" \
    || fail "resolve cache_root"
  mkdir -p "${CACHE_ROOT}"
  cp "${SKILL_ROOT}/package.json" "${SKILL_ROOT}/package-lock.json" "${CACHE_ROOT}/"
  ( cd "${CACHE_ROOT}" && npm ci ) || fail "npm ci"
else
  step "Node dependencies (skipped — no package.json/package-lock.json yet)"
fi

# 3. Prefetch offline caches: copies the vendored Semgrep ruleset into the cache
#    (ADR-0016) and reconciles any download-based artifacts. Idempotent.
# prefetch_caches.py resolves cache_root() itself; running it from CACHE_CWD makes
# the CWD-anchored default land where the consumers read.
step "Prefetch offline caches"
( cd "${CACHE_CWD}" && python "${SCRIPT_DIR}/prefetch_caches.py" ) || fail "prefetch_caches.py"

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

# 5. Starter config template. Print the absolute path of the bundled example
#    and a one-line copy hint pointing at the host project root (or a generic
#    hint if no .claude/ ancestor resolves).
step "Starter config template"
if [[ -z "${BUNDLE_DIR}" ]]; then
  note "skill bundle not located (no SKILL.md under SKILL_ROOT or its .claude/skills/code-review/ subtree)"
  note "skipping starter-config report — re-fetch the skill bundle if the layout is unexpected"
else
EXAMPLE_PATH="${BUNDLE_DIR}/code-review.toml.example"
if [[ -f "${EXAMPLE_PATH}" ]]; then
  note "available: ${EXAMPLE_PATH}"
  if HOST_ROOT="$(find_host_root "${SKILL_ROOT}")"; then
    note "to override defaults: cp ${EXAMPLE_PATH} ${HOST_ROOT}/code-review.toml"
  else
    note "to override defaults: copy to your project root (the CWD you'll invoke"
    note "the CLI from) as code-review.toml, then edit."
  fi
else
  note "missing: ${EXAMPLE_PATH}"
  note "the starter template is bundled with the skill; if missing, re-fetch the bundle."
fi
fi  # close BUNDLE_DIR-empty guard

step "Done. The code-review skill is installed and ready."
