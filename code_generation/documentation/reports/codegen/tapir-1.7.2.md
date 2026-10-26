## Tapir generation report

**Result:** Ready for human review · **Tapir:** 1.7.1 → 1.7.2  
**Checked-in baseline:** `8e051ec8a182116fb2153ecdc2695acc8653be12`  
**Inputs:** The two documentation schemas fetched from the upstream `1.7.2` tag. Initial tracked outputs matched HEAD; unrelated untracked files were preserved. No implementation source was inspected.

### API change summary

Counts ignore descriptions, ordering, and equivalent reference factoring. Existing model changes include dependencies; new public names include aliases. The previous client API is the checked-in 1.7.1 API, without the working-tree discrepancies documented in the preceding release report.

- **Commands:** 46 added: `ConnectToElectricalCircuits`, `CreateCurtainWalls`, `CreateElectricalCircuits`, `CreateElectricalDevices`, `CreateElectricalPanels`, `CreateGraphicOverrideCombinations`, `CreateGraphicOverrideRules`, `CreateGraphicalOverrideCombination`, `CreateGraphicalOverrideRule`, `CreateGridElements`, `CreateLevelDimensions`, `CreateMEPPhysicalSystems`, `CreateMEPSystemGroups`, `DeleteDesignOptionCombinations`, `DeleteDesignOptionSets`, `DeleteDesignOptions`, `DeleteElectricalCircuits`, `DeleteGraphicOverrideCombinations`, `DeleteGraphicOverrideRuleGroups`, `DeleteGraphicOverrideRules`, `Get3DGeometryOfElements`, `Get3DProjectionSettings`, `GetActiveGraphicalOverrideCombination`, `GetElectricalCircuits`, `GetElectricalDevices`, `GetElectricalPanels`, `GetElectricalProjectSettings`, `GetGraphicOverrideCombinations`, `GetGraphicOverrideRuleGroups`, `GetGraphicOverrideRules`, `GetGraphicalOverrideRules`, `GetGridElementDefaults`, `GetGridElements`, `GetMEPSystemGroups`, `GetQuantitiesOfElements`, `ModifyElectricalCircuits`, `ModifyElectricalDevices`, `ModifyElectricalPanels`, `ModifyElectricalProjectSettings`, `ModifyGraphicOverrideRules`, `RenameDesignOptionCombinations`, `RenameDesignOptionSets`, `RenameDesignOptions`, `SaveCurrentWindowAsImage`, `Set3DProjectionSettings`, `SetActiveGraphicalOverrideCombination`. None removed. 21 released command contracts change: `CloneProjectMapItemToViewMap`, `CreateColumns`, `CreateDoors`, `CreateLabels`, `CreateLayout`, `CreateMEPRoutingElements`, `CreateMeshes`, `CreateMorphs`, `CreateTexts`, `CreateViewsInViewMap`, `CreateWindows`, `ExportFavorites`, `GetDetailsOfElements`, `GetMEPElements`, `GetMEPPreferenceTables`, `GetViewSettings`, `ModifyLabels`, `ModifyTexts`, `RenameNavigatorItem`, `SaveProject`, `SetViewSettings`. Cleaner repairs additionally restore existing validation on `GetAutoTextName` and `HighlightElements`, making **23 affected existing commands**.
- **Public type models:** **176 names added**, none removed: 119 release/naming models and 57 newly emitted aliases for existing schemas, enumerated below. **25 existing type contracts change directly or through dependencies:** `AutoTextKeyValue`, `ColumnData`, `DetailsOfElement`, `DoorData`, `HighlightedColor`, `LabelData`, `LabelDetails`, `LabelSymbolStyleSettableDetails`, `LayoutData`, `MEPElement`, `MEPElementType`, `MEPRoutingElementData`, `MeshData`, `MorphData`, `TextData`, `TextDataWithRuns`, `TextDataWithText`, `TextDetails`, `TextRunDetails`, `TextStyleDetails`, `TextStyleSettableDetails`, `ViewCloneData`, `ViewData`, `ViewSettings`, `WindowData`. Of these, 20 generated declarations change directly. Annotation-only `Field` changes and descriptions are excluded.
- **Command models:** 85 names added, none removed; four declarations change directly (`ExportFavoritesResult`, `GetMEPPreferenceTablesParameters`, `GetMEPPreferenceTablesResult`, `RenameNavigatorItemParameters`). Expanded schemas change 22 existing command-model contracts; the two restored alias constraints affect two further parameter models.
- **Unified API:** 46 methods added, none removed; **8 methods have compatibility changes**, detailed below. Existing top-level method syntax changes only for `export_favorites`, `get_mep_preference_tables`, `rename_navigator_item`, and `save_project`; referenced models account for the other breaks.
- **Patches, expanded helper operations:** 15 new Permanent operations extend the creation/modification lists; 71 new Temporary operations cover every other new name or shared-schema/enum refinement. Retired 2 Permanent and 10 Temporary operations. Two older conditional-variant naming operations move Permanent → Temporary; the nine existing hotlink/status/marker naming operations remain Temporary as in the checked-in source. Final inventory: **80 Permanent + 82 Temporary**. All 76 retained baseline operations preserve generated behavior; classification counts exclude retired operations and distinguish the two reclassifications from new work. No breaking-permanent or source-review patches.

<details>
<summary>Added public type names (119 release/naming models)</summary>

`ActiveGraphicalOverrideCombinationById`, `ActiveGraphicalOverrideCombinationByName`, `AxonometricProjectionParameters`, `BeamQuantities`, `BeamSegmentQuantities`, `Body3D`, `Body3DPolygon`, `Body3DPolygonHole`, `ColumnQuantities`, `ColumnSegmentQuantities`, `CurtainWallCrossingFrameType`, `CurtainWallData`, `CurtainWallFlexibleIndex`, `CurtainWallPattern`, `CurtainWallPatternCell`, `CurtainWallPatternLogic`, `CurtainWallPatternOrigin`, `CurtainWallPatternSize`, `DesignOptionCombinationRename`, `DesignOptionRename`, `DesignOptionSetId`, `DesignOptionSetIdArrayItem`, `DesignOptionSetRename`, `DimensionOrigin`, `ElectricalCircuitConnectionData`, `ElectricalCircuitData`, `ElectricalCircuitDetails`, `ElectricalCircuitDetailsOrError`, `ElectricalCircuitModificationData`, `ElectricalDeviceData`, `ElectricalDeviceDetails`, `ElectricalDeviceDetailsOrError`, `ElectricalDeviceModificationData`, `ElectricalLoadClassification`, `ElectricalLoads`, `ElectricalPanelData`, `ElectricalPanelDetails`, `ElectricalPanelDetailsOrError`, `ElectricalPanelModificationData`, `ElectricalWiringType`, `ElementComponentQuantities`, `ElementGeometry3D`, `ElementQuantities`, `ElementQuantityDetails`, `GraphicOverrideColumnCoatingType`, `GraphicOverrideColumnCrossSectionType`, `GraphicOverrideCombinationData`, `GraphicOverrideCombinationDetails`, `GraphicOverrideCombinationId`, `GraphicOverrideCombinationIdArrayItem`, `GraphicOverrideCombinationIdOrError`, `GraphicOverrideCriterion`, `GraphicOverrideCustomPropertyBool`, `GraphicOverrideCustomPropertyInteger`, `GraphicOverrideCustomPropertyNumber`, `GraphicOverrideCustomPropertyString`, `GraphicOverrideElementType`, `GraphicOverrideFillTypes`, `GraphicOverridePenReplacement`, `GraphicOverridePosition`, `GraphicOverrideProfileParameter`, `GraphicOverrideRoofCutBodyType`, `GraphicOverrideRoofEaveOverhangType`, `GraphicOverrideRoofEdgeAngle`, `GraphicOverrideRoofGeometryType`, `GraphicOverrideRuleData`, `GraphicOverrideRuleDetails`, `GraphicOverrideRuleGroup`, `GraphicOverrideRuleId`, `GraphicOverrideRuleIdArrayItem`, `GraphicOverrideRuleIdOrError`, `GraphicOverrideRuleModificationData`, `GraphicOverrideShellCutBodyType`, `GraphicOverrideShellGeometryType`, `GraphicOverrideSlabEdgeAngle`, `GraphicOverrideStructuralFunction`, `GraphicOverrideStructureType`, `GraphicOverrideStyle`, `GraphicOverrideSurfaceTypes`, `GraphicOverrideWallComplexity`, `GraphicOverrideWallGeometryType`, `GraphicalOverrideRuleDetails`, `GridElementData`, `GridElementDetails`, `GridElementLengthMode`, `GridParameter`, `GridParameterDetails`, `ImageColorDepth`, `ImageFormat`, `LevelDimensionData`, `LevelDimensionDetails`, `MEPAngleSet`, `MEPBranchPreferenceTable`, `MEPBranchPreferenceTableRow`, `MEPElbowPreferenceTable`, `MEPElbowPreferenceTableRow`, `MEPOrientation`, `MEPPhysicalSystemData`, `MEPPhysicalSystemDetails`, `MEPPhysicalSystemDetailsOrError`, `MEPPhysicalSystemId`, `MEPPhysicalSystemIdArrayItem`, `MEPPhysicalSystemIdOrError`, `MEPReferenceSet`, `MEPSystemGroupData`, `MEPSystemGroupDetails`, `MEPSystemGroupDetailsOrError`, `MEPSystemGroupId`, `MEPSystemGroupIdArrayItem`, `MEPSystemGroupIdOrError`, `MEPTransitionPreferenceTable`, `MEPTransitionPreferenceTableRow`, `MorphQuantities`, `PerspectiveProjectionParameters`, `RoofQuantities`, `ShellQuantities`, `SlabQuantities`, `WallQuantities`, `ZoneQuantities`.

</details>

<details>
<summary>Newly emitted aliases for existing schemas (57)</summary>

`AttributeHeadersOrError`, `AttributeIdOrError`, `AutoTextNameOrError`, `BoundingBox3DOrError`, `BuildingMaterialAttributeOrError`, `ClassificationIdOrError`, `CompositeAttributeOrError`, `ConnectedElementsOrError`, `DatabaseIdOrError`, `DesignOptionCombinationIdOrError`, `DesignOptionIdOrError`, `DimensionDataOrError`, `ElementIFCIdsOrError`, `ElementIFCPropertiesOrError`, `ElementIFCTypeOrError`, `ElementIdOrError`, `ElementOrGroupId`, `ElementRelationsOrError`, `ElementTrimsOrError`, `ElementsOfDesignOptionOrError`, `ElementsWithExecutionResultsOrError`, `ElementsWrapperOrError`, `EnumValueId`, `ExecutionResult`, `FavoritesOrError`, `FillAttributeOrError`, `GroupIdOrError`, `HotlinkNodeCreatedOrError`, `KeynoteAutoTextTokensOrError`, `KeynoteFolderIdOrError`, `KeynoteItemIdOrError`, `LayerAttributeOrError`, `LayerCombinationAttributeOrError`, `LineAttributeOrError`, `MEPConnectionResultOrError`, `MEPElementPortsOrError`, `MEPRoutingElementDetailsOrError`, `MEPSystemAttributeOrError`, `NavigatorItemIdOrDatabaseIdAndWindowType`, `NavigatorItemIdOrError`, `NormalOrUserUndefinedPropertyValue`, `PenTableAttributeOrError`, `ProfileAttributeOrError`, `PropertyDefaultValue`, `PropertyIdOrError`, `PropertyValueDetails`, `PropertyValueOrErrorItem`, `RevisionChangesOfEntities`, `SpecialFolderPathOrError`, `SurfaceAttributeOrError`, `TypeSpecificDetails`, `TypeSpecificSettings`, `ViewSettingsOrError`, `ViewTransformationsOrError`, `ZoneBoundariesOrError`, `ZoneCategoryAttributeOrError`, `ZoneCreationGeometry`.

</details>

### Changes by patch category

#### Permanent

The user-reviewed exception is the established creation/modification item-naming pattern. The 11 new creation/connection entries now live in `creation_data_types`; the four modification entries live in `element_modification_datatypes`. They extend the existing lists rather than a separate mixed loop. No other 1.7.2 naming/extraction operations remain Permanent.

- **Electrical creation, modification, and connections.** Separate creation items require a panel or position; modifications require an element ID. Devices use `position` on creation and `anchorPoint` on modification/readback. Sharing these models would change requiredness. The connection payload identifies an element and its circuit. Exact source/destination pairs:

  ```python
  # Tuple entries consumed by extract_inline_schema(parent, [field, "items"], name).
  ("CreateElectricalCircuitsParameters", "electricalCircuitsData", "ElectricalCircuitData")
  ("CreateElectricalDevicesParameters", "electricalDevicesData", "ElectricalDeviceData")
  ("CreateElectricalPanelsParameters", "electricalPanelsData", "ElectricalPanelData")
  ("ModifyElectricalCircuitsParameters", "electricalCircuitsData", "ElectricalCircuitModificationData")
  ("ModifyElectricalDevicesParameters", "electricalDevicesData", "ElectricalDeviceModificationData")
  ("ModifyElectricalPanelsParameters", "electricalPanelsData", "ElectricalPanelModificationData")
  ("ConnectToElectricalCircuitsParameters", "connectionsData", "ElectricalCircuitConnectionData")
  ```

- **Level dimensions.** `CreateLevelDimensionsParameters/levelDimensionsData/items` becomes `LevelDimensionData`; it requires a position, unlike response `LevelDimensionDetails`, which requires reported measurements and display settings. Keep creation/readback separate.
- **MEP systems and groups.** `CreateMEPPhysicalSystemsParameters/physicalSystemsData/items` → `MEPPhysicalSystemData`, and `CreateMEPSystemGroupsParameters/systemGroupsData/items` → `MEPSystemGroupData`. These singular names remove `Datum`; physical-system creation requires a system group and name, while group creation requires a name.
- **Curtain-wall creation.** `CreateCurtainWallsParameters/curtainWallsData/items` becomes `CurtainWallData` in the creation list. Pattern scalar naming remains Temporary below.
- **Graphic override creation/modification.** The creation list extracts `CreateGraphicOverrideCombinationsParameters/graphicOverrideCombinations/items` as `GraphicOverrideCombinationData` and `CreateGraphicOverrideRulesParameters/graphicOverrideRules/items` as `GraphicOverrideRuleData`. The modification list extracts `ModifyGraphicOverrideRulesParameters/graphicOverrideRules/items` as `GraphicOverrideRuleModificationData`. Readback and legacy Graphical naming remain Temporary; their payloads differ.
- **Grid creation.** `CreateGridElementsParameters/gridElements/items` becomes `GridElementData` in the creation list. Readback, parameter details and enum naming remain Temporary.

#### Temporary

**82 expanded helper operations:** 60 naming/variant extractions and 22 shared-reference replacements. This includes 71 new operations for 1.7.2, nine retained hotlink/status/marker operations, and two older conditional-variant naming operations reclassified from Permanent. Every extraction introducing a name outside the established creation/modification lists is temporary, including generic-name fixes and shared-schema/enum producers.

Retire each extraction when released documentation supplies an equivalent named contract at the affected consumers. If upstream chooses a different name, review equivalence, adopt the upstream definition and retain the existing Python name through a compatibility alias where needed. Temporary does not mean silently accepting renamed or changed targets: all loud guards remain. Naming candidates do not by themselves assert that valid inline JSON Schema is defective.

- **Curtain-wall pattern scalars.** `CurtainWallPattern/sizes/items` → `CurtainWallPatternSize` and `/flexibleIndices/items` → `CurtainWallFlexibleIndex`, replacing `Size`/`FlexibleIndice`. Positive-size and nonnegative-index constraints remain. Retire when upstream names these items equivalently, retaining compatibility if it chooses different names.
- **Graphic override readback.** `GetGraphicOverrideCombinationsResult/graphicOverrideCombinations/items` → `GraphicOverrideCombinationDetails`, `GetGraphicOverrideRulesResult/graphicOverrideRules/items` → `GraphicOverrideRuleDetails`, and `GetGraphicalOverrideRulesResult/rules/items` → `GraphicalOverrideRuleDetails`. Preserve their required identity/XML/style differences; the legacy Graphical interface is distinct from the plural Graphic interface.
- **Grid readback and parameters.** `GetGridElementsResult/gridElements/items` → `GridElementDetails`; `GridElementData/parameters/items` → `GridParameter`; `GridElementDetails/parameters/items` → `GridParameterDetails`; `GridElementData/lengthMode` → `GridElementLengthMode`. Creation parameters require name/value; read/default parameters require name/displayName/type with optional value/dimensions. Do not merge these different contracts.
- **Design-option renames.** The array items at `RenameDesignOptionCombinationsParameters/designOptionCombinations/items`, `RenameDesignOptionSetsParameters/designOptionSets/items`, and `RenameDesignOptionsParameters/designOptions/items` become `DesignOptionCombinationRename`, `DesignOptionSetRename`, and `DesignOptionRename`. This prevents collision with existing readback `DesignOptionSet`. Combination/set renames require a name; an option may change its name or ID. Descriptive selection rules are not additional schema constraints.
- **3D body topology.** `Body3D/polygons/items` → `Body3DPolygon`; its `holes/items` → `Body3DPolygonHole`. These replace context-free `Polygon`/`Hole`; required vertex-index lists still require at least three entries. `Get3DGeometryOfElementsResult/geometries3D/items/oneOf/0` → `ElementGeometry3D`, preserving the error branch and required bodies.
- **Element quantities.** `GetQuantitiesOfElementsResult/quantitiesOfElements/items/oneOf/0` → `ElementQuantityDetails`; its `composites/items` → `ElementComponentQuantities`. Preserve required type/quantities/composites, optional subelement IDs, and the ten upstream quantity variants. `ElementQuantities` itself is restored as a named union by the cleaner.
- **Projection readback.** `Get3DProjectionSettingsResult/axonometric` → `AxonometricProjectionParameters`. Its transformation matrix still has exactly 12 numbers; `PerspectiveProjectionParameters` stays distinct.
- **MEP fitting rows.** For each of `Branch`, `Elbow`, and `Transition`, extract `MEP<kind>PreferenceTable/rows/items` as `MEP<kind>PreferenceTableRow`. The three rows have different dimensions and requiredness, replacing `Row`, `Row1`, `Row2`; GUID strings remain unconstrained upstream strings, rather than being strengthened to UUIDs.
- **MEP identifier result wrappers.** `MEPPhysicalSystemIdOrError/oneOf/0` → `MEPPhysicalSystemIdArrayItem`; `MEPSystemGroupIdOrError/oneOf/0` → `MEPSystemGroupIdArrayItem`. These retain their identifier object wrappers and error branches without numbered public names.
- **Image saving options.** Extract `SaveCurrentWindowAsImageParameters/format` as `ImageFormat` and `/colorDepth` as `ImageColorDepth`, preventing collision with existing export-format enums. Preserve all five formats and seven depths.
- **Active graphical-override selection.** Preserve the released `SetActiveGraphicalOverrideCombinationParameters` conditional union with `ActiveGraphicalOverrideCombinationById` and `ActiveGraphicalOverrideCombinationByName` via `name_required_variants`. The unified method uses its existing union-parameter path (`parameters=...`). No unified generator special case was added. Pydantic unions still do not enforce every JSON Schema `oneOf` exclusivity rule when extra keys are ignored; this established limitation remains.
- **Graphic-override criterion enums.** Extract these paths under `GraphicOverrideCriterion` with the indicated `GraphicOverride` prefix, avoiding context-free names and collision with edit enums whose wire spellings differ:

  ```text
  structureType → StructureType; wallComplexity → WallComplexity;
  wallGeometryType → WallGeometryType; columnCoatingType → ColumnCoatingType;
  columnCrossSectionType → ColumnCrossSectionType; slabEdgeAngle → SlabEdgeAngle;
  roofCutBodyType → RoofCutBodyType; roofEaveOverhangType → RoofEaveOverhangType;
  roofEdgeAngle → RoofEdgeAngle; roofGeometryType → RoofGeometryType;
  shellCutBodyType → ShellCutBodyType; shellGeometryType → ShellGeometryType;
  penReplacement → PenReplacement; structuralFunction → StructuralFunction;
  position → Position.
  ```

  For example, criterion wall geometry accepts `Uniform`, while element editing uses its separate enum; equal-looking roles do not justify reusing incompatible values. Negative-operator reuse is Temporary below. Column coating remains separate from `CompositeSkinType`: identical values alone do not establish the same concept.
- **Graphic-override structured operands.** At `GraphicOverrideCriterion`, extract `profileParameter` → `GraphicOverrideProfileParameter` and `customPropertyBool/String/Number/Integer` → `GraphicOverrideCustomPropertyBool/String/Number/Integer`. Their distinct value/operator types remain intact. The released requirement to choose exactly one criterion/operator, and restrictions on nesting, are descriptive; no stronger runtime validator was invented.
- **Shared-definition naming producers.** Extract `GetElectricalProjectSettingsResult/wiringTypes/items` → `ElectricalWiringType`, `/loadClassifications/items` → `ElectricalLoadClassification`, and `TextStyleDetails/textFrameShape` → `TextFrameShape`. The last preserves an existing public enum name. These Temporary producers run before their Temporary consumers; completed-schema reference checks pass.
- **Retained earlier naming.** The nine hotlink, object-set status and marker naming operations stay Temporary, matching their checked-in source category. Exact consumers/destinations are retained from the [1.7.1 report](tapir-1.7.1.md#permanent). Released named replacements allow retirement even if their names differ, with compatibility aliases as needed.
- **Older conditional variants.** Move `name_required_variants(master_defs, "Hole2D", [], ["Hole2DWithOutline", "Hole2DWithLegacyCoordinates"])` and the corresponding `TextData` call naming `TextDataWithText`/`TextDataWithRuns` to Temporary. These two operations also introduce public names. Their generic helper remains durable generator machinery; the schema-specific naming decisions can retire after equivalent upstream variant definitions arrive.

The following 22 replacements share equivalent contracts; extraction producers are counted above, rather than hidden in Permanent:

- **Electrical project settings.** Replace `ModifyElectricalProjectSettingsParameters/wiringTypesToAdd/items` with `ElectricalWiringType` and `/loadClassificationsToAdd/items` with `ElectricalLoadClassification`. These match the read contracts exactly: name plus cross-sectional area or demand factor. Retire when read/add locations share the named definitions.
- **Grid default parameters.** `GetGridElementDefaultsResult/parameters/items` reuses `GridParameterDetails` extracted from grid readback. Keep the enclosing default result's required parameter list and optional element ID distinct from each grid result. Retire when both parameter-item locations share a named definition.
- **Legacy graphical-rule color.** `CreateGraphicalOverrideRuleParameters/surfaceRGB` reuses `ColorRGB`, preserving its contextual description and required red/green/blue numbers. No 0–1 bounds were added beyond the released schema. Retire when this field references the existing color definition.
- **Active graphical-override IDs.** The original `GetActiveGraphicalOverrideCombinationResult/combinationId` and `SetActiveGraphicalOverrideCombinationParameters/combinationId` use the same GUID-object contract as `GraphicOverrideCombinationId`. Reuse it in the read result and both locally named selection variants (three expanded operations). Retire when both original locations reference the shared ID definition; preserve name/ID selection behavior.
- **Criterion positive/negative enum identity.** Under `GraphicOverrideCriterion`, the ten paths `wallComplexityNot`, `wallGeometryTypeNot`, `columnCoatingTypeNot`, `slabEdgeAngleNot`, `roofCutBodyTypeNot`, `roofEdgeAngleNot`, `roofGeometryTypeNot`, `penReplacementNot`, `structuralFunctionNot`, and `positionNot` reference their positive operator's named enum. Four further paths reuse existing shared enums: `wallReferenceLinePosition` and `wallReferenceLinePositionNot` → `WallReferenceLineLocation`; `slabReferencePlaneLocation` and `slabReferencePlaneLocationNot` → `SlabReferencePlaneLocation`. All values and optionality match. Retire when these 14 consumers share equivalent named definitions; retain distinct filtering enums where values differ from editing enums.
- **Text-frame enum reuse.** `TextStyleSettableDetails/textFrameShape` reuses `TextFrameShape` extracted from the read style, preserving values and public enum identity. Retire when both upstream style definitions share that enum.

#### Removed patches

The release supplies all six tracked decisions from [the preceding upstream refinement report](../upstream-patches/upstream-refinements-1.7.1-2026-10-17.md), comprising 12 expanded operations. Their destination contracts match the old patched contracts after reference expansion; no compatibility aliases need changing.

- **Mesh partial updates:** `ModifyMeshesParameters/meshesData/items/meshData` now references `MeshModificationData`. Remove its one extraction; retain `MeshWithDetails`, its required element/data wrapper, optional edit fields and bounds.
- **Revision custom-scheme entries:** `RevisionCustomSchemeData/items` now references `RevisionCustomSchemeEntry`. Remove one extraction; the key/value remain required with additional properties forbidden.
- **Beam modification holes:** `ModifyBeamsParameters/beamsWithDetails/items/holes/items` now references `BeamHoleModification`, whose `/type` references `BeamHoleType`. Remove two operations; retain absence of response-only `holeId`, positive dimensions, and required type/center/width.
- **Slab structure:** `CreateSlabsParameters/slabsData/items/structureType` now references `SlabStructureType`, retaining optionality and default/favorite notes. Remove one replacement.
- **Wall story links:** `CreateWallsParameters/wallsData/items/linkToSettings`, `WallDetails/linkToSettings`, and `ModifyWallsParameters/wallsWithDetails/items/linkToSettings` now reference `LinkToSettings`. Remove three replacements; released placement/readback descriptions remain intact.
- **Teamwork users:** `ReserveElementsResult/conflicts/items/user`, `GetLockableObjectSetStatusResult/conflicts/items`, `ReserveLockableObjectSetResult/conflicts/items`, and `ReserveHotlinkCacheManagementResult/conflicts/items` now reference `User`. Remove four operations; numeric userId/string userName remain required and enclosing wrappers are unchanged.

#### Upstream changes — no local patch

- **Creation options:** `ColumnData` adds slant angle/direction and flag; `DoorData`/`WindowData` add library-part name; `LayoutData` adds paper width/height; `MEPRoutingElementData` adds layer index; `MeshData` adds building-material ID; `MorphData` adds nonnegative top expansion; both `TextData` variants add layer index. Source paths are the corresponding `Create<element>Parameters/<data-array>/items` definitions, retained by the established naming extractions. Existing requiredness stays intact.
- **Text and label styles:** `TextRunDetails`, `TextStyleDetails`, `TextStyleSettableDetails`, and `LabelSymbolStyleSettableDetails` add optional fontName. Their label/text consumers change transitively; text-frame enum sharing is addressed above.
- **MEP:** `MEPElementType` adds `ElectricalPanel`/`ElectricalDevice` in the existing enum class. `GetMEPPreferenceTablesParameters` adds optional `includeFittingTables`; its result adds required `referenceSet` plus optional angle/fitting tables. The new electrical/system/group operations retain their released Archicad availability notes.
- **Navigator/project:** `ViewCloneData` and `ViewData` now require `parentNavigatorItemId`; `ViewSettings/renovationFilterGuid` changes from a UUID value to `GuidId`; `RenameNavigatorItemParameters/customName` and `SaveProjectParameters/projectPath` are optional additions. The former absent SaveProject parameter schema is not a new command.
- **Results/details:** `ExportFavoritesResult` now references `ExecutionResult`. `TypeSpecificDetails` adds `LevelDimensionDetails`, expanding `DetailsOfElement.details`; the new branch is retained in both representations. Geometry, quantity, projection, curtain-wall, grid, graphic override, electrical, and design-option command additions are enumerated in the API summary.

### Unified API breaking changes

- **`clone_project_map_item_to_view_map`:** each `ViewCloneData` now requires `parentNavigatorItemId`. Supply the intended destination parent instead of relying on the previous omission.
- **`create_views_in_view_map`:** each `ViewData` now requires the same destination parent. Existing method annotations stay unchanged, but parameter validation is stricter.

  ```python
  clone = ViewCloneData(navigatorItemId=source_id, parentNavigatorItemId=parent_id)
  view = ViewData(navigatorItemId=source_id, parentNavigatorItemId=parent_id)
  ```

- **`set_view_settings`:** `ViewSettings.renovationFilterGuid` takes `GuidId` (a `{"guid": ...}` object), replacing a UUID/string value. Wrap existing identifiers.
- **`get_view_settings`:** the same response field returns a `GuidId` model. Read `.guid` before comparing/serializing a bare UUID. Both changes originate at `ViewSettings/properties/renovationFilterGuid`.

  ```python
  settings = ViewSettings(renovationFilterGuid=GuidId(guid=filter_uuid))
  filter_uuid = returned_settings.renovationFilterGuid.guid  # when present
  ```

- **`get_mep_preference_tables`:** returns `GetMEPPreferenceTablesResult` instead of unwrapping `tables` to a list. Read `.tables`; mocks/cached payloads must include `referenceSet` (required name/referenceIds). Optional `include_fitting_tables` is additive. Cause: the released multi-field result schema.

  ```python
  result = api.get_mep_preference_tables(domain)
  tables = result.tables
  reference_ids = result.referenceSet.referenceIds
  ```

- **`export_favorites`:** returns a validated `SuccessfulExecutionResult | FailedExecutionResult`, replacing `None`; mocks must supply the real execution-result shape. Callers that ignore the return remain valid. Cause: released `ExportFavoritesResult` reference.

  ```python
  result = api.export_favorites(path)
  if isinstance(result, FailedExecutionResult):
      handle_error(result.error)
  ```

- **`get_auto_text_name`:** the repaired cleaner enforces the existing `AutoTextKeyValue` minimum length of one on each key. Remove empty key strings; method syntax and wire schema did not change.
- **`highlight_elements`:** the repaired `HighlightedColor` alias enforces exactly four integers per highlighted color. Supply RGBA, e.g. `[[255, 0, 0, 255]]`; this restores an existing schema rule without inventing component-value bounds. Method syntax stays unchanged.

### Untouched new type models

- `BeamQuantities`
- `BeamSegmentQuantities`
- `ColumnQuantities`
- `ColumnSegmentQuantities`
- `CurtainWallCrossingFrameType`
- `CurtainWallPatternCell`
- `CurtainWallPatternLogic`
- `CurtainWallPatternOrigin`
- `DesignOptionSetId`
- `DesignOptionSetIdArrayItem`
- `DimensionOrigin`
- `ElectricalCircuitDetails`
- `ElectricalDeviceDetails`
- `ElectricalLoads`
- `ElectricalPanelDetails`
- `GraphicOverrideCombinationIdArrayItem`
- `GraphicOverrideElementType`
- `GraphicOverrideFillTypes`
- `GraphicOverrideRuleGroup`
- `GraphicOverrideRuleId`
- `GraphicOverrideRuleIdArrayItem`
- `GraphicOverrideStyle`
- `GraphicOverrideSurfaceTypes`
- `LevelDimensionDetails`
- `MEPAngleSet`
- `MEPOrientation`
- `MEPPhysicalSystemDetails`
- `MEPPhysicalSystemId`
- `MEPReferenceSet`
- `MEPSystemGroupDetails`
- `MEPSystemGroupId`
- `MorphQuantities`
- `PerspectiveProjectionParameters`
- `RoofQuantities`
- `ShellQuantities`
- `SlabQuantities`
- `WallQuantities`
- `ZoneQuantities`

### Generator and audit changes

Compared with the original pre-update baseline, the Pydantic cleaner adds about 17 lines for root constraints and 16 lines to broaden existing alias restoration. The union-only change and 57 regenerated aliases for the previous release are now isolated in commit `c9e5933` (`fix(codegen): preserve named object union aliases`), with independent regression tests; no Tapir 1.7.2 dependency is included in that commit. Release-summary counts above retain their stated original baseline. The TypedDict repair has been reduced from a 51-line generic helper to a 12-line targeted transformation plus import plumbing.

| Change | What happens without it? | Review assessment |
| --- | --- | --- |
| Preserve root-alias constraints | Invalid sizes/indices and some older invalid payloads pass Pydantic validation. | Correctness repair needed; the exact AST implementation is one option. |
| Restore more named unions | Existing calls still validate their inlined unions, but named imports are missing from Pydantic. | Public-surface completeness; the 57-name historical backfill is optional scope. |
| Repair functional TypedDict references | Generated dictionary module fails to import, or nested Typeguard checks are skipped. | Short targeted repair; optional-key metadata and nested checks now both work. |
| Accept keyword keys; inspect functional definitions | Audit rejects valid `and`/`or` keys or misses some generated names. | Keyword correction is needed; functional-name inspection is a small coverage improvement. |
| Bound generated test recursion | Hypothesis cannot build strategies for the recursive criterion schema. | Needed for the current test-generation approach; runtime schema stays unchanged. |

#### 1. Root aliases: preserve constraints that the old cleaner threw away

**Source:** `tapir/model_generators/03_model_cleaner.py`, `fix_root_model_unions_to_type_alias`.

The raw generator already emits the constraint. For example, this is actual generated input:

```python
class CurtainWallPatternSize(RootModel[float]):
    root: float = Field(..., gt=0.0)
```

The old cleaner kept only the type inside `RootModel[...]`:

```python
# Old output: loses the positive-value constraint.
CurtainWallPatternSize: TypeAlias = float

# Current output: plain float values, with validation metadata retained.
CurtainWallPatternSize: TypeAlias = Annotated[float, Field(gt=0.0)]
```

The observable difference is small and important:

```python
TypeAdapter(float).validate_python(0)                  # 0.0: accepted
TypeAdapter(CurtainWallPatternSize).validate_python(0) # ValidationError
```

The new code parses the matched class, locates its `root = Field(...)` declaration, then builds the alias metadata. Actual core excerpt, after locating that field:

```python
constraints = [kw for kw in field.value.keywords
               if kw.arg not in {"description", "title", "default"}]
if constraints:
    metadata = ast.unparse(ast.Call(func=ast.Name(id="Field"),
                                   args=[], keywords=constraints))
    inner_type = f"Annotated[{inner_type}, {metadata}]"
```

The surrounding AST checks identify the root field and its Field call; they are not additional validators. AST parsing handles multiline calls and nested type syntax without another fragile regex. The metadata filter copies all remaining keywords, rather than a fixed whitelist of numeric constraints; unusual future Field metadata would need review.

**Scope:** four current aliases gain validation: `CurtainWallPatternSize` (`gt=0`), `CurtainWallFlexibleIndex` (`ge=0`), existing `AutoTextKeyValue` (`min_length=1`), and existing `HighlightedColor` (exactly four items). The latter two fixes affect existing callers. Unconstrained aliases/unions are unchanged. `use_annotated=False` still controls ordinary fields; nested constrained aliases need their own `Annotated` metadata. Keeping RootModel wrappers instead would also preserve constraints, but would change the established scalar/list API into wrapper objects.

**Recommendation:** retain the repair. The two older alias repairs are consequences of fixing the general transformation, rather than separate schema patches. These aliases are no longer bare runtime types; validate through TypeAdapter and use ordinary `str`/`list` types for runtime isinstance checks. Regression tests exercise numeric bounds, nonempty strings and fixed-length arrays.

#### 2. Named unions: recover public names, without changing existing call behavior

**Source:** the existing `restore_collapsed_named_unions` function in the same cleaner. This function predates 1.7.2; the update broadens the schema shapes it accepts.

A schema can name an object union even though the generator substitutes its branches directly into every consuming field. Abbreviated example showing two of the actual ten quantity branches:

```json
"ElementQuantities": {
  "type": "object",
  "description": "...",
  "oneOf": [
    {"$ref": "#/$defs/WallQuantities"},
    {"$ref": "#/$defs/ColumnQuantities"}
  ]
}
```

Before this change, consumers already had the corresponding Python union, but the Pydantic module did not export the `ElementQuantities` name. Restoration appends that alias; it does not rewrite the consumer fields. Abbreviated output:

```python
# Actual alias has all ten branches; shortened here for readability.
ElementQuantities: TypeAlias = WallQuantities | ColumnQuantities  # ...other branches
```

The old eligibility check accepted only a bare union dictionary. Actual before/after checks:

```python
# Before: description or type alone caused the definition to be skipped.
set(definition) == {union_keys[0]}

# After: allow these known siblings, reject any other sibling constraint.
not (set(definition) - {union_keys[0], "type", "description", "title"})
```

The other checks still require exactly one union keyword and reference-only branches. If the wrapper says `type: object`, `is_object_variant` also checks that each referenced branch is an object, following reference aliases with a cycle guard. Why that check matters: replacing `type: object` plus `oneOf[Object, Number]` with a bare `Object | Number` would incorrectly admit numbers. Wrappers with `minProperties`, extra properties, or other unsupported sibling constraints are skipped rather than weakened.

**Scope:** 67 additional Pydantic aliases appear: ten for new release definitions and 57 for preexisting schemas. TypedDict already retained these names. Adding the aliases does not strengthen Python unions into exact JSON Schema oneOf validators; overlapping branch acceptance remains an existing limitation.

**Reviewed decision:** retain the complete alias surface, including the useful 57-name historical backfill, in separate commit `c9e5933`. It is API completeness rather than a repair required for existing method calls. The object-safety check remains; recursive reference-chain support is defensive generality rather than the primary failure trigger.

#### 3. Functional TypedDicts: a short targeted fix for the two recursive fields

**Source:** `tapir/model_generators/06_typed_dict_cleaner.py`, `fix_graphic_override_forward_refs`. The generic 51-line AST/byte-offset helper has been removed. The replacement targets the exact raw expression emitted for the two criterion fields, quotes those self-references, and resolves the completed type's annotations once.

Why `and`/`or` differ from `copy`:

- `copy` is a legal Python identifier, but collides with Pydantic's inherited method. Codegen emits `copy_` with wire alias `copy`. TypedDict can keep `copy` in an ordinary class declaration.
- `and` and `or` are Python keywords: `and: ...` is invalid class syntax. Codegen therefore emits a functional `TypedDict(...)` call preserving those dictionary keys.
- The import failure comes from the recursive value in that call, not from the key itself. Its argument dictionary is evaluated before `GraphicOverrideCriterion` has been assigned. `from __future__ import annotations` does not defer ordinary expressions.

Actual copy-field excerpts:

```python
# Pydantic
copy_: bool | None = Field(None, alias="copy")

# TypedDict class body: no functional declaration needed.
copy: NotRequired[bool]
```

The targeted criterion transformation produces this shape (other fields omitted):

```python
GraphicOverrideCriterion = TypedDict("GraphicOverrideCriterion", {
    "and": NotRequired[list["GraphicOverrideCriterion"]],
    "or": NotRequired[list["GraphicOverrideCriterion"]],
})
GraphicOverrideCriterion.__annotations__ = get_type_hints(
    GraphicOverrideCriterion, include_extras=True
)
```

The two parts have separate purposes:

1. Quoting only the self-reference lets the constructor run. `NotRequired` remains visible during construction, so both keys are genuinely optional in `__required_keys__`/`__optional_keys__`.
2. `get_type_hints` resolves the references in the completed type's module. Assigning that resolved dictionary means Typeguard sees concrete recursive types, instead of skipping inner string references. `include_extras=True` preserves the NotRequired wrappers.

Current cleaner implementation:

```python
def fix_graphic_override_forward_refs(content: str) -> str:
    """Defer the two recursive keyword fields, then resolve their runtime types."""
    reference = "NotRequired[list[GraphicOverrideCriterion]]"
    if reference not in content:
        return content
    content = content.replace(reference, 'NotRequired[list["GraphicOverrideCriterion"]]')
    return re.sub(
        r"(?ms)^(GraphicOverrideCriterion = TypedDict\(.*?^\))",
        r"\1\nGraphicOverrideCriterion.__annotations__ = get_type_hints(GraphicOverrideCriterion, include_extras=True)",
        content,
        count=1,
    )
```

The regex appends the finalization line immediately after this functional declaration. It stays in the same definition block through splitting. The cleaner and splitter retain the required `get_type_hints` import. The early return also makes the transformation idempotent and leaves unrelated definitions alone. This deliberately handles the current generated criterion form rather than attempting arbitrary future functional TypedDicts; a generator-format change requires review.

The earlier explicit `ForwardRef("Criterion", module=__name__)` proposal worked at runtime but mypy rejected the constructor call in the TypedDict field type. The targeted quote-and-resolve form passes the focused mypy check. The old whole-annotation quoting variant was also removed: it hid NotRequired and incorrectly reported required keys.

**Verified behavior:** empty criteria are accepted by the Python type; missing operators remain optional; invalid nested field values are rejected without Typeguard warnings. Focused checks passed on installed Python **3.13.11 and 3.14.2**. Python 3.12 is not installed here. Regression tests exercise both operators, raw optional-key metadata, nested validation, idempotence and untouched unrelated TypedDicts. The runtime schema's other descriptive criterion restrictions remain unchanged.

#### 4. Audit: one false-positive correction and one small coverage extension

**Source:** `tapir/generation_audit.py`.

Actual property-name check, abbreviated to its condition:

```python
# Before: isidentifier() AND not keyword.iskeyword(name)
if not _is_python_identifier(name): ...

# After: keyword property keys are allowed.
if not name.isidentifier(): ...
```

`"and".isidentifier()` is true. JSON permits it; Pydantic emits `and_` with `alias="and"`, while TypedDict preserves the key through the functional form. Schema definition names still use the stricter non-keyword check. Other non-identifier property keys are still rejected by this audit; this change does not make it a general JSON-key validator.

The second addition recognizes assignments such as this when collecting public names:

```python
Criterion1 = TypedDict("Criterion1", {"and": list[str]})
```

Previously only class definitions and annotated TypeAlias assignments were inspected. The new AST branch extracts the assignment target, letting the existing numeric-suffix audit catch `Criterion1` too.

**Recommendation:** retain both. The first removes a real false positive; the second is optional audit coverage, small enough to justify without a new rule or naming exception.

#### 5. Generated test recursion: keep runtime behavior separate from test-data limits

**Source:** `bound_graphic_override_criteria` in the existing `shared/utils.py`. The standalone `shared/test_schema_bounds.py` file has been removed. The existing `patch_schema_definitions` and `patch_recursive_schemas` hooks call this small shared routine after copying their schemas; no new recursion framework was introduced.

The runtime schema references itself through operator items. Hypothesis-jsonschema raises HypothesisRefResolutionError when asked to generate data from that recursive schema:

```text
GraphicOverrideCriterion.and.items → GraphicOverrideCriterion
GraphicOverrideCriterion.or.items  → GraphicOverrideCriterion
```

The helper changes only a copied schema into a one-level tree:

```text
GraphicOverrideCriterion.and/or.items → GraphicOverrideCriterionLeafForTests
GraphicOverrideCriterionLeafForTests → scalar/operand fields, without and/or
```

Actual implementation core:

```python
criterion = definitions["GraphicOverrideCriterion"]
leaf = deepcopy(criterion)
for operator in ("and", "or"):
    del leaf["properties"][operator]
    criterion["properties"][operator]["items"] = {
        "$ref": "#/$defs/GraphicOverrideCriterionLeafForTests"
    }
definitions["GraphicOverrideCriterionLeafForTests"] = leaf
```

The surrounding code is an existence check, imports and documentation. One shared helper avoids making different recursion fixes in the model and method test generators. This permits nonempty operator arrays such as `{"and": [{"layer": "Walls"}]}`; simply removing and/or would leave the newly repaired keyword/recursive fields untested.

**Reviewed decision:** extend the existing schema-patching mechanisms and keep the small shared routine in the existing utilities module. It does not affect runtime schemas or client payload acceptance. It covers one operator level, matching the released description; it does not prove arbitrary recursion, exactly-one-criterion semantics, or every descriptive restriction. An alternative would be hand-written recursive Hypothesis strategies, with a larger maintenance cost.

### New patterns noticed

- **Eager functional TypedDict expressions:** future annotations do not protect recursive names inside the functional form. Added a cleaner regression and maintained functional-form name auditing; import/Typeguard checks verify the repair. Keep eager functional TypedDict evaluation in semantic import/runtime review, backed by the focused regression; no audit rule executes generated modules. It is not a reason to rename JSON keywords.

### Upstream follow-up

The six prior decisions are confirmed in the fetched 1.7.2 documentation and removed from the active queue. The six new Temporary decisions above are recorded in [active tracking](../../schema-patch-tracking.md), with original paths and release retirement conditions. The 15 new Permanent operations extend the established creation/modification lists; the other 71 new operations are Temporary naming or sharing candidates. No upstream implementation review, submission, or publication was performed.

### Verification

- Strict audit and complete-pipeline reproducibility: passed; a second full Tapir run changed no generated output. This is same-process reproducibility, not a cross-process hash-seed claim.
- Unified generation: passed; outputs target imported `clients/unified_api` and `clients/core/literal_commands.py`. No stale-import bootstrap or unified method generator special case was needed. A Windows console encoding failure was resolved by running with UTF-8 enabled.
- Patch equivalence: all released raw definitions match patched definitions after reference expansion and equivalent conditional-union normalization. The 12 retired operations' six destination contracts match the previous patched contracts.
- Representations: 1,058 generated Pydantic classes match TypedDict wire fields and requiredness derived from resolved type hints, allowing the 42 established singleton-literal defaults. The targeted TypedDict follow-up additionally verifies raw `__required_keys__`/`__optional_keys__`, fixing the criterion discrepancy identified during explanation review. All six compatibility aliases retain identical targets. Added/changed types, consumers, enum sharing, public aliases, method signatures and return expressions were reviewed; remaining movement is dependency ordering or documentation.
- Ruff: all changed handwritten source and regression tests pass formatting and lint. Generated formatting passed; the broader final model/dictionary/unified lint scope reports 24 unused-import template findings (25 findings on the same baseline scope), including the new graphic-override module's unused TypeAdapter import. No unrelated template cleanup was performed.
- Tests: **3,540 passed in 185.92 seconds** across the complete `tests/` suite, including generator regressions, generated models/methods, mock-server integration, and existing release-helper tests; no exclusions. The final run enabled localhost and temporary-file access after sandbox-only failures in the initial run. No warnings remained. No live Archicad instance was exercised.
- Reclassification verification: applying the old and reviewed stage organization to the same released raw schema produces exactly equal complete patched dictionaries, also equal to the current generated master schema. Strict audit and all **63 codegen tests passed** after reclassification. Generated outputs and client behavior remain unchanged, so the preceding full-suite result remains applicable.
- Diff: `git diff --check` passed. Common model movement is dependency ordering; unchanged method ASTs were distinguished from docstring/import changes. No generated files were edited manually.

- Generator refinement (2026-10-20): union restoration is retained in separate commit `c9e5933`; its generated artifacts were independently produced from the old 1.7.1 inputs and existing definitions/commands were checked unchanged. Both union-key regression cases pass against that isolated source. The targeted TypedDict fix passes focused mypy and Python 3.13/3.14 runtime checks. Full regenerated-suite verification: **3,540 passed in 185.92 seconds**, with no warnings or exclusions. Strict audit, complete-pipeline reproducibility and unified generation also passed. The regenerated criterion has all 666 keys optional in raw metadata; both operators reject invalid nested values without warnings. Patch categories and the user's existing edits were preserved.


### Human review

Apply the eight caller migrations above when adopting this update. The union-alias surface is retained in its own commit, the targeted TypedDict repair corrects both nested validation and raw optional-key metadata, and recursion bounding uses existing hooks/utilities. No pending generator design decision remains. Upstream schema naming/sharing follow-up remains separate.
