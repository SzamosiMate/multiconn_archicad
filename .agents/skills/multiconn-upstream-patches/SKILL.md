---
name: multiconn-upstream-patches
description: Review MultiConn schema patches against Tapir source and prepare validated draft PRs with Claude review for human review. Supports review-only and local preparation; client model regeneration belongs to multiconn-codegen.
---

# Refine Tapir API schemas upstream

Use the current downstream inventory to find useful source-schema improvements. Tapir's public changes are schema refinements, not downstream patches. A successful review can find no new work when fixes are already merged or awaiting release.

## Choose the endpoint

- `review`: investigate and recommend; do not modify Tapir source or publish/sync remote branches.
- `prepare`: implement and validate locally when the user explicitly wants preparation only.
- `publish`: implement, validate, commit and push topic branches, open draft PRs, and manually request Claude review. Stop for human review on the PRs after Claude finishes. This is the default for requests such as “bring the temporary patches upstream” or “prepare PRs.”

Infer scope from the request and existing authorization. Preserve an explicit local-only or review-only instruction. Do not regenerate models, change the release pin, remove patches merely because source changes merged, or start this workflow automatically after codegen. Explain any incorrect client patch separately and change it only within scope.

## Establish inputs and source state

Read the relevant final release report in `code_generation/documentation/reports/codegen/` and any prior upstream run report in `code_generation/documentation/reports/upstream-patches/`, the active `schema-patch-tracking.md`, and relevant calls/helpers in `code_generation/shared/schema_patching.py`. Use `tapir_unpatched_schema.json` and `tapir_master_schema.json` for released comparisons; confirm the client release and local patch revision. They are not upstream-main snapshots. Historical reports are supporting evidence, not mandatory reading when current source answers the question. Use the [pipeline brief](../../../code_generation/documentation/archicad_api_codegen_brief.md) only when generation-layer context is needed.

Locate the Tapir checkout from remotes and user context. Read its repository instructions and working-tree state. Discover the upstream repository, available fork and default branches rather than assuming `origin` is upstream. Record the client release, exact source baseline and final branch tip; avoid routine per-file hashes and exhaustive snapshots in durable reports.

For new proposals, prefer topic branches in upstream when the user has write access. Use a fork when access or the user's preference requires it; preserve the head location of existing PRs. Fetch and verify upstream's default branch before starting. Only when publishing through a fork, fast-forward sync its default branch with `gh repo sync <fork> --source <upstream> --branch <default-branch>`. Never force-reset a fork's default branch; preserve divergent commits and base the proposal on fetched upstream instead. Preserve unrelated local work.

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

Describe upstream changes in commit subjects rather than downstream patch debt. Use an explanatory body when provenance or a compatibility decision matters. Follow requested commit/amend history. After validation, commit only intended Tapir source changes, push to the selected repository's topic branch and verify its remote tip. Rebase an existing branch when requested or needed for integration; force-push only with authorization and an explicit lease on the recorded remote tip. Never publish directly to upstream main.

### Draft PR, Claude review, then human review

In `publish` mode, open each validated branch as a draft PR without an intermediate approval or copy/paste step. Use the prepared title and body, check for an existing PR first, and verify `isDraft=true`.

Manually request Claude review while the PR stays draft; see [Claude review](references/schema-review.md#claude-review). Wait for the run and read its summary and inline findings: a green Actions job means the review ran, not that it approved the change. Fix actionable findings within scope, repeat affected validation, and request at most one follow-up review. Stop with the findings if another round would be needed or a contract decision requires the user. Do not expand scope just to satisfy a bot suggestion.

Return a compact table of draft PR links, affected commands/names, validation, Claude's result, and remaining decisions. Human review happens on those PRs. Do not mark them ready or launch the merge action until the user explicitly authorizes merging. If the user chooses manual submission, provide copyable Markdown instead.

### Schema-refinement PR format

Use a short aim, the exact names and consumers changed, and validation evidence. Create PRs with `--draft`; no `tapir-schema-refinement` marker or label is needed. Draft status prevents Tapir's auto-merger from taking them before the final check. Keep intentional acceptance changes in separate PRs with their justification.

After reviewing a draft, a maintainer starts `schema_refinement.yml` from `main` with its PR number and `merge=true`. The action compares against current main while the PR remains draft, then marks it ready and requests a merge only after validation and existing checks pass. Do not mark it ready by hand first. See [manual action usage](references/schema-review.md#manual-action) for the CLI command. The local preflight and this final action are the two schema comparisons; do not add a separate automatic PR comparison. Inspect upstream's current workflow before dispatching it, and do not claim that the merge API atomically pins main.

## Validate proportionately

Interpret sources using Tapir's current documentation tooling in memory or isolated temporary output. Cache the baseline for the run. Check reference resolution, name collisions, command access to common definitions and the complete structural difference against that baseline. Do not hand-edit or commit generated docs.

Before pushing a committed schema proposal, run the [schema merge check](scripts/check_schema_merge.py) against the fetched upstream base and proposal head. It generates schemas from the base and the synthetic merge in isolation. This catches schema regressions that Git can merge cleanly. Repeat it when the base or the proposal's schemas change, including after conflict resolution. See [merge check usage](references/schema-review.md#merge-check) for the command and how to review intentional changes.

Equivalent changes preserve fields, types, requiredness, additional properties, bounds, enum order and union branches; review annotations separately. For a correction/tightening, allow only the justified acceptance change and explain it. Input validation can change behavior before unchanged execution code runs.

Do not use indiscriminate expansion as proof: preserve reference siblings, recursive definitions and union semantics. Check the actual renderer when descriptions move. Run focused annotation/renderer checks after prose-only edits; repeat the full contract comparison when source contracts or the rebase baseline change. Distinguish source checks, SDK builds and live Archicad tests, and put their evidence/limitations in the run report.

## Deliver one run record and maintain the active queue

Return draft PR links with the main validation and Claude review results. For local preparation, return the branch/diff and prepared PR text instead. Provide fenced Markdown titles/descriptions when the user wants manual submission. Explain the resulting upstream schema and material compatibility consequences; keep routine test logs and investigation history out of the PR body. Do not force the title to list every affected domain.

Maintain **at most one durable upstream report per logical run**, including follow-up reviews, description edits, rebases and publication on later dates. Store it at `code_generation/documentation/reports/upstream-patches/upstream-refinements-<version>-<start-date>.md` and update it in place. Read generation reports from the sibling `reports/codegen/` folder; keep relative links valid across these folders. Keep only useful decisions/rejected alternatives, source baseline/final head/PR, compatibility evidence and validation limits. When both a reference and its definition retain descriptions, list their locations and full strings. Link to active tracking instead of repeating its path inventory. Keep scratch scripts, intermediate logs and snapshots untracked; no additional report per phase, day or question. A no-new-work review may only need a tracking update.

`code_generation/documentation/schema-patch-tracking.md` is the **active queue**: unresolved candidates, published branches/submitted PRs and merged fixes awaiting released documentation. Group by decision and record original paths, source/PR status, removal conditions and alias needs. Do not copy all Permanent patches into it or keep retired-patch inventories/tombstones. Once release adoption confirms retirement, remove the entry; the generation report and Git history preserve what changed. Do not duplicate executable patch implementations or generated schemas.

Automatically stage the completed run report in the **MultiConn checkout** with `git add -- code_generation/documentation/reports/upstream-patches/upstream-refinements-<version>-<start-date>.md`, using the exact current report path. Restage that same report after final revisions or later follow-ups in the logical run. Stage only this report; do not additionally stage tracking or unrelated files. Preserve existing staged changes and do not commit MultiConn changes unless requested. A review-only run remains read-only; a tracking-only no-new-work outcome has no report to stage.

Retirement belongs to a later `$multiconn-codegen update tapir to <released-version>` run: confirm the correction in fetched release documentation, resolve renamed paths/dependencies, remove redundant calls, retain necessary aliases in `code_generation/shared/model_aliases.py`, then complete both representations, unified generation and tests. A source merge or release tag alone is insufficient. Preserve loud stale-patch guards. Do not create a watcher or scheduled task.
