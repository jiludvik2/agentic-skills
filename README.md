# agentic-skills

A growing collection of skills, frameworks, and reference architectures for agentic AI systems — Claude Code, Microsoft Agent Framework, and other platforms that consume the SKILL.md / MCP convention.

## Skills

| Skill | What it does | Status |
|---|---|---|
| [`skill-tool-hook-decision`](./skill-tool-hook-decision/) | Decides whether a business requirement should be implemented as a prompt-driven skill, code-driven skill, tool, or hook. Walks a documented decision tree and returns a structured verdict. | v2.1 |
| [`reqs-quality-review`](./reqs-quality-review/) | Reviews whether a user story or epic is ready to support implementation. Grades verifiable criteria (INVEST, Gherkin acceptance criteria, splitting patterns) and surfaces team-context questions separately. | new |
| [`sdlc`](./sdlc/) | AI-native, spec-anchored SDLC for solo operators working with AI agents. Filesystem-as-source-of-truth + verb cycle (capture → compile → plan → execute → verify → review → file → document), no external tracker. Self-bootstrapping: scaffolds itself into a project on first use. | v6.4 |
| [`gsd-api-first`](./gsd-api-first/) | GSD addon: inserts a contract-first API design step between discuss-phase and planning. Reads project context to derive a complete HTTP contract proposal (Google AIP, Zalando, RFC 9457, OpenAPI), presents it for confirmation in a single round, then commits `API-SPEC.md` before the planner runs. Installs `/api-phase` and `/api-plan` skills plus a discuss-phase patch. | new |
| [`gsd-standard-enforcement`](./gsd-standard-enforcement/) | GSD addon: patches three GSD core workflows to enforce architecture contracts, generate ADRs for significant decisions captured during discuss-phase, and enable full-codebase code-review audits via an `--audit` flag. | new |

More skills will be added here over time. There are two patterns:

- **Packaged skills** — a top-level folder with `SKILL.md`, references, evals, and a `.skill` file ready to install globally.
- **GSD addons** (`gsd-*`) — project-level extensions to the [GSD workflow](./sdlc/). Each addon ships an `install.py` that copies skill files and config into a target project. They are not installed globally; run the installer once per project.

## Installing a skill

For packaged skills, drop the `.skill` file into your Claude Code skills directory:

```
~/.claude/skills/
```

Or extract it first to inspect:

```bash
unzip <skill-name>/<skill-name>.skill -d ~/.claude/skills/
```

The `sdlc` skill installs the same way, then bootstraps itself: on first invocation in a project it scaffolds the `/sdlc/` tree, copies its canonical process doc and sub-agents in, and points `CLAUDE.md` at them. See [`sdlc/README.md`](./sdlc/README.md).

See each skill's own `README.md` (or framework doc) for full usage, trigger details, and methodology.

## Repository structure

```
agentic-skills/
├── README.md
├── LICENSE                                  (MIT)
├── .gitignore
├── skill-tool-hook-decision/                (packaged skill)
│   ├── SKILL.md
│   ├── README.md
│   ├── skill-tool-hook-decision.skill
│   ├── evals/
│   └── references/
├── reqs-quality-review/                     (skill, markdown-only)
│   ├── SKILL.md
│   └── references/
├── sdlc/                                    (self-bootstrapping skill)
│   ├── SKILL.md
│   ├── README.md
│   └── references/
│       ├── SDLC.md
│       ├── verifier.md
│       └── reviewer.md
├── gsd-api-first/                           (GSD addon — installs into a project)
│   ├── README.md
│   ├── install.py
│   └── target/                              (files copied into the target project)
│       ├── .agents/skills/api-phase/
│       ├── .agents/skills/api-plan/
│       ├── .agents/skills/gsd-discuss-phase/
│       └── .claude/
├── gsd-standard-enforcement/               (GSD addon — patches GSD core files)
│   ├── README.md
│   ├── install.py
│   └── target/
│       ├── agents/
│       └── gsd-core/workflows/
└── docs/                                    (cross-cutting reference material)
    └── *.md
```

## Contributing

This is a personal collection. If you find a skill useful or have a refinement, open an issue or PR.

## License

MIT. See [`LICENSE`](./LICENSE).
