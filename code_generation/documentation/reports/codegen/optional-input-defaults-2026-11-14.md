# Optional input defaults and backward compatibility — 2026-11-14

**Selected continuation:** the [2026-11-15 Literal-based implementation plan](../../optional-default-serialization-plan.md)
supersedes this investigation's initial presence-aware repair proposal. It keeps
method/model defaults, excludes optional default values from generated requests,
and preserves required Literals under a generator audit. Implementation is pending.

Analysis baseline: `82070c1`, branch `extensible-elmement-query`, generated Tapir
2.0.0. Shipped-signature baseline: MultiConn `v0.9.7`, commit
`e8990a0b1b9b57a21b03085164c09f4032db79fb`, generated against Tapir 1.8.0.
This investigation changes no runtime or generator implementation.

## Finding

Optional request fields with schema defaults are emitted even when the caller
omits them. This is a general generation/serialization policy gap. Most newly
added options have no schema default, become `None`, and are omitted correctly.

For example, the old call `get_property_values_of_elements([], [])` now sends
`{"elements": [], "properties": [], "useSIUnits": false}`. Tapir 1.8.0's schema
does not define `useSIUnits` and forbids additional properties. Offline validation
against that schema rejects the new default payload; the payload without the
flag validates. The local Tapir `1.8.0` tag's `PropertyCommands.cpp` independently
confirms that input schema. No older live instance was called during this audit.

## Pipeline trace

| Stage | Observed behavior | Source |
| --- | --- | --- |
| Released schema ingestion | Copies command input schemas, including optional fields' `default` annotations. `useSIUnits` has `default: false`, is absent from `required`, and remains unchanged in the patched master schema. | [`01_schema_generator.py`](../../../tapir/model_generators/01_schema_generator.py), `get_command_defs()` and `main()` |
| Pydantic generation | The actual model stage generates `useSIUnits: bool | None = Field(False, ...)`. Optional fields without defaults become `None`. TypedDicts use optional keys without supplying runtime values. | [`02_generate_dicts_and_models.py`](../../../tapir/model_generators/02_generate_dicts_and_models.py) |
| Cleanup and splitting | The cleaner preserves ordinary field defaults; splitting moves the definition into public command/type modules. Raw, cleaned and final SI fields all default to `False`. | [`03_model_cleaner.py`](../../../tapir/model_generators/03_model_cleaner.py), [`04_split_models.py`](../../../tapir/model_generators/04_split_models.py) |
| Client signature generation | Reads `inspect.signature(params_model)` and copies `repr(param.default)` into the method. Thus `use_si_units: None | bool = False`. | [`02_generate_method_code.py`](../../../unified/api_generator/02_generate_method_code.py), `_build_signature_and_docs()` |
| Shipped-call compatibility | Preserves positional order and makes new fields keyword-only. The snapshot records parameter names/kinds and return annotations; it does not record defaults or wire omission. | [`shipped_signatures.py`](../../../unified/api_generator/shipped_signatures.py), `_order_parameters()` |
| Generated body | Builds `params_dict` containing every argument, including defaults the caller did not supply. Constructs a new Pydantic request model from that dictionary. | `_build_body()` in the method generator |
| Serialization | Uses `model_dump(..., exclude_none=True)`. This removes `None`, but preserves `False`, `True`, zero, strings and other non-null defaults. `APIModel` also defaults only to excluding `None`. | Method generator and [`models/base.py`](../../../../src/multiconn_archicad/models/base.py) |
| Transport | Passes the dictionary through `API.ExecuteAddOnCommand` without filtering fields by installed Tapir version. | [`core_commands.py`](../../../../src/multiconn_archicad/clients/core/core_commands.py), `post_tapir_command()` |
| Generated verification | Derives expected payloads by validating the supplied test input through the same Pydantic model and dumping with `exclude_none=True`. The expected payload therefore injects the same defaults. | [`05_generate_command_tests.py`](../../../unified/api_generator/05_generate_command_tests.py) |
| Strict audit | Checks schema names/references and generated syntax/naming, with no omitted-input compatibility check. | [`generation_audit.py`](../../../tapir/generation_audit.py) |

The unified signature/body/test generator is shared with the Official API, so
its general default-forwarding behavior is not Tapir-specific.

## Current scope

Walking definitions reachable from command inputs found **13 optional model
fields with non-None runtime defaults**. Counts are unique definition/field pairs,
not the number of command paths that can reach a shared model.

| Definition | Optional fields / defaults |
| --- | --- |
| `GetArcFromUserParameters` | Three prompt strings; `showRubberArcFeedback=True` |
| `GetLineFromUserParameters` | Two prompt strings; `showRubberLineFeedback=True` |
| `GetPolygonFromUserParameters` | Two prompt strings; `method='General'` |
| `GetPropertyValuesOfElementsParameters` | `useSIUnits=False` |
| `SetCurrentWindowDrawingScaleParameters` | `rebuild=False` |
| `InputConstraint` | `fromLastPoint=False` |

Twelve defaults are declared directly on properties; `method` inherits its
default from the referenced `PolygonInputMethod` schema. Eleven direct property
defaults are on command roots; `InputConstraint` demonstrates nested injection.

Compared with the checked-in Tapir schema at the shipped-signature revision,
there are **82 direct field additions to existing parameter schemas**. Among
those additions, `useSIUnits` is the only field with an explicit property-level
schema default. Several other compatibility issues, such as changed call shapes
or return values, have separate policies; this count does not certify them.

The 13 defaults are exposure points for the general policy, not a claim that all
13 currently break older servers. Pre-existing defaults may be accepted by old
versions. A newly added defaulted field on an existing closed input schema is
the demonstrated backward-compatibility failure.

## Reproduction and verification

An isolated probe used the actual Tapir model-generation stage and actual unified
method generator. An old one-argument method gained optional fields:
`addedFlag` with schema default false, `enabledFlag` with default true, `limit`
with default zero, and `optionalFlag` with no default. Calling it with only the
old required argument sent all three defaulted additions and omitted
`optionalFlag`. New arguments were correctly keyword-only, demonstrating that
signature compatibility does not establish payload compatibility.

Real property-client probes recorded:

| Call option | Wire `useSIUnits` |
| --- | --- |
| Omitted | `false` |
| Explicit `None` | Omitted |
| Explicit `False` | `false` |
| Explicit `True` | `true` |

Supplying `constraint={"type": "Angle", "value": 0.1}` to the real point-input
parameter model also inserts `fromLastPoint=false` into the nested payload.

- All isolated audit assertions passed.
- Current generated property-read method test, deep schema mode: **1 passed**.
  This passes while the omission defect exists, confirming the test coverage gap.
- Existing shipped-signature tests: **4 passed**.
- The preceding numeric-query validation separately reproduced all five SI
  omission failures against the earlier unchanged branch HEAD.

Saved local [audit script](../../../../tmp/tapir-optional-default-audit-2026-11-14/audit.py),
[JSON evidence](../../../../tmp/tapir-optional-default-audit-2026-11-14/evidence.json),
[audit log](../../../../tmp/tapir-optional-default-audit-2026-11-14/audit.log),
[isolated generated model](../../../../tmp/tapir-optional-default-audit-2026-11-14/probe-models.py),
[isolated generated method](../../../../tmp/tapir-optional-default-audit-2026-11-14/probe-client.py),
[generated-test log](../../../../tmp/tapir-optional-default-audit-2026-11-14/generated-property-test.log),
and [signature-test log](../../../../tmp/tapir-optional-default-audit-2026-11-14/signature-tests.log)
are under untracked `tmp/` and need separate copying for another computer.

## Repair requirements

The intended generic contract is: omit optional request fields unless supplied;
preserve explicitly supplied values, including `False`, `True`, zero, empty
collections and values equal to the server's documented default. Apply the same
rule recursively to dictionaries and model instances used as nested inputs.
Keep server-default documentation separate from client assignment of that value.

Repair both request construction and serialization/model policy:

1. Optional method arguments need an omission-preserving default (`None` under
   the existing API convention, or a dedicated sentinel if explicit null must
   become distinguishable). Server schema defaults must not automatically mean
   that the client supplies a value.
2. Preserve field presence through request validation and nested serialization.
   Model cleanup for request optional fields or presence-aware request dumping
   are implementation choices. Shared request/response models and required
   singleton-literal defaults need deliberate treatment; do not globally change
   response dumping or drop required discriminator fields as a side effect.
3. Add independent generated/handwritten checks for omitted versus explicit
   default-valued arguments, nested omission and old closed schemas. Test newly
   added fields with boolean, number, string, collection and referenced defaults.

`exclude_unset=True` alone cannot fix the current generated method: the body
already passes every default-valued argument into the model, marking it set.
`exclude_defaults=True` would remove explicitly requested `False` and other
values equal to defaults. A signature-only adjustment would leave the nested
default injection. Hard-coding the SI flag or stripping its schema annotation
would leave the general generator gap.

Parameter omission prevents unsolicited use of new capabilities. Explicit use
of a feature unsupported by an older server still requires a separate version
check or an API error; omission alone cannot make that feature available.

## Live follow-up — 2026-11-15

The [live Archicad extra-field experiment](archicad-extra-fields-2026-11-15.md)
confirmed that Archicad 27 / Tapir 1.7.3 rejects both `useSIUnits=False` and `True`
with error 4002 (`additionalProperties`). Fully inline schemas reject extra
root and nested fields. Extra keys within the tested common-schema references
are accepted instead, consistent with the reported reference-validation gap.
Unknown JSON-null fields behave like omission in the tested cases. This
follow-up supplies live evidence for the earlier offline compatibility finding.
