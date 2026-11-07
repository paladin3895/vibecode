---
name: validate-idea-implementation
description: 'Use when the user wants to check that an idea captured in the wiki (wiki/Ideas or wiki/Projects) has been implemented correctly. Compares the idea page''s proposed SQLite data model with the live database, checks that the skills, scripts, or code it describes exist and behave as specified, checks wiki consistency, and runs test cases against a copy of the data. Reports a pass/fail checklist and offers fixes after confirmation. Works across AI agents (Copilot, Codex, Claude Code). Trigger phrases: "validate the idea", "is this idea implemented", "check implementation against the wiki", "does the database match the idea page", "audit this feature", "verify the implementation", "test the idea".'
---

# Validate Idea Implementation

Audit whether an idea page in [wiki/](../../../wiki/) matches what actually exists in the repository. The idea page is the spec; the database, skills, scripts, and wiki links are the implementation.

Follow [AGENTS.md](../../../AGENTS.md): the database is read-only by default, and the live schema is authoritative over memory or assumptions.

## When to use

- After an idea from `brainstorm-idea` has been built (fully or partly).
- Before promoting an idea from `wiki/Ideas/` to `wiki/Projects/`.
- When the schema, skills, or wiki may have drifted from each other.

## Procedure

### 1. Select the idea

1. If the user named an idea, open that page. Otherwise list `wiki/Ideas/` and `wiki/Projects/` and ask which one to validate. If several are plausible, ask; do not guess.
2. If the page does not exist, say so and stop.
3. Read the whole page. Extract a checklist of claims:
   - **Data model**: tables, columns, types, constraints, foreign keys, indexes, enumerations.
   - **Behavior**: workflows, skills, scripts, or commands the Details section says should exist, and what each should do.
   - **Wiki structure**: tags, links, index entries, diagrams.
   - **Open questions** and **non-goals**: record them; do not treat open questions as failures.

### 2. Validate the data model against the live database

Skip with an explicit note if the page says "No persistent data model".

1. List the SQLite files in [database/](../../../database/). If none exist, report every table as missing. If several exist and the page does not say which, ask.
2. Open read-only (for example `sqlite3 -readonly database/<file>.db`). Never create, alter, or write.
3. For each table on the page, inspect the live schema: `.tables`, `PRAGMA table_info(<table>)`, `PRAGMA foreign_key_list(<table>)`, `PRAGMA index_list(<table>)`, and `.schema <table>`.
4. Compare and classify each item as **match**, **missing**, **extra** (in the database but not on the page), or **different** (type, nullability, default, key, or constraint mismatch). Treat SQLite type affinity as equivalent (for example `DECIMAL(16,2)` is acceptable where the page says `NUMERIC`), and note it.
5. Check enumerations with the `CHECK` constraint if present, otherwise with `SELECT DISTINCT <col>`. Report values outside the documented set.
6. Check referential integrity: `PRAGMA foreign_key_check;` and `PRAGMA integrity_check;`.
7. Check the page's `erDiagram` agrees with its own tables.

### 3. Validate behavior (skills, scripts, code)

1. For each skill, script, or command the page describes, confirm it exists. Search `.agents/skills/`, `scripts/`, and the repository. A skill must have a `SKILL.md` whose folder name matches its `name`, valid frontmatter, and a `description` with trigger phrases.
2. Read each implementation and compare it with the described behavior. Check:
   - It reads and writes the tables and columns the data model defines (no invented column names).
   - It respects stated rules, such as confirm-before-write or read-only queries.
   - Referenced files, templates, and relative links resolve.
3. Flag behavior described but not implemented, and implementation present but not documented.

### 4. Validate wiki consistency

- The page is linked from its index ([Idea Index](../../../wiki/Ideas/Idea%20Index.md) or [Project Index](../../../wiki/Projects/Project%20Index.md)) and, if significant, [Home](../../../wiki/Home.md).
- Frontmatter `tags:` is present and includes `idea` (or the project tag).
- All `[[wikilinks]]` and relative links resolve to existing pages.
- Mermaid blocks are syntactically plausible: fenced as `mermaid` and balanced.
- Decisions that changed the design are recorded in [Decisions](../../../wiki/Decisions.md).

### 5. Run test cases

1. Derive test cases from the page's Details and from each skill's own procedure. Cover at least one typical case, one edge case (boundary values, empty data, missing input), and one failure case (invalid input, missing database).
2. Write each case as: prompt or command, preconditions, expected result, pass criteria. Define the criteria before running.
3. **Never run write tests against the live database.** Copy it to a temporary location (for example `/tmp/<name>-test.db`) or build a small fixture with the live schema, and point the test at the copy. If a skill cannot be pointed at another database, run only its read-only paths and mark the write paths as not run.
4. Check real artifacts (rows, files, command output), not the agent's summary. Confirm the live database file hash is unchanged before and after.
5. If running a case needs side effects outside the repository (network, installs, credentials), skip it, mark it **not run**, and say why.
6. Remove temporary copies when done.

### 6. Report

Deliver the report in the response only. Do not write report files unless the user asks. Use this shape:

```markdown
## Validation: <Idea title>

**Verdict:** PASS | PARTIAL | FAIL  (<n> passed, <n> failed, <n> not run)

### Data model
| Item | Status | Detail |
| --- | --- | --- |

### Behavior
| Item | Status | Detail |
| --- | --- | --- |

### Wiki
| Check | Status | Detail |
| --- | --- | --- |

### Test cases
| # | Case | Result | Evidence |
| --- | --- | --- | --- |

### Gaps and suggested fixes
1. <gap> -> <fix> (target: idea page | database | skill | script)
```

Rules for the report:

- Use only **PASS**, **FAIL**, **WARN**, and **NOT RUN**. Cite the evidence (query output, file and line) for every FAIL.
- WARN is for drift that is not wrong, such as an extra column or an unresolved open question.
- Do not claim a PASS for anything that was not inspected or run.

### 7. Offer fixes (after confirmation)

1. List each gap with its target: the idea page, the database, a skill or script, or the wiki.
2. Ask which fixes to apply. Apply only the approved ones.
3. When the page and the implementation disagree, ask which one is correct. Do not assume either.
4. Schema changes (`ALTER`, `CREATE`, `DROP`, data updates) need explicit user approval for each statement, per [AGENTS.md](../../../AGENTS.md). Show the SQL first, and back up the database before applying.
5. After applying fixes, re-run only the affected checks and report the new status.

## Completion checks

- [ ] The idea page was read in full and a claim checklist was extracted.
- [ ] The live schema was inspected read-only; no database file was modified.
- [ ] Every claim has a status with evidence, and nothing is marked PASS without being checked.
- [ ] Write-path tests ran only on a copy or fixture, and the live database hash is unchanged.
- [ ] Temporary files were removed.
- [ ] Fixes were applied only with confirmation, and affected checks were re-run.
