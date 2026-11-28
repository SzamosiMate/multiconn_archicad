# Stair schema pilot following Tapir 2.0.1

Started 2026-11-26. The user requested one 30–100-schema pilot for the new merge workflow. After reviewing the published branch and prepared PR text, the user approved draft submission; [PR #3084](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3084) is open as a verified draft.

## Source and publication

- Client target: Tapir **2.0.1**, released unpatched/patched schemas and the [adoption record](../codegen/tapir-2.0.1.md). Reviewed local patch revision: `e988b3b68591530b6b537f5bdda8239f754e8c38`. The [active queue](../../schema-patch-tracking.md) and patch source own retirement scope.
- Upstream: `ENZYME-APD/tapir-archicad-automation`, default `main`; fork: `SzamosiMate/tapir-archicad-automation`, default `main`. Fork main fast-forward synced without force, then both fetched tips verified at `b85ee4740c924f9825431cf3f7c098487c308c96`.
- Source baseline: `b85ee4740c924f9825431cf3f7c098487c308c96`. Published proposal: [`schema/refinements-2.0.1-stairs`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-2.0.1-stairs), commit [`6669cf019`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/6669cf01990b24b0cbc9882379a5f2f1c5801b05); [review diff](https://github.com/SzamosiMate/tapir-archicad-automation/compare/b85ee4740c924f9825431cf3f7c098487c308c96...schema/refinements-2.0.1-stairs). The pushed fork tip was verified with `git ls-remote` and exactly matches the validated head.
- Existing proposal review: no open upstream PRs by SzamosiMate; #1557 is merged, #1386 and #1754 are closed without merge. Current source, rather than historical batch status, determined eligibility. No existing proposal was rewritten or included as a dependency.
- Tapir work stayed in the current checkout on a new branch. Existing untracked `.idea/` and earlier sandbox worktrees were preserved. No MultiConn models, patch implementation, release pin or generated documentation changed.

## Batch and compatibility decisions

One independent stair batch: **35 definitions (26 enums, 9 objects), 39 Temporary helper operations (35 producers and four reference consumers)**. Fourteen existing shared roots change. A single focused source commit changes only `archicad-addon/Sources/RFIX/Images/CommonSchemaDefinitions.json`.

Affected commands through existing shared references: `GetDetailsOfElements`, `CreateStairs`, `ModifyStairs`, `RecreateStairs`. Existing `CommonSchema::Used` access remains in place; command constructors and execution code are unchanged. No other proposal is required.

The candidate plan was limited to the stair family before implementation. Permanent creation/modification item names were used only to identify excluded command-inline paths. Those inputs intentionally repeat some contracts because the source documents an Archicad reference-validation workaround. This pilot does not extract those inputs or claim the pending reference-validation PR is a prerequisite. Read and settings contracts with different requiredness or `Unknown` members remain separate, including baseline segment types, structure types, story visibility and break-line choices.

All 35 proposed contracts compare structurally equal with the corresponding patched 2.0.1 definitions. Three source names are more specific: `SegmentType` → `StairBaselineSegmentType`, `BreakLineAngleType` → `StairBreakLineAngleType`, and `BreakLinePositionType` → `StairBreakLinePositionType`. Preserve the old Python imports through aliases during release adoption if these source names ship. Other names match current patched client names. This run changes no downstream aliases.

| Definition | Kind | Original common path / producer |
| --- | --- | --- |
| `StairBaselineEdgeDetails` | object | `StairDetails/baseLineEdges/items` |
| `StairBaselineSegmentTypeOrUnknown` | enum | `StairDetails/baseLineEdges/items/segmentType` |
| `StairBaselineVertexDetails` | object | `StairDetails/baseLineVertices/items` |
| `StairBaselineTurnTypeOrUnknown` | enum | `StairDetails/baseLineVertices/items/turnType` |
| `StairStructureSymbolType` | enum | `StairDetails/structureSymbols/items/structureType` |
| `StairStoryStructureVisibility` | object | `StairDetails/structureVisibilityOnStories/items/stories/items/structures/items` |
| `StairStoryStructureType` | enum | `StairDetails/structureVisibilityOnStories/items/stories/items/structures/items/structure` |
| `StairStoryVisibility` | enum | `StairLayout/storyVisibility` |
| `StairBoundaryEdge` | object | `StairBoundary/edges/items` |
| `StairStoryVisibilitySettings` | object | `StairStructureVisibilitySettings/stories/items` |
| `StairStructureLineVisibility` | object | `StairStructureVisibilitySettings/stories/items/structures/items` |
| `StairStructureFillVisibility` | object | `StairStructureVisibilitySettings/stories/items/fills/items` |
| `StairMonolithPartVisibility` | object | `StairStructureVisibilitySettings/stories/items/monolithParts/items` |
| `StairBaselineSegmentType` | enum | `StairBaseLineEdge/segmentType` |
| `StairBaselinePositionOrUnknown` | enum | `StairDetails/baselinePosition` |
| `StairDisplayType` | enum | `StairDetails/stairDisplayType` |
| `StairHeadroomMethod` | enum | `StairHeadroom/method` |
| `StairRiserPosition` | enum | `StairRiserDetails/riserPosition` |
| `StairStructureRoleOrUnknown` | enum | `StairStructureDetails/role` |
| `StairStructureSideOrUnknown` | enum | `StairStructureDetails/side` |
| `StairStructureTypeOrUnknown` | enum | `StairStructureDetails/structureType` |
| `StairStructureBottomTypeOrUnknown` | enum | `StairStructureDetails/bottomType` |
| `StairDrainingSide` | enum | `StairStructureDraining/side` |
| `StairSymbolStructureType` | enum | `StairStructureSymbolSettings/structureType` |
| `StairWalkingLineSymbolPosition` | enum | `StairDetails/walkingLineSymbolPosition` |
| `StairUniformSideSupports` | object | `StairDetails/uniformLeftRightSideSupports` |
| `StairSideStructureHeightMeasure` | enum | `StairSideStructure/heightMeasure` |
| `StairVisibilityStoryRange` | enum | `StairStructureVisibilitySettings/stories/items/relevantStories` |
| `StairLineStructureType` | enum | `StairStructureVisibilitySettings/stories/items/structures/items/structure` |
| `StairBreakLineAngleType` | enum | `StairLayout/breakLineAngleType` |
| `StairBreakLinePositionType` | enum | `StairLayout/breakLinePositionType` |
| `StairStoryVisibilityInput` | enum | `StairLayoutSettings/storyVisibility` |
| `StairBreakLineAngleTypeInput` | enum | `StairLayoutSettings/breakLineAngleType` |
| `StairBreakLinePositionTypeInput` | enum | `StairLayoutSettings/breakLinePositionType` |
| `StairDrainingSurfaceType` | enum | `StairStructureDraining/surfaceType` |

Sharing is limited to equivalent concepts: `StairStructureDrainingSettings/side` → `StairDrainingSide`, `/surfaceType` → `StairDrainingSurfaceType`, `StairSideStructureSettings/heightMeasure` → `StairSideStructureHeightMeasure`, and `StairStructureFillVisibility/structureType` → `StairSymbolStructureType`. The last reference drops a redundant generic description; its full meaning resides on the target enum. No caller default or restriction is removed.

## Validation and limits

- Required skill merge check: base `b85ee4740c924f9825431cf3f7c098487c308c96`, head `6669cf01990b24b0cbc9882379a5f2f1c5801b05`, synthetic merge tree `62473589968531ecf2d418f114f46e463ad3e3e1`. **832 commands and 1111 existing definitions, zero structural differences**, plus 35 added definitions. Both revisions use their own current docs generator in isolated temporary output. Snapshots retained only as untracked scratch data for the rest of this run.
- Cached baseline comparison confirms every existing common definition and command input/response preserves fields, requiredness, bounds, enum order, union alternatives and reference siblings. No intentional acceptance change. All common and command references resolve, and every added name is unique.
- Current source uses Archicad **30** for documentation interpretation. Other version-conditioned schema paths are outside that check.
- Actual `docs/archicad-addon/renderer.js` passed all **39 changed reference sites** and **1,550 non-null command schemas**, preserves the reviewed descriptions and does not mutate shared definitions. The three inherited reference/definition description pairs in extracted records are listed below; the caller-only `Unknown` restriction stays at the field.
- `git diff --check` passes. No native SDK build or live Archicad test was run. The PR's native checks and maintainer review remain part of the new workflow; structural equivalence does not prove Archicad's reference-handling behavior.

### Retained reference and definition descriptions

- `/definitions/StairStructureFillVisibility/properties/part` references `StairSymbolPart`. Reference: "The visible or the hidden part of the structure (Unknown is refused)." Definition `/definitions/StairSymbolPart/description`: "Whether a stair structure symbol setting is for the visible or the hidden part of the structure (API_StairStructSymbPartID)."

- `/definitions/StairStructureLineVisibility/properties/part` references `StairSymbolPart`. Reference: "The visible or the hidden part of the structure (Unknown is refused)." Definition `/definitions/StairSymbolPart/description`: "Whether a stair structure symbol setting is for the visible or the hidden part of the structure (API_StairStructSymbPartID)."

- `/definitions/StairMonolithPartVisibility/properties/part` references `StairSymbolPart`. Reference: "The visible or the hidden part of the structure (Unknown is refused)." Definition `/definitions/StairSymbolPart/description`: "Whether a stair structure symbol setting is for the visible or the hidden part of the structure (API_StairStructSymbPartID)."

## Draft submission and workflow

Title: **Refine API schemas following Tapir 2.0.1**. The complete proposal description is preserved on [PR #3084](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3084).

Submitted [PR #3084](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3084) with the reviewed title and body after explicit user approval. Verified `isDraft=true`, base `main`, head `6669cf01990b24b0cbc9882379a5f2f1c5801b05` and the single changed `CommonSchemaDefinitions.json` file. No readiness change or merge workflow was requested.

The inspected upstream `schema_refinement.yml` now uses manual dispatch, not the superseded comment-marker flow described by the older tooling report. No marker or label is needed. Keep the proposal draft during review; do not mark it ready manually. A maintainer later dispatches from `main` with `pr=3084` and `merge=true`; validation occurs while draft, then readiness and merge are requested only after validation and existing checks pass. This run does not authorize or dispatch merging. The API pins the head but does not atomically pin a concurrent main update.

Retire the corresponding Temporary operations only when fetched release documentation contains equivalent definitions and references at every producer/consumer; preserve the three compatibility aliases if required. A source merge alone does not retire any operation. The completed report is staged in MultiConn; tracking remains unstaged. MultiConn changes are not committed.
