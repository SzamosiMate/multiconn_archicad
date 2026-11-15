# Optional default serialization: implementation plan

Date: 2026-11-15, Europe/Budapest. Status: **implementation pending**.

Work branch: `codex/optional-default-compatibility`, created from the element-query
tip `9e4de6f`. General compatibility checks have been moved from the SI query
module into [`tests/clients/smoke`](../../tests/clients/smoke/README.md).
The initial 15-case smoke suite has **5 passing and 10 deliberately failing
cases** before the serializer/generator implementation. SI-specific query
behavior remains tested separately in the query suite.

## 1. Objective and selected policy

Preserve informative Python method/model defaults while making generated API
requests compatible with older servers that reject newly added optional fields.

The selected approach is **default exclusion with automatic Literal preservation**:

- Keep upstream schemas, field descriptions, method signatures and model defaults.
- Generated request payloads explicitly use `exclude_defaults=True` alongside
  the existing JSON mode, wire aliases and `exclude_none=True`.
- A serializer on `APIModel` preserves defaulted, direct `Literal` fields when
  default exclusion would otherwise remove them. This includes Boolean literals
  such as `success=False`, not just string fields named `type` or `status`.
- A generation audit proves that this Literal rule agrees with original wire
  requiredness for both Tapir and Official models. Fail when that assumption
  changes; do not silently broaden the runtime rule.
- Ordinary dumps without default exclusion keep their existing behavior.

This is intentionally a value-based policy. An optional value equal to its
model default is omitted even when the caller explicitly supplies it.

| Case | Selected request behavior |
| --- | --- |
| Optional Boolean default false, omitted | Omit |
| Same option explicitly false | Omit |
| Same option explicitly true | Send true |
| Optional default-valued number, string or collection | Omit according to Pydantic's default comparison |
| Required field with no Python default | Retain through normal Pydantic serialization |
| Wire-required Literal with a Python convenience default | Retain unless another explicit serialization filter excludes it |
| Existing None omission | Preserve `exclude_none=True` behavior |

For example, `use_si_units` remains defaulted to `False` in the method and
`useSIUnits` remains defaulted to `False` in the model. An ordinary generated
read omits the flag; an SI query explicitly sending `True` retains it.

## 2. Evidence and scope

The [generator trace](reports/codegen/optional-input-defaults-2026-11-14.md)
identified schema defaults becoming model defaults, method defaults and finally
unsolicited request fields. The [live experiment](reports/codegen/archicad-extra-fields-2026-11-15.md)
confirmed that Archicad 27 / Tapir 1.7.3 rejects both `useSIUnits=False` and `True`
with error 4002 at `#/useSIUnits`. Fully inline schemas also reject extra root
and nested fields. Acceptance of extras through common-schema references is a
separate validation gap, not a backward-compatibility guarantee.

The current schema/model comparison found:

| Provider | Wire-required fields with Python defaults | Non-Literal cases | Optional direct Literal fields |
| --- | ---: | ---: | ---: |
| Tapir | 49 | 0 | 0 |
| Official | 46 | 0 | 0 |

These counts are observations, not constants to enforce after every release.
The structural relationship is the invariant to enforce.

The implementation covers shared `APIModel` serialization and generated
request construction for **both providers**, including nested types, lists,
root/union request handling and the Official rename special case.

Do not implement:

- None-default replacement, UNSET sentinels or caller-presence tracking.
- Per-field `json_schema_extra` tags, generated required-field registries or
  runtime loading of JSON schemas.
- Schema-default removal, signature changes, return-shape changes or new public
  method options.
- Silent version-dependent stripping/downgrading of explicitly requested features.
- Fixes to Tapir's common-schema validation or changes to the query operators.

## 3. Runtime serializer

Primary file: [`models/base.py`](../../src/multiconn_archicad/models/base.py).

Implement the policy through an inherited **`@model_serializer(mode="wrap")`**.
Overriding `model_dump()` alone does not cover nested models, JSON dumping or
`TypeAdapter` serialization; local probes demonstrated those failures.

### Protected-field predicate

Use `type(self).model_fields`. A field is a restoration candidate when:

1. `get_origin(field.annotation) is Literal`.
2. It has a concrete Python default, rather than `PydanticUndefined` or a default
   factory.
3. It is missing from the handler's serialized result under its effective
   serialization key.

Do not infer protection from names such as `type`, `status` or `success`.
Use the direct annotation exposed by Pydantic; do not automatically protect
nullable unions containing a Literal. The audit must match this exact rule.

Required Literals without defaults already survive ordinary default exclusion;
they need no restoration. Non-Literal fields retain native exclusion behavior.

### Algorithm and serialization fidelity

1. Call the normal serialization handler first.
2. If `info.exclude_defaults` is false, return its result without intervention.
3. If its result is not a dictionary, retain normal root-model serialization.
4. Find missing protected fields eligible under the other serialization filters.
5. Obtain their **serialized** values with default exclusion disabled, retaining
   the caller's mode, aliases, context and other applicable filters.
6. Add only missing eligible values; never overwrite a value the handler already
   serialized.

A practical implementation can use a constrained second serialization pass
selecting only the missing protected scalar fields, with `exclude_defaults=False`.
That pass re-enters the wrapper's no-restoration branch and must not recursively
reapply the exclusion policy. Intersect its field selection with any original
`include` selection and preserve the original `exclude` selection. Avoid a full
second dump of the entire model tree.

Do not restore values with unconditional `data[name] = getattr(self, name)`:
that can bypass aliases, JSON conversion, field serializers and explicit filters.

The implementation must preserve:

- `mode="python"` and `mode="json"`, plus `model_dump_json()`.
- Effective `by_alias` behavior, including configuration-driven alias defaults
  used by `TypeAdapter`, `alias` and `serialization_alias`.
- Explicit `include`, `exclude`, field-level exclusion and applicable conditional
  field-exclusion behavior. Explicit exclusion wins over Literal protection.
- Existing `exclude_none` and explicitly requested `exclude_unset` behavior.
- Serialization context and ordinary field serializers.
- Root-model and validated union behavior.

Only Literal default exclusion is reversed. The hook does not promise to undo
every other reason a caller might intentionally exclude a field.

Preserve the existing `APIModel.model_dump()` / `model_dump_json()` defaults
(`by_alias=True`, `exclude_none=True`); do not make `exclude_defaults=True`
their global default.

### Existing mixin

[`OmitDefaultsMixin`](../../src/multiconn_archicad/models/mixins.py) already
defaults its dump methods to `exclude_defaults=True`. Keep that opt-in behavior.
Its calls should gain Literal protection through the shared serializer, while
explicit `exclude_defaults=False` continues overriding the mixin default.
Test configured models in fresh subprocesses because the model registry locks
after import. Do not modify unrelated configuration mixins.

## 4. Audit the generator assumption

Add a shared audit, for example
`code_generation/shared/default_policy_audit.py`, with a callable audit function
and a nonzero-exit CLI accepting `--provider tapir|official|both`.

Use the patched schemas actually consumed by generation and the finalized
Pydantic classes. Do not compare against Pydantic's generated JSON Schema:
constructor defaults have already changed its requiredness representation.

For every matched common/command object field, verify:

1. Every wire-required field that has a Python default matches the runtime
   defaulted-Literal predicate.
2. Every field matching that predicate is wire-required. A newly optional
   direct Literal must cause a review failure, rather than being silently
   restored into requests.
3. The Literal/default representation is compatible with the restoration
   implementation, including the scalar value types it handles.

Match fields through Python names and wire aliases. Resolve ordinary schema
references and traverse conditional/union branches as needed to establish
effective requiredness. Account for deliberately renamed/generated definitions
using existing schema/model inventories and alias conventions.

Do not skip unmatched or ambiguous fields relevant to the policy. Emit a
diagnostic requiring an explicit mapping or requiredness review. Do not turn
the audit into a blanket rejection of unrelated schemas that have no relevant
defaulted fields. Ordinary optional fields with defaults remain allowed.

Diagnostic examples:

```text
tapir: SomeParameters.option
Defaulted Literal is optional in the wire schema; default restoration would
send it even when default exclusion was requested.

official: SomeType.count
Wire-required field has a Python default but is not a protected Literal;
exclude_defaults could omit it.
```

Integrate the shared audit:

- Into the existing strict Tapir generation audit after final model outputs exist.
- As a final audit stage of the Official model pipeline.
- As a fresh-process preflight before unified generation removes/rewrites its
  outputs, so unified-only regeneration also checks the assumption.
- Into handwritten code-generation regression tests.

Use fresh module state at pipeline boundaries. The Official pipeline runs stages
in-process, so do not audit stale imported model classes after rewriting them.
A subprocess CLI is the straightforward boundary there.

No fixed 49/46 count assertion and no automatic fallback to field tags. A changed
invariant stops generation and explains what needs review.

## 5. Generated request serialization

In [`02_generate_method_code.py`](../unified/api_generator/02_generate_method_code.py),
change generated request dumps to:

```python
validated_params.model_dump(
    mode="json",
    by_alias=True,
    exclude_none=True,
    exclude_defaults=True,
)
```

Cover `_build_body()` and `_generate_rename_navigator_item_fix()`, including
normal requests, validated parameter unions/root wrappers and dry-run companion
methods. Do not hand-edit generated client files.

Keep signature construction and the shipped-signature snapshot unchanged.
Keep response validation and return unwrapping unchanged.

In [`05_generate_command_tests.py`](../unified/api_generator/05_generate_command_tests.py),
align ordinary expected-payload serialization with the new request policy.
Retain independent handwritten/generated contract assertions below: comparing
two dumps produced by the same model is insufficient evidence of correctness.

Regenerate unified clients and method tests for **both** providers. Model
declarations, model schemas and TypedDicts do not need changes for the Literal
approach; full model regeneration is not necessary merely to activate it.
The model pipeline changes add audit enforcement for future regeneration.

## 6. Regression tests

### Serializer tests

Add focused tests, for example `tests/clients/unit/test_request_default_serialization.py`:

| Scenario | Required assertion |
| --- | --- |
| Required string Literal default + ordinary required value | Both retained |
| Required Boolean Literal default false/true | Retained |
| Optional Boolean default false | Omitted for omitted and explicit false; true retained |
| Optional string/number default | Default omitted; nondefault retained |
| Default collection | Native Pydantic default comparison preserved; nondefault collection retained |
| Nested model and list of models | Literal protection and optional exclusion at every tested depth |
| Actual `NormalNumberPropertyValue(value=3)` | `type` and `status` retained |
| Actual `InputConstraint(..., fromLastPoint=False)` | Optional flag omitted |
| Aliased Literal | Correct wire key under by_alias, Python key otherwise |
| Direct dump / JSON dump / TypeAdapter dump | Same policy through all paths |
| Root/union request | Correct original payload shape, no new root key |
| Explicit include/exclude or field exclusion | No excluded field resurrected |
| Field serializer/context | Restored value uses normal serialization |
| No default exclusion | Existing ordinary output retained |
| Configured `OmitDefaultsMixin` | Literals protected; explicit false override of exclusion respected |

Test the supported Pydantic floor (2.12) as well as the normal development
environment for the serializer APIs/options used. Do not assume a behavior
observed only on the installed 2.13.4 is available at the declared minimum.

### Audit tests

Use small independent schema/model fixtures and current-output checks:

- Valid required defaulted Literal passes; string and Boolean cases.
- Required defaulted non-Literal fails with an actionable location.
- Optional defaulted direct Literal fails.
- Optional nullable Literal that the runtime predicate does not protect is
  handled consistently with the source schema.
- Wire aliases, referenced definitions and conditional/union requiredness.
- Relevant missing/ambiguous mappings fail instead of reducing audit coverage.
- Both current provider outputs satisfy the invariant.
- Pipeline preflight stops before rewriting unified outputs on audit failure.

### Independent request compatibility tests

The representative checks now live in
`tests/clients/smoke/test_request_compatibility.py`, with an independent old-server
fixture in `tests/fixtures/request_compatibility/property_read_tapir_1_7_3.json`.
Extend those checks and `tests/code_generation/test_unified_shipped_signatures.py`
as needed to establish these literal expected payloads:

```text
SI option omitted       -> no useSIUnits key
SI option explicit None -> no useSIUnits key (existing convention)
SI option explicit False-> no useSIUnits key (selected policy)
SI option explicit True -> useSIUnits: true
```

The former query-module compatibility tests have been replaced by these general
smokes. Their explicit-False case deliberately expects omission, rather than the
old forwarding assertion. The five original omission failures remain represented
and should pass after implementation. Query SI reads still explicitly send true;
returned precision is unchanged.

Also cover:

- An isolated generated method gaining a new optional schema-defaulted flag;
  its old call emits no new key while its signature still displays the default.
- Required Literal fields nested in actual request records remain present.
- Explicit nondefault options remain present.
- Shipped positional/keyword-only order is unchanged.
- Ordinary property writes and dry-run companions retain their intended
  command, payload and return behavior.
- Minimal old-style property-read payload validates against a self-contained
  older closed schema; adding the unsupported flag fails that control schema.

Do not make routine tests depend on a local Git tag or a live Archicad instance.
Use a small recorded schema fixture for the compatibility assertion.

## 7. Implementation sequence and verification

1. Record baseline branch/status; preserve existing user changes and scratch data.
2. Add independent failing serializer and request-contract tests.
3. Implement the shared serializer hook and small supporting helpers.
4. Add and test the shared audit; wire it into the three generation entry points.
5. Update unified method/test generators, including the rename special case.
6. Run the audit against both current provider outputs.
7. Regenerate unified clients/method tests; review that signatures and model
   defaults remain unchanged and request dumps carry the intended policy.
8. Run focused tests, then the routine suite and both providers' deep generated
   tests appropriate to the shared generator change.
9. Repeat unified generation and compare intended outputs for reproducibility.
10. Run the live compatibility check below, update documentation, and save final
    results with the change.

Representative commands (the audit module is new work in this plan):

```console
python -m code_generation.shared.default_policy_audit --provider both
python -m code_generation.unified.api_generator.run_pipeline
python -m pytest tests/clients/smoke -m smoke -q -p no:cacheprovider
python -m pytest tests/clients/unit/test_request_default_serialization.py tests/code_generation tests/utilities/queries/test_si_property_reads.py tests/orchestration/unit/test_model_config.py -q -p no:cacheprovider
python -m pytest -p no:cacheprovider
python -m pytest --schema-tests=deep tests/generated/test_generated_tapir_models.py tests/generated/test_generated_tapir_methods.py tests/generated/test_generated_official_models.py tests/generated/test_generated_official_methods.py tests/generated/test_model_integrity.py tests/code_generation -p no:cacheprovider
git diff --check
```

Use the project's environment, run Ruff on changed implementation/test files,
and check any newly introduced typing. Save results and distinguish genuinely
pre-existing failures from policy changes that require test updates. Follow the
generation brief's normal fetch/regeneration procedure only if model inputs
actually need regeneration; do not refresh upstream inputs as a side effect
of this work.

For live verification, rediscover the current instance rather than assuming
port 19723. On Tapir 1.7.3 verify that the **generated** property client now sends
no SI field and succeeds for ordinary reads and explicit false. A raw true flag
must still fail there, confirming that the server has not changed. Query SI
utilities should continue rejecting unsupported Tapir before reading. Test SI
true on a 2.0.0+ instance if available; otherwise distinguish the existing
mocked SI-read checks from a live new-version check. No writes are necessary.

## 8. Documentation and accepted limitations

Update the [generation brief](archicad_api_codegen_brief.md), applicable model
configuration documentation and the SI integration notes to state:

- Signatures/models retain documented defaults.
- Generated requests exclude optional values equal to their Python defaults.
- Direct defaulted Literals are preserved by the shared hook, under an audited
  schema/model invariant.
- Explicit default-valued options cannot be forced through the normal generated
  request path. A caller needing an exact payload can use the existing raw core
  interface deliberately; do not add a new per-method override in this change.
- Client defaults can differ from the installed server's behavior. A future
  changed default can make omission semantically different, even for an explicit
  argument. Regeneration review must continue to examine changed defaults.
- Modification fields where omission means "leave unchanged" can differ from
  explicit default assignment or clearing a collection. This is an accepted
  limitation of the selected general policy, not solved by Literal protection.
- Default factories retain native Pydantic semantics; do not evaluate arbitrary
  factories manually in the restoration hook.
- The policy does not provide automatic server capability/version negotiation.

Link this plan from the earlier investigation. Its initial presence-aware repair
proposal is historical; the selected implementation here supersedes that proposal.
Retain the live experiment's results without changing their meaning.

## 9. Completion criteria

- Defaulted required Literals survive nested, JSON and TypeAdapter serialization.
- Ordinary optional defaults disappear from generated requests for both providers.
- Explicit serialization filters, aliases and field serializers are respected.
- Signatures, model defaults, response handling and ordinary dumps stay intact.
- Both provider audits pass and independently tested invalid invariants fail
  generation with clear diagnostics.
- Existing SI tests reflect the deliberate explicit-False policy; the five
  known omission failures are resolved.
- Independent generated-method compatibility tests pass; generated/mocked
  verification is distinguished from live results.
- Live older-Tapir default calls succeed because the actual request omits the flag.
- The generated diff, documentation and saved validation results match this scope.

This document plans the implementation; creating it does not implement the
serializer, change the generator or regenerate clients.
