---
description: Implement a spec file end-to-end on a branch and open a PR
argument-hint: <path to spec file, e.g. specs/0001-fix-xyz.md>
model: sonnet
---

You are implementing an approved spec for the ChronoLog codebase. Read `CLAUDE.md` for
conventions before starting.

Spec to implement: $ARGUMENTS

Workflow:
1. Read the spec file in full. Read every file it lists under "Affected files" plus anything
   else needed to implement correctly.
2. Enter plan mode and present a concrete implementation plan based on the spec. WAIT for the
   author to approve before writing any code. If the spec is missing or unclear, say so instead
   of guessing.
3. Once approved:
   a. Create a branch off `main` named `feat/NNNN-slug` or `fix/NNNN-slug` matching the spec.
   b. Implement the SMALLEST change that satisfies the spec. Follow existing conventions exactly
      (blueprints + success_response/failure_response, user_id-scoped queries, ensure_utc for
      datetimes, useFetch for frontend calls). Do NOT refactor beyond what the spec requires —
      if you discover the spec needs a large change, stop and report back.
   c. Verify to the degree practical: for backend, sanity-check the route logic / run the app if
      feasible; for frontend, ensure it builds. Report what you verified and what you didn't.
4. Commit with a clear message referencing the spec. Push the branch.
5. Open a PR with `gh pr create`, targeting `main`. The PR body should:
   - Link/summarize the spec.
   - List the changes made and any deviations from the spec (with reasons).
   - State what was verified and how the author can test it.
   End the PR body with:
   🤖 Generated with [Claude Code](https://claude.com/claude-code)
6. Print the PR URL for the author to review.

Stay scoped to this one spec. One spec = one branch = one PR.
