---
name: multiconn-upstream-patches
description: Review MultiConn schema patches against Tapir source and publish justified API schema refinements to the user's fork after a release update. Supports review-only and local preparation; client model regeneration belongs to multiconn-codegen.
---

# Refine Tapir API schemas upstream

Use the current downstream inventory to find useful source-schema improvements. Tapir's public changes are schema refinements, not downstream patches. A successful review can find no new work when fixes are already merged or awaiting release.

## Choose the endpoint

- `review`: investigate and recommend; do not modify Tapir source or publish/sync remote branches.
- `prepare`: implement and validate locally when the user explicitly wants preparation only.
- `publish`: sync the fork, implement, validate, commit and push reviewable fork branches, then stop for user review. This is the default for requests such as “bring the temporary patches upstream” or “prepare PRs.” After approval, open the reviewed PRs using the prepared descriptions.

Infer scope from the request and existing authorization. Preserve an explicit local-only or review-only instruction. Do not regenerate models, change the release pin, remove patches merely because source changes merged, or start this workflow automatically after codegen. Explain any incorrect client patch separately and change it only within scope.

## Establish inputs and source state

Read the relevant final release report in `code_generation/documentation/reports/codegen/` and any prior upstream run report in `code_generation/documentation/reports/upstream-patches/`, the active `schema-patch-tracking.md`, and relevant calls/helpers in `code_generation/shared/schema_patching.py`. Use `tapir_unpatched_schema.json` and `tapir_master_schema.json` for released comparisons; confirm the client release and local patch revision. They are not upstream-main snapshots. Historical reports are supporting evidence, not mandatory reading when current source answers the question. Use the [pipeline brief](../../../code_generation/documentation/archicad_api_codegen_brief.md) only when generation-layer context is needed.

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

### Keep batches reviewable

Aim for 30–50 related definitions per PR, grouped by command family or concept. Use the full structural check to support larger equivalent-refinement batches; do not impose a small command count or line limit on mechanical extractions. These are soft targets: keep small complete fixes together and include every consumer needed for a sharing decision. Split for distinct concepts, dependencies, or acceptance changes rather than solely to meet a count.

Before implementing a large inventory, propose a compact batch plan. For an inventory of roughly 300–400 definitions, aim for about 5–10 coherent PRs after excluding already-covered work. Review names, intended sharing, and descriptions manually; the guard verifies contract preservation, not naming quality or conceptual equivalence.

Base independent batches on upstream main and use one focused commit per batch where practical. State dependencies when a batch genuinely requires another; do not silently stack independent PRs. Keep acceptance changes separate from equivalent extractions.

## Branches, commits and publication

Use version-based names without a `codex/` prefix:

```text
PR title: Refine API schemas following Tapir <reviewed-version>
Branch:   schema/refinements-<reviewed-version>
Example:  schema/refinements-1.7.1
```

The version identifies the reviewed release, not a promise about the release containing the changes. Add a short suffix only when separate proposals genuinely need it. Reuse an existing proposal's branch and keep an open PR's head intact; do not rename it just to adopt this convention.

Describe upstream changes in commit subjects rather than downstream patch debt. Use an explanatory body when provenance or a compatibility decision matters. Follow requested commit/amend history. After validation, commit only intended Tapir source changes, push to the user's fork and verify its remote tip. Rebase an existing branch when requested or needed for integration; force-push only with authorization and an explicit lease on the recorded remote tip. The first stopping point is published fork branches with contents and prepared PR text ready for user review.

### Human review before PR submission

Finish implementation, validation, the run report and its staging before opening any upstream PR, including a draft. For multiple batches, present one review table with each branch/diff, title, affected commands and definition names, validation result, and any dependencies or compatibility decisions. Prepare each full PR body in a scratch file and link it for review; do not require the user to copy descriptions between chats and GitHub.

Stop for review. Approval such as “go ahead” in response to that concrete proposal authorizes opening the reviewed PRs, without a second confirmation. Respect approval of only selected batches. Use the prepared titles and bodies, check for existing PRs before creating them, and return their links. If scope materially changes after approval, present the affected batch again. If the user chooses manual submission, provide copyable Markdown instead. Do not merge PRs or post command comments unless separately requested.

### Schema-refinement PR format

Use a short aim, the exact names and consumers changed, and validation evidence. Add `<!-- tapir-schema-refinement -->` to equivalent refinement PR bodies. Do not use that marker for intentional acceptance changes; submit those separately with their justification.

Inspect the workflow on upstream's default branch before describing its behavior as available. Where supported, the PR author can post `/check-schema`; `/merge-schema` requires repository write access. The marker does not itself make a check required or authorize merging. Keep any remaining merge race explicit; do not claim that the API atomically pins main.

## Validate proportionately

Interpret sources using Tapir's current documentation tooling in memory or isolated temporary output. Cache the baseline for the run. Check reference resolution, name collisions, command access to common definitions and the complete structural difference against that baseline. Do not hand-edit or commit generated docs.

Before pushing a committed schema proposal, run the [schema merge check](scripts/check_schema_merge.py) against the fetched upstream base and proposal head. It generates schemas from the base and the synthetic merge in isolation. This catches schema regressions that Git can merge cleanly. Repeat it when the base or the proposal's schemas change, including after conflict resolution. See [merge check usage](references/schema-review.md#merge-check) for the command and how to review intentional changes.

Equivalent changes preserve fields, types, requiredness, additional properties, bounds, enum order and union branches; review annotations separately. For a correction/tightening, allow only the justified acceptance change and explain it. Input validation can change behavior before unchanged execution code runs.

Do not use indiscriminate expansion as proof: preserve reference siblings, recursive definitions and union semantics. Check the actual renderer when descriptions move. Run focused annotation/renderer checks after prose-only edits; repeat the full contract comparison when source contracts or the rebase baseline change. Distinguish source checks, SDK builds and live Archicad tests, and put their evidence/limitations in the run report.

## Deliver one run record and maintain the active queue

Return the branch/commit or existing PR link and the main validation result. For batch review, use the review table and linked prepared bodies above; after approved submission, return PR links. Provide fenced Markdown titles/descriptions when the user wants manual submission. Explain the resulting upstream schema and material compatibility consequences; keep routine test logs and investigation history out of the PR body. Do not force the title to list every affected domain.

Maintain **at most one durable upstream report per logical run**, including follow-up reviews, description edits, rebases and publication on later dates. Store it at `code_generation/documentation/reports/upstream-patches/upstream-refinements-<version>-<start-date>.md` and update it in place. Read generation reports from the sibling `reports/codegen/` folder; keep relative links valid across these folders. Keep only useful decisions/rejected alternatives, source baseline/final head/PR, compatibility evidence and validation limits. When both a reference and its definition retain descriptions, list their locations and full strings. Link to active tracking instead of repeating its path inventory. Keep scratch scripts, intermediate logs and snapshots untracked; no additional report per phase, day or question. A no-new-work review may only need a tracking update.

`code_generation/documentation/schema-patch-tracking.md` is the **active queue**: unresolved candidates, published branches/submitted PRs and merged fixes awaiting released documentation. Group by decision and record original paths, source/PR status, removal conditions and alias needs. Do not copy all Permanent patches into it or keep retired-patch inventories/tombstones. Once release adoption confirms retirement, remove the entry; the generation report and Git history preserve what changed. Do not duplicate executable patch implementations or generated schemas.

Automatically stage the completed run report in the **MultiConn checkout** with `git add -- code_generation/documentation/reports/upstream-patches/upstream-refinements-<version>-<start-date>.md`, using the exact current report path. Restage that same report after final revisions or later follow-ups in the logical run. Stage only this report; do not additionally stage tracking or unrelated files. Preserve existing staged changes and do not commit MultiConn changes unless requested. A review-only run remains read-only; a tracking-only no-new-work outcome has no report to stage.

Retirement belongs to a later `$multiconn-codegen update tapir to <released-version>` run: confirm the correction in fetched release documentation, resolve renamed paths/dependencies, remove redundant calls, retain necessary aliases in `code_generation/shared/model_aliases.py`, then complete both representations, unified generation and tests. A source merge or release tag alone is insufficient. Preserve loud stale-patch guards. Do not create a watcher or scheduled task.
