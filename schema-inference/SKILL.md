---
name: schema-inference
description: "Use when inferring JSON schemas from raw PDF documents. Feeds documents directly to the LLM (no pre-extraction), stress-tests the schema against more documents, and refines it to capture edge cases."
version: 1.5.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [json-schema, data-modeling, pdf-extraction, schema-inference, schema-review, unstructured-data]
    related_skills: [plan, software-development-workflow]
---

# Schema Inference Engine

Infer JSON schemas from raw unstructured documents (PDFs with mixed
free-form text and tabular data), then stress-test and refine them
against more documents.

Key principle: documents are fed as RAW TEXT to the LLM. No schema-aware
pre-extraction. The LLM must discover fields and structures that no
existing schema knows about. Pre-extracting would only find what the
extraction tool already knows -- the same blind spots we're trying to find.


## When Not to Use

- API request/response schema design (use OpenAPI)
- Database schema design (use ER modeling tools)
- Simple key-value extraction where no nesting is needed
- Pre-extracted/structured data (schema is already known)


## Quick Start: Point at a Folder

Given just a folder path, the skill runs autonomously through rounds 1-2:

  "Run schema-inference on ~/data/prospectus_pdfs/"

What happens automatically:

1. SCAN the folder
   - List all PDFs and their sizes
   - Identify document categories from filenames
   - Report: "Found N documents across K categories"

2. CATEGORIZE documents
   - Filename patterns: "term_sheet", "prospectus", "offering_memorandum",
     "supplement", "indenture", "pricing", "closing"
   - Issuer hints: first N characters or directory subfolders
   - Size extremes: small = summary, large = full prospectus
   - Date patterns in filenames: YYYY, YYYY-MM, YYYYMMDD
   - If <20 docs: all are candidates. 20-100: stratified. >100: broad sampling.
   - User can override: "categories: {term_sheet: *.ts.pdf, prospectus: *.pr.pdf}"

3. SELECT representative samples (non-overlapping)
   - Pick 3-5 docs for round 1 (one per category, largest in each)
   - Pick 10-15 docs for round 2 that were NOT used in round 1
     (edge cases: smallest, largest, unusual names from remaining pool)
   - Report: "Round 1: selected 5 docs. Round 2: selected 15 docs."
   - Track used documents in .schema-work/used-documents.txt

4. READ raw documents into context
   - Convert each selected PDF to markdown using PyMuPDF4LLM (the pinned extraction library)
   - Converted text is cached in <source>-schema/extracted/ -- each PDF is only
     converted once. On subsequent runs, cached text is read from disk.
   - This is NOT schema-aware extraction -- it converts PDF pages to markdown
     preserving layout and table structure, but does not know about or filter to any schema
   - All fields in the document are preserved -- nothing is filtered or mapped
   - Report progress per document:
     [progress] Converting doc 3/5: filename.pdf (not cached, running PyMuPDF4LLM...)
     or
     [progress] Loading doc 3/5: filename.pdf (cached)
   - If a file fails to convert, skip it and note the failure

5. INFER schema (round 1)
   - Feed all 5 raw docs to model in one call
   - [progress] Round 1: sending 5 documents (~440K tokens) to model...
   - Save initial schema as v1.0.0.schema.json
   - Validate with jsonschema library
   - If invalid: fix and re-validate before proceeding
   - [progress] Round 1 complete. Schema saved to v1.0.0.schema.json

6. REVIEW + REFINE schema (round 2, iteratively)
   - The updated schema from each step is the input to the next step
   - When refining, verify backward compatibility for each fix:
     - New optional fields: always safe
     - Type changes: check if existing data still validates
     - Nesting changes: may break existing consumers -- flag explicitly
     - Field renames: NEVER -- add aliases instead
   - Load current schema (v1.0.0.schema.json from step 5)
   - Select 11 docs NOT in used-documents.txt for first REVIEW call
   - Feed schema + 11 docs in first REVIEW call
   - [progress] Round 2a: sending 11 documents (~970K tokens) to model...
   - [progress] Round 2a complete. Found X gaps.
   - Append these 11 docs to used-documents.txt
   - If gaps found: REFINE schema, save as v1.1.0.schema.json, validate
   - If validation fails: fix, re-validate
   - Load updated schema (v1.1.0.schema.json)
   - Select 4 more docs NOT in used-documents.txt for second REVIEW call
   - Feed schema + 4 docs in second REVIEW call
   - [progress] Round 2b: sending 4 documents (~350K tokens) to model...
   - [progress] Round 2b complete. Found Y gaps.
   - Append these 4 docs to used-documents.txt
   - If gaps found: REFINE schema, save as v1.2.0.schema.json, validate
   - If no critical/high gaps: schema is stable, report final version
   - Save gap report to gap-report-round2.txt

7. FINAL VALIDATION
   - Validate final schema with jsonschema library
   - If invalid: fix and re-validate
   - Report: "Schema vX.Y.Z: N total gaps found and resolved across rounds."
   - Report: "Current schema has no critical/high severity gaps."

CRITICAL: No pre-extraction with Marker or Docling before rounds 1-2.
The whole point is that the LLM discovers fields that no existing
schema or extraction tool knows about. If you pre-extract, you only
find what the tool already knows -- the same blind spots you're trying
to eliminate.

All outputs saved to a separate directory next to the source folder.
Source folder:   ~/data/prospectus_pdfs/
Work directory:  ~/data/prospectus_pdfs-schema/

  ~/data/prospectus_pdfs-schema/
    used-documents.txt      # list of all documents already fed to the model
    extracted/              # cached markdown text (one .md per PDF, converted once)
    v1.0.0.schema.json      # initial schema (after round 1)
    v1.1.0.schema.json      # refined schema (after round 2a)
    v1.2.0.schema.json      # refined schema (after round 2b)
    gap-report-round2.txt   # gap findings from round 2
    evolution-log.txt       # what changed at each version and why

Each version is saved immediately after refinement and validated before
the next step uses it. The latest version is always the input to the
next REVIEW call.

The evolution-log.txt tracks every individual change with justification:
  v1.0.0 -> v1.1.0:
    [1] Added field "terms.floating_rate" (type: object)
        Reason: 2 of 15 documents describe floating rate notes with SOFR+spread,
        which the fixed coupon_rate field cannot represent.
        Severity: critical
    [2] Changed "call_provision" from single object to array "call_provisions"
        Reason: 3 of 15 documents have stepped call schedules or multiple call
        types (hard + make-whole) that a single object cannot capture.
        Severity: critical
    [3] Added "call_provisions[].notice_period_days" (type: integer)
        Reason: 3 of 15 documents specify notice period for call exercise.
        Severity: high
    ...


## Anti-Patterns to Detect and Fix

1. HARDCODED KEYS -- Using specific values as object keys instead of arrays.
   Bad:  { "us_treasuries": ..., "corp_bonds": ... }
   Good: { "allocations": [{ "asset_class": "us_treasuries", ... }] }
   Reason: keys can't be iterated, validated, or extended.

2. FLAT FIELDS THAT SHOULD BE NESTED -- A cluster of related fields at the
   same level as unrelated fields.
   Bad:  { "call_date", "call_price", "call_notice_days", "put_date" }
   Good: { "issuer_call": { "date", "price", "notice_days" }, "investor_put": { ... } }
   Reason: grouping conveys semantics; avoids namespace collisions.

3. UNCONSTRAINED OR FLOAT-PRECISION NUMBERS -- Precise quantitative metrics
   (financial amounts, rates, coordinates) stored as unconstrained strings,
   OR as floats where rounding error is unacceptable.
   Bad:  { "coupon_rate": { "type": "string" } }              (no constraint)
   Bad:  { "coupon_rate": { "type": "number" } }              (float precision loss)
   Good: { "coupon_rate": { "type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$" } }
   Reason: prevents downstream parsing errors AND floating-point precision loss.
   See "Precise Numeric Values" in Schema Design Rules.

4. MISSING UNITS/CURRENCY -- Numeric values without unit context.
   Bad:  { "face_value": { "type": "number" } }
   Good:  { "face_value": { "type": "object", "properties": { "amount": { "type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$" }, "currency": { "type": "string", "pattern": "^[A-Z]{3}$" } } } }

5. SINGLE-VALUE WHERE MULTI IS POSSIBLE -- A field that should be an array
   because documents vary, but is typed as a single value.
   Bad:  { "rating": { "type": "string" } }
   Good:  { "ratings": { "type": "array", "items": { "$ref": "#/$defs/rating_entry" } } }
   Reason: multiple agencies rate the same instrument.

6. NO ENUMS FOR CLOSED SETS -- Fields with a known finite set of values
   typed as free-form strings.
   Bad:  { "day_count_convention": { "type": "string" } }
   Good:  { "day_count_convention": { "type": "string", "enum": ["ACT/360","ACT/365","30/360","ACT/ACT"] } }

7. NO VERSIONING -- Schema has no way to track which version produced
   an extraction. Always include a top-level $schemaVersion field.

8. TRUSTING MODEL OUTPUT WITHOUT VALIDATION -- Even models with structured
   output can produce subtly invalid schemas (e.g., $ref pointing to
   non-existent $defs, required fields not in properties). Always run
   jsonschema validation on the output before accepting it.

9. INAPPROPRIATE SPECIFICITY -- Using document-specific proper nouns
   (city names, exchange names, issuer names) as field names instead of
   modeling them as values in a generic field.

10. STRINGLY-TYPED EVERYTHING -- Defaulting all values to { "type": "string" }
    instead of inferring monetary objects, dates, enums, booleans, and
    structured rates.

11. DUPLICATE INLINE DEFINITIONS -- Defining the same property set (e.g.
    monetary amount, party name+role) inline in 5+ different objects
    instead of using $ref to a single $defs entry.

12. FLAT MUTUALLY-EXCLUSIVE OBJECTS -- Creating a single object where
    most fields are optional because it tries to cover multiple mutually
    exclusive scenarios (e.g., a "terms" object where fixed_rate_fields
    and floating_rate_fields are both optional). Use separate objects or
    oneOf/anyOf instead.


## Pattern Library

Reusable $defs for common field types found in financial/document extraction:

DATE PATTERN:
  { "type": "string", "format": "date", "description": "ISO 8601 date" }
  With optional specificity:
  { "oneOf": [
    { "type": "string", "format": "date" },
    { "type": "string", "format": "date-time" },
    { "type": "object", "properties": { "year": { "type": "integer" }, "month": { "type": "integer" } } }
  ]}

MONETARY PATTERN:
  { "type": "object", "properties": {
    "amount": { "type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$" },
    "currency": { "type": "string", "pattern": "^[A-Z]{3}$" }
  }, "required": ["amount", "currency"], "additionalProperties": false }
  Note: amount is a pattern-constrained string, NOT a float, to prevent
  floating-point precision loss on monetary values.

RATE PATTERN:
  { "type": "object", "properties": {
    "value": { "type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$" },
    "basis": { "type": "string", "enum": ["percent", "basis_points", "decimal"] }
  }, "required": ["value", "basis"], "additionalProperties": false }
  Note: value is a pattern-constrained string to preserve exact precision.

IDENTIFIER PATTERN:
  { "type": "object", "properties": {
    "value": { "type": "string" },
    "scheme": { "type": "string", "description": "ISIN, CUSIP, SEDOL, LEI, etc." }
  }, "required": ["value", "scheme"], "additionalProperties": false }

STRICT IDENTIFIER PATTERNS (apply when scheme is known):
  ISIN:        { "type": "string", "pattern": "^[A-Z]{2}[A-Z0-9]{9}[0-9]$" }
  CUSIP:       { "type": "string", "pattern": "^[0-9A-Z]{9}$" }
  LEI:         { "type": "string", "pattern": "^[A-Z0-9]{18}[0-9]{2}$" }
  SEDOL:       { "type": "string", "pattern": "^[0-9A-Z]{7}$" }
  Common Code: { "type": "string", "pattern": "^[0-9]{9}$" }
  CFI:         { "type": "string", "pattern": "^[A-Z]{6}$" }
  When the scheme is known from context, use the strict pattern directly
  instead of the generic {value, scheme} object.

RATING PATTERN:
  { "type": "object", "properties": {
    "grade": { "type": "string" },
    "agency": { "type": "string", "enum": ["S&P", "Moody's", "Fitch", "DBRS", "AM Best"] },
    "date": { "type": "string", "format": "date" },
    "outlook": { "type": "string", "enum": ["stable", "positive", "negative", "developing"] }
  }, "required": ["grade", "agency"], "additionalProperties": false }

PARTY PATTERN:
  { "type": "object", "properties": {
    "name": { "type": "string" },
    "role": { "type": "string" },
    "identifiers": { "type": "array", "items": { "$ref": "#/$defs/identifier" } },
    "address": { "type": "string" }
  }, "required": ["name", "role"], "additionalProperties": false }


## Output Format

Before any multi-document call, emit a progress line:
  [progress] Round N: sending K documents (~T tokens) to model...

After the call completes:
  [progress] Call completed in Xs. Found Y gaps.

If a call exceeds 60s without response:
  [progress] Still waiting... (free tier queuing is normal for large inputs)

For REVIEW, output gaps as:

BATCH [N] SCHEMA STRESS TEST

Gap [1]: <short name>
  Challenge: <what the document contains>
  Gap: <why the schema fails>
  Fix: <concrete schema change>
  Severity: critical|high|medium|low
  Frequency: appears in <N> of <M> documents

(repeat for each gap)

---

For REFINE, output the complete updated JSON schema.
Do NOT truncate. Include all $defs, all properties, all annotations.
Include a $comment on every field explaining its purpose.

For BREAKING CHANGES, explicitly flag:

BREAKING: <description of what breaks and why>
Migration: <how existing consumers should adapt>


## Schema Design Rules

These rules come from comparing skill-inferred schemas against independently
produced reference schemas. They are domain-independent -- they apply
regardless of what document type you are inferring a schema from.

### Naming
- Use snake_case for all field names (standard JSON/data convention)
- Be descriptive but not verbose
- Use consistent suffixes: _pct for percentages, _date for dates, _amount for monetary, _type for classifications, _count for counts, _days for day durations, _seconds for time durations
- Use _timestamp for exact times including timezones (e.g., created_at_timestamp)
- Use _date for calendar days only (e.g., submission_date)
- Boolean fields must read like a yes/no question: prefix with is_, has_, can_, requires_, should_ (e.g., is_active, has_attachments, requires_approval)
- Array/collection fields must use plural nouns (e.g., associated_documents, approval_nodes, error_codes)
- Never use naked reserved words (type, value, key, id, date, limit, status) -- always prepend domain context (document_type, transaction_status, order_identifier)
- Adopt the exact terminology used in the source documents -- do not invent synonyms or generic terms if the domain uses specific nomenclature

### Identifiers
- Well-known identifiers should be flat string fields at the identifiers level
- Use the scheme/value pattern only for extensible/unknown identifier types
- If the domain has a small fixed set of standard identifiers, model them as
  named fields (e.g., isin, common_code) rather than an array of {scheme, value}

### Grouping
- Group top-level properties into logical sections that match how users think
  about the domain (e.g., issuer_details, issue_economics, interest_profile)
- Related fields that are commonly queried together should be co-located
- Avoid both extremes: 50 flat top-level fields is chaotic, but 5 levels of
  nesting for a simple value is unusable

### Flat vs Nested
- Prefer flat fields for simple values that are commonly queried or filtered
- Use objects only for genuinely grouped data that shares lifecycle/optionality
- If a value is often checked independently (e.g., settlement_currency vs
  specified_currency), give it its own flat field rather than nesting
- Include quick-access flat fields alongside full structured arrays
  (e.g., lead_manager_name in addition to full parties array)

### Classification Fields
- Include high-level classification strings for filtering and routing
- These let consumers quickly categorize documents without parsing details
- Examples from different domains: interest_type, repayment_type, form_of_note,
  document_type, transaction_type, asset_class

### Null Fields
- Include fields that may be null to signal they were considered
- This makes the schema self-documenting about what data points exist in the domain
- Example: "esg_framework_details": null signals this is a known field that
  simply does not apply to this particular document
- To declare a nullable field, use a type array -- "type": ["string", "null"] --
  NOT a verbose oneOf with a separate { "type": "null" } branch. Type arrays are
  cleaner, faster to validate, and more readable.

### Free Text vs Enums
- Use free-form strings for values that vary too much across documents for an
  enum to be useful (e.g., business_day_convention, calculation_method)
- Use enums only for truly closed sets that are stable across the corpus
- When in doubt, start with string and tighten to enum after seeing 10+ docs
- When you DO use an enum to enforce an industry/system standard, do NOT put
  verbatim source text in it. Enforce the normalized standard value in the enum
  and add a companion [field_name]_raw string capturing the original text for
  auditability and debugging (see "Raw Value Companion Fields")
- If an enum includes "Other"/"Custom"/"Miscellaneous", pair it with an optional
  [field_name]_description string, conditionally required when the fallback is
  selected (see "The 'Other' Loophole")

### Dates and Amounts
- Distinguish between conceptually distinct dates even if they are often the same
  (e.g., issue_date vs interest_commencement_date vs settlement_date)
- Distinguish between conceptually distinct amounts
  (e.g., nominal_amount vs minimum_denomination vs calculation_amount)
- Use ISO 8601 date format strings

### Generalization Over Memorization
- Do NOT hardcode document-specific values as field names or enums unless
  they are true industry standards (ISO codes, etc.).
- Abstract specific terms into broader schema categories.
- Bad:  { "london_business_day": true, "new_york_business_day": true }
- Good: { "business_day_convention": "Following Business Day", "business_day_centers": ["London", "New York"] }
- Rule: if a field name contains a proper noun (city, exchange, specific issuer),
  it should probably be a value inside a generic field.

### Strict Semantic Typing (No Defaulting to Strings)
- Do NOT lazily default to type: "string". Infer strict semantic type from context:
  - Money: structured monetary object {amount, currency} (amount is a
    pattern-constrained string -- see Precise Numeric Values)
  - Dates: { "type": "string", "format": "date" }
  - Date-time: { "type": "string", "format": "date-time" }
  - Lists of options: strictly use "enum" arrays
  - Yes/no clauses: use "boolean"
  - Percentages/rates: use structured rate object {value, basis}
  - Quantities with units: use {value, unit}
  - Precise numeric metrics (money, rates, coordinates): pattern-constrained
    string, NOT float -- this is the one intentional "string" exception
- If a field could be typed multiple ways across documents, choose the
  strictest type that covers all occurrences.

### Strict Reuse via $defs (DRY Principle)
- Identify ALL recurring data structures (parties, addresses, monetary values,
  percentages, identifiers) and extract them into $defs at the schema root.
- Reference these definitions via $ref throughout the schema -- never duplicate
  the same property set inline in multiple places.
- Bad:  "fee": {"type": "number"} and "price": {"type": "number"} defined inline
  in 10 different objects.
- Good: "monetary_amount" in $defs, then "$ref": "#/$defs/monetary_amount"
  everywhere it appears.
- This is MANDATORY for: monetary values, rates, identifiers, parties/ratings,
  addresses, contact information, audit/timestamp objects, and location objects.

### Polymorphic / Mutually Exclusive Structures
- Documents often describe scenarios like "If Fixed Rate... If Floating Rate..."
  with different fields applicable to each scenario.
- Do NOT place these mutually exclusive fields side-by-side as optional
  properties. Use JSON Schema conditional logic:
  - Best: separate objects under a parent, each describing one variant
    (e.g., "fixed_rate_terms": {...}, "floating_rate_terms": {...})
  - If they share many fields: use oneOf/anyOf with required discriminator
  - If truly independent: separate objects that are only required when
    the corresponding type_of_note value applies
- The parent schema should have a discriminator field (e.g., type_of_note)
  that controls which sub-schema applies.
- Enforce the exclusivity with Draft-07+ if/then/else, NOT comments: when the
  discriminator is "Type A", require Type A's properties and explicitly forbid
  Type B's with "not": { "required": [...] }. Never rely on schema comments or
  documentation to convey that fields are mutually exclusive.
- NEVER create a single object where 80% of fields are optional because the
  object tries to cover multiple mutually exclusive scenarios.

### Precise Numeric Values (No Floating-Point)
- Never use "type": "number" for precise quantitative metrics where rounding
  error is unacceptable -- financial amounts, rates, high-precision scientific
  measurements, exact geospatial coordinates.
- Represent these as "type": "string" with an exact-decimal regex:
  { "type": "string", "pattern": "^-?[0-9]+(\\.[0-9]+)?$" }
- "type": "number" is acceptable ONLY for values where float rounding is
  harmless (counts, approximate quantities, display-only figures).

### Raw Value Companion Fields
- Do NOT populate enums with raw, verbatim source text. Enforce the strict
  industry/system standard in the enum, and capture the original input in a
  companion [field_name]_raw string for auditability and debugging.
- Example: day_count_convention (enum, normalized) alongside
  day_count_convention_raw (string, verbatim as it appeared in the document).

### The "Other" Loophole
- Whenever an enum includes "Other", "Custom", or "Miscellaneous", pair it with
  an optional [field_name]_description string.
- Make that description mandatory via if/then when the fallback is selected:
  "if":   { "properties": { "category": { "const": "Other" } } },
  "then": { "required": ["category_description"] }

### Symmetrical Completeness
- When modeling opposing actions, state changes, or multi-actor workflows
  (request vs. response, buyer vs. seller, issuer call vs. investor put,
  start vs. stop), flesh out BOTH sides to equal operational depth.
- If one side carries execution dates, metadata, and state flags, its
  counterpart object must mirror that same depth -- do not model one richly and
  the other as a bare string.

### Operationalize Processes and Workflows
- Do NOT merely capture the name of a process, algorithm, or state. Include the
  mechanical fields a downstream system needs to actually execute or evaluate it:
  input parameters, threshold triggers, execution delays, dependency flags.
- Example: a "make_whole" redemption is not just a label -- model the discount
  rate, spread, and reference benchmark needed to compute the price.

### Contextual Dependencies (if/then)
- Avoid leaving critical arrays/objects universally optional. Use if/then to
  enforce dependencies on sibling fields.
- Example: if status is "Rejected", require the rejection_reasons array;
  if is_callable is true, require the call_provisions array.

### Object Boundaries
- Set "additionalProperties": false on every object to prevent undocumented
  fields from being injected by downstream systems or data entry.
- The only exception is an object deliberately designed as an open-ended
  metadata dictionary or unstructured payload -- mark those explicitly.

### Financial Identifier Validation
- When inferring financial identifiers (ISIN, CUSIP, LEI, SEDOL, CFI,
  Common Code), always apply strict regex pattern validation immediately
  instead of leaving them as plain strings (see Pattern Library for patterns).
- If an identifier in the document doesn't match any known pattern, still
  use { "type": "string", "pattern": "..." } with the best-guess pattern
  from the observed values, rather than leaving it unrestricted.

### Structural Hierarchy Enforcement
- Enforce that the schema has logical groupings -- a flat list of hundreds
  of properties is unacceptable.
- Required groupings:
  - All issuer-related fields together
  - All interest/rate terms together
  - All redemption/call/put features together
  - All settlement/clearing/distribution fields together
  - All regulatory/legal/annexes together
- Maximum nesting depth: 4 levels from root to any leaf property.
- If a group has more than 12 properties, split it into sub-objects with
  clear names (e.g., "interest_calculation", "interest_payment",
  "interest_adjustment" under the interest group).


## Document Dedup Tracking

No document may be fed to the LLM more than once. This prevents:

- The model confirming its own gaps instead of discovering new ones
- Wasting context budget on already-analyzed content
- Inflating gap frequency counts (a gap in the same doc counted twice)

Implementation:

  <source-folder>-schema/used-documents.txt
    One line per document, appended after each successful model call.
    Format: <filename>\t<round>\t<timestamp>

Before selecting documents for any round:
  1. Read used-documents.txt
  2. Exclude all filenames in the list from the candidate pool
  3. Select from remaining documents only
  4. After model call completes, append all documents in that call

If the skill is re-run on the same folder (e.g. to continue after an
interrupted session), used-documents.txt is already populated and
the skill picks up where it left off with fresh documents only.

If all documents have been used, the skill reports:
  "All N documents have been analyzed. No new documents available."

Then it presents the final schema:
  - If schema < 200 lines: print it inline
  - If schema >= 200 lines: print the path and a summary
    "Final schema: vX.Y.Z saved to <source>-schema/v1.2.0.schema.json"
    "  Definitions: N $defs, M top-level properties, K required fields"
    "  View with: cat <source>-schema/v1.2.0.schema.json | python -m json.tool"

Regardless of size, always print:
  - Total documents analyzed
  - Total gaps discovered and resolved
  - Evolution log location
  - Any remaining low-severity gaps that were not fixed


## Large Document Collections

When source documents number in the hundreds, you cannot feed all to
the LLM. Use a stratified sampling approach:

1. CATEGORIZE FIRST (by issuer, document type, time period, geography)
2. STRATIFIED SAMPLING:
   - Round 1 (INFER): 3-5 docs, one per major category
   - Round 2 (REVIEW): 10-15 docs, edge cases within each category
3. AUTOMATED BATCH VALIDATION (for rounds 3+):
   - Use an extraction tool or script to extract ALL docs against the schema
   - Validate with jsonschema Python library
   - Cluster errors by type
   - Review representative docs from each cluster
4. CONVERGENCE: schema is stable when automated validation shows <5% failure

Note: automated batch validation (step 3) DOES use extraction tools,
because by round 3+ the schema is mostly stable and the goal shifts
from discovery to validation. Rounds 1-2 must be raw.


## Model Configuration

Primary model:
  nvidia/nemotron-3-super-120b-a12b:free

Rate limits (with $10+ OpenRouter credits):
  - 20 requests/minute on :free variants
  - 1,000 requests/day on :free variants
  - Rounds 1-2 require only 3 calls total -- well within limits

Set the model:
  hermes config set model.default nvidia/nemotron-3-super-120b-a12b:free
  Or per-session: /model nvidia/nemotron-3-super-120b-a12b:free

See also: references/test-run-bond-issuances-2026-06-27-v2.md (detailed pitfalls from bond issuance test run)


## PDF Text Extraction

Pinned library: PyMuPDF4LLM

Run with uv (no venv, no system install):
  uv run --with pymupdf4llm python3 -c "import pymupdf4llm; print('ready')"

PyMuPDF4LLM converts PDFs to markdown with layout preservation, heading
detection, multi-column support, and table structure. It is NOT schema-aware
-- it does not know about or filter to any particular data model. All text
and structural elements in the document are preserved.

Why PyMuPDF4LLM over alternatives:
  - Extremely fast: ~1 second per document (vs 2+ minutes for Marker)
  - No GPU required, no model downloads (Marker downloads 1.3GB+ models)
  - Good enough table structure for schema inference purposes
  - Multi-column and heading awareness
  - LlamaIndex and LangChain integration
  - Works with uv --with for zero-setup ephemeral usage

Usage:
  import pymupdf4llm
  text = pymupdf4llm.to_markdown("document.pdf")

Caching: converted markdown is saved to <source-folder>-schema/extracted/<filename>.md.
On subsequent runs or rounds, if the .md file already exists in the cache,
extraction is skipped and the cached text is loaded from disk. A PDF is only
converted once regardless of how many times the skill is run.

The resulting markdown text is what gets fed to the LLM. The LLM
then discovers fields, relationships, and structures by reading
this text -- not by any pre-defined schema mapping.


## Throughput and Progress

Batch splitting for free models:
  Free models (especially on OpenRouter) may timeout with >500K input tokens.
  Split round 2 into batches of ~8 documents each. Run each batch as a
  separate subagent call, then merge the gap reports before REFINE.

Progress updates during slow calls:

When a call is processing a large document batch, emit status updates
between calls so the user knows work is progressing. Use this pattern:

  Before each call:
    [progress] Sending N documents (T tokens) to model...
    [progress] Estimated wait: Xs (free tier may queue)

  After each call completes:
    [progress] Call completed in Xs. Found Y gaps.

  If a call takes >60s with no output:
    [progress] Still waiting on model response... (free tier queuing)
    [progress] This is normal for large inputs on free models.

For background execution of long REVIEW runs:
  /background Review the schema against documents batch2/*.pdf


## Common Pitfalls

1. Ignoring document metadata. Always capture source document reference
   (filename, page range, extraction timestamp) in the output schema.

2. Mixing concerns. Keep the extraction schema (what comes out of the PDF)
   separate from the storage schema (what goes in the database). The extraction
   schema should be permissive about optionality (most fields optional) but
   still lock its boundaries with additionalProperties: false; the storage
   schema should additionally be strict about requiredness.

3. Default max_tokens too small for schema generation. Free models on
   OpenRouter often default to 4096-8192 output tokens, which truncates
   schemas mid-property. Always set max_tokens=65000 (or at least 32000)
   for schema generation calls. Check finish_reason in the response: if it
   says "length", increase max_tokens and retry.

4. $comment misplacement by model. Models frequently place $comment strings
   inside the properties dict (as a sibling of property definitions) instead
   of at the object level. This causes jsonschema metaschema validation to
   fail because it treats $comment as a property name that must be a schema
   (object/boolean), not a string. Post-process: scan for $comment keys
   inside properties dicts and move them to the parent object level.

5. Free-tier timeout budget. OpenRouter free models regularly queue for
   2-5 minutes on large inputs (>50K tokens). Use timeout=600 (not the
   default 300) for model calls. If a call times out, retry with the same
   payload -- free tier queuing is transient, not permanent.

6. $defs nesting. Some models place $defs inside a nested object (e.g.,
   inside the "issue" property) instead of at the schema root. This breaks
   $ref resolution. After generation, verify $defs is at the top level of
   the schema object. If not, move it up one level.


## Verification Checklist

- [ ] Schema is valid JSON Schema (validate with jsonschema library)
- [ ] All fields have $comment annotations
- [ ] No hardcoded-key anti-patterns remain
- [ ] Numeric fields have type constraints (minimum, maximum, format)
- [ ] Closed sets use enums; open sets use string + pattern
- [ ] Monetary fields use the monetary pattern (amount + currency)
- [ ] Date fields have format: "date" or format: "date-time"
- [ ] Schema has $schemaVersion field
- [ ] Schema has source document metadata fields
- [ ] Required array is explicit and minimal
- [ ] Examples provided for non-obvious fields
- [ ] No breaking changes without migration notes
- [ ] No document-specific proper nouns used as field names (generalization)
- [ ] All monetary/rate/identifier values use strict semantic types (not strings)
- [ ] All recurring structures use $ref to $defs (no duplicate inline definitions)
- [ ] Mutually exclusive scenarios use separate objects or oneOf/anyOf
- [ ] Financial identifiers have strict regex pattern validation
- [ ] Schema has logical groupings with max 4 levels of nesting
- [ ] Precise numeric values (money, rates, coordinates) are pattern-constrained
      strings, not floats
- [ ] Normalized enums have a companion [field]_raw verbatim string
- [ ] Every "Other"/"Custom" enum option has a conditionally-required
      [field]_description
- [ ] Mutual exclusivity is enforced with if/then/else + not:required, not comments
- [ ] Contextual dependencies are enforced with if/then (e.g. status -> reasons)
- [ ] Opposing actions/workflows are modeled with symmetrical depth
- [ ] Processes/states include the mechanical fields needed to execute them
- [ ] Nullable fields use type arrays ["x","null"], not oneOf-with-null
- [ ] Objects set additionalProperties: false (except open metadata dictionaries)
