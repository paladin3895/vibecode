# Agent Skills (SKILL.md) Reference

Folders of instructions, scripts, and resources that an agent loads on demand for a specialized task. Adapted from the VS Code Copilot `agent-customization` skill; agent-neutral.

## Structure

```
<skills-root>/<skill-name>/
├── SKILL.md           # Required (name must match folder)
├── scripts/           # Executable code
├── references/        # Docs loaded as needed
└── assets/            # Templates, boilerplate
```

## Locations

| Path | Scope | Read by |
| --- | --- | --- |
| `.agents/skills/<name>/` | Project | Copilot, Codex, others |
| `.github/skills/<name>/` | Project | Copilot |
| `.claude/skills/<name>/` | Project | Claude Code (Copilot also reads it) |
| `~/.agents/skills/<name>/` | Personal | Copilot, Codex, others |
| `~/.copilot/skills/<name>/` | Personal | Copilot |
| `~/.codex/skills/<name>/` | Personal | Codex |
| `~/.claude/skills/<name>/` | Personal | Claude Code (Copilot also reads it) |

Path support varies by agent and version. When unsure, use `.agents/skills/` and symlink where another agent needs a different path.

## SKILL.md format

```yaml
---
name: skill-name         # Required: 1-64 chars, lowercase alphanumeric + hyphens, must match folder
description: 'What and when to use. Max 1024 chars.'   # Required
---
```

Optional keys exist in some agents (for example `argument-hint`, `user-invocable`, `disable-model-invocation`). They are not portable: other agents may ignore them. Omit them unless the user targets a single agent.

### Body

- What the skill accomplishes
- When to use it (triggers and use cases)
- Step-by-step procedures
- Links to resources: `[script](./scripts/test.js)`

## Template

```markdown
---
name: webapp-testing
description: 'Test web applications using Playwright. Use for verifying frontend, debugging UI, capturing screenshots.'
---

# Web Application Testing

## When to Use
- Verify frontend functionality
- Debug UI behavior

## Procedure
1. Start the web server
2. Run [test script](./scripts/test.js)
3. Review screenshots in `./screenshots/`
```

## Progressive loading

1. **Discovery** (~100 tokens): the agent reads only `name` and `description`.
2. **Instructions** (under ~5000 tokens): the `SKILL.md` body loads when the skill looks relevant.
3. **Resources**: extra files load only when the body references them.

Keep file references one level deep from `SKILL.md`.

## Core principles

1. **Keyword-rich descriptions**: put trigger words in `description`; it is the only discovery surface.
2. **Progressive loading**: keep `SKILL.md` under about 500 lines; move detail into `references/`.
3. **Relative paths**: always reference bundled files relative to the skill folder (`./references/x.md`).
4. **Self-contained**: include all the procedural knowledge needed to finish the task.

## Anti-patterns

- **Vague descriptions**: "A helpful skill" does not enable discovery.
- **Monolithic SKILL.md**: everything in one file instead of references.
- **Name mismatch**: the folder name differs from the `name` field.
- **Missing procedures**: a description without step-by-step guidance.

## Pitfalls

- **YAML silent failures.** Unescaped colons in values, tabs instead of spaces, or a `name` that does not match the folder fail silently. Quote descriptions that contain colons.
- **Description is the discovery surface.** Use the "Use when..." pattern with specific keywords and trigger phrases.

## Validation checklist

- [ ] Folder is under a recognized skills root
- [ ] `name` matches the folder, lowercase with hyphens
- [ ] Frontmatter is valid YAML between `---` markers
- [ ] `description` states what it does and when to use it, under 1024 characters
- [ ] Referenced files exist and use relative paths
