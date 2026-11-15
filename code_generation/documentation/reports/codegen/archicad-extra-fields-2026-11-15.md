# Live Archicad extra-field validation — 2026-11-15

## Environment and method

- Live instance: Archicad **27**, build **3001**, language **INT**; Tapir **1.7.3**.
- Target: `http://127.0.0.1:19723`, project **TestProject01**.
- The connected Archicad discovery identified the instance; raw `GetAddOnVersion`
  and `API.GetProductInfo` calls independently confirmed the versions.
- Inspected local Tapir tag `1.7.3`, commit `e91613009dd9b884ac317c8141e710719374541d`.
- **45 raw HTTP requests**, including setup, valid controls, malformed controls
  and final verification. All commands were read-only.
- Used Python `httpx` directly, without the generated client or Pydantic request
  validation, so extra fields could not be rejected or removed by our client.
  HTTP status was 200 for the application-level validation errors; the JSON
  envelope reports `succeeded: false`, error code **4002**.
- Element listing before/after was identical: **118 elements**.

## 1. The new SI flag on Tapir 1.7.3

Read four scalar length definitions (thickness, width and two height aliases)
for 20 real elements. The baseline returned 42 value cells, including `0.30`,
`3.00`, `0.20` and `2.80`; other cells retained their availability/error results.

| Variant of `GetPropertyValuesOfElements` | Observed outcome |
| --- | --- |
| No `useSIUnits` | Success, normal property response |
| `useSIUnits: false` | Error 4002, `additionalProperties`, path `#/useSIUnits` |
| `useSIUnits: true` | Same error |
| `useSIUnits: "not-a-boolean"` | Same unknown-field error |
| Arbitrary extra object at command root | Error 4002, `additionalProperties` |
| Invalid type for known inline `includeAvailability` | Error 4002, `type` |

The error returned by Archicad for both Boolean flag values was:

```json
{
  "succeeded": false,
  "error": {
    "code": 4002,
    "message": "Invalid command parameters (The JSON is invalid according to the JSON schema. Validation failed on schema rule 'additionalProperties' while trying to validate field on path '#/useSIUnits'.)"
  }
}
```

This establishes an actual compatibility failure on the installed instance,
rather than only a disagreement with an offline schema validator. These requests
do not execute the property read successfully when the extra Boolean flag is sent.

## 2. Fully inline input schemas

The tag's input schemas for these commands contain **no `$ref`**. Their
`additionalProperties: false` rules and ordinary constraints are inline.

| Command / case | Outcome |
| --- | --- |
| `GetNavigatorItemTree`, valid `navigatorMapId: "ProjectMap"` | Success |
| Same, extra root key valued false, true or an object | All rejected: 4002, `additionalProperties` |
| Same, missing required map / wrong map type / invalid enum | Rejected with `required` / `type` / `enum` respectively |
| `GetProjectPreferences`, valid `preferenceTypes: ["WorkingUnits"]` | Success |
| Same, extra root Boolean key | Rejected: 4002, `additionalProperties` |
| Same, wrong array type / invalid enum item / empty array | Rejected with `type` / `enum` / `minItems` respectively |
| `GetGraphicOverrideRulesByName`, valid inline name record | Command executed; expected per-item "No graphic override rule is named ..." error for the deliberately nonexistent name |
| Same, extra root Boolean key | Rejected: 4002, `additionalProperties` |
| Same, extra Boolean key inside a rule record | Rejected: 4002, `additionalProperties`, path `#/graphicOverrideRules/0/codexExtraProbe` |
| Same, missing nested name / wrong name type | Rejected with nested `required` / `type` errors |

Source locations at the inspected tag:

- `PropertyCommands.cpp`: `GetPropertyValuesOfElementsCommand::GetInputParametersSchema()`.
- `NavigatorCommands.cpp:2420`: `GetNavigatorItemTreeCommand::GetInputParametersSchema()`.
- `ProjectCommands.cpp:3589`: `GetProjectPreferencesCommand::GetInputParametersSchema()`.
- `GraphicOverrideCommands.cpp:374`: `GetGraphicOverrideRulesByNameCommand::GetInputParametersSchema()`.

## 3. Referenced common schemas behave differently

In the property-read request, the element and property arrays use common-schema
references. Added a Boolean extra key separately at each of these locations:

```text
elements[0].codexExtraProbe
elements[0].elementId.codexExtraProbe
properties[0].codexExtraProbe
properties[0].propertyId.codexExtraProbe
```

All four requests succeeded and their complete decoded responses were identical
to the corresponding one-element baseline. The marker value was `false`, the
same non-null value rejected in the inline cases.

This is consistent with the reported common-schema reference validation gap.
It does not disable the command root's inline validation and does not make new
root options acceptable to older Tapir versions. These probes demonstrate extra
key handling; they do not establish that every kind of common-schema constraint
is ignored.

## 4. JSON null is a separate exception

An unknown key with value `null` was accepted at command roots and inside the
tested inline rule record. In contrast, unknown fields valued false, true, zero,
empty string, empty array or empty object were rejected in the tested cases.

`useSIUnits: null` also succeeded, with the same full response as omission.
Sending required `navigatorMapId: null` produced a **required-field** error,
identical to omitting the required field. These observations are consistent with
null-valued fields being treated as absent during server-side processing; they
do not establish where in the Archicad parsing/validation pipeline that occurs.

This exception cannot justify sending `False` defaults: those fail explicitly.
The existing client convention of omitting `None` remains suitable for these cases.

## Conclusion and saved evidence

On Archicad 27 / Tapir 1.7.3, new non-null root flags are **not ignored** when the
command's inline schema forbids extra properties. The default-forwarding issue
therefore requires handling if old Tapir compatibility is intended. A missing
common-schema validation path cannot be used as a general compatibility policy.
The findings describe this instance/build and the tested commands.

All raw requests, complete decoded responses and durations are saved locally:

- [Probe script](../../../../tmp/archicad-extra-fields-2026-11-15/probe.py).
- [Raw evidence, all 45 requests](../../../../tmp/archicad-extra-fields-2026-11-15/evidence.json).
- [Extracted 1.7.3 command schemas](../../../../tmp/archicad-extra-fields-2026-11-15/tag-1.7.3-command-schemas.json).
- [Bootstrap log](../../../../tmp/archicad-extra-fields-2026-11-15/bootstrap.log).
- [Initial probes](../../../../tmp/archicad-extra-fields-2026-11-15/probes.log).
- [Follow-up probes](../../../../tmp/archicad-extra-fields-2026-11-15/followup.log).

Files under `tmp/` are untracked and require separate copying to another computer.
The report is intended to be retained with the generator investigation. No
runtime, generator, schema or test implementation was changed in this experiment.
