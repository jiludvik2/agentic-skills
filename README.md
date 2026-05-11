# agentic-skills

A growing collection of skills, frameworks, and reference architectures for agentic AI systems — Claude Code, Microsoft Agent Framework, and other platforms that consume the SKILL.md / MCP convention.

## Skills

| Skill | What it does | Status |
|---|---|---|
| [`skill-tool-hook-decision`](./skill-tool-hook-decision/) | Decides whether a business requirement should be implemented as a prompt-driven skill, code-driven skill, tool, or hook. Walks a documented decision tree and returns a structured verdict. | v2.1 |
| [`reqs-quality-review`](./reqs-quality-review/) | Reviews whether a user story or epic is ready to support implementation. Grades verifiable criteria (INVEST, Gherkin acceptance criteria, splitting patterns) and surfaces team-context questions separately. | new |
| [`sdlc`](./sdlc/SDLC.md) | AI-native, spec-anchored SDLC for solo operators working with AI agents. Filesystem-as-source-of-truth + verb cycle (capture → compile → plan → execute → verify → file → document), no external tracker. | v5.6 |

More skills will be added here over time. Packaged skills live in their own top-level folder containing a `SKILL.md`, references, evals, and a `.skill` file ready to install. Framework skills (like `sdlc`) are markdown-only — adopted by copying the framework doc into a target repo and pointing `CLAUDE.md` at it.

## Installing a skill

For packaged skills, drop the `.skill` file into your Claude Code skills directory:

```
~/.claude/skills/
```

Or extract it first to inspect:

```bash
unzip <skill-name>/<skill-name>.skill -d ~/.claude/skills/
```

For framework skills (like `sdlc`), copy the framework doc into the target repo and point `CLAUDE.md` at it.

See each skill's own `README.md` (or framework doc) for full usage, trigger details, and methodology.

## Repository structure

```
agentic-skills/
├── README.md
├── LICENSE                                  (MIT)
├── .gitignore
├── skill-tool-hook-decision/                 (packaged skill)
│   ├── SKILL.md
│   ├── README.md
│   ├── skill-tool-hook-decision.skill
│   ├── evals/
│   └── references/
├── reqs-quality-review/                    (skill, markdown-only)
│   ├── SKILL.md
│   └── references/
├── sdlc/                                    (framework skill)
│   └── SDLC.md
└── docs/                                    (cross-cutting reference material)
    └── *.md
```

## Contributing

This is a personal collection. If you find a skill useful or have a refinement, open an issue or PR.

## License

MIT. See [`LICENSE`](./LICENSE).
