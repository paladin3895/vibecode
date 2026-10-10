# AGENT.md

Instructions for AI coding agents working in this repository.

## Project Overview

_TODO: describe what this project does._

## Working Agreements

- Keep changes small, focused, and reversible.
- Prefer editing existing files over creating new ones.
- Document notable decisions in [wiki/Decisions.md](wiki/Decisions.md).
- Keep the [wiki/](wiki/) vault up to date when architecture or conventions change.

## Project Structure

```
vibecode/
├── AGENTS.md           # This file — agent-facing instructions
├── wiki/               # Obsidian vault with project documentation
├── database/           # SQLite database files (git-ignored)
└── .agents/skills/     # Reusable agent skills (SKILL.md packages)
```

## Wiki (Obsidian)

The [wiki/](wiki/) folder is an Obsidian vault. Open it as a vault in Obsidian to
browse notes with backlinks and graph view. Agents should read relevant pages
before making architectural changes and update them afterward.

Start at [wiki/Home.md](wiki/Home.md).

## Skills

The [.agents/skills/](.agents/skills/) folder contains domain-specific skill
packages, discoverable by Copilot and other agents. Each skill lives in its
own folder with a `SKILL.md` file describing when and how to use it. See
[.agents/skills/README.md](.agents/skills/README.md) for the authoring
convention.

## Database (SQLite)

SQLite database files live in [database/](database/). When performing any
skill:

1. **Explore the schema first.** Before running queries, inspect the
   database(s) in [database/](database/) to learn what exists, e.g.
   `sqlite3 database/<file>.db ".tables"` and
   `sqlite3 database/<file>.db ".schema <table>"`. Don't assume table or
   column names.
2. **Query the relevant data.** Each skill describes which data it needs
   (tables, fields, filters). Query exactly that data and use it as context
   for the task, rather than guessing or relying on memory.
3. **Read-only by default.** Use `SELECT` queries only. Do not
   `INSERT`/`UPDATE`/`DELETE`/`DROP` or alter the schema unless the user or
   the skill explicitly asks for it.
4. **If the data isn't there,** say so (missing database, table, or rows)
   and ask the user rather than inventing values.

## Build / Test / Run

_TODO: fill in commands once the project has code (e.g. `npm install`,
`npm test`, `npm run dev`)._

## Conventions

_TODO: coding style, naming conventions, commit message format, etc._
