## Tapir generation report

**Result:** Ready for human review · **Tapir:** 1.6.0 → 1.7.0  
**Baseline:** `1b23a5031b957472a7913930045ad772d399c8d6`

### API change summary

- **Commands:** 1 added (`SetIFCPropertiesOfElements`), none removed, 7 structurally changed: `CreateMEPRoutingElements`, `CreateMEPSystems`, `GetGeoLocation`, `GetMEPRoutingElements`, `GetMEPSystems`, `ModifyMEPRoutingElements`, `SetGeoLocation`.
- **Type models added (5):** `ElementIFCPropertyValue`, `GeoReferencingParametersUpdate`, `ProjectLocationUpdate`, `SurveyPointPositionUpdate`, `SurveyPointUpdate`.
- **Type models changed (8):** `GeoReferencingParameters`, `MEPRoutingElementData`, `MEPRoutingElementModificationData`, `MEPRoutingSegmentDetails`, `MEPSystemAttribute`, `MEPSystemAttributeField`, `MEPSystemData`, `SurveyPoint`. None removed.
- **Unified API breaks (2):** `get_geo_location`, `set_geo_location`.
- **Patch declarations:** 4 new Temporary; 2 existing source-review patches removed. No other new/changed patches; remaining inventory unchanged.

Counts include referenced schema changes and exclude documentation-only edits. Command models add the IFC setter's parameters/result and change `SetGeoLocationParameters`.

### Changes by patch category

#### Temporary

These four extractions give the setter its own optional models, while keeping complete read models. Each call identifies the upstream definition and property path.

- **`ProjectLocationUpdate`:** set known project-location values without supplying longitude, latitude, altitude, and north together.

  ```python
  extract_inline_schema(
      master_defs, "SetGeoLocationParameters",
      ["projectLocation"], "ProjectLocationUpdate",
  )
  ```

- **`SurveyPointPositionUpdate`:** change eastings, northings, or elevation independently.

  ```python
  extract_inline_schema(
      master_defs, "SetGeoLocationParameters",
      ["surveyPoint", "position"], "SurveyPointPositionUpdate",
  )
  ```

- **`GeoReferencingParametersUpdate`:** update any subset of the nine CRS/map-conversion fields.

  ```python
  extract_inline_schema(
      master_defs, "SetGeoLocationParameters",
      ["surveyPoint", "geoReferencingParameters"],
      "GeoReferencingParametersUpdate",
  )
  ```

- **`SurveyPointUpdate`:** optional wrapper using the two nested update models. `positionInProject` is also optional, but still requires complete xyz coordinates when supplied.

  ```python
  extract_inline_schema(
      master_defs, "SetGeoLocationParameters",
      ["surveyPoint"], "SurveyPointUpdate",
  )
  ```

Retire these naming patches when upstream supplies equivalent named update definitions and references, preserving their optional fields and the strict read models. No generator or cleaner workaround was needed.

#### Removed source-review patches

The following calls previously replaced partial setter objects with complete read models, making optional fields mandatory. Removing them restores the upstream setter contract; the user selected this split on 2026-10-06.

```python
# Removed:
replace_inline_schema_with_ref(
    master_defs, "SetGeoLocationParameters", ["projectLocation"], "ProjectLocation",
)
replace_inline_schema_with_ref(
    master_defs, "SetGeoLocationParameters", ["surveyPoint"], "SurveyPoint",
)
```

#### Upstream changes — no local patch

- **IFC property setter:** `set_ifc_properties_of_elements` accepts `ElementIFCPropertyValue` items and returns a list of execution results. Source: `#/$defs/SetIFCPropertiesOfElementsParameters/properties/elementIFCPropertyValues/items` and `#/$defs/SetIFCPropertiesOfElementsResult`.

  ```python
  api.set_ifc_properties_of_elements([
      ElementIFCPropertyValue(
          elementId={"guid": element_guid},
          propertySetName="Pset_DoorCommon",
          propertyName="IsExternal",
          type="IfcBoolean",
          value=True,
      )
  ])
  ```

  The write model stays separate from `ElementIFCProperty`, whose response uses `name` and a string value. The new schema leaves `value` unconstrained (`Any`); scalar/type rules remain descriptions. Upstream documents Archicad 25–27 support; no runtime version gate was added.

- **MEP routing:** creation adds optional `preferenceTableId`; modification and segment responses add optional `preferenceTableId` and `crossSectionReferenceId`. Sources: `#/$defs/CreateMEPRoutingElementsParameters`, `#/$defs/ModifyMEPRoutingElementsParameters`, `#/$defs/MEPRoutingSegmentDetails`. Existing creation/modification/details models retain their distinct roles; table IDs use UUID/GUID forms. Preference tables do not apply to CableCarrier.

- **MEP system surfaces:** creation and responses add optional `materialId` and `insulationMaterialId`, using `AttributeIdArrayItem`. The field-selection enum gains both names. Sources: `#/$defs/CreateMEPSystemsParameters`, `#/$defs/MEPSystemAttribute`, `#/$defs/GetMEPSystemsParameters`.

- **Documentation only:** `ChangeWindow` clarifies story activation. `DetailsOfElement.floorPlanPolygons` clarifies eligible element types at `#/$defs/GetDetailsOfElementsResult/properties/detailsOfElements/items/properties/floorPlanPolygons/description`; its shape is unchanged.

### Unified API breaking changes

- **`get_geo_location`:** the return annotation stays `GetGeoLocationResult`, but its nested read models now require four additional fields. Source: `#/$defs/GetGeoLocationResult/properties/surveyPoint` (`positionInProject`) and its `geoReferencingParameters` property (`xAxisAbscissa`, `xAxisOrdinate`, `scale`). Update constructed read models, cached responses, and mocks with actual project values; no defaults were invented.

- **`set_geo_location`:** the model split above changes both parameter types. Defaults and the execution-result return stay unchanged.

  ```diff
  - project_location: ProjectLocation | None = None
  + project_location: ProjectLocationUpdate | None = None
  - survey_point: SurveyPoint | None = None
  + survey_point: SurveyPointUpdate | None = None
  ```

  Known values need no preceding read:

  ```python
  api.set_geo_location(project_location=ProjectLocationUpdate(altitude=100.0))
  ```

  To reuse read data, modify the strict object before converting it:

  ```python
  geo = api.get_geo_location()
  geo.surveyPoint.position.eastings += 2.0
  update = SurveyPointUpdate.model_validate(geo.surveyPoint.model_dump())
  api.set_geo_location(survey_point=update)
  ```

  For both top-level objects, validate `geo.model_dump()` with `SetGeoLocationParameters`, then pass its `projectLocation` and `surveyPoint`. Conversion preserves supplied fields; it does not compute a minimal diff. Omitted fields are not sent. `None` means omission, not JSON null or clearing a value.

### Untouched new type models

- `ElementIFCPropertyValue`

### Verification

- **Strict audit and full-pipeline reproducibility:** passed; the second run changed no output.
- **Unified generation:** passed, targeting the consumed package and command-literal paths; no stale-import bootstrap.
- **Ruff:** formatting passed. Five baseline F401 findings remain: `TypeAdapter`, `List` in two files, `Error`, and `User`. The changed schema patch, setter, and focused regression tests passed lint.
- **Full suite:** **2,936 passed** in **139.31 s**, including 11 focused cases for partial writes, strict reads, conversion, zero/empty values, and complete xyz coordinates.
- **Model consistency:** Pydantic/TypedDict fields and requiredness agree. The split added exactly four types and left every existing read model unchanged.
- **Diff review:** no unexplained changes under normal newline normalization; `git diff --check` passed. Version constant and README badge both use 1.7.0.

### Human review

No pending decisions. Apply the two caller migrations above when adopting the update.
