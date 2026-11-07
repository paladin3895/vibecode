# Choosing the Right Customization

Use this before creating a skill, to confirm a skill is the right tool. Adapted from the VS Code Copilot `agent-customization` skill; agent-neutral.

## Decision flow

| Primitive | Use when | Typical file |
| --- | --- | --- |
| Agent instructions | Always-on rules that apply everywhere in the project | `AGENTS.md` (also `CLAUDE.md`, `.github/copilot-instructions.md`) |
| Scoped instructions | Rules for specific files or folders | Agent-specific (for example `*.instructions.md` in Copilot) |
| Skill | On-demand workflow with bundled scripts or templates | `SKILL.md` |
| Prompt / slash command | Single focused task with parameterized input | Agent-specific (for example `*.prompt.md`, `.claude/commands/`) |
| Custom agent / subagent | Context isolation, or different tool restrictions per stage | Agent-specific (for example `*.agent.md`, `.claude/agents/`) |
| Hooks | Deterministic shell commands at lifecycle events (block tools, auto-format) | Agent-specific config |
| MCP server | Integrates external systems, APIs, or data | Agent-specific config |

Only `AGENTS.md` and `SKILL.md` are broadly portable across agents. Prefer them.

## Edge cases

- **Instructions vs skill?** Applies to most work: instructions. Applies to specific tasks: skill.
- **Skill vs prompt?** Multi-step workflow with bundled assets: skill. Single task with inputs: prompt.
- **Skill vs custom agent?** Same capabilities for every step: skill. Needs context isolation or per-stage tool limits: custom agent.
- **Hooks vs instructions?** Instructions guide behavior and are non-deterministic. Hooks enforce behavior and can block operations.

## Instruction pitfalls

- Always-on instructions load into every interaction, so keep them short and put task-specific detail into skills.
- Do not duplicate content between `AGENTS.md` and skills; link instead.

## Creation process

1. **Scope**: ask whether it is for this project (shared with the team) or personal (all projects).
2. **Primitive**: pick from the decision flow above.
3. **Create**: write the file at the correct path with valid frontmatter and a body that follows the template.
4. **Validate**: confirm location, YAML syntax, and a meaningful `description`.

If the agent has a read-only exploration or subagent feature, use it to check existing patterns in the codebase. If it has a question tool, use it to interview the user; otherwise ask in plain text.
