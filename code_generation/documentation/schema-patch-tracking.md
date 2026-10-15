# Tapir schema patch retirement tracking

Confirmed against the fetched **Tapir 1.7.1** documentation on 2026-10-15. Paths below use the patch helpers' shorthand: property names descend through `properties`; `items` descends through array items. All references are under `#/$defs/`.

Inputs: [common definitions](https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/refs/tags/1.7.1/docs/archicad-addon/common_schema_definitions.js), [command definitions](https://raw.githubusercontent.com/ENZYME-APD/tapir-archicad-automation/refs/tags/1.7.1/docs/archicad-addon/command_definitions.js).

## Retired in 1.7.1

184 temporary helper operations, nine manual edits and two source-review operations are retired. The released references use the same destination names. Expanded contracts match the pre-update patched schema, except the `MEPDistributionSystem.domain` difference against the saved generated snapshot. The prior client API used `MEPDomain`; `MEPDomainOrUnknown` widens its values. See the [enum compatibility note](reports/tapir-1.7.1.md#mep-enum-class-compatibility-wire-compatible-widening).

### Source-review operations (2)

- `MEPDomain`: `MEPSystemData/domain`. **Retired**; release supplies the intended enum contract.
- `MEPElementType`: `GetMEPElementsResult/elements/items/type`. **Retired**; release supplies the intended enum contract.

### Temporary named definitions and references (184 operations)

- `AssociativeWitnessPoint`: `AssociativeDimensionData/witnessPoints/items`.
- `AutoTextKeyValue`: `GetAutoTextNameParameters/keys/items`.
- `BeamAnchorPoint`: `BeamDetails/anchorPoint`, `BeamData/anchorPoint`, `BeamWithDetails/anchorPoint`.
- `BeamHole`: `BeamDetails/holes/items`.
- `BeamHoleType`: `BeamHole/type`.
- `BoundingBox2D`: `DrawingDetails/bounds`.
- `BuildingMaterialAttributeField`: `GetBuildingMaterialsParameters/fields/items`.
- `ClassificationItemConflictPolicy`: `ImportClassificationsXmlParameters/itemConflictPolicy`.
- `ClassificationItemUpdate`: `UpdateClassificationItemsParameters/classificationItems/items`.
- `ClassificationSystemConflictPolicy`: `ImportClassificationsXmlParameters/systemConflictPolicy`.
- `ClassificationSystemUpdate`: `UpdateClassificationSystemsParameters/classificationSystems/items`.
- `ColumnCoreAnchor`: `ColumnDetails/coreAnchor`, `ColumnData/coreAnchor`, `ColumnWithDetails/coreAnchor`.
- `CompositeAttributeField`: `GetCompositesParameters/fields/items`.
- `CompositeSkinType`: `CompositeSkin/type`.
- `Coordinate2D`: `RotateElementsParameters/elementsWithRotations/items/rotation/beginPoint`, `RotateElementsParameters/elementsWithRotations/items/rotation/endPoint`, `RotateElementsParameters/elementsWithRotations/items/rotation/origin`.
- `CoordinateWitnessPoint`: `DimensionData/witnessPoints/items`.
- `CoverFillOrientation`: `MorphDetails/coverFillOrientation`, `MorphData/coverFillOrientation`, `MorphWithDetails/coverFillOrientation`.
- `DesignOptionCombinationData`: `CreateDesignOptionCombinationsParameters/designOptionCombinations/items`.
- `DesignOptionCombinationDetails`: `GetDesignOptionCombinationsResult/designOptionCombinations/items`.
- `DesignOptionData`: `CreateDesignOptionsParameters/designOptions/items`.
- `DesignOptionLinkType`: `GetDesignOptionForElementsResult/designOptionForElements/items/type`.
- `DisplayOption`: `MorphDetails/displayOption`, `MorphData/displayOption`, `MorphWithDetails/displayOption`.
- `DrawingNameType`: `DrawingData/nameType`, `DrawingDetails/nameType`, `DrawingSettings/nameType`.
- `DrawingNumberingType`: `DrawingDetails/numberingType`, `DrawingSettings/numberingType`.
- `EnumValue`: `PossibleEnumValues/items/enumValue`.
- `EnumValueToAdd`: `EnumValuesToAdd/items/enumValue`.
- `FavoriteRename`: `RenameFavoritesParameters/renames/items`.
- `FavoritesFromElementUpdate`: `UpdateFavoritesFromElementsParameters/favoritesFromElements/items`.
- `FillAttributeField`: `GetFillsParameters/fields/items`.
- `FillLineItem`: `FillData/lineItems/items`.
- `FillSubType`: `FillAttribute/subType`.
- `FillSymbolArc`: `FillData/symbolArcs/items`.
- `FillSymbolLine`: `FillData/symbolLines/items`.
- `GeoReferencingParameters`: `GetGeoLocationResult/surveyPoint/geoReferencingParameters`.
- `GeoReferencingParametersUpdate`: `SetGeoLocationParameters/surveyPoint/geoReferencingParameters`.
- `GuidId`: `PropertyDetails/defaultEnumValueIds/items`, `PropertyEnumValueRename/enumValueId`, `PropertyEnumValueRemoval/enumValueId`, `ImportClassificationsXmlResult/created/items`, `ImportClassificationsXmlResult/removed/items`, `ImportPropertiesXmlResult/created/items`, `ImportPropertiesXmlResult/removed/items`.
- `HatchOrientationType`: `CoverFillOrientation/type`, `HatchOrientation/type`.
- `HotlinkInstanceChange`: `ChangeHotlinkInstancesParameters/hotlinkInstances/items`.
- `HotlinkInstanceCreation`: `CreateHotlinkInstancesParameters/hotlinkInstances/items`.
- `HotlinkType`: `Hotlink/type`, `HotlinkDetails/hotlinkType`.
- `IFCElementsToExport`: `IFCFileOperationParameters/elementsToExport`.
- `IFCExportTranslator`: `GetIFCExportTranslatorsResult/translators/items`.
- `InteriorElevationData`: `CreateInteriorElevationsParameters/interiorElevationsData/items`.
- `Justification`: `TextDataWithText/justification`, `TextDataWithRuns/justification`, `TextDetails/justification`, `TextSettings/justification`, `TextStyleDetails/justification`, `TextStyleSettableDetails/justification`.
- `LabelClass`: `LabelData/labelClass`, `LabelDetails/labelClass`.
- `LabelLeaderLineAnchorPoint`: `LabelLeaderLineDetails/anchorPoint`, `LabelLeaderLineSettableDetails/anchorPoint`.
- `LayerAttributeField`: `GetLayersParameters/fields/items`.
- `LayoutCustomData`: `GetLayoutSettingsResult/layoutSettings/items/customData/items`.
- `LayoutCustomDataToSet`: `LayoutSettingsData/customData/items`.
- `Library`: `GetLibrariesResult/libraries/items`.
- `LibraryLocation`: `AddLibrariesParameters/libraries/items`, `SetLibrariesParameters/libraries/items`.
- `LineAttributeField`: `GetLinesParameters/fields/items`.
- `LineDashItem`: `LineData/dashItems/items`.
- `LineSymbolItemData`: `LineData/lineItems/items`.
- `LinkToSettings`: `MorphDetails/linkToSettings`, `MorphData/linkToSettings`, `MorphWithDetails/linkToSettings`, `ObjectDetails/linkToSettings`, `ObjectData/linkToSettings`, `ObjectWithDetails/linkToSettings`, `LampData/linkToSettings`, `LampWithDetails/linkToSettings`.
- `MEPComponentType`: `MEPElementData/type`.
- `MEPCrossSectionShape`: `MEPRoutingElementData/crossSectionShape`, `MEPRoutingElementModificationData/crossSectionShape`.
- `MEPDistributionSystem`: `GetMEPDistributionSystemsResult/distributionSystems/items`.
- `MEPDomain`: `MEPSystemAttribute/domain/items`, `GetMEPElementsParameters/domains/items`, `MEPElementData/domain`, `MEPRoutingElementData/domain`.
- `MEPElement`: `GetMEPElementsResult/elements/items`.
- `MEPElementType`: `GetMEPElementsParameters/elementTypes/items`.
- `MEPPreferenceRow`: `MEPPreferenceTable/rows/items`.
- `MEPPreferenceTable`: `GetMEPPreferenceTablesResult/tables/items`.
- `MEPPreferenceTableDomain`: `GetMEPPreferenceTablesParameters/domain`.
- `MEPSystemAttributeField`: `GetMEPSystemsParameters/fields/items`.
- `MeshRidges`: `MeshDetails/ridges`, `MeshData/ridges`, `MeshModificationData/ridges`.
- `MeshSubline`: `MeshDetails/sublines/items`, `MeshData/sublines/items`, `MeshModificationData/sublines/items`.
- `MorphPolygon`: `MorphBody/polygons/items`.
- `MorphPolygonHole`: `MorphPolygon/holes/items`.
- `NavigatorItemType`: `NavigatorItem/type`.
- `PenData`: `PenTableData/pens/items`.
- `PenTableAttributeField`: `GetPenTablesParameters/fields/items`.
- `ProfileAttributeField`: `GetProfilesParameters/fields/items`.
- `ProfileEdgeOverride`: `ProfileData/skinOverrides/items/edgeOverrides/items`, `ProfileSkinData/edgeOverrides/items`.
- `ProfileSkinContour`: `ProfileSkinData/contours/items`.
- `ProfileSkinData`: `ProfileData/newSkins/items`.
- `ProfileUseWith`: `ProfileAttribute/useWith/items`.
- `ProjectInfoFieldData`: `CreateProjectInfoFieldsParameters/projectInfoFields/items`.
- `ProjectLocation`: `GetGeoLocationResult/projectLocation`.
- `ProjectLocationUpdate`: `SetGeoLocationParameters/projectLocation`.
- `PropertyAvailabilityUpdate`: `PropertyDefinitionUpdate/availability`.
- `PropertyDefinitionUpdate`: `UpdatePropertyDefinitionsParameters/propertyDefinitions/items`.
- `PropertyEnumValueRemoval`: `PropertyDefinitionUpdate/removeEnumValues/items`.
- `PropertyEnumValueRename`: `PropertyDefinitionUpdate/renameEnumValues/items`.
- `PropertyGroupDetails`: `GetAllPropertiesResult/propertyGroups/items`.
- `PropertyGroupUpdate`: `UpdatePropertyGroupsParameters/propertyGroups/items`.
- `PropertyImportConflictPolicy`: `ImportPropertiesXmlParameters/conflictPolicy`.
- `RoofDetailsLevel`: `RoofDetails/levels/items`.
- `RoofDetailsPivotLine`: `RoofDetails/pivotLine`.
- `RoofLevel`: `RoofData/levels/items`, `RoofWithDetails/levels/items`.
- `RoofPivotLine`: `RoofData/pivotLine`.
- `RoofStructureType`: `RoofData/structureType`, `RoofWithDetails/structureType`, `RoofDetails/structureType`.
- `SlabReferencePlaneLocation`: `SlabDetails/referencePlaneLocation`, `SlabData/referencePlaneLocation`, `SlabWithDetails/referencePlaneLocation`.
- `SlabStructureType`: `SlabDetails/structureType`, `SlabWithDetails/structureType`.
- `SolidLinkData`: `CreateSolidElementLinksParameters/solidLinks/items`.
- `SolidLinkReference`: `RemoveSolidElementLinksParameters/solidLinks/items`.
- `SolidLinksOfElement`: `GetSolidElementLinksResult/solidLinks/items`.
- `StoryVisibility`: `ObjectDetails/visibility`, `ObjectData/visibility`, `ObjectWithDetails/visibility`, `LampData/visibility`, `LampWithDetails/visibility`.
- `SurfaceAttributeField`: `GetSurfacesParameters/fields/items`.
- `SurveyPoint`: `GetGeoLocationResult/surveyPoint`.
- `SurveyPointPosition`: `GetGeoLocationResult/surveyPoint/position`.
- `SurveyPointPositionUpdate`: `SetGeoLocationParameters/surveyPoint/position`.
- `SurveyPointUpdate`: `SetGeoLocationParameters/surveyPoint`.
- `SymbolLabelTextDirection`: `LabelSymbolStyleSettableDetails/textWay`.
- `TextBoxAnchor`: `TextStyleDetails/anchor`, `TextStyleSettableDetails/anchor`.
- `TextureProjectionType`: `MorphDetails/textureProjectionType`, `MorphData/textureProjectionType`, `MorphWithDetails/textureProjectionType`.
- `TrimType`: `ElementTrims/trimmedBy/items/trimType`, `TrimElementsParameters/trimType`.
- `ViewDepthLimitation`: `MorphDetails/viewDepthLimitation`, `MorphData/viewDepthLimitation`, `MorphWithDetails/viewDepthLimitation`.
- `WallGeometryType`: `WallDetails/geometryType`.
- `WallModificationGeometryType`: `WallWithDetails/geometryType`.
- `WallModificationProfileType`: `WallWithDetails/profileType`.
- `WallProfileType`: `WallDetails/profileType`.
- `WallReferenceLineLocation`: `WallDetails/referenceLineLocation`, `WallData/referenceLineLocation`, `WallWithDetails/referenceLineLocation`.
- `WallStructureType`: `WallDetails/structureType`, `WallData/structureType`, `WallWithDetails/structureType`.
- `WallZoneRelation`: `WallDetails/zoneRel`, `WallWithDetails/zoneRel`.
- `ZoneCategoryAttributeField`: `GetZoneCategoriesParameters/fields/items`.
- `Zoom`: `ViewTransformations/zoom`, `ViewSettings/zoom`.

### Manual edits (9 operations)

- `GetElementsOfDesignOptionsParameters/designOptions/items` → `DesignOptionIdArrayItem`.
- `GetElementsOfDesignOptionsResult/elementsOfDesignOptions/items` → `ElementsOfDesignOptionOrError`.
- `NavigatorItemIdOrDatabaseIdAndWindowType/oneOf/1` → `DatabaseIdAndWindowType`.
- `ElementRelationsOrError/oneOf/0..5` → `WallRelations`, `BeamRelations`, `BeamSegmentRelations`, `ZoneRelationsOfElement`, `OpeningRelationsOfElement`, `RoofOrShellRelationsOfElement`. The error branch is unchanged.

## Still needed after 1.7.1

- **Beam holes — retained (2 operations).** Original source: `ModifyBeamsParameters/beamsWithDetails/items/holes/items`. Extract `BeamHoleModification`, then share `BeamHoleType`. The released modification item stays inline and differs from the response `BeamHole`: no `holeId`, positive width/height. Retire after equivalent upstream naming/reuse.
- **New temporary candidates - eight operations.** Slab structure reuse (1), wall story-link reuse (3), and Teamwork user extraction/reuse (4). Exact calls, consumers and retirement conditions are in the [generation report](reports/tapir-1.7.1.md#temporary). Status: **needs upstream follow-up**; no source PR investigated or created in this run.

All 69 existing permanent helper invocations remain. Nine new naming operations are Permanent generator workarounds (78 permanent invocations total): marker models (6), hotlink payloads (2), Teamwork status (1). These are not upstream candidates: valid inline schemas and generator singularization/collisions are local concerns. The setter wrapper is `ElementWithMarkerParameters`; branches are `MarkerParameterUpdateByName` and `MarkerParameterUpdateByIndex`. No breaking-permanent or source-review operations remain. Compatibility aliases stay in `code_generation/shared/model_aliases.py`. Retirement is based on released documentation, independently of source PR status.
