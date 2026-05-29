# ccglass traffic analysis — avoidable Anthropic API spend

- Source root: `/Users/jiri/.ccglass`
- Token estimator: tiktoken/cl100k_base
- Captures analysed: **375** POST `/v1/messages` calls (HEAD health-checks and `count_tokens` calls excluded)

## 1. Overall footprint

- Requests: **375** (with usable usage: 370; 5 errored / empty)
- Sessions (run streams): **2** — `2026-05-29T07-22-13-797Z` (1 reqs), `2026-05-29T08-28-10-565Z` (374 reqs)
- Date range: **2026-05-29 07:35:13Z** → **2026-05-29 16:43:53Z**

| Token class | Total | Note |
|---|--:|---|
| input (uncached) | 47,667 | billed at full input rate |
| output | 329,405 | generation (incl. thinking) |
| cache read | 51,062,313 | 0.1× input rate |
| cache creation | 1,845,566 | 5m=400,636 (1.25×), 1h=1,444,930 (2×) |
| **total prompt** (in+cr+cc) | **52,955,546** | tokens shipped into the context window |

- **Overall cache hit rate** = cache_read / (cache_read + cache_creation + input) = **96.4%**

### Estimated cost (current Anthropic list pricing)

| Model | Reqs | input $ | output $ | cache-read $ | cache-write $ | total $ |
|---|--:|--:|--:|--:|--:|--:|
| `claude-opus-4-8` | 375 | $0.72 | $24.71 | $76.59 | $50.86 | **$152.87** |
| | | | | | | **$152.87** |

_Captured window total: **$152.87**._ 

## 2. Tool schema overhead

Per-request the tool schema block totals **~24,447 tokens** (the most common tools blob is **20,376 bytes** when serialized whole). Across all requests, **7,143,029 tool-schema tokens** were shipped; **6,033,865 (84%)** belong to tools called in <5% of the requests that carried them.

Ranked by *tokens shipped but rarely called* (call-rate <5% flagged ⚠️ as removal candidates):

| Tool | Reqs w/ it | Schema bytes | Est. tokens | Tokens shipped | Times called | Call rate | |
|---|--:|--:|--:|--:|--:|--:|:--|
| `Workflow` | 250 | 20,376 | 4,842 | 1,210,500 | 0 | 0% | ⚠️ remove |
| `Bash` | 371 | 6,348 | 1,578 | 585,438 | 166 | 45% | ✅ used |
| `Monitor` | 315 | 6,205 | 1,570 | 494,550 | 0 | 0% | ⚠️ remove |
| `Agent` | 250 | 6,678 | 1,521 | 380,250 | 12 | 5% | ⚠️ remove |
| `CronCreate` | 315 | 3,730 | 1,025 | 322,875 | 0 | 0% | ⚠️ remove |
| `TaskUpdate` | 315 | 3,588 | 912 | 287,280 | 20 | 6% | 🟡 low |
| `AskUserQuestion` | 250 | 5,028 | 1,123 | 280,750 | 5 | 2% | ⚠️ remove |
| `EnterPlanMode` | 250 | 4,343 | 979 | 244,750 | 0 | 0% | ⚠️ remove |
| `EnterWorktree` | 315 | 3,068 | 737 | 232,155 | 0 | 0% | ⚠️ remove |
| `ScheduleWakeup` | 250 | 3,717 | 899 | 224,750 | 0 | 0% | ⚠️ remove |
| `TaskCreate` | 315 | 2,855 | 635 | 200,025 | 9 | 3% | ⚠️ remove |
| `ExitWorktree` | 315 | 2,531 | 606 | 190,890 | 0 | 0% | ⚠️ remove |
| `Read` | 371 | 1,629 | 431 | 159,901 | 114 | 31% | ✅ used |
| `ExitPlanMode` | 250 | 2,575 | 576 | 144,000 | 0 | 0% | ⚠️ remove |
| `Skill` | 315 | 1,736 | 397 | 125,055 | 2 | 1% | ⚠️ remove |
| `NotebookEdit` | 315 | 1,555 | 375 | 118,125 | 0 | 0% | ⚠️ remove |
| `PushNotification` | 315 | 1,576 | 362 | 114,030 | 0 | 0% | ⚠️ remove |
| `RemoteTrigger` | 315 | 1,233 | 328 | 103,320 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__build_corpus` | 315 | 1,256 | 316 | 99,540 | 0 | 0% | ⚠️ remove |
| `TaskOutput` | 250 | 1,585 | 372 | 93,000 | 0 | 0% | ⚠️ remove |
| `TaskList` | 315 | 1,201 | 285 | 89,775 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__observation_record_event` | 315 | 975 | 255 | 80,325 | 0 | 0% | ⚠️ remove |
| `TaskGet` | 315 | 1,036 | 252 | 79,380 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__search` | 315 | 930 | 251 | 79,065 | 2 | 1% | ⚠️ remove |
| `Edit` | 315 | 1,001 | 243 | 76,545 | 188 | 60% | ✅ used |
| `mcp__plugin_claude-mem_mcp-search__observation_add` | 315 | 926 | 221 | 69,615 | 0 | 0% | ⚠️ remove |
| `WebSearch` | 315 | 869 | 217 | 68,355 | 0 | 0% | ⚠️ remove |
| `WebFetch` | 315 | 771 | 192 | 60,480 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__smart_search` | 315 | 762 | 187 | 58,905 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__timeline` | 315 | 714 | 180 | 56,700 | 0 | 0% | ⚠️ remove |
| `Write` | 315 | 663 | 164 | 51,660 | 13 | 4% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__memory_add` | 315 | 642 | 157 | 49,455 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__observation_search` | 315 | 592 | 155 | 48,825 | 0 | 0% | ⚠️ remove |
| `TaskStop` | 315 | 558 | 140 | 44,100 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__smart_unfold` | 315 | 537 | 138 | 43,470 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__observation_context` | 315 | 571 | 138 | 43,470 | 0 | 0% | ⚠️ remove |
| `mcp__ccglass__request_detail` | 315 | 463 | 138 | 43,470 | 0 | 0% | ⚠️ remove |
| `mcp__ccglass__recent_requests` | 315 | 496 | 129 | 40,635 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search____IMPORTANT` | 315 | 433 | 113 | 35,595 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__query_corpus` | 315 | 433 | 112 | 35,280 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__get_observations` | 315 | 421 | 111 | 34,965 | 2 | 1% | ⚠️ remove |
| `mcp__ccglass__usage_summary` | 315 | 439 | 108 | 34,020 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__observation_generation_status` | 315 | 415 | 106 | 33,390 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__rebuild_corpus` | 315 | 395 | 100 | 31,500 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__smart_outline` | 315 | 398 | 99 | 31,185 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__memory_search` | 315 | 377 | 99 | 31,185 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__reprime_corpus` | 315 | 395 | 97 | 30,555 | 0 | 0% | ⚠️ remove |
| `CronDelete` | 315 | 378 | 96 | 30,240 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__memory_context` | 315 | 365 | 94 | 29,610 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__prime_corpus` | 315 | 374 | 92 | 28,980 | 0 | 0% | ⚠️ remove |
| `mcp__ccglass__list_sessions` | 315 | 281 | 73 | 22,995 | 0 | 0% | ⚠️ remove |
| `CronList` | 315 | 243 | 63 | 19,845 | 0 | 0% | ⚠️ remove |
| `mcp__plugin_claude-mem_mcp-search__list_corpora` | 315 | 224 | 58 | 18,270 | 0 | 0% | ⚠️ remove |

**MCP server families** (each tool ships on every request whether or not the server is used):

| MCP server | Tools | Tokens shipped | Total calls |
|---|--:|--:|--:|
| `mcp__plugin_claude-mem_mcp-search__*` | 21 | 969,885 | 4 |
| `mcp__ccglass__*` | 4 | 141,120 | 0 |

## 3. System prompt

Size distribution (tokens, whole system field per request):

- min **0** · median **1,830** · p95 **2,154** · max **2,156**

**Cross-request stability of system blocks** (a block that changes upstream of a cache breakpoint forces re-creation of everything after it):

| Block idx | Distinct values | Appears in | Verdict |
|--:|--:|--:|---|
| 0 | 373 | 373 | ⚠️ changes almost every request |
| 1 | 1 | 373 | stable |
| 2 | 6 | 373 | 🟡 varies |

Block 0 — sample values (this is the cache-relevant churn):

- `x-anthropic-billing-header: cc_version=2.1.156.e51; cc_entrypoint=cli; cch=9803e;`
- `x-anthropic-billing-header: cc_version=2.1.156.4d0; cc_entrypoint=cli; cch=7c5fb;`

> Each request emits a different value here. It sits **above** the `cache_control` breakpoints on the later blocks. In this capture the bulk prefix still cached (see §5 — 96%+ read rate), so the practical cost is small, but it is genuinely dynamic content at the top of the prompt and a latent cache-buster if its position relative to the breakpoint ever shifts.

**Top 5 largest stable system blocks** (recur unchanged — candidates to trim or move into an on-demand skill rather than ship every turn):

| Est. tokens | Recurs in | First 90 chars |
|--:|--:|---|
| 2,109 | 36 reqs | `# Reviewer — fresh-context code-quality review with classified findings  You are the SDLC` |
| 1,814 | 20 reqs | `# Verifier — fresh-context review of spec ↔ diff alignment  You are the SDLC verifier sub-` |
| 1,786 | 185 reqs | ` You are an interactive agent that helps users with software engineering tasks.  IMPORTANT` |
| 1,763 | 65 reqs | ` You are an interactive agent that helps users with software engineering tasks.  IMPORTANT` |
| 694 | 65 reqs | `You are an agent for Claude Code, Anthropic's official CLI for Claude. Given the user's me` |

## 4. Message history growth

Effective context size per turn = input + cache_read + cache_creation (raw `input_tokens` is near-zero once caching engages, so it understates growth).

### Session `2026-05-29T08-28-10-565Z` — 374 requests (370 with usage)

Context size by request #: `▁▁▁▁▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▃▃▃▃▃▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▅▅▅▁▁▁▁▁▁▅▁▁▁▁▁▁▁▅▅▅▅▅▅▅▅▅▅▅▅▅▁▁▁▁▁▅▁▁▁▁▁▁▁▅▅▅▅▁▁▁▁▁▁▂▂▂▂▂▂▅▅▅▅▅▅▅▅▅▅▅▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▆▇▇▇▇▇▇▇▁▁▁▁▁▁▁▁▁▇▁▁▁▁▁▁▁▁▁▁▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇█▁▁▁▁▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▂▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▃▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▁▂▁▁▁▁▁▁▂▂▁▁▂▂▂▁▂▁▂▂▂▂▂▂▂▃▃▃▃▄▄▄▄`  (min 615 → max 375,294 tokens)

- **Largest jump**: req #204 grew context by **304,817 tokens** (from 30,255 to 335,072).
  - new `user_text` (~1,995 tok): `<system-reminder> As you answer the user's questions, you can use the following context: # claudeMd Codebase and user instructions are shown below. Be sure to adhere to these instructions. IMPORTANT:`
  - new `user_text` (~10 tok): `Talk me through how to setup pypi trusted publisher`

**Tool results over 10k tokens** — these land once and then ride in the cached prefix on every later turn (3 found):

| Est. tokens | Tool | tool_use_id | Preview |
|--:|---|---|---|
| 15,452 | `Read` | `toolu_01UKKGGhFzcjLq8hLqCurWdN` | <system-reminder>[Truncated: PARTIAL view — showing lines 1-1344 of 2586 total ( |
| 11,381 | `Read` | `toolu_01LJFYEZM1bkiUQuwCCSmgrX` | 1	--- 2	title: Reimagined Software Delivery Lifecycle 3	purpose: How Claude Code |
| 10,974 | `Read` | `toolu_015HvndVQcshJ1BMZm6uRLDi` | 1	.github/workflows/release.yml                      |  4 +- 2	 code-review/.cla |

## 5. Cache efficiency

### Session `2026-05-29T07-22-13-797Z`

Hit-rate by request: `▁`

- No sustained low-hit window after request #5 — the prefix is stable when warm.

### Session `2026-05-29T08-28-10-565Z`

Hit-rate by request: `▁▁▁▆█▇▇█▇█▁▇▇██▇▇█▁▇▇█▇███▇▇█▇▇▇▇▇▇█▇▆▆▇▇█▇█████▇▇▇████▇▇█▇▇█▁██████████████████████████▁▄▅▇▇█▇▃▄▅▆▇▇▇▇█████▇██████▃▅▆▇▇▇▃▄▇▇▇▇▇▇███▅▄▇▄▇▇▇▇▇▇▇▇▇▇████████████▂▇▇▇█▇▁▇▇▇▇████████████▁▁▇██████▁▅▅▆▇▇▇▇▇▇▃▄▅▇▇▇▇▇▇▇█▇██████████▇██████████████▁█████▁▆▆▇▇▇▇▇█▇██▇▇█▇███▇▇▇▇▇▇▇▇▇▇▇▇▃██▇▇███████▇██▇▇▇▇▇███████▁▆▆▆▆▆▆▇▅▆▇▇▆▇▇▆▇▇▇▇▆▇▇▇▇█▇▇▇▇▇▇█▇▇█▇▇█▇█▇▇▇█▇▇▇▇▇█▇██████▇███▇██▇▇████▇█`

- **Full prefix rebuilds** (`cache_read=0`, large `cache_creation`): **7** events recreating **411,491 tokens** from cold. Each is a turn where the cached prefix had expired (idle past TTL) or shifted:
  - req #65: recreated 192,250 tokens (read 0)
  - req #20: recreated 67,981 tokens (read 0)
  - req #12: recreated 59,056 tokens (read 0)
  - req #4: recreated 43,920 tokens (read 0)
  - req #306: recreated 27,374 tokens (read 0)
  - req #92: recreated 10,487 tokens (read 0)

- Requests after #5 with <70% hit rate: **28** (of 370). These indicate prefix instability at those turns.

## 6. Top recommendations (ranked by tokens saved per session)

_Baseline: the dominant captured session `2026-05-29T08-28-10-565Z` ran **374 requests**. Dollar figures use Opus list pricing; cached-prefix tokens are billed at the $1.50/M cache-read rate on every turn they survive._

### 1. Drop the never-called built-in tools from the request — ~13,916 tok/request

These tools were carried on every request but **called 0 times** in the capture: `Workflow` (4,842 tok), `Monitor` (1,570 tok), `CronCreate` (1,025 tok), `EnterPlanMode` (979 tok), `EnterWorktree` (737 tok), `ScheduleWakeup` (899 tok) ….
- **`Workflow` alone is the single biggest line item**: 4,842 tok × 250 reqs = 1,210,500 tokens shipped, 0 calls.
- Per request saved: **~13,916 tokens**. Across the 374-request session: **~3,885,120 tokens** (mostly cache-read, ≈ $5.83 at the cache-read rate, plus the cache-write cost on every cold rebuild).
- _How_: these are harness/orchestration tools (Workflow, Monitor, Cron*, EnterWorktree/ExitWorktree, EnterPlanMode/ExitPlanMode, ScheduleWakeup, PushNotification, RemoteTrigger, NotebookEdit, and the unused Task* variants TaskList/TaskGet/TaskOutput/TaskStop). Gate them behind explicit opt-in so they are not advertised on every turn of an ordinary coding session.

### 2. Disconnect idle MCP servers — ~3,527 tok/request

The `mcp__plugin_claude-mem_mcp-search__*` and `mcp__ccglass__*` families add **~3,527 tokens of schema per request** (1,111,005 shipped across the session) for **4 total calls**.
- `mcp__plugin_claude-mem_mcp-search__*`: 969,885 tok shipped, 4 calls → keep only if used interactively
- `mcp__ccglass__*`: 141,120 tok shipped, 0 calls → **disconnect**
- Per request saved: **~3,527 tokens** ≈ $1.98/session at the cache-read rate.

### 3. Scope or delegate the giant tool results — 37,807 tok of permanent context

3 tool results exceed 10k tokens (15,452 tok, 11,381 tok, 10,974 tok). Once returned they sit in the cached prefix for **every subsequent turn**, so a 15,452-token result on an early turn is re-billed (at cache-read) on all the turns after it.
- _How_: narrow the offending `Read` call (line ranges, `head`, grep filters) or run it inside a subagent via `Agent` so the bulk output lands in the subagent context and only its conclusion returns to the main thread.
- Estimated saving: keeping the largest 15,452-tok result out of the prefix for ~124 later turns ≈ 1,916,048 cache-read tokens ≈ $2.87/session.

### 4. Cut the cold full-prefix rebuilds — 411,491 tok recreated cold

**7** turns rebuilt the whole prefix with `cache_read=0` (e.g. the 192,250-token rebuild). At the 1h cache-write rate ($30.00/M) that cold mass cost ≈ $12.34.
- _How_: these are prefix-cache misses — usually idle gaps past the cache TTL, or a prefix that shifted. Recommendations 1–3 shrink the prefix so each rebuild is cheaper; additionally, batching work into tighter bursts (staying inside the 1h TTL) avoids the cold rebuild entirely.

### 5. Stabilise the top-of-prompt billing header (hygiene)

System block 0 (the `x-anthropic-billing-header … cch=…` line) takes a **new value every request**. It currently sits above the cache breakpoints without breaking the bulk cache (§5 shows 96%+ reads), so today the cost is negligible — but it is dynamic content at position 0 of the prompt and one reorder away from invalidating the entire 1,830-token cached system prefix on every turn. Keep volatile counters strictly below the first `cache_control` point, or drop them from the cached portion entirely.

---
_Generated by `analyze_ccglass.py` over 375 captures. Token counts via tiktoken/cl100k_base; pricing is Anthropic list pricing for the model in each request's response stream._
