# Skills

This folder holds reusable, domain-specific "skills" that an AI agent can load
on demand instead of keeping all instructions in context at once.

## Convention

Each skill lives in its own folder and contains a `SKILL.md` file:

```
skills/
└── my-skill/
    └── SKILL.md
```

`SKILL.md` must start with YAML frontmatter:

```markdown
---
name: my-skill
description: One or two sentences describing what this skill does and,
  importantly, WHEN an agent should use it (trigger phrases, task types).
---

# My Skill

Detailed, step-by-step instructions, examples, and references the agent
should follow once this skill is activated.
```

## Guidelines

- Keep `description` specific and trigger-oriented — it's how an agent decides
  whether to read the skill.
- Keep the skill self-contained; link to external docs rather than duplicating
  large reference material inline.
- One skill = one responsibility. Split unrelated workflows into separate
  skills instead of growing a single SKILL.md indefinitely.
- Reference supporting files (scripts, templates) relative to the skill's own
  folder, e.g. `skills/my-skill/template.md`.

See [example-skill/SKILL.md](example-skill/SKILL.md) for a minimal template.
