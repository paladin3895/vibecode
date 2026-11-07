---
name: implement-idea
description: 'Use when the user wants to build an idea that is captured in the wiki (wiki/Ideas) from its spec. Reads the idea page, proposes an implementation plan and waits for approval, then creates the SQLite schema, skills, scripts, and dependencies it describes, documents the system design and each feature in wiki/Projects, updates shared wiki pages, and populates links back into the idea page. Works across AI agents (Copilot, Codex, Claude Code). Trigger phrases: "implement the idea", "build this idea", "implement the spec", "turn the idea into a project", "document the system design and features", "link the implementation back to the idea page".'
---

# Implement Idea

Turn an idea page in [wiki/Ideas/](../../../wiki/Ideas/) into a working implementation, document how it works in the wiki, and link everything back from the idea page.

The idea page is the spec. Follow [AGENTS.md](../../../AGENTS.md): inspect the live database before touching it, and keep changes small and reversible.

## When to use

- An idea from `brainstorm-idea` is confirmed and ready to build.
- The user asks for the system design or feature descriptions to be written into the wiki.
- The user wants to add a feature to an already implemented project (see [Adding a feature to an existing project](#adding-a-feature-to-an-existing-project)).

Do not use it to brainstorm (use `brainstorm-idea`) or to audit an existing implementation (use `validate-idea-implementation`).

## Procedure

### 1. Select and read the idea

1. Use the idea the user named. Otherwise list `wiki/Ideas/`, and ask which one. Stop if the page does not exist.
   If `wiki/Projects/<Idea Title>/` already exists, switch to [Adding a feature to an existing project](#adding-a-feature-to-an-existing-project).
2. Read the whole page. Extract:
   - **Features**: each distinct capability the Details describe.
   - **Data model**: tables, columns, constraints, keys, indexes, enumerations.
   - **Deliverables**: skills, scripts, code, templates, or reports it expects.
   - **Dependencies**: libraries, CLIs, and services mentioned or implied.
   - **Open questions** and **non-goals**.
3. If an open question blocks the build, ask the user before planning. If the spec is ambiguous or contradictory, ask; do not guess.

### 2. Inspect the current state

1. Check whether any of it already exists: pages under `wiki/Projects/`, matching skills in `.agents/skills/`, scripts, and tables in [database/](../../../database/) (`.tables`, `.schema <table>`).
2. Reuse what exists. Report name collisions and partial implementations in the plan.

### 3. Propose the plan and wait for approval

Do not change anything until the user approves. Present:

1. **Features** to build, in dependency order.
2. **Database changes**: the exact SQL (`CREATE TABLE`, indexes), which database file, and whether a backup is needed. Reuse existing tables where possible.
3. **Files** to create or edit: skills, scripts, code, templates.
4. **Dependencies** to install, with the exact commands and where they install (see step 5).
5. **Wiki pages** to create or update (step 7).
6. **Decisions** worth an ADR, and any deviation from the spec.

Revise the plan until the user approves. Approval of the plan covers the SQL and installs listed in it; anything new needs fresh approval.

### 4. Implement the database

1. Back up the database file before changing it (for example copy to `database/<file>.db.bak-<date>`; the folder is git-ignored).
2. Apply only the approved SQL, with foreign keys on (`PRAGMA foreign_keys=ON`). Use transactions, and stop on the first error.
3. Verify with `PRAGMA table_info`, `PRAGMA foreign_key_list`, `PRAGMA index_list`, `PRAGMA foreign_key_check`. Confirm the live schema matches the idea page's Data Model.
4. Never drop or rewrite existing data or tables not in the plan.

### 5. Install dependencies

1. Install only what the approved plan lists. Prefer project-local environments (the repository `.venv` for Python, local `node_modules` for Node). Do not use `sudo` or system-wide installs; if one is required, tell the user to run it.
2. Pin or record the versions installed (for example in `requirements.txt` or `package.json`) if the repository already tracks them.
3. Verify each dependency imports or runs before relying on it.
4. Record the dependency and why it is needed in the system design page.

### 6. Implement features

1. Build features in plan order. Keep each change focused; prefer editing existing files.
2. Skills follow the `create-skill` conventions: `.agents/skills/<name>/SKILL.md`, portable frontmatter, quoted `description`, relative links.
3. Code and skills use only the tables and columns defined in the schema. Writes need user confirmation where the idea says so.
4. After each feature, run a smoke test on a copy or fixture of the database, never the live one, and fix failures before moving on.
5. If the implementation must deviate from the spec, stop, tell the user, and record the deviation in the ADR and the idea page.

### 7. Document in the wiki

Use the Obsidian layout below. Prefer updating existing notes over creating near-duplicates.

```
wiki/Projects/<Idea Title>/
├── <Idea Title>.md        # Overview (from templates/project-overview.md)
├── System Design.md       # From templates/system-design.md
└── Features/
    └── <Feature>.md       # One per feature, from templates/feature-page.md
```

1. **Overview**: purpose, status, links to the idea, system design, every feature, and the implementation artifacts.
2. **System Design**: components, a Mermaid component or data-flow diagram, the final data model (table descriptions and `erDiagram`), interfaces (skills, scripts, commands, files), dependencies and why, security and privacy notes, and deviations from the spec.
3. **Feature pages**: one per feature, covering what it does, how to trigger it, inputs and outputs, the tables and files it touches, rules and edge cases, an example, and how it was tested.
4. **Shared pages**:
   - [Project Index](../../../wiki/Projects/Project%20Index.md): add the project.
   - [Home](../../../wiki/Home.md): add it if significant.
   - [Architecture](../../../wiki/Architecture.md): add or extend the Components and Data Flow sections.
   - [Decisions](../../../wiki/Decisions.md): add ADRs at the top using its template.
   - [Glossary](../../../wiki/Glossary.md): add new terms.
5. Use `[[wikilinks]]` with full vault paths for wiki notes (for example `[[Projects/<Idea Title>/System Design|System Design]]`). Use relative markdown links for repository files (skills, scripts, database folder).
6. Every new page has YAML frontmatter `tags:` (for example `[project, design]`, `[project, feature]`) and a Related section linking back to the idea and overview.

### 8. Link back into the idea page

Edit the idea page; keep its existing content and add or update one `## Implementation` section:

```markdown
## Implementation

- **Status**: implemented | partial
- **Overview**: [[Projects/<Idea Title>/<Idea Title>|<Idea Title>]]
- **System design**: [[Projects/<Idea Title>/System Design|System Design]]
- **Features**: [[Projects/<Idea Title>/Features/<Feature>|<Feature>]], ...
- **Decisions**: [[Decisions]] (<ADR title>)
- **Skills / scripts**: [<name>](../../.agents/skills/<name>/SKILL.md), ...
- **Database**: `database/<file>.db` tables `<table>`, ...
```

Resolve the relative paths from the idea page's location. Mark open questions that are now resolved, and note any deviation. Add `implemented` or `project` to the idea's `tags:` only if it is not already there. Do not move the idea out of `wiki/Ideas/`.

### 9. Verify and report

1. Run `validate-idea-implementation` for this idea, or its checks if the skill is unavailable: schema matches, deliverables exist, wiki links resolve, test cases pass on a copy.
2. Fix gaps you introduced. Ask before changing anything else.
3. Report briefly: what was built, files and tables created, dependencies installed, wiki pages written or updated, deviations, and anything not done or not run.

## Adding a feature to an existing project

Use this mode when `wiki/Projects/<Idea Title>/` already exists and the user wants a new capability. Run steps 1-9 above, with these changes. Plan and build only the delta; never rebuild what exists.

1. **Define the feature in the spec first.** If the idea page does not describe it, ask the user for the feature's behavior, inputs, outputs, and data needs. With approval, add it to the idea page's Details (and Data Model if needed) so the spec and implementation stay in sync.
2. **Read the current state.** Read the project overview, System Design, existing Feature pages, the `## Implementation` section, and the live schema. Note which existing features share tables, files, or skills with the new one.
3. **Delta plan (step 3).** List only new or changed items:
   - New tables or indexes with `CREATE`, and new columns with `ALTER TABLE ... ADD COLUMN`. Show the SQL and back up first.
   - Never drop, rename, or rewrite existing columns or data. If a breaking change is unavoidable, call it out and get separate approval.
   - Files to create or edit, new dependencies, and which existing features could be affected.
4. **Implement (steps 4-6).** Extend existing skills and scripts instead of duplicating them. Keep existing behavior and interfaces unchanged unless the plan says otherwise.
5. **Regression check.** Re-run the existing features' tests on a copy or fixture of the database, and confirm they still pass. Report any that fail before continuing.
6. **Document (step 7), append only:**
   - Add `Features/<New Feature>.md` from the feature template.
   - In the overview, append to Features and Artifacts, update Status if it changed, and add a dated line under a `## Changelog` section (create it if missing).
   - In System Design, update components, data model, interfaces, and dependencies for the delta. Keep unchanged sections as they are.
   - Add an ADR to [Decisions](../../../wiki/Decisions.md) if the change affects the design, and update Architecture and Glossary only where they changed.
7. **Link back (step 8), append only.** Add the new feature to the existing `## Implementation` section without removing existing links. Mark the feature as implemented in the idea page's Details.
8. **Verify (step 9).** Run `validate-idea-implementation` on the whole idea, not just the new feature, and report new and pre-existing findings separately.

## Completion checks

- [ ] The user approved the plan before any change.
- [ ] In add-feature mode, only the delta was changed, existing tests were re-run, and existing links and sections were kept.
- [ ] A database backup was made before schema changes, and the live schema matches the idea page or the documented deviation.
- [ ] Dependencies are installed locally, versions recorded, and each verified.
- [ ] Each feature was smoke-tested on a copy or fixture, not the live database.
- [ ] Overview, System Design, and one page per feature exist with tags and a Related section.
- [ ] Project Index, Architecture, and Decisions are updated (plus Home and Glossary where relevant).
- [ ] The idea page has an Implementation section whose links all resolve.
- [ ] Validation was run and the result reported.

## Templates

- [templates/project-overview.md](./templates/project-overview.md)
- [templates/system-design.md](./templates/system-design.md)
- [templates/feature-page.md](./templates/feature-page.md)
