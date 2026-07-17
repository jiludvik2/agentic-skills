#!/usr/bin/env node
'use strict';
/*
 * gsd-standards-guard — the rule engine.
 *
 * Single authority for: given a file set, (a) which standing rules apply
 * (glob-match against docs/adr/index.yaml) and (b) where a rule carries a
 * `check:` assertion, whether the file set violates it (deterministic tier).
 *
 * Two independent callers feed it a file set — the PreToolUse hook
 * (--scope=diff) and /standards-audit (--scope=all). One rule table, one
 * matcher, one code path: the callers cannot drift in what they enforce.
 *
 * Dependency-free (Node stdlib only). The YAML reader is a scoped parser for
 * the index.yaml schema documented in templates/index.yaml — not a general
 * YAML implementation. The §5.3 lint keeps the file inside that shape.
 *
 * Usage:
 *   node engine.js --scope=diff  [--files a b …] [--format=json|pretty]
 *   node engine.js --scope=all   [--exit-code]   [--format=json|pretty]
 *   node engine.js --lint        [--project DIR]
 *
 * As a module:
 *   const { run } = require('./engine.js');
 *   run({ scope: 'diff', projectDir });   // no process.exit — safe for the hook
 */

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

// Paths never worth matching or checking (vendored / generated / VCS).
const DEFAULT_EXCLUDES = [
  '.git/', 'node_modules/', 'dist/', 'build/', 'out/', 'coverage/',
  '.venv/', 'venv/', '__pycache__/', 'vendor/', '.mypy_cache/',
  '.ruff_cache/', '.pytest_cache/', '.next/', '.turbo/',
];

function isExcluded(file) {
  return DEFAULT_EXCLUDES.some((p) => file === p || file.startsWith(p) || file.includes('/' + p));
}

// --------------------------------------------------------------------------
// Scoped YAML reader for the index.yaml schema
// --------------------------------------------------------------------------

function stripComment(line) {
  // Remove a trailing `#…` comment that is not inside quotes.
  let inS = false, inD = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === "'" && !inD) inS = !inS;
    else if (c === '"' && !inS) inD = !inD;
    else if (c === '#' && !inS && !inD && (i === 0 || /\s/.test(line[i - 1]))) {
      return line.slice(0, i);
    }
  }
  return line;
}

function parseScalar(raw) {
  const s = raw.trim();
  if (s === '') return '';
  if (s === '~' || s === 'null') return null;
  if (s === 'true') return true;
  if (s === 'false') return false;
  if ((s.startsWith('"') && s.endsWith('"')) || (s.startsWith("'") && s.endsWith("'"))) {
    return s.slice(1, -1);
  }
  if (s.startsWith('[') && s.endsWith(']')) {
    const inner = s.slice(1, -1).trim();
    if (inner === '') return [];
    return splitFlow(inner).map(parseScalar);
  }
  if (s.startsWith('{') && s.endsWith('}')) {
    const inner = s.slice(1, -1).trim();
    const obj = {};
    if (inner !== '') {
      for (const part of splitFlow(inner)) {
        const idx = part.indexOf(':');
        obj[parseScalar(part.slice(0, idx))] = parseScalar(part.slice(idx + 1));
      }
    }
    return obj;
  }
  if (/^-?\d+$/.test(s)) return parseInt(s, 10);
  return s;
}

// Split a flow collection body on top-level commas (respect quotes/brackets).
function splitFlow(s) {
  const out = [];
  let depth = 0, inS = false, inD = false, cur = '';
  for (const c of s) {
    if (c === "'" && !inD) inS = !inS;
    else if (c === '"' && !inS) inD = !inD;
    if (!inS && !inD) {
      if (c === '[' || c === '{') depth++;
      else if (c === ']' || c === '}') depth--;
      else if (c === ',' && depth === 0) { out.push(cur.trim()); cur = ''; continue; }
    }
    cur += c;
  }
  if (cur.trim() !== '') out.push(cur.trim());
  return out;
}

function parseYAML(text) {
  const lines = [];
  for (const raw of text.split(/\r?\n/)) {
    const stripped = stripComment(raw);
    if (stripped.trim() === '') continue;
    lines.push({ indent: stripped.length - stripped.trimStart().length, text: stripped.trim() });
  }
  let pos = 0;

  function parseNode(minIndent) {
    const cur = lines[pos];
    if (!cur || cur.indent < minIndent) return null;
    if (cur.text === '-' || cur.text.startsWith('- ')) return parseSeq(cur.indent);
    return parseMap(cur.indent);
  }

  function parseSeq(indent) {
    const arr = [];
    while (pos < lines.length && lines[pos].indent === indent &&
           (lines[pos].text === '-' || lines[pos].text.startsWith('- '))) {
      const rest = lines[pos].text === '-' ? '' : lines[pos].text.slice(2);
      const childIndent = indent + 2;
      if (rest === '') {
        pos++;
        arr.push(parseNode(indent + 1));
      } else if (isMapEntry(rest)) {
        const map = {};
        pos++;
        applyEntry(map, rest, childIndent);
        while (pos < lines.length && lines[pos].indent === childIndent &&
               lines[pos].text !== '-' && !lines[pos].text.startsWith('- ')) {
          applyEntry(map, lines[pos].text, childIndent);
          pos++;
        }
        arr.push(map);
      } else {
        arr.push(parseScalar(rest));
        pos++;
      }
    }
    return arr;
  }

  function parseMap(indent) {
    const map = {};
    while (pos < lines.length && lines[pos].indent === indent &&
           lines[pos].text !== '-' && !lines[pos].text.startsWith('- ')) {
      applyEntry(map, lines[pos].text, indent);
      pos++;
    }
    return map;
  }

  // Apply one `key: value` / `key:` entry to `map`. When the value is empty the
  // entry owns the deeper block that follows; parseNode consumes it (and may
  // advance `pos`), so callers that iterate siblings re-check pos afterwards.
  function applyEntry(map, text, indent) {
    const idx = colonSplit(text);
    if (idx === -1) return; // not a map entry; ignore defensively
    const key = parseScalar(text.slice(0, idx));
    const valueRaw = text.slice(idx + 1).trim();
    if (valueRaw === '') {
      // Nested block belongs to this key. It starts on the NEXT line, deeper.
      const save = pos;
      const wasAt = lines.indexOf(lines[save]); // no-op guard for clarity
      void wasAt;
      // The current line (this key) has already been consumed by the caller for
      // the sibling loop EXCEPT when called for the seq-inline first entry. To
      // unify, we peek the next line here without assuming who advanced pos.
      const child = parseNextBlock(indent);
      map[key] = child === undefined ? null : child;
    } else {
      map[key] = parseScalar(valueRaw);
    }
  }

  // Parse a block that is strictly deeper than `parentIndent`, starting at the
  // line after the current key line. Returns null when nothing is deeper.
  function parseNextBlock(parentIndent) {
    // Advance past the key line if the caller left pos on it.
    // Callers set pos to the key line; move to the next line to inspect depth.
    const keyLineIdx = pos;
    const next = lines[keyLineIdx + 1];
    if (!next || next.indent <= parentIndent) return null;
    pos = keyLineIdx + 1;
    const val = parseNode(parentIndent + 1);
    // parseNode left pos after the block; step back one so the caller's own
    // pos++ (sibling loop) lands correctly on the next sibling.
    pos -= 1;
    return val;
  }

  return parseNode(0) || {};
}

// Index of the `:` that separates a map key from its value (respect quotes).
function colonSplit(text) {
  let inS = false, inD = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === "'" && !inD) inS = !inS;
    else if (c === '"' && !inS) inD = !inD;
    else if (c === ':' && !inS && !inD && (i + 1 >= text.length || text[i + 1] === ' ')) {
      return i;
    }
  }
  return -1;
}

function isMapEntry(text) {
  return colonSplit(text) !== -1;
}

// --------------------------------------------------------------------------
// Index loading
// --------------------------------------------------------------------------

function loadIndex(indexPath) {
  if (!fs.existsSync(indexPath)) {
    throw new Error(`index not found: ${indexPath}`);
  }
  const raw = fs.readFileSync(indexPath, 'utf8');
  let doc;
  try {
    doc = parseYAML(raw);
  } catch (e) {
    throw new Error(`index parse failed (${indexPath}): ${e.message}`);
  }
  if (!doc || typeof doc !== 'object') {
    throw new Error(`index malformed: expected a mapping at top level (${indexPath})`);
  }
  return {
    version: doc.version ?? 1,
    adr_dir: doc.adr_dir || 'docs/adr',
    rules: Array.isArray(doc.rules) ? doc.rules : [],
    superseded: doc.superseded && typeof doc.superseded === 'object' ? doc.superseded : {},
    historical: doc.historical && typeof doc.historical === 'object' ? doc.historical : {},
  };
}

// --------------------------------------------------------------------------
// Glob matching
// --------------------------------------------------------------------------

function globToRegExp(glob) {
  let re = '';
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === '*') {
      if (glob[i + 1] === '*') {
        i++;
        if (glob[i + 1] === '/') { i++; re += '(?:.*/)?'; }
        else re += '.*';
      } else {
        re += '[^/]*';
      }
    } else if (c === '?') {
      re += '[^/]';
    } else if ('.+^${}()|[]\\'.includes(c)) {
      re += '\\' + c;
    } else {
      re += c;
    }
  }
  return new RegExp('^' + re + '$');
}

function fileMatchesGlobs(file, globs) {
  if (!Array.isArray(globs)) return false;
  return globs.some((g) => globToRegExp(String(g)).test(file));
}

// --------------------------------------------------------------------------
// Rule matching + deterministic checks
// --------------------------------------------------------------------------

function matchRules(rules, files) {
  const matched = [];
  for (const rule of rules) {
    if (!rule || !Array.isArray(rule.globs)) continue;
    const hitFiles = files.filter((f) => fileMatchesGlobs(f, rule.globs));
    if (hitFiles.length > 0) {
      matched.push({
        adr: rule.adr,
        area: rule.area,
        rule: rule.rule,
        globs: rule.globs,
        check: rule.check || null,
        matchedFiles: hitFiles,
        deterministic: !!rule.check,
      });
    }
  }
  return matched;
}

function evaluateChecks(matchedRules, files, projectDir) {
  const violations = [];
  for (const r of matchedRules) {
    if (!r.check) continue;
    const check = r.check;
    const scopeGlobs = Array.isArray(check.in_globs) && check.in_globs.length
      ? check.in_globs
      : r.globs;
    const targets = files.filter((f) => fileMatchesGlobs(f, scopeGlobs));

    // Vocabulary: forbid_pattern / require_absent (must NOT contain);
    // require_present (must contain). Literal substring — not regex — by design.
    const forbid = check.forbid_pattern ?? check.require_absent ?? null;
    const require = check.require_present ?? null;

    for (const rel of targets) {
      const abs = path.join(projectDir, rel);
      let content;
      try {
        content = fs.readFileSync(abs, 'utf8');
      } catch {
        continue; // deleted/binary/unreadable — skip
      }
      if (forbid != null && content.includes(forbid)) {
        violations.push({
          adr: r.adr, area: r.area, rule: r.rule, file: rel,
          kind: 'forbid_pattern', pattern: forbid,
          line: lineOf(content, forbid),
        });
      }
      if (require != null && !content.includes(require)) {
        violations.push({
          adr: r.adr, area: r.area, rule: r.rule, file: rel,
          kind: 'require_present', pattern: require, line: null,
        });
      }
    }
  }
  return violations;
}

function lineOf(content, needle) {
  const idx = content.indexOf(needle);
  if (idx === -1) return null;
  return content.slice(0, idx).split('\n').length;
}

// --------------------------------------------------------------------------
// File-set acquisition
// --------------------------------------------------------------------------

function git(args, projectDir) {
  try {
    return execFileSync('git', args, { cwd: projectDir, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  } catch {
    return '';
  }
}

function obtainFiles(scope, projectDir) {
  let out = [];
  if (scope === 'all') {
    out = git(['ls-files'], projectDir).split('\n');
  } else { // diff
    const sources = [
      git(['diff', '--name-only', 'HEAD'], projectDir),
      git(['diff', '--name-only', '--cached'], projectDir),
      git(['ls-files', '--others', '--exclude-standard'], projectDir),
    ];
    out = sources.join('\n').split('\n');
  }
  const seen = new Set();
  const files = [];
  for (const f of out) {
    const t = f.trim();
    if (t === '' || seen.has(t) || isExcluded(t)) continue;
    seen.add(t);
    files.push(t);
  }
  return files;
}

// --------------------------------------------------------------------------
// Public entry point (no process.exit — safe to require from the hook)
// --------------------------------------------------------------------------

function run(opts = {}) {
  const projectDir = opts.projectDir || process.cwd();
  const indexPath = opts.indexPath || path.join(projectDir, 'docs', 'adr', 'index.yaml');
  const scope = opts.scope === 'all' ? 'all' : 'diff';

  let index;
  try {
    index = loadIndex(indexPath);
  } catch (e) {
    return {
      degraded: true, error: e.message, scope, indexPath,
      matchedRules: [], violations: [], fileCount: 0,
    };
  }

  const files = (opts.files && opts.files.length)
    ? opts.files.filter((f) => !isExcluded(f))
    : obtainFiles(scope, projectDir);

  const matchedRules = matchRules(index.rules, files);
  const violations = evaluateChecks(matchedRules, files, projectDir);

  return { degraded: false, scope, indexPath, fileCount: files.length, matchedRules, violations, index };
}

// --------------------------------------------------------------------------
// Lint (§5.3 mechanical tier — the index-integrity invariants of AC2c)
// --------------------------------------------------------------------------

function lint(opts = {}) {
  const projectDir = opts.projectDir || process.cwd();
  const indexPath = opts.indexPath || path.join(projectDir, 'docs', 'adr', 'index.yaml');
  const errors = [];
  const warnings = [];

  let index;
  try {
    index = loadIndex(indexPath);
  } catch (e) {
    return { ok: false, errors: [e.message], warnings: [] };
  }

  // Bucket membership: no ADR in two buckets.
  const buckets = { rules: new Set(), superseded: new Set(), historical: new Set() };
  for (const r of index.rules) {
    if (!r || r.adr == null) { errors.push('a rule has no `adr`'); continue; }
    const id = String(r.adr);
    if (buckets.rules.has(id)) errors.push(`ADR ${id} appears twice in rules[]`);
    buckets.rules.add(id);
    if (!r.rule || String(r.rule).trim() === '') errors.push(`ADR ${id}: empty rule text`);
    if (!Array.isArray(r.globs) || r.globs.length === 0) errors.push(`ADR ${id}: no globs`);
    if (r.check) {
      const c = r.check;
      const hasOp = c.forbid_pattern != null || c.require_absent != null || c.require_present != null;
      if (!hasOp) errors.push(`ADR ${id}: check has no forbid_pattern/require_absent/require_present`);
    }
  }
  for (const id of Object.keys(index.superseded)) buckets.superseded.add(String(id));
  for (const id of Object.keys(index.historical)) buckets.historical.add(String(id));

  const seen = new Map();
  for (const [bucket, set] of Object.entries(buckets)) {
    for (const id of set) {
      if (seen.has(id)) errors.push(`ADR ${id} is in two buckets (${seen.get(id)} and ${bucket})`);
      else seen.set(id, bucket);
    }
  }

  // Coverage: every docs/adr/NNN-*.md appears in exactly one bucket, and vice versa.
  const adrDir = path.join(projectDir, index.adr_dir);
  let adrFiles = [];
  try {
    adrFiles = fs.readdirSync(adrDir).filter((f) => /^\d+-.*\.md$/.test(f));
  } catch {
    warnings.push(`ADR directory not readable: ${adrDir}`);
  }
  const onDisk = new Set(adrFiles.map((f) => f.match(/^(\d+)-/)[1]));
  for (const id of onDisk) {
    if (!seen.has(id) && !seen.has(String(parseInt(id, 10)))) {
      errors.push(`ADR ${id} exists on disk but is unindexed (in no bucket) — it is unenforced`);
    }
  }
  for (const id of seen.keys()) {
    const padded = [...onDisk].some((d) => parseInt(d, 10) === parseInt(id, 10));
    if (!padded) warnings.push(`ADR ${id} is indexed but has no matching file in ${index.adr_dir}`);
  }

  // Glob resolution: warn when a glob matches nothing tracked.
  if (opts.checkGlobs !== false) {
    const tracked = obtainFiles('all', projectDir);
    for (const r of index.rules) {
      if (!Array.isArray(r.globs)) continue;
      for (const g of r.globs) {
        if (!tracked.some((f) => globToRegExp(String(g)).test(f))) {
          warnings.push(`ADR ${r.adr}: glob "${g}" matches no tracked file`);
        }
      }
    }
  }

  return { ok: errors.length === 0, errors, warnings, counts: {
    rules: buckets.rules.size, superseded: buckets.superseded.size,
    historical: buckets.historical.size, onDisk: onDisk.size,
  } };
}

module.exports = {
  run, lint, loadIndex, parseYAML, matchRules, evaluateChecks,
  globToRegExp, fileMatchesGlobs, obtainFiles,
};

// --------------------------------------------------------------------------
// CLI
// --------------------------------------------------------------------------

function parseArgv(argv) {
  const opts = { scope: 'diff', format: 'json', exitCode: false, lint: false, files: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--scope=')) opts.scope = a.slice(8);
    else if (a === '--scope') opts.scope = argv[++i];
    else if (a.startsWith('--format=')) opts.format = a.slice(9);
    else if (a === '--exit-code') opts.exitCode = true;
    else if (a === '--lint') opts.lint = true;
    else if (a.startsWith('--project=')) opts.projectDir = a.slice(10);
    else if (a === '--project') opts.projectDir = argv[++i];
    else if (a.startsWith('--index=')) opts.indexPath = a.slice(8);
    else if (a === '--files') { opts.files = argv.slice(i + 1); break; }
    else if (a === '--pretty') opts.format = 'pretty';
  }
  return opts;
}

function printPretty(result) {
  if (result.degraded) {
    console.error(`[gsd-standards-guard] DEGRADED: ${result.error}`);
    console.error('  → consult docs/ARCHITECTURE.md decision index manually.');
    return;
  }
  console.log(`scope=${result.scope}  files=${result.fileCount}  matched=${result.matchedRules.length}  violations=${result.violations.length}`);
  for (const r of result.matchedRules) {
    const tag = r.deterministic ? '[check]' : '[semantic]';
    console.log(`  ${tag} ADR-${r.adr} (${r.area}): ${r.rule}`);
  }
  for (const v of result.violations) {
    console.log(`  VIOLATION ADR-${v.adr}: ${v.file}${v.line ? ':' + v.line : ''} — ${v.kind} "${v.pattern}"`);
  }
}

function main() {
  const opts = parseArgv(process.argv.slice(2));

  if (opts.lint) {
    const res = lint({ projectDir: opts.projectDir, indexPath: opts.indexPath });
    if (opts.format === 'json') {
      console.log(JSON.stringify(res, null, 2));
    } else {
      console.log(`lint: ${res.ok ? 'PASS' : 'FAIL'}  (${JSON.stringify(res.counts || {})})`);
      for (const e of res.errors) console.log(`  ERROR: ${e}`);
      for (const w of res.warnings) console.log(`  warn:  ${w}`);
    }
    process.exit(res.ok ? 0 : 1);
  }

  const result = run({ scope: opts.scope, projectDir: opts.projectDir, indexPath: opts.indexPath, files: opts.files });
  if (opts.format === 'pretty') printPretty(result);
  else console.log(JSON.stringify(result, (k, v) => (k === 'index' ? undefined : v), 2));

  if (opts.exitCode && result.violations.length > 0) process.exit(1);
  process.exit(0);
}

if (require.main === module) main();
