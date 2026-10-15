---
name: multiconn-upstream-patches
description: Review multiconn_archicad temporary and source-review schema patches against Tapir implementation source, and prepare upstream schema fixes with reviewable branches and PR descriptions. Use for upstream patch cleanup following a Tapir model update; model regeneration belongs to multiconn-codegen.
---

# Bring MultiConn schema patches upstream

Reduce downstream patch debt by fixing Tapir's schema sources. Start from the current patch inventory and generation report, then check current upstream source. A successful run can find no new upstream work: merged fixes may still await a release.

## Operations and boundaries

- `review`: read-only investigation and a proposed grouping of changes.
- `prepare`: investigate, implement justified upstream changes on reviewable branches, validate them and write copyable PR descriptions. Commit and publish only within the user's requested scope. Infer the operation from the request when omitted; an inventory or explanation request remains read-only.

```text
$multiconn-upstream-patches review the follow-up from the latest generation report
$multiconn-upstream-patches prepare the new non-breaking temporary fixes
$multiconn-upstream-patches prepare and push branches; I will open the PRs manually
```

Do not regenerate client models, change the pinned release, remove patches merely because source changes merged, or automatically start this workflow when generation finishes. If investigation exposes an incorrect local patch, explain the client correction separately and implement it only within the requested scope. A passing generation audit does not establish that a patch should go upstream.

## Establish inputs and pending work

Read the relevant final release report in `code_generation/documentation/reports/`, the current `code_generation/documentation/schema-patch-tracking.md`, and relevant parts of `code_generation/shared/schema_patching.py`. Use `tapir_unpatched_schema.json` and `tapir_master_schema.json` for released-schema comparisons; confirm their release and patch revision. They do not represent upstream `main`.

Record the client release and upstream default-branch commit. Locate the real Tapir checkout using its remote and user context, rather than an assumed working directory or personal absolute path. Inspect repository instructions and existing PRs/tracking before creating duplicate work; fetch current upstream when needed.

Use the [pipeline brief](../../../code_generation/documentation/archicad_api_codegen_brief.md) when generation-layer context is needed. Source and current released schemas are authoritative; historical reports explain their recorded decisions.

Review temporary patches and unresolved breaking source-review patches, including older candidates without a disposition. Distinguish unmerged fixes, merged fixes awaiting a release, and fixes confirmed in released documentation. Skip already merged proposals. Exclude established permanent generator workarounds and intentional breaking client choices unless explicitly selected for review. Incorrect singularization, numeric collision suffixes and other generator-only naming issues belong to local Permanent patches; valid inline schemas do not require upstream extraction just to accommodate this generator. Propose naming/extraction only with independent schema-design justification or an explicitly requested upstream extraction policy.

Trace dependencies: a patch can target a definition introduced by earlier naming operations rather than an actual upstream definition. Map it back to the original command/property before searching C++.

## Investigate each decision

Record the original schema path, consumers, local transformation and reason, source location and retirement condition. Count declarations separately from operations expanded by loops; counts do not determine PR boundaries.

Compare the released schema, patched schema and latest upstream source. If source already contains the fix, record that outcome rather than extracting it again. For a contract-changing patch, inspect command execution and the exact SDK getter/setter. Use primary Graphisoft documentation and available version-specific SDK headers when behavior depends on them. Distinguish documented supported values, Tapir fallback handling and live observations.

Outcomes include equivalent extraction/reuse; source typo/correction; deliberate contract tightening; incorrect local patch; intentional workaround; already submitted/merged; and unresolved. Do not relabel an uncertain breaking patch as non-breaking. Read [schema-review.md](references/schema-review.md) for sharing, names, descriptions and compatibility evidence.

## Prepare upstream changes

- Edit `archicad-addon/Sources/*.cpp` schema strings and `archicad-addon/Sources/RFIX/Images/CommonSchemaDefinitions.json`. Documentation `.js` files are generated inputs for MultiConn, not the upstream editing surface. Leave documentation generation to maintainers unless requested.
- Reuse definitions for the same concept and contract, preserving request/response and creation/modification distinctions. Search related consumers for further meaningful reuse, including equivalent enums outside the original patch list.
- Ensure commands introducing common references include common definitions through `CommonSchema::Used`. This constructor change can be needed even without execution changes.
- Start with numerous straightforward equivalent changes, then payloads and unions. Isolate acceptance changes and other breaking decisions. Combine logical groups into a few PRs and meaningful commits; do not impose a fixed count or one commit per patch.
- Prefer independent branches from current upstream `main` for the user's rebase-and-merge workflow. Shared definitions can create dependencies: combine or sequence such changes explicitly. Separate files do not prove independence.
- Follow requested review history: new commit versus amend/rebase. Force-push only when authorized, using an explicit lease. Preserve unrelated work and make managed-worktree branches available for normal checkout when finished.

## Validate

Interpret C++ schema sources with Tapir's current documentation tooling in memory or in isolated temporary output. Do not hand-edit or commit generated documentation. Check reference resolution, name collisions, command access to common definitions and the complete structural difference against the recorded upstream baseline.

For equivalent extraction, preserve fields, types, requiredness, additional properties, bounds, enum values/order and union branches. Review annotations separately. For correction/tightening, allow only the justified acceptance change and explain it: input validation can alter behavior before unchanged C++ execution code runs.

Indiscriminate reference expansion does not prove equivalence: sibling keywords, recursive definitions and union semantics require care. Check actual description rendering when moving text beside `$ref`. Use checks proportional to the change; distinguish source checks, SDK builds and live Archicad tests. Put validation evidence in the work report, without a routine verification section in the PR description.

## Deliver and track retirement

Provide short copyable Markdown per PR: the concrete problem, resulting behavior, useful examples and material compatibility consequences. Keep validation and unresolved decisions in the accompanying report. When both reference and definition retain descriptions, separately list their locations and full quoted strings.

Maintain the ongoing tracking document at `code_generation/documentation/schema-patch-tracking.md`. Put durable upstream review reports under `code_generation/documentation/reports/` when needed; link to tracking rather than duplicating its inventory. Keep final reviewed reports and tracking suitable for source control, and keep intermediate logs/snapshots in untracked scratch storage. Do not stage or commit these files unless requested. Group related operations by decision and record the original paths, PR/commit or unresolved question, removal condition, client alias needs and disposition:

```text
needs investigation -> proposed -> submitted -> merged awaiting release -> retired
```

Record the released version only after confirmation. This is tracking, not an executable patch registry: do not duplicate patch implementations or generated schemas. Update it during requested runs; do not create a watcher or scheduled task.

Retirement belongs to a later `$multiconn-codegen update tapir to <released-version>` run. Confirm the correction in fetched release documentation, map renamed/moved paths, remove redundant operations and resolve dependencies, retain necessary aliases in `code_generation/shared/model_aliases.py`, then complete both model representations, unified generation and tests. A release tag is insufficient if its documentation lacks the correction. Preserve loud guards; do not hide stale patches with conditional skips.
