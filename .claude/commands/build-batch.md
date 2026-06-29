---
description: Orchestrate building multiple specs — dependency-ordered, parallel where independent, one wave at a time
argument-hint: "[spec paths/range, e.g. specs/0003 specs/0004 ... — or 'all' for every unbuilt spec]"
model: opus
---

You are orchestrating the implementation of MULTIPLE approved specs for ChronoLog. This is the batch
counterpart to `/build`: instead of one spec → one PR, you plan and drive several specs to PRs in the
right order — building independent ones in parallel and sequencing the ones that touch the same code.
Read `CLAUDE.md` first for conventions and the working agreement.

Specs to build: $ARGUMENTS
If `all` (or empty), target every spec in `specs/` that doesn't already have a corresponding branch/PR
(ignore `specs/README.md` and `specs/triage.md`).

## Operating rules (chosen by the author — do not change without asking)
- **Pause between waves.** Build one wave's PRs, then STOP and report. The author merges that wave;
  only then do you build the next wave, off the freshly-updated `main`. Never auto-merge. Never commit
  to `main` directly.
- **Parallel via worktrees.** Independent specs in the same wave are built simultaneously, each by its
  own build agent in an isolated git worktree (`Agent` tool with `isolation: "worktree"`), on its own
  branch, each opening its own PR.
- One spec = one branch = one PR, EXCEPT specs you deliberately group (see below) which share one
  branch/PR.

## Step 1 — Read and analyze (no code changes yet)
1. Read every target spec in full, especially each "Affected files" and any "Risks & notes" that call
   out dependencies on another spec.
2. Build a dependency/overlap map: two specs are **coupled** if they modify the same file(s) or one
   spec's "Risks & notes" says it depends on / pairs with another.
3. Decide, for each coupled pair, whether to:
   - **Group** into one branch/PR (when they're really one change to the same area — e.g. specs that
     explicitly say "best done together"), or
   - **Sequence** across waves (when one logically builds on the other's merged code — the later one
     goes in a later wave).
4. Partition into **waves**: wave 1 = specs with no unbuilt dependencies; each later wave = specs whose
   dependencies are all merged by then. Within a wave, all items are mutually independent (no shared
   files) so they can run in parallel safely.

## Step 2 — Present the orchestration plan and WAIT for approval
Enter plan mode and present:
- The wave breakdown: which specs run in which wave, which are grouped, which are parallel.
- For each spec/group: the branch name (`feat/NNNN-slug` or `fix/NNNN-slug`) and one line on the change.
- Any specs flagged investigation-first (their spec says "reproduce/confirm before fixing") or that
  carry an unresolved author decision — note these so the author can weigh in now.
WAIT for the author to approve the plan. This single approval stands in for the per-spec plan-mode
approval that `/build` normally does — the parallel build agents will NOT each stop for approval.

## Step 3 — Build the current wave (parallel, isolated)
For each spec/group in the wave, spawn a build agent with `isolation: "worktree"`. Give each agent:
- The spec path(s) and the instruction to follow the `/build` workflow and `CLAUDE.md` conventions
  (blueprints + success_response/failure_response, user_id-scoped queries, ensure_utc, useFetch, the
  smallest change that satisfies the spec; refactor only if the spec calls for it).
- Explicit overrides for batch mode: **do NOT enter plan mode / do NOT wait for approval** (already
  approved); branch off current `main`; implement; verify to the degree practical; commit; push; open a
  PR with `gh` targeting `main`; return the PR URL. End PR bodies with the Claude Code footer.
- If the spec is investigation-first and the investigation shows its premise is wrong, or the spec hits
  an unresolved decision, the agent must STOP and report back instead of guessing — surface that.
Run the wave's agents concurrently. Wait for all to finish; collect PR URLs and any "stopped/needs
input" reports.

## Step 4 — Report and pause
Print: the wave's PRs (URL + spec + one-line summary), anything an agent flagged or couldn't complete,
and the remaining waves. Then STOP with a clear instruction: "Merge these PRs, then tell me to continue
and I'll build wave N+1 off the updated main." Do not proceed until told.

## Step 5 — Resume next wave
When the author says to continue: `git fetch` + confirm the prior wave is merged into `main`, re-read
the next wave's specs (line numbers may have shifted post-merge — re-ground against current code),
recompute if anything changed, and repeat Steps 3–4 for the next wave until all specs are done.

## Notes
- `gh` may not be installed locally; if PR creation fails, have the agent push the branch and report the
  branch name + a compare URL so the author can open the PR, rather than failing silently.
- Keep each diff scoped and reviewable. If a wave's agent discovers the work is much larger than its
  spec, it stops and reports — don't let batch mode paper over a spec that needs revising.
- This command does not deploy. Deploys remain manual via `/deploy-backend`.
