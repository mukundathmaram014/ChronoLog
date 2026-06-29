# Specs

Each file here is a small, self-contained implementation spec for one todo or bug fix.

Naming: `NNNN-short-slug.md` (e.g. `0001-fix-stopwatch-reset.md`), zero-padded, incrementing.

Lifecycle:
1. You give Claude a rough todo/bug → `/spec` generates a file here.
2. You review/edit the spec (this is the cheap, high-leverage review point).
3. `/build specs/NNNN-....md` implements it on a branch and opens a PR.
4. You review the PR. The spec stays in the repo as a record of intent.
