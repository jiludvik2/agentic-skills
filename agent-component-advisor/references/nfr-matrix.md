# Non-Functional Concerns Matrix

Use this when the user asks "why this type and not that one?" — the comparative answer is in the matrix.

| Concern | Prompt-skill | Code-skill | Tool (incl. MCP) | Hook / middleware |
|---|---|---|---|---|
| **Determinism** | Probabilistic | Deterministic | Deterministic interface; behaviour depends on backend | Deterministic |
| **Observability** | Hard — needs LLM trace tooling, prompt diffs | Medium — stdout/stderr, can wrap with logging | Strong — native metrics, structured logs, distributed tracing | Strong — runs in agent runtime telemetry |
| **Security surface** | Prompt-injection, instruction subversion | Sandbox-bounded; supply-chain risk in deps | IAM/OAuth scopes, secret store, network policy | Last line of defence — redaction, scope check |
| **Blast radius of change** | Wide, silent — affects every agent that loads it | Bounded to the script; versioned with the skill | Bounded by schema; semver + contract tests catch breaks | Wide — applies to every call it intercepts |
| **Latency profile** | Token-bound, variable; degrades on long context | Bounded by script runtime | Bounded by backend; timeouts enforceable | Microseconds to low ms; on every call |
| **Token cost** | Full skill text in context per session | Output only enters context | Schema only enters context | None to the model (runtime-side) |
| **Data residency** | Always sends data to the model | Local processing | Depends on tool deployment region | Local to the runtime |
| **Testability** | LLM-as-judge eval suites; flaky | Unit tests | Unit + contract + integration tests | Unit tests; replay tests on captured traces |
| **Versioning model** | Description + body, no semver convention | Versioned with the skill bundle | Semver + schema versioning | Versioned with the agent runtime / plugin |
