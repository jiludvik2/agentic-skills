Schema Inference Test Run: Bond Issuances (Second Run)
=====================================================

Date: 2026-06-27 (second run, different model)
Source: /Users/jiri/Code/2026/funding-data/docs/bond-issuances/ (374 PDFs)
Output: /Users/jiri/Code/2026/funding-data/docs/bond-issuances-schema/
Model: nvidia/nemotron-3-super-120b-a12b:free (via direct API call, NOT delegate_task)


RESULTS
-------

Round 1 (INFER):   5 docs -> schema v1.0.0 (22,810 chars)
Round 2a (REVIEW): 15 docs -> 10 gaps (4 high, 6 medium) -> v1.1.0 (27,635 chars)
Round 2b (REVIEW):  4 docs ->  0 gaps (schema stable) -> v1.2.0 (28,626 chars)

Final schema: v1.2.0 (2 top-level objects, 39 issue properties, 6 $defs)
Documents analyzed: 24 of 374


KEY LEARNINGS
-------------

1. Model matters: nemotron produced a different schema shape than owl-alpha.
   - owl-alpha: 22 properties, 22 $defs (more granular)
   - nemotron: 39 properties, 6 $defs (flatter, uses $ref less)
   - nemotron placed $defs at wrong nesting level (inside issue, not root)

2. nemotron-specific issues discovered:
   a. max_tokens truncation: Default output limit truncated schema at 11K chars.
      Fix: set max_tokens=65000 (or at least 32000 for schema generation).
   b. $comment misplacement: Model puts $comment string inside properties dicts
      where jsonschema metaschema treats it as a property name (type mismatch).
      Fix: post-process to move $comment from properties to parent object level.
   c. Free tier timeout: 300s timeout insufficient. Use 600s for large inputs.

3. Bond types in this run (EBRD Eurobond prospectuses):
   - Fixed Rate (vanilla, callable, step-down)
   - Zero Coupon (standard, ultra-long 2060, payable in JPY)
   - Floating Rate (SOFR, TONIA index linked)
   - Currency Linked (TJS, MNT, EGP, ARS, INR linked to USD)
   - Amortising (decreasing principal schedule)
   - Green / Green Transition notes
   - Dual currency (INR denominated, payable in JPY)
   - Partly paid notes

4. Edge cases that drove schema evolution (v1.0 -> v1.2):
   - total_commissions field (4/15 docs had it as % of nominal)
   - currency_linked_notes object (7/15 docs had linkage)
   - amortising_notes with payment_schedule array (1/15 docs)
   - rate_schedule in fixed_rate_notes for step-down structures
   - selling_restrictions as structured array by jurisdiction
   - performance_of_rates_of_exchange as oneOf(object, string)
   - programme field (EBRD programme name, present in all docs)
   - payment_frequency enum (annual, semi-annual, etc.)
   - 30/360 day count fraction (missing from original enum)

5. Schema stability: After v1.1.0, round 2b with 4 additional edge-case
   documents found 0 new gaps. Schema converged after ~20 documents.


PITFALLS TO AVOID
-----------------

1. Don't use delegate_task for large token inputs to free models.
   Direct API calls with explicit timeout control are more reliable.

2. Always set max_tokens explicitly for schema generation calls.
   The model's default is often too small for comprehensive schemas.

3. Always post-process $comment placement after model output.
   Check for $comment keys inside properties dicts and move them up one level.

4. Budget 600s timeout for free-tier model calls with >50K input tokens.
   The 300s default times out regularly on OpenRouter free tier.


FILES PRODUCED
--------------

v1.0.0.schema.json      (22,810 chars, initial schema)
v1.1.0.schema.json      (27,635 chars, +10 gap fixes)
v1.2.0.schema.json      (28,626 chars, +4 refinements)
evolution-log.txt       (all changes with justification)
round2a-output.txt       (10 gaps from round 2a)
round2b-output.txt       (0 gaps - schema stable)
used-documents.txt       (24 docs tracked)
extracted/               (24 cached .md files)
