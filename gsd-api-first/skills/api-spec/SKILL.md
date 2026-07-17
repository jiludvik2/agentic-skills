---
name: api-spec
description: "Design the HTTP API contract for a phase — a new API surface or a change to an existing one — then register it in the phase CONTEXT.md <canonical_refs> so the planner reads it automatically. The user provides WHAT the API must do; the skill derives HOW from REST/HTTP industry practice (Google AIP, Zalando, RFC 9457, OpenAPI), conforming to any existing conventions and classifying every change as additive or breaking. Run before /gsd-plan-phase for any phase that adds or changes the API surface."
argument-hint: "<phase>"
allowed-tools:
  - Read
  - Write
  - Bash
  - Glob
  - Grep
  - AskUserQuestion
---

<objective>
Produce a locked HTTP API design contract (API-SPEC.md) before the planner runs — whether
this phase creates a **new API surface** or **changes an existing one**. Both are first-class:
for a new surface the design is derived from industry practice and defaults; for an existing
surface the skill conforms to the established conventions, diffs the proposal against the
current surface, and classifies every change as additive or breaking.

**The user's job:** Describe the functional requirements — what resources exist, what operations are needed, who the consumers are, and what the domain-specific error conditions are.

**The skill's job:** Apply REST and HTTP industry practice to derive all API design decisions — HTTP methods, URL structure, status codes, naming convention, pagination strategy, error format, null semantics, and envelope shape. The user should not be asked to make any of these design decisions.

**Design authority:** Google API Design Guide, Zalando RESTful API Guidelines, Microsoft Azure REST API Best Practices, RFC 9457 (Problem Details), OpenAPI Specification best practices.

**Position in workflow:** spec-phase → discuss-phase → **api-spec** → gsd-plan-phase → execute-phase → verify
</objective>

<context>
Phase number: $ARGUMENTS (required)
</context>

<process>
Execute every step in order. Do not skip any.

## Step 0 — Prerequisites check

Before doing anything else, verify:

1. **Phase argument provided:** $ARGUMENTS must not be empty. If it is, stop and tell the user: `Usage: /api-spec <phase-number>`

2. **GSD initialized:** `.planning/` directory must exist and `ROADMAP.md` must be readable at the project root. If either is missing, stop and tell the user: `GSD is not initialized in this project. Run /gsd-new-project or ensure ROADMAP.md and .planning/ exist before using /api-spec.`

If any check fails, stop immediately — do not proceed to Step 1.

## Step 1 — Resolve phase

Parse the phase number from $ARGUMENTS. Find the phase directory under `.planning/phases/`. Load ROADMAP.md to confirm the phase exists and read its description. If the phase cannot be found, ask the user.

## Step 2 — Discover project API context (parallel reads)

Read whichever of these exist. Do not assume any specific paths — check each possibility.

**Committed OpenAPI spec (baseline for existing API surface):**
`openapi.json`, `openapi.yaml`, `openapi.yml`, `swagger.json`, `swagger.yaml`,
`api/openapi.json`, `docs/openapi.json`, `src/openapi.json`

**Governance and design precedents (to discover established patterns):**
`docs/adr/*.md`, `adr/*.md`, `docs/decisions/*.md`,
`docs/ARCHITECTURE.md`, `docs/STANDARDS.md`, `docs/API.md`,
`.planning/phases/*/[0-9][0-9]-API-SPEC.md` (prior contracts from earlier phases)

**Phase context (if produced by earlier workflow steps):**
`{phase_dir}/XX-SPEC.md`, `{phase_dir}/XX-CONTEXT.md`

Note what was found. Derive the project's established patterns from any existing API surface (envelope shape, error format, naming convention). Where no pattern is established yet, the skill decides based on consumer type (Step 4).

## Step 3 — Determine mode and summarise the existing surface

**Determine the mode** from what Step 2 found, and state it explicitly — it drives Steps 4, 6, and 9:

- **NEW API** — no committed OpenAPI baseline and no prior `*-API-SPEC.md` covers the
  resources this phase touches. The design is derived from industry practice and defaults.
- **EXISTING API** — a committed baseline (OpenAPI spec and/or a prior contract) exists and
  this phase adds to or modifies that surface. Established conventions become **hard
  constraints**, and every change is diffed against the baseline and classified (Steps 6–7).

A phase is EXISTING even when it only adds brand-new endpoints: if a baseline exists, the new
endpoints must conform to it. A single phase can also be mixed (some endpoints modify existing
ones, others are new) — treat it as EXISTING and mark each endpoint's status in Steps 6 and 9.

**Summarise the baseline.** If an OpenAPI spec and/or prior contract was found, print a
compact table of the current surface relevant to this phase:

| Path | Method(s) | Brief purpose | Relationship to this phase |
|------|-----------|---------------|----------------------------|
| ...  | ...       | ...           | new / modified / unchanged |

State the committed spec version and the established patterns (envelope shape, error format,
naming convention, versioning, pagination). If no baseline exists, state: **mode = NEW API
(greenfield surface)** and skip the table.

## Step 4 — Derive design draft from project context

Do not ask the user any questions yet. Read the context gathered in Steps 1–3 plus the
codebase and infer every design decision using the rules below. The goal is to produce
a complete proposed API contract before the user is asked anything.

**Mode drives the rules below.** In **EXISTING API** mode the established conventions from
Step 3 (naming, envelope, error format, versioning, pagination, identifiers) are **binding
constraints** — match them exactly even where a different greenfield default would otherwise
apply, and reuse existing request/response shapes for anything the change extends. The
greenfield defaults and heuristics below apply in **NEW API** mode, or to a genuinely new,
independent resource group within an existing API that shares no shape with current
endpoints. Never silently introduce a second convention into an existing surface; if the
existing surface violates a best practice, conform to it and record the deviation as a note
rather than "fixing" it inside an unrelated change (a convention migration is its own phase).

**Consumer type** — infer from:
- Presence of a frontend (React/Vue/Angular/Next.js files, `package.json` with browser deps) → browser/web
- Mobile-specific directories (`ios/`, `android/`, React Native, Flutter) → mobile
- Project description, CLAUDE.md, README describing a public or partner API → external/public
- No frontend code, internal service or CLI project → server-to-server/internal
- Multiple signals present → list all that apply; this affects naming convention

**Naming convention** — infer from:
- Existing API JSON field names: follow whatever is already in use (snake_case or camelCase)
- If greenfield: browser/mobile consumer → `camelCase`; backend/analytics/agent/internal consumer → `snake_case`
- URL path segments are always `kebab-case` regardless (Zalando MUST rule)

**Resources and operations** — derive from:
- Phase SPEC.md or CONTEXT.md: what entities/resources does this phase introduce or change?
- Use the domain vocabulary from those documents verbatim — do not invent generic names
- Infer which CRUD operations the phase requires from the phase goal and UAT criteria
- Map to HTTP methods: list → `GET /{resources}`, get one → `GET /{resources}/{id}`,
  create → `POST /{resources}` (201 + Location header), full replace → `PUT /{resources}/{id}` (200),
  partial update → `PATCH /{resources}/{id}` (200), delete → `DELETE /{resources}/{id}` (204)
- Custom actions that do not fit CRUD → `POST /{resources}/{id}/{action-noun}` — never verb URLs
- Sub-resource nesting: only propose `/{resource}/{id}/{sub-resource}` when the sub-resource
  genuinely cannot exist without its parent; cap nesting at one level

**Identifiers** — infer from:
- Existing models or database schemas (UUID, integer ID, slug, composite key)
- Domain conventions visible in the codebase
- Default to UUID if no evidence exists

**Pagination** — infer from:
- Existing paginated endpoints: follow the same strategy already in use
- If greenfield: apply the domain scale heuristic —
  - Reference/catalogue data (≤1k items, rarely mutated) → unbounded with a hard row cap and documented size invariant
  - Typical business entities (orders, invoices, users — thousands to tens of thousands) → offset/limit (`?offset=0&limit=20`, max 100)
  - High-volume or high-mutation data (events, logs, timeseries) → cursor/keyset (`?cursor=<opaque>&limit=20`, `next_cursor` in metadata)

**Filterable and sortable fields** — infer from:
- Fields referenced in phase UAT criteria or SPEC.md
- Fields that appear in existing query parameters on analogous endpoints
- Obvious domain fields (status, date range, owner/tenant ID)

**Domain error conditions** — infer the obvious ones from domain context:
- State machine violations (e.g. "cancel after shipped", "publish without content") — look for state fields or status enums in the codebase
- Uniqueness/conflict conditions — look for unique constraints in schema or model definitions
- Prerequisite violations visible in the phase spec
- Mark inferred errors clearly as `[inferred]`; note any operations where domain errors are unclear

**Evolution and versioning** — infer from:
- Existing API versioning (URL prefix `/v1/`, `api-version` header, date versioning)
- ADRs or ARCHITECTURE.md mentioning versioning policy
- If no existing surface: internal service → no versioning (coordinate upgrades); external/public → URL versioning (`/v1/`)

**Status codes** — fixed by industry practice, not a user decision:

| Condition | Code |
|-----------|------|
| Successful read/update | 200 |
| Successful creation | 201 |
| Successful delete or action with no body | 204 |
| Malformed syntax (unparseable request) | 400 |
| Missing or invalid credentials | 401 |
| Authenticated but not permitted | 403 |
| Resource does not exist | 404 |
| State conflict (duplicate, version mismatch) | 409 |
| Syntactically valid but semantically invalid | 422 |
| Rate limit exceeded | 429 |
| Server-side fault | 500 |

**Collection response envelope** — fixed, never a bare array:
```json
{
  "data": [...],
  "metadata": {
    "total_count": 142,
    "has_more": true,
    "offset": 0,
    "limit": 20
  }
}
```

**Error format** — fixed by RFC 9457:
```
Content-Type: application/problem+json
```
```json
{
  "type": "https://{api-domain}/errors/{kebab-slug}",
  "title": "Human-readable summary (same string every time for this type)",
  "status": 422,
  "detail": "Instance-specific explanation for THIS request",
  "errors": [{"field": "quantity", "reason": "Must be a positive integer"}]
}
```

**Null semantics** — default convention:
- `null` = field applies but value is currently unavailable (transient)
- Absent key = field does not apply to this resource type (structural)
- Deviate only when the existing codebase uses a different convention — follow whatever is in use

**Idempotency** — infer from consumer type:
- Mobile or external consumers: propose `Idempotency-Key` header on POST operations
- Internal services with retry-safe infrastructure: optional, do not propose by default

After applying all rules, produce a complete draft contract:

1. **Inferred context table** — what was inferred and from what evidence:

   | Decision | Inferred value | Evidence |
   |----------|---------------|---------|
   | Consumer type | ... | ... |
   | Naming convention | ... | ... |
   | Versioning policy | ... | ... |
   | Pagination strategy | ... | ... |

2. **Proposed endpoint table**:

   | Method | Path | Purpose | Success code | Notes |
   |--------|------|---------|-------------|-------|
   | GET | /resources | List all | 200 | offset/limit pagination |
   | POST | /resources | Create | 201 + Location | ... |

3. **Proposed domain error table** (business-rule violations only):

   | Operation | Condition | Status | `type` slug | `[inferred]`? |
   |-----------|-----------|--------|------------|--------------|
   | ... | ... | ... | ... | ... |

4. **Open questions** — list any decisions that could not be confidently inferred,
   labelled by category (consumer type, domain errors, identifiers, etc.).

## Step 5 — Confirm draft with user (single question)

Present the draft from Step 4 concisely. Use AskUserQuestion with **one question**:

> "Here's the proposed API design. Does anything need to change? Note any corrections,
> additions, or missing domain error conditions — I'll incorporate them before writing
> the spec."

Also ask about any **open questions** from Step 4 in the same message (keep to a
maximum of three; if more than three are unresolved, pick the three with the highest
impact on the contract shape).

Apply the user's corrections. If a correction introduces a genuinely new design
decision not covered by the inference rules, apply industry practice to resolve it —
do not open a new question round unless the user's input is contradictory or
ambiguous.

## Step 6 — Classify every change against the baseline

In **NEW API** mode there is no baseline, so every endpoint is new and additive by
definition — state that and skip the breaking-change gate (Step 7).

In **EXISTING API** mode, diff every proposed endpoint, parameter, response field, status
code, and error against the baseline captured in Steps 2–3, and classify each using this
taxonomy:

**ADDITIVE (safe — no gate required):**
- New endpoint not in the current spec
- New optional query parameter with a documented default
- New optional response field (always in schema, nullable if sometimes absent)
- New enum value on an existing field (note: breaking for exhaustive switch consumers — ask if any exist)
- New ProblemDetail `type` slug for a genuinely new error condition
- Accepting a wider range of valid input (less strict validation)

**BREAKING (requires explicit approval and a change-ledger entry):**
- Removing or renaming an endpoint, parameter, or response field
- Changing a field's type (string → integer, or any type narrowing)
- Making an optional parameter required
- Removing an enum value
- Changing the HTTP method of an existing endpoint
- Changing a success status code or error status code
- Changing the Content-Type of an error response
- Adding a required auth check to a previously open endpoint
- Changing the semantics of a field (same name, different meaning)

Present the full classification table. Ask for confirmation.

## Step 7 — Breaking-change gate

If ANY change is classified as BREAKING:

Ask the user for both:
1. Explicit confirmation the break is intentional (not accidental drift)
2. A change-ledger entry: one-line description of what breaks and what the new contract is

Do not proceed to Step 8 until both are given.

## Step 8 — Validate against REST/HTTP invariants

Apply these checks to the proposed contract. Flag violations as blockers.

**HTTP method semantics:**
- [ ] GET/HEAD are safe (no side effects); GET is idempotent
- [ ] PUT and DELETE are idempotent
- [ ] No verb in any URL path segment (`/orders`, not `/getOrders` or `/create-order`)
- [ ] Custom actions use POST with a noun path segment (`POST /orders/{id}/cancellation`, not `POST /cancel-order`)

**Status codes:**
- [ ] Successful creation returns 201 (not 200)
- [ ] Successful delete with no body returns 204 (not 200)
- [ ] Business rule violations return 422 (not 400)
- [ ] State conflicts return 409 (not 400 or 422)
- [ ] Auth failures use 401 (missing credentials) or 403 (insufficient permissions) correctly
- [ ] No 5xx for client input errors

**Collection responses:**
- [ ] Every collection endpoint returns `{data: [...], metadata: {...}}` — never a bare array
- [ ] `metadata` includes `has_more` (boolean) and enough information to retrieve the next page
- [ ] A maximum page size is documented and enforced with a 422 if exceeded

**Error contract:**
- [ ] All client errors return `application/problem+json` body following RFC 9457
- [ ] Each named error condition has a stable `type` URI slug
- [ ] `title` is the same string for every instance of a given `type`
- [ ] Stack traces and internal identifiers (DB column names, class names) do not appear in error bodies

**Naming:**
- [ ] All URL path segments are `kebab-case`
- [ ] JSON field names follow the project's chosen convention (snake_case or camelCase) consistently
- [ ] Boolean fields use positive predicates (`is_active`, not `not_deleted`)
- [ ] Date/time fields carry timezone context (ISO 8601 with `Z` or offset)
- [ ] Currency amount fields are paired with a `currency` field (ISO 4217)

**Nullability:**
- [ ] Every nullable field has a documented meaning for absence
- [ ] `null` and "absent key" are not used interchangeably without documentation

**Consistency with established patterns:**
- [ ] New endpoints follow the envelope shape established by existing endpoints
- [ ] Error bodies follow the established error format

## Step 9 — Write API-SPEC.md

Fill the `.claude/templates/API-SPEC.md` template (if it exists in the project) or use the standard sections listed in the template. Write to `{phase_dir}/XX-API-SPEC.md`.

State the **mode** (NEW API / EXISTING API) at the top of the spec. Then include:
- Every endpoint the phase touches, each tagged with its status — **NEW**, **MODIFIED**,
  **DEPRECATED**, or **UNCHANGED (referenced)**. Unchanged endpoints are referenced by path
  for context so the planner sees the whole surface, not redefined in full.
- A concrete JSON example for every new or changed endpoint — use realistic values, not placeholder strings
- One ProblemDetail example per named error condition
- The derived design decisions (HTTP methods, status codes, envelope shape, naming convention) as explicit statements, not implicit
- All null semantics decisions as a table
- The invariant sign-off checklist

**In EXISTING API mode**, also include a **"Changes to existing surface"** section: the
additive/breaking classification table from Step 6 and, for every breaking change, the
change-ledger entry plus a short migration/deprecation note (what consumers must do, and any
versioning or sunset plan). For MODIFIED endpoints, show the before → after so the planner
can see the delta, not just the new state. In NEW API mode, state that there is no prior
surface and this section is not applicable.

## Step 10 — Register the contract in CONTEXT.md (`<canonical_refs>`)

This is what makes `gsd-plan-phase` pick up the contract with **no wrapper and no
`--ingest`**. The planner does not auto-discover arbitrary documents; it reads the phase
`CONTEXT.md` and treats the file paths listed in its `<canonical_refs>` block as required
reading (GSD rule: "agents must read listed files before planning or implementing").
Registering the spec there routes it to the planner, the researcher, and the
plan-checker automatically.

`CONTEXT.md` is normally a sealed, discuss-owned artifact. This one entry is the single
sanctioned exception — keep the edit surgical and touch nothing else.

1. **Locate** the phase context at `{phase_dir}/XX-CONTEXT.md`.
   - If it does not exist, warn:
     `CONTEXT.md not found for phase XX — run /gsd-discuss-phase XX first so the contract can be registered for the planner.`
     Then skip the rest of this step (the spec is still written and committed in Step 11).

2. **Read** `CONTEXT.md` and find the `<canonical_refs> … </canonical_refs>` block.
   - If the block is missing, insert one immediately after the `<decisions>` block (or at
     end of file if `<decisions>` is absent), with the standard header comment and the
     single entry from step 3.

3. **Build the entry** — a bullet in the block's existing style, with the path RELATIVE
   to the project root:
   ``- `{project-relative path to XX-API-SPEC.md}` — Locked HTTP API design contract for this phase (produced by /api-spec)``

4. **Write idempotently** — this step may run again (corrections, breaking-change gate,
   re-derivation):
   - If a line already references this phase's `XX-API-SPEC.md`, **replace that line in
     place** — never add a duplicate.
   - Otherwise, append the entry as the last item inside `<canonical_refs>`.
   - Do **not** reorder, reformat, or modify any other entry or block. Preserve all
     existing content, spacing, and the `<canonical_refs>` header comment exactly.

5. Report: `Registered {project-relative path} in CONTEXT.md <canonical_refs>`.

## Step 11 — Commit atomically

Commit the spec and the CONTEXT.md registration together so the contract and its planner
hand-off land in one revision:

```bash
git add {phase_dir}/XX-API-SPEC.md {phase_dir}/XX-CONTEXT.md
git commit -m "contract(phase-XX): API design contract — <one-line summary>"
```

(If CONTEXT.md was absent and Step 10 was skipped, `git add` the spec only.)

## Step 12 — Report and next step

Print:
- N additive changes, M breaking changes
- Gate result
- Path of written spec
- Whether the contract was registered in `CONTEXT.md <canonical_refs>` (or the warning if CONTEXT.md was missing)
- Next step: `/gsd-plan-phase <phase>` — the standard GSD planner. It reads this contract
  automatically via the `<canonical_refs>` entry; no `/api-plan`, wrapper, or `--ingest`
  flag is needed.
</process>

<success_criteria>
- No more than one AskUserQuestion round before the spec is written (plus the breaking-change gate if applicable)
- All design decisions derived from project context and industry practice before asking the user anything
- The single confirmation question includes the complete draft contract and at most three open questions
- User corrections applied without opening additional question rounds
- Mode (NEW API vs EXISTING API) determined and stated; in EXISTING API mode the established conventions are treated as binding constraints and the proposal is diffed against the baseline
- Every proposed change classified as additive or breaking (in NEW API mode, all endpoints are new/additive and the breaking-change gate is skipped)
- Endpoints in the spec tagged NEW / MODIFIED / DEPRECATED / UNCHANGED, with before→after deltas for modified endpoints in EXISTING API mode
- Breaking changes explicitly approved with change-ledger entry recorded, and migration/deprecation notes captured in the spec
- All invariant groups checked (or violations resolved) before the spec is written
- Concrete JSON examples for every endpoint and error condition
- The written API-SPEC.md path registered in the phase `CONTEXT.md <canonical_refs>` block (idempotently; no duplicate entry on re-run), or a clear warning if CONTEXT.md was absent
- API-SPEC.md and the CONTEXT.md registration committed atomically
- User knows next step is `/gsd-plan-phase <phase>`, which reads the contract automatically via `<canonical_refs>`
</success_criteria>
