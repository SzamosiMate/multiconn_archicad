# Active Tapir schema refinements

Client release: **Tapir 1.7.2**. Released documentation checked: **2026-10-19**. This file contains open sharing candidates awaiting released documentation. Remove an entry only after the fetched release contains equivalent definitions and references; historical decisions remain in reports and Git.

## Active naming and sharing candidates following 1.7.2

**Published to the fork; awaiting user PR submission.** All decisions below are covered by [`schema/refinements-1.7.2`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.7.2), commit [`e7bcf0bb`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/e7bcf0bb6aad030333239d3b7052485c20967e9c), based on upstream `8c607d93c94200ed69496fae145c9aed53810f4d`. No PR was created. See the [single run report](reports/upstream-refinements-1.7.2-2026-10-20.md) for source rationale, compatibility evidence and copyable PR text.

Active inventory: **82 expanded Temporary helper operations**: 60 naming/conditional-variant operations and 22 shared-reference replacements. This includes 71 new 1.7.2 operations and 11 retained operations (nine hotlink/status/marker names plus two conditional-variant names). The established creation/modification lists retain 80 Permanent operations.

All new schema-specific names outside those lists are Temporary. Source review confirms equivalent contracts for the whole queue; the fork retains current client destination names, so no additional compatibility aliases are anticipated. Placement discrepancy: the actual `Hole2D` and `TextData` conditional calls still run at the end of `apply_permanent_patches`, despite their Temporary classification in the report/queue. They are explicitly included here; this run leaves client implementation unchanged. Later release retirement must remove their actual calls. Released equivalent definitions/references allow retirement; when upstream chooses different names, review equivalence and retain old Python names as compatibility aliases where needed. Keep loud missing-target/existing-reference guards. Valid inline schemas are not inherently defective; these entries record the desired naming convergence. Exact source paths, consumer differences and patch decisions are in the [generation report](reports/tapir-1.7.2.md#temporary).

### Naming and conditional variants (60 operations)

| Decision | Operations | Retirement scope |
| --- | ---: | --- |
| Response and rename item names | 7 | Graphic override combination/rule reads, grid reads, three design-option rename payloads and legacy graphical-rule reads use equivalent named item definitions. |
| Geometry, quantities, projection and MEP result details | 11 | Body polygon/hole shapes, element geometry/quantity success branches and components, axonometric projection settings, three fitting-table rows and two MEP ID success wrappers use equivalent named definitions. |
| Grid parameter shapes and length-mode enum | 3 | Creation parameter item, readback parameter item and creation length mode have equivalent named definitions; preserve read/write differences. |
| Image saving enums | 2 | Released image format and color-depth fields reference equivalent named enums. |
| Curtain-wall pattern scalars | 2 | Released size/index items use equivalent named constrained definitions. |
| Active graphical-override conditional selection | 1 | Released ID/name alternatives have equivalent named variants; preserve the conditional union. |
| Criterion enums and structured operands | 20 | The 15 positive criterion enum definitions and five structured operands have equivalent named definitions; preserve values and operator field types. |
| Shared electrical setting/text-frame producers | 3 | Read wiring/load-classification items and read text-frame shape have equivalent named definitions. Their reference consumers are counted in the next table. |
| Retained hotlink/status/marker naming | 9 | Equivalent released named payloads, status enum and marker variants/details replace the retained operations; exact paths remain in the [1.7.1 report](reports/tapir-1.7.1.md#permanent). |
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

No unresolved breaking source-review candidates remain. Keyword support, alias constraint preservation and functional TypedDict cleanup are generator implementation concerns, separate from these schema-patch classifications. The creation/modification naming lists retain their established Permanent exception. All queued candidates now have source-reviewed, published refinements. Keep every operation until equivalent definitions/references appear in released documentation; retirement belongs to a later release-codegen run.
