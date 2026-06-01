// Fixture for s4 / G8: a JS function with unmistakable cyclomatic complexity (> 1)
// so the vendored ESLint `complexity` rule (threshold 0) reports a stable, non-trivial
// value. The TypeScript counterpart is branchy.ts (ADR-0022 TS follow-up).
function branchy(a, b) {
  if (a) {
    return 1;
  } else if (b) {
    return 2;
  } else if (a && b) {
    return 3;
  }
  return a || b ? 4 : 5;
}

module.exports = { branchy };
