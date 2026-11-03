# Upstream schema refinements following Tapir 1.8.0

Started 2026-11-03. Initial endpoint: publish a reviewable fork branch. The user subsequently opened [PR #1754](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1754); this run later resolved its merge conflicts.

- Client release: **Tapir 1.8.0**, release input and patched input from the [generation run](../codegen/tapir-1.8.0.md); active local patch inventory **100 Permanent + 611 Temporary + one Breaking source-review operation**. MultiConn review started on `update-to-tapir-1.8.0` at `4cef0b4ddc1344b98573c3ad1c637871b3aec657` with in-progress release changes. During this run the user committed that release work as `7eba2f5` (`codegen: updated to tapir 1.8.0`); the reviewed patch/schema contents were preserved. This run did not create a MultiConn commit.
- Upstream: `ENZYME-APD/tapir-archicad-automation`, default branch `main`. Fork: `SzamosiMate/tapir-archicad-automation`, default branch `main`; fast-forward synced at the start without force.
- Exact source baseline: `c4db2ade1fcfb40bedf81832ad4b5cd429d8504e`.
- Published [branch](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.8.0); current verified remote tip [`808781f6`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/808781f63ebb786ab809e1aa490959b3396c944c).
- Commits: [`2fb8182c`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/2fb8182c54b72c15f6cddc29dcc773c08cd6536b) names/shares equivalent schemas; [`72bf361f`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/72bf361f07e4b34200ea2067a89202095ac9ea2c) contains the isolated **breaking classification schema correction**.
- Upstream advanced during the run to `0683cb669893ed893eea21b2eab7cda72dc733d6`; `git merge-tree --write-tree` confirms a clean merge with the published head. Those later commits are not included in this branch or its SDK build.

The [active queue](../../schema-patch-tracking.md) owns the published/deferred retirement scope. This is the single durable record for this logical run. The user opened [PR #1754](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1754).

## Scope and dependencies

Reviewed all **370 new Temporary operations** from the 1.8.0 inventory: **341 implemented**, **29 deferred**, yielding **279 new common definitions**. Implemented operations comprise 139 object/scalar extractions, 90 union-branch extractions, 46 enum extractions, two conditional-variant calls (four definitions), and 64 shared-reference replacements. Counts expand helper loops; they are not PR boundaries. The 100 Permanent client operations were used only to trace nested paths, then inlined again; they were not published.

[PR #1386](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1386) and [PR #1557](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1557) were confirmed open. Their commits were not stacked, copied or rewritten. Missing prerequisites include pending `HotlinkNodeReference`, `AreaDimensionFormat` and `PartialStructureDisplay`, plus earlier deferred opening, library-script and text-measurement extractions. All 29 dependent operations remain inline. The queue records their original command/common paths and prerequisites.

Named schemas cover analytical models and settings; MEP table keys/values, routing and defaults; viewpoint/library/property/classification payloads; dimension standards, zone settings, drawing primitives and user-data keys. Creation/update/read contracts with differing fields or requiredness remain separate. Source helpers were retained where needed; schema-only constants/helpers made unused by extraction were removed. Three commands newly opt into `CommonSchema::Used`: `GetProductVersionInfo`, `GetDocumentFrom3DDefaults` and `SetPlaceSettings`.

The two routing-transition update objects have explicit `required: []`, while `MEPTransitionDefaults` omits `required`. Both impose no required properties; they are equivalent and share that definition. Validation explicitly normalizes empty required lists rather than treating that syntactic difference as an acceptance change. Standard dimension formats remain separate from differing project-preference formats; `ElementUnmergePair` remains separate from trimming `ElementPair`. All 279 new definitions match the existing patched released client structurally after normalization, so this proposal introduces no new compatibility alias requirement. Release adoption must still verify every consumer and existing alias.

## Classification compatibility decision

Two commands had incorrect response schemas: `GetClassificationsOfElements` and `GetClassificationsOfElementDefaults`. Both implementations return the classification fields directly, while the old schema required a `classificationId` wrapper. `GetClassificationOfAttributesInSystem` already matched its wrapped response. Its schema was only separated from the shared definition to preserve that existing contract. No working command receives a breaking contract change. The earlier PR wording obscured this distinction; the copyable text below has been rewritten in plain language.

`ClassificationIdOrError/oneOf/0` changes from `ClassificationIdArrayItem` to `ClassificationId`. `GetClassificationsOfElements` constructs direct system/item fields in each classification slot; `GetClassificationsOfElementDefaults` also constructs direct fields and omits `classificationItemId` for an unclassified default. The schema now matches that existing execution contract. This is a breaking published-schema/generated-client change, isolated in the second commit. It does not change command execution, introduce a second accepted element shape, remove optional item handling or alter errors. Other wrapped input/read consumers still use `ClassificationIdArrayItem`.

The new 1.8.0 consumer **`GetClassificationOfAttributesInSystem` is different**: its execution explicitly constructs `GS::ObjectState ("classificationId", classificationId)`. Its success/error array is therefore separated from the corrected shared element union and retains its wrapped contract. The command's contextual description is unchanged.

Inspected the exact AC29 declarations and comments in the available version-specific DevKit `Support/Inc/ACAPinc.h`: `ACAPI_Element_GetClassificationInSystem`, `ACAPI_Element_GetClassificationInSystemDefault` and `ACAPI_Attribute_GetClassificationInSystem`, plus Tapir's `TAPIR_Element_GetClassificationInSystemDefault` adapter. The getters return an output classification item, with a null GUID for an unclassified item; the JSON wrapper choice comes from Tapir execution, not SDK inference. Primary Graphisoft documentation: [classification getters](https://graphisoft.github.io/archicad-api-devkit/group___classification.html) and [attribute getter](https://graphisoft.github.io/archicad-api-devkit/group___attribute.html). The latter site currently documents AC30, so AC29 header evidence is recorded separately. Previous live AC27/Tapir 1.7.3 element observations remain supporting evidence from active tracking; no new live request was made in this run.

**Downstream follow-up:** the current client patch globally corrects `ClassificationIdOrError`, which also flattens the attribute consumer. Source review shows that attribute application is incorrect. This upstream proposal preserves the real wrapper; it does not edit the client patch, regenerate models or add an adapter. Release adoption must reconcile that client consumer separately and must not blindly retire the correction from a source merge alone.

## Original validation and limits

- Interpreted current C++ schemas with the target branch's official `tools/generate_addon_docs.py`, in memory: **666 commands**, **1,878 baseline shared-definition/command-side roots**, **1,226 non-null command schemas**. Baseline cached once. An untracked lookup cache/prefilter only avoids repeated or impossible searches; it does not change interpreter semantics. After the final common-resource-only MEP edit, the resource was re-read and the complete comparison repeated; command schemas were unchanged. The local history cleanup left the validated final tree unchanged.
- Every baseline root passes the schema-aware complete structural comparison, allowing only the explicitly reviewed classification delta. Final pass: **35,397 compared nodes**. It preserves reference siblings, recursion, ordered enum/union branches, fields, bounds and additional-property behavior; conditional required-only unions are compared with their distributed complete alternatives. Empty required lists normalize to absence. Original-versus-final comparison identifies exactly two changed command response contracts: element and element-default classification reads; the attribute result is equivalent.
- All common references resolve, with no name collision or dependency on either pending PR. `CommonSchema::Used` is verified for all **139 directly affected commands**. Every changed C++ execution/non-schema region is unchanged after excluding schema functions/constants and the three explicit common-schema opt-ins. Moved schema methods and their retained string-building helpers have no Archicad-version preprocessing branches.
- All **279 new named definitions** structurally match patched Tapir 1.8.0 input; no client models, aliases, release pin or generated documentation were changed.
- **26 classification cases passed**: old/new direct and wrapped element responses, defaults, optional unclassified items, inner/outer errors, unchanged wrapped attribute successes/errors and unchanged `ClassificationIdArrayItem` acceptance. These are JSON Schema checks against source-derived schemas, not live integration tests.
- The actual target renderer resolved all **1,226 command schemas** and verified **102 retained reference/definition description pairs**, without mutating definitions or leaking caller context. Full strings/locations are recorded below. This checks renderer preparation, not a browser screenshot/DOM render.
- **Archicad 29 Windows Debug SDK build passed**, including the final classification compile and final MEP common-resource rebuild. The initial full link emitted the SDK's missing `API_c.pdb` debug-symbol warning (LNK4099); it linked successfully. No other SDK version, macOS build or live Archicad execution was tested. At original branch publication there was no upstream PR or PR CI run; the later PR status is recorded below.
- `git diff --check` passed. Only the 36 intended Tapir source/resource files are in the two commits. Original Tapir `get-SI-properties` checkout and its untracked `.idea/` were preserved; work used `sandbox/upstream180`. The final report is staged in MultiConn; tracking is deliberately left unstaged, and existing staged user changes are preserved. MultiConn changes were not committed.

## Conflict resolution after upstream changes — 2026-11-03

Merged upstream `main` at `dd7eafc67656f9f397c95e8438f9cd168e612d70` into the existing PR branch, producing merge commit [`37b3e3bd`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/37b3e3bd2c003d49e69d6673fc91d643a2eaf150). Pushed normally and verified the remote tip. GitHub now reports PR #1754 as **MERGEABLE**; its six listed CI/review checks are queued. The two original commits, including the separate classification correction `72bf361f`, are unchanged. The earlier clean-merge check at `0683cb66` described the upstream state at that time; later upstream commits introduced these two conflicts.

- `DrawingPrimitiveCommands.cpp`: upstream changed primitive collection after the proposal extracted its schema. Kept the upstream execution changes and the shared-schema references. Updated `DrawingPrimitive` to omit the now-unreported `text` property, describe `coordinates` for `Tri`, and describe `DrawingPrimitiveHatchBorder` for `Ctrl_HatchBorderBeg` only, matching current upstream schemas.
- `CommonSchemaDefinitions.json`: both sides appended definitions at the end. Preserved all proposal definitions and the upstream additions `AnalyticalImportMappingTable` and `AnalyticalImportIdMapping`, together with the automatically merged upstream field/description changes.
- Reinterpreted both current upstream and the resolved source: **677 commands**, **1,910 baseline roots**, **279 additional common definitions**. Full structural comparison passed (**36,324 nodes**) with only the existing classification correction allowed. All references resolve. Execution and other non-schema C++ code match current upstream after accounting for the three existing common-schema opt-ins and removed schema helpers/constants.
- The actual renderer processed **1,246 command schemas**, checked **692 description pairs** across all schemas, and left shared definitions unchanged. The **103 pairs** in changed/new roots are recorded below. All **26 classification checks** passed again. The attribute wrapper remains unchanged.
- The **AC29 Windows Debug SDK build passed**, including a final incremental resource and drawing-source build. The full link again emitted the SDK's missing `API_c.pdb` debug-symbol warning. No new live Archicad test or other-platform build was performed. Both `git diff upstream/main --check` and the staged merge whitespace check passed. No generated documentation or MultiConn client model was edited. The original 29 dependency deferrals remain.

## Model-view-option description correction — 2026-11-03

Published commit [`808781f6`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/808781f63ebb786ab809e1aa490959b3396c944c) removes the misleading optional-other-selector clauses. `ModelViewOptionById/description` is now "Selects a model view option combination by identifier." and `ModelViewOptionByName/description` is "Selects a model view option combination by name." `FindModelViewOption` combines these alternatives with `oneOf`, so supplying both keys matches both alternatives and fails validation.

Focused checks confirm only these two descriptions changed, each corrected string survives the actual reference renderer, and ID-only/name-only inputs pass while an input containing both keys fails. `git diff --check` passed. No contract or execution code changed; no SDK rebuild was needed for this wording-only edit. The remote tip was verified after the push.

## Copyable PR text

```markdown
# Refine API schemas following Tapir 1.8.0

This PR gives inline schemas names and moves them into the shared schema file, so commands can reuse the same definitions.

- Add named schemas for analytical data, MEP settings, drawing primitives, project settings and command parameters.
- Replace matching inline schemas with references to those definitions.
- Leave out changes that need definitions from the unmerged schema PRs #1386 and #1557 or their deferred work.

The classification fix is in a separate commit. The response schemas for `GetClassificationsOfElements` and `GetClassificationsOfElementDefaults` described a `classificationId` wrapper that these commands do not return. Their schemas now describe the fields directly, matching their existing responses. This is a breaking schema correction for clients generated from the old schemas.

`GetClassificationOfAttributesInSystem` does return the wrapper. Its schema keeps that structure; it was separated from the shared definition so the fix above does not change its contract.

No command implementation or actual response was changed.
```

## Retained reference and definition descriptions

Current locations and full strings after the upstream merge are listed below. Command roots ending in `Parameters`/`Result` identify the corresponding C++ schema method; other roots identify definitions in `Sources/RFIX/Images/CommonSchemaDefinitions.json`. Pairs in new/changed roots include previously present contextual fields moved with their containing schema. Definitions are quoted once.

### Shared definitions

- `CommonSchemaDefinitions.json#/IFCClassificationReferenceSource/description`: "Where the reference comes from: preview (mapped by the preview IFC export translator) or local (stored on the element)."
- `CommonSchemaDefinitions.json#/GuidId/description`: "Identifier."
- `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."
- `CommonSchemaDefinitions.json#/AnalyticalCrossSection/description`: "The cross section of a curve member. The profile image of Archicad 26 and newer is not returned."
- `CommonSchemaDefinitions.json#/Error/description`: "The details of an error."
- `CommonSchemaDefinitions.json#/AddOnViewpointId/description`: "The identifier of an add-on viewpoint item."
- `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."
- `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."
- `CommonSchemaDefinitions.json#/DatabaseId/description`: "The identifier of a database"
- `CommonSchemaDefinitions.json#/WindowType/description`: "The type of a window."
- `CommonSchemaDefinitions.json#/NavigatorItemId/description`: "The identifier of a navigator item."
- `CommonSchemaDefinitions.json#/MEPPreferenceTableId/description`: "The GUID of an MEP preference table."
- `CommonSchemaDefinitions.json#/Elements/description`: "A list of elements."
- `CommonSchemaDefinitions.json#/Date/description`: "A date in its string representation as defined in ISO 8601: YYYY-MM-DD."
- `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."
- `CommonSchemaDefinitions.json#/ElementCategoryValueId/description`: "The identifier of a value of an element category."
- `CommonSchemaDefinitions.json#/ClassificationSystemId/description`: "The identifier of a classification system."
- `CommonSchemaDefinitions.json#/ClassificationItemId/description`: "The identifier of a classification item."
- `CommonSchemaDefinitions.json#/ElementType/description`: "The type of an element."
- `CommonSchemaDefinitions.json#/Coordinate2D/description`: "2D coordinate."
- `CommonSchemaDefinitions.json#/BoundingBox2D/description`: "A two-dimensional bounding box defined by its minimum and maximum coordinates."
- `CommonSchemaDefinitions.json#/AnalyticalMemberPartRef/description`: "A reference to a part (vertex, edge or surface) of an analytical member. partId, customVertexData and ratioEdgeData are zero when left out."
- `CommonSchemaDefinitions.json#/PropertyValue/description`: "The string value of a property, formatted according to the command's options."
- `CommonSchemaDefinitions.json#/AttributePropertyValueStatus/description`: "A property value with its status."
- `CommonSchemaDefinitions.json#/ProjectInfoGroupId/description`: "The identifier of a Project Info group. Available from Archicad 30."
- `CommonSchemaDefinitions.json#/DesignOptionSetId/description`: "The identifier of a design option set."
- `CommonSchemaDefinitions.json#/DesignOptionId/description`: "The identifier of a design option."
- `CommonSchemaDefinitions.json#/ClassificationId/description`: "The element classification identifier."
- `CommonSchemaDefinitions.json#/MEPElbowParameters/description`: "Elbow parameters. Archicad 29 or newer."
- `CommonSchemaDefinitions.json#/PhotoRenderFormat/description`: "The rendered image file format."
- `CommonSchemaDefinitions.json#/PlaceInfo/description`: "The place settings. sunAngXY and sunAngZ are the sun position Archicad calculated for the place, date and time, in radians."
- `CommonSchemaDefinitions.json#/SunPosition/description`: "The position of the sun as Archicad calculates it from a date, time and location, in degrees."
- `CommonSchemaDefinitions.json#/SunLightSettings/description`: "The sun and ambient light settings of the project."
- `CommonSchemaDefinitions.json#/ElementStateType/description`: "How GetElementChangesSince finds the changed elements between this state and another one. ModificationStamp compares the modification stamps of the elements, so any change to an element counts. 3DModel compares the 3D model of the elements, so only a change that alters the 3D model counts, and capturing it generates the 3D model of the project. Two states can only be compared when they were captured with the same type."
- `CommonSchemaDefinitions.json#/ElementStateId/description`: "The identifier of the captured state, accepted by GetElementChangesSince and ReleaseElementState. It is only valid in the Archicad session and project it was captured in."
- `CommonSchemaDefinitions.json#/ExecutionResults/description`: "A list of execution results."
- `CommonSchemaDefinitions.json#/FavoriteImportFormat/description`: "The format to import from, the counterpart of the format of ExportFavorites. prefs works in every Archicad version. xml imports Favorite files from a folder, and legacyPRF a Favorites file of earlier Archicad versions; these two require Archicad 29 or newer."
- `CommonSchemaDefinitions.json#/FavoriteConflictPolicy/description`: "What to do when a Favorite with this name already exists: Error fails, Skip leaves the existing Favorite unchanged, OverwriteExisting gives the existing Favorite the new settings (its folder does not change), RenameNew creates the Favorite with ' (2)', ' (3)', ... appended to the name."
- `CommonSchemaDefinitions.json#/PropertyIds/description`: "A list of property identifiers."
- `CommonSchemaDefinitions.json#/PenTarget/description`: "Which active Pen Table to change: the one in effect for the model views or the one in effect for the layouts. The two can be the same Pen Table."
- `CommonSchemaDefinitions.json#/LibraryPartType/description`: "Enumeration of available library part types. 'Unknown' is the schema-valid catch-all returned for any libpart whose typeID is not one of the named values (rare ACAPI sentinels and any future SDK subtype)."
- `CommonSchemaDefinitions.json#/AvailableLibraryPartType/description`: "The kind of the library part file: a GDL object, an image, a text file, a binary list criteria file or other."
- `CommonSchemaDefinitions.json#/CreatedLibraryPart/description`: "A newly created library part, in the same form as in GetAvailableLibraryParts."
- `CommonSchemaDefinitions.json#/MEPCrossSectionShape/description`: "Shape of an MEP routing segment's cross section or of an MEP port."
- `CommonSchemaDefinitions.json#/MEPDomain/description`: "The MEP domain."
- `CommonSchemaDefinitions.json#/ExecutionResult/description`: "The result of the execution."

### Referencing properties

- `ElementIFCClassificationReference/properties/source/description` → `IFCClassificationReferenceSource`: "Missing in Archicad 25, 26 and 27, where the storedOnly input chooses between the stored references and all of them."
- `AnalyticalModelVariation/properties/amVariationGuid/description` → `GuidId`: "The identifier of the analytical model variation. Archicad 27 and newer."
- `AnalyticalModelVariation/properties/renovationFilterGuid/description` → `GuidId`: "The identifier of the renovation filter of the variation. Archicad 25 and 26."
- `AnalyticalSurfaceMember/properties/lcsXVector/description` → `Coordinate3D`: "The X axis of the local coordinate system. Archicad 26 and newer."
- `AnalyticalMemberPartRef/properties/elemGuid/description` → `GuidId`: "The element of the analytical member."
- `AnalyticalRelease/properties/guid/description` → `GuidId`: "The identifier of the release."
- `AnalyticalVaryingSegment/properties/endProfile/description` → `AnalyticalCrossSection`: "Only for a tapered segment."
- `AnalyticalEdgeLoadSettings/properties/loadCaseId/description` → `GuidId`: "The load case the load belongs to."
- `AnalyticalPointLoadSettings/properties/loadCaseId/description` → `GuidId`: "The load case the load belongs to."
- `AnalyticalSurfaceLoadSettings/properties/loadCaseId/description` → `GuidId`: "The load case the load belongs to."
- `DesignOptionMoveCapability/properties/error/description` → `Error`: "The reason why the element cannot be moved. Only present when canMove is false."
- `AddOnViewpointModificationData/properties/viewpointId/description` → `AddOnViewpointId`: "The item to change."
- `TextContentChange/properties/elementId/description` → `ElementId`: "A Text element or a Label of the Text class."
- `MEPPortPair/properties/portId/description` → `Guid`: "The port to check, as returned by GetMEPPorts."
- `MEPPortPair/properties/otherPortId/description` → `Guid`: "The port to connect it to, as returned by GetMEPPorts."
- `WindowToClose/properties/databaseId/description` → `DatabaseId`: "The database shown in the window, as GetDatabases, GetContainingDatabases or GetDatabaseIdFromNavigatorItemId return it."
- `WindowToClose/properties/windowType/description` → `WindowType`: "Optional. When given, the window is only closed when its database is of this type."
- `AddOnViewpointIdArrayItem/properties/viewpointId/description` → `AddOnViewpointId`: "The identifier of the created add-on viewpoint item."
- `CreatedDatabase/properties/navigatorItemId/description` → `NavigatorItemId`: "The Project Map item of the new database, for ChangeWindow or CreateDrawings. Missing when the item could not be found."
- `MEPPreferenceTableCreationResult/properties/tableId/description` → `MEPPreferenceTableId`: "The id of a preference table, for the tableId of the preference table row commands."
- `SolidOperationResult/properties/elements/description` → `Elements`: "The morphs created by the operation."
- `AddOnViewpointDetails/properties/parentViewpointId/description` → `AddOnViewpointId`: "The identifier of the root or group the item is in. Missing when Archicad reports no parent, as for a root."
- `ClassificationSystemSummary/properties/date/description` → `Date`: "The release date of the classification system's current version."
- `BodyMaterialDetails/properties/buildingMaterialId/description` → `AttributeId`: "The building material of the body. Left out when it cannot be found among the attributes of the project."
- `DefaultCategoryValue/properties/categoryValueId/description` → `ElementCategoryValueId`: "Left out when the default has no value in this category."
- `ClassificationItemParent/properties/classificationSystemId/description` → `ClassificationSystemId`: "The classification system the item belongs to."
- `ClassificationItemParent/properties/parentClassificationItemId/description` → `ClassificationItemId`: "The parent item. Missing for a top level item of its system."
- `ClassificationVisibilityToolDefault/properties/elementType/description` → `ElementType`: "The tool default of this element type is checked."
- `ElementCutPlane/properties/basePoint/description` → `Coordinate3D`: "A point of the plane, the origin of the returned 2D coordinates."
- `ElementCutPlane/properties/axisX/description` → `Coordinate3D`: "The direction of the x axis of the returned 2D coordinates."
- `ElementCutPlane/properties/axisY/description` → `Coordinate3D`: "The direction of the y axis of the returned 2D coordinates."
- `ElementCutPlane/properties/axisZ/description` → `Coordinate3D`: "The normal of the plane."
- `BodyCutPolygons/properties/buildingMaterialId/description` → `AttributeId`: "The building material of the body. Left out when it cannot be found among the attributes of the project."
- `DrawingNumberingGridLine/properties/begC/description` → `Coordinate2D`: "The start point of the line, in layout coordinates."
- `DrawingNumberingGridLine/properties/endC/description` → `Coordinate2D`: "The end point of the line, in layout coordinates."
- `DrawingPrimitive/properties/loc/description` → `Coordinate2D`: "Point: the location. Text: the left baseline position."
- `DrawingPrimitive/properties/destBox/description` → `BoundingBox2D`: "Pict: the bounding box of the picture."
- `ElementSetDetails/properties/elements/description` → `Elements`: "The elements of the element set."
- `HotlinkDesignOptionTableDetails/properties/nodeGuid/description` → `GuidId`: "The node guid the design option table belongs to."
- `AnalyticalMemberCoordinateSystemRequest/properties/intersectingMemberPartRef/description` → `AnalyticalMemberPartRef`: "When given, the local coordinate system of memberPartRef in its intersection with this member part is returned."
- `LibraryPartTransformation/properties/location/description` → `Coordinate2D`: "The location of the referenced library part on the floor plan."
- `PropertyObjectToolDefault/properties/elementType/description` → `ElementType`: "Read the links of the element defaults of this type instead of an element."
- `MEPElementDetails/properties/routingSegmentId/description` → `ElementId`: "The routing segment the rigid segment belongs to (see GetMEPRoutingElements). RigidSegment."
- `MEPElementDetails/properties/routingNodeId/description` → `ElementId`: "The routing node the elbow or transition belongs to (see GetMEPRoutingElements). Elbow and Transition."
- `MEPElementDetails/properties/preferenceTableId/description` → `Guid`: "The guid of the elbow or transition preference table (see GetMEPPreferenceTables). Elbow and Transition, from Archicad 29."
- `MEPElementDetails/properties/widerPortId/description` → `Guid`: "The port at the wider end of the transition (see GetMEPPorts). Transition."
- `MEPElementDetails/properties/narrowerPortId/description` → `Guid`: "The port at the narrower end of the transition (see GetMEPPorts). Transition."
- `MEPPreferenceTableContainerDetails/properties/tableId/description` → `MEPPreferenceTableId`: "The id of a preference table, for the tableId of the preference table row commands."
- `ToolDefaultProperty/properties/propertyValue/description` → `PropertyValue`: "The value in the tool default, in the format of GetPropertyValuesOfElements. Only returned when includeValues is true."
- `ToolDefaultProperty/properties/error/description` → `Error`: "Why the value could not be read. Only returned when includeValues is true."
- `AttributePropertyValuesResult/properties/propertyValues/items/oneOf/1/description` → `AttributePropertyValueStatus`: "Returned when includeStatus is true."
- `AttributePropertyValueStatus/properties/propertyValue/description` → `PropertyValue`: "Missing when the value is not available or not evaluated."
- `RenovationFilterDetails/properties/renovationFilterId/description` → `GuidId`: "Identifier of the renovation filter. The same identifier is the renovationFilterGuid of GetViewSettings and SetViewSettings."
- `TextureCoordinate/properties/point/description` → `Coordinate3D`: "The first vertex of the face, in world coordinates."
- `MEPElbowDefaults/properties/preferenceTableId/description` → `Guid`: "The guid of an elbow preference table of the domain (see GetMEPPreferenceTables with includeFittingTables)."
- `MEPTransitionDefaults/properties/preferenceTableId/description` → `Guid`: "The guid of a transition preference table of the domain (see GetMEPPreferenceTables with includeFittingTables)."
- `ProjectInfoGroupMove/properties/beforeProjectInfoGroupId/description` → `ProjectInfoGroupId`: "The group to move the group before. When omitted, the group is moved to the end of the group list."
- `DesignOptionSetMove/properties/designOptionSetId/description` → `DesignOptionSetId`: "The design option set to move."
- `DesignOptionSetMove/properties/beforeDesignOptionSetId/description` → `DesignOptionSetId`: "The design option set to move it before. When it is not given, the set is moved to the end."
- `DesignOptionMove/properties/designOptionId/description` → `DesignOptionId`: "The design option to move within its set."
- `DesignOptionMove/properties/beforeDesignOptionId/description` → `DesignOptionId`: "The design option of the same set to move it before. When it is not given, the design option is moved to the end of its set."
- `AttributeClassification/properties/classificationId/description` → `ClassificationId`: "The classification to set. The item replaces the attribute's current item in the same classification system. If the classificationItemId field is omitted, the attribute becomes unclassified in the given system."
- `LinkedPropertyObjectsByToolDefault/properties/elementType/description` → `ElementType`: "Set the links of the element defaults of this type instead of an element."
- `ElementMEPRoutingParameters/properties/elbowParameters/description` → `MEPElbowParameters`: "The elbow parameters of a routing node (RoutingNode::Modifier::SetElbowDefaultParameters). Archicad 29 or newer."
- `MEPRoutingSegmentDefaults/properties/preferenceTableId/description` → `Guid`: "A segment preference table, as returned by GetMEPPreferenceTables."
- `ElementHeaderFromOtherDatabase/properties/hotlinkId/description` → `ElementId`: "The hotlink instance this element belongs to. Present only for elements that came in through a placed hotlink."
- `ActiveRenovationFilterById/properties/renovationFilterId/description` → `GuidId`: "Identifier of the renovation filter, as listed by GetRenovationFilters. Takes precedence over name when both are given."
- `ActiveRenovationFilterByName/properties/renovationFilterId/description` → `GuidId`: "Identifier of the renovation filter, as listed by GetRenovationFilters. Takes precedence over name when both are given."
- `PhotoRenderParameters/properties/format/description` → `PhotoRenderFormat`: "Optional. When omitted, the format comes from the extension of imageFilePath (.png, .jpg or .jpeg, .bmp, .tif or .tiff, .gif)."
- `SetPlaceSettingsResult/properties/placeInfo/description` → `PlaceInfo`: "The place settings read back after the change."
- `GetSunSettingsResult/properties/sunPosition/description` → `SunPosition`: "The sun position for the project's date, time and location."
- `GetSunSettingsResult/properties/sunLight/description` → `SunLightSettings`: "Missing when Archicad cannot report them."
- `CaptureElementStateParameters/properties/type/description` → `ElementStateType`: "ModificationStamp by default."
- `GetElementChangesSinceParameters/properties/stateId/description` → `ElementStateId`: "The state to compare from, as returned by CaptureElementState."
- `GetElementChangesSinceParameters/properties/toStateId/description` → `ElementStateId`: "The state to compare to, as returned by CaptureElementState with the same type as stateId. If omitted, the current state of the project is used, so the response lists what changed since stateId was captured."
- `ReleaseElementStateParameters/properties/stateId/description` → `ElementStateId`: "The state to free, as returned by CaptureElementState."
- `GetDetailsOfElementsResult/properties/detailsOfElements/items/oneOf/0/properties/hotlinkId/description` → `ElementId`: "The hotlink instance this element belongs to. Present only for elements that came in through a placed hotlink; such elements are read-only."
- `GetElementConnectionsResult/properties/executionResults/description` → `ExecutionResults`: "Aligned with the input array of elements: whether the element was found and taken into the search."
- `ImportFavoritesParameters/properties/format/description` → `FavoriteImportFormat`: "Optional, prefs by default."
- `CreateFavoriteParameters/properties/conflictPolicy/description` → `FavoriteConflictPolicy`: "Default Error."
- `GetAllPropertiesParameters/properties/properties/description` → `PropertyIds`: "Returns only the definitions of these properties. Identifiers not found in the project are left out of the response. All properties are returned when omitted."
- `ModifyPensParameters/properties/target/description` → `PenTarget`: "The model views Pen Table by default."
- `CreateLibraryPartsParameters/properties/libraryParts/items/properties/type/description` → `LibraryPartType`: "Optional. The type of the new library part. By default the type of the parent found by parentName or by a parentId GUID, and Object otherwise."
- `GetAvailableLibraryPartsResult/properties/libraryParts/items/properties/type/description` → `AvailableLibraryPartType`: "Available from Archicad 28; missing when it cannot be read."
- `CreateLibraryPartResult/properties/libraryPart/description` → `CreatedLibraryPart`: "Left out when it is not loaded."
- `GetRenovationFiltersResult/properties/activeRenovationFilterId/description` → `GuidId`: "Identifier of the renovation filter of the current window. Absent when the current window has none or it could not be read."
- `GetAddOnViewpointChildrenParameters/properties/viewpointId/description` → `AddOnViewpointId`: "The add-on viewpoint root or group to list the children of."
- `CreateAddOnViewpointsParameters/properties/viewpoints/items/properties/parentViewpointId/description` → `AddOnViewpointId`: "The root or group to create the item in. Required for a group or a leaf node, ignored for a root."
- `CreateMEPRoutingElementsParameters/properties/routingElementsData/items/properties/crossSectionShape/description` → `MEPCrossSectionShape`: "Optional; applied to all segments."
- `CreateMEPRoutingElementsParameters/properties/routingElementsData/items/properties/preferenceTableId/description` → `Guid`: "Optional guid of the segment preference table (see GetMEPPreferenceTables) applied to all segments. Not applicable to the CableCarrier domain."
- `CreateMEPRoutingElementsParameters/properties/routingElementsData/items/properties/mepSystemId/description` → `AttributeId`: "Optional MEP system attribute."
- `CreateMEPElementsParameters/properties/elementsData/items/properties/domain/description` → `MEPDomain`: "Required for all types except Equipment."
- `CreateMEPElementsParameters/properties/elementsData/items/properties/orientationDirection/description` → `Coordinate3D`: "Optional direction vector of the orientation. Defaults to (1, 0, 0)."
- `CreateMEPElementsParameters/properties/elementsData/items/properties/orientationRotation/description` → `Coordinate3D`: "Optional rotation vector of the orientation. Defaults to (0, 1, 0)."
- `ModifyMEPPreferenceTablesResult/properties/tables/description` → `ExecutionResults`: "One result for each item of tables."
- `ModifyMEPPreferenceTablesResult/properties/deletedTables/description` → `ExecutionResults`: "One result for each item of tablesToDelete."
- `ModifyMEPPreferenceTablesResult/properties/referenceSet/description` → `ExecutionResult`: "Only when referenceIdsToDelete is given."
- `ModifyMEPPreferenceTablesResult/properties/addedAngles/description` → `ExecutionResult`: "Only when anglesToAdd is given."
- `ModifyMEPPreferenceTablesResult/properties/angleSet/description` → `ExecutionResult`: "Only when anglesToDelete is given."
- `GetMEPPreferenceTableRowsParameters/properties/tableId/description` → `MEPPreferenceTableId`: "The guid of a preference table, as returned by GetMEPPreferenceTables (the branch, elbow and transition tables with includeFittingTables): a pipe or circular duct segment table, a branch or elbow table of the Piping or Ventilation domain, or, from Archicad 29, a transition table. Rectangular duct and cable carrier segment tables are found too, but their rows have no key. Archicad 27: any preference table, as returned by GetMEPPreferenceTableContainers."
- `SetMEPPreferenceTableRowsParameters/properties/tableId/description` → `MEPPreferenceTableId`: "The guid of a preference table, as returned by GetMEPPreferenceTables (the branch, elbow and transition tables with includeFittingTables): a pipe or circular duct segment table, a branch or elbow table of the Piping or Ventilation domain, or, from Archicad 29, a transition table. Rectangular duct and cable carrier segment tables are found too, but their rows have no key. Archicad 27: any preference table, as returned by GetMEPPreferenceTableContainers."
- `AddMEPPreferenceTableRowsParameters/properties/tableId/description` → `MEPPreferenceTableId`: "The guid of a preference table, as returned by GetMEPPreferenceTables (the branch, elbow and transition tables with includeFittingTables): a pipe or circular duct segment table, a branch or elbow table of the Piping or Ventilation domain, or, from Archicad 29, a transition table. Rectangular duct and cable carrier segment tables are found too, but their rows have no key. Archicad 27: any preference table, as returned by GetMEPPreferenceTableContainers."
- `DeleteMEPPreferenceTableRowsParameters/properties/tableId/description` → `MEPPreferenceTableId`: "The guid of a preference table, as returned by GetMEPPreferenceTables (the branch, elbow and transition tables with includeFittingTables): a pipe or circular duct segment table, a branch or elbow table of the Piping or Ventilation domain, or, from Archicad 29, a transition table. Rectangular duct and cable carrier segment tables are found too, but their rows have no key. Archicad 27: any preference table, as returned by GetMEPPreferenceTableContainers."
