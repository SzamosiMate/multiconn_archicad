# Active Tapir schema refinements

Client release: **Tapir 1.8.0**. Released documentation checked: **2026-11-02**. This file contains open sharing candidates awaiting released documentation. Remove an entry only after the fetched release contains equivalent definitions and references; historical decisions remain in reports and Git.

## Classification assignment response correction — 2026-11-01

One Breaking source-review correction changes `ClassificationIdOrError/oneOf/0`
from `ClassificationIdArrayItem` to `ClassificationId`. Element and element-default
assignment reads return direct `classificationSystemId` / `classificationItemId`
fields in `classificationIds`, without a `classificationId` wrapper. Source and
earlier live AC27/Tapir 1.7.3 element reads confirm that direct shape.

Published separately as commit [`72bf361f`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/72bf361f07e4b34200ea2067a89202095ac9ea2c)
on [`schema/refinements-1.8.0`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.8.0), now submitted by the user as [PR #1754](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1754).
The correction is a breaking schema/generated-client change; execution is unchanged.
Retain it until fetched release documentation corrects the element success branch.
Preserve `ClassificationIdArrayItem` for its remaining wrapped consumers.

**Attribute exception found in the 2026-11-03 source review:**
`GetClassificationOfAttributesInSystem` explicitly returns wrapped `classificationId`
successes. The upstream proposal gives that result a separate wrapped/error union,
preserving its existing wire shape. The current downstream global patch also
flattens this consumer, which is incorrect. Reconcile this separately during client
release adoption; no patch implementation, model or adapter was changed by this
upstream run. Do not treat the attribute consumer as evidence for a direct shape.

The [single 1.8.0 run report](reports/upstream-patches/upstream-refinements-1.8.0-2026-11-03.md)
records SDK/source evidence, validation and compatibility consequences. A source
merge alone does not retire any client operation.

## Classification assignment response correction — 2026-11-01

One Breaking source-review correction now changes the success branch of
`ClassificationIdOrError` from `ClassificationIdArrayItem` to `ClassificationId`.
`GetClassificationsOfElements` and `GetClassificationsOfElementDefaults` return
direct `classificationSystemId` / `classificationItemId` fields inside
`classificationIds`, without a `classificationId` wrapper. The released 1.7.3
documentation reference is incorrect. The source in `ClassificationCommands.cpp`
and live element-assignment reads on Archicad 27/Tapir 1.7.3 confirm the direct
shape. It is assigned to `apply_breaking_source_review_patches` at the user's
request, for upstream submission in the next release cycle. No second accepted
shape or compatibility adapter is added.

Keep this correction until the fetched release schema uses `ClassificationId` at
the success branch. The existing named `ClassificationIdArrayItem` remains for
its other consumers. Prior naming/sharing counts below describe their original
review batches; this correction is additional to those inventories. Regeneration,
strict audit, reproducibility and the live classification-utility read passed.

## Retained naming and sharing candidates from 1.7.2

**Submitted as [PR #1386](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1386); still open and unmerged, updated and checked 2026-11-04.** The retained older decisions in this section are tracked against [`schema/refinements-1.7.2`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.7.2), commit [`e72078d2`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/e72078d2440e70f57fbedfe6d861bc40b18acbdf), merged with upstream `173e4fa0fdd37653a55832b5a1ad8423196e2082`. Text creation variants, marker readback and MEP preference-table rows were deferred during the rebase; reassess those against the 1.7.4 release documentation before deciding on any new upstream proposal or client patch retirement. See the [single run report](reports/upstream-patches/upstream-refinements-1.7.2-2026-10-20.md) for source rationale, compatibility evidence and copyable PR text. The 1.7.3 proposal below remains independent.

Original retained inventory before the 2026-11-02 rebase: **80 expanded Temporary helper operations**: 58 naming/conditional-variant operations and 22 shared-reference replacements. This includes 70 operations introduced for 1.7.2 and ten older operations (eight hotlink/status/marker names plus two conditional-variant names). Tapir 1.7.3 retires the graphic-rule readback and marker-parameter item extractions, adopting `GraphicOverrideRule` and `StoredGDLParameter` with old Python names retained as compatibility aliases. The latter also relaxes requiredness of `value`; all previous payloads remain accepted. See the [1.7.3 report](reports/codegen/tapir-1.7.3.md#removed-patches).

All new schema-specific names outside the established creation/modification lists are Temporary. The original source review found equivalent contracts for the older queue at its then-current baseline; the rebased fork retains the applicable client destination names and defers the changed contracts listed above. Released equivalent definitions/references allow retirement; when upstream chooses different names, review equivalence and retain old Python names as compatibility aliases where needed. The actual `Hole2D` and `TextData` conditional calls were already in `apply_temporary_patches` at 1.7.3 preflight; the previous tracking placement note was stale. No category was moved in this update. Keep loud missing-target/existing-reference guards. Valid inline schemas are not inherently defective; these entries record the desired naming convergence. The [condensed generation record](reports/codegen/tapir-1.7.2.md#temporary) preserves the decisions; full historical source paths and consumer differences remain at `776808e:code_generation/documentation/reports/codegen/tapir-1.7.2.md` in Git. The tables below own the active retirement scope.

### Naming and conditional variants (58 operations)

| Decision | Operations | Retirement scope |
| --- | ---: | --- |
| Response and rename item names | 6 | Graphic override combination reads, grid reads, three design-option rename payloads and legacy graphical-rule reads use equivalent named item definitions. Graphic-rule readback retired in 1.7.3. |
| Geometry, quantities, projection and MEP result details | 11 | Body polygon/hole shapes, element geometry/quantity success branches and components, axonometric projection settings, three fitting-table rows and two MEP ID success wrappers use equivalent named definitions. |
| Grid parameter shapes and length-mode enum | 3 | Creation parameter item, readback parameter item and creation length mode have equivalent named definitions; preserve read/write differences. |
| Image saving enums | 2 | Released image format and color-depth fields reference equivalent named enums. |
| Curtain-wall pattern scalars | 2 | Released size/index items use equivalent named constrained definitions. |
| Active graphical-override conditional selection | 1 | Released ID/name alternatives have equivalent named variants; preserve the conditional union. |
| Criterion enums and structured operands | 20 | The 15 positive criterion enum definitions and five structured operands have equivalent named definitions; preserve values and operator field types. |
| Shared electrical setting/text-frame producers | 3 | Read wiring/load-classification items and read text-frame shape have equivalent named definitions. Their reference consumers are counted in the next table. |
| Retained hotlink/status/marker naming | 8 | Equivalent released named payloads, status enum and marker variants replace the retained operations; exact paths remain in the [1.7.1 report](reports/codegen/tapir-1.7.1.md#permanent). The marker parameter item extraction retired in 1.7.3. |
| Retained Hole2D/TextData conditional variant naming | 2 | Equivalent released named outline/legacy-coordinate and text/runs variants replace `name_required_variants` at `Hole2D` and `TextData`. Preserve branch fields and requiredness. |

### Shared-reference replacements (22 operations)

Paths below are original upstream paths using the patch helpers' shorthand. Extraction producers and reference consumers now run together in Temporary, with producers first.

| Decision | Operations | Original paths and retirement condition |
| --- | ---: | --- |
| Share electrical project setting items | 2 | `GetElectricalProjectSettingsResult/wiringTypes/items` and `ModifyElectricalProjectSettingsParameters/wiringTypesToAdd/items` share equivalent `ElectricalWiringType`; read `/loadClassifications/items` and modify `/loadClassificationsToAdd/items` share equivalent `ElectricalLoadClassification`. Preserve required name/value fields and bounds. |
| Share grid read/default parameter details | 1 | `GetGridElementsResult/gridElements/items/parameters/items` and `GetGridElementDefaultsResult/parameters/items` share equivalent `GridParameterDetails`. Preserve required name/displayName/type, optional value/dimensions, and additional-property behavior. Keep the creation parameter contract separate. |
| Reuse legacy graphical-override color | 1 | `CreateGraphicalOverrideRuleParameters/surfaceRGB` references equivalent `ColorRGB`, preserving its contextual description and required RGB numbers. Do not invent numeric bounds. |
| Reuse active graphical-override combination identity | 3 | Original `GetActiveGraphicalOverrideCombinationResult/combinationId` and `SetActiveGraphicalOverrideCombinationParameters/combinationId` reference equivalent `GraphicOverrideCombinationId`. Three local operations cover readback and the two conditional input variants; retain selection requiredness and union behavior. |
| Share criterion comparison enums | 14 | In `GraphicOverrideCriterion`, `wallComplexityNot`, `wallGeometryTypeNot`, `columnCoatingTypeNot`, `slabEdgeAngleNot`, `roofCutBodyTypeNot`, `roofEdgeAngleNot`, `roofGeometryTypeNot`, `penReplacementNot`, `structuralFunctionNot`, `positionNot` share their corresponding positive-operator enums (local names have `GraphicOverride` prefixes). `wallReferenceLinePosition`/`wallReferenceLinePositionNot` reference equivalent `WallReferenceLineLocation`; `slabReferencePlaneLocation`/`slabReferencePlaneLocationNot` reference equivalent `SlabReferencePlaneLocation`. Preserve all accepted values and optionality; do not conflate filtering/editing enums with different spellings. |
| Share text-frame shape enum | 1 | `TextStyleDetails/textFrameShape` and `TextStyleSettableDetails/textFrameShape` reference equivalent `TextFrameShape`, preserving the existing Python enum name and all four values. |

## Source-reviewed 1.7.3 refinements

**Original 1.7.3 review: 161 expanded Temporary operations, including 159 originally submitted in [PR #1557](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1557), two deferred pending definitions in #1386.** The published branch is [`schema/refinements-1.7.3`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.7.3), commit [`6729a322`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/6729a322353207b3b2c965dd226224b908340592), merged with upstream `173e4fa0fdd37653a55832b5a1ad8423196e2082`. Its original scope yielded 133 named definitions; the rebased proposal retains 92 after deferring changed contracts. Text measurement, group user data, opening schemas, library-part scripts and project preference pages remain in the client queue and should be reassessed against the 1.7.4 release documentation. Three further equivalent format references in `GetCalculationUnits` extend meaningful reuse without adding client patch operations. See the [single run report](reports/upstream-patches/upstream-refinements-1.7.3-2026-10-26.md) for source decisions and validation.

The [condensed 1.7.3 generation record](reports/codegen/tapir-1.7.3.md#temporary) preserves the decisions; exact historical calls and consumer paths remain at `776808e:code_generation/documentation/reports/codegen/tapir-1.7.3.md` in Git and active calls remain in `code_generation/shared/schema_patching.py`. The original proposal passed source interpretation, a complete structural comparison and an AC29 Debug SDK build at its original baseline. The rebased proposal passed a new structural comparison and renderer checks against `d3bc733d`; it has not received a new SDK build. The rebased proposal covers database selection, element-detail success naming, selected calculation-unit formats, 3D styles/cut planes, favorites, attribute/graphic-rule metadata, IFC fields, categories and relations, geometry/measurement results, project data, Teamwork and command-specific options. Read/update contracts remain separate when required fields differ. The original 133 names matched existing patched client names; no new compatibility alias was proposed. Reassess the retained and deferred names during release adoption.

### Deferred cross-batch references (two operations)

| Original path | Source/PR status and retirement condition |
| --- | --- |
| `GetFavoriteSettingsResult/favoriteSettings/items/oneOf/0/marker` (locally `FavoriteSettings/marker`) | Keep inline in #1557. The #1386 marker-readback extraction was deferred during rebase; reconsider reuse only after an equivalent definition with current `StoredGDLParameter` semantics is available. Preserve the caller description: "The marker stored with a Window or Door Favorite. Absent when the Favorite has no marker - that is not an error." The existing client replacement drops this annotation; its acceptance contract is equivalent, and no client implementation is changed by this upstream run. Retire only when released docs reference an equivalent marker contract. |
| `DeleteMEPPhysicalSystemsParameters/physicalSystems/items` | Keep inline in #1557. Its required `physicalSystemId` wrapper is equivalent to `MEPPhysicalSystemIdArrayItem`, proposed by #1386. Add the reference after that definition is available; retire only when released docs use it at this consumer. |

Retire each operation when released documentation supplies equivalent named definitions and references at all affected consumers, preserving requiredness, bounds, accepted enum values and union/error behavior. Producers must precede dependent references. If upstream chooses different names, preserve required existing Python imports through compatibility aliases. Existing source-reviewed candidates remain independently tracked above.

Final inventory: **241 Temporary operations** (80 retained + 161 new) and **82 Permanent operations** (80 retained + two MEP modification-item additions). No existing patch changes category; no new breaking patch or unresolved breaking source-review candidate is introduced. Wire-key support, alias constraint preservation and functional TypedDict cleanup are generator concerns, separate from these categories. Keep every active operation until equivalent definitions/references appear in released documentation.


## Tapir 1.8.0 naming and sharing additions — 2026-11-02

The released 1.8.0 documentation still has all existing patch targets, including
its incorrect `ClassificationIdOrError` success reference. Retain the existing
82 Permanent, 241 Temporary and one Breaking source-review operation; no existing
operation changes category or retires in this update. The classification correction
also reaches the new `GetClassificationOfAttributesInSystem` result through the
shared schema. The later upstream source review found that attribute consumer
requires a wrapped result; see the classification exception above. The generation
update itself did not inspect implementation source.

The update adds **18 Permanent creation/modification item extractions** in the
established lists and **370 Temporary helper operations**: 283 inline object/enum
or union-branch names, four conditional-variant naming calls, and 83 shared
references. The active inventory is **100 Permanent + 611 Temporary + one Breaking
source-review operation**; counts expand loops, and each conditional-variant call
counts once rather than once per emitted definition. There are no Breaking
permanent additions or classification-only changes.

Retirement scope for the new Temporary operations is the exact producer and
consumer paths in [`apply_temporary_patches`](../shared/schema_patching.py), after
the 1.7.3 preference-page operations. Released documentation must provide equivalent
named definitions and reference each affected consumer, preserving fields,
requiredness, constraints, accepted enum values and union/error alternatives.
The creation/modification list additions remain Permanent. Naming-only refinements
are candidates for a separate upstream-patches run; none was submitted by this run.

- Replace generic/path-derived names, keeping domain context: analytical settings,
  geometries and success branches; viewpoint, library, property, element and MEP
  contracts; opening symbol/extrusion/floor-plan enums; and user-data keys. These
  include distinct dimension-standard formats instead of displacing `Level` or
  sharing preference formats with different fields, and `ElementUnmergePair`
  instead of displacing the existing trimming `ElementPair`.
- Name conditional alternatives at `FindModelViewOptionParameters`,
  `SetActiveRenovationFilterParameters`, `LibraryPartScriptData` and
  `TextMeasurementData`. Retire only with equivalent named alternatives retaining
  the release's `oneOf`/`anyOf` and required-field behavior.
- Share equivalent read/write/reference contracts for viewpoint IDs, MEP row keys
  and values, opening updates, drawing primitives, user-data keys, and existing
  color/bounding-box/partial-display contracts. Keep differing requiredness,
  dimensions, identifier formats, bounds and read/write payloads separate; source
  calls own the complete paths and canonical destination names.

See the [condensed 1.8.0 record](reports/codegen/tapir-1.8.0.md) for compatibility
consequences and generator decisions. The older batch descriptions above retain
their stated historical baselines; their open release-adoption conditions remain
applicable to the fetched 1.8.0 documentation.

### Published independent 1.8.0 proposal — 2026-11-03

Submitted by the user as [PR #1754](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1754). Published branch
[`schema/refinements-1.8.0`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.8.0)
now has tip [`383346e4`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/383346e4847d78346d7ae58067790f7298a22123).
It contains **341 of the 370 new Temporary operations**, yielding **279 named
definitions**, plus the separate breaking classification commit above. The original
source baseline was `c4db2ade1fcfb40bedf81832ad4b5cd429d8504e`. The latest
update merged upstream `d780607b1597f9921135d5f48c0ee67daf5aca13`, refreshed the shared MEP and IFC definitions,
and updated the new drawing command to use the shared primitive schema.
The full schema comparison and AC29 SDK build passed again. The separate
classification commit remains intact. #1386 and #1557 remain outside this
branch's prerequisites. Their dependent operations stay deferred.

Retire the 341 published operations only after fetched released documentation
provides equivalent definitions/references at their producer and consumer paths
in `apply_temporary_patches`. All 279 names match the patched released client;
no new alias is currently needed, subject to actual release-adoption review.
Preserve loud guards and every current client operation in the meantime.

**29 operations remain deferred** because a parent or reference definition is
absent from main. Some prerequisites are in the pending earlier PRs; opening,
library-script and text-measurement parents were already deferred from those PRs.
Do not silently publish their consumers or copy the earlier batches into this
branch. Reassess after equivalent prerequisites are available. The original paths
below trace through local creation-item and earlier temporary extractions.

| Deferred operation | Original path | Missing prerequisite(s) |
| --- | --- | --- |
| `extract_inline_enum` | `SetLibraryPartScriptsParameters/properties/libraryParts/items/properties/deleteScripts/items` | `LibraryPartScriptData` |
| `extract_inline_enum` | `GetOpeningDefaultResult/properties/floorPlanParameters/properties/floorPlanDisplayMode` | `OpeningDefaultFloorPlanParameters` |
| `extract_inline_enum` | `GetOpeningDefaultResult/properties/floorPlanParameters/properties/dividedOpeningMode` | `OpeningDefaultFloorPlanParameters` |
| `extract_inline_enum` | `GetOpeningDefaultResult/properties/floorPlanParameters/properties/openEdgeStyle` | `OpeningDefaultFloorPlanParameters` |
| `extract_inline_enum` | `GetOpeningDetailsResult/properties/openings/items/oneOf/0/properties/extrusionParameters/properties/constraint` | `OpeningExtrusionParameters` |
| `extract_inline_enum` | `GetOpeningDetailsResult/properties/openings/items/oneOf/0/properties/extrusionParameters/properties/limitType` | `OpeningExtrusionParameters` |
| `extract_inline_enum` | `GetOpeningDetailsResult/properties/openings/items/oneOf/0/properties/extrusionParameters/properties/linkedStatus` | `OpeningExtrusionParameters` |
| `extract_inline_enum` | `GetOpeningDetailsResult/properties/openings/items/oneOf/0/properties/extrusionParameters/properties/shapeType` | `OpeningExtrusionParameters` |
| `replace_inline_schema_with_ref` | `BreakHotlinkNodesParameters/properties/hotlinkNodes/items` | `HotlinkNodeReference` |
| `replace_inline_schema_with_ref` | `DeleteHotlinkNodesParameters/properties/hotlinkNodes/items` | `HotlinkNodeReference` |
| `replace_inline_schema_with_ref` | `GetDimensionStandardsResult/properties/dimensionStandards/items/properties/settings/properties/area` | `AreaDimensionFormat` |
| `replace_inline_schema_with_ref` | `GetHotlinkDesignOptionTableDetailsParameters/properties/hotlinkNodes/items` | `HotlinkNodeReference` |
| `replace_inline_schema_with_ref` | `GetVisibleSkinStatusParameters/properties/structureDisplay` | `PartialStructureDisplay` |
| `replace_inline_schema_with_ref` | `SetOpeningDetailsParameters/properties/openingsWithDetails/items/properties/extrusionParameters/properties/constraint` | `OpeningExtrusionParametersUpdate`, `OpeningConstraint` |
| `replace_inline_schema_with_ref` | `SetOpeningDetailsParameters/properties/openingsWithDetails/items/properties/extrusionParameters/properties/limitType` | `OpeningExtrusionParametersUpdate`, `OpeningLimitType` |
| `replace_inline_schema_with_ref` | `SetOpeningDetailsParameters/properties/openingsWithDetails/items/properties/extrusionParameters/properties/linkedStatus` | `OpeningExtrusionParametersUpdate`, `OpeningLinkedStatus` |
| `replace_inline_schema_with_ref` | `SetOpeningDetailsParameters/properties/openingsWithDetails/items/properties/extrusionParameters/properties/shapeType` | `OpeningExtrusionParametersUpdate`, `OpeningShapeType` |
| `replace_inline_schema_with_ref` | `GetOpeningFloorPlanParametersResult/properties/openings/items/oneOf/0/properties/floorPlanParameters/properties/floorPlanDisplayMode` | `OpeningFloorPlanParameters`, `OpeningFloorPlanDisplayMode` |
| `replace_inline_schema_with_ref` | `GetOpeningFloorPlanParametersResult/properties/openings/items/oneOf/0/properties/floorPlanParameters/properties/dividedOpeningMode` | `OpeningFloorPlanParameters`, `OpeningDividedMode` |
| `replace_inline_schema_with_ref` | `GetOpeningFloorPlanParametersResult/properties/openings/items/oneOf/0/properties/floorPlanParameters/properties/openEdgeStyle` | `OpeningFloorPlanParameters`, `OpeningEdgeStyle` |
| `replace_inline_schema_with_ref` | `SetOpeningFloorPlanParametersParameters/properties/openingsWithFloorPlanParameters/items/properties/floorPlanParameters/properties/floorPlanDisplayMode` | `OpeningFloorPlanParametersUpdate`, `OpeningFloorPlanDisplayMode` |
| `replace_inline_schema_with_ref` | `SetOpeningFloorPlanParametersParameters/properties/openingsWithFloorPlanParameters/items/properties/floorPlanParameters/properties/dividedOpeningMode` | `OpeningFloorPlanParametersUpdate`, `OpeningDividedMode` |
| `replace_inline_schema_with_ref` | `SetOpeningFloorPlanParametersParameters/properties/openingsWithFloorPlanParameters/items/properties/floorPlanParameters/properties/openEdgeStyle` | `OpeningFloorPlanParametersUpdate`, `OpeningEdgeStyle` |
| `replace_inline_schema_with_ref` | `PlaceOpeningsParameters/properties/openingsData/items/properties/extrusionParameters` | `OpeningExtrusionParametersUpdate` |
| `replace_inline_schema_with_ref` | `PlaceOpeningsParameters/properties/openingsData/items/properties/floorPlanParameters` | `OpeningFloorPlanParametersUpdate` |
| `name_required_variants` | `SetLibraryPartScriptsParameters/properties/libraryParts/items` | `LibraryPartScriptData` |
| `name_required_variants` | `MeasureTextsParameters/properties/texts/items` | `TextMeasurementData` |
| `replace_inline_schema_with_ref` | `SetOpeningDefaultParameters/properties/extrusionParameters` | `OpeningExtrusionParametersUpdate` |
| `replace_inline_schema_with_ref` | `SetOpeningDefaultParameters/properties/floorPlanParameters` | `OpeningFloorPlanParametersUpdate` |

The [single run report](reports/upstream-patches/upstream-refinements-1.8.0-2026-11-03.md) records implementation decisions, the classification exception, full validation and copyable PR text.
