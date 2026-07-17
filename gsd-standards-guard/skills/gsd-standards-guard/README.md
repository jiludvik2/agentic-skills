# gsd-standards-guard — rule engine

Not a prompt-skill. `engine.js` is a plain Node executable (stdlib only) that the
PreToolUse hook and `/standards-audit` both call. It is the single authority for:
given a file set, (a) which standing rules from `docs/adr/index.yaml` apply
(glob match) and (b) where a rule carries a `check:`, whether the files violate
it (deterministic tier). One rule table, one matcher, one code path — the two
callers cannot drift.

```bash
# Rules + violations for the current diff (JSON — what the hook consumes):
node engine.js --scope=diff

# Whole tree, human-readable, exit non-zero on any deterministic violation (CI):
node engine.js --scope=all --exit-code --pretty

# Validate the index (bucket integrity, coverage, glob resolution):
node engine.js --lint --pretty

# Explicit file set (used by the hook when a phase manifest is available, and by tests):
node engine.js --scope=diff --files a/b.py c/d.tsx
```

`--scope` only selects *how the file set is obtained* (`diff` = git working
changes; `all` = `git ls-files`); `--files` overrides it. Rule resolution is
identical either way.

The YAML reader is a **scoped parser** for the `index.yaml` schema (see
`templates/index.yaml`), not a general YAML implementation — the `--lint` gate
keeps the file inside that shape. `check:` vocabulary is deliberately tiny:
`forbid_pattern` / `require_absent` (literal substring must be absent) and
`require_present` (must be present), each within an `in_globs` path set. Anything
needing real judgment stays a semantic rule (no `check:`).
