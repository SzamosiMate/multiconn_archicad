# Upstream API schema refinements following Tapir 1.7.2

Run started **2026-10-20** using MultiConn's `multiconn-upstream-patches` skill and its default publish endpoint.

## Published result

- Reviewed client release **1.7.2** at client/patch revision `8e27852e838af645d35055d8af83ed5404f6fc87` on `update-to-tapir-1.7.2`. Released unpatched/master inputs and the current patch implementation were read before implementation.
- Upstream: `ENZYME-APD/tapir-archicad-automation`; fork: `SzamosiMate/tapir-archicad-automation`; both default branches are `main`. The fork was fast-forward synced first. Both baselines were verified as `8c607d93c94200ed69496fae145c9aed53810f4d`, including a fresh check before publication.
- Published [`schema/refinements-1.7.2`](https://github.com/SzamosiMate/tapir-archicad-automation/tree/schema/refinements-1.7.2), final commit [`e7bcf0bb6aad030333239d3b7052485c20967e9c`](https://github.com/SzamosiMate/tapir-archicad-automation/commit/e7bcf0bb6aad030333239d3b7052485c20967e9c). `git ls-remote` independently verified the remote tip. One source-only commit changes 12 C++ command files and the common JSON resource; Tapir remains on that branch.
- Existing proposals were checked: earlier schema proposals, including [#1056](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/1056), are merged. No existing open proposal from this fork covered this queue, and the new branch name was unused. No PR was created.

The [active queue](../../schema-patch-tracking.md) owns original paths, grouped operations, publication status and retirement conditions; this report does not duplicate its inventory. All **82 expanded review operations** are represented: 60 naming/conditional operations and 22 shared-reference replacements, yielding **63 new common definitions**. No acceptance correction or tightening was necessary.

## Decisions and compatibility

The request selects the complete tracked naming/sharing queue, including older undecided candidates. This supplies the naming-convergence scope for equivalent extractions; anonymous valid schemas are not treated as defects. Named domain contracts and conditional alternatives provide stable public identities and allow meaningful reuse. The established creation/modification lists and generator implementation fixes remain local.

- **Settings/identity:** electrical read/add objects match; grid read/default items match, while creation items stay separate with name/value required. Read/write text-frame enums share their values and version notes. Graphical RGB reuses existing `ColorRGB` without new bounds. Active combination read/selection IDs reuse `GraphicOverrideCombinationId`.
- **Graphic overrides:** positive/negative criteria share enum identities with neutral general descriptions; equality/inequality text stays at its applicable property. Structured profile/custom-property operands retain distinct operator types and descriptive restrictions. Related schemas and `GraphicOverrideCriterion.cpp` were inspected: filtering versus editing spellings, roof versus shell cut-body values, and slab versus roof edge modes prevent further merging. Equal values alone do not justify conflating column coating with composite-skin roles.
- **Named results/inputs:** readback and rename payloads remain distinct from creation/modification data. Geometry index lists/minimum lengths, quantity alternatives/component identities, distinct MEP row dimensions/requiredness, unstrengthened identifier strings and MEP error alternatives are preserved. Image inference/defaults and grid length-mode behavior stay on their referencing fields.
- **Retained candidates:** hotlink relinking and refreshing stay distinct. Marker definitions preserve the complete current source, including `itemDescriptions` added after the reviewed release input. Generic GDL, marker and grid detail schemas differ in required fields, additional-property rules and available data; they are not merged simply because some fields match.
- **Conditional alternatives:** holes retain exclusive outline/legacy-coordinate `oneOf`; text retains inclusive text/runs `anyOf`, including acceptance of both and documented runs precedence; active combination selection retains exclusive identifier/name `oneOf`. Full shared fields/constraints are copied into named alternatives. Neither branch loses its optional fields.
- **Client placement discrepancy:** the report/queue calls the two `Hole2D`/`TextData` operations Temporary, but their actual calls still run at the end of `apply_permanent_patches`. They are included through explicit active-queue scope. Client implementation was not reclassified or edited; later retirement must remove calls at their actual locations.

No existing upstream public definition is renamed or removed. Generated type names may change despite equivalent wire acceptance. This proposal uses the current MultiConn destination names, so no new compatibility aliases are anticipated; recheck final released names. Models, pinned release and client patches were not regenerated or retired.

## Validation and limits

- Interpreted the complete current C++ source with Tapir's actual `tools/generate_addon_docs.py`, using Archicad 30 (its newest supported documentation target), with a cached baseline and scratch-only output. All **314 commands / 584 command-side schemas** parse and exactly match the reviewed transformation.
- Compared all **1,121 original common/command schemas**, checking **19,136 structural nodes** through memoized recursive reference-pair comparison. Schema annotations are separated from validation, preserving property-map fields literally named `description`. Required-only conditional unions are distributed into full contracts; validation siblings on references fail loudly instead of being silently merged/discarded. Fields, types, requiredness, additional properties, bounds, enum value/order, recursion and union keywords all match.
- All references resolve to actual common definitions, with no new-name collisions. All **24 affected commands** use `CommonSchema::Used`, directly or through `CreateElementsCommandBase`; no constructor edits are needed. Stripping raw schema literals confirms execution/constructors are unchanged, allowing only the intended grid readback string-composition replacement.
- **34 representative JSON Schema acceptance cases** pass on baseline and proposal: missing/extra fields, positive/negative enums, recursive criteria, electrical required fields, grid creation, hole exclusivity, text/runs coexistence, active selection exclusivity and array bounds.
- Executed the actual target-branch renderer's `ResolveReferences`/`EnsureRenderableSchemas` over all **584 schemas**. All **46 double-description pairs** preserve general/caller strings in order; shared definitions remain unchanged, plain references retain general meaning, and caller context does not leak. Negative wall-complexity criteria do not inherit equality wording. This covers renderer preparation, without browser DOM/screenshot validation.
- `git diff --check` passed. Generated docs were neither edited nor committed. No SDK build or live Archicad request was performed; these checks establish source-schema/renderer equivalence, not cross-version binaries or integration behavior.

Scratch material is untracked under `tmp/upstream172/`. Durable report/tracking changes remain unstaged. MultiConn temporarily switched to `main` during the run; the user selected `update-to-tapir-1.7.2` for these records, and the checkout was returned to that branch without changing its commit.

## Copyable PR text

```markdown
# Refine API schemas following Tapir 1.7.2

Give API payloads and domain values stable named definitions, and share equivalent contracts across their consumers.

| Area | Changes |
| --- | --- |
| Settings | Share electrical settings, grid read parameters, text-frame shapes, graphic-override IDs and RGB colors. |
| Graphic overrides | Name criterion enums and structured operands; share comparison enums with equality/inequality descriptions at their callers. |
| Results and inputs | Name geometry/quantity results, MEP rows and ID wrappers, grid/override readback, rename payloads, hotlink/marker inputs and image options. |
| Conditional schemas | Name hole, text-content and active-combination alternatives while preserving `oneOf`/`anyOf` behavior. |

The hole and text-content schemas predate Tapir 1.7.2 and are included as older refinements. Complete named alternatives make their required-field choices visible in Tapir's documentation, whose viewer currently hides requirements expressed in required-only union branches.

Command payloads and schema acceptance remain equivalent, including read/write differences, required fields, bounds and enum values. Generated client type names can change when adopting the named definitions. Caller defaults and restrictions remain documented alongside shared meaning.
```

## Retained reference and definition descriptions

Interpreted command roots ending in `Parameters`/`Result` identify their C++ schema methods; other roots live in the common JSON resource. Pairs already present inside moved definitions or unchanged properties of an affected command are included. Each general definition is quoted once; caller locations/strings are listed separately.

### Shared definitions

- `CommonSchemaDefinitions.json#/GraphicOverrideElementType/description`: "The tool an element was created with. Limited to tools that are not backed by a built-in GDL library part (Door, Window, Object, Lamp, Zone, Label, Grid and most MEP part types are intentionally excluded - their identification relies on a library part guid that was confirmed to differ across ArchiCAD builds, so it cannot be hardcoded reliably)."
- `CommonSchemaDefinitions.json#/GraphicOverrideStructureType/description`: "Structure type used in graphic override criteria for walls, beams and columns."
- `CommonSchemaDefinitions.json#/GraphicOverrideWallComplexity/description`: "Wall complexity used in graphic override criteria."
- `CommonSchemaDefinitions.json#/WallReferenceLineLocation/description`: "The Core* values only have an effect on a Composite or Profile wall (structureType) - a Basic wall has no core skin, and Archicad falls back to the nearest non-core equivalent (e.g. CoreCenter becomes Center)."
- `CommonSchemaDefinitions.json#/GraphicOverrideWallGeometryType/description`: "Wall geometry type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideColumnCoatingType/description`: "Column coating type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideColumnCrossSectionType/description`: "Column cross-section type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/SlabReferencePlaneLocation/description`: "Location of the slab reference plane."
- `CommonSchemaDefinitions.json#/GraphicOverrideSlabEdgeAngle/description`: "Slab edge angle mode used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideRoofCutBodyType/description`: "Roof cut body type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideRoofEaveOverhangType/description`: "Roof eave overhang type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideRoofEdgeAngle/description`: "Roof edge angle mode used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideRoofGeometryType/description`: "Roof geometry type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideShellCutBodyType/description`: "Shell cut body type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideShellGeometryType/description`: "Shell geometry type used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverridePenReplacement/description`: "Pen replacement rule used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverrideStructuralFunction/description`: "Structural function used in graphic override criteria."
- `CommonSchemaDefinitions.json#/GraphicOverridePosition/description`: "Element position used in graphic override criteria."
- `CommonSchemaDefinitions.json#/Coordinate3D/description`: "3D coordinate."
- `CommonSchemaDefinitions.json#/Justification/description`: "Text justification."
- `CommonSchemaDefinitions.json#/TextStyleSettableDetails/description`: "Every user-configurable style setting of a Text or a text-class Label (API_TextType). Shared by CreateTexts/CreateLabels ('style'), ModifyTexts/ModifyLabels ('style'), and the Get response."
- `CommonSchemaDefinitions.json#/ElementId/description`: "The identifier of an element."
- `CommonSchemaDefinitions.json#/Coordinate2D/description`: "2D coordinate."
- `CommonSchemaDefinitions.json#/AttributeId/description`: "The identifier of an attribute."
- `CommonSchemaDefinitions.json#/GraphicOverrideCombinationId/description`: "The identifier of a graphic override combination."
- `CommonSchemaDefinitions.json#/ImageFormat/description`: "Image file format."
- `CommonSchemaDefinitions.json#/ImageColorDepth/description`: "Image color depth, as in the Save as picture dialog."
- `CommonSchemaDefinitions.json#/GridElementLengthMode/description`: "How a grid element's line length is applied."
- `CommonSchemaDefinitions.json#/PerspectiveProjectionParameters/description`: "The parameters of a perspective projection of the 3D window."
- `CommonSchemaDefinitions.json#/AxonometricProjectionParameters/description`: "The parameters of an axonometric projection."
- `CommonSchemaDefinitions.json#/ColorRGB/description`: "RGB color."

### Referencing properties

- `GraphicOverrideCriterion/properties/elementType/description` → `GraphicOverrideElementType`: "Matches elements created with this tool."
- `GraphicOverrideCriterion/properties/structureType/description` → `GraphicOverrideStructureType`: "Matches elements whose structure type (Wall/Beam/Column basic vs. composite vs. complex profile) equals this value."
- `GraphicOverrideCriterion/properties/wallComplexity/description` → `GraphicOverrideWallComplexity`: "Matches walls whose complexity equals this."
- `GraphicOverrideCriterion/properties/wallComplexityNot/description` → `GraphicOverrideWallComplexity`: "Matches walls whose complexity is NOT this."
- `GraphicOverrideCriterion/properties/wallReferenceLinePosition/description` → `WallReferenceLineLocation`: "Matches walls whose reference line position equals this."
- `GraphicOverrideCriterion/properties/wallGeometryType/description` → `GraphicOverrideWallGeometryType`: "Matches walls whose geometry type equals this."
- `GraphicOverrideCriterion/properties/columnCoatingType/description` → `GraphicOverrideColumnCoatingType`: "Matches columns whose coating type equals this."
- `GraphicOverrideCriterion/properties/columnCrossSectionType/description` → `GraphicOverrideColumnCrossSectionType`: "Matches columns whose cross section type equals this."
- `GraphicOverrideCriterion/properties/slabReferencePlaneLocation/description` → `SlabReferencePlaneLocation`: "Matches slabs whose reference plane location equals this."
- `GraphicOverrideCriterion/properties/slabEdgeAngle/description` → `GraphicOverrideSlabEdgeAngle`: "Matches slabs whose edge angle mode equals this."
- `GraphicOverrideCriterion/properties/roofCutBodyType/description` → `GraphicOverrideRoofCutBodyType`: "Matches roofs whose cut body type equals this."
- `GraphicOverrideCriterion/properties/roofEaveOverhangType/description` → `GraphicOverrideRoofEaveOverhangType`: "Matches roofs whose eave overhang type equals this."
- `GraphicOverrideCriterion/properties/roofEdgeAngle/description` → `GraphicOverrideRoofEdgeAngle`: "Matches roofs whose edge angle mode equals this."
- `GraphicOverrideCriterion/properties/roofGeometryType/description` → `GraphicOverrideRoofGeometryType`: "Matches roofs whose geometry type equals this."
- `GraphicOverrideCriterion/properties/shellCutBodyType/description` → `GraphicOverrideShellCutBodyType`: "Matches shells whose cut body type equals this."
- `GraphicOverrideCriterion/properties/shellGeometryType/description` → `GraphicOverrideShellGeometryType`: "Matches shells whose geometry type equals this."
- `GraphicOverrideCriterion/properties/penReplacement/description` → `GraphicOverridePenReplacement`: "Matches elements whose pen replacement rule equals this value."
- `GraphicOverrideCriterion/properties/penReplacementNot/description` → `GraphicOverridePenReplacement`: "Matches elements whose pen replacement rule does not equal this value."
- `GraphicOverrideCriterion/properties/structuralFunction/description` → `GraphicOverrideStructuralFunction`: "Matches elements whose structural function equals this value."
- `GraphicOverrideCriterion/properties/structuralFunctionNot/description` → `GraphicOverrideStructuralFunction`: "Matches elements whose structural function does not equal this value."
- `GraphicOverrideCriterion/properties/position/description` → `GraphicOverridePosition`: "Matches elements whose position equals this value."
- `GraphicOverrideCriterion/properties/positionNot/description` → `GraphicOverridePosition`: "Matches elements whose position does not equal this value."
- `TextDataWithText/properties/coordinate/description` → `Coordinate3D`: "The placement position of the text. The z value is used to determine the floor when floorIndex is omitted."
- `TextDataWithText/properties/justification/description` → `Justification`: "Optional; equivalent to style.justification."
- `TextDataWithText/properties/style/description` → `TextStyleSettableDetails`: "height/pen/angle/justification above take precedence over the same fields here if both are given."
- `TextDataWithRuns/properties/coordinate/description` → `Coordinate3D`: "The placement position of the text. The z value is used to determine the floor when floorIndex is omitted."
- `TextDataWithRuns/properties/justification/description` → `Justification`: "Optional; equivalent to style.justification."
- `TextDataWithRuns/properties/style/description` → `TextStyleSettableDetails`: "height/pen/angle/justification above take precedence over the same fields here if both are given."
- `GridElementDetails/properties/elementId/description` → `ElementId`: "The grid element. The zero GUID for the tool defaults."
- `GridElementDetails/properties/pos/description` → `Coordinate2D`: "Insertion point: the start of the grid line."
- `Body3DPolygon/properties/surfaceId/description` → `AttributeId`: "The surface attribute of the face. Left out when the face's material is not a project attribute (for example one defined by a GDL script)."
- `ElementComponentQuantities/properties/subElementId/description` → `ElementId`: "The sub-element (for example a column or beam segment) the skin belongs to. Present only when Archicad attaches the skin to a sub-element."
- `ActiveGraphicalOverrideCombinationById/properties/combinationId/description` → `GraphicOverrideCombinationId`: "As returned by GetActiveGraphicalOverrideCombination."
- `ActiveGraphicalOverrideCombinationByName/properties/combinationId/description` → `GraphicOverrideCombinationId`: "As returned by GetActiveGraphicalOverrideCombination."
- `SaveCurrentWindowAsImageParameters/properties/format/description` → `ImageFormat`: "Optional. When omitted, the format comes from the extension of imageFilePath (.png, .jpg or .jpeg, .bmp, .tif or .tiff, .gif)."
- `SaveCurrentWindowAsImageParameters/properties/colorDepth/description` → `ImageColorDepth`: "Optional, trueColor by default."
- `GetGridElementDefaultsResult/properties/elementId/description` → `ElementId`: "The grid element. The zero GUID for the tool defaults."
- `GetGridElementDefaultsResult/properties/pos/description` → `Coordinate2D`: "Insertion point: the start of the grid line."
- `CreateGridElementsParameters/properties/gridElements/items/properties/begCoordinate/description` → `Coordinate2D`: "Start point of the grid line (the object's insertion point)."
- `CreateGridElementsParameters/properties/gridElements/items/properties/endCoordinate/description` → `Coordinate2D`: "End point of the grid line. Sets the direction and, unless lengthMode is 'none', the length."
- `CreateGridElementsParameters/properties/gridElements/items/properties/lengthMode/description` → `GridElementLengthMode`: "length (default): to the GDL parameter AC_Length when the library part has it, as the Grid Tool's grid marker does; otherwise to the object's A size, converted to xRatio as CreateObjects does. none: the length is left to 'parameters'."
- `Get3DProjectionSettingsResult/properties/cameraElementId/description` → `ElementId`: "The Camera element the projection was set from. Missing when the projection does not come from a camera."
- `Get3DProjectionSettingsResult/properties/activeCameraSetElementId/description` → `ElementId`: "The active Camera Set element. Missing when there is none."
- `Get3DProjectionSettingsResult/properties/perspective/description` → `PerspectiveProjectionParameters`: "The perspective parameters. Present only when isPersp is true."
- `Get3DProjectionSettingsResult/properties/axonometric/description` → `AxonometricProjectionParameters`: "Present only when isPersp is false."
- `CreateGraphicalOverrideRuleParameters/properties/surfaceRGB/description` → `ColorRGB`: "Optional color override of the cut and uncut surfaces. Components are in the 0..1 range."
