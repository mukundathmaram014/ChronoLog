# Specs

Each file here is a small, self-contained implementation spec for one todo or bug fix.

Naming: `NNNN-short-slug.md` (e.g. `0001-fix-stopwatch-reset.md`), zero-padded, incrementing.

Lifecycle:
0. (Optional) `/triage` reads your Obsidian "Chronolog Documentation" doc, pulls every unchecked
   idea, and writes `specs/triage.md` — a single accept/reject list of candidate specs (large
   large/heavy items flagged with their value-vs-cost trade-off). You triage; accepted items feed
   into step 1. `triage.md` is a scratch worklist, not a permanent spec.
1. You give Claude a rough todo/bug (or an accepted triage candidate) → `/spec` generates a file here.
2. You review/edit the spec (this is the cheap, high-leverage review point).
3. `/build specs/NNNN-....md` implements one spec on a branch and opens a PR. For several specs at
   once, `/build-batch <specs...>` orchestrates them: it reads each spec's "Affected files", builds a
   dependency map, and drives them to PRs in waves — independent specs in parallel (isolated git
   worktrees), coupled specs sequenced. It pauses after each wave for you to merge before building the
   next wave off updated `main`; it never auto-merges or touches `main` directly.
4. You review the PR(s). The spec stays in the repo as a record of intent.
