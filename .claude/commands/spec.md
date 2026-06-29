---
description: Turn a rough todo or bug report into a structured implementation spec
argument-hint: <todo or bug description>
model: opus
---

You are turning a rough todo/bug note from the author into a precise, reviewable
implementation spec for the ChronoLog codebase. Read `CLAUDE.md` first for conventions.

The raw request: $ARGUMENTS

Steps:
1. Investigate the codebase enough to ground the spec in real files, functions, and routes.
   Read the relevant backend route(s)/model(s) and/or frontend page(s)/component(s). Do NOT
   write any implementation code in this step.
2. If something essential is genuinely ambiguous (and you can't resolve it from the code or a
   sensible default), ask the author ONE round of clarifying questions before writing the spec.
3. Determine the next spec number by looking at existing files in `specs/`.
4. Write the spec to `specs/NNNN-short-slug.md` using this structure:

   ```
   # NNNN — <Title>

   ## Problem / Goal
   <1–3 sentences: what the author wants and why.>

   ## Scope
   - In scope: <bullets>
   - Out of scope / non-goals: <bullets. If the change needs a large refactor, don't silently
     exclude it — note it here or in Approach and justify why it's worth it (or why it's deferred)>

   ## Affected files
   <bulleted list of specific files, with a phrase on what changes in each>

   ## Approach
   <Concrete, ordered steps. Reference real functions/routes/components. Prefer the smallest change
   that satisfies the goal, but include a larger refactor if it genuinely earns its keep — just say
   so and justify it here; no refactors for their own sake. Note conventions to follow
   (success_response/failure_response, user_id scoping, ensure_utc, useFetch, etc.).>

   ## Acceptance criteria
   <Checkable bullets describing observable correct behavior.>

   ## Testing / verification
   <How to confirm it works: which page/route, what to click or curl, expected result.>

   ## Risks & notes
   <Edge cases, data/migration concerns, anything the author should weigh in on.>
   ```

5. After writing, print a 3–5 line summary and the spec path, and tell the author to review/edit
   it, then run `/build specs/NNNN-short-slug.md` when satisfied.

Keep the spec tight and honest. Flag, don't hide, anything that smells like it needs a big change.
