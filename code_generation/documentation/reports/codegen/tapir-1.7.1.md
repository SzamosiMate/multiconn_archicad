# Tapir 1.7.1 codegen record

**Input:** released Tapir 1.7.1 documentation, updating 1.7.0. **Checked-in baseline:** `c00f1a822556dbae8dc7fc32b1134ea0904191cd`. Initial working outputs already contained beam-hole, naming/alias and export-result repairs; those are not new upstream additions. Existing six compatibility aliases were retained.

Against that baseline: nine commands added, 13 existing contracts changed, no removals; 14 type names added and 13 existing type contracts changed. Against the initial working tree, the incremental counts are nine added/11 changed commands and ten added/12 changed type names. Additions cover hotlink updates, Teamwork locks/cache reservations and marker parameters.

## Temporary

Retain separate `BeamHoleModification` data at `ModifyBeamsParameters/beamsWithDetails/items/holes/items`, without response-only `holeId`. Share the slab creation structure enum, equivalent wall `linkToSettings` objects and reservation-user shapes. The run retains two beam-hole operations and adds eight sharing operations. Retire only when released named definitions/references cover all affected consumers without changing requiredness.

## Permanent

Nine naming operations were classified Permanent in this run; later 1.7.2 source classifies these schema-specific names as Temporary. The historical consumers/destinations are:

- `ChangeHotlinkNodesParameters/hotlinkNodes/items` → `HotlinkNodeChange`; `UpdateHotlinksParameters/hotlinkNodes/items` → `HotlinkNodeReference`. Keep these distinct from creation's `HotlinkNode`.
- `GetLockableObjectSetStatusResult/status` → `LockableObjectSetStatus`, distinct from revision status.
- `GetMarkerParametersOfElementsResult/markerParametersOfElements/items/oneOf/0` → `MarkerParametersOfElement`; its `parameters/items` → `MarkerGDLParameterDetails`. Marker reads do not require ordinary GDL `isLocked`.
- `SetMarkerParametersOfElementsParameters/elementsWithMarkerParameters/items` → `ElementWithMarkerParameters`; its `markerParameters/items` → `MarkerParameterUpdate`, with `MarkerParameterUpdateByName` and `MarkerParameterUpdateByIndex` branches. Preserve released selection and value rules; ordinary GDL setters have unsupported array-index fields.

## Removed patches

Released naming/reuse replaces 184 Temporary helper operations, nine direct edits and two source-review operations. Preserve expanded contracts and old Python imports. The retired path inventory remains in Git at `653cf806:code_generation/documentation/schema-patch-tracking.md`. Historical final inventory: ten Temporary operations in six declarations and 78 Permanent helper invocations.

## Compatibility and generator decisions

`get_script_ui_result` requires actual `isOpen` state. The pre-existing beam-modification correction changes its hole model. MEP read APIs widen from `MEPDomain` to the distinct `MEPDomainOrUnknown` enum: wire strings remain valid, but Python enum identity/equality and enum-instance validation differ. `MEPDomains` remains an identical alias of canonical `MEPDomain`.

Alphabetize final command modules while retaining dependency order for common/combined models. Stale patch destinations, missing enums and already-referenced targets must fail loudly. `extract_union_variant` names a selected branch without changing the enclosing union. Naming does not make the existing untagged Pydantic unions a complete JSON Schema exclusivity validator.

No pending generation decisions were recorded. Later upstream status and retirement conditions belong to [active tracking](../../schema-patch-tracking.md).
