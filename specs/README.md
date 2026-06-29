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
3. `/build specs/NNNN-....md` implements it on a branch and opens a PR.
4. You review the PR. The spec stays in the repo as a record of intent.
