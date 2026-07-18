#!/usr/bin/env node
'use strict';
/*
 * gsd-standards-guard — PreToolUse hook (thin caller of the rule engine).
 *
 * Fires inside the GSD code-review subagent and injects the standing rules
 * whose file-globs match the changed files, plus the enforcement directive.
 * It is a *thin* caller: all rule resolution lives in the engine (§5.1), so the
 * hook and /standards-audit cannot drift in what they enforce.
 *
 * Scoping (AC5, validated on Claude Code 2.1.212): PreToolUse stdin carries a
 * top-level `agent_type` inside a Task subagent (absent on main-loop calls), so
 * we gate on `agent_type === "gsd-code-reviewer"`. `additionalContext` reaches
 * the subagent's model.
 *
 * Fire-once: the reviewer issues many reads; we inject on the first matching
 * call per `agent_id` and no-op thereafter (a per-agent_id sentinel in tmpdir).
 *
 * Dependency-free. Never throws to the harness: on any error it exits 0 with no
 * output (fail-open — enforcement is belt-and-suspenders behind CLAUDE.md).
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

const REVIEWER_AGENT_TYPE = 'gsd-code-reviewer';
// Broaden to any structural edit by setting SCOPE=structural (higher token cost).
const SCOPE_MODE = process.env.GSD_STANDARDS_SCOPE || 'review';

function readStdin() {
  try {
    return fs.readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

const DIRECTIVE =
  'Standards enforcement (code review): Treat docs/ARCHITECTURE.md (invariants + standing-rule ' +
  'ledger), docs/STANDARDS.md, and the standing rules listed below as BINDING. The listed rules are ' +
  'the ones whose file-globs match the changed files — apply those; you need not read the full ADR ' +
  'corpus. Any code that contradicts a rule is a finding — cite the source (e.g. "violates ADR-024 — ' +
  'view DDL must run at the composition root, not in a repository"). Open docs/adr/<NNN>-*.md only ' +
  'when a rule is ambiguous for this change. Do not infer rules beyond these documents; they define ' +
  'the standard.';

function buildContext(result) {
  const lines = [DIRECTIVE, ''];
  if (result.degraded) {
    lines.push(
      'NOTE: docs/adr/index.yaml is missing or unparseable — the rule index could not be loaded. ' +
      'Consult the docs/ARCHITECTURE.md decision index manually for the standing rules that apply ' +
      'to the changed files.'
    );
    return lines.join('\n');
  }
  if (result.matchedRules.length === 0) {
    lines.push('No standing rule’s globs match the changed files. Review against ARCHITECTURE.md invariants and STANDARDS.md.');
    return lines.join('\n');
  }
  lines.push('Standing rules that apply to the changed files:');
  for (const r of result.matchedRules) {
    lines.push(`- ADR-${r.adr} (${r.area}): ${r.rule}`);
  }
  if (result.violations.length > 0) {
    lines.push('', 'Pre-noted deterministic violations (confirm and report each as a finding):');
    for (const v of result.violations) {
      lines.push(`- ADR-${v.adr}: ${v.file}${v.line ? ':' + v.line : ''} contains forbidden "${v.pattern}"`);
    }
  }
  return lines.join('\n');
}

function emit(additionalContext) {
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: { hookEventName: 'PreToolUse', additionalContext },
  }));
}

function main() {
  let input;
  try {
    input = JSON.parse(readStdin() || '{}');
  } catch {
    return; // malformed stdin — fail open
  }

  // Scope gate (AC5). In "review" mode only the reviewer subagent triggers.
  if (SCOPE_MODE === 'review' && input.agent_type !== REVIEWER_AGENT_TYPE) return;
  if (SCOPE_MODE === 'structural' && !input.agent_type) {
    // structural mode: also allow main-loop edits — no further gate here.
  }

  // Fire-once per agent_id.
  const agentId = input.agent_id || input.session_id || 'main';
  const sentinel = path.join(os.tmpdir(), `gsd-standards-guard-${sanitize(agentId)}`);
  try {
    if (fs.existsSync(sentinel)) return; // already injected for this agent
    fs.writeFileSync(sentinel, ''); // create marker
  } catch {
    // If we cannot write a sentinel, still inject once (better than never).
  }

  const projectDir = input.cwd || process.env.CLAUDE_PROJECT_DIR || process.cwd();

  let engine;
  try {
    engine = require(path.join(projectDir, '.claude', 'skills', 'gsd-standards-guard', 'engine.js'));
  } catch {
    return; // engine not installed — fail open
  }

  let result;
  try {
    // Prefer the phase manifest's changed-file list when the harness provides one.
    const files = Array.isArray(input.changed_files) ? input.changed_files : null;
    result = engine.run({ scope: 'diff', projectDir, files });
  } catch {
    return; // engine error — fail open
  }

  emit(buildContext(result));
}

function sanitize(s) {
  return String(s).replace(/[^a-zA-Z0-9_.-]/g, '_').slice(0, 120);
}

main();
