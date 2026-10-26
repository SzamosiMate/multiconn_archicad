## Tapir generation report

**Result:** Ready for human review, with an unrelated full-suite collection limitation | **Tapir:** 1.7.2 -> 1.7.3

Baseline: checked-in `6257d20` (also `origin/main` at preflight). Tracked outputs initially matched that revision; unrelated untracked work was preserved. Counts below compare public definitions structurally, ignoring definition order, docstrings and description-only Field wrappers. Released input is the two documentation JavaScript files at upstream tag `1.7.3`, fetched on 2026-10-26. No Tapir implementation source was inspected.

### API change summary

- Commands: **112 added, 0 removed, 13 with directly changed input/output schemas**. Additional commands consume changed shared types, described below. Ten existing generated method signatures change; six changes append optional arguments, three change return annotations (one is an equivalent compatibility-name change) and one expands the window-selection union.
- Common Pydantic type definitions: **157 added, 0 removed, 59 structurally changed**, including two old names now retained as compatibility aliases. Command model definitions: **204 added, 0 removed, 11 structurally changed**. These are definition counts, not just BaseModel classes or distinct transitive wire contracts.
- Unified API breaks: **4 methods**: `change_window`, `get_design_option_sets`, `get_details_of_elements`, `get_property_values_of_elements`.
- Patches: **2 new Permanent**, **161 new Temporary**, **2 retired Temporary**; no modified retained operations, new breaking patches or category migrations. Counts are expanded helper operations, including loop iterations, not source declarations. Unchanged inventory: 80 Permanent and 80 Temporary operations; final inventory: 82 Permanent and 241 Temporary. Compatibility aliases are counted separately.

<details>
<summary>Added commands by released documentation group</summary>

- **Property Commands:** `AddPropertyToAttributes`, `GetPropertyDefinitionsOfAttributes`, `MakePropertyAvailableForElements`, `MakePropertyUnavailableForElements`, `RemovePropertyFromAttributes`.
- **Navigator Commands:** `Change3DStyles`, `Create3DStyles`, `Get3DCutPlanes`, `Get3DStyleDetails`, `Get3DWindowSettings`, `GetDatabases`, `GetDrawingContentBoxes`, `GetLayoutSubsetSettings`, `GetNavigatorParentItems`, `GetStructureDisplay`, `ResetZoom`, `Set3DWindowSettings`, `SetStructureDisplay`, `SetZoom`.
- **Element Commands:** `ConvertRevealOffsets`, `DeleteSelectedElements`, `GetCategoryValuesOfElements`, `GetElementAtCoordinate`, `GetElementCategories`, `GetElementTypeNames`, `GetElementsInDrawOrder`, `GetHierarchicalElementOwners`, `GetLinksOfElements`, `GetOpeningDefault`, `GetOpeningDetails`, `GetOpeningFloorPlanParameters`, `GetOpeningTransformations`, `GetSurfaceQuantitiesOfElements`, `GetZoneReductions`, `LinkElements`, `MeasureTexts`, `MirrorElements`, `RegularizePolygons`, `RegularizePolylines`, `RunParameterScriptOfElements`, `SetCategoryValuesOfElements`, `SetOpeningDetails`, `SetOpeningFloorPlanParameters`, `SetZoneLabelingSettings`, `SolveStairBaseline`, `TriangulatePolygonsOfElements`, `UnlinkElements`.
- **Library Commands:** `CopyFilesIntoEmbeddedLibrary`, `CreateFolderInEmbeddedLibrary`, `SetLibraryPartScripts`.
- **Attribute Commands:** `CreateAttributeFolders`, `DeleteAttributeFolders`, `GetAttributesFromProject`, `GetCurrentLayerCombination`, `GetCurrentPenTable`, `GetFontsByName`, `GetGraphicOverrideRulesByName`, `MoveAttributesAndFolders`, `MoveGraphicOverrideRules`, `RenameAttributeFolders`, `RenameGraphicOverrideRuleGroups`.
- **Design Options Commands:** `DeactivateDesignOptionsInCombinations`, `DuplicateDesignOptionCombinations`.
- **MEP Commands:** `DeleteMEPPhysicalSystems`, `ModifyMEPPhysicalSystems`, `ModifyMEPSystemGroups`.
- **Project Data Commands:** `DeleteProjectData`, `GetProjectData`, `GetProjectDataKeys`, `GrantProjectData`, `ReleaseProjectData`, `RequestProjectData`, `ReserveProjectData`, `SetProjectData`.
- **Application Commands:** `Get3DCutawayStatus`, `GetArchicadReleaseInfo`, `GetContainingDatabases`, `GetCurrentWindowDrawingScale`, `GetElementFromUser`, `GetPrinterInfo`, `GetProductVersionInfo`, `Set3DCutawayStatus`, `SetCurrentWindowDrawingScale`, `SetDialogAutoClose`.
- **Favorites Commands:** `GetAllFavorites`, `GetFavoriteSettings`.
- **Analytical Commands:** `GetAnalyticalModelCheckTypeId`, `GetCurrentAnalyticalModel`, `SetAnalyticalGenerationSettingsToNoRule`, `UpdateAnalyticalModel`.
- **Classification Commands:** `GetClassificationsOfElementDefaults`, `SetClassificationsOfElementDefaults`.
- **Project Commands:** `GetCurrentViewImage`, `GetHotlinkProxyElementTable`, `GetNoteAutoTextKeywords`, `GetProjectNotes`, `GetProjectPreferences`, `GetSurveyPointTransformation`, `NewProject`, `SetProjectNotes`, `SetProjectPreferences`.
- **Element grouping Commands:** `GetElementSetsOfElements`, `GetUserDataOfGroups`, `UngroupElements`.
- **IFC Commands:** `GetIFCAttributesOfElements`, `RemoveIFCPropertiesOfElements`, `SetIFCAttributesOfElements`.
- **Teamwork Commands:** `GetReservationStatusOfElements`, `GetTeamworkStatus`, `GrantElements`.
- **Revision Management Commands:** `GetRevisionChangeCustomScheme`.
- **Issue Management Commands:** `ImportMarkupsFromPDF`.

</details>

Directly changed command schemas: `ApplyFavoritesToElements`, `ExportFavorites`, `FilterElements`, `GetDesignOptionSets`, `GetDetailsOfElements`, `GetGraphicOverrideRules`, `GetLayoutSettings`, `GetNavigatorItemTree`, `GetPropertyValuesOfElements`, `GetQuantitiesOfElements`, `GetSubelementsOfHierarchicalElements`, `Set3DCutPlanes`, `SetDetailsOfElements`.

<details>
<summary>Common type definition changes</summary>

**Added:** `AngleDimensionFormat`, `AngleDimensionFormatUpdate`, `AngleUnitFormat`, `AngleUnitFormatUpdate`, `AreaDimensionFormat`, `AreaDimensionFormatUpdate`, `AttributeCreationInfo`, `AttributeCreationMethod`, `AttributeFolder`, `AttributeFolderRename`, `AttributePropertyDefinitionFilter`, `AttributePropertyIds`, `AutoTextId`, `BeamSegmentDetails`, `CalculationUnitAreaFormat`, `CalculationUnitAreaFormatUpdate`, `CalculationUnitLengthFormat`, `CalculationUnitLengthFormatUpdate`, `CalculationUnitPreferences`, `CalculationUnitPreferencesUpdate`, `CalculationUnitVolumeFormat`, `CalculationUnitVolumeFormatUpdate`, `ColumnSegmentDetails`, `ContainingDatabase`, `DatabaseById`, `DatabaseByWindowType`, `DatabaseDetails`, `DatabaseType`, `DesignOptionDeactivation`, `DimensionPreferences`, `DimensionPreferencesUpdate`, `DrawingContentBox`, `ElementCategoryDetails`, `ElementCategoryId`, `ElementCategoryType`, `ElementCategoryValue`, `ElementCategoryValueData`, `ElementCategoryValueDetails`, `ElementCategoryValueId`, `ElementCategoryValues`, `ElementDefaultClassification`, `ElementIFCAttribute`, `ElementIFCAttributeValue`, `ElementIFCAttributes`, `ElementIFCAttributesOrError`, `ElementIFCPropertyRemoval`, `ElementLinkData`, `ElementLinkDetails`, `ElementLinkReference`, `ElementLinks`, `ElementLinksOrError`, `ElementMirrorData`, `ElementReservationState`, `ElementReservationStatus`, `ElementSet`, `ElementSetId`, `ElementSetsOfElement`, `ElementSurfaceQuantities`, `ElementSurfaceQuantity`, `ElementTriangulation`, `ElementTypeName`, `EmbeddedLibraryFile`, `FavoriteExportFormat`, `FavoriteKeepField`, `FavoriteSettings`, `FavoriteSubelement`, `FavoriteSubelementType`, `FavoriteSummary`, `FontDetails`, `GraphicOverrideRule`, `GraphicOverrideRuleGroupRename`, `GraphicOverrideRuleMove`, `GraphicOverrideRuleOrError`, `GraphicOverrideRuleReference`, `GroupUserData`, `GroupUserDataResult`, `HierarchicalElementOwner`, `HierarchicalElementType`, `HierarchicalOwnerMode`, `HotlinkProxyElement`, `HotlinkProxyElementTable`, `IFCPropertySource`, `IFCPropertyType`, `LayoutInsertionPosition`, `LayoutSubsetSettings`, `LengthDimensionFormat`, `LengthDimensionFormatUpdate`, `LibraryPartScriptData`, `LibraryPartScripts`, `MEPPhysicalSystemModificationData`, `MEPRoutingAnchor`, `MEPSystemGroupModificationData`, `MirrorAxis`, `NavigatorParentItem`, `NoteAutoTextKeyword`, `OpeningAnchor`, `OpeningDefaultFloorPlanParameters`, `OpeningDetails`, `OpeningExtrusionParameters`, `OpeningExtrusionParametersUpdate`, `OpeningFloorPlanDetails`, `OpeningFloorPlanModificationData`, `OpeningFloorPlanParameters`, `OpeningFloorPlanParametersUpdate`, `OpeningGeometry`, `OpeningModificationData`, `OpeningRevealOffsetData`, `OpeningRevealOffsets`, `OpeningTransformation`, `PartialStructureDisplay`, `PolygonAncestry`, `PolygonContourAncestry`, `PolygonEdgeAncestry`, `PolygonRegularizationData`, `PolygonVertexAncestry`, `PolylineAncestry`, `PolylineEdgeAncestry`, `PolylineRegularizationData`, `PolylineVertexAncestry`, `PrinterPrintArea`, `ProjectAttributes`, `ProjectAttributesByType`, `ProjectDataKey`, `ProjectDataName`, `ProjectDataReservationConflict`, `ProjectDataValue`, `ProjectDataValueData`, `ProjectPreferenceType`, `PropertyValueErrorItem`, `RegularizedPolygon`, `RegularizedPolygons`, `RegularizedPolyline`, `RevisionChangeCustomSchemeItem`, `SegmentStructureType`, `StairBaselineData`, `StairBaselineSolution`, `StairBaselineSolutionState`, `StairDetails`, `StoredGDLParameter`, `Style3DDetails`, `TeamworkUser`, `TextMeasurement`, `TextMeasurementData`, `Triangle`, `ViewImageFormat`, `ViewImageSource`, `WorkingUnitAreaFormat`, `WorkingUnitAreaFormatUpdate`, `WorkingUnitLengthFormat`, `WorkingUnitLengthFormatUpdate`, `WorkingUnitPreferences`, `WorkingUnitPreferencesUpdate`, `WorkingUnitVolumeFormat`, `WorkingUnitVolumeFormatUpdate`, `ZoneReduction`, `ZoneReductionType`, `ZoneReductions`.

**Changed:** `ArcData`, `AssociativeWitnessPoint`, `AttributeHeader`, `BeamData`, `CircleData`, `ColumnData`, `ColumnWithDetails`, `CurtainWallData`, `CurtainWallDetails`, `CurtainWallPanelDetails`, `DatabaseIdAndWindowType`, `Details`, `DetailsOfElement`, `DrawingDetails`, `DrawingSettings`, `ElementIFCProperty`, `FloorFill`, `GraphicOverrideRuleDetails`, `HatchData`, `HatchOrientation`, `Hotlink`, `HotspotData`, `LabelData`, `LampData`, `LayoutData`, `LayoutSetting`, `LayoutSettingsData`, `LevelDimensionData`, `LineElementData`, `MEPPhysicalSystemDetails`, `MEPRoutingElementDetails`, `MEPRoutingElementModificationData`, `MEPRoutingNodeDetails`, `MEPRoutingSegmentDetails`, `MEPSystemGroupDetails`, `MarkerGDLParameterDetails`, `MarkerParametersOfElement`, `MeshData`, `NavigatorItem`, `ObjectData`, `PolylineData`, `PropertyValueArrayItem`, `PropertyValueOrErrorItem`, `PropertyValuesArrayItem`, `SlabData`, `SlabWithDetails`, `SplineData`, `StairData`, `Subelement`, `SurveyPoint`, `SurveyPointUpdate`, `TextDataWithRuns`, `TextDataWithText`, `TypeSpecificDetails`, `WallData`, `WindowDoorDetails`, `ZoneData`, `ZoneDetails`, `ZoneSettings`.

</details>

### Patch decisions by reason

Each group states the reason for patching and places the corresponding operations immediately below. Permanent/Temporary labels retain the existing lifecycle classifications. Calls are expanded for review; execution order remains in `schema_patching.py`.

<a id="permanent"></a>

#### Extend the established creation/modification item-naming pattern

**Permanent - 2 expanded operations.** The two new MEP modification-array items need singular, established public names instead of generated `PhysicalSystemsDatum` / `SystemGroupsDatum`. Add them to the existing modification list. Physical-system modifications require their ID and allow partial field changes; group modifications require ID and name. Creation/readback contracts keep their own required fields. Existing category assignments remain unchanged.

Actual entries in the existing modification list:

```python
"ModifyMEPPhysicalSystemsParameters": ("physicalSystemsData", "MEPPhysicalSystemModificationData"),
"ModifyMEPSystemGroupsParameters": ("systemGroupsData", "MEPSystemGroupModificationData"),
```

<a id="temporary"></a>

**Temporary retirement rule.** For every Temporary entry below, retire the local operation when released documentation supplies equivalent named contracts and references at all shown consumers, preserving fields, requiredness, bounds, accepted values and selection/error branches. If upstream chooses another name, retain required existing Python imports through compatibility aliases. All replacements were checked after reference expansion, ignoring only descriptive metadata. No implementation-source investigation or publication was performed in this run.

#### Name conditional variants while preserving their required-field alternatives

**Temporary - 1 expanded operation.** The released database selector has `anyOf` requirements: window type or database ID. Naming its alternatives prevents numbered generated classes without flattening the selector into an object that accepts an empty payload. The union and its caller migration remain explicit.

```python
name_required_variants(master_defs, 'DatabaseIdAndWindowType', [], ['DatabaseByWindowType', 'DatabaseById'])
```

#### Preserve an established public name after upstream moves its schema

**Temporary - 1 expanded operation.** Upstream moved element-detail success fields into a success/error union. Extract that success branch as the existing `DetailsOfElement`, preserving imports while retaining the new error alternative. This avoids an incidental public rename caused by the extra schema nesting.

```python
extract_union_variant(master_defs, 'GetDetailsOfElementsResult', ['detailsOfElements', 'items'], 0, 'DetailsOfElement')
```

#### Prevent naming collisions between distinct read, default and update contracts

**Temporary - 28 expanded operations.** The generator derives repeated names such as `Length`, `Area`, `Level`, `ExtrusionParameters` and `FloorPlanParameters` from inline paths, then adds suffixes when those paths represent different contracts. Give each non-equivalent contract a stable role name. Preference read pages/formats retain required reported fields; update types allow partial writes. Opening defaults, readback and writes keep their different required lists and clear-symbol fields. These extractions preserve acceptance; they do not add new required fields. Equivalent nested formats and extrusion read/default consumers are handled under reuse reasons below.

```python
extract_inline_schema(master_defs, 'GetProjectPreferencesResult', ['workingUnits'], 'WorkingUnitPreferences')
extract_inline_schema(master_defs, 'WorkingUnitPreferences', ['length'], 'WorkingUnitLengthFormat')
extract_inline_schema(master_defs, 'WorkingUnitPreferences', ['area'], 'WorkingUnitAreaFormat')
extract_inline_schema(master_defs, 'WorkingUnitPreferences', ['volume'], 'WorkingUnitVolumeFormat')
extract_inline_schema(master_defs, 'SetProjectPreferencesParameters', ['workingUnits'], 'WorkingUnitPreferencesUpdate')
extract_inline_schema(master_defs, 'WorkingUnitPreferencesUpdate', ['length'], 'WorkingUnitLengthFormatUpdate')
extract_inline_schema(master_defs, 'WorkingUnitPreferencesUpdate', ['area'], 'WorkingUnitAreaFormatUpdate')
extract_inline_schema(master_defs, 'WorkingUnitPreferencesUpdate', ['volume'], 'WorkingUnitVolumeFormatUpdate')
extract_inline_schema(master_defs, 'GetProjectPreferencesResult', ['calculationUnits'], 'CalculationUnitPreferences')
extract_inline_schema(master_defs, 'CalculationUnitPreferences', ['length'], 'CalculationUnitLengthFormat')
extract_inline_schema(master_defs, 'CalculationUnitPreferences', ['area'], 'CalculationUnitAreaFormat')
extract_inline_schema(master_defs, 'CalculationUnitPreferences', ['volume'], 'CalculationUnitVolumeFormat')
extract_inline_schema(master_defs, 'SetProjectPreferencesParameters', ['calculationUnits'], 'CalculationUnitPreferencesUpdate')
extract_inline_schema(master_defs, 'CalculationUnitPreferencesUpdate', ['length'], 'CalculationUnitLengthFormatUpdate')
extract_inline_schema(master_defs, 'CalculationUnitPreferencesUpdate', ['area'], 'CalculationUnitAreaFormatUpdate')
extract_inline_schema(master_defs, 'CalculationUnitPreferencesUpdate', ['volume'], 'CalculationUnitVolumeFormatUpdate')
extract_inline_schema(master_defs, 'GetProjectPreferencesResult', ['dimensions'], 'DimensionPreferences')
extract_inline_schema(master_defs, 'DimensionPreferences', ['angle'], 'AngleDimensionFormat')
extract_inline_schema(master_defs, 'DimensionPreferences', ['area'], 'AreaDimensionFormat')
extract_inline_schema(master_defs, 'SetProjectPreferencesParameters', ['dimensions'], 'DimensionPreferencesUpdate')
extract_inline_schema(master_defs, 'DimensionPreferencesUpdate', ['angle'], 'AngleDimensionFormatUpdate')
extract_inline_schema(master_defs, 'DimensionPreferencesUpdate', ['area'], 'AreaDimensionFormatUpdate')
extract_inline_schema(master_defs, 'SetOpeningDetailsParameters', ['openingsWithDetails', 'items'], 'OpeningModificationData')
extract_inline_schema(master_defs, 'OpeningModificationData', ['extrusionParameters'], 'OpeningExtrusionParametersUpdate')
extract_inline_schema(master_defs, 'SetOpeningFloorPlanParametersParameters', ['openingsWithFloorPlanParameters', 'items'], 'OpeningFloorPlanModificationData')
extract_inline_schema(master_defs, 'GetOpeningDefaultResult', ['floorPlanParameters'], 'OpeningDefaultFloorPlanParameters')
extract_inline_schema(master_defs, 'OpeningFloorPlanDetails', ['floorPlanParameters'], 'OpeningFloorPlanParameters')
extract_inline_schema(master_defs, 'OpeningFloorPlanModificationData', ['floorPlanParameters'], 'OpeningFloorPlanParametersUpdate')
```

#### Replace context-free generated enum names with meaningful public names

**Temporary - 17 expanded operations.** Inline fields otherwise produce names such as `Method`, `Source`, `Format`, `Type`, `Status`, `Position` and `SubType`, including numbered collisions with existing exports. Name each enum for its actual role. The calls below keep all released values and preserve unrelated existing enum identities. Producers whose purpose is sharing an enum are grouped with their reference consumers below.

```python
extract_inline_enum(master_defs, 'GetProjectPreferencesParameters', ['preferenceTypes', 'items'], 'ProjectPreferenceType')
extract_inline_enum(master_defs, 'ApplyFavoritesToElementsParameters', ['keepFields', 'items'], 'FavoriteKeepField')
extract_inline_enum(master_defs, 'ExportFavoritesParameters', ['format'], 'FavoriteExportFormat')
extract_inline_enum(master_defs, 'FavoriteSubelement', ['subType'], 'FavoriteSubelementType')
extract_inline_enum(master_defs, 'AttributeCreationInfo', ['method'], 'AttributeCreationMethod')
extract_inline_enum(master_defs, 'GetPropertyDefinitionsOfAttributesParameters', ['filter'], 'AttributePropertyDefinitionFilter')
extract_inline_enum(master_defs, 'ElementIFCProperty', ['propertyType'], 'IFCPropertyType')
extract_inline_enum(master_defs, 'ElementIFCProperty', ['source'], 'IFCPropertySource')
extract_inline_enum(master_defs, 'GetHierarchicalElementOwnersParameters', ['ownerMode'], 'HierarchicalOwnerMode')
extract_inline_enum(master_defs, 'ZoneReduction', ['type'], 'ZoneReductionType')
extract_inline_enum(master_defs, 'StairBaselineSolution', ['solution'], 'StairBaselineSolutionState')
extract_inline_enum(master_defs, 'ElementReservationStatus', ['status'], 'ElementReservationState')
extract_inline_enum(master_defs, 'GetCurrentViewImageParameters', ['source'], 'ViewImageSource')
extract_inline_enum(master_defs, 'GetCurrentViewImageParameters', ['format'], 'ViewImageFormat')
extract_inline_enum(master_defs, 'GetDatabasesParameters', ['types', 'items'], 'DatabaseType')
extract_inline_enum(master_defs, 'GetPrinterInfoResult', ['printArea'], 'PrinterPrintArea')
extract_inline_enum(master_defs, 'LayoutData', ['position'], 'LayoutInsertionPosition')
```

#### Replace plural or path-derived request-item names with singular role names

**Temporary - 18 expanded operations.** The following array-item extractions name the represented request object rather than its containing collection. They avoid generated forms such as `StairsDatum`, `LibraryPart1`, `AttributeFolder1` or overly broad `Text` / `Value`. Creation/modification-list additions are already shown under the Permanent reason; these other extractions retain their Temporary classification. Each request keeps its own required fields rather than being merged with similarly shaped readback.

```python
extract_inline_schema(master_defs, 'ConvertRevealOffsetsParameters', ['openings', 'items'], 'OpeningRevealOffsetData')
extract_inline_schema(master_defs, 'RenameAttributeFoldersParameters', ['attributeFolders', 'items'], 'AttributeFolderRename')
extract_inline_schema(master_defs, 'GetGraphicOverrideRulesByNameParameters', ['graphicOverrideRules', 'items'], 'GraphicOverrideRuleReference')
extract_inline_schema(master_defs, 'MoveGraphicOverrideRulesParameters', ['graphicOverrideRules', 'items'], 'GraphicOverrideRuleMove')
extract_inline_schema(master_defs, 'RenameGraphicOverrideRuleGroupsParameters', ['ruleGroups', 'items'], 'GraphicOverrideRuleGroupRename')
extract_inline_schema(master_defs, 'RemoveIFCPropertiesOfElementsParameters', ['elementIFCProperties', 'items'], 'ElementIFCPropertyRemoval')
extract_inline_schema(master_defs, 'SetIFCAttributesOfElementsParameters', ['elementIFCAttributeValues', 'items'], 'ElementIFCAttributeValue')
extract_inline_schema(master_defs, 'SetCategoryValuesOfElementsParameters', ['elementCategoryValues', 'items'], 'ElementCategoryValueData')
extract_inline_schema(master_defs, 'SetClassificationsOfElementDefaultsParameters', ['elementDefaultClassifications', 'items'], 'ElementDefaultClassification')
extract_inline_schema(master_defs, 'MeasureTextsParameters', ['texts', 'items'], 'TextMeasurementData')
extract_inline_schema(master_defs, 'MirrorElementsParameters', ['elementsWithMirrorAxes', 'items'], 'ElementMirrorData')
extract_inline_schema(master_defs, 'RegularizePolygonsParameters', ['polygons', 'items'], 'PolygonRegularizationData')
extract_inline_schema(master_defs, 'RegularizePolylinesParameters', ['polylines', 'items'], 'PolylineRegularizationData')
extract_inline_schema(master_defs, 'SolveStairBaselineParameters', ['stairsData', 'items'], 'StairBaselineData')
extract_inline_schema(master_defs, 'SetProjectDataParameters', ['values', 'items'], 'ProjectDataValueData')
extract_inline_schema(master_defs, 'CopyFilesIntoEmbeddedLibraryParameters', ['files', 'items'], 'EmbeddedLibraryFile')
extract_inline_schema(master_defs, 'SetLibraryPartScriptsParameters', ['libraryParts', 'items'], 'LibraryPartScriptData')
extract_inline_schema(master_defs, 'DeactivateDesignOptionsInCombinationsParameters', ['deactivatedDesignOptionsInCombinations', 'items'], 'DesignOptionDeactivation')
```

#### Give anonymous success branches stable names without changing error alternatives

**Temporary - 30 expanded operations.** Inline union branches otherwise become plural, numbered or wrapper-path names such as `Results1`, `Openings1`, `ElementLinksOrError1` and `GetAttributesFromProjectResult1`. Extract the successful shape at each exact location below; leave the enclosing error alternative, result order and required fields intact. This changes naming, not success/error acceptance. The existing-name preservation and shared-contract producer cases are shown under their more specific reasons.

```python
extract_union_variant(master_defs, 'GetOpeningDetailsResult', ['openings', 'items'], 0, 'OpeningDetails')
extract_union_variant(master_defs, 'GetOpeningFloorPlanParametersResult', ['openings', 'items'], 0, 'OpeningFloorPlanDetails')
extract_union_variant(master_defs, 'GetOpeningTransformationsResult', ['openingTransformations', 'items'], 0, 'OpeningTransformation')
extract_union_variant(master_defs, 'ConvertRevealOffsetsResult', ['revealOffsets', 'items'], 0, 'OpeningRevealOffsets')
extract_union_variant(master_defs, 'GetFavoriteSettingsResult', ['favoriteSettings', 'items'], 0, 'FavoriteSettings')
extract_union_variant(master_defs, 'GetPropertyDefinitionsOfAttributesResult', ['propertyDefinitionsOfAttributes', 'items'], 0, 'AttributePropertyIds')
extract_union_variant(master_defs, 'GetAttributesFromProjectResult', [], 0, 'ProjectAttributes')
extract_union_variant(master_defs, 'ProjectAttributes', ['attributesByType', 'items'], 0, 'ProjectAttributesByType')
extract_union_variant(master_defs, 'GetCategoryValuesOfElementsResult', ['categoryValuesOfElements', 'items'], 0, 'ElementCategoryValues')
extract_union_variant(master_defs, 'GetHierarchicalElementOwnersResult', ['owners', 'items'], 0, 'HierarchicalElementOwner')
extract_union_variant(master_defs, 'ElementLinksOrError', [], 0, 'ElementLinks')
extract_union_variant(master_defs, 'GetHotlinkProxyElementTableResult', ['proxyElementTables', 'items'], 0, 'HotlinkProxyElementTable')
extract_union_variant(master_defs, 'GetElementSetsOfElementsResult', ['elementSetsOfElements', 'items'], 0, 'ElementSetsOfElement')
extract_union_variant(master_defs, 'MeasureTextsResult', ['measurements', 'items'], 0, 'TextMeasurement')
extract_union_variant(master_defs, 'RegularizePolygonsResult', ['results', 'items'], 0, 'RegularizedPolygons')
extract_union_variant(master_defs, 'RegularizePolylinesResult', ['results', 'items'], 0, 'RegularizedPolyline')
extract_union_variant(master_defs, 'GetSurfaceQuantitiesOfElementsResult', ['surfaceQuantitiesOfElements', 'items'], 0, 'ElementSurfaceQuantities')
extract_union_variant(master_defs, 'GetZoneReductionsResult', ['reductionsOfZones', 'items'], 0, 'ZoneReductions')
extract_union_variant(master_defs, 'SolveStairBaselineResult', ['solutions', 'items'], 0, 'StairBaselineSolution')
extract_union_variant(master_defs, 'TriangulatePolygonsOfElementsResult', ['triangulations', 'items'], 0, 'ElementTriangulation')
extract_union_variant(master_defs, 'GetProjectDataResult', ['values', 'items'], 0, 'ProjectDataValue')
extract_union_variant(master_defs, 'GetReservationStatusOfElementsResult', ['reservationStatuses', 'items'], 0, 'ElementReservationStatus')
extract_union_variant(master_defs, 'GetUserDataOfGroupsResult', ['userDataOfGroups', 'items'], 0, 'GroupUserDataResult')
extract_union_variant(master_defs, 'GetContainingDatabasesResult', ['databases', 'items'], 0, 'ContainingDatabase')
extract_union_variant(master_defs, 'GetLayoutSubsetSettingsResult', ['subsetSettings', 'items'], 0, 'LayoutSubsetSettings')
extract_union_variant(master_defs, 'GetDrawingContentBoxesResult', ['contentBoxes', 'items'], 0, 'DrawingContentBox')
extract_union_variant(master_defs, 'GetNavigatorParentItemsResult', ['parentItems', 'items'], 0, 'NavigatorParentItem')
extract_union_variant(master_defs, 'GetElementTypeNamesResult', ['names', 'items'], 0, 'ElementTypeName')
extract_union_variant(master_defs, 'GetNoteAutoTextKeywordsResult', ['keywords', 'items'], 0, 'NoteAutoTextKeyword')
extract_union_variant(master_defs, 'GetFontsByNameResult', ['fonts', 'items'], 0, 'FontDetails')
```

#### Give nested response structures and collections contextual public names

**Temporary - 25 expanded operations.** These inline components have generic or mechanically derived names such as `Geometry`, `UserData`, `Polygon1`, `Ancestry1`, `Vertice1` and `Edge1`. Name the represented object and its role. Distinct vertex/edge ancestry and read/write polygon roles stay separate even when some field sets coincide. This is contextual naming; no bounds, requiredness or payload shape change.

```python
extract_inline_schema(master_defs, 'OpeningDetails', ['geometry'], 'OpeningGeometry')
extract_inline_schema(master_defs, 'GetAllFavoritesResult', ['favorites', 'items'], 'FavoriteSummary')
extract_inline_schema(master_defs, 'FavoriteSettings', ['subElements', 'items'], 'FavoriteSubelement')
extract_inline_schema(master_defs, 'GetElementCategoriesResult', ['categories', 'items'], 'ElementCategoryDetails')
extract_inline_schema(master_defs, 'ElementCategoryDetails', ['values', 'items'], 'ElementCategoryValueDetails')
extract_inline_schema(master_defs, 'ElementCategoryValues', ['categoryValues', 'items'], 'ElementCategoryValue')
extract_inline_schema(master_defs, 'ElementLinks', ['links', 'items'], 'ElementLinkDetails')
extract_inline_schema(master_defs, 'HotlinkProxyElementTable', ['proxyElements', 'items'], 'HotlinkProxyElement')
extract_inline_schema(master_defs, 'RegularizedPolygons', ['polygons', 'items'], 'RegularizedPolygon')
extract_inline_schema(master_defs, 'RegularizedPolygon', ['ancestry'], 'PolygonAncestry')
extract_inline_schema(master_defs, 'PolygonAncestry', ['contours', 'items'], 'PolygonContourAncestry')
extract_inline_schema(master_defs, 'PolygonContourAncestry', ['vertices', 'items'], 'PolygonVertexAncestry')
extract_inline_schema(master_defs, 'PolygonContourAncestry', ['edges', 'items'], 'PolygonEdgeAncestry')
extract_inline_schema(master_defs, 'RegularizedPolyline', ['ancestry'], 'PolylineAncestry')
extract_inline_schema(master_defs, 'PolylineAncestry', ['vertices', 'items'], 'PolylineVertexAncestry')
extract_inline_schema(master_defs, 'PolylineAncestry', ['edges', 'items'], 'PolylineEdgeAncestry')
extract_inline_schema(master_defs, 'ElementSurfaceQuantities', ['surfaces', 'items'], 'ElementSurfaceQuantity')
extract_inline_schema(master_defs, 'ZoneReductions', ['reductions', 'items'], 'ZoneReduction')
extract_inline_schema(master_defs, 'GetProjectDataKeysResult', ['keys', 'items'], 'ProjectDataKey')
extract_inline_schema(master_defs, 'ReserveProjectDataResult', ['conflicts', 'items'], 'ProjectDataReservationConflict')
extract_inline_schema(master_defs, 'GetTeamworkStatusResult', ['users', 'items'], 'TeamworkUser')
extract_inline_schema(master_defs, 'GroupUserDataResult', ['userData'], 'GroupUserData')
extract_inline_schema(master_defs, 'GetDatabasesResult', ['databases', 'items'], 'DatabaseDetails')
extract_inline_schema(master_defs, 'LibraryPartScriptData', ['scripts'], 'LibraryPartScripts')
extract_inline_schema(master_defs, 'GetRevisionChangeCustomSchemeResult', ['customScheme', 'items'], 'RevisionChangeCustomSchemeItem')
```

#### Reuse one object model where consumers have the same meaning and contract

**Temporary - 11 expanded operation.** Avoid duplicate public classes for equivalent contracts. The style create/change/read consumers share a name-required style object; cut-plane read/write consumers share four required coefficients; default/read opening extrusion parameters match; favorite marker settings match the existing marker contract; deletion identities match the existing physical-system ID wrapper; reservation owner/reservedBy match `User`. Each producer is beside its replacements below. Identity classes for different domains and contracts with different required fields remain distinct.

```python
extract_union_variant(master_defs, 'Get3DStyleDetailsResult', ['styles', 'items'], 0, 'Style3DDetails')
replace_inline_schema_with_ref(master_defs, 'Create3DStylesParameters', ['styles', 'items'], 'Style3DDetails')
replace_inline_schema_with_ref(master_defs, 'Change3DStylesParameters', ['styles', 'items'], 'Style3DDetails')
extract_inline_schema(master_defs, 'Set3DCutPlanesParameters', ['cutPlanes', 'items'], 'CutPlane')
replace_inline_schema_with_ref(master_defs, 'Get3DCutPlanesResult', ['cutPlanes', 'items'], 'CutPlane')
extract_inline_schema(master_defs, 'OpeningDetails', ['extrusionParameters'], 'OpeningExtrusionParameters')
replace_inline_schema_with_ref(master_defs, 'GetOpeningDefaultResult', ['extrusionParameters'], 'OpeningExtrusionParameters')
replace_inline_schema_with_ref(master_defs, 'FavoriteSettings', ['marker'], 'MarkerParametersOfElement')
replace_inline_schema_with_ref(master_defs, 'DeleteMEPPhysicalSystemsParameters', ['physicalSystems', 'items'], 'MEPPhysicalSystemIdArrayItem')
replace_inline_schema_with_ref(master_defs, 'ElementReservationStatus', ['reservedBy'], 'User')
replace_inline_schema_with_ref(master_defs, 'ElementReservationStatus', ['owner'], 'User')
```

#### Reuse one enum class for equivalent read/write roles

**Temporary - 8 expanded operations.** Matching consumers should return/accept the same Python enum class, not separately generated classes with equal strings. Share each equivalent pair below: segment structure, MEP routing anchor, current-window partial structure display and opening anchor. Preserve values and optionality. Existing saved-view `StructureDisplay` has a different accepted-value set, and existing beam/column anchor enum identities remain unchanged.

```python
extract_inline_enum(master_defs, 'OpeningExtrusionParameters', ['anchor'], 'OpeningAnchor')
replace_inline_schema_with_ref(master_defs, 'OpeningExtrusionParametersUpdate', ['anchor'], 'OpeningAnchor')
extract_inline_enum(master_defs, 'GetStructureDisplayResult', ['structureDisplay'], 'PartialStructureDisplay')
replace_inline_schema_with_ref(master_defs, 'SetStructureDisplayParameters', ['structureDisplay'], 'PartialStructureDisplay')
extract_inline_enum(master_defs, 'BeamSegmentDetails', ['structureType'], 'SegmentStructureType')
replace_inline_schema_with_ref(master_defs, 'ColumnSegmentDetails', ['structureType'], 'SegmentStructureType')
extract_inline_enum(master_defs, 'MEPRoutingSegmentDetails', ['anchor'], 'MEPRoutingAnchor')
replace_inline_schema_with_ref(master_defs, 'MEPRoutingElementModificationData', ['anchor'], 'MEPRoutingAnchor', preserve_description=True)
```

#### Reuse repeated format contracts while separating required and partial forms

**Temporary - 16 expanded operations.** Working/calculation angle-unit formats are equivalent within readback and within updates. Six length-dimension roles also share the same format within each form. Reuse those definitions, retaining separate required readback and optional update types and preserving contextual descriptions. This also prevents a generated dimension `Level` model from displacing the established `Level = RoofLevel` compatibility alias. Other unit domains and precision fields are not merged.

```python
extract_inline_schema(master_defs, 'WorkingUnitPreferences', ['angle'], 'AngleUnitFormat')
extract_inline_schema(master_defs, 'WorkingUnitPreferencesUpdate', ['angle'], 'AngleUnitFormatUpdate')
replace_inline_schema_with_ref(master_defs, 'CalculationUnitPreferences', ['angle'], 'AngleUnitFormat')
replace_inline_schema_with_ref(master_defs, 'CalculationUnitPreferencesUpdate', ['angle'], 'AngleUnitFormatUpdate')
extract_inline_schema(master_defs, 'DimensionPreferences', ['linear'], 'LengthDimensionFormat')
replace_inline_schema_with_ref(master_defs, 'DimensionPreferences', ['radial'], 'LengthDimensionFormat', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferences', ['level'], 'LengthDimensionFormat', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferences', ['elevation'], 'LengthDimensionFormat', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferences', ['doorWindow'], 'LengthDimensionFormat', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferences', ['parapet'], 'LengthDimensionFormat', preserve_description=True)
extract_inline_schema(master_defs, 'DimensionPreferencesUpdate', ['linear'], 'LengthDimensionFormatUpdate')
replace_inline_schema_with_ref(master_defs, 'DimensionPreferencesUpdate', ['radial'], 'LengthDimensionFormatUpdate', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferencesUpdate', ['level'], 'LengthDimensionFormatUpdate', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferencesUpdate', ['elevation'], 'LengthDimensionFormatUpdate', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferencesUpdate', ['doorWindow'], 'LengthDimensionFormatUpdate', preserve_description=True)
replace_inline_schema_with_ref(master_defs, 'DimensionPreferencesUpdate', ['parapet'], 'LengthDimensionFormatUpdate', preserve_description=True)
```

#### Reuse one named constrained scalar instead of duplicating a generic alias

**Temporary - 6 expanded operations.** All six project-data name-array commands require the same nonempty string. Extract `ProjectDataName` once and reference it at every consumer, replacing context-free `Name` while preserving `minLength=1`. This creates neither a new validation rule nor a new restriction.

```python
extract_inline_schema(master_defs, 'DeleteProjectDataParameters', ['names', 'items'], 'ProjectDataName')
replace_inline_schema_with_ref(master_defs, 'GetProjectDataParameters', ['names', 'items'], 'ProjectDataName')
replace_inline_schema_with_ref(master_defs, 'GrantProjectDataParameters', ['names', 'items'], 'ProjectDataName')
replace_inline_schema_with_ref(master_defs, 'ReleaseProjectDataParameters', ['names', 'items'], 'ProjectDataName')
replace_inline_schema_with_ref(master_defs, 'RequestProjectDataParameters', ['names', 'items'], 'ProjectDataName')
replace_inline_schema_with_ref(master_defs, 'ReserveProjectDataParameters', ['names', 'items'], 'ProjectDataName')
```

<a id="removed-patches"></a>

#### Retire released refinements while preserving existing Python imports

**Retired Temporary - 2 operations; 2 compatibility aliases added.** The upstream definitions now replace the local extractions. The reason for keeping code below is Python import compatibility after adopting the released names.


**Adopt a released equivalent name and retain the old import.** Retire the extraction at `GetGraphicOverrideRulesResult/graphicOverrideRules/items`: released input now references `GraphicOverrideRule`. Its wire fields and requiredness match the previous patched `GraphicOverrideRuleDetails`; retain that old name as a direct alias in both representations. Consumers now use the shared upstream type, including the new by-name read API.

```python
GraphicOverrideRuleDetails: TypeAlias = GraphicOverrideRule
```

**Adopt a released shared name and preserve compatibility with the older, stricter contract.** Retire extraction at original `GetMarkerParametersOfElementsResult/markerParametersOfElements/items/oneOf/0/parameters/items` (patched parent `MarkerParametersOfElement`). Released input now references `StoredGDLParameter`, also used by Favorites. All old fields and values remain accepted; the release additionally makes `value` optional. Retain `MarkerGDLParameterDetails` as an alias in both representations, preserving the existing `Flag` enum identity. This is named adoption plus a released relaxation, not proof that the old/new required lists are identical.

```python
MarkerGDLParameterDetails: TypeAlias = StoredGDLParameter
```


#### Upstream changes (no local contract patch)

- Element creation payloads gain optional Element IDs; slab/column modifications gain floor indices. Layout creation gains insertion positioning, layout reads/updates gain master-layout identity, and drawing reads/updates gain border settings. See changed common definitions above and the corresponding released `Create*Parameters`, `ModifySlabsParameters`, `ModifyColumnsParameters`, `GetLayoutSettingsResult` and `SetLayoutSettingsParameters`.
- `AssociativeWitnessPoint` accepts static coordinates; `FloorFill` and `HatchOrientation` fields become optional. `Set3DCutPlanesParameters/cutPlanes` accepts an empty array, removing the old minimum length. Descriptive restrictions (such as choosing an element or coordinate) remain descriptions when the released schema does not enforce them.
- `TypeSpecificDetails` adds beam/column segments and stairs. Curtain-wall, window/door and drawing readback requiredness changes are covered with the element-details migration below. Zones gain reference positions; curtain-wall panels report degeneration.
- MEP routing adds node/segment connectivity, offsets, anchor, thickness, flange and branch-preference fields; system/group details gain editability. Survey-point reads/updates gain visibility and locking, hotlinks gain instance lists, and hierarchical subelements gain external subelements.
- Existing methods append optional `keep_fields`, favorite export `format`, element filter lists, navigator `include_child_count`, property `include_availability`, and quantity `calculate_in_one_call`. The six signatures are additive. New command methods retain the release's Archicad-version restrictions in their generated documentation, even when upstream's introduction metadata says 1.7.2 for a command first present in the fetched 1.7.3 input.

### Unified API breaking changes

- **`change_window`.** `DatabaseIdAndWindowType` changes from a callable BaseModel class to the union alias `DatabaseByWindowType | DatabaseById`, reflecting the new selection alternatives in that schema. The method still takes `parameters`; construct the appropriate concrete model instead of calling the old union name. Existing navigator-item selection remains supported.

  ```python
  # Before
  api.change_window(DatabaseIdAndWindowType(windowType="FloorPlan"))
  # After
  api.change_window(DatabaseByWindowType(windowType="FloorPlan"))
  api.change_window(DatabaseById(databaseId=database_id))
  ```

- **`get_design_option_sets`.** The optional `GetDesignOptionSetsResult/teamworkId` turns a one-field result into a two-field result. Unified generation therefore returns `GetDesignOptionSetsResult` instead of unwrapping a list. Use `.designOptionSets`; `.teamworkId` is optional in solo projects.

  ```python
  # Before: sets = api.get_design_option_sets()
  response = api.get_design_option_sets()
  sets = response.designOptionSets
  teamwork_id = response.teamworkId
  ```

- **`get_details_of_elements`.** Each item can now be `DetailsOfElement | ErrorItem`, preserving input alignment on failures. Handle errors before using `.details`. Update manually constructed/mocked `CurtainWallDetails` with required `height`, `flipped`, `angle`; `DrawingDetails` with required `hasBorderLine`, `borderLineTypeIndex`, `borderPenIndex`, `borderSize`; and `WindowDoorDetails` with required `reveal`, `revealDepthOffset`. These are released shared-readback changes; Pydantic unions still use the existing untagged matching behavior, so they do not independently prove every branch's semantic identity.

  ```python
  for entry in api.get_details_of_elements(elements):
      if isinstance(entry, ErrorItem):
          handle_error(entry.error)
          continue
      consume(entry.details)
  ```

- **`get_property_values_of_elements`.** The outer return annotation remains the same, but `PropertyValuesArrayItem.propertyValues` now uses `PropertyValueArrayItem | PropertyValueErrorItem`. Inner failures are no longer instances of `ErrorItem`; use `PropertyValueErrorItem` there (outer element errors still use `ErrorItem`). Both successful and failed property entries can carry optional `isAvailable` when requested.

  ```python
  for element in api.get_property_values_of_elements(elements, properties, include_availability=True):
      if isinstance(element, ErrorItem):
          handle_error(element.error)
          continue
      for value in element.propertyValues:
          if isinstance(value, PropertyValueErrorItem):
              handle_error(value.error)
          else:
              consume(value.propertyValue)
  ```

### Untouched new type models

- `AttributeFolder`
- `AutoTextId`
- `ElementCategoryId`
- `ElementCategoryType`
- `ElementCategoryValueId`
- `ElementIFCAttribute`
- `ElementIFCAttributes`
- `ElementIFCAttributesOrError`
- `ElementLinkData`
- `ElementLinkReference`
- `ElementSet`
- `ElementSetId`
- `GraphicOverrideRule`
- `GraphicOverrideRuleOrError`
- `HierarchicalElementType`
- `MirrorAxis`
- `PropertyValueErrorItem`
- `StairDetails`
- `StoredGDLParameter`
- `Triangle`

### Generator and audit changes

- **Valid wire property keys.** `generation_audit.audit_schema_names` no longer treats JSON property names as Python identifiers. Released `LibraryPartScripts/properties/2d` and `/3d` are legal wire keys: Pydantic uses aliases and TypedDict uses its functional form. Generated Python still receives the syntax audit; schema definition names still require valid PascalCase identifiers, and malformed `properties` containers still fail. The updated audit regression covers keywords, numeric prefixes and punctuation; runtime regression verifies numeric script keys, optional-key metadata and rejected non-string values. No schema key is renamed. No cleaner/generator code, generation settings or test-data bounds changed.

Abbreviated audit diff (definition-name and generated-syntax checks remain):

```diff
- for name in properties:
-     if not name.isidentifier():
-         ...  # invalid-schema-name finding
+ # Wire keys need not be Python identifiers. Pydantic aliases and
+ # functional TypedDicts preserve keywords, numeric prefixes and punctuation;
+ # audit_python_files checks that their generated declarations are valid.
```

- **Batch utility integration.** Add `PropertyValueErrorItem` to `utilities.results.batch_results.ERROR_CONTAINER_MODELS`. Without it, the released inner property-error wrapper is sent to the successful-value accessor and raises AttributeError. The migrated utility regression verifies cell errors and aggregated failed rows remain available. This runtime adaptation is separate from schema patch categories.

```diff
 ERROR_CONTAINER_MODELS = (
     tapir.FailedExecutionResult,
     tapir.ErrorItem,
+    tapir.PropertyValueErrorItem,
     official.FailedExecutionResult,
     official.ErrorItem,
 )
```


### New patterns noticed

- Numeric-prefixed wire keys generalize the known keyword-key case: valid JSON keys need not be Python identifiers. Correct the deterministic audit's false positive and retain representation/runtime checks; do not add a model-specific exception or rename wire keys.

### Upstream follow-up

The two adopted naming refinements above retire from the older fork queue. The other **80 retained Temporary operations** still lack released equivalent naming/sharing. The **161 new Temporary operations** are schema-only candidates for a separately requested upstream review, distinct from the already source-reviewed/published older queue. [Active tracking](../../schema-patch-tracking.md) records both groups and retirement conditions. No unresolved breaking source-review patch is introduced.

### Verification

- Strict audit and complete Tapir reproducibility: passed; final complete run took 94.35 seconds. The second complete pass changed no enumerated Tapir output. This is same-process byte reproducibility, not a cross-process hash-seed claim.
- Unified generation: passed against finalized Tapir outputs; command literals and methods target the imported `clients/core/literal_commands.py` and `clients/unified_api`. No manual generated-file edits or stale-import bootstrap were needed. New pipeline-owned `analytical.py` and `project_data.py` are staged with this report as required by the skill.
- All shared-schema replacements preserve expanded wire contracts. Existing enum names/values and all eight compatibility aliases were reviewed. Representation check: **1,361 distinct Pydantic classes**, no field/requiredness mismatch against resolved TypedDict hints, allowing the **42 established singleton-literal defaults**. Root list aliases and inline enum exports continue to differ according to the established Pydantic collapse/literal settings; new `AttributeFolders` and `ElementIFCAttributesOrErrors` follow the existing list-alias policy.
- Ruff: all changed handwritten files pass lint. The three codegen source files and two codegen regressions pass formatting; the two minimally edited utility/test files already fail whole-file formatting on HEAD, so unrelated formatting was preserved. Generated formatting passed; generated lint reports 23 unused-import template findings on the final scope, versus 24 on the same baseline scope. No template cleanup was performed.
- Tests: **4,477 passed in 205.96 seconds**, including generated models/methods, codegen regressions, utilities and all mock integration tests. The unfiltered suite was attempted first and stopped during collection on pre-existing untracked `tests/utilities/unit/test_query_registry.py`, which imports missing `AmbiguousPropertyTypeError`. The final run excludes only that file; no query implementation changed. After the user closed Archicad, its port-range guard passed and no integration tests were excluded. No live Archicad instance was exercised.
- Structural definition, changed method signature/return, consumer and complete changed-path review completed. Generated movement is dependency ordering and description changes; no Official model pipeline was rerun. Final `git diff --check` passed.

### Human review

No pending generation or patch-classification decision. Apply the four caller migrations above. The untracked query-registry test requires its separate utilities implementation before an unfiltered suite can collect successfully; this update preserves that work.
