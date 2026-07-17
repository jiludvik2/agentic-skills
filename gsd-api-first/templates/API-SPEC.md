# API Design Contract — Phase {XX}: {Phase Name}

<!-- Produced by /api-spec before planning. Its path is registered in CONTEXT.md          -->
<!-- <canonical_refs>, so /gsd-plan-phase reads it automatically. Commit before planning.  -->
<!-- All API design decisions are derived from REST/HTTP industry practice by the skill.  -->
<!-- The user provided only functional requirements; this spec records the derived design. -->

## Summary

**Phase goal:** {One sentence: what functional capability this phase adds or changes}

**Change classification:** {Additive only | Additive + {N} breaking changes}

**Breaking-change gate:** {Passed — no breaking changes | Breaking changes approved — see Change Ledger}

**API version:** {Unchanged: {current-version} | Bumped: {old} → {new} (breaking changes present)}

---

## Change Ledger

<!-- Complete only if breaking changes exist. Remove this section for additive-only phases. -->

| # | What currently exists | What breaks | New contract | Why this change is necessary |
|---|-----------------------|-------------|-------------|------------------------------|
| 1 | {current field/param/endpoint} | {who breaks and how} | {new shape} | {business justification} |

---

## Established Patterns (Project Baseline)

<!-- Discovered from the existing OpenAPI spec and prior API-SPEC files. Not assumed.     -->
<!-- These constraints apply to ALL new endpoints in this phase.                         -->

**Response envelope:** {e.g. `{"data": [...], "metadata": {...}}` for collections; `{"data": {...}}` for items | none established — decided in this phase}

**Error shape:** {e.g. RFC 9457 ProblemDetail at `application/problem+json` | `{"error": "...", "message": "..."}` | none established — decided in this phase}

**JSON field naming:** {`snake_case` | `camelCase`} — derived from consumer type: {consumer type from interview}

**URL path casing:** `kebab-case` (Zalando MUST rule — always)

**Null semantics:** {naked `null` for transient absence; absent key for structural | sentinel strings: `"not_applicable"` / `"unavailable"` | not yet established}

**Pagination:** {offset/limit | cursor/keyset | unbounded with hard cap} — applied to all collection endpoints

**Versioning policy:** {URL path `/v1/` | date-based header | no versioning — internal single-consumer}

---

## Consumer Context

**Who calls this API:** {browser frontend | mobile app | internal service | external partner | LLM/agent | public internet}

**Lifecycle stability requirement:** {Prototype — weeks | Internal coordinated — months | External/public — years with backward-compat guarantee}

**Idempotency key required on POST operations:** {Yes — consumers are network-unreliable | No — infrastructure retries are safe}

---

## New / Changed Endpoints

<!-- One block per endpoint. Duplicate the block for each new or modified endpoint. -->

---

### {METHOD} {/resource-path}

**Status:** {New | Modified (previously: {old METHOD /old-path})}

**Purpose:** {One paragraph: what operation this performs, who calls it and why, what it returns}

#### Request

**Path parameters:**

| Name | Type | Description |
|------|------|-------------|
| `{id}` | `string` (UUID) | {semantic meaning — what resource this identifies} |

**Query parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `{param}` | `{string\|integer\|boolean\|enum}` | {Yes\|No} | {value or —} | {semantic meaning; for enums list all values and their meanings} |

**Request body** (omit if none):

```json
{
  "{field}": "example-value"
}
```

#### Responses

**{HTTP status} {Status Name} — {condition that produces this response}**

```json
{
  "data": [
    {
      "{field}": "realistic-example-value",
      "{another_field}": 42
    }
  ],
  "metadata": {
    "total_count": 142,
    "has_more": true,
    "offset": 0,
    "limit": 20
  }
}
```

*Derived design decisions:*
- HTTP method chosen because: {e.g. "GET — this is a safe read with no side effects"}
- Status code chosen because: {e.g. "200 — returns existing data; 201 not used because no resource is created"}
- Envelope used because: {e.g. "collection endpoint — bare array would prevent adding pagination metadata without a breaking change"}

---

**{4xx} {Error Name} — {trigger condition}**

```
Content-Type: application/problem+json
```
```json
{
  "type": "https://{api-domain}/errors/{kebab-slug}",
  "title": "{Stable human-readable summary — identical for every occurrence of this error type}",
  "status": {4xx},
  "detail": "{Instance-specific explanation — varies per request; e.g. 'Field quantity must be a positive integer, got: -5'}",
  "errors": [
    {"field": "{field-name}", "reason": "{why this field failed}"}
  ]
}
```

*Status code chosen because:* {e.g. "422 — request is syntactically valid JSON but the quantity value violates a business rule"}

---

## Error Catalogue

All error conditions introduced or changed by this phase.

| HTTP Status | Type slug | Title (stable) | Trigger |
|-------------|-----------|----------------|---------|
| {422} | `{domain}:{kebab-slug}` | {Stable title} | {When this fires} |
| {404} | `{domain}:{kebab-slug}` | {Stable title} | {When this fires} |

**Rules enforced:**
- `title` is the same string every time for a given `type` — instance-specific text goes in `detail`
- `type` URI is stable — changing it is a breaking change
- Stack traces and internal identifiers do not appear in error bodies

---

## Null Semantics

<!-- One row per nullable field. -->

| Field | Endpoint | Null / absent means | Sentinel (if machine-readable) | Consumer guidance |
|-------|---------|---------------------|-------------------------------|------------------|
| `{field}` | `{METHOD /path}` | {Structural: field not applicable to this resource type} OR {Transient: value temporarily unavailable} | `"{not_applicable\|unavailable}"` or — | {What consumer should do: skip / retry later / treat as zero} |

---

## Idempotency

| Endpoint | Method | Idempotent? | Safe to retry? | Mechanism |
|----------|--------|------------|----------------|-----------|
| `{/path}` | {POST} | {No} | {Yes — `Idempotency-Key` header required} OR {No — double-submit risk} | {Idempotency-Key or none} |

---

## Invariant Sign-Off

All items must be checked before committing this spec. The planner treats unchecked items as open questions.

**HTTP method semantics:**
- [ ] GET/HEAD operations are safe (no side effects) and idempotent
- [ ] PUT and DELETE are idempotent
- [ ] No verb appears in any URL path segment

**Status codes (derived from industry practice — not a design choice):**
- [ ] Successful creation returns 201 (not 200)
- [ ] Successful delete with no body returns 204 (not 200)
- [ ] Business rule violations return 422 (not 400)
- [ ] State conflicts return 409 (not 422)
- [ ] Auth: 401 = missing credentials; 403 = present but insufficient
- [ ] No 5xx for client input errors

**Collection responses:**
- [ ] Every collection endpoint returns `{data: [...], metadata: {...}}` — no bare arrays
- [ ] `metadata` includes `has_more` and the information needed to retrieve the next page
- [ ] A maximum page size is documented and enforced (422 if exceeded)

**Error contract (RFC 9457):**
- [ ] All client errors return `application/problem+json`
- [ ] Each named error has a stable `type` URI slug
- [ ] `title` is the same for every instance of a given `type`
- [ ] No stack traces or internal identifiers in error bodies

**Naming (consistent with established pattern):**
- [ ] All URL path segments are `kebab-case`
- [ ] All JSON field names follow the project's convention (snake_case or camelCase)
- [ ] Boolean fields use positive predicates
- [ ] Date/time fields are ISO 8601 with timezone

**Nullability:**
- [ ] Every nullable field has documented absence semantics

**Consistency:**
- [ ] New endpoints follow the established envelope shape
- [ ] Error responses follow the established error format

---

## OpenAPI Snapshot Plan

**Update timing:** Wave 0 of the execution plan.
1. Update schema/model classes to match this contract exactly
2. Regenerate the committed OpenAPI spec: `{regeneration command}`
3. Commit the updated spec
4. Verify that any OpenAPI snapshot gate passes
5. Only then implement business logic — implementation works to satisfy the already-committed spec

**Why Wave 0:** If the spec is updated at the end (after implementation), it becomes documentation rather than a contract. The spec loses its authority as the source of truth.

**Version bump:** {None — additive changes only | Major: {old} → {new} — breaking changes present | Minor: {old} → {new} — new endpoints added}
