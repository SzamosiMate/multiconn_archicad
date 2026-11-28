# Three schema refinement topics following Tapir 2.0.1

Started 2026-11-27. The user requested three substantial topics and three PRs through the upstream-patches skill. Initially prepared as three independent drafts. After the user merged #3106, #3104 and #3105 were refreshed on that main; the latest heads and integration evidence are recorded below.

## Inputs and source state

- Client target: **Tapir 2.0.1**; [release adoption record](../codegen/tapir-2.0.1.md), released unpatched and patched schemas. Reviewed patch revision: `e988b3b68591530b6b537f5bdda8239f754e8c38`; client HEAD at start: `ae1e2c2c05dacf85da46d7c24cdff5e3c84cb0b0`.
- Upstream: `ENZYME-APD/tapir-archicad-automation`, default `main`, source baseline **`5c0555cbee237e85ad385098b14794bc32f9cf52`**. Fetched main and verified its remote tip. The authenticated user has maintain/push access, so new branches and PR heads live upstream. The available `SzamosiMate` fork is not used or synced for these proposals.
- Existing proposals were checked before implementation. Stair pilot [#3084](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3084) is merged and present in the baseline; it is excluded. Earlier #1386 and #1754 are closed without merge; #1557 is merged. No open schema proposal duplicates these three topics. Open reference-validation proposals #2520/#2755 are separate work, not dependencies or included changes.
- Work uses three isolated worktrees under Tapir's untracked sandbox. The original checkout and unrelated local work are preserved. No generated documentation, client models, release pin, patch implementation or aliases changed. The [active queue](../../schema-patch-tracking.md) owns retirement scope.

## Topic decisions and publication

| Topic | New definitions | Operations | PR | Head at initial handoff |
| --- | ---: | ---: | --- | --- |
| Analytical models | 38 | 40 | [#3104](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3104) | `27fca84162b126a6e93df46950b873270e27c3a4` |
| Project preferences and dimension formats | 42 | 67 | [#3105](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3105) | `c06d599b4bfdffb8b97e7e4a62d5574eacd5a927` |
| Graphic override criteria | 21 | 35 | [#3106](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3106) | `7eba49d132dd6143acf8154f436deeee7bf3d0af` |

### Analytical models

Name cross-section/profile, curve/surface-member, load, link, support, release, visibility and mapping concepts already embedded in common schemas. The 38 names correspond to 39 Temporary operations; one additional sharing operation reuses the same `API_AnalyticalElemPartId` record in import and export mappings. Source execution writes the identical `memberGuid`, `contourIndex`, `edgeOrVertexIndex` record in both directions (`AnalyticalCommands.cpp`). Use the broader upstream name `AnalyticalElementPartId`; retain `AnalyticalExportElementPartId` as a Python compatibility alias during later release adoption if this name ships. Rigid-link start/end connection fields also share their equivalent enum. Preserve the model-variation union and optional/required geometry fields. No command-inline extraction is included.

### Project preferences and dimension formats

42 names, 67 Temporary operations, including the complete `DimensionStandard` item producer needed by its settings. Six preference-page helpers now return separate read/update references. The three affected commands already use `CommonSchema::Used`. Remove the superseded nested format/level builders; command execution remains unchanged. Claude's first review identified the now-unused height-limit count helper as a warnings-as-errors build failure; the follow-up commit removes that helper and its comment. The height-limit bounds remain on the named definitions, and the updated committed head receives a fresh synthetic-merge check.

Readbacks require the reported fields; updates retain optional fields. Zone height-limit arrays preserve exactly three readback entries versus one to three update entries and index-based updates. Dimension-standard length/angle formats remain separate from preferences: in particular standard `showZeroInch` stays integer, preference `showZeroInch` stays boolean, and their other field differences remain. Equivalent radial/level/elevation/door-window/parapet formats share definitions; existing angle/calculation unit definitions are reused.

`ProjectPreferenceType` has 11 values on current main, while patched/released 2.0.1 has six. The five already-supported source pages are `Legacy`, `ImagingAndCalculation`, `Layouts`, `DataSafety`, `CalculationRules`. Extraction preserves current main's full selector; this run introduces no acceptance widening relative to the source baseline. The other 41 definitions match patched 2.0.1 structurally.

### Graphic override criteria

21 names (16 enums, five structured operands), 35 Temporary operations. This complete criterion family is deliberately smaller than the soft 30–50-definition target: the paired operators and custom-property operands form one coherent sharing decision. Preserve recursive composition, enum order, existing comparison operators and free-text/option-set restrictions. Reuse equivalent positive/negative enums and the existing wall-reference-line/slab-reference-plane definitions. General enum meaning belongs on each definition; equality/inequality meaning stays on the actual criterion fields.

## Validation and limits

Each committed head passed the skill's synthetic-merge comparison against the fetched baseline: all command inputs/responses and existing definitions preserve fields, types, requiredness, additional-property constraints, bounds, enum order, union alternatives and reference siblings. Added names are unique and references resolve. No structural differences are intentionally allowed.

The current revision's documentation generator is used in isolated output for Archicad **30**. Scratch-only function-lookup prefilters/cache skip files that cannot contain the requested C++ identifier tokens; the generator's original matching/tokenization/interpreter still determines every function and schema. No documentation generator changes are proposed upstream. Generated snapshots are cached for reference, annotation and renderer review.

- **Analytical models**: 832 commands, 1146 existing definitions, 38 additions, zero structural differences; synthetic merge tree `791aae76d406fc2d65e60fccab4efa83556f6109`. Affected commands: `GetAnalyticalModelVariation`, `GetAnalyticalModel`, `GetAnalyticalVisibilitySettings`, `SetAnalyticalVisibilitySettings`, `GetAnalyticalMemberDetails`, `GetAnalyticalReleases`, `SetAnalyticalReleases`, `GetLCSOfAnalyticalMembers`, `GetAnalyticalMemberPartGeometries`, `GetAnalyticalSupports`, `GetAnalyticalLinks`, `CreateAnalyticalSupports`, `CreateAnalyticalLinks`, `ConvertAnalyticalLinksToNonShortest`, `GetAnalyticalLoads`, `CreateAnalyticalLoads`, `CreateElementsFromAnalyticalMembers`.
- **Project preferences and dimension formats**: 832 commands, 1146 existing definitions, 42 additions, zero structural differences; synthetic merge tree `d91dfb91630422b2a7643d4ae3d06f1f065fa356`. Affected commands: `GetDimensionStandards`, `GetProjectPreferences`, `SetProjectPreferences`.
- **Graphic override criteria**: 832 commands, 1146 existing definitions, 21 additions, zero structural differences; synthetic merge tree `6c12101372bddf59df4a02368d7b905b1e86ba29`. Affected commands: `GetGraphicOverrideRules`, `GetGraphicOverrideRulesByName`, `CreateGraphicOverrideRules`, `ModifyGraphicOverrideRules`.

All 101 added definitions were compared with patched 2.0.1; only the pre-existing source selector expansion described above differs. The actual target-branch renderer passed every changed reference site and every non-null command schema without mutating common definitions. `git diff --check` passes. Existing common-schema access remains in place.

Supplemental confirmation requested by Claude: each branch's own `tools/expand_schemas.py` expands all 832 before/after command contracts equally after excluding prose annotations. Intentional prose differences affect three analytical schema sides, one preference schema side and four criterion schema sides; they are reviewed separately above and in the full description pairs below. This expansion check supplements the reference/union-aware structural guard rather than replacing it.

No local SDK build or live Archicad test was run. Structural schema equivalence does not prove Archicad's handling of relocated references; native CI and maintainer review remain separate evidence. Other version-conditioned schemas are outside the Archicad 30 comparison. No contract correction/tightening was selected, so no new SDK getter/setter acceptance claim is made.

## Initial Claude review and handoff

- **Analytical models**: manually requested draft review [46059359034](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46059359034) for head `27fca84162b126a6e93df46950b873270e27c3a4`. Clean: no blocking findings or inline threads. Claude checked the diff; it could not run the schema expander on its runner. [Review summary](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3104#issuecomment-7226928490).
- **Project preferences and dimension formats**: manually requested draft review [46059979196](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46059979196) for head `c06d599b4bfdffb8b97e7e4a62d5574eacd5a927`. The [initial review](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46059382026) found the unused height-limit count helper would fail warnings-as-errors builds. Removed it and its comment in the final head; fresh full structural and renderer validation passed. The one follow-up review is clean with no inline threads or blocking findings. Claude could not run the generator/expander in its sandbox; local validation additionally confirms all 832 expanded command contracts are equal after excluding prose. [Follow-up summary](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3105#issuecomment-7227011114).
- **Graphic override criteria**: manually requested draft review [46059385524](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46059385524) for head `7eba49d132dd6143acf8154f436deeee7bf3d0af`. Clean: no blocking findings or inline threads. Claude confirmed values/order, requiredness, additional-property rules, equivalent enum reuse and unique names. [Review summary](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3106#issuecomment-7226959581).

At the initial handoff, all three published heads had clean Claude summaries and no inline review threads. Draft/head verification passed and there were no failed CI checks; native CI was still pending. All three remained draft for human review, and the agent dispatched no readiness change or merge workflow. Retire downstream operations only after fetched release documentation supplies equivalent named definitions/references at every producer and consumer; preserve the analytical identifier alias if needed. A source merge alone is insufficient. The report is staged in MultiConn; tracking stays unstaged, and existing staged work is preserved. MultiConn changes are not committed.

## Refresh after the first batch merged

The user dispatched all three final merge actions. All three schema-validation jobs passed against the original baseline. #3106 merged as `52fd8877fbabe848b1f527646573a4fae3b21fad`; the #3104/#3105 finish jobs then refused the stale base. Their subsequent Git conflicts were independent of that freshness protection: each proposal had appended its definitions at the same closing brace of the common JSON file.

The user authorized refreshing both open PRs with explicit force-with-lease updates and no extra commits, and requested a prevention rule in the upstream-patches skill. Both branches were rebased directly onto fetched main `52fd8877fbabe848b1f527646573a4fae3b21fad`, retaining all merged criteria changes. Added analytical definitions now precede `AnalyticalCrossSection`; preference definitions precede the existing `AngleUnitFormat`. Only their placement and ancestry change; every reviewed named schema and the preference C++ implementation match the previous heads.

| PR | Recorded lease / previous tip | Refreshed published tip | Commits above main | Fresh Claude review |
| --- | --- | --- | ---: | --- |
| [#3104](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3104) | `27fca84162b126a6e93df46950b873270e27c3a4` | `135dd3bddc779f6ee4f69135b178850dc1906b11` | 1 | [Run 46066753399](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46066753399): incomplete; reviewer abstained, no new verdict |
| [#3105](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3105) | `c06d599b4bfdffb8b97e7e4a62d5574eacd5a927` | `72bc7ab9a03aaf4bba13f192368756612b04c110` | 2 | [Run 46066756664](https://github.com/ENZYME-APD/tapir-archicad-automation/actions/runs/46066756664): clean diff review, runner validation limitation |

Both remote tips were verified after the explicit leased pushes, and GitHub reports both PRs draft and mergeable. The original one-/two-commit histories were rewritten without adding a commit; the helper removal remains in #3105. No merge action was dispatched during this refresh.

Read both fresh runs' summaries/logs and inline threads. #3104's green job is **not** a completed review: Claude reported that its sandbox refused file writes/chained commands, read only the first part of the diff, and explicitly declined to write a verdict or post a summary. It is recorded as incomplete and was not automatically retried. #3105 posted a [clean summary](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3105#issuecomment-7227995239) with no blockers from reading the diff, while explicitly noting that runner restrictions prevented its own reference/expansion checks. The local checks below provide that validation independently; they do not turn #3104's partial review into an approval. Neither PR has inline review threads. Native CI on the refreshed heads is pending; no failed checks were present at handoff.

Validation against refreshed main: each proposal passes the full synthetic-merge comparison for **832 commands and 1167 existing definitions, zero structural differences**. Added definitions remain 38 and 42. Renderer checks pass all 40/67 changed sites and 1550 non-null command schemas; expanded contracts are equal excluding the previously reviewed prose. Individual synthetic trees are `ec065fffc55b43cf3ff6192df1caec48eb91efaf` and `d729f9e1924bc4cecae076ebe8d23760de9afea6`.

Joint integration was checked in both orders, **#3104 → #3105** and **#3105 → #3104**. Both merge without conflicts and produce the identical tree `0ac5aab246891f7d567cf1498768faad27055391`, containing **1247 definitions** (all current-main definitions plus both topics' 80 additions). Duplicate-key parsing and exact union-of-changes comparisons preserve every definition/reference and the preference C++ file. The full combined structural comparison also passes for all 832 commands and 1167 baseline definitions with zero differences. The old heads fail the same pairwise Git test in both orders, reproducing the original failure mode. Synthetic commits/objects and generation outputs remain scratch-only.

The [upstream-patches skill](../../../../.agents/skills/multiconn-upstream-patches/SKILL.md) now blocks publication of an independent batch set until pairwise/both-order and full-set integration checks pass, requires separate domain insertion anchors, and requires sequential final validation-and-merge actions against fresh main. Detailed steps live in its schema-review reference. The skill validator and `git diff --check` pass. Skill changes remain unstaged; only this existing run report is restaged. Native SDK builds and live Archicad tests were not run locally.

## Local sequential merge helper preparation

The user requested a simpler ordered merge runner with roughly 20-second checks, agreed that Tapir should own it, and explicitly requested leaving it uncommitted for later review. Prepared `tools/queue_schema_refinements.py`, its isolated tests under `tools/tests/`, and usage guidance in `CLAUDE.md` on local branch `codex/schema-merge-queue`, worktree `C:/Users/szami/source/repos/tapir-archicad-automation/sandbox/schema-merge-queue`, based on fetched main `30d499d91a1fd188f5ce80cfa591afc2d09a739f`. No helper changes were committed or published, and no merge actions were dispatched by the helper.

The one-shot command previews by default; an explicitly authorized `--merge` invocation waits for existing PR CI, verifies the captured head, dispatches the existing workflow from main, watches its exact returned run every 20 seconds, and reconciles its result before another action starts. At the user's 2026-11-28 review request, pre-dispatch head changes refresh that item and move it to the back of the queue for fresh checks. Main advancing between queued actions needs no retry because each new action captures fresh main. A main advance during validation is now rescheduled as well: require the exact trusted-controller freshness error, an unchanged PR head, and for finish failures the matching pinned request artifact plus proof current main differs from that base. Head/stale-base reschedules share a three-reschedule default (`--max-reschedules` adjusts it); every stale-base retry starts a fresh comparison. Definite per-PR failures are recorded and removed while remaining entries continue; the final exit status is nonzero if any failed. A failed watcher polls the same server run until it is confirmed completed within the remaining wait budget. An unresolved/active run at timeout, ambiguous dispatch, or interruption blocks further dispatches. Generic validation/build/conflict failures do not authorize retries. Already-merged entries are skipped for resumption, and stopping the helper does not cancel a dispatched server action. This removes manual waiting without shortening or weakening each schema comparison. MultiConn's skill documents invocation only; implementation/tests stay in Tapir.

At the user's readability follow-up, separated preparation and finalization stale-base detection into named functions returning `str | None`. Extracted controller-log parsing, pinned-request verification, dispatch identity checking, workflow watching, merge-result checking, plan construction and bounded rescheduling from the longer functions. Renamed the head guard to `ensure_head_unchanged`; `reschedule_proposal` now explicitly owns moving a changed candidate to the queue's back. Added argument and return annotations throughout the helper, a typed GitHub client interface and a named workflow-run value. This refactor preserves queue behavior.

Validation: **33 isolated tests pass**, including main advancing during preparation before a request artifact exists, main advancing between actions without retries, main advancing during validation with a fresh comparison, bounded stale-base retries, and rejection of untrusted log text, missing request artifacts, mismatched request heads or unchanged main. Other tests cover sequential dispatch/merge confirmation, read-only preview, resumability, reordered head-change rescheduling, per-item failure continuation, failed-run terminal-state reconciliation, status-read retries and active/unknown/ambiguous-run dispatch blocking. All 34 helper functions have argument/return annotations, and their type hints resolve. A read-only classifier check before this refactor against historical failed run `46063467774` successfully recognized its stale base using its real logs/request artifact and current main; it dispatched no workflow. The earlier live read-only preview skipped already-merged #3104 and reported #3105 as draft without dispatching a workflow. CLI help, skill validation and whitespace checks pass. All helper, test and usage changes remain local and uncommitted for the requested review; no live merge was used to test the changes.

## Workflow-tooling publication — 2026-11-28

The user subsequently authorized committing and opening one PR in each repository, superseding the earlier local-only preparation request. [Tapir PR #3116](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3116) publishes the queue helper, its 33 isolated tests and usage guidance from `codex/schema-merge-queue-review`, commit `8bda51daf10a2def91a841a579d6146a0f1ff175`, based on main `780b9fa12ab3dc77f42605b31d8d62d641ef50e7`. Its description links the validation controller (#2814), draft-review support (#3103), stair pilot (#3084) and three topic PRs (#3104–#3106) to explain preparation, review and sequential integration. All **55 tool tests** pass on that source baseline; CLI help and whitespace checks pass. No live merge action was dispatched by the helper.

The companion MultiConn branch `codex/schema-batch-merge-queue` starts from fetched main `925ce86` (the previous draft-review skill PR #110 is already merged). It contains the joint-integration rules, ordered-queue invocation guidance, the existing two run records and active tracking updates. The queue guidance links Tapir #3116 and applies only when that helper is available in the selected Tapir checkout. Skill validation and whitespace checks pass. #3104 and #3105 are confirmed merged as `8d8480c13291c138fd731fb070e62a8f98f2eb5b` and `e2ceba6cc95e4bdb5929997e85615c37ab1d0051`; active tracking now records all three topics as merged, awaiting equivalent released documentation. No client code, patch implementation or release pin changes.

## Retained reference and definition descriptions

The pairs below include newly extracted fields with existing reference annotations and changed references with caller-specific meaning. Full strings are recorded to make renderer/description decisions reviewable.

<details>
<summary>Analytical models</summary>

- `/definitions/AnalyticalVaryingSegment/properties/endProfile` → `AnalyticalCrossSection`
  - Reference: "Only for a tapered segment."
  - Definition: "The cross section of a curve member. The profile image of Archicad 26 and newer is not returned."
- `/definitions/AnalyticalEdgeLoadSettings/properties/loadCaseId` → `GuidId`
  - Reference: "The load case the load belongs to."
  - Definition: "Identifier."
- `/definitions/AnalyticalPointLoadSettings/properties/loadCaseId` → `GuidId`
  - Reference: "The load case the load belongs to."
  - Definition: "Identifier."
- `/definitions/AnalyticalSurfaceLoadSettings/properties/loadCaseId` → `GuidId`
  - Reference: "The load case the load belongs to."
  - Definition: "Identifier."

</details>

<details>
<summary>Project preferences and dimension formats</summary>

- `/definitions/DimensionPreferences/properties/linear` → `LengthDimensionFormat`
  - Reference: "The format of the linear dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferences/properties/radial` → `LengthDimensionFormat`
  - Reference: "The format of the radial dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferences/properties/level` → `LengthDimensionFormat`
  - Reference: "The format of the level dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferences/properties/elevation` → `LengthDimensionFormat`
  - Reference: "The format of the elevation dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferences/properties/doorWindow` → `LengthDimensionFormat`
  - Reference: "The format of the door, window and skylight dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferences/properties/parapet` → `LengthDimensionFormat`
  - Reference: "The format of the sill height (parapet) dimensions."
  - Definition: "The display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/linear` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the linear dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/radial` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the radial dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/level` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the level dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/elevation` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the elevation dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/doorWindow` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the door, window and skylight dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/DimensionPreferencesUpdate/properties/parapet` → `LengthDimensionFormatUpdate`
  - Reference: "The format of the sill height (parapet) dimensions."
  - Definition: "Partial changes to the display format of a length dimension."
- `/definitions/FloorPlanCutPlanePreferences/properties/topLevel` → `FloorPlanCutPlaneLevel`
  - Reference: "The top of the floor plan range: elements are shown up to this level."
  - Definition: "A floor plan display limit measured from a relative story."
- `/definitions/FloorPlanCutPlanePreferences/properties/bottomLevel` → `FloorPlanCutPlaneLevel`
  - Reference: "The bottom of the floor plan range: elements are shown down to this level."
  - Definition: "A floor plan display limit measured from a relative story."
- `/definitions/FloorPlanCutPlanePreferencesUpdate/properties/topLevel` → `FloorPlanCutPlaneLevelUpdate`
  - Reference: "The top of the floor plan range: elements are shown up to this level."
  - Definition: "Partial changes to a floor plan display limit measured from a relative story."
- `/definitions/FloorPlanCutPlanePreferencesUpdate/properties/bottomLevel` → `FloorPlanCutPlaneLevelUpdate`
  - Reference: "The bottom of the floor plan range: elements are shown down to this level."
  - Definition: "Partial changes to a floor plan display limit measured from a relative story."
- `/definitions/ProjectReferenceLevels/properties/level1` → `ProjectReferenceLevel`
  - Reference: "The first reference level."
  - Definition: "A named reference level measured from Project Zero."
- `/definitions/ProjectReferenceLevels/properties/level2` → `ProjectReferenceLevel`
  - Reference: "The second reference level."
  - Definition: "A named reference level measured from Project Zero."
- `/definitions/ProjectReferenceLevelsUpdate/properties/level1` → `ProjectReferenceLevelUpdate`
  - Reference: "The first reference level."
  - Definition: "Partial changes to a named reference level measured from Project Zero."
- `/definitions/ProjectReferenceLevelsUpdate/properties/level2` → `ProjectReferenceLevelUpdate`
  - Reference: "The second reference level."
  - Definition: "Partial changes to a named reference level measured from Project Zero."

</details>

<details>
<summary>Graphic override criteria</summary>

- `/definitions/GraphicOverrideCriterion/properties/structureType` → `GraphicOverrideStructureType`
  - Reference: "Matches elements whose structure type (Wall/Beam/Column basic vs. composite vs. complex profile) equals this value."
  - Definition: "The structure type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/wallComplexity` → `GraphicOverrideWallComplexity`
  - Reference: "Matches walls whose complexity equals this."
  - Definition: "The wall complexity compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/wallComplexityNot` → `GraphicOverrideWallComplexity`
  - Reference: "Matches walls whose complexity is NOT this."
  - Definition: "The wall complexity compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/wallReferenceLinePosition` → `WallReferenceLineLocation`
  - Reference: "Matches walls whose reference line position equals this."
  - Definition: "The Core* values only have an effect on a Composite or Profile wall (structureType) - a Basic wall has no core skin, and Archicad falls back to the nearest non-core equivalent (e.g. CoreCenter becomes Center)."
- `/definitions/GraphicOverrideCriterion/properties/renovationStatus` → `GraphicOverrideRenovationStatus`
  - Reference: "Matches elements whose renovation status equals this."
  - Definition: "The renovation status compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/wallGeometryType` → `GraphicOverrideWallGeometryType`
  - Reference: "Matches walls whose geometry type equals this."
  - Definition: "The wall geometry type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/columnCoatingType` → `GraphicOverrideColumnCoatingType`
  - Reference: "Matches columns whose coating type equals this."
  - Definition: "The column coating type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/columnCrossSectionType` → `GraphicOverrideColumnCrossSectionType`
  - Reference: "Matches columns whose cross section type equals this."
  - Definition: "The column cross section type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/slabReferencePlaneLocation` → `SlabReferencePlaneLocation`
  - Reference: "Matches slabs whose reference plane location equals this."
  - Definition: "Location of the slab reference plane."
- `/definitions/GraphicOverrideCriterion/properties/slabEdgeAngle` → `GraphicOverrideSlabEdgeAngle`
  - Reference: "Matches slabs whose edge angle mode equals this."
  - Definition: "The slab edge angle mode compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/roofCutBodyType` → `GraphicOverrideRoofCutBodyType`
  - Reference: "Matches roofs whose cut body type equals this."
  - Definition: "The roof cut body type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/roofEaveOverhangType` → `GraphicOverrideRoofEaveOverhangType`
  - Reference: "Matches roofs whose eave overhang type equals this."
  - Definition: "The roof eave overhang type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/roofEdgeAngle` → `GraphicOverrideRoofEdgeAngle`
  - Reference: "Matches roofs whose edge angle mode equals this."
  - Definition: "The roof edge angle mode compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/roofGeometryType` → `GraphicOverrideRoofGeometryType`
  - Reference: "Matches roofs whose geometry type equals this."
  - Definition: "The roof geometry type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/shellCutBodyType` → `GraphicOverrideShellCutBodyType`
  - Reference: "Matches shells whose cut body type equals this."
  - Definition: "The shell cut body type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/shellGeometryType` → `GraphicOverrideShellGeometryType`
  - Reference: "Matches shells whose geometry type equals this."
  - Definition: "The shell geometry type compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/penReplacement` → `GraphicOverridePenReplacement`
  - Reference: "Matches elements whose pen replacement rule equals this value."
  - Definition: "The pen replacement rule compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/penReplacementNot` → `GraphicOverridePenReplacement`
  - Reference: "Matches elements whose pen replacement rule does not equal this value."
  - Definition: "The pen replacement rule compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/structuralFunction` → `GraphicOverrideStructuralFunction`
  - Reference: "Matches elements whose structural function equals this value."
  - Definition: "The structural function compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/structuralFunctionNot` → `GraphicOverrideStructuralFunction`
  - Reference: "Matches elements whose structural function does not equal this value."
  - Definition: "The structural function compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/position` → `GraphicOverridePosition`
  - Reference: "Matches elements whose position equals this value."
  - Definition: "The position compared by a graphic override criterion."
- `/definitions/GraphicOverrideCriterion/properties/positionNot` → `GraphicOverridePosition`
  - Reference: "Matches elements whose position does not equal this value."
  - Definition: "The position compared by a graphic override criterion."

</details>
