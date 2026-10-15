## Tapir generation report

**Result:** Ready for human review · **Tapir:** 1.7.0 → 1.7.1  
**Checked-in baseline:** `c00f1a822556dbae8dc7fc32b1134ea0904191cd`  
**Inputs:** Released 1.7.1 documentation schemas, fetched by the generation pipeline. Existing working changes and all six compatibility aliases were retained.

### API change summary

Counts compare public definitions and expanded schema contracts with the checked-in baseline, ignoring descriptions and ordering. The incremental comparison with the initial working tree is stated separately because it already contained generation repairs.

- **Commands:** 9 added: `ChangeHotlinkNodes`, `UpdateHotlinks`, `GetLockableObjectSetStatus`, `ReserveLockableObjectSet`, `ReleaseLockableObjectSet`, `ReserveHotlinkCacheManagement`, `ReleaseHotlinkCacheManagement`, `GetMarkerParametersOfElements`, `SetMarkerParametersOfElements`. None removed. 13 existing commands have changed generated contracts: `CreateHatches`, `CreateSlabs`, `CreateWalls`, `ExportFavorites`, `GetDetailsOfElements`, `GetMEPDistributionSystems`, `GetMEPPorts`, `GetMEPRoutingElements`, `GetScriptUIResult`, `GetStories`, `ModifyBeams`, `ModifyWalls`, `SetDetailsOfElements`.
- **Public type models:** 14 names added: `BeamHoleModification`, `ElementWithMarkerParameters`, `HotlinkNodeChange`, `HotlinkNodeReference`, `LockableObjectSetStatus`, `MEPDomain`, `MEPDomainOrUnknown`, `MarkerGDLParameterDetails`, `MarkerParameterUpdateByIndex`, `MarkerParameterUpdateByName`, `MarkerParameterUpdate`, `MarkerParametersOfElement`, `RoofLevel`, `RoofPivotLine`. None removed; former canonical names remain aliases. 13 existing named models change directly or through their dependencies: `BeamWithDetails`, `HatchData`, `HatchDetails`, `HatchSettings`, `MEPDistributionSystem`, `MEPElementPorts`, `MEPPortDetails`, `MEPRoutingElementDetails`, `SlabData`, `StoryParameters`, `WallData`, `WallDetails`, `WallWithDetails`.
- **Incremental 1.7.1 changes from the working tree:** 9 new commands, 11 existing commands changed; 10 new type names, 12 existing named type contracts changed. The additional checked-in differences are the already present beam-hole split, canonical type names/aliases, and restored `ExportFavoritesResult`. Command-model definitions add 17 against HEAD (16 from 1.7.1 plus the existing export-result repair), with 12 structurally changed; none removed.
- **Unified API compatibility:** two structural breaks against HEAD (Script UI polling and the existing beam-modification correction), plus three MEP enum-class compatibility changes. Only the Script UI structural break originates in 1.7.1. For the previously used client API, MEP is `MEPDomain` → `MEPDomainOrUnknown`, widening accepted values rather than introducing enums. No existing method was removed, and existing method signatures/return unwrapping match the initial working tree. `get_mep_elements` changes its annotation to the canonical `MEPDomain`, with `MEPDomains` retained as the identical enum alias.
- **Patches, counted as expanded operations:** retired 184 temporary helper operations, nine temporary manual edits, and two source-review operations. Retained two temporary beam-hole operations; added eight Temporary sharing operations and nine Permanent naming operations. Current inventory: 10 temporary operations in six declarations and 78 permanent helper invocations (the existing 69 plus nine naming operations). The nine new naming operations were reclassified from Temporary without changing accepted payloads; three marker names were also revised before release. No breaking-permanent or source-review patches remain.

### Changes by patch category

#### Temporary

All retained/new permanent naming and temporary patches preserve the released schema's acceptance contract. Expanding references before and after this stage produces no structural differences in any existing definition. Exact calls below use the helper's property-path shorthand.

- **Beam modifications — retained.** The source is `ModifyBeamsParameters/beamsWithDetails/items/holes/items`, reached through the permanent `BeamWithDetails` extraction. The modification item has no response-only `holeId` and requires positive width/height when supplied. It must remain distinct from `BeamHole`. Both representations retain the existing working-tree correction.

  ```python
  extract_inline_schema(master_defs, "BeamWithDetails", ["holes", "items"], "BeamHoleModification")
  replace_inline_schema_with_ref(master_defs, "BeamHoleModification", ["type"], "BeamHoleType")
  ```

  Retire when upstream names that exact modification item and references the shared enum.

- **Slab creation structure.** New `CreateSlabsParameters/slabsData/items/structureType` would become the broad generated `StructureType`, duplicating the existing two-value slab enum. Reuse preserves both values and the optional field.

  ```python
  replace_inline_schema_with_ref(master_defs, "SlabData", ["structureType"], "SlabStructureType", preserve_description=True)
  ```

  Retire when the released creation item uses this reference.

- **Wall story links.** New inline story-link objects in creation, details and modification generate `LinkToSettings1/2/3`. They have the same optional fields, types and additional-property rule as `LinkToSettings`; reuse it for all three consumers. Source parents originate in `CreateWallsParameters/wallsData/items`, `WallDetails`, and `ModifyWallsParameters/wallsWithDetails/items`.

  ```python
  for parent in ("WallData", "WallDetails", "WallWithDetails"):
      replace_inline_schema_with_ref(master_defs, parent, ["linkToSettings"], "LinkToSettings", preserve_description=True)
  ```

  Retire when all three upstream consumers use the shared definition. This preserves the contextual object description; nested field descriptions come from the shared definition.

- **Teamwork reservation users.** Object-set/cache conflicts contain the same required `userId`/`userName` pair as an element reservation's nested `User`. They differ from the existing `Conflict`, which also identifies an element. Extract the established `User` name and reuse it, preventing a new `Conflict1` without changing the old `Conflict` model.

  ```python
  extract_inline_schema(master_defs, "ReserveElementsResult", ["conflicts", "items", "user"], "User")
  for parent in ("GetLockableObjectSetStatusResult", "ReserveLockableObjectSetResult", "ReserveHotlinkCacheManagementResult"):
      replace_inline_schema_with_ref(master_defs, parent, ["conflicts", "items"], "User")
  ```

  Retire when these four upstream locations share a named user definition. Status/reserve results retain their optional conflict lists and their existing wrapper shapes.

#### Permanent

Generator-specific singularization, naming collisions and local public-name stability belong here while upstream permits inline schemas. Valid inline schemas do not require upstream changes solely to accommodate this generator.

- **Hotlink change/reference payloads.** The new operations collide with the existing `HotlinkNode` creation model, generating numbered names and changing which payload owns the unnumbered name. Name the new shapes explicitly; the existing creation model remains `HotlinkNode`.

  ```python
  extract_inline_schema(master_defs, "ChangeHotlinkNodesParameters", ["hotlinkNodes", "items"], "HotlinkNodeChange")
  extract_inline_schema(master_defs, "UpdateHotlinksParameters", ["hotlinkNodes", "items"], "HotlinkNodeReference")
  ```

  These collision fixes are permanent local naming decisions; valid upstream inline schemas do not require named extractions. Creation requires `sourceLocation`; change requires it plus `hotlinkNodeId`; refresh requires only `hotlinkNodeId`.

- **Teamwork reservation status.** The new status enum otherwise becomes `Status1`, colliding with revision status. It retains exactly `Free`, `Editable`, `Locked`, `NotAvailable`, `NotExist`.

  ```python
  extract_inline_enum(master_defs, "GetLockableObjectSetStatusResult", ["status"], "LockableObjectSetStatus")
  ```

  This is a permanent local collision fix; `objectSetName` remains an unrestricted string, as documented.

- **Marker reads.** Name the success branch separately from `ErrorItem` and name its GDL parameter details. Reusing `GDLParameterDetails` would incorrectly require `isLocked`, which marker responses do not supply. `libPart` remains optional; `parameters` remains required.

  ```python
  extract_union_variant(master_defs, "GetMarkerParametersOfElementsResult", ["markerParametersOfElements", "items"], 0, "MarkerParametersOfElement")
  extract_inline_schema(master_defs, "MarkerParametersOfElement", ["parameters", "items"], "MarkerGDLParameterDetails")
  ```

  This is a local generator naming workaround, not a request for an upstream schema change. The inline success branch is valid; naming its parameter type prevents a context-free `Parameter` model.

- **Marker writes.** Name the element wrapper and the name/index update union instead of generating `ElementsWithMarkerParameter`, `MarkerParameters` and `MarkerParameters1`. Reusing the existing GDL setters would introduce unsupported array-index fields. The name/index branches and unconstrained `value` remain exactly as released; scalar restrictions are descriptive upstream rules.

  ```python
  extract_inline_schema(master_defs, "SetMarkerParametersOfElementsParameters", ["elementsWithMarkerParameters", "items"], "ElementWithMarkerParameters")
  extract_inline_schema(master_defs, "ElementWithMarkerParameters", ["markerParameters", "items"], "MarkerParameterUpdate")
  extract_union_variant(master_defs, "MarkerParameterUpdate", [], 0, "MarkerParameterUpdateByName")
  extract_union_variant(master_defs, "MarkerParameterUpdate", [], 1, "MarkerParameterUpdateByIndex")
  ```

  These are local generator naming workarounds. `ElementWithMarkerParameters` minimally fixes the generated `ElementsWithMarkerParameter`: one element carrying multiple parameters. The `Update` suffix on the former wrapper name was an unnecessary preference and did not resolve a collision. The named update union and its two branches provide unambiguous local names; they do not establish an upstream defect. Pydantic and TypedDict both expose `MarkerParameterUpdate`. As with existing generated unions, a Python union is not a complete JSON Schema `oneOf` validator; the shared Pydantic base ignores extra keys. Naming preserves the schema branches and does not change that established behavior.

#### Removed patches

- **Released named definitions/reuse.** All 184 temporary helper operations that now encounter upstream references were inspected, including paths behind earlier extractions. Their destination names match exactly. Expanded contracts match the old patched targets, apart from the MEP domain difference against the saved generated snapshot, explained below. The [retirement inventory](../schema-patch-tracking.md#temporary-named-definitions-and-references-184-operations) records every original path and destination, grouped by definition. This covers classification/property updates, drawing/GUID reuse, attribute enums and payloads, geolocation read/update separation, geometry details, MEP, libraries, hotlinks, text/labels, and related shared definitions.
- **Design options and union edits.** The two design-option array-item corrections, navigator window branch extraction, and six element-relation branch extractions are already supplied by the release. Their [exact nine locations](../schema-patch-tracking.md#manual-edits-9-operations) are recorded in tracking. Removing the old direct edits also removes the conditional navigator extraction and relation loop that silently skipped existing references.
- **Two source-review patches.** `CreateMEPSystemsParameters/mepSystemDataArray/items/domain` (the local `MEPSystemData/domain`) now references the three-value `MEPDomain`; `GetMEPElementsResult/elements/items/type` now reaches the eleven-value `MEPElementType` through upstream `MEPElement`. These are the contracts previously imposed locally. Both patches are retired, with no remaining source-review question.

#### Upstream changes — no local patch

- **Wall controls and requiredness.** `CreateWallsParameters/wallsData/items`, `WallDetails`, and `ModifyWallsParameters/wallsWithDetails/items` add contour/overhead pens and line types, display/depth settings, composite priority, story linkage, surface/texture options and log height. Read details additionally expose connection/junction data, offset and window/door flags. Creation now requires only `begCoordinate` and `endCoordinate`; `height` and `thickness` become optional. Pen minimums remain intact. Story-link deduplication is handled above.
- **Slabs, hatches and stories.** `CreateSlabsParameters/slabsData/items` adds optional `structureType`, `buildingMaterialId`, `compositeId`; `HatchData`, `HatchDetails`, `HatchSettings` add optional `foregroundColor`/`backgroundColor` using `ColorRGB`; `StoryParameters/ifcId` is optional. Existing command wrappers and unwrapping stay unchanged.
- **MEP response domains.** `MEPDistributionSystem/domain`, `MEPPortDetails/domain`, and `MEPRoutingElementDetails/domain` now reference upstream `MEPDomainOrUnknown`, with `Ventilation`, `Piping`, `CableCarrier`, `Unknown`. Relative to the prior client API identified during review, this widens `MEPDomain` with `Unknown`; it is not a string-to-enum migration or a wire-contract break. The saved initial generated files happened to annotate these fields as `str`, so the mechanical snapshot diff overstated the release migration. Input `MEPDomain` remains the separate three-value enum. The enum-class compatibility detail is documented separately below.
- **Script UI lifecycle.** `GetScriptUIResultResult/isOpen` is a new required boolean reporting palette lifetime. The response already had multiple fields, so unified return unwrapping is unchanged.
- **New command behavior.** The nine added command definitions are listed in the API summary. Marker get/set use per-element success/error and execution-result lists; hotlink relink/refresh return execution-result lists; object-set status and reserve operations retain status/conflict or execution/conflict wrappers. Release operations return execution-result unions. No extra runtime version gates were introduced.
- **Documentation.** Released reference factoring changes descriptions and model ordering throughout generated files. Schema comparison confirms that the remaining affected definitions differ only in annotations, reference layout, aliases, or the public changes listed above.

### Unified API breaking changes

- **`get_script_ui_result`:** the same result model now requires `isOpen`. Include the actual palette state in mocks/cached payloads; polling can stop when it becomes false. No default was invented.
- **`modify_beams` — existing working change retained:** `BeamWithDetails.holes` uses `BeamHoleModification` instead of `BeamHole`. Supply modification items without the response-only identifier and with positive dimensions. This correction predates the 1.7.1 run but differs from HEAD.

  ```python
  # Script UI mocks:
  response = {"hasResult": False, "isOpen": True}

  # Beam edits converted from a read response:
  edit = BeamHoleModification.model_validate(hole.model_dump(exclude={"holeId"}))
  ```

### MEP enum-class compatibility (wire-compatible widening)

`get_mep_distribution_systems`, `get_mep_ports`, and `get_mep_routing_elements` previously used `MEPDomain` in the client API identified during review; the released shared definition is `MEPDomainOrUnknown`. Existing wire values are retained and `Unknown` is added. No new `.value` conversion is required for callers that already handled enums.

The distinct Python enum class still matters for explicitly typed consumers: `MEPDomain.PIPING == MEPDomainOrUnknown.PIPING` is false, and Pydantic rejects a `MEPDomain` instance when validating `MEPDomainOrUnknown`. Compare against the new enum class, compare wire values, or convert at the boundary:

```python
reported_domain = MEPDomainOrUnknown(existing_domain.value)
assert reported_domain == MEPDomainOrUnknown.PIPING
# For comparisons that intentionally span both enum classes:
assert reported_domain.value == existing_domain.value
```

This caveat applies to `MEPDistributionSystem.domain`, `MEPPortDetails.domain`, and `MEPRoutingElementDetails.domain`; it is separate from JSON Schema acceptance and patch retirement.

### Untouched new type models

- `MEPDomain`
- `MEPDomainOrUnknown`
- `RoofLevel`
- `RoofPivotLine`

### Generator and audit changes

- **Stable final command order.** Both Tapir splitters alphabetize command definitions after separating common types. `CreateMEPElementsParameters` had moved without a body change because its `MEPElementData` dependency moved earlier after the domain enum became shared; the original splitters carried combined-file dependency order into the command modules. Current command definitions import common types and do not depend on one another, so the final command files now have name-based ordering. Common types and combined intermediates retain generator dependency order, and both `keep_model_order` settings remain disabled. This introduces a one-time reorder without changing public definitions, fields or method behavior. The new regression tests feed both splitters different valid combined dependency orders and require identical command output, including aliases, while preserving common-type order.
- **Fail loudly on stale patches.** Schema extraction and enum extraction now reject an existing destination definition before overwriting it, even when it is identical. Conditional required-variant naming checks all destination names before writing any. Enum extraction raises when the enum disappeared instead of warning and returning. Existing missing-target/reference guards remain. There are no conditional stale-patch skips.
- **Union branch extraction.** `extract_union_variant` names an inline `oneOf`/`anyOf` branch while retaining the other branches and parent keywords. It rejects missing/ambiguous unions, invalid indices, existing references and existing destination names. The three marker branches use this helper. No new generator settings or deterministic audit exceptions were needed; the existing audit caught all numeric-suffix problems.
- **Preserved source changes.** Existing model-alias, Pydantic cleaner, unified return-model and generated-test changes were retained as the requested starting point. This run and its naming review changed schema patching and its guard tests; it did not add a cleaner workaround or alter shared Pydantic extra-key behavior.

### Upstream follow-up

The remaining new temporary reuse/naming candidates and the retained beam-hole operations are recorded [in tracking](../schema-patch-tracking.md#still-needed-after-171), with their exact decisions and retirement conditions above. The nine permanent naming operations are excluded from upstream recommendations; valid inline schemas and generator naming limitations are not sufficient grounds for an upstream change. All older retirement candidates are confirmed in the released schema. No Tapir implementation source was inspected and no upstream PR was opened.

### Verification

- **Strict audit and complete-pipeline reproducibility:** passed with the finalized names and stable command ordering; the second complete Tapir run changed no generated output.
- **Ordering checks:** both splitters produced byte-identical outputs in separate processes with `PYTHONHASHSEED=1` and `98765`. This verifies the splitting stage, not whole-pipeline cross-process reproducibility. Structural comparison against the outputs before the ordering change found identical names and AST bodies for all 499 definitions in each command representation; only order changed. Both common-type files stayed byte-identical. Two regression cases exercise input-order variation through the actual splitters, including a command alias and preserved common dependencies.
- **Unified generation:** passed; 267 Tapir method tests generated. Outputs target the imported `clients/unified_api` package and `clients/core/literal_commands.py`. No stale-import bootstrap was needed.
- **Patch contracts:** reference-expanded before/after comparison shows no acceptance changes from the nine permanent naming operations and 10 temporary operations. The prior snapshot-based MEP difference is not a restriction relative to the user-identified previous enum contract.
- **Representations:** all 894 generated Pydantic class entries match TypedDict fields and requiredness after wire-alias normalization and the established single-literal defaults (42 fields). All six public compatibility aliases point to identical targets in both representations. Every added or structurally changed public type was reviewed with its schema consumers; no public names were lost.
- **Ruff:** patch source and guard tests pass formatting and lint. Generated formatting passed. A wider generated-code lint check reports 13 existing template-style findings: nine unused `TypeAdapter` imports, two unused `List` imports, an unused `Error` import and the unused validated export response. These were not broadly cleaned up.
- **Tests:** the current full suite passed after the ordering change: **3,033 passed in 135.08 seconds**, with localhost socket access enabled for mock-server integration tests. No exclusions or targeted reruns were needed for this result. This includes all 30 patch-helper tests and both new splitter-order regression cases.
- **Diff:** all changed generated definitions and unified signatures/return expressions were classified. Final Tapir command definitions use alphabetical ordering; remaining common-model movement is generator dependency ordering, annotation/reference changes and retained compatibility aliases. `git diff --check` passed.

### Human review

No pending decisions. Apply the structural caller migrations and any relevant enum-class adjustments above when adopting this working-tree update. Verification used generated tests and mock HTTP integration tests; no live Archicad instance was exercised.
