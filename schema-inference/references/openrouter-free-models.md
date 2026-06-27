1|OpenRouter Free Model Analysis for Schema Evolution
2|====================================================
3|
4|Date: 2026-06-27
5|Document size: ~300KB (~88K tokens each)
6|Rounds: 1-2 only (CREATE + REVIEW)
7|
8|
9|SELECTED MODEL
10|==============
11|
12|nvidia/nemotron-3-super-120b-a12b:free
13|
14|  Context:     1,000,000 tokens
15|  Parameters:  120B MoE (active 12B per token)
16|  Tools:       YES
17|  Structured:  YES (response_format, json_schema)
18|  Reasoning:   YES (reasoning toggle)
19|  Prompt cost: $0 (free)
20|  Completion:  $0 (free)
21|
22|Capacity at 88K tokens/doc:
23|  - System prompt + skill + schema: ~8K tokens
24|  - Output reserve: ~16K tokens
25|  - Available for docs: ~976K tokens
26|  - Documents per call: ~11
27|
28|Why this model:
29|  - Only free model with ALL THREE: structured output + reasoning + 1M context
30|  - Structured output eliminates JSON formatting errors in EVOLVE mode
31|  - Reasoning toggle improves gap detection quality in REVIEW mode
32|  - 1M context fits 11 docs/call vs 2 docs/call on 256K models
33|  - 120B MoE is large enough for complex financial document reasoning
34|
35|
36|RATE LIMITS
37|===========
38|
39|With $10-20 in OpenRouter pre-paid credits:
40|  - is_free_tier: false (credits purchased)
41|  - Free model requests: 20 per minute, 1,000 per day
42|  - DDoS protection: Cloudflare blocks extreme bursts
43|
44|Without credits (<$10):
45|  - Free model requests: 20 per minute, 50 per day
46|
47|Rounds 1-2 usage:
48|  - Round 1 (CREATE): 1 call (5 docs)
49|  - Round 2 (REVIEW): 2 calls (11 docs + 4 docs)
50|  - Total: 3 calls, well within 1,000/day limit
51|
52|If iterating beyond round 2:
53|  - Up to 1,000 calls/day = 11,000 documents reviewed/day
54|  - Rate limited to 20 calls/min = 220 docs/min throughput
55|
56|
57|THROUGHPUT EXPECTATIONS
58|=======================
59|
60|Free models queue behind paid requests. Estimated latency:
61|
62|Call size              Input tokens    Expected time
63|-----------------------------------------------------
64|5 docs (CREATE)       ~440K           30-90s
65|11 docs (REVIEW)      ~970K           60-180s
66|1-2 docs (EVOLVE)     ~10-20K         5-15s
67|
68|Total rounds 1-2: ~2-8 minutes wall clock
69|
70|Mitigation for slow responses:
71|  - Use /background for long REVIEW calls
72|  - Emit progress updates between calls
73|  - Consider pre-extracting fields with Marker for smaller payloads
74|    in round 3+ (not needed for rounds 1-2)
75|
76|
77|ALTERNATIVES CONSIDERED
78|========================
79|
80|Model                              Why not selected
81|---------------------------------------------------------------------------
82|nvidia/nemotron-3-ultra-550b:free  No structured output. 550B reasoning
83|  is marginally better, but loss of response_format means JSON Schema
84|  output relies on prompting alone. Not worth the tradeoff.
85|
86|qwen/qwen3-coder:free              No structured output. Strong at code/
87|  schema generation despite this, but Nemotron Super's guaranteed valid
88|  JSON via response_format is more reliable for EVOLVE mode.
89|
90|openrouter/owl-alpha               Unknown model quality on complex
91|  analytical work. Has structured output + 1M ctx. Worth testing as
92|  alternative but not first choice for production schema work.
93|
94|google/gemma-4-26b-a4b-it:free     Only 262K context = 2 docs/call.
95|  Would need 8 calls for round 2 vs 2 calls with Nemotron Super.
96|  Good for EVOLVE mode (no docs ingested) but not CREATE/REVIEW.
97|
98|google/gemma-4-31b-it:free         Same limitation as 26B. 262K ctx.
99|
100|qwen/qwen3-next-80b-a3b:free       262K context. Same docs/call issue.
101|
102|131K context models (gpt-oss,      CANNOT fit even 1 full document.
103|  llama-3.3-70b, hermes-3-405b)    Eliminated for raw document review.
104|
105|nousresearch/hermes-3-405b:free    No tool calling. Cannot do file I/O
106|  or automated validation. Eliminated.
107|
108|
109|DOCUMENT SIZE ANALYSIS
110|======================
111|
112|At 300KB/document:
113|  - Dense financial text: ~88K tokens/doc (4 bytes/token conservative)
114|  - Each doc consumes ~9% of 1M context window
115|  - 11 docs/call is the practical maximum (leaving room for system prompt,
116|    schema, and output)
117|
118|At smaller document sizes:
119|  - 100KB (~29K tokens): 33 docs/call in 1M context
120|  - 50KB (~14K tokens): 65 docs/call
121|  - Pre-extracted JSON (~5-20KB): 50-190 docs/call
122|
123|If documents are pre-extracted to key fields (using Marker/Docling)
124|before schema review, even 131K context models become viable at
125|~25 docs/call. But this defeats the purpose of rounds 1-2, which
126|need RAW documents to discover unexpected fields.
127|
128|
129|SETTING UP IN HERMES
130|=====================
131|
132|Persistent:
133|  hermes config set model.default nvidia/nemotron-3-super-120b-a12b:free
134|
135|Per-session:
136|  /model nvidia/nemotron-3-super-120b-a12b:free
137|
138|Per-delegation:
139|  delegate_task(goal="...", model={"model": "nvidia/nemotron-3-super-120b-a12b:free"})
140|
141|Enable reasoning for gap analysis:
142|  hermes config set model.reasoning medium
143|  Or pass reasoning_effort parameter per-call
144|
145|
146|CHECKING RATE LIMIT STATUS
147|===========================
148|
149|  curl -s "https://openrouter.ai/api/v1/key" \
150|    -H "Authorization: Bearer $OPENR...KEY"
151|
152|Returns: limit, limit_remaining, usage_daily, is_free_tier
153|