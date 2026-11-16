# Docs restructure and way of working: design

Date: 2026-11-16.

## Intent

The docs have grown too big to take in: `docs/SPEC.md` is about 600 lines, and
TODO, ui-guidelines and DESIGN add about 600 more. The local models (opencode,
Qwen3 30B, 32k context) can't hold them next to the code a task needs, and the
user can't see what one area does without reading everything. The project moves to
a structured way of working: small docs per area that say what the app does now,
dated designs for changes, and plans that split a design into tasks for the local
builder.

## Goals

- Every doc a builder needs for one task fits comfortably in a local model's
  context next to the code: the entry `SPEC.md` (~100 lines) plus one area file
  (~60–150 lines).
- The user can read one area at a time, with its decisions and reasons beside it.
- One place for the truth about the current app (the area files); designs record
  changes and why.
- `CLAUDE.md` and the agent files describe the new flow and who does what.

## Non-goals

- Changing what the app does. This moves and trims text; it doesn't decide features.
  (Code comments that cite SPEC sections are updated; see "Settled after review".)
- Rewriting `ui-guidelines.md` or `DESIGN.md` (see "Settled after review").
- Writing retroactive designs for features that already exist.
- Brainstorming the roadmap steps; that comes after this, one step at a time.

## Anti-goals

- Losing information: every requirement, acceptance check and decision in the
  current SPEC must land somewhere (an area file or `SPEC.md`), or be removed on
  purpose and listed as removed.
- Two sources of truth: once a design is built, its content lives in the area file
  and the design is marked done, not left as a second description.

## Approaches

- **A. Split the spec per area, dated designs for changes.** Picked.
- B. Keep `SPEC.md` whole, only add designs for new work: the big file stays big,
  and the truth is split over the spec and every later design.
- C. Only designs, retroactive ones for every feature, no spec: to know the app
  today you'd read every design in order; the most rewriting.

## Design

### Files

```
docs/
  SPEC.md            entry point, ~100 lines
  spec/
    planning.md
    shopping.md
    recipes.md
    kitchen.md
    finance.md
    accounts.md
    operations.md
  ui-guidelines.md   unchanged
  DESIGN.md          stale parts of §8 removed once the theme is done
  TODO.md            short roadmap
  superpowers/specs/ dated designs (YYYY-MM-DD-<topic>-design.md)
  superpowers/plans/ dated plans
```

### `SPEC.md` (entry point)

- What the app is for, who uses it (current §1, §2), the glossary.
- The three stages: before the camp (menu, shopping lists, budget), during
  (kitchen mode, extra trips, bills, evaluation), after (bills review, financial
  report, menu evaluation).
- Tech stack (§3), core concepts (§4).
- Rules for every area: access basics (login required, Chiro membership, example
  Chiros), languages and time zone, logging, errors, testing and style,
  performance (from §9.9 and §10).
- Decisions that apply everywhere (SQLite, no SPA, vendored assets, …).
- Index: one line per area file and per other doc.

### Area files

Each has the same headings: **Purpose** (one or two lines and which stage),
**Data** (the models of the area, from §6), **Behaviour** (from §9 and the logic
sections), **Acceptance**, **Decisions** (from §13, with dates where known),
**Planned** (links to designs not yet built).

| File | Takes from current SPEC |
|---|---|
| `planning.md` | §5 meal structure, §6 camps + planning, §7 scaling, §9.3 camps, §9.4 planner, §9.7 output, §9.8 runbook, §9.11 diets, §9.13 balance |
| `shopping.md` | §6 shopping, §8 shopping list logic, §9.5 lists, §9.6 budget, §9.12 pantry, §9.15 utilities (the camp's needs on the shopping page) |
| `recipes.md` | §6 recipes, §9.1 recipes, §9.2 ingredients, §9.9 recipe and ingredient access |
| `kitchen.md` | §6 kitchen, §9.15 utilities (the stock), §9.19 kitchen mode; until built: "Planned: see `superpowers/specs/2026-11-16-kitchen-mode-design.md`" |
| `finance.md` | §6 bills, §9.17 bills, §9.18 financial report; Planned: cost splitting, deposits (no design yet: listed as roadmap items) |
| `accounts.md` | §6 accounts + pages, §9.9 camp access, §9.10 public site, §9.14 Chiros/roles/invitations/join requests, §9.16 example camp |
| `operations.md` | §11 deployment, §10 security, settings, commands, backups |

§12 UI becomes a short paragraph in `SPEC.md` pointing at ui-guidelines and DESIGN.
§14 Future items move to the TODO roadmap. Where a section belongs to two areas
(utilities, access), each file keeps its own part and links to the other.

### Folding a design in

When a design's plan is finished: the `docs` agent (or Claude) moves its content
into the area file's Behaviour, Data, Acceptance and Decisions, removes the
Planned link, and adds a line at the top of the design: "Built; folded into
`docs/spec/<area>.md` on <date>." The design stays as the record of why.

### `TODO.md` (roadmap)

- Steps in order, each one or two lines, with links to its design and plan once
  they exist, and its status (to brainstorm / designed / planned / building / done).
- Data cleanup and first deploy keep their checklists (they are manual work, not
  designs).
- The "needs you or something outside the project" list stays.
- The "Done on `dev`" list is removed: git history and the area files say what
  exists.
- New items from the kitchen mode conversation: deposits (waarborg/leeggoed),
  and going public before the first camp that uses kitchen mode.

### Way of working (`CLAUDE.md`)

1. **Brainstorm** a roadmap step with the user, write a dated design, user approves.
2. **Plan** it (Claude, writing-plans): tasks small enough for the local builder,
   each naming its area file.
3. **Build** each task with the opencode `builder`; the brief is the plan task plus
   the area file (and `ui-guidelines.md` / `DESIGN.md` lines for UI work).
4. **Review:**
   - opencode `reviewer` for small tasks (one to three files);
   - Claude for larger ones: more than three files; models, migrations or settings;
     access between Chiros, login, bills or privacy; and always the whole plan
     before a commit;
   - `ui-reviewer` (Claude) for the browser check; `secret_reviewer` before commits.
5. **Finish:** checks, fold the design into its area file, update the roadmap,
   commit when the user asks.

Planning is Claude's; the opencode `planner` agent is retired (file removed, table
row removed).

### Agent files

- `.opencode/agents/builder.md`, `reviewer.md`: read `docs/SPEC.md` and the area
  file named in the brief, not the whole spec. Style and testing rules now live in
  `SPEC.md`.
- `.opencode/agents/docs.md`: knows the area files, the roadmap format, and how to
  fold a design in.
- `.opencode/agents/planner.md`: removed.
- `.claude/agents/ui-builder.md`, `ui-reviewer.md`: "the area file for the screen"
  instead of `docs/SPEC.md`.
- `README.md`: the docs section points at the new layout.

### Order of the work

1. Write `SPEC.md` and the seven area files from the current SPEC. Check nothing was
   lost: every heading and acceptance line of the old SPEC maps to a new place
   (keep the mapping table above as the checklist).
2. Rewrite `TODO.md` as the roadmap.
3. Update `CLAUDE.md`, the agent files and README.
4. Retarget every SPEC reference in the kitchen mode design and plan (task 12 now
   updates `kitchen.md`, `recipes.md`, `shopping.md` and folds the design in), and
   the SPEC references in code comments.
5. Read every new file once as the local model would: does one area file plus
   `SPEC.md` answer a builder's questions for a task in that area?

## Settled after review (Claude's calls)

- **"SPEC §x" references in code** (74 in 54 `.py`/`.html` files, many already
  wrong): replaced with the area file, without section numbers, e.g. `(SPEC §9.17)`
  → `(docs/spec/finance.md)`. Comments and docstrings only, done mechanically by
  Claude, then ruff, black and pytest. No behaviour changes.
- **Order:** this restructure goes first; kitchen mode isn't built yet. Every SPEC
  reference in the kitchen mode design and plan is retargeted (not only task 12):
  the plan's header and tasks point at `SPEC.md` and the area files.
- **Decision numbers:** decisions keep their current global numbers wherever they
  land (`D16` in `kitchen.md`), so older references stay traceable. New decisions
  continue the sequence (D19, …).
- **`ui-guidelines.md`:** only the pointer on line 13 changes (to `SPEC.md` and the
  area files). Nothing else.
- **`DESIGN.md` §8:** not touched now. Its clean-up is a line in roadmap step 4,
  after the theme's phone-width check.
- **`SPEC.md` size:** ~100 lines is a goal, not a limit; up to ~150 is fine. If it
  runs over, tech stack details move to `operations.md` first.
- Removed-on-purpose items are listed in the plan's mapping checklist and the commit
  message. Roadmap steps are renumbered from 1. §10 security goes to
  `operations.md`, the rest of §10 to `SPEC.md`.

## Left to the builder

- Exact wording, and trimming repetition while moving text (meaning unchanged).
- Where a borderline item goes when the table doesn't name it, with a link from the
  other area.
- Which parts of DESIGN.md §8 are stale.
