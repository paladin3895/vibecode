---
name: brainstorm-idea
description: 'Use when brainstorming a new idea, feature, or project concept with the user and want to capture it as an Obsidian wiki page. Elicits the user''s vision, paraphrases it back to confirm shared understanding, asks clarifying questions when anything is vague or contradictory, then writes a wiki page with title, description, details, a relationship graph, and tags. Trigger phrases: "brainstorm", "let''s flesh out this idea", "capture this idea in the wiki", "help me think through this concept".'
argument-hint: '<short idea pitch, e.g. "a plugin that auto-tags notes">'
---

# Brainstorm Idea → Wiki Page

## Purpose

Turn a rough idea into a well-structured page in [wiki/Ideas/](../../../wiki/Ideas/),
while making sure the agent and the user actually agree on what the idea *is*
before it gets written down. The paraphrase-and-confirm loop is the point of
this skill — do not skip it, even if the idea sounds simple.

## When to Use

- User wants to brainstorm, flesh out, or think through a new idea/feature/project concept.
- User asks to "capture this in the wiki" or "write this up as a note".
- An idea emerged organically in conversation and is worth preserving before it's lost.

## Procedure

1. **Elicit.** If the user hasn't already described the idea, ask them to explain
   it in their own words. Don't start filling in gaps yet.

2. **Paraphrase back.** Restate the idea in your own words as a short paragraph:
   the problem it solves, who/what it's for, the core approach, and the rough
   scope. Ask the user directly: "Is this an accurate understanding?"

3. **Clarify ambiguity.** For every vague, missing, or contradictory point
   (e.g. unclear scope, conflicting goals, undefined terms), ask a targeted
   question — use the `vscode_askQuestions` tool when available instead of
   guessing or silently assuming. Repeat steps 2–3 until the user explicitly
   confirms the paraphrase is correct. Do not proceed to drafting while
   confusion remains.

4. **Classify.** Decide the right home for the note:
   - Default: a new page under `wiki/Ideas/`.
   - If the idea is already actionable/committed, suggest `wiki/Projects/`
     instead and confirm with the user.

5. **Propose the data model.** Identify the entities the idea manages and
   design a proposed SQLite schema for them. A later create-skill will use
   this schema to write relevant database queries, so be precise:
   - First inspect existing databases in [database/](../../../database/)
     (`sqlite3 database/<file>.db ".tables"` / `".schema <table>"`) to reuse
     existing tables and avoid name collisions. If none exist, say so.
   - For each entity define the **table name** (snake_case, plural),
     **columns** (name, SQLite type, constraints such as `PRIMARY KEY`,
     `NOT NULL`, `UNIQUE`, `DEFAULT`), **foreign keys**, and useful
     **indexes**.
   - Describe relationships (1:1, 1:N, N:M via a join table) and enumerated
     values (e.g. allowed `status` values).
   - Confirm entities and columns with the user (use `vscode_askQuestions`
     for unclear fields). Record guesses as open questions.
   - This is a **proposal only**: do not create or modify any database file.
     If the idea has no persistent data, write "No persistent data model"
     and explain why.

6. **Draft the page** using the [template](./templates/idea-page.md) with:
   - **Title** — short, specific noun phrase.
   - **Description** — one or two sentence summary (the "elevator pitch").
   - **Details** — the elaborated explanation: motivation, approach,
     assumptions, non-goals, and open questions still unresolved.
   - **Graph** — a Mermaid diagram showing the idea's components/relationships,
     plus `[[wikilinks]]` to any related existing notes so Obsidian's native
     graph view also picks up the connections.
   - **Data Model** — entity tables (columns, types, constraints, keys),
     relationships, and a Mermaid `erDiagram`, per step 5.
   - **Tags** — YAML frontmatter `tags:` list; always include `idea` plus 2-4
     topical tags (e.g. `[idea, cli, automation]`).

7. **Save and link.** Write the file to `wiki/Ideas/<Title>.md`. Add a link to
   it from [wiki/Ideas/Idea Index.md](../../../wiki/Ideas/Idea%20Index.md), and
   from [wiki/Home.md](../../../wiki/Home.md) if the idea is significant enough
   to surface at top level.

8. **Confirm the artifact.** Show the user the final page (or at least the
   description/details) and ask if it accurately captures the idea. Revise
   before considering the task done.

## Quality Checklist

- [ ] The agent paraphrased the idea and the user explicitly confirmed it before any file was written.
- [ ] Every ambiguous or contradictory point was clarified with the user, not assumed.
- [ ] The page has a title, description, details, a Mermaid graph, a data model (tables, columns, keys, relationships) or an explicit "no persistent data" note, and tags.
- [ ] Existing schemas in `database/` were inspected before proposing new tables.
- [ ] The page is linked from `Idea Index.md` (and `Home.md` if significant).

## Template

See [templates/idea-page.md](./templates/idea-page.md).
