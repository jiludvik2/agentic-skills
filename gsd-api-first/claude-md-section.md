## API-First Workflow

For any phase that touches the API layer, use this extended workflow instead of the
standard GSD sequence:

```
/gsd-spec-phase <N>        ← lock WHAT (functional requirements only — generic GSD)
/gsd-discuss-phase <N>     ← lock HOW decisions; include .claude/api-gray-areas.md
/api-phase <N>             ← design HTTP contract from functional requirements
/api-plan <N>              ← plan with API-SPEC.md + governance docs auto-ingested
/gsd-execute-phase <N>     ← execute; Wave 0 MUST regenerate the OpenAPI spec
/gsd-verify-work <N>       ← UAT against the locked contract
```

### When each skill applies

| Situation | Use |
|-----------|-----|
| Phase adds or modifies any endpoint, parameter, response field, or error code | `/api-phase <N>` then `/api-plan <N>` |
| Phase is purely internal (adapters, data layer) with no API surface change | Standard `/gsd-plan-phase <N>` is fine |
| You ran `/gsd-plan-phase` and forgot the governance context for an API phase | Re-run as `/api-plan <N>` — it auto-discovers API-SPEC.md and governance docs |

### How /api-phase works

`/api-phase` asks the user only for **functional requirements**: what resources exist,
what operations are needed, who the consumers are, and what domain-specific error
conditions arise. All API design decisions (HTTP methods, URL structure, status codes,
naming convention, pagination strategy, error format, null semantics) are derived from
REST and HTTP industry practice without asking the user.

Design authority: Google API Design Guide, Zalando RESTful API Guidelines,
RFC 9457 Problem Details, OpenAPI Specification best practices.

### Breaking-change rule

A breaking change is any removal, rename, type change, or newly-required parameter on
an existing endpoint. `/api-phase` blocks until you provide an explicit change-ledger
entry. Never ship a breaking change as additive — consumers have no fallback.

### Upgrade safety

The project skills (`/api-phase`, `/api-plan`) live in `.agents/skills/` and are
tracked in git. The reference files live in `.claude/`. Neither location is touched by
GSD upgrades. To restore after an upgrade: `python3 ../gsd-api-first/install.py`
