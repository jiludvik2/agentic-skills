## API-First Workflow

For any phase that touches the API layer, insert one extra step — `/api-spec` — into the
standard GSD sequence. There is no replacement planner: `/api-spec` registers the contract
where the normal `/gsd-plan-phase` already looks for it.

```
/gsd-spec-phase <N>        ← lock WHAT (functional requirements only — generic GSD)
/gsd-discuss-phase <N>     ← lock HOW decisions
/api-spec <N>             ← design the HTTP contract; register it in CONTEXT.md <canonical_refs>
/gsd-plan-phase <N>        ← standard GSD planner; reads the contract via <canonical_refs>
/gsd-execute-phase <N>     ← execute; Wave 0 MUST regenerate the OpenAPI spec
/gsd-verify-work <N>       ← UAT against the locked contract
```

### When each skill applies

| Situation | Use |
|-----------|-----|
| Phase **adds a new endpoint/resource, changes an endpoint's shape, or makes a breaking change** (removal, rename, type change, newly-required param) | Full chain: `/api-spec <N>` → `/gsd-plan-phase <N>` → execute |
| Phase makes a **trivial additive change** — one new optional field, one new enum value, a defect fix restoring already-intended behaviour — with no design decision to make | **Go light** (see below) — no contract, no discuss/plan ceremony |
| Phase is **purely internal** (adapters, data layer) with no API surface change | Standard `/gsd-plan-phase <N>` — skip `/api-spec` |

There is no separate planning command to remember. Once `/api-spec` has run, the contract
is referenced from `CONTEXT.md`, so any subsequent `/gsd-plan-phase` for that phase reads it
automatically — no wrapper, no `--ingest` flag.

**Going light.** When the only API change is trivially additive and the correct behaviour is
already specified, the full spec→discuss→plan chain is empty ceremony. Keep the rigor gates,
drop the planning: write the failing test first → make the change → run the suite → `/verify`
the affected flow → `/code-review` the diff → commit. Record it as a fix commit, not a new phase.

**The one check before going light:** a new enum value is breaking for any consumer that does an
exhaustive `switch`/`match` with no default branch. If such a consumer exists, treat it as a
breaking change and run the full chain. Otherwise it stays additive — go light.

**When unsure, let `/api-spec`'s verdict decide:** run it; if it classifies every change as
ADDITIVE and there's no open design question, you didn't need discuss/plan — proceed straight
to execute. A BREAKING classification always means the full chain.

### How /api-spec works

`/api-spec` asks the user only for **functional requirements**: what resources exist,
what operations are needed, who the consumers are, and what domain-specific error
conditions arise. All API design decisions (HTTP methods, URL structure, status codes,
naming convention, pagination strategy, error format, null semantics) are derived from
REST and HTTP industry practice without asking the user.

It writes the full contract to `{phase_dir}/XX-API-SPEC.md`, then registers that path in the
phase `CONTEXT.md` `<canonical_refs>` block. GSD requires planning and implementing agents to
read every file listed there, so the planner, researcher, and plan-checker all pick up the
contract with no further wiring. The registration is idempotent — re-running `/api-spec`
updates the entry in place rather than duplicating it.

Design authority: Google API Design Guide, Zalando RESTful API Guidelines,
RFC 9457 Problem Details, OpenAPI Specification best practices.

### Breaking-change rule

A breaking change is any removal, rename, type change, or newly-required parameter on
an existing endpoint. `/api-spec` blocks until you provide an explicit change-ledger
entry. Never ship a breaking change as additive — consumers have no fallback.

### Upgrade safety

The project skill (`/api-spec`) and its reference files live in `.claude/` and are
tracked in git. That location is not touched by GSD upgrades. To restore
after an upgrade: `../gsd-api-first/install.sh`
