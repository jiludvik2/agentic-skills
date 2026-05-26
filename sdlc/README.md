# sdlc — AI-native spec-anchored delivery workflow

A software delivery lifecycle for a solo operator working with AI agents. The filesystem is the source of truth, git history is the audit trail, Claude Code is the primary development agent, and there is no external tracker (Jira, Notion, etc.). Work is a small set of verbs — capture, compile, plan, execute, verify, review, file, document — applied as needed, not as a fixed sequence.

## What's in this folder

```
sdlc/
├── SKILL.md              skill entry point: bootstrap-or-route + version-check
├── README.md             this file
└── references/
    ├── SDLC.md           the canonical process (the body of knowledge)
    ├── verifier.md       fresh-context spec↔diff verifier sub-agent
    └── reviewer.md       fresh-context code-quality reviewer sub-agent
```

## How it installs

Install the skill like any other in this repo — drop the `sdlc/` folder into your Claude Code skills directory (`~/.claude/skills/sdlc/`) or install the repo as a plugin. There is **one** install path; the skill does the rest.

The skill is self-bootstrapping. On its **first invocation in a project** it detects that the project isn't SDLC-initialised and sets it up:

1. Scaffolds the `/sdlc/` tree (`raw/`, `work/active/`, `work/done/`, `docs/...`).
2. Copies the canonical `references/SDLC.md` into the project as `/sdlc/SDLC.md` — the project's pinned, authoritative copy.
3. Installs the `verifier` and `reviewer` sub-agents into `/.claude/agents/`.
4. Points the repo's `CLAUDE.md` at `/sdlc/SDLC.md`.
5. Seeds `/sdlc/STATE.md`.

On **every later invocation** it routes to the project-local `/sdlc/SDLC.md` (the source of truth, which may have been customised) and runs the session-start protocol.

## Why a bundled copy per project, not a shared one

The runtime source of truth is always the project-local `/sdlc/SDLC.md`, never the skill's bundled copy. Each project pins its own version. This is deliberate: an SDLC upgrade must never silently change a running project's workflow mid-stream. When the bundled version moves ahead of a project's pinned copy, the skill *offers* an upgrade and waits for an explicit decision — it never auto-applies.

## The two sub-agents

Verify and Review are non-negotiable steps in the loop, and both run with **no memory of how the implementation was built** — fresh context is the whole point.

- **`verifier`** answers *"did you build the right thing?"* — walks the spec's acceptance criteria against the diff, runs the tests, and reports AC alignment, coverage, architectural drift, and security/attribution issues. Read-only.
- **`reviewer`** answers *"did you build it well?"* — reports code-quality findings classified Critical / Important / Minor / Nit, at task level and (cross-cutting) at story level. Read-only.

Both reference architecture and NFR docs by convention (`sdlc/docs/architecture/`) rather than by fixed filename, so they work in any project.

## Adapting to your stack

`references/SDLC.md` is harvested from a live project, so a few hard rules are project-specific examples rather than universal law — most obviously rule #26's `make audit` (a Python pip-audit gate) and the ADR-0008 sandbox references. During a project's first compile, adapt or drop the rules that don't fit your stack and renumber. The workflow itself — the verbs, the autonomy gate, tests-first, fresh-context Verify/Review, filesystem-as-truth — is stack-agnostic.

## Origin

Adapted from Mark Strefford's SDLC harness (https://github.com/markstrefford/claude-skills/tree/main/sdlc) and informed by spec-driven development, Anthropic's fresh-context PR-review practice, and Karpathy's LLM-managed-wiki pattern. See the References section of `references/SDLC.md`.
