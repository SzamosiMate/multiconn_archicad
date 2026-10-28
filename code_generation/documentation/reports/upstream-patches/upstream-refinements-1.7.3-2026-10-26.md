# Upstream schema refinements following Tapir 1.7.3

Run started: **2026-10-26**. Endpoint completed: **publish and create the upstream PR**.

- Client: Tapir **1.7.3**, local schema-patch revision `e0c4f172da8a4bfc7a9b215f7d8284b559f61afb`; patch implementation was clean at preflight.
- Upstream/fork default branch: `main`. Fast-forward fork sync completed without force.
- Exact upstream source baseline: `6323441a9000912ba1a7a6df9aaf73c7f7cff936`.
- Branch: `SzamosiMate:schema/refinements-1.7.3`.
- Final commit and verified remote tip: `fde941fa575ca358f7f15a4e3d54a715d1e47b6a`.
- [PR #1557: Refine API schemas following Tapir 1.7.3](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1557), open, ready for review and confirmed mergeable against the recorded base.
- Previous [PR #1386](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1386) remains open/unmerged; its recorded head `e7bcf0bb6aad030333239d3b7052485c20967e9c` was preserved. This proposal starts directly from upstream main, has no newly introduced definition-name collisions with that batch, and requires none of its definitions.

The [active queue](../../schema-patch-tracking.md) holds source/PR state, deferred consumers and retirement conditions. The [condensed 1.7.3 generation record](../codegen/tapir-1.7.3.md#temporary) preserves the decisions; the expanded historical operation/path inventory remains at `776808e:code_generation/documentation/reports/codegen/tapir-1.7.3.md` in Git and is not repeated here.

## Decisions and source review

**159 of 161 new Temporary operations implemented**, yielding **133 named definitions**: 78 inline-object/scalar extractions, 32 union-success extractions, 21 enum extractions, one database conditional-variant operation and 27 shared-reference replacements. Two cross-batch reference replacements remain deferred. Counts are expanded helper operations, not definitions or PR boundaries. Existing Permanent naming workarounds and the older 80 Temporary operations were not republished.

| Decision | Original source paths and consumers | Source result and compatibility |
| --- | --- | --- |
| Database selection and result identity | `DatabaseIdAndWindowType`; `GetDetailsOfElements` response success branch; result branches across element, navigator, attribute, geometry and project commands | Name complete database alternatives and success objects. Preserve `anyOf` versus `oneOf`, branch order, constraints and error alternatives. Database selectors still require window type or ID and allow both. `DetailsOfElement` retains the optional field-filter qualification. |
| Preference pages and formats | `GetProjectPreferences` read pages and `SetProjectPreferences` input pages; `GetCalculationUnits` area, volume and angle | Read pages/formats retain complete required fields; updates retain empty required lists and partial-update behavior. Reuse angle formats across working/calculation pages and six equivalent length-dimension slots per read/update page. Remove the seven superseded static schema helpers. Legacy calculation length remains separate because it has additional optional `roundInch`; area, volume and angle receive three further equivalent references. |
| Openings and 3D settings | `GetOpeningDetails`, `SetOpeningDetails`, `GetOpeningDefault`, floor-plan getter/setter; `Get3DStyleDetails`, `Create3DStyles`, `Change3DStyles`; cut-plane getter/setter | Share equivalent extrusion read/default shapes, while keeping extrusion updates and floor-plan read/default/update variants distinct. All three 3D style consumers have the same schema requiredness and may share `Style3DDetails`; caller-specific create/change effects stay on their arrays. Share `CutPlane`, remove superseded C++ schema constants, and retain all geometric constraints. |
| Domain enums and repeated values | Beam/column segment structure; routing segment/read and routing modification anchors; IFC properties; favorite/export/image options; hierarchy, layout, database and preference selections; structure-display getter/setter | Name accepted existing values without adding/tightening enums. Preserve spellings and order. Keep defaults and command restrictions at callers. The routing modification anchor applies to all segments, unlike its per-segment read consumer. |
| Command payloads and nested result data | Favorites, attributes, IFC, library, categories/links, geometry/measurement/regularization, project data and Teamwork source schemas | Give the selected contracts explicit upstream names. Share `User` while retaining `reservedBy` versus `owner` absence/meaning notes. Share the nonempty `ProjectDataName` in six name-list consumers. Preserve distinct read/write category and project-data shapes, success/error wrappers, and ancestry availability notes. |

Five commands newly opt into `CommonSchema::Used`: `GetPrinterInfo`, `GetReservationStatusOfElements`, `GetStructureDisplay`, `Set3DCutPlanes` and `Get3DCutPlanes`. All other affected commands already have direct or inherited common-schema access.

### Deferred dependencies and annotation issue

- `FavoriteSettings/marker` stays inline because `MarkerParametersOfElement` is proposed in #1386. Current source uses `StoredGDLParameter`; the older proposal uses its earlier `MarkerGDLParameterDetails` contract and must be reviewed against current requiredness when integrated. The future reference must preserve the favorite-specific absence note. The downstream replacement currently omits that annotation (acceptance is equivalent); no client patch implementation was changed in this upstream-only run.
- `DeleteMEPPhysicalSystemsParameters/physicalSystems/items` stays inline because its equivalent `MEPPhysicalSystemIdArrayItem` is proposed in #1386. No substitute definition is duplicated in this PR.

These omissions keep this proposal independent; they do not claim that downstream patch operations can be removed yet. Both PRs touch common source areas and may need ordinary conflict resolution when integrated.

## Validation and limits

- Interpreted the complete source using current upstream `tools/generate_addon_docs.py`, in memory. Cached the baseline once. A scratch-only prefilter skips files lacking a function's qualified identifiers before invoking the official interpreter's existing lookup; no repository tooling was edited.
- Interpreted final source exactly matches the reviewed transformation plan: **430 commands**, **1,353 baseline definitions**, **133 new definitions**, **72 directly affected commands**.
- Complete schema-aware structural comparison passed for every baseline definition (**24,103 compared nodes**), retaining fields, types, requiredness, additional-property rules, bounds, enum order and union/error semantics. Conditional required-only alternatives are compared to their distributed complete variants. Reference siblings and recursive pairs are handled explicitly; constraint-bearing reference siblings are rejected rather than silently discarded.
- Every interpreted reference resolves to a common definition; all affected commands have common-schema access. New names have no collisions with source or pending #1386 definitions.
- All **133 new named contracts** match the released patched client after reference normalization and constraint-preserving comparison. `FavoriteSettings` differs only by its intentionally deferred inline marker versus the client's shared reference. These exact upstream names require no new aliases; release adoption must still review pre-existing aliases and all consumers.
- Actual `docs/archicad-addon/renderer.js` resolved **796 command schemas**, preserving **83 reference/definition description pairs** with no definition mutation or caller-context leakage. Full strings/locations follow below.
- Reviewed removed annotation strings: defaults, restrictions and ancestry notes were split between definitions and callers; reservation-user absence notes were explicitly retained. No acceptance change or SDK enum inference was introduced.
- Non-schema execution code is unchanged; only schema method bodies, retired schema-only helpers/constants and the five common-schema opt-ins differ.
- `git diff --check` passed. **Archicad 29 Windows Debug SDK build passed**, including a final incremental resource build after the annotation edits. The initial full link reported the SDK's missing `API_c.pdb` debug-symbol warning (LNK4099); the add-on linked successfully.
- No live Archicad command execution, other SDK version build or macOS build was performed. GitHub CI is separate from the local SDK result: the final snapshot had Grasshopper successful, Installer in progress and Archicad Add-On queued.
- Only 25 intended Tapir source files were committed. Generated docs, release pins, client models, aliases and patch implementations were not edited. The pre-existing untracked `.idea/` directory was preserved. This report is staged in the MultiConn checkout; active queue changes remain unstaged.

## Submitted PR text

```markdown
# Refine API schemas following Tapir 1.7.3

Give the API payloads introduced or extended in Tapir 1.7.3 stable named schemas and reuse equivalent contracts across commands.

| Area | Changes |
| --- | --- |
| Project and view settings | Name preference pages and unit formats, preserving separate complete-read and partial-update contracts; share 3D styles, cut planes and structure-display modes. |
| Elements and geometry | Name opening read/update shapes, result-success branches, category/link details, measurement results and regularization ancestry. |
| Command payloads and options | Name favorites, attributes, IFC, library, Teamwork and project-data payloads and enums; reuse matching user, anchor and project-data-name contracts. |
| Database selection | Name the window-type and database-ID alternatives while preserving the existing `anyOf` selection rules. |

This PR is based directly on current upstream `main` and can merge independently of #1386. The favorite-marker and physical-system-ID references that need definitions from that PR are deferred.

Fields, requiredness, bounds, enum values/order and success/error alternatives remain equivalent. Generated client type names can change. Caller defaults, restrictions and absence notes remain documented.
```

## Retained reference and definition descriptions

Locations below are interpreted command-schema paths or common-definition paths. Command `Parameters`/`Result` paths correspond to their source `GetInputParametersSchema`/`GetRawResponseSchema`; common definitions live in `archicad-addon/Sources/RFIX/Images/CommonSchemaDefinitions.json`. Existing description pairs carried through a changed enclosing object are included, as well as newly split descriptions.

- Reference `MEPRoutingSegmentDetails/properties/preferenceTableId/description`: "The guid of the segment preference table used by the segment (see GetMEPPreferenceTables)."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `MEPRoutingSegmentDetails/properties/beginNodeId/description`: "The routing node at the beginning of the segment."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `MEPRoutingSegmentDetails/properties/endNodeId/description`: "The routing node at the end of the segment."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `MEPRoutingSegmentDetails/properties/rigidSegments/description`: "The rigid segments (the straight duct, pipe or cable carrier pieces) of the routing segment."
  Definition `CommonSchemaDefinitions.json#/Elements/description`: "A list of elements."

- Reference `ColumnSegmentDetails/properties/ownerElementId/description`: "The Column element the segment belongs to."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `ColumnSegmentDetails/properties/buildingMaterialId/description`: "Present when the cross section uses a building material rather than a custom profile."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `ColumnSegmentDetails/properties/profileId/description`: "Present when the cross section uses a custom extruded profile rather than a building material."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `BeamSegmentDetails/properties/ownerElementId/description`: "The Beam element the segment belongs to."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `BeamSegmentDetails/properties/buildingMaterialId/description`: "Present when the cross section uses a building material rather than a custom profile."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `BeamSegmentDetails/properties/profileId/description`: "Present when the cross section uses a custom extruded profile rather than a building material."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `DatabaseByWindowType/properties/databaseId/description`: "The database to activate. When windowType is omitted, the window type is taken from the database; when both are given, they must match."
  Definition `CommonSchemaDefinitions.json#/DatabaseId/description`: "The identifier of a database"

- Reference `DatabaseById/properties/databaseId/description`: "The database to activate. When windowType is omitted, the window type is taken from the database; when both are given, they must match."
  Definition `CommonSchemaDefinitions.json#/DatabaseId/description`: "The identifier of a database"

- Reference `DetailsOfElement/properties/hotlinkId/description`: "The hotlink instance this element belongs to. Present only for elements that came in through a placed hotlink; such elements are read-only."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `OpeningRevealOffsetData/properties/elementId/description`: "A window or door placed in a wall."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `FavoriteSummary/properties/elementType/description`: "The element type of the Favorite. Missing when Archicad cannot read the Favorite's element settings."
  Definition `CommonSchemaDefinitions.json#/ElementType/description`: "The type of an element."

- Reference `ElementMirrorData/properties/mirrorAxis/properties/beginPoint/description`: "First point of the mirror axis."
  Definition `CommonSchemaDefinitions.json#/Coordinate2D/description`: "2D coordinate."

- Reference `ElementMirrorData/properties/mirrorAxis/properties/endPoint/description`: "Second point of the mirror axis. Must differ from beginPoint."
  Definition `CommonSchemaDefinitions.json#/Coordinate2D/description`: "2D coordinate."

- Reference `GraphicOverrideRuleMove/properties/beforeGraphicOverrideRuleId/description`: "The rule of the target group the moved rule is put in front of. Left out: the rule becomes the last of the group."
  Definition `CommonSchemaDefinitions.json#/GraphicOverrideRuleId/description`: "The identifier of a graphic override rule."

- Reference `ElementCategoryValueData/properties/categoryValueId/description`: "A value of the category given by type, as GetElementCategories lists them."
  Definition `CommonSchemaDefinitions.json#/ElementCategoryValueId/description`: "The identifier of a value of an element category."

- Reference `OpeningModificationData/properties/parentElementId/description`: "The new element the opening belongs to."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `Style3DDetails/properties/monochromeSurfaceColor/description`: "The surface color of the monochrome model."
  Definition `CommonSchemaDefinitions.json#/ColorRGB/description`: "RGB color."

- Reference `Style3DDetails/properties/monochromeContourColor/description`: "The contour color of the monochrome model."
  Definition `CommonSchemaDefinitions.json#/ColorRGB/description`: "RGB color."

- Reference `Style3DDetails/properties/backgroundSkyColor/description`: "The sky color of the background (API_3DStyle.bkgSkyColor)."
  Definition `CommonSchemaDefinitions.json#/ColorRGB/description`: "RGB color."

- Reference `Style3DDetails/properties/backgroundColor/description`: "The (ground) color of the background (API_3DStyle.backGroundRGB)."
  Definition `CommonSchemaDefinitions.json#/ColorRGB/description`: "RGB color."

- Reference `DrawingContentBox/properties/contentBox/description`: "The full boundary box of the Drawing's content, independent of its frame, as returned by Archicad."
  Definition `CommonSchemaDefinitions.json#/BoundingBox2D/description`: "A two-dimensional bounding box defined by its minimum and maximum coordinates."

- Reference `HierarchicalElementOwner/properties/ownerElementId/description`: "The owner element. For a main element (e.g. a Curtain Wall) or an element that is not part of a hierarchical element, Archicad returns the input element itself."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `OpeningDetails/properties/parentElementId/description`: "The element the opening was placed in. Left out when the opening has none."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `OpeningTransformation/properties/origin/description`: "The origin of the opening's local coordinate system in world coordinates, from localToGlobal. Missing when globalToLocal cannot be inverted."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningTransformation/properties/xAxis/description`: "The local X axis in world coordinates, from localToGlobal. Missing when globalToLocal cannot be inverted."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningTransformation/properties/yAxis/description`: "The local Y axis in world coordinates, from localToGlobal. Missing when globalToLocal cannot be inverted."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningTransformation/properties/zAxis/description`: "The local Z axis in world coordinates, from localToGlobal. Missing when globalToLocal cannot be inverted."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `RegularizedPolyline/properties/ancestry/description`: "Only with withAncestry."
  Definition `CommonSchemaDefinitions.json#/PolylineAncestry/description`: "Read from the vertexAncestry and edgeAncestry of Archicad's API_RegularizedPoly; -1 marks a vertex or edge that Archicad created (for example at a self-intersection)."

- Reference `ElementLinkDetails/properties/elementId/description`: "The element the link points to."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `HotlinkProxyElement/properties/proxyElementId/description`: "The proxy element in the current project."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `HotlinkProxyElement/properties/sourceElementId/description`: "The element in the hotlink's source file the proxy was made from."
  Definition `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."

- Reference `OpeningGeometry/properties/anchorPoint/description`: "The anchor point of the opening in world coordinates."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningGeometry/properties/extrusionDirection/description`: "The direction the opening is extruded in."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningGeometry/properties/xAxis/description`: "The X axis of the plane of the opening's polygon."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningGeometry/properties/yAxis/description`: "The Y axis of the plane of the opening's polygon."
  Definition `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."

- Reference `OpeningExtrusionParameters/properties/extrusionSurfaceId/description`: "The surface of the extrusion faces. Only given when it is overridden."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningExtrusionParameters/properties/endSurfaceId/description`: "The surface of the end faces. Only given when it is overridden."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningExtrusionParametersUpdate/properties/extrusionSurfaceId/description`: "The surface of the extrusion faces. Only used when the surface is overridden."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningExtrusionParametersUpdate/properties/endSurfaceId/description`: "The surface of the end faces. Only used when the surface is overridden."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningDefaultFloorPlanParameters/properties/referenceAxisLineTypeId/description`: "The line type of the reference axis."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningDefaultFloorPlanParameters/properties/coverFillId/description`: "The fill of the cover fills."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningDefaultFloorPlanParameters/properties/coverFillTransformation/description`: "The orientation and distortion of the cover fill. Left out when Archicad gives none."
  Definition `CommonSchemaDefinitions.json#/CoverFillTransformation/description`: "Orientation and distortion parameters of a cover fill."

- Reference `OpeningDefaultFloorPlanParameters/properties/cutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the cut opening. Left out when the opening has no cut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `OpeningDefaultFloorPlanParameters/properties/unCutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the uncut opening. Left out when the opening has no uncut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `OpeningFloorPlanParameters/properties/referenceAxisLineTypeId/description`: "The line type of the reference axis."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningFloorPlanParameters/properties/coverFillId/description`: "The fill of the cover fills."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningFloorPlanParameters/properties/coverFillTransformation/description`: "The orientation and distortion of the cover fill. Left out when Archicad gives none."
  Definition `CommonSchemaDefinitions.json#/CoverFillTransformation/description`: "Orientation and distortion parameters of a cover fill."

- Reference `OpeningFloorPlanParameters/properties/cutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the cut opening. Left out when the opening has no cut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `OpeningFloorPlanParameters/properties/unCutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the uncut opening. Left out when the opening has no uncut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `OpeningFloorPlanParametersUpdate/properties/referenceAxisLineTypeId/description`: "The line type of the reference axis."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningFloorPlanParametersUpdate/properties/coverFillId/description`: "The fill of the cover fills."
  Definition `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."

- Reference `OpeningFloorPlanParametersUpdate/properties/coverFillTransformation/description`: "The orientation and distortion of the cover fill. Left out when Archicad gives none."
  Definition `CommonSchemaDefinitions.json#/CoverFillTransformation/description`: "Orientation and distortion parameters of a cover fill."

- Reference `OpeningFloorPlanParametersUpdate/properties/cutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the cut opening. Left out when the opening has no cut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `OpeningFloorPlanParametersUpdate/properties/unCutSymbolLibPartId/description`: "The id of the library part drawn as the symbol of the uncut opening. Left out when the opening has no uncut symbol."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `RegularizedPolygon/properties/ancestry/description`: "Only with withAncestry."
  Definition `CommonSchemaDefinitions.json#/PolygonAncestry/description`: "Read from the vertexAncestry and edgeAncestry of Archicad's API_RegularizedPoly; -1 marks a vertex or edge that Archicad created (for example at a self-intersection)."

- Reference `DimensionPreferences/properties/linear/description`: "The format of the linear dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferences/properties/radial/description`: "The format of the radial dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferences/properties/level/description`: "The format of the level dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferences/properties/elevation/description`: "The format of the elevation dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferences/properties/doorWindow/description`: "The format of the door, window and skylight dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferences/properties/parapet/description`: "The format of the sill height (parapet) dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormat/description`: "The format of a length dimension."

- Reference `DimensionPreferencesUpdate/properties/linear/description`: "The format of the linear dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `DimensionPreferencesUpdate/properties/radial/description`: "The format of the radial dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `DimensionPreferencesUpdate/properties/level/description`: "The format of the level dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `DimensionPreferencesUpdate/properties/elevation/description`: "The format of the elevation dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `DimensionPreferencesUpdate/properties/doorWindow/description`: "The format of the door, window and skylight dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `DimensionPreferencesUpdate/properties/parapet/description`: "The format of the sill height (parapet) dimensions."
  Definition `CommonSchemaDefinitions.json#/LengthDimensionFormatUpdate/description`: "The fields of a length dimension format to change."

- Reference `GetCurrentViewImageParameters/properties/source/description`: "Optional, 3DWindow by default."
  Definition `CommonSchemaDefinitions.json#/ViewImageSource/description`: "The window whose image is returned: the 3D window, or the PhotoRendering window."

- Reference `GetCurrentViewImageParameters/properties/format/description`: "Optional, png by default."
  Definition `CommonSchemaDefinitions.json#/ViewImageFormat/description`: "The image format."

- Reference `GetHierarchicalElementOwnersParameters/properties/elements/description`: "The elements whose owners are looked up, e.g. Curtain Wall frames or panels, Stair treads or Railing posts."
  Definition `CommonSchemaDefinitions.json#/Elements/description`: "A list of elements."

- Reference `GetHierarchicalElementOwnersParameters/properties/ownerMode/description`: "root by default."
  Definition `CommonSchemaDefinitions.json#/HierarchicalOwnerMode/description`: "root: the root of the hierarchical element tree, e.g. the Curtain Wall, Stair or Railing. parent: the immediate parent, which may itself be a subelement."

- Reference `ExportFavoritesParameters/properties/format/description`: "prefs (the default) works in every Archicad version. xml exports each Favorite to its own file in the folder, and legacyPRF exports to a Favorites file of earlier Archicad versions; these two require Archicad 29 or newer."
  Definition `CommonSchemaDefinitions.json#/FavoriteExportFormat/description`: "Favorite export file format."

- Reference `GetPropertyDefinitionsOfAttributesParameters/properties/filter/description`: "The default is UserDefined."
  Definition `CommonSchemaDefinitions.json#/AttributePropertyDefinitionFilter/description`: "Which property definitions to return: the user defined (custom) ones, the fundamental built-in ones, or all of them."

- Reference `CreateLayoutParameters/properties/layoutsData/items/properties/previousNavigatorItemId/description`: "The sibling after which the new layout is placed, as in MoveNavigatorItem. It must be a child of parentNavigatorItemId (or of the Layout Book root when that is omitted). Cannot be combined with position."
  Definition `CommonSchemaDefinitions.json#/NavigatorItemId/description`: "The identifier of a navigator item."

- Reference `CreateLayoutParameters/properties/layoutsData/items/properties/position/description`: "Archicad inserts new layouts at the first place, which renumbers the sheets after them; \"last\" appends it after the existing children instead. Cannot be combined with previousNavigatorItemId."
  Definition `CommonSchemaDefinitions.json#/LayoutInsertionPosition/description`: "Position of a new layout among its parent's children."

- Reference `ModifyMEPRoutingElementsParameters/properties/routingElementsData/items/properties/crossSectionShape/description`: "The new shape is applied to all segments."
  Definition `CommonSchemaDefinitions.json#/MEPCrossSectionShape/description`: "Shape of an MEP routing segment's cross section."

- Reference `ModifyMEPRoutingElementsParameters/properties/routingElementsData/items/properties/preferenceTableId/description`: "New segment preference table (guid as returned by GetMEPPreferenceTables) applied to all segments. Not applicable to the CableCarrier domain."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `ModifyMEPRoutingElementsParameters/properties/routingElementsData/items/properties/branchPreferenceTableId/description`: "New branch preference table (guid as returned by GetMEPPreferenceTables) of the routing element."
  Definition `CommonSchemaDefinitions.json#/Guid/description`: "A Globally Unique Identifier (or Universally Unique Identifier) in its string representation as defined in RFC 4122."

- Reference `ModifyMEPRoutingElementsParameters/properties/routingElementsData/items/properties/anchor/description`: "Applied to all segments of the routing element."
  Definition `CommonSchemaDefinitions.json#/MEPRoutingAnchor/description`: "The anchor point of the cross section, on a 3x3 grid."

