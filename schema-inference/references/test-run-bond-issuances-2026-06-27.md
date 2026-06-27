Schema Inference Test Run: Bond Issuances
==========================================

Date: 2026-06-27
Source: /Users/jiri/Code/2026/funding-data/docs/bond-issuances/ (374 PDFs)
Output: /Users/jiri/Code/2026/funding-data/docs/bond-issuances-schema/
Model: openrouter/owl-alpha (free tier, via delegate_task)


RESULTS
-------

Round 1 (INFER):   5 docs -> schema v1.0.0 (22 properties, 495 lines)
Round 2a (REVIEW):  8 docs -> 12 gaps (4 critical, 6 high) -> v1.1.0
Round 2b (REVIEW):  7 docs ->  9 gaps (3 critical, 4 high) -> v1.2.0

Final schema: v1.2.0 (1269 lines, 22 properties, 22 $defs)
Docs analyzed: 20 of 374
Remaining: 354


KEY LEARNINGS
-------------

1. Batch splitting is mandatory for free models.
   A single call with 15 docs (~970K tokens) timed out after 600s.
   Splitting into 8-doc and 7-doc batches worked reliably.

2. PyMuPDF4LLM is the right extraction tool.
   - ~1 second per document
   - No GPU, no model downloads
   - Works with `uv run --with pymupdf4llm`
   - Marker is 200x slower (2+ min/doc) and downloads 1.3GB+ models

3. Document size varies more than expected.
   These pricing supplements are 120-550KB but only produce 3-9K tokens
   of markdown text each (compact legal text, not verbose prose).
   The 88K token/doc estimate from the original analysis was for
   denser document types.

4. Schema evolution pattern works well.
   Each round found real gaps (dual-currency, callable schedules,
   floating rate details, green notes, hybrid note types).
   The v1.0.0 -> v1.2.0 progression captured meaningful improvements.

5. Dedup tracking via used-documents.txt is simple and effective.
   No document was accidentally reused across rounds.


CRITICAL GAPS FOUND
-------------------

- Payment currency != specified currency (BRL/INR/ARS payable in USD)
- Fungible notes with multiple existing tranches (up to 17 tranches)
- Callable notes with stepped redemption schedules
- Floating rate reference rates (SOFR, SONIA, TONIA)
- Hybrid note types (Fixed Rate + Currency Linked)
- Green/sustainable bond listing venues
- Local clearing systems (KCSD) not in initial enum


FILES PRODUCED
--------------

bond-issuance-pricing-supplement.schema.json  (v1.2.0, 36KB)
evolution-log.txt                            (all changes tracked)
gap-report-round2a.txt                       (12 gaps)
gap-report-round2b.txt                       (9 gaps)
used-documents.txt                           (20 docs)
extracted/                                   (20 cached .md files)
