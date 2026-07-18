#!/usr/bin/env node
'use strict';
/*
 * Engine regression tests — dependency-free (node --test).
 * Builds a throwaway fixture repo in a tmp dir and asserts the acceptance
 * behaviours from the spec (§8): AC2/AC2b selective injection, AC2c index
 * integrity lint, AC8 single-engine parity, plus the deterministic check and
 * fail-loud degrade paths.
 *
 *   node --test tests/engine.test.js
 */

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');

const engine = require('../skills/gsd-standards-guard/engine.js');

// --- fixture ---------------------------------------------------------------

const INDEX = `version: 1
adr_dir: docs/adr
rules:
  - adr: "024"
    area: persistence
    rule: "View DDL runs at the composition root, not in a repository."
    globs:
      - "backend/src/**/repositories/**"
    check:
      forbid_pattern: "CREATE VIEW"
      in_globs:
        - "backend/src/**/repositories/**"
  - adr: "042"
    area: charts
    rule: "Chart components read units from series metadata."
    globs:
      - "frontend/components/answer-types/**"
superseded:
  "015": "→ 024 (composition-root DDL)"
historical:
  "001": "Initial architecture context, no standing rule."
`;

function buildFixture() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gsg-test-'));
  const mk = (p, c) => {
    fs.mkdirSync(path.join(dir, path.dirname(p)), { recursive: true });
    fs.writeFileSync(path.join(dir, p), c);
  };
  mk('docs/adr/001-init.md', '# 001\n');
  mk('docs/adr/015-old.md', '# 015\n');
  mk('docs/adr/024-view.md', '# 024\n');
  mk('docs/adr/042-charts.md', '# 042\n');
  mk('docs/adr/index.yaml', INDEX);
  mk('backend/src/app/repositories/reports.py', 'db.execute("CREATE VIEW v AS SELECT 1")\n');
  mk('backend/src/app/repositories/clean.py', 'return rows\n');
  mk('frontend/components/answer-types/chart.tsx', 'export const C = () => null\n');
  execFileSync('git', ['init', '-q'], { cwd: dir });
  execFileSync('git', ['config', 'user.email', 't@t.co'], { cwd: dir });
  execFileSync('git', ['config', 'user.name', 't'], { cwd: dir });
  execFileSync('git', ['add', '-A'], { cwd: dir });
  execFileSync('git', ['commit', '-qm', 'init'], { cwd: dir });
  return dir;
}

const DIR = buildFixture();

// --- tests -----------------------------------------------------------------

test('AC2b — a chart file matches only its area, no superseded/unrelated', () => {
  const r = engine.run({ scope: 'diff', projectDir: DIR, files: ['frontend/components/answer-types/chart.tsx'] });
  assert.deepEqual(r.matchedRules.map((x) => x.adr), ['042']);
  assert.equal(r.violations.length, 0);
});

test('AC2 — deterministic check fires on a repository containing CREATE VIEW', () => {
  const r = engine.run({ scope: 'diff', projectDir: DIR, files: ['backend/src/app/repositories/reports.py'] });
  assert.deepEqual(r.matchedRules.map((x) => x.adr), ['024']);
  assert.equal(r.violations.length, 1);
  assert.equal(r.violations[0].adr, '024');
  assert.equal(r.violations[0].file, 'backend/src/app/repositories/reports.py');
  assert.ok(r.violations[0].line > 0);
});

test('deterministic check is clean on a compliant repository file', () => {
  const r = engine.run({ scope: 'diff', projectDir: DIR, files: ['backend/src/app/repositories/clean.py'] });
  assert.equal(r.matchedRules.length, 1);
  assert.equal(r.violations.length, 0);
});

test('AC8 — hook(diff) and audit(all) resolve the same rule set for the same file', () => {
  const asDiff = engine.run({ scope: 'diff', projectDir: DIR, files: ['backend/src/app/repositories/reports.py'] });
  const asAll = engine.run({ scope: 'all', projectDir: DIR });
  const inAll = asAll.matchedRules.find((r) => r.adr === '024');
  assert.ok(inAll, 'ADR-024 should match under --scope=all');
  assert.equal(asDiff.matchedRules[0].rule, inAll.rule); // same rule text, one code path
});

test('AC2c — lint passes and reports bucket counts, no ADR in two buckets', () => {
  const res = engine.lint({ projectDir: DIR, checkGlobs: false });
  assert.equal(res.ok, true, JSON.stringify(res.errors));
  assert.equal(res.counts.rules, 2);
  assert.equal(res.counts.superseded, 1);
  assert.equal(res.counts.historical, 1);
});

test('AC2c — lint flags an ADR present in two buckets', () => {
  const p = path.join(DIR, 'docs/adr/bad.yaml'); // 024 is both a rule and historical
  fs.writeFileSync(p, `version: 1
adr_dir: docs/adr
rules:
  - adr: "024"
    area: a
    rule: "r"
    globs: ["backend/**"]
historical:
  "024": "also here"
`);
  const res = engine.lint({ projectDir: DIR, indexPath: p, checkGlobs: false });
  assert.equal(res.ok, false);
  assert.ok(res.errors.some((e) => /two buckets/.test(e)), JSON.stringify(res.errors));
});

test('AC2c — lint flags an on-disk ADR that is unindexed', () => {
  // 042 exists on disk but this index omits it entirely.
  const p = path.join(DIR, 'docs/adr/partial.yaml');
  fs.writeFileSync(p, `version: 1
adr_dir: docs/adr
rules:
  - adr: "024"
    area: a
    rule: "r"
    globs: ["backend/**"]
superseded:
  "015": "x"
historical:
  "001": "y"
`);
  const res = engine.lint({ projectDir: DIR, indexPath: p, checkGlobs: false });
  assert.equal(res.ok, false);
  assert.ok(res.errors.some((e) => /042.*unindexed/.test(e)), JSON.stringify(res.errors));
});

test('fail-loud — a missing index degrades, it does not throw', () => {
  const r = engine.run({ scope: 'diff', projectDir: DIR, indexPath: path.join(DIR, 'nope.yaml') });
  assert.equal(r.degraded, true);
  assert.match(r.error, /not found/);
  assert.deepEqual(r.matchedRules, []);
});

test('glob matcher — ** spans path segments and * stays within one', () => {
  assert.ok(engine.globToRegExp('backend/src/**/repositories/**').test('backend/src/a/b/repositories/c.py'));
  assert.ok(engine.globToRegExp('backend/src/**/repositories/**').test('backend/src/repositories/c.py'));
  assert.ok(!engine.globToRegExp('frontend/*.tsx').test('frontend/a/b.tsx'));
  assert.ok(engine.globToRegExp('frontend/*.tsx').test('frontend/b.tsx'));
});
