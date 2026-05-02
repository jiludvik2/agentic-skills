# agentic-skills

A growing collection of skills, frameworks, and reference architectures for agentic AI systems — Claude Code, Microsoft Agent Framework, and other platforms that consume the SKILL.md / MCP convention.

## Skills

| Skill | What it does | Status |
|---|---|---|
| [`agent-component-advisor`](./agent-component-advisor/) | Decides whether a business requirement should be implemented as a prompt-driven skill, code-driven skill, tool, or hook. Walks a documented decision tree and returns a structured verdict. | v2.1 |

More skills will be added here over time. Each lives in its own top-level folder, contains a `SKILL.md` plus references and evals, and ships with a packaged `.skill` file ready to install.

## Installing a skill

Drop the skill's `.skill` file into your Claude Code skills directory:

```
~/.claude/skills/
```

Or extract it first to inspect:

```bash
unzip <skill-name>/<skill-name>.skill -d ~/.claude/skills/
```

See each skill's own `README.md` for full usage, trigger details, and methodology.

## Repository structure

```
agentic-skills/
├── README.md
├── LICENSE                                  (MIT)
├── .gitignore
└── <skill-name>/                            (one folder per skill)
    ├── README.md                            (skill docs, install, methodology)
    ├── SKILL.md                             (entry point — frontmatter + procedure)
    ├── <skill-name>.skill                   (packaged, ready to install)
    ├── evals/                               (test cases used to develop the skill)
    ├── references/                          (loaded on demand by the skill)
    └── docs/                                (optional — accompanying long-form docs)
```

## Contributing

This is a personal collection. If you find a skill useful or have a refinement, open an issue or PR.

## License

MIT. See [`LICENSE`](./LICENSE).
