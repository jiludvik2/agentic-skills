---
id: s0-fix2-empty-sarif-shape-consistency
kind: task
project: code-review
status: done
parent: s0-analyzer-facade-and-two-adapters
sources: [s0-fix1-reviewer, s0-fix1-verifier]
created: 2026-05-26
updated: 2026-05-26
notes: |
  s0-fix1 Reviewer Minor (not filed separately): add coupling == {} assertion to Radon test.
---

# s0-fix2 — Consistent empty-SARIF shape for both adapters

## Outcome

Both adapters return a structurally identical empty-SARIF on the early-return path:
`{"$schema": "...", "version": "2.1.0", "runs": []}` — same shape as the non-empty path.

## Acceptance Criteria

- `SemgrepAdapter.run(empty_paths).sarif` passes through `_normalise()` so it includes `$schema`.
- `RadonAdapter.run(empty_paths).sarif` has `"runs": []` (not a one-element list).
- Both adapter empty-paths tests assert `output.sarif.get("runs") == []`.
