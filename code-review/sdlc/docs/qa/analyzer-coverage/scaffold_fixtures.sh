#!/usr/bin/env bash
#
# scaffold_fixtures.sh — (re)generate the synthetic fixtures used by the
# analyzer-coverage smoke test. Each fixture plants exactly the defect(s) the
# matching analyzer is expected to surface. Idempotent: wipes and rewrites
# fixtures/ on every run. Persisted so the test set is reviewable AND
# regenerable. See README.md for the analyzer→fixture map.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
F="${HERE}/fixtures"
rm -rf "${F}"
mkdir -p "${F}/python/couplingpkg" "${F}/deps" "${F}/js/src" "${F}/api"

# ── Python: security (bandit + semgrep) ──────────────────────────────────────
cat > "${F}/python/sec_vuln.py" <<'PY'
"""Planted security defects for bandit + semgrep."""
import subprocess
import hashlib
import pickle


def run_shell(cmd: str) -> int:
    return subprocess.call(cmd, shell=True)  # bandit B602 / shell injection


def weak_hash(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()  # bandit B324 weak hash


def run_eval(expr: str):
    return eval(expr)  # bandit B307 / dangerous eval


def load_untrusted(data: bytes):
    return pickle.loads(data)  # bandit B301 / insecure deserialization
PY

# ── Python: secrets (gitleaks; trivy secret scanner) ─────────────────────────
cat > "${F}/python/secrets_leak.py" <<'PY'
"""Planted hardcoded secrets for gitleaks. All values are well-known dummies."""
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
GITHUB_PAT = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
SLACK_TOKEN = "xoxb-0000000000-0000000000000-abcdefghijklmnopqrstuvwx"
PY

# ── Python: complexity (radon — emits METRICS, not findings) ─────────────────
cat > "${F}/python/complex_fn.py" <<'PY'
"""High cyclomatic-complexity function for radon (reported via metrics.per_file)."""


def tangled(a, b, c, d, e):
    total = 0
    for i in range(a):
        if i % 2 == 0:
            if b > 0:
                total += 1
            elif b < 0:
                total -= 1
            else:
                total += 2
        elif i % 3 == 0:
            if c > 0:
                total += 3
            else:
                total -= 3
        else:
            if d > 0 and e > 0:
                total += 4
            elif d < 0 or e < 0:
                total -= 4
            else:
                total += 5
    while total > 100:
        total -= 10
        if total % 7 == 0:
            break
    return total
PY

# ── Python: dead code (vulture) ──────────────────────────────────────────────
cat > "${F}/python/dead_code.py" <<'PY'
"""Planted dead code for vulture."""
import os  # unused import

USED = 1


def used_function():
    return USED


def _unused_function():  # never called
    leftover = 42  # unused local
    return 1


class UnusedClass:  # never instantiated
    pass
PY

# ── Python: low cohesion (cohesion) ──────────────────────────────────────────
cat > "${F}/python/low_cohesion.py" <<'PY'
"""A god-ish class whose methods touch disjoint attributes -> low cohesion."""


class GrabBag:
    def __init__(self):
        self.alpha = 1
        self.beta = 2
        self.gamma = 3
        self.delta = 4

    def only_alpha(self):
        return self.alpha

    def only_beta(self):
        return self.beta

    def unrelated(self):
        return 42

    def also_unrelated(self, x):
        return x * 2
PY

# ── Python: coupling / high fan-out (pydeps) ─────────────────────────────────
echo '"""Coupling fixture package for pydeps high-fan-out detection."""' \
    > "${F}/python/couplingpkg/__init__.py"
for i in $(seq -w 0 11); do
    echo "VALUE_${i} = ${i}" > "${F}/python/couplingpkg/mod${i}.py"
done
{
    echo '"""Hub module importing 12 siblings -> fan-out 12 (>= threshold 10)."""'
    for i in $(seq -w 0 11); do
        echo "from couplingpkg import mod${i}"
    done
    echo ''
    echo 'TOTAL = ('
    for i in $(seq -w 0 11); do
        echo "    mod${i}.VALUE_${i} +"
    done
    echo '    0'
    echo ')'
} > "${F}/python/couplingpkg/hub.py"

# ── Python deps: vulnerable dependencies (trivy) ─────────────────────────────
cat > "${F}/deps/requirements.txt" <<'REQ'
PyYAML==5.1
requests==2.19.0
REQ

# ── JS/TS project (eslint, knip, jscpd, depcruiser) ──────────────────────────
cat > "${F}/js/package.json" <<'JSON'
{
  "name": "qa-js-fixture",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "main": "src/index.ts"
}
JSON

cat > "${F}/js/tsconfig.json" <<'JSON'
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noEmit": true
  },
  "include": ["src/**/*.ts"]
}
JSON

cat > "${F}/js/knip.json" <<'JSON'
{
  "$schema": "https://unpkg.com/knip@5/schema.json",
  "entry": ["src/index.ts"],
  "project": ["src/**/*.ts"]
}
JSON

cat > "${F}/js/eslint.config.js" <<'JS'
export default [
  {
    files: ["**/*.js"],
    rules: {
      "no-unused-vars": "error",
      "no-debugger": "error",
    },
  },
];
JS

cat > "${F}/js/lint_me.js" <<'JS'
// Planted ESLint violations: unused var + debugger statement.
const unusedVar = 42;

function foo() {
  debugger;
  return 1;
}

foo();
JS

# entry uses only `usedExport` -> knip flags `unusedExport`
cat > "${F}/js/src/index.ts" <<'TS'
import { usedExport } from "./lib";

console.log(usedExport());
TS

cat > "${F}/js/src/lib.ts" <<'TS'
export function usedExport(): number {
  return 1;
}

// Never imported anywhere -> knip "unused export".
export function unusedExport(): number {
  return 2;
}
TS

# clone_a / clone_b: identical block -> jscpd duplication
for n in clone_a clone_b; do
cat > "${F}/js/src/${n}.ts" <<'TS'
export function computeStatistics(values: number[]): Record<string, number> {
  const count = values.length;
  const total = values.reduce((acc, v) => acc + v, 0);
  const mean = count === 0 ? 0 : total / count;
  const sorted = [...values].sort((a, b) => a - b);
  const median = count === 0 ? 0 : sorted[Math.floor(count / 2)];
  const max = count === 0 ? 0 : sorted[count - 1];
  const min = count === 0 ? 0 : sorted[0];
  return { count, total, mean, median, max, min };
}
TS
done

# dependency-cruiser config (the adapter passes no --config; depcruise requires one)
cat > "${F}/js/.dependency-cruiser.cjs" <<'CJS'
module.exports = {
  forbidden: [
    { name: "no-circular", severity: "error", from: {}, to: { circular: true } },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
  },
};
CJS

# cycle_a <-> cycle_b: circular dependency -> depcruiser
cat > "${F}/js/src/cycle_a.ts" <<'TS'
import { banana } from "./cycle_b";

export function apple(): number {
  return banana() + 1;
}
TS
cat > "${F}/js/src/cycle_b.ts" <<'TS'
import { apple } from "./cycle_a";

export function banana(): number {
  return (apple ? 1 : 0) + 2;
}
TS

# ── API for contract testing (schemathesis) ──────────────────────────────────
cat > "${F}/api/app.py" <<'PY'
"""Minimal FastAPI app whose 200 response violates its advertised schema.

The OpenAPI doc advertises the `User` model (id + user_name required), but the
handler returns a raw JSONResponse missing `user_name`, bypassing FastAPI's
response validation. Schemathesis' response_schema_conformance check should flag
a JsonSchemaError -> ruleId schemathesis.response_schema_violation.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI()


class User(BaseModel):
    id: int
    user_name: str


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: int) -> JSONResponse:
    # BUG: omits the required `user_name` field.
    return JSONResponse({"id": user_id})
PY

echo "Fixtures scaffolded under ${F}"
