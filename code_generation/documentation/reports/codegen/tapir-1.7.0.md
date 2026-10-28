# Tapir 1.7.0 codegen record

**Input:** released Tapir 1.7.0 documentation, updating 1.6.0. **Baseline:** `1b23a5031b957472a7913930045ad772d399c8d6`. Historical counts and decisions below describe that run; current patch code and [active tracking](../../schema-patch-tracking.md) govern later releases.

The release adds one command (`SetIFCPropertiesOfElements`) and changes seven existing command contracts, including referenced models. Five type models are added, eight change and none are removed. Two Unified API methods have compatibility consequences.

## Temporary

Four naming extractions under `SetGeoLocationParameters` introduce `ProjectLocationUpdate`, `SurveyPointPositionUpdate`, `GeoReferencingParametersUpdate` and `SurveyPointUpdate`. Setter fields stay optional while read models retain complete reported data. A supplied `positionInProject` still requires complete xyz coordinates. Retire these extractions only when released equivalent named update contracts and their references replace them.

## Removed source-review patches

Remove the two replacements that reused complete geolocation read models in partial setters: they imposed required fields absent from the setter contract. The user selected distinct read/update models on 2026-10-06. No generator workaround is needed.

## Compatibility and lasting decisions

- `get_geo_location` now requires `positionInProject` and three additional map-conversion fields in its nested read data. Do not invent defaults for constructed responses.
- `set_geo_location` accepts the new update models. Converting a read model preserves supplied fields rather than calculating a minimal diff; omitted fields and `None` are not sent.
- IFC writes use a distinct `ElementIFCPropertyValue` contract; do not reuse the differently shaped read model or infer validation stronger than the released unconstrained value field. Availability is documented for Archicad 25–27.
- Keep MEP creation/modification/details roles separate while adopting preference-table, cross-section-reference and system-surface fields. CableCarrier does not use the preference tables.

No pending decisions were recorded.
