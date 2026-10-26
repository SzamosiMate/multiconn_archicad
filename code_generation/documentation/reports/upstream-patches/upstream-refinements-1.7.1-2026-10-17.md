# Refine API schemas following Tapir 1.7.1

One upstream-refinement run, started 2026-10-17 and updated through submission on 2026-10-18. This report consolidates the initial preparation, selected-permanent-patch review and publication follow-up. The [active tracking queue](../../schema-patch-tracking.md) owns the original paths and release-retirement conditions; this report preserves decisions and evidence rather than duplicating that inventory.

## Delivery and provenance

- **Submitted PR:** [#1056 — Refine API schemas following Tapir 1.7.1](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1056), open when checked on 2026-10-18. The user submitted it after the branch was published.
- **Published head:** [`43e12ebcf55805ba7b76f1a5608c8e80112b60ed`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/43e12ebcf55805ba7b76f1a5608c8e80112b60ed), on fork branch `codex/schema-temporary-patches-1-7-1`. Keep this existing PR head; the preferred naming for future runs is `schema/refinements-<reviewed-version>`.
- **Final base:** synced fork `main`, `6dfc87d54da3dbd51ebab435e5cfd05a45ffa92a`. The original investigation used upstream `0111fe86620b1f5bebf6105c0695f13cea34cbfe`; the branch was rebased without conflicts and checked again against the final base.
- **Commits:** `f1ac4d497d5cbbceb461f7829673be6a35b9de3d` contains the original beam/slab/wall/Teamwork refinements and description cleanup. `43e12ebc` separately adds the two older extractions selected by the user. Its body explains their older origin versus the 1.7.1 follow-up.
- **Client inputs:** pinned Tapir 1.7.1, its [final generation report](../codegen/tapir-1.7.1.md), saved unpatched/patched schemas and the corresponding helper calls. These are released-schema evidence, not upstream-main snapshots. The initial client commit was `17cda2f6778a8bcdb8068a418a14f9f72d506e33`; input schema/patch content was not changed in this run.
- The fork branch was force-pushed with an explicit lease on its former tip `5a084e93c52a94db7abd5443281e78e25a23332f`, and its final remote tip was verified. No base branch, generated documentation or client model output was pushed.

## Source decisions

| Area | Result and reason |
| --- | --- |
| Beam holes | Introduce `BeamHoleModification` and reuse `BeamHoleType`. Keep the write contract separate from `BeamHole`: execution assigns replacement identifiers; supplied modifications omit `holeId`, retain positive width/height and the rectangular-only height note. The read definition is unchanged. |
| Slab creation | Reuse equivalent `SlabStructureType`, retaining optionality and the caller's material/composite/tool-default/favorite rules. Do not merge slab and roof enums solely because their current values match. |
| Wall story links | Reuse `LinkToSettings`. Put general creation-time selection on its `newCreationMode` field. Keep only the mapping to `floorIndex`/`zCoordinate` at `CreateWalls`, and the wall readback expectation at `WallDetails`. `ModifyWalls` adds no redundant caller description. |
| Teamwork reservations | Share `User` across four result locations without changing the enclosing element-conflict/execution/status wrappers. Preserve numeric `userId`, string `userName`, both required, and no extra user properties. Enable `CommonSchema::Used` in all four commands. The application GSID `userId` is a different concept. |

Creation commands already inherit common-definition support; the other element consumers also already have it. Search found no further equivalent user object in current source; the other story-link consumers already use the shared definition. The SDK creation-time rule was checked against AC27/AC29 headers and [Graphisoft's `API_LinkToSettings` documentation](https://graphisoft.github.io/archicad-api-devkit/struct_a_p_i___link_to_settings.html). The wall readback expectation is retained from source; this run did not newly establish it live or assert a reset rule for every element type. Object/Lamp limitations stay on `ObjectDetails`.

The earlier schema PRs #803–#808 and #816 were already merged; their work was not resubmitted. In particular, the renderer already supports descriptions beside references. Open Teamwork additions #955/#1021 were not incorporated or made dependencies. The inspected #1021 diff has inline owner/reserver objects that could reuse `User` if both changes land; review that integration when relevant.

## Explicitly selected older extractions

These were exceptions selected after the ordinary temporary-patch review, not a change to the skill's default scope:

- **`MeshModificationData`:** extract the complete existing partial-update object, retaining the outer element/`meshData` wrapper. Creation data requires a polygon and has creation-specific settings, while response data has required read fields; neither is a substitute for the optional modification payload. This naming call originated in `66c7173250dfcdc2e7db836aeb8bcda3ad6b3109`, a generator naming curation commit.
- **`RevisionCustomSchemeEntry`:** name the existing required GUID-key/string-value pair while preserving the shared array and its `RevisionIssue`, `RevisionChange` and `LayoutInfo` consumers. The call originated in `451eb50e36e2567fcfe5b35df32f7226085c09b3` alongside the generation audit, avoiding the generated `RevisionCustomSchemeDatum` name; `653cf806` later reformatted it.

These two objects have independent schema-design value, though the previous inline forms were valid. Their local Permanent placement described the original naming motivation, not an inherent wire break. No local category change or retirement was made.

## Alternatives kept local

The nine generator-only hotlink/marker/status naming operations remain excluded from the ordinary upstream proposal. Their naming collisions do not establish a source-schema defect.

The user also selected the `Hole2D` and `TextData` conditional naming calls for review and agreed to keep them local. Both originated with `name_required_variants` in client commit `20a5db740cd536889499173458e807553eaea8d4` to prevent numeric suffixes. Unlike extraction of a complete object, this helper distributes all common constraints into two fully named branches, duplicating the common properties.

| Contract | One content form | Both forms | Neither form |
| --- | --- | --- | --- |
| `Hole2D`, `oneOf` | Accept valid outline or legacy coordinates | Reject | Reject |
| Text creation, `anyOf`, with valid `coordinate` | Accept valid text or runs | Accept; runs take precedence | Reject |

For the inspected required-only branches, distributing common constraints across the unchanged union preserves acceptance. Changing the text union to `oneOf`, excluding its other optional content field, relaxing the hole union to `anyOf`, or dropping common validation would not. Naming the branches improves generated identifiers but duplicates source maintenance. A different composition design would need separate validator/renderer/generator review, especially around closed objects. See [JSON Schema combination](https://json-schema.org/understanding-json-schema/reference/combining) and [closed-object composition](https://json-schema.org/understanding-json-schema/reference/object#extending-closed-schemas).

## Validation and compatibility

- Interpreted both final-base and proposed C++ schemas in memory using Tapir's documentation tooling: **312 commands**, **533 → 537 common definitions**. No generated docs were written.
- Across the full rebased proposal, selectively unfolded only changed nonrecursive references, rejected validation siblings at replaced sites and compared complete command metadata/schemas and existing definitions while ignoring only `title`/`description`. **No acceptance change**: fields, requiredness, additional properties, bounds, enum order and union branches match. All references resolve; all four added names are unique.
- Nine commands change reference layout. Existing common changes are `WallDetails`, `RevisionCustomSchemeData`, and description-only `LinkToSettings`. `Hole2D` and the full `CreateTexts` command match the final baseline exactly.
- The older extraction commit separately reproduces the previous mesh input and revision contracts exactly after unfolding its two references, including all annotations.
- The four selected Permanent-helper transformations were also checked against **150 validator cases**: 35 holes, 99 text, seven revision arrays and nine mesh wrappers. Results matched, including malformed optional fields, both/neither forms, missing requirements, bounds and extra fields. This supports the structural argument; it is not exhaustive execution coverage.
- Executed the actual renderer resolver for five story-link contexts and both older extracted definitions. Descriptions survive without mutating definitions or leaking caller context. Reviewed source changes and ran `git diff --check`.
- **Limits:** no SDK build or live Archicad test. No command execution logic changed. Checks establish source-schema equivalence and description resolution, not live behavior.

Other generators can rename or consolidate public classes when inline objects become named. Therefore the guarantee is unchanged JSON acceptance, not universal generated-SDK source compatibility. MultiConn already uses these destination names, so no new aliases are needed. Keep all corresponding local calls until later released documentation confirms the definitions and their consumers. The mesh wrapper extraction remains separate; loud stale-target guards must remain.

If conditional naming is reconsidered later, preserve `Hole2D` as the public union. Text's local `TextData` extraction currently targets an inline creation item; if upstream introduces a named parent reference, retire that earlier extraction as well as the conditional helper. Otherwise its stale-target guard will correctly fail.

## Retained descriptions

Two changed references retain descriptions alongside the shared `LinkToSettings` object description. `ModifyWalls` uses only the reference. The actual strings and locations are:

`CommonSchemaDefinitions.json`, `LinkToSettings/description`:

> Mode of linking an element to its home story.

`CommonSchemaDefinitions.json`, `LinkToSettings/newCreationMode/description`:

> Controls home-story selection during element creation. If true, homeStoryDifference selects the home story relative to the current story and the element's absolute floor index is ignored. If false, the absolute floor index is used and Archicad fills homeStoryDifference. This is a creation instruction, not a persistent linking mode.

`ExtendedElementCommands.cpp`, `CreateWallsParameters/wallsData/items/linkToSettings/description`:

> When newCreationMode is true, homeStoryDifference overrides the home story selected by floorIndex or derived from zCoordinate.

`CommonSchemaDefinitions.json`, `WallDetails/linkToSettings/description`:

> newCreationMode is expected to read back as false after creation; Archicad resolves the relative story selection to an absolute floor index.

The slab caller preserves its default/favorite description, but its enum definition has no description. Mesh's generic description moves onto its definition with no duplicate at the reference. Beam and revision objects add no double-description cases.

## Submitted PR text

Title: **Refine API schemas following Tapir 1.7.1**

```markdown
This PR introduces named schemas for distinct payloads and reuses shared definitions where commands describe the same contract.

| Area | Changes |
|---|---|
| Beam holes | Introduces `BeamHoleModification` and reuses `BeamHoleType`. Keeps modification inputs separate from read results, which include `holeId` and have different dimensional constraints. |
| Slab creation | Reuses `SlabStructureType`, preserving the rules for selecting a structure from supplied attributes, tool defaults or favorites. |
| Wall story links | Reuses `LinkToSettings`. Explains creation-time behavior on `newCreationMode`, with only placement and readback details retained at the relevant callers. |
| Teamwork reservations | Shares `User` across four reservation/status responses and enables access to common definitions in those commands. |
| Mesh modification | Introduces `MeshModificationData` for partial updates, preserving the existing wrapper and the distinction between omitted and supplied fields. |
| Revision custom schemes | Introduces `RevisionCustomSchemeEntry` for individual key/value pairs within the existing shared array. |

The mesh and revision extractions address older naming gaps. The remaining changes follow the Tapir 1.7.1 schema review.

Fields, requiredness, constraints and accepted JSON payloads remain unchanged. Generated clients may consolidate or rename previously inline types when adopting the named definitions.
```

## Skill review after first use

Excluding the two explicitly selected older extractions, the skill matched the core work: investigate current source instead of stale docs, avoid merged proposals, preserve request/read distinctions, check common-definition access, validate acceptance and defer retirement until release adoption. The effective scope was the ten temporary operations, with no remaining breaking source-review decisions.

The first run exposed workflow friction rather than an incorrect contract result:

- The initial endpoint was local preparation; the preferred endpoint is a validated branch pushed to the fork. Future actionable runs now sync the fork without force, publish by default, and leave PR submission to the user. Explicit review/local-only requests remain narrower.
- Preserving every old sentence initially left field-level creation instructions on parent references. The skill now puts general behavior on the actual shared field and retains only unique caller facts.
- The preferred title is version-based, broad enough for naming, reuse, union restructuring or corrections. New branches use `schema/refinements-<version>` without `codex/`. PR bodies use descriptive tables/bullets and are returned as fenced raw Markdown.
- Three phase-specific reports and a long retired-patch inventory duplicated state. Future runs maintain one report across follow-ups and an active-only tracking queue. Git and the generation reports retain history. Intermediate artifacts do not become durable documentation.

No generalized rule to upstream Permanent patches was added. The two exceptions remain decisions of this run, not evidence that the default exclusion was ineffective.
