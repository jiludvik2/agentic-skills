// Fixture for s4 / G8: a JS function with unmistakable cyclomatic complexity (> 1)
// so the vendored ESLint `complexity` rule (threshold 0) reports a stable, non-trivial
// value. JS-only — jscomplexity does not cover TypeScript (ADR-0022 s4-t1 amendment).
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
