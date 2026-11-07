---
name: create-skill
description: 'Use when the user wants to create, draft, or package a reusable agent skill (SKILL.md) from a workflow, conversation, or idea. Works across AI agents (Copilot, Codex, Claude Code). Trigger phrases: "create a skill", "make a skill for", "turn this workflow into a skill", "package this as a SKILL.md", "new agent skill".'
---

# Create Skill

Guide the user through creating a portable `SKILL.md` that any agent supporting the Agent Skills format can load.

Bundled references (load when needed):

- [references/skills.md](./references/skills.md): SKILL.md format, locations, template, principles, anti-patterns, validation checklist
- [references/choosing-a-primitive.md](./references/choosing-a-primitive.md): decide whether a skill, instructions, prompt, agent, hook, or MCP server fits

## 1. Extract from the conversation

Review the conversation first. If the user has been following a multi-step workflow (debugging approach, review checklist, implementation pattern), generalize it. Capture:

- The step-by-step process
- Decision points and branching logic
- Quality criteria or completion checks

## 2. Clarify only what is missing

If no clear workflow emerges, ask:

- What outcome should the skill produce?
- Which scope: this repository or personal (all projects)?
- Quick checklist or full multi-step workflow?

If the agent has no question tool, ask in plain text. If it is unclear that a skill is the right primitive, check [references/choosing-a-primitive.md](./references/choosing-a-primitive.md).

## 3. Choose the location

| Scope | Path | Read by |
| --- | --- | --- |
| Repository (default here) | `.agents/skills/<name>/SKILL.md` | Copilot, Codex, other agents |
| Repository (Claude Code) | `.claude/skills/<name>/SKILL.md` | Claude Code |
| Personal | `~/.agents/skills/<name>/SKILL.md` | Copilot, others |
| Personal (Codex) | `~/.codex/skills/<name>/SKILL.md` | Codex |
| Personal (Claude Code) | `~/.claude/skills/<name>/SKILL.md` | Claude Code |

In this repository, create skills under `.agents/skills/`. If Claude Code needs it, offer a symlink instead of copying:

```bash
mkdir -p .claude && ln -s ../.agents/skills .claude/skills
```

## 4. Write the SKILL.md

Follow the template and checklist in [references/skills.md](./references/skills.md).

Required frontmatter (keep to portable keys; avoid agent-specific ones such as `argument-hint` or `disable-model-invocation`):

```markdown
---
name: kebab-case-name          # must match the folder name
description: What it does AND when to use it. Include trigger phrases.
---

# Title

## When to use
## Steps
1. ...
## Completion checks
- ...
```

Principles:

- `description` is how the agent decides to load the skill. Make it specific, trigger-oriented, and under about 1024 characters.
- One skill, one responsibility. Split unrelated workflows.
- Write imperative, numbered steps. State decision points explicitly.
- Keep it self-contained. Put long reference material in sibling files (`reference.md`, `scripts/`, `templates/`) and link them with relative paths.
- Do not hard-code tool names from one agent. Describe the action ("search the workspace", "run in a terminal") so any agent can map it to its own tools.
- Follow this repository's rules in [AGENTS.md](../../../AGENTS.md) (e.g. read-only database by default).

## 5. Iterate

1. Save the draft.
2. Identify the most ambiguous or weak parts and ask the user about them.
3. When finalized, summarize what the skill produces, suggest example prompts to try, and propose related skills to create next.
4. Add a line for the new skill to [../README.md](../README.md) only if the user asks.
