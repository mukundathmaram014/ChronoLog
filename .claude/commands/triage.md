---
description: Pull unchecked ideas from the Obsidian doc into a reviewable list of candidate specs
argument-hint: "[optional path to the Obsidian doc — defaults to the ChronoLog Documentation file]"
model: opus
---

You are doing a FIRST PASS over the author's Obsidian "brain" notes for ChronoLog: read every
unimplemented idea, and compile them into a single triage list of candidate specs the author can
quickly accept or reject. This sits BEFORE `/spec` in the workflow — accepted candidates later
become real specs via `/spec`, which then get built via `/build`. Read `CLAUDE.md` first for
conventions and the project's working agreement (large refactors are fine when they deliver
substantial value — judge by value, not size).

Source file: $ARGUMENTS
If no argument is given, use the default:
`C:\Obsidian\Brain\Projects\Chronolog\Chronolog Documentation.md`

IMPORTANT: This file is the author's personal notes. **It is READ-ONLY — never edit, reformat, or
write to it.** You only read from it.

Steps:

1. Read the source file in full. The author's convention: `- [x]` = already implemented, `- [ ]` =
   NOT yet implemented. Collect:
   - Every unchecked `- [ ]` item (these are the primary candidates).
   - Any non-checkbox design notes / idea sections that describe something clearly not built yet
     (e.g. a "Protocol" or design section). Treat each as one candidate.
   Ignore everything that is `- [x]` (already done).

2. Read `specs/README.md` and list the existing files in `specs/` (including any prior
   `specs/triage.md`) so you can DEDUPE: if an idea already has a spec or is clearly already
   shipped, don't list it as a fresh candidate — note it under "Already specced / done" instead.

3. Do a LIGHT pass over the codebase only as needed to classify each candidate — enough to guess
   the area and refactor size at a glance. Do NOT deeply investigate every item and do NOT write any
   spec bodies or implementation code here; that grounding happens later in `/spec`. Glance at
   `backend/src/routes/` and `frontend/src/` structure if it helps you size things.

4. For each candidate, decide:
   - **Title** — a short imperative name.
   - **Summary** — 1 line in your own words (paraphrase the note; keep the author's intent).
   - **Area** — backend / frontend / both / infra / non-code.
   - **Size** — small / medium / large. Mark anything that would need broad restructuring as
     **LARGE** and note the value/cost trade-off — large is NOT an automatic reject; flag it so the
     author can weigh whether the payoff justifies the work.
   - **Reject hint** — a short note on why this might not be worth it (cost outweighs value,
     low value, duplicate, depends on X, not really a ChronoLog code task, etc.). Size alone isn't a
     reason — a big change that delivers something substantial is fair game.
   Group obviously-related items together (e.g. several lines about the same feature) into one
   candidate, noting the sub-points.

5. Separate out items that are NOT ChronoLog application code tasks — e.g. personal learning/setup
   TODOs, or work for a different/standalone app (like a separate assignment-tracker / todo-list
   product) that would be its own project. Put these under "Out of scope for ChronoLog specs" so
   they don't clutter the actionable list, but don't silently drop them.

6. Write the triage list to `specs/triage.md` (overwrite if it exists), using this structure:

   ```
   # Spec triage — from Obsidian (<today's date>)

   Source: <path to the Obsidian doc>
   <N> unchecked ideas reviewed. Check the box on the ones you want; then run
   `/spec <the idea>` on each accepted item to produce a real, grounded spec.

   ## Candidates
   - [ ] **<Title>** — <one-line summary>
         size: <small|medium|large> · area: <area> · reject hint: <short note>
   - [ ] **<Title>** — <one-line summary>
         size: <…> · area: <…> · reject hint: <…>

   ## Heavy / advanced — weigh value vs. cost
   - [ ] **<Title>** — <summary> ⚠️ LARGE — <the value it delivers vs. what it costs>

   ## Out of scope for ChronoLog specs (not app code)
   - <Title> — <why: learning task / separate app / etc.>

   ## Already specced or shipped (skipped)
   - <Title> — <points to specs/NNNN-… or "already in app">
   ```

7. After writing, print to the author:
   - A 5–10 line summary: how many candidates, how many flagged as large (with a word on whether
     the payoff looks worth it), anything notable or ambiguous.
   - The path `specs/triage.md`.
   - A reminder: review the list, keep the candidates worth doing, then run `/spec <idea>` on each
     accepted one to flesh it into a real spec (`/build` after that).

Keep it honest and skimmable — the whole point is a fast accept/reject pass, so flag the heavy or
dubious ideas clearly rather than making everything look equally actionable.
