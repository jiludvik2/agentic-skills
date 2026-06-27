---
name: api-phase
description: "Design a complete HTTP API contract from functional requirements. The user provides WHAT the API must do; the skill derives HOW from REST/HTTP industry practice (Google AIP, Zalando, RFC 9457, OpenAPI). Run before /api-plan or /gsd-plan-phase for any phase that adds or changes the API surface."
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
Produce a locked HTTP API design contract (API-SPEC.md) before the planner runs.

**The user's job:** Describe the functional requirements — what resources exist, what operations are needed, who the consumers are, and what the domain-specific error conditions are.

**The skill's job:** Apply REST and HTTP industry practice to derive all API design decisions — HTTP methods, URL structure, status codes, naming convention, pagination strategy, error format, null semantics, and envelope shape. The user should not be asked to make any of these design decisions.

**Design authority:** Google API Design Guide, Zalando RESTful API Guidelines, Microsoft Azure REST API Best Practices, RFC 9457 (Problem Details), OpenAPI Specification best practices.

**Position in workflow:** spec-phase → discuss-phase → **api-phase** → api-plan → execute-phase → verify
</objective>

<context>
Phase number: $ARGUMENTS (required)
</context>

<process>
Execute every step in order. Do not skip any.

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

## Step 3 — Summarise existing API surface

If an OpenAPI spec was found, print a compact table of the current surface:

| Path | Method(s) | Brief purpose |
|------|-----------|---------------|
| ...  | ...       | ...           |

State the committed spec version. Note established patterns (envelope shape, error format, naming). If no spec exists: note that this is a greenfield API surface.

## Step 4 — Functional requirements interview

Use AskUserQuestion. Ask one group at a time; confirm before moving to the next. The goal is to understand WHAT the API must do — not to ask the user to make API design decisions.

**Group A — Consumer and lifecycle (ask once; drives most downstream decisions)**

Ask:
1. Who are the API consumers? (Select all that apply: browser/web frontend, mobile app, server-to-server internal service, third-party partner, autonomous agent/LLM, public internet)
2. Is this a new API, an extension of the existing one, or a replacement for an existing contract?
3. How long must the current contract remain stable? (Prototype/throwaway — weeks; Internal service — months with coordinated upgrades; External/public — years with backward compatibility guarantees)

*The skill derives from these answers:*
- Naming convention (snake_case for backend/analytics/agent APIs; camelCase for JavaScript-first browser/mobile APIs)
- Error verbosity (detailed problem+json with instance context for developers; minimal for automated consumers)
- Versioning policy (URL versioning for external/public; date-header for long-lived multi-client; none for internal coordinatable)
- Idempotency key requirement (important for network-unreliable mobile/external consumers)

**Group B — Resources and operations (ask per resource type)**

For each distinct entity or resource type the phase introduces or changes, ask:
1. What is the domain name for this resource? (Use the user's natural language — field, order, instrument, invoice — not a generic "entity")
2. Which standard operations apply: list all, get one, create, update (full replace), update (partial), delete?
3. Does any resource operation have a sub-resource? (e.g. `/orders/{id}/items` — only propose this if the sub-resource genuinely cannot exist independently)
4. What are the natural identifiers? Is there a single canonical key, or multiple identifier schemes?

*The skill derives from these answers:*
- HTTP method for each operation (GET for reads, POST for create, PUT for full replace, PATCH for partial, DELETE for remove)
- URL path structure: `/{plural-resource-name}` for collection, `/{plural-resource-name}/{id}` for item, nesting capped at `collection/item/collection`
- URL path casing: always `kebab-case` segments (Zalando MUST rule)
- Whether an idempotency key should be proposed for POST operations

**Group C — Query, filter, and scale (ask per collection endpoint)**

For each collection endpoint:
1. What fields should be filterable, and what comparison operations make sense for each? (equality, range, contains, etc.)
2. What fields should the results be sortable by?
3. What is the expected result set size in normal operation — tens, hundreds, thousands, or unbounded? How quickly does the data mutate?
4. Does the consumer need the full result set atomically, or can it process page by page?

*The skill derives from these answers:*
- Pagination strategy: **offset/limit** for small stable datasets; **cursor/keyset** for large or high-mutation datasets; **unbounded** only for provably-small static resources (e.g. a field catalogue with ≤100 entries) — document the decision and its size invariant
- Filter parameter design: a repeatable `filter=<field><op><value>` predicate pattern for data-field predicates; dedicated enum params for categorical universe narrowing
- Default and maximum page size

**Group D — Domain error conditions (ask per operation)**

For each operation:
1. What business-rule violations can occur? (Not generic validation errors — those are covered by industry practice. Domain-specific conditions: "an order cannot be cancelled after it has shipped", "a portfolio cannot be rebalanced with fewer than 2 assets")
2. For each domain error: is this condition permanent (the consumer should not retry) or transient (the consumer may retry)?

*The skill derives from these answers:*
- The appropriate HTTP status code for each error (422 for semantic validation, 409 for state conflicts, 404 for not-found)
- The ProblemDetail `type` URI and `title` for each named error condition
- Whether retry guidance should be included in the error response

**Group E — Evolution and breaking change constraints (ask once)**

1. Are there any existing clients or integrations that are coupled to the current API surface?
2. Is there anything in the current contract that must change — and if so, what breaks for existing consumers?
3. Does the project have an established versioning policy? If yes, what is it?

## Step 5 — Derive all API design decisions

From the answers in Step 4, apply industry practice to decide everything the user was not asked:

**Resource naming (from Group B answers):**
- Collection path: `/{plural-noun}` (e.g. `/orders`, `/instruments`, `/invoices`)
- Item path: `/{plural-noun}/{id}`
- Sub-resource (if justified): `/{plural-noun}/{id}/{plural-sub-noun}`
- All path segments in `kebab-case` (Zalando MUST rule)

**HTTP methods (from Group B operations):**
- List all → `GET /{resources}`
- Get one → `GET /{resources}/{id}`
- Create → `POST /{resources}` → 201 Created + `Location: /{resources}/{new-id}`
- Full replace → `PUT /{resources}/{id}` → 200 OK
- Partial update → `PATCH /{resources}/{id}` → 200 OK
- Delete → `DELETE /{resources}/{id}` → 204 No Content
- Custom actions that do not fit CRUD → `POST /{resources}/{id}/{action-noun}` (not verb URLs)

**Naming convention (from Group A consumer type):**
- Backend/analytics/agent/internal: `snake_case` for all JSON field names and query parameters
- Browser/mobile/JavaScript-first: `camelCase` for all JSON field names and query parameters
- Both: `kebab-case` for URL path segments

**Status codes (fixed by industry practice — not a user decision):**

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

**Collection response envelope (fixed — never a bare array):**
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
Rationale: bare array responses cannot carry pagination metadata without a breaking change. Always wrap.

**Pagination (from Group C scale answer):**
- Offset/limit: `?offset=0&limit=20` — use for small stable datasets (≤10k items, low mutation rate)
- Cursor: `?cursor=<opaque-token>&limit=20` + `next_cursor` in metadata — use for large or high-mutation datasets
- Unbounded: document the size invariant; enforce a hard maximum row cap with a 422 error if exceeded

**Error format (fixed by RFC 9457 — not a user decision):**
```
Content-Type: application/problem+json
```
```json
{
  "type": "https://{api-domain}/errors/{kebab-slug}",
  "title": "Human-readable summary (stable — same string every time for this type)",
  "status": 422,
  "detail": "Instance-specific explanation for THIS request",
  "errors": [
    {"field": "quantity", "reason": "Must be a positive integer"}
  ]
}
```
- `type` is a stable URI — never changes for a given error condition
- `title` never varies per instance (put instance-specific text in `detail`)
- `errors[]` is a standard RFC 9457 extension for per-field validation failures

**Null semantics (from Group D permanent/transient answer):**
- `null` = field applies to this resource type but value is currently unavailable (transient)
- Absent key = field is not applicable to this resource type at all (structural)
- Sentinel string = when the distinction must be machine-readable for automated consumers (e.g. `"not_applicable"`, `"unavailable"`)
- Decide which convention to use for each nullable field and document it in the spec

**Idempotency (from Group A consumer type):**
- For POST operations called by mobile or external consumers: propose `Idempotency-Key` header
- For POST operations called by internal services with retry-safe infrastructure: optional
- Document the idempotency policy for each POST endpoint

## Step 6 — Classify every change

For any change to the existing API surface, apply this taxonomy:

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

Include:
- A concrete JSON example for every new or changed endpoint — use realistic values, not placeholder strings
- One ProblemDetail example per named error condition
- The derived design decisions (HTTP methods, status codes, envelope shape, naming convention) as explicit statements, not implicit
- All null semantics decisions as a table
- The invariant sign-off checklist

## Step 10 — Commit atomically

```bash
git add {phase_dir}/XX-API-SPEC.md
git commit -m "contract(phase-XX): API design contract — <one-line summary>"
```

## Step 11 — Report and next step

Print:
- N additive changes, M breaking changes
- Gate result
- Path of written spec
- Next step: `/api-plan <phase>` — auto-discovers ADR/governance docs and this spec, passes them to the planner
</process>

<success_criteria>
- Only functional requirements asked of the user; all API design decisions derived from industry practice
- Consumer type and lifecycle established before any design decisions are made
- Every proposed change classified as additive or breaking
- Breaking changes explicitly approved with change-ledger entry recorded
- All invariant groups checked (or violations resolved) before the spec is written
- Concrete JSON examples for every endpoint and error condition
- API-SPEC.md committed atomically
- User knows next step is `/api-plan <phase>`
</success_criteria>
