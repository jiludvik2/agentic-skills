# API Gray Areas — Discuss-Phase Reference

When running `/gsd-discuss-phase` for a phase that touches the API layer, surface these
items as additional gray areas alongside the standard discuss-phase analysis.

These gray areas are grounded in REST and HTTP industry practice (Google AIP, Zalando,
RFC 9457). They cover implementation-level decisions that cannot be derived purely from
functional requirements — the user must make a choice, but the choice is informed by
established industry patterns presented here.

Note: `/api-phase` handles the detailed API design interview. The items here are the
higher-level decisions that should be settled at the discuss-phase level, before API
design begins.

---

## 1. Breaking vs Additive — Scope Assessment

**Gray area:** Does this phase require any changes that would break existing consumers
of the current API surface?

**Why surface at discuss-phase:** A breaking change requires explicit approval, a
versioning event, and a migration path. Discovering this late (at planning or execution)
derails the phase. Surfacing it here allows the operator to either adjust scope (make
the change additive) or budget time for the versioning work.

**How to evaluate:**
- Removing, renaming, or changing the type of any existing field → breaking
- Making an optional parameter required → breaking
- Changing the HTTP method or URL of an existing endpoint → breaking
- Adding new optional fields or new endpoints → additive (safe)

**Consequence of getting this wrong:** A breaking change shipped as additive silently
breaks consumers with no opportunity to adapt. This is the most damaging class of API
defect for externally-consumed APIs.

---

## 2. Consumer Type and API Lifecycle

**Gray area:** Who are the consumers of this API surface, and how long must the current
contract remain stable?

**Why surface at discuss-phase:** Consumer type drives naming convention, error verbosity,
versioning policy, and idempotency requirements. Lifecycle determines how aggressive the
backward-compatibility constraint should be. These decisions affect every subsequent
design choice.

**Consumer-type decisions it drives:**
- Browser/JavaScript-first consumers → `camelCase` JSON field names
- Backend/analytics/agent consumers → `snake_case` JSON field names
- Mobile/external consumers → idempotency keys needed on POST operations
- Public/partner consumers → formal versioning policy required (URL path `/v1/` recommended)
- Internal coordinated consumers → versioning can be informal (date-based or coordinated cutover)

**Lifecycle decisions it drives:**
- Prototype/throwaway → additive-only constraint is relaxed
- Long-lived external/public → breaking changes require deprecation notices and sunset timelines

---

## 3. Versioning Policy

**Gray area:** Does this phase require a versioning decision — either because it introduces
breaking changes, or because no versioning policy has been established yet?

**Industry options:**
| Strategy | Mechanism | Best for |
|----------|-----------|----------|
| URL path versioning | `/v1/`, `/v2/` | Public/partner APIs; most common; browser-testable |
| Date-based header | `API-Version: 2024-11-15` | APIs with many long-term pinned clients (Stripe model) |
| No explicit versioning | Additive-only forever | Internal single-consumer APIs with coordinated deploys |

**When to surface:** When the phase has breaking changes, OR when this is the first
phase establishing a public API surface, OR when existing API docs reference a version
that is about to be superseded.

**Consequence of deferring:** A versioning policy established under pressure tends to be
inconsistent. Inconsistency breaks consumer tooling and creates maintenance debt.

---

## 4. OpenAPI Spec as the Source of Truth

**Gray area:** Does the project have a committed OpenAPI spec, and is it treated as the
authoritative contract (code conforms to spec) or as generated documentation (spec is
generated from code)?

**Why it matters for planning:** The implementation wave ordering changes completely
depending on the answer:
- Contract-first (spec is authority): Wave 0 = update schema classes → regenerate spec
  → commit → all subsequent waves implement business logic to match
- Code-first (spec is docs): The spec is generated at the end; no spec gate constrains
  the implementation order

**Industry practice recommendation:** Contract-first. The committed spec is the locked
design artifact that `/api-phase` produces. The planner should treat Wave 0 as "update
schema classes and regenerate the spec" before any business logic is written.

---

## 5. Error Contract — Consistency vs. Practicality

**Gray area:** Should this phase introduce a new error response format, or must it
be consistent with whatever the project currently uses?

**Surface when:** The project has mixed error formats (some endpoints return
`{"error": "message"}`, others return RFC 9457 ProblemDetail), and this phase touches
multiple endpoints.

**Industry recommendation:** RFC 9457 (`application/problem+json`) is the current IETF
standard. A single consistent error shape across all endpoints is more important than
which specific shape is chosen — inconsistency forces consumers to handle multiple
error shapes, which is worse than either format alone.

**If the project already has an established format:** Follow it for consistency, even if
it's not RFC 9457. Changing the error format is a breaking change.

---

## 6. Pagination Strategy for New Collection Endpoints

**Gray area:** For any new collection endpoint: what pagination strategy is appropriate,
and what are the size bounds?

**Decision criteria:**
| Dataset characteristic | Recommended approach |
|-----------------------|---------------------|
| ≤ ~1k items, low mutation rate | Offset/limit (`?offset=0&limit=20`) |
| Large or high-mutation | Cursor/keyset (`?cursor=<token>&limit=20`) |
| Provably small and static (e.g. ≤100 items, like a field catalogue) | Unbounded, with documented max and a hard cap enforcement |

**Why surface at discuss-phase:** Adding pagination later is a breaking change (the
response shape changes). It must be designed in from the start. Discovering that a
collection can grow large after shipping an unbounded endpoint forces a version bump.

**Trap to avoid:** Choosing unbounded because the current dataset is small. The question
is whether it can grow, not whether it is currently large.

---

## 7. Null and Absence Semantics for New Fields

**Gray area:** For any new nullable field: does absence mean the value is not applicable
to this resource (structural), or that the value is temporarily unavailable (transient)?

**Why it matters for consumers:**
- Structural absence (permanent): consumer should not retry; the field will never have
  a value for this resource type
- Transient absence (temporary): consumer may retry later; the field will have a value
  once data is available

**Implementation options:**
- `null` = transient; absent key = structural → clean but requires disciplined schema
  enforcement (field must always be in schema even when structurally absent)
- Sentinel string (`"not_applicable"`, `"unavailable"`) = machine-readable distinction
  without two different JSON shapes → preferred for automated/agent consumers

**Surface when:** The phase introduces nullable fields that an automated consumer will
need to act on differently depending on the reason for absence.

---

## 8. Discoverability for Agent/LLM Consumers

**Gray area:** If this API will be consumed by an autonomous agent or LLM, can the
agent discover and correctly use the new surface from the API itself — without reading
source code or internal documentation?

**Discoverability requirements for agent consumers:**
- Every endpoint, parameter, and response field must have a description in the OpenAPI
  schema that is sufficient to infer correct usage
- If the API uses coded values (enums, status codes, flags), all values and their
  meanings must be in the schema description
- If the API uses resource identifiers, the response must carry enough context for the
  agent to know what type of identifier it received and how to use it in subsequent calls
- There should be a logical entry point (index endpoint, `/fields` endpoint, or similar)
  from which an agent can navigate to any resource

**Surface when:** The phase adds capabilities that will be used by the agent/LLM
consumer (if one exists in this project's context).
