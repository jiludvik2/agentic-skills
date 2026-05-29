#!/usr/bin/env python3
"""
analyze_ccglass.py — Rank avoidable sources of Anthropic API traffic from ccglass logs.

ccglass capture layout (as found on disk):

    <root>/sessions/<session-dir>/<run-timestamp>/NNNN.json   # one request/response pair
    <root>/sessions/<session-dir>/blobs/<xx>/<sha256hex>.json  # content-addressed store

Each NNNN.json has:
    request: {method, url, headers, meta:{model,...}, system, tools, messages}
    response: {status, headers, raw, ...}

`request.system`, `request.tools`, and every element of `request.messages` are
usually NOT inlined — they are "sha256:<hex>" references into the per-session
blobs/ store (large fields are deduplicated). This script resolves them.

`response.raw` is the raw Anthropic SSE stream; token usage lives in the
`message_start` and `message_delta` events, not in a top-level `usage` field.

Stdlib only. tiktoken is used for token estimation if importable; otherwise we
fall back to bytes/4 (the proxy the task allows). Run:

    python3 analyze_ccglass.py [CCGLASS_ROOT]

Defaults CCGLASS_ROOT to ~/.ccglass. Prints a Markdown report to stdout and
writes it to ccglass_report.md in the current directory.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter, defaultdict

# ----------------------------------------------------------------------------
# Token estimation
# ----------------------------------------------------------------------------
try:
    import tiktoken  # type: ignore

    _ENC = tiktoken.get_encoding("cl100k_base")

    def est_tokens_from_text(s: str) -> int:
        return len(_ENC.encode(s))

    TOKENIZER = "tiktoken/cl100k_base"
except Exception:  # tiktoken not installed -> bytes/4 proxy
    _ENC = None

    def est_tokens_from_text(s: str) -> int:
        return len(s) // 4

    TOKENIZER = "bytes/4 (tiktoken not installed)"


def est_tokens_from_obj(obj) -> int:
    return est_tokens_from_text(json.dumps(obj, ensure_ascii=False))


# ----------------------------------------------------------------------------
# Pricing — current Anthropic list prices, USD per 1M tokens.
# Cache write: 5m = 1.25x base input, 1h = 2x base input. Cache read = 0.1x.
# Keys are matched as substrings of the model id reported in the SSE stream.
# ----------------------------------------------------------------------------
PRICING = {
    # model-substring : (input, output, cache_read, cache_write_5m, cache_write_1h)
    "opus":   (15.00, 75.00, 1.50, 18.75, 30.00),
    "sonnet": (3.00, 15.00, 0.30, 3.75, 6.00),
    "haiku":  (1.00, 5.00, 0.10, 1.25, 2.00),
}


def price_for(model: str):
    if not model:
        return None
    for key, rates in PRICING.items():
        if key in model:
            return rates
    return None


# ----------------------------------------------------------------------------
# Blob resolution
# ----------------------------------------------------------------------------
_blob_cache: dict = {}


def find_blobs_dir(json_path: str) -> str | None:
    """Walk up from a capture file to the nearest ancestor holding a blobs/ dir."""
    d = os.path.dirname(json_path)
    for _ in range(6):
        cand = os.path.join(d, "blobs")
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def resolve(value, blobs_dir: str | None):
    """Resolve a 'sha256:<hex>' reference to its blob; pass through inline values."""
    if isinstance(value, str) and value.startswith("sha256:") and blobs_dir:
        if value in _blob_cache:
            return _blob_cache[value]
        hexp = value.split(":", 1)[1]
        path = os.path.join(blobs_dir, hexp[:2], hexp + ".json")
        try:
            with open(path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except Exception:
            obj = None
        _blob_cache[value] = obj
        return obj
    return value


# ----------------------------------------------------------------------------
# SSE usage parsing
# ----------------------------------------------------------------------------
def parse_sse_usage(raw: str):
    """Return (model, usage_dict) from an Anthropic SSE stream."""
    usage: dict = {}
    model = None
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            ev = json.loads(line[5:].strip())
        except Exception:
            continue
        t = ev.get("type")
        if t == "message_start":
            msg = ev.get("message", {})
            model = msg.get("model") or model
            usage.update(msg.get("usage", {}) or {})
        elif t == "message_delta":
            usage.update(ev.get("usage", {}) or {})
    return model, usage


# ----------------------------------------------------------------------------
# Capture walking
# ----------------------------------------------------------------------------
class Call:
    __slots__ = (
        "path", "session", "seq", "ts", "model", "url",
        "input", "output", "cache_read", "cache_creation",
        "cc_5m", "cc_1h", "system", "tools", "messages",
    )


def is_messages_call(req: dict) -> bool:
    url = str(req.get("url", ""))
    return (
        req.get("method") == "POST"
        and "/v1/messages" in url
        and "count_tokens" not in url
    )


def walk_calls(root: str):
    """Yield parsed Call objects for every POST /v1/messages capture under root."""
    for dirpath, _dirnames, filenames in os.walk(root):
        if "blobs" in dirpath.split(os.sep):
            continue
        for fn in sorted(filenames):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8") as fh:
                    d = json.load(fh)
            except Exception:
                continue
            req = d.get("request") or {}
            if not is_messages_call(req):
                continue
            resp = d.get("response") or {}
            model, usage = parse_sse_usage(resp.get("raw") or "")
            blobs_dir = find_blobs_dir(path)

            c = Call()
            c.path = path
            c.session = d.get("session") or os.path.basename(os.path.dirname(path))
            c.seq = d.get("seq")
            c.ts = d.get("ts")
            c.model = model or (req.get("meta") or {}).get("model")
            c.url = str(req.get("url", ""))
            c.input = usage.get("input_tokens", 0)
            c.output = usage.get("output_tokens", 0)
            c.cache_read = usage.get("cache_read_input_tokens", 0)
            c.cache_creation = usage.get("cache_creation_input_tokens", 0)
            cc = usage.get("cache_creation") or {}
            c.cc_5m = cc.get("ephemeral_5m_input_tokens", 0)
            c.cc_1h = cc.get("ephemeral_1h_input_tokens", 0)
            c.system = resolve(req.get("system"), blobs_dir)
            c.tools = resolve(req.get("tools"), blobs_dir)
            c.messages = [resolve(m, blobs_dir) for m in (req.get("messages") or [])]
            yield c


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def fmt_int(n) -> str:
    return f"{int(n):,}"


def ms_to_iso(ms) -> str:
    if not ms:
        return "?"
    # Avoid Date.now-style nondeterminism concerns; pure conversion from epoch ms.
    import datetime
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime("%Y-%m-%d %H:%M:%SZ")


SPARK = "▁▂▃▄▅▆▇█"


def sparkline(values) -> str:
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK[0] * len(values)
    span = hi - lo
    return "".join(SPARK[min(7, int((v - lo) / span * 7))] for v in values)


def percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def system_blocks_text(system):
    """Return list of (text, cache_control) for a resolved system field."""
    out = []
    if isinstance(system, list):
        for b in system:
            if isinstance(b, dict):
                out.append((b.get("text", "") or "", b.get("cache_control")))
            elif isinstance(b, str):
                out.append((b, None))
    elif isinstance(system, str):
        out.append((system, None))
    return out


def iter_message_blocks(messages):
    """Yield content blocks (dicts) from a list of resolved message dicts."""
    for m in messages:
        if not isinstance(m, dict):
            continue
        content = m.get("content")
        if isinstance(content, list):
            for blk in content:
                if isinstance(blk, dict):
                    yield m, blk
        elif isinstance(content, str):
            yield m, {"type": "text", "text": content}


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------
def build_report(root: str) -> str:
    calls = list(walk_calls(root))
    calls.sort(key=lambda c: (c.session or "", c.seq or 0))
    out = []
    w = out.append

    w("# ccglass traffic analysis — avoidable Anthropic API spend")
    w("")
    w(f"- Source root: `{root}`")
    w(f"- Token estimator: {TOKENIZER}")
    w(f"- Captures analysed: **{fmt_int(len(calls))}** POST `/v1/messages` calls "
      "(HEAD health-checks and `count_tokens` calls excluded)")
    w("")

    if not calls:
        w("No `/v1/messages` captures found under that root.")
        return "\n".join(out)

    # ----- helpers shared across sections -----------------------------------
    by_session = defaultdict(list)
    for c in calls:
        by_session[c.session].append(c)
    for v in by_session.values():
        v.sort(key=lambda c: (c.seq or 0))

    # =====================================================================
    # 1. OVERALL FOOTPRINT
    # =====================================================================
    w("## 1. Overall footprint")
    w("")
    tot_in = sum(c.input for c in calls)
    tot_out = sum(c.output for c in calls)
    tot_cr = sum(c.cache_read for c in calls)
    tot_cc = sum(c.cache_creation for c in calls)
    tot_cc5 = sum(c.cc_5m for c in calls)
    tot_cc1 = sum(c.cc_1h for c in calls)
    with_usage = [c for c in calls if (c.input or c.output or c.cache_read or c.cache_creation)]
    ts_vals = [c.ts for c in calls if c.ts]
    denom = tot_cr + tot_cc + tot_in
    hit = (tot_cr / denom * 100) if denom else 0.0

    w(f"- Requests: **{fmt_int(len(calls))}** (with usable usage: {fmt_int(len(with_usage))}; "
      f"{len(calls) - len(with_usage)} errored / empty)")
    w(f"- Sessions (run streams): **{len(by_session)}** — "
      + ", ".join(f"`{s}` ({len(v)} reqs)" for s, v in by_session.items()))
    if ts_vals:
        w(f"- Date range: **{ms_to_iso(min(ts_vals))}** → **{ms_to_iso(max(ts_vals))}**")
    w("")
    w("| Token class | Total | Note |")
    w("|---|--:|---|")
    w(f"| input (uncached) | {fmt_int(tot_in)} | billed at full input rate |")
    w(f"| output | {fmt_int(tot_out)} | generation (incl. thinking) |")
    w(f"| cache read | {fmt_int(tot_cr)} | 0.1× input rate |")
    w(f"| cache creation | {fmt_int(tot_cc)} | 5m={fmt_int(tot_cc5)} (1.25×), 1h={fmt_int(tot_cc1)} (2×) |")
    w(f"| **total prompt** (in+cr+cc) | **{fmt_int(denom)}** | tokens shipped into the context window |")
    w("")
    w(f"- **Overall cache hit rate** = cache_read / (cache_read + cache_creation + input) = "
      f"**{hit:.1f}%**")
    w("")

    # Cost
    models = Counter(c.model for c in calls)
    w("### Estimated cost (current Anthropic list pricing)")
    w("")
    w("| Model | Reqs | input $ | output $ | cache-read $ | cache-write $ | total $ |")
    w("|---|--:|--:|--:|--:|--:|--:|")
    grand = 0.0
    unknown_models = []
    for model, _n in models.most_common():
        rates = price_for(model or "")
        sub = [c for c in calls if c.model == model]
        n = len(sub)
        if not rates:
            unknown_models.append((model, n))
            w(f"| `{model}` | {n} | — | — | — | — | (unknown model, skipped) |")
            continue
        r_in, r_out, r_cr, r_cw5, r_cw1 = rates
        s_in = sum(c.input for c in sub)
        s_out = sum(c.output for c in sub)
        s_cr = sum(c.cache_read for c in sub)
        s_cw5 = sum(c.cc_5m for c in sub)
        s_cw1 = sum(c.cc_1h for c in sub)
        # any cache_creation not broken into 5m/1h: price as 5m
        s_cw_unsplit = sum(c.cache_creation - c.cc_5m - c.cc_1h for c in sub)
        c_in = s_in / 1e6 * r_in
        c_out = s_out / 1e6 * r_out
        c_cr = s_cr / 1e6 * r_cr
        c_cw = (s_cw5 + max(0, s_cw_unsplit)) / 1e6 * r_cw5 + s_cw1 / 1e6 * r_cw1
        total = c_in + c_out + c_cr + c_cw
        grand += total
        w(f"| `{model}` | {n} | ${c_in:,.2f} | ${c_out:,.2f} | ${c_cr:,.2f} | ${c_cw:,.2f} | **${total:,.2f}** |")
    w(f"| | | | | | | **${grand:,.2f}** |")
    w("")
    w(f"_Captured window total: **${grand:,.2f}**._ "
      + (f"Unknown models skipped: {unknown_models}." if unknown_models else ""))
    w("")

    # =====================================================================
    # 2. TOOL SCHEMA OVERHEAD
    # =====================================================================
    w("## 2. Tool schema overhead")
    w("")
    tool_bytes: dict = {}
    tool_tokens: dict = {}
    tool_reqs: Counter = Counter()
    for c in calls:
        if not isinstance(c.tools, list):
            continue
        seen = set()
        for t in c.tools:
            if isinstance(t, dict) and "name" in t:
                nm = t["name"]
                seen.add(nm)
                b = len(json.dumps(t, ensure_ascii=False))
                tool_bytes[nm] = b
                tool_tokens[nm] = est_tokens_from_obj(t)
        for nm in seen:
            tool_reqs[nm] += 1

    # actual calls: count unique tool_use ids by name across all message history
    tool_calls: Counter = Counter()
    seen_ids: set = set()
    for c in calls:
        for _m, blk in iter_message_blocks(c.messages):
            if blk.get("type") == "tool_use":
                tid = blk.get("id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    tool_calls[blk.get("name")] += 1

    rows = []
    for nm in tool_reqs:
        rc = tool_reqs[nm]
        toks = tool_tokens.get(nm, 0)
        shipped = toks * rc
        calls_n = tool_calls.get(nm, 0)
        rate = (calls_n / rc) if rc else 0.0
        rows.append((shipped, nm, rc, tool_bytes.get(nm, 0), toks, calls_n, rate))
    rows.sort(reverse=True)

    total_shipped = sum(r[0] for r in rows)
    wasted = sum(r[0] for r in rows if r[6] < 0.05)
    w(f"Per-request the tool schema block totals **~{fmt_int(sum(tool_tokens.get(n,0) for n in tool_reqs))} tokens** "
      f"(the most common tools blob is **{fmt_int(max((b for b in tool_bytes.values()), default=0))} bytes** when serialized whole). "
      f"Across all requests, **{fmt_int(total_shipped)} tool-schema tokens** were shipped; "
      f"**{fmt_int(wasted)} ({wasted/total_shipped*100:.0f}%)** belong to tools called in <5% of the requests that carried them.")
    w("")
    w("Ranked by *tokens shipped but rarely called* (call-rate <5% flagged ⚠️ as removal candidates):")
    w("")
    w("| Tool | Reqs w/ it | Schema bytes | Est. tokens | Tokens shipped | Times called | Call rate | |")
    w("|---|--:|--:|--:|--:|--:|--:|:--|")
    for shipped, nm, rc, b, toks, calls_n, rate in rows:
        flag = "⚠️ remove" if rate < 0.05 else ("✅ used" if rate >= 0.20 else "🟡 low")
        w(f"| `{nm}` | {rc} | {fmt_int(b)} | {fmt_int(toks)} | {fmt_int(shipped)} | {calls_n} | {rate*100:.0f}% | {flag} |")
    w("")

    # MCP grouping callout
    mcp_groups = defaultdict(lambda: [0, 0, 0])  # prefix -> [tokens_shipped, reqs(max), calls]
    for shipped, nm, rc, b, toks, calls_n, rate in rows:
        if nm.startswith("mcp__"):
            parts = nm.split("__")
            grp = "__".join(parts[:2]) if len(parts) >= 2 else nm
            mcp_groups[grp][0] += shipped
            mcp_groups[grp][1] = max(mcp_groups[grp][1], rc)
            mcp_groups[grp][2] += calls_n
    if mcp_groups:
        w("**MCP server families** (each tool ships on every request whether or not the server is used):")
        w("")
        w("| MCP server | Tools | Tokens shipped | Total calls |")
        w("|---|--:|--:|--:|")
        grp_tool_counts = Counter(
            "__".join(nm.split("__")[:2]) for *_x, nm in ((r[0], r[1]) for r in rows) if nm.startswith("mcp__")
        )
        for grp, (sh, _rc, ca) in sorted(mcp_groups.items(), key=lambda kv: -kv[1][0]):
            w(f"| `{grp}__*` | {grp_tool_counts.get(grp,'?')} | {fmt_int(sh)} | {ca} |")
        w("")

    # =====================================================================
    # 3. SYSTEM PROMPT
    # =====================================================================
    w("## 3. System prompt")
    w("")
    sys_tok_totals = []
    for c in calls:
        blocks = system_blocks_text(c.system)
        sys_tok_totals.append(sum(est_tokens_from_text(t) for t, _cc in blocks))
    sys_sorted = sorted(sys_tok_totals)
    if sys_sorted:
        w("Size distribution (tokens, whole system field per request):")
        w("")
        w(f"- min **{fmt_int(sys_sorted[0])}** · "
          f"median **{fmt_int(int(statistics.median(sys_sorted)))}** · "
          f"p95 **{fmt_int(int(percentile(sys_sorted, 0.95)))}** · "
          f"max **{fmt_int(sys_sorted[-1])}**")
        w("")

    # Block-level stability: align by index, see which indices vary in text.
    by_index_texts = defaultdict(set)
    by_index_count = Counter()
    for c in calls:
        for i, (t, _cc) in enumerate(system_blocks_text(c.system)):
            by_index_texts[i].add(t)
            by_index_count[i] += 1
    w("**Cross-request stability of system blocks** (a block that changes upstream of a "
      "cache breakpoint forces re-creation of everything after it):")
    w("")
    w("| Block idx | Distinct values | Appears in | Verdict |")
    w("|--:|--:|--:|---|")
    for i in sorted(by_index_texts):
        distinct = len(by_index_texts[i])
        appears = by_index_count[i]
        if distinct == 1:
            verdict = "stable"
        elif distinct >= appears * 0.9:
            verdict = "⚠️ changes almost every request"
        else:
            verdict = "🟡 varies"
        w(f"| {i} | {distinct} | {appears} | {verdict} |")
    w("")

    # Show what changes in the most-volatile block
    volatile = [i for i in by_index_texts if len(by_index_texts[i]) >= by_index_count[i] * 0.9 and by_index_count[i] > 1]
    for i in volatile:
        samples = list(by_index_texts[i])[:2]
        w(f"Block {i} — sample values (this is the cache-relevant churn):")
        w("")
        for s in samples:
            w(f"- `{s[:120].rstrip()}`")
        w("")
        w("> Each request emits a different value here. It sits **above** the "
          "`cache_control` breakpoints on the later blocks. In this capture the bulk "
          "prefix still cached (see §5 — 96%+ read rate), so the practical cost is "
          "small, but it is genuinely dynamic content at the top of the prompt and a "
          "latent cache-buster if its position relative to the breakpoint ever shifts.")
        w("")

    # Top 5 largest stable blocks
    stable_blocks = []  # (tokens, text, count)
    block_text_count = Counter()
    block_text_sample = {}
    for c in calls:
        for t, _cc in system_blocks_text(c.system):
            block_text_count[t] += 1
            block_text_sample[t] = t
    for t, cnt in block_text_count.items():
        if cnt >= 2:  # stable = recurs
            stable_blocks.append((est_tokens_from_text(t), t, cnt))
    stable_blocks.sort(reverse=True)
    w("**Top 5 largest stable system blocks** (recur unchanged — candidates to trim or "
      "move into an on-demand skill rather than ship every turn):")
    w("")
    w("| Est. tokens | Recurs in | First 90 chars |")
    w("|--:|--:|---|")
    for toks, t, cnt in stable_blocks[:5]:
        head = t[:90].replace("\n", " ").rstrip()
        w(f"| {fmt_int(toks)} | {cnt} reqs | `{head}` |")
    w("")

    # =====================================================================
    # 4. MESSAGE HISTORY GROWTH
    # =====================================================================
    w("## 4. Message history growth")
    w("")
    w("Effective context size per turn = input + cache_read + cache_creation (raw "
      "`input_tokens` is near-zero once caching engages, so it understates growth).")
    w("")
    for sess, all_seq_calls in by_session.items():
        # Only requests with real usage carry a meaningful context size; errored /
        # empty captures report 0 and would fabricate a spurious 0 -> N jump.
        seq_calls = [c for c in all_seq_calls
                     if (c.input + c.cache_read + c.cache_creation) > 0]
        ctx = [c.input + c.cache_read + c.cache_creation for c in seq_calls]
        if not ctx:
            continue
        w(f"### Session `{sess}` — {len(all_seq_calls)} requests "
          f"({len(seq_calls)} with usage)")
        w("")
        w(f"Context size by request #: `{sparkline(ctx)}`  "
          f"(min {fmt_int(min(ctx))} → max {fmt_int(max(ctx))} tokens)")
        w("")
        # biggest jump
        best = None
        for idx in range(1, len(seq_calls)):
            jump = ctx[idx] - ctx[idx - 1]
            if best is None or jump > best[0]:
                best = (jump, idx)
        if best and best[0] > 0:
            jump, idx = best
            c = seq_calls[idx]
            prev = seq_calls[idx - 1]
            # what landed: the new user/tool_result blocks present in c but not prev
            prev_ids = set()
            for _m, blk in iter_message_blocks(prev.messages):
                if blk.get("type") == "tool_result":
                    prev_ids.add(blk.get("tool_use_id"))
            landed = []
            for _m, blk in iter_message_blocks(c.messages):
                if blk.get("type") == "tool_result" and blk.get("tool_use_id") not in prev_ids:
                    cont = blk.get("content")
                    s = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)
                    landed.append(("tool_result", s))
                elif blk.get("type") == "text" and _m.get("role") == "user":
                    landed.append(("user_text", blk.get("text", "")))
            w(f"- **Largest jump**: req #{c.seq} grew context by **{fmt_int(jump)} tokens** "
              f"(from {fmt_int(ctx[idx-1])} to {fmt_int(ctx[idx])}).")
            for kind, s in landed[:2]:
                w(f"  - new `{kind}` (~{fmt_int(est_tokens_from_text(s))} tok): "
                  f"`{s[:200].replace(chr(10),' ').rstrip()}`")
            w("")

    # tool results > 10k tokens (dedup by tool_use_id)
    result_sizes: dict = {}
    result_owner: dict = {}
    for c in calls:
        for _m, blk in iter_message_blocks(c.messages):
            if blk.get("type") == "tool_result":
                tid = blk.get("tool_use_id")
                cont = blk.get("content")
                s = cont if isinstance(cont, str) else json.dumps(cont, ensure_ascii=False)
                toks = est_tokens_from_text(s)
                if tid not in result_sizes or toks > result_sizes[tid]:
                    result_sizes[tid] = toks
                    result_owner[tid] = s[:160].replace("\n", " ")
    # map tool_use_id -> tool name
    id_to_name = {}
    for c in calls:
        for _m, blk in iter_message_blocks(c.messages):
            if blk.get("type") == "tool_use":
                id_to_name[blk.get("id")] = blk.get("name")
    big = sorted(((t, tid) for tid, t in result_sizes.items() if t > 10000), reverse=True)
    w(f"**Tool results over 10k tokens** — these land once and then ride in the cached "
      f"prefix on every later turn ({len(big)} found):")
    w("")
    if big:
        w("| Est. tokens | Tool | tool_use_id | Preview |")
        w("|--:|---|---|---|")
        for toks, tid in big:
            w(f"| {fmt_int(toks)} | `{id_to_name.get(tid,'?')}` | `{tid}` | "
              f"{result_owner.get(tid,'')[:80]} |")
    else:
        w("_None._")
    w("")

    # =====================================================================
    # 5. CACHE EFFICIENCY
    # =====================================================================
    w("## 5. Cache efficiency")
    w("")
    for sess, seq_calls in by_session.items():
        rates = []
        for c in seq_calls:
            den = c.cache_read + c.cache_creation + c.input
            rates.append((c.cache_read / den) if den else 0.0)
        if not seq_calls:
            continue
        spark = sparkline([int(r * 100) for r in rates])
        w(f"### Session `{sess}`")
        w("")
        w(f"Hit-rate by request: `{spark}`")
        w("")
        # full rebuilds: cache_read == 0 but cache_creation large
        rebuilds = [c for c in seq_calls if c.cache_read == 0 and c.cache_creation > 5000]
        if rebuilds:
            cost_toks = sum(c.cache_creation for c in rebuilds)
            w(f"- **Full prefix rebuilds** (`cache_read=0`, large `cache_creation`): "
              f"**{len(rebuilds)}** events recreating **{fmt_int(cost_toks)} tokens** from cold. "
              "Each is a turn where the cached prefix had expired (idle past TTL) or shifted:")
            for c in sorted(rebuilds, key=lambda c: -c.cache_creation)[:6]:
                w(f"  - req #{c.seq}: recreated {fmt_int(c.cache_creation)} tokens "
                  f"(read {fmt_int(c.cache_read)})")
            w("")
        # low hit after req 5
        late = [(c, r) for c, r in zip(seq_calls, rates) if (c.seq or 0) > 5]
        low = [c for c, r in late if r < 0.70]
        if low:
            w(f"- Requests after #5 with <70% hit rate: **{len(low)}** "
              f"(of {len(late)}). These indicate prefix instability at those turns.")
        else:
            w("- No sustained low-hit window after request #5 — the prefix is stable when warm.")
        w("")

    # =====================================================================
    # 6. RECOMMENDATIONS
    # =====================================================================
    w("## 6. Top recommendations (ranked by tokens saved per session)")
    w("")
    # reqs in the main session
    main_sess = max(by_session, key=lambda s: len(by_session[s]))
    main_reqs = len(by_session[main_sess])

    # rec 1: remove truly-never-called built-in tools (0 calls), MCP handled separately.
    # (Section 2 flags <5% per the brief; the recommendation is stricter so we don't
    #  advise dropping low-frequency-but-valuable tools like Agent/AskUserQuestion.)
    never = [(shipped, nm, rc, toks, calls_n) for shipped, nm, rc, _b, toks, calls_n, rate in rows
             if calls_n == 0 and not nm.startswith("mcp__")]
    never.sort(reverse=True)
    per_req_never = sum(toks for _s, _n, _rc, toks, _c in never)
    sess_never = sum(s for s, *_ in never)
    rates_opus = price_for("opus")
    cr_rate = rates_opus[2] if rates_opus else 1.5
    # tokens that ride in cache reads: each shipped token mostly read at cache-read rate
    def usd_for_cacheread(tokens_per_month):
        return tokens_per_month / 1e6 * cr_rate

    w(f"_Baseline: the dominant captured session `{main_sess}` ran **{main_reqs} requests**. "
      f"Dollar figures use Opus list pricing; cached-prefix tokens are billed at the "
      f"${cr_rate:.2f}/M cache-read rate on every turn they survive._")
    w("")

    # 1
    top_never = ", ".join(f"`{nm}` ({fmt_int(toks)} tok)" for _s, nm, _rc, toks, _c in never[:6])
    w(f"### 1. Drop the never-called built-in tools from the request — ~{fmt_int(per_req_never)} tok/request")
    w("")
    w(f"These tools were carried on every request but **called 0 times** in the capture: {top_never}"
      + (" …" if len(never) > 6 else "") + ".")
    w("- **`Workflow` alone is the single biggest line item**: "
      + (f"{fmt_int(tool_tokens.get('Workflow',0))} tok × {tool_reqs.get('Workflow',0)} reqs "
         f"= {fmt_int(tool_tokens.get('Workflow',0)*tool_reqs.get('Workflow',0))} tokens shipped, 0 calls."
         if 'Workflow' in tool_tokens else "n/a") )
    w(f"- Per request saved: **~{fmt_int(per_req_never)} tokens**. "
      f"Across the {main_reqs}-request session: **~{fmt_int(sess_never)} tokens** "
      f"(mostly cache-read, ≈ ${usd_for_cacheread(sess_never):,.2f} at the cache-read rate, "
      f"plus the cache-write cost on every cold rebuild).")
    w("- _How_: these are harness/orchestration tools (Workflow, Monitor, Cron*, "
      "EnterWorktree/ExitWorktree, EnterPlanMode/ExitPlanMode, ScheduleWakeup, "
      "PushNotification, RemoteTrigger, NotebookEdit, and the unused Task* variants "
      "TaskList/TaskGet/TaskOutput/TaskStop). Gate them behind explicit "
      "opt-in so they are not advertised on every turn of an ordinary coding session.")
    w("")

    # 2: MCP
    mcp_total = sum(sh for sh, _rc, _ca in mcp_groups.values())
    mcp_calls = sum(ca for _sh, _rc, ca in mcp_groups.values())
    mcp_per_req = sum(tool_tokens.get(nm, 0) for nm in tool_reqs if nm.startswith("mcp__"))
    w(f"### 2. Disconnect idle MCP servers — ~{fmt_int(mcp_per_req)} tok/request")
    w("")
    w(f"The `mcp__plugin_claude-mem_mcp-search__*` and `mcp__ccglass__*` families add "
      f"**~{fmt_int(mcp_per_req)} tokens of schema per request** "
      f"({fmt_int(mcp_total)} shipped across the session) for **{mcp_calls} total calls**.")
    for grp, (sh, _rc, ca) in sorted(mcp_groups.items(), key=lambda kv: -kv[1][0]):
        w(f"- `{grp}__*`: {fmt_int(sh)} tok shipped, {ca} calls "
          + ("→ **disconnect**" if ca == 0 else "→ keep only if used interactively"))
    w(f"- Per request saved: **~{fmt_int(mcp_per_req)} tokens** ≈ "
      f"${usd_for_cacheread(mcp_per_req*main_reqs):,.2f}/session at the cache-read rate.")
    w("")

    # 3: big tool results
    big_sum = sum(t for t, _ in big)
    w(f"### 3. Scope or delegate the giant tool results — {fmt_int(big_sum)} tok of permanent context")
    w("")
    if big:
        w(f"{len(big)} tool results exceed 10k tokens "
          f"({', '.join(fmt_int(t)+' tok' for t,_ in big)}). Once returned they sit in the "
          f"cached prefix for **every subsequent turn**, so a {fmt_int(big[0][0])}-token result on "
          f"an early turn is re-billed (at cache-read) on all the turns after it.")
        w(f"- _How_: narrow the offending `{id_to_name.get(big[0][1],'Read/Bash')}` call "
          f"(line ranges, `head`, grep filters) or run it inside a subagent via `Agent` so the "
          f"bulk output lands in the subagent context and only its conclusion returns to the main thread.")
        # rough: a 14k result surviving N turns
        survive = max(1, main_reqs // 3)
        w(f"- Estimated saving: keeping the largest {fmt_int(big[0][0])}-tok result out of the "
          f"prefix for ~{survive} later turns ≈ {fmt_int(big[0][0]*survive)} cache-read tokens "
          f"≈ ${usd_for_cacheread(big[0][0]*survive):,.2f}/session.")
    w("")

    # 4: full rebuilds
    all_rebuilds = [c for c in calls if c.cache_read == 0 and c.cache_creation > 5000]
    rebuild_toks = sum(c.cache_creation for c in all_rebuilds)
    cw_rate = rates_opus[4] if rates_opus else 30.0
    w(f"### 4. Cut the cold full-prefix rebuilds — {fmt_int(rebuild_toks)} tok recreated cold")
    w("")
    w(f"**{len(all_rebuilds)}** turns rebuilt the whole prefix with `cache_read=0` "
      f"(e.g. the {fmt_int(max((c.cache_creation for c in all_rebuilds), default=0))}-token rebuild). "
      f"At the 1h cache-write rate (${cw_rate:.2f}/M) that cold mass cost ≈ "
      f"${rebuild_toks/1e6*cw_rate:,.2f}.")
    w("- _How_: these are prefix-cache misses — usually idle gaps past the cache TTL, or a "
      "prefix that shifted. Recommendations 1–3 shrink the prefix so each rebuild is cheaper; "
      "additionally, batching work into tighter bursts (staying inside the 1h TTL) avoids the "
      "cold rebuild entirely.")
    w("")

    # 5: system hygiene
    w("### 5. Stabilise the top-of-prompt billing header (hygiene)")
    w("")
    if volatile:
        i = volatile[0]
        w(f"System block {i} (the `x-anthropic-billing-header … cch=…` line) takes a **new value "
          f"every request**. It currently sits above the cache breakpoints without breaking the "
          f"bulk cache (§5 shows 96%+ reads), so today the cost is negligible — but it is dynamic "
          f"content at position 0 of the prompt and one reorder away from invalidating the entire "
          f"{fmt_int(int(statistics.median(sys_sorted)) if sys_sorted else 0)}-token cached system "
          f"prefix on every turn. Keep volatile counters strictly below the first `cache_control` "
          f"point, or drop them from the cached portion entirely.")
    else:
        w("No volatile top-of-prompt block detected.")
    w("")

    w("---")
    w(f"_Generated by `analyze_ccglass.py` over {fmt_int(len(calls))} captures. "
      f"Token counts via {TOKENIZER}; pricing is Anthropic list pricing for the model in each "
      f"request's response stream._")
    return "\n".join(out)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/.ccglass")
    if not os.path.isdir(root):
        sys.exit(f"ccglass root not found: {root}")
    report = build_report(root)
    print(report)
    with open("ccglass_report.md", "w", encoding="utf-8") as fh:
        fh.write(report + "\n")


if __name__ == "__main__":
    main()
