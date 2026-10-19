---
name: multiconn-upstream-patches
description: Review MultiConn schema patches against Tapir source and publish justified API schema refinements to the user's fork after a release update. Supports review-only and local preparation; client model regeneration belongs to multiconn-codegen.
---

# Refine Tapir API schemas upstream

Use the current downstream inventory to find useful source-schema improvements. Tapir's public changes are schema refinements, not downstream patches. A successful review can find no new work when fixes are already merged or awaiting release.

## Choose the endpoint

- `review`: investigate and recommend; do not modify Tapir source or publish/sync remote branches.
- `prepare`: implement and validate locally when the user explicitly wants preparation only.
- `publish`: sync the fork, implement, validate, commit and push a reviewable fork branch. This is the default for actionable requests such as “bring the temporary patches upstream.” Deliver the PR title/body for the user to submit; create or edit a PR only when requested.

Infer scope from the request and existing authorization. Preserve an explicit local-only or review-only instruction. Do not regenerate models, change the release pin, remove patches merely because source changes merged, or start this workflow automatically after codegen. Explain any incorrect client patch separately and change it only within scope.

## Establish inputs and source state

Read the relevant final release report in `code_generation/documentation/reports/`, the active `schema-patch-tracking.md`, and relevant calls/helpers in `code_generation/shared/schema_patching.py`. Use `tapir_unpatched_schema.json` and `tapir_master_schema.json` for released comparisons; confirm the client release and local patch revision. They are not upstream-main snapshots. Historical reports are supporting evidence, not mandatory reading when current source answers the question. Use the [pipeline brief](../../../code_generation/documentation/archicad_api_codegen_brief.md) only when generation-layer context is needed.

Locate the Tapir checkout from remotes and user context. Read its repository instructions and working-tree state. Discover the upstream repository, the user's fork and default branches rather than assuming `origin` is upstream. Record the client release, exact source baseline and final branch tip; avoid routine per-file hashes and exhaustive snapshots in durable reports.

For `publish`, start by fast-forward syncing the fork's matching default branch, for example `gh repo sync <fork-owner/repo> --source <upstream-owner/repo> --branch <default-branch>`, then fetch and verify the chosen base. Syncing needs no manual GitHub UI step. Never add `--force` to reset the fork's default branch. If it has diverged, preserve its commits, report that sync was skipped and base the proposal on fetched upstream instead. Preserve unrelated local work.

Inspect existing PRs and active tracking before starting duplicate work. Review temporary and unresolved source-review candidates, including older items without a disposition; distinguish unmerged, merged-awaiting-release and released fixes. Skip already merged proposals. Permanent generator workarounds and intentional client contract choices remain out of scope unless selected. Valid inline schemas need not be extracted just because a generator names them poorly; require independent schema-design value or an explicitly selected extraction policy.

Trace dependencies back through local extractions to the original command/property before searching source. Count expanded helper operations separately from declarations; counts do not determine branch or PR boundaries.

## Decide and implement

For each decision identify the original path and consumers, local transformation, source implementation and retirement condition. Compare released input, patched input and current source. Record already-fixed outcomes instead of extracting again. For contract changes, inspect execution plus the exact SDK getter/setter, using primary Graphisoft documentation and available version-specific headers. Separate documented support, fallback handling and live observations. An uncertain acceptance change is not a non-breaking extraction.

Read [schema-review.md](references/schema-review.md) for sharing, descriptions and compatibility evidence.

- Edit schema strings in `archicad-addon/Sources/*.cpp` and `archicad-addon/Sources/RFIX/Images/CommonSchemaDefinitions.json`. Leave generated documentation to maintainers unless requested.
- Share the same concept and contract, preserving creation/modification/read differences. Search related consumers for meaningful further reuse. Ensure commands introducing common references use `CommonSchema::Used`.
- Put general meaning on the shared definition or its actual field. Keep only distinct caller defaults, restrictions, effects or readback notes at referencing properties. Do not move a nested field's entire explanation onto every enclosing reference just to preserve its wording.
- Group coherent equivalent changes; isolate acceptance changes. Use a few meaningful commits and independent branches where appropriate, making definition dependencies explicit.

## Branches, commits and publication

Use version-based names without a `codex/` prefix:

```text
PR title: Refine API schemas following Tapir <reviewed-version>
Branch:   schema/refinements-<reviewed-version>
Example:  schema/refinements-1.7.1
```

The version identifies the reviewed release, not a promise about the release containing the changes. Add a short suffix only when separate proposals genuinely need it. Reuse an existing proposal's branch and keep an open PR's head intact; do not rename it just to adopt this convention.

Describe upstream changes in commit subjects rather than downstream patch debt. Use an explanatory body when provenance or a compatibility decision matters. Follow requested commit/amend history. After validation, commit only intended Tapir source changes, push to the user's fork and verify its remote tip. Rebase an existing branch when requested or needed for integration; force-push only with authorization and an explicit lease on the recorded remote tip. The endpoint is a published fork branch, not a merged upstream PR.

## Validate proportionately

Interpret sources using Tapir's current documentation tooling in memory or isolated temporary output. Cache the baseline for the run. Check reference resolution, name collisions, command access to common definitions and the complete structural difference against that baseline. Do not hand-edit or commit generated docs.

Equivalent changes preserve fields, types, requiredness, additional properties, bounds, enum order and union branches; review annotations separately. For a correction/tightening, allow only the justified acceptance change and explain it. Input validation can change behavior before unchanged execution code runs.

Do not use indiscriminate expansion as proof: preserve reference siblings, recursive definitions and union semantics. Check the actual renderer when descriptions move. Run focused annotation/renderer checks after prose-only edits; repeat the full contract comparison when source contracts or the rebase baseline change. Distinguish source checks, SDK builds and live Archicad tests, and put their evidence/limitations in the run report.

## Deliver one run record and maintain the active queue

Return the branch/commit or existing PR link and the main validation result. Provide the PR title and description inside a fenced `markdown` block so the user can copy raw Markdown. Use a short descriptive opening, a compact `Area | Changes` table or bullets, then material compatibility consequences. Explain the resulting upstream schema; keep routine test logs and investigation history out of the PR body. Do not force the title to list every affected domain.

Maintain **at most one durable upstream report per logical run**, including follow-up reviews, description edits, rebases and publication on later dates. Use a name such as `reports/upstream-refinements-<version>-<start-date>.md` and update it in place. Keep only useful decisions/rejected alternatives, source baseline/final head/PR, compatibility evidence and validation limits. When both a reference and its definition retain descriptions, list their locations and full strings. Link to active tracking instead of repeating its path inventory. Keep scratch scripts, intermediate logs and snapshots untracked; no additional report per phase, day or question. A no-new-work review may only need a tracking update.

`code_generation/documentation/schema-patch-tracking.md` is the **active queue**: unresolved candidates, published branches/submitted PRs and merged fixes awaiting released documentation. Group by decision and record original paths, source/PR status, removal conditions and alias needs. Do not copy all Permanent patches into it or keep retired-patch inventories/tombstones. Once release adoption confirms retirement, remove the entry; the generation report and Git history preserve what changed. Do not duplicate executable patch implementations or generated schemas. Reports/tracking remain unstaged unless the user asks to commit them.

Retirement belongs to a later `$multiconn-codegen update tapir to <released-version>` run: confirm the correction in fetched release documentation, resolve renamed paths/dependencies, remove redundant calls, retain necessary aliases in `code_generation/shared/model_aliases.py`, then complete both representations, unified generation and tests. A source merge or release tag alone is insufficient. Preserve loud stale-patch guards. Do not create a watcher or scheduled task.
