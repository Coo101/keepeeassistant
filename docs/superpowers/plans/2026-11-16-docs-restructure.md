# Docs Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 600-line `docs/SPEC.md` with a short entry point plus seven
area files, turn `docs/TODO.md` into a roadmap, and write the new way of working
into `CLAUDE.md` and the agent files.

**Architecture:** Area files are written first, straight from the old SPEC (which
stays intact until Task 5, so every task can read its source). Then the entry
point replaces the old SPEC, then the roadmap, the instructions, and the
references elsewhere. A mapping checklist proves nothing was lost.

**Tech Stack:** Markdown. Code files are touched only in comments (Task 8),
checked with ruff, black and pytest.

**Spec:** `docs/superpowers/specs/2026-11-16-docs-restructure-design.md`.

## Global Constraints

- Move and trim text; never change meaning. Every requirement, acceptance line and
  decision of the old SPEC lands in exactly one place, or is listed as removed on
  purpose in `docs/superpowers/plans/2026-11-16-docs-mapping.md` (Task 1).
- Area file headings, in this order: `## Purpose`, `## Data`, `## Behaviour`,
  `## Acceptance`, `## Decisions`, `## Planned`. Empty ones say "None yet."
- Area files 60–150 lines; `SPEC.md` ~100, at most ~150.
- Decisions keep their global number: `- **D16** (2026-xx-xx if known): …`.
- Cross-area links as relative Markdown links (`[shopping](shopping.md)`), no
  section numbers anywhere in the new docs.
- English, same plain style as the current docs (short sentences, no marketing).
- Briefs for opencode `docs` follow CLAUDE.md "Writing a brief": paste the source
  sections into the brief, name the one file to write, give the headings above.
- Commits only when the user asks; stage files by name.

## Review Focus

1. **Silently dropped lines.** An acceptance check or decision in the old SPEC that
   appears in no new file. Caught by the mapping checklist (Task 1) and the grep in
   Task 5.
2. **Duplicated truth.** The same rule written in two area files with different
   wording (access, utilities). One owns it; the other links. Checked in Task 9.
3. **Dangling pointers.** Any `SPEC §`, `§9.`, `§13` or `decision 16` left in docs,
   agents, code or the kitchen mode docs. Grep in Task 9.
4. **Agents still reading the whole spec.** An agent file that tells the local
   model to read `docs/SPEC.md` "for what the app does" instead of the area file
   from the brief. Grep in Task 7.
5. **Broken flow in CLAUDE.md.** The new steps, the review threshold and the agents
   table disagree with each other or with the agent files. Read-through in Task 9.

---

### Task 1: Mapping checklist

**Files:**
- Create: `docs/superpowers/plans/2026-11-16-docs-mapping.md`

- [ ] **Step 1:** List every heading of the old `docs/SPEC.md` (`grep -n "^#" docs/SPEC.md`)
  and every numbered decision in §13, one checkbox each, with its target from the
  design's table: e.g. `- [ ] §9.17 Bills → spec/finance.md`, `- [ ] D16 →
  spec/kitchen.md`. §1–§4, §10 (minus security), §12 and cross-cutting decisions →
  `SPEC.md`; §10 security and §11 → `operations.md`; §14 → `TODO.md`. §9.9 splits:
  login/camps → `accounts.md`, recipes/ingredients → `recipes.md`. §9.15 splits:
  stock → `kitchen.md`, camp needs → `shopping.md`.
- [ ] **Step 2:** Add a "Removed on purpose" section (empty for now).
- [ ] **Step 3: Verify:** the number of checkboxes equals headings + decisions
  (`grep -c "^#" docs/SPEC.md` plus the decision count).

### Task 2: `planning.md` and `shopping.md`

**Files:**
- Create: `docs/spec/planning.md`, `docs/spec/shopping.md`

Two opencode `docs` runs (one file each), or Claude. Brief per file: the old SPEC
sections from the mapping (pasted), the six headings, the line budget, "keep D-numbers".

- [ ] **Step 1:** Write `planning.md` from §5, §6 camps + planning, §7, §9.3, §9.4,
  §9.7, §9.8, §9.11, §9.13 and their decisions. Keep the §7 code block and its
  acceptance examples verbatim.
- [ ] **Step 2:** Write `shopping.md` from §6 shopping, §8 (code block verbatim),
  §9.5, §9.6, §9.12, the camp-needs part of §9.15, their decisions. Link to
  `kitchen.md` for the utility stock.
- [ ] **Step 3: Review (Claude):** each line of the source sections is present in
  meaning; tick the mapping boxes; `wc -l` within 60–150.

### Task 3: `recipes.md`, `kitchen.md`, `finance.md`

**Files:**
- Create: `docs/spec/recipes.md`, `docs/spec/kitchen.md`, `docs/spec/finance.md`

- [ ] **Step 1:** `recipes.md` from §6 recipes, §9.1, §9.2, the recipe and
  ingredient part of §9.9, decisions.
- [ ] **Step 2:** `kitchen.md` from §6 kitchen (Utensil, CampUtensil only), the
  stock part of §9.15, D16 as it stands. `## Planned`: kitchen mode, link to
  `../superpowers/specs/2026-11-16-kitchen-mode-design.md` and its plan, and the
  note that the design reverses D16 once built. Old §9.19 text is replaced by that
  link (tick it in the mapping as "superseded by the design").
- [ ] **Step 3:** `finance.md` from §6 bills, §9.17, §9.18, decisions. `## Planned`:
  cost splitting and deposits (waarborg/leeggoed), "no design yet, see roadmap".
- [ ] **Step 4: Review (Claude)** as in Task 2 Step 3.

### Task 4: `accounts.md` and `operations.md`

**Files:**
- Create: `docs/spec/accounts.md`, `docs/spec/operations.md`

- [ ] **Step 1:** `accounts.md` from §6 accounts + pages, the login/camp part of
  §9.9 (rules every area follows stay in `SPEC.md`; this file has the details),
  §9.10, §9.14, §9.16, decisions.
- [ ] **Step 2:** `operations.md` from §11, the security part of §10, the commands
  list, backups, settings (pointer to `.env.example`), decisions (SQLite/WAL stays
  in `SPEC.md` as cross-cutting; link to it).
- [ ] **Step 3: Review (Claude)** as in Task 2 Step 3.

### Task 5: New `SPEC.md`

**Files:**
- Modify: `docs/SPEC.md` (rewritten)

Claude writes this one (it sets the frame for every brief).

- [ ] **Step 1:** Sections: `# Keepee assistant`, what it's for and who uses it,
  glossary, the three stages (before: menu, shopping lists, budget; during:
  kitchen mode, extra trips, bills, evaluation; after: bill review, financial
  report, menu evaluation, each with its area file), tech stack, core concepts,
  rules for every area (access basics, languages and time zone, logging, errors,
  testing and style, performance), UI (one paragraph pointing at
  `ui-guidelines.md` and `DESIGN.md`), cross-cutting decisions with D-numbers,
  index of area files and other docs, "How changes are made" (one line pointing at
  CLAUDE.md and `docs/superpowers/`).
- [ ] **Step 2: Verify nothing lost:** every mapping box is ticked or listed under
  "Removed on purpose"; `git show HEAD:docs/SPEC.md | grep -c "Acceptance"` equals
  the count of `## Acceptance` sections with content plus acceptance lines in
  `SPEC.md`; spot-check five random lines of the old SPEC with `grep -rn` in
  `docs/spec/` and `docs/SPEC.md`.
- [ ] **Step 3:** `wc -l docs/SPEC.md` ≤ 150.

### Task 6: `TODO.md` as roadmap

**Files:**
- Modify: `docs/TODO.md` (rewritten)

- [ ] **Step 1:** Format per step:
  `### N. <name> — <status>` (to brainstorm / designed / planned / building /
  done), one or two lines, then `Design:` / `Plan:` links when they exist, then
  any manual checklist. Steps, in order:
  1. Data cleanup (checklist kept as is)
  2. First deploy on the LAN (checklist kept)
  3. UI on Bootstrap and HTMX (to brainstorm; its current lines kept as notes, plus
     "clean up DESIGN.md §8 after the phone-width check")
  4. Going public (to brainstorm; the "before going public" items move here; needed
     before the first camp that uses kitchen mode)
  5. Kitchen mode (planned; design + plan links)
  6. Deposits: waarborg/leeggoed (to brainstorm)
  7. Splitting personal costs (to brainstorm)
  Then `## Needs you or something outside this project` (kept, minus the
  going-public item), and §14 Future items under `## Later`.
- [ ] **Step 2:** Remove "Done on `dev`".
- [ ] **Step 3: Verify:** every unchecked item of the old TODO is in the new one
  (`git show HEAD:docs/TODO.md | grep -c "\- \[ \]"` vs the new count, differences
  explained).

### Task 7: `CLAUDE.md`, agent files, README, ui-guidelines pointer

**Files:**
- Modify: `.claude/CLAUDE.md`, `.opencode/agents/builder.md`, `reviewer.md`,
  `docs.md`, `.claude/agents/ui-builder.md`, `ui-reviewer.md`, `README.md`,
  `docs/ui-guidelines.md` (line 13 only)
- Delete: `.opencode/agents/planner.md`

Claude does this task (permissions and instructions).

- [ ] **Step 1: `CLAUDE.md`:** first paragraph → "What the app does: `docs/SPEC.md`
  and the area files in `docs/spec/`. The work: `docs/TODO.md` (roadmap). Changes go
  through a design and a plan in `docs/superpowers/`." Add a `## Way of working`
  section with the five steps from the design (brainstorm → design → plan → build
  with opencode `builder` → review → finish), the review threshold verbatim from the
  design, and "fold the design into its area file" in finish. Agents table: remove
  `planner`; `docs` row: "Brings the area files, roadmap, README and help pages in
  line; folds a finished design in". "What goes where": planning is Claude's;
  small-task reviews are opencode `reviewer`; larger ones Claude. Brief section:
  "paste the plan task and name the area file".
- [ ] **Step 2: opencode agents:** `builder.md` and `reviewer.md` read
  `docs/SPEC.md` (rules for every area) and the area file named in the brief.
  `docs.md`: knows `docs/spec/*.md` with the six headings, the roadmap format, the
  fold-in rule (move content, remove the Planned link, add "Built; folded into
  `docs/spec/<area>.md` on <date>." at the top of the design), and D-numbering.
  Delete `planner.md`; remove any `subagent` permission that names `planner` in the
  other agents.
- [ ] **Step 3: Claude agents:** `ui-builder.md` step 2 and `ui-reviewer.md` →
  "the area file for the screen (`docs/spec/`)".
- [ ] **Step 4:** README docs section lists the new layout. `ui-guidelines.md` line
  13 → "What each screen does is in the area files in `docs/spec/` (kitchen mode:
  `docs/spec/kitchen.md`)."
- [ ] **Step 5: Verify:** `opencode debug agents --standalone < /dev/null` lists no
  planner and no errors; `grep -rn "SPEC.md" .opencode .claude` shows only the new
  wording.

### Task 8: References in the kitchen mode docs and in code

**Files:**
- Modify: `docs/superpowers/specs/2026-11-16-kitchen-mode-design.md`,
  `docs/superpowers/plans/2026-11-16-kitchen-mode.md`, the 50 code files listed by
  the grep below (migrations excluded: they're history)

- [ ] **Step 1: Kitchen docs:** replace each `SPEC §x` with the area file that now
  holds it (`§5`, `§7` → `planning.md`; `§9.9` → `accounts.md`/`recipes.md`;
  `§9.12` → `shopping.md`; `§10` → `SPEC.md`; "decision 16" → "D16 in
  `kitchen.md`"). Plan task 12 becomes: update `kitchen.md` (fold the design in,
  D16 rewritten), `recipes.md` (copies), `shopping.md` (pantry count), roadmap, help
  pages, translations.
- [ ] **Step 2: Code:** list with
  `grep -rln "SPEC" --include=*.py --include=*.html . | grep -v "\.venv\|migrations"`.
  Replace `SPEC §…` inside comments/docstrings with the area file by app folder:
  `bills/` → `docs/spec/finance.md`; `recipes/` → `recipes.md`; `planning/` →
  `planning.md`; `shopping/` → `shopping.md`; `kitchen/` → `kitchen.md`;
  `accounts/`, `pages/`, `camps/access.py` → `accounts.md`; other `camps/` →
  `planning.md`; `core/portions.py`, `core/constants.py` → `planning.md`;
  `core/pdf.py`, `config/` → `operations.md`; `tests/test_<x>.py` → the file of the
  app it tests; `static/vendor/README.md` → `SPEC.md`. Where a comment cites
  several sections of different areas, name each file.
- [ ] **Step 3: Verify:** `grep -rn "SPEC §" --include=*.py --include=*.html . |
  grep -v "\.venv\|migrations"` → no output; `git diff --stat` shows only comment
  lines changed (`git diff -U0 | grep "^[-+]" | grep -v "SPEC\|docs/spec\|^+++\|^---"`
  → nothing); ruff, black --check, pytest -q pass.

### Task 9: Read-through and final checks

- [ ] **Step 1: Pointer grep:** `grep -rn "SPEC §\|§9\.\|§13\|decision 16" docs .claude
  .opencode README.md --include=*.md | grep -v "docs/superpowers/plans/2026-11-16-docs"`
  → nothing outside dated records that intentionally quote history.
- [ ] **Step 2: Duplicates:** for access, utilities, pantry and copies, confirm one
  area file owns the rule and others link.
- [ ] **Step 3: Builder's-eye check:** for three sample tasks (kitchen plan task 4,
  roadmap step 1's ingredient tags, a bills fix), open only `SPEC.md` + the one area
  file and confirm they answer the task's questions. Fix gaps.
- [ ] **Step 4:** All CLAUDE.md checks (ruff, black --check, pytest -q,
  `makemigrations --check --dry-run` with `DJANGO_DEBUG=1`).
- [ ] **Step 5:** opencode `secret_reviewer` on the changes; then commit if the user
  asks, staging by name, listing removed-on-purpose items in the message.
