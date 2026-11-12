# Integrating a query editor

This guide is for consumers building editors or extending field discovery.
Use the [practical guide](element_queries.md) for scripts and the
[reference](element_query_reference.md) for execution semantics.

The engine owns field metadata, test validation, serializable drafts, expression
compilation, and evaluation. The consumer owns controls, bindings, presentation,
and selection behavior. Metadata/input descriptions and row compilation make no
API calls; bound discovery and execution perform the reads.

## Discover and resolve fields

```python
# Live example: api is the UnifiedApi from the practical guide.
fields = api.utilities.element.discover_query_fields()
for entry in fields.browse_fields():
    print(entry.group_path, entry.field.name, entry.field.reference)
```

The combined `QueryFieldCatalogue` contains built-in element types, properties,
and classification systems. `resolve(reference)` returns a descriptor or `None`.
Use the descriptor's JSON-friendly `reference`, not its label, for identity.
Display grouping is separate from resolution.

To refresh fields already referenced by a saved or incomplete draft, pass its
rows to `api.utilities.element.discover_query_fields(draft.rows)`. This discovers
the referenced property/system IDs instead of depending on the browse list.
On Archicad versions below 28, the browse path uses legacy property/default-tool
availability information to restrict offered properties. Direct lookup is not
restricted by that browse policy. An absent browse choice does not prove a
saved GUID is invalid.

Individual `PropertyCatalogue` and `ClassificationCatalogue` snapshots support
iteration, identity lookup, `.get()`, `.supported`, `.unsupported`, `.search()`,
and `.describe()`. They hold no live API/cache connection. Refresh explicitly
when project metadata changes. Unsupported properties remain visible with a
reason; duplicate labels can coexist, but duplicate identities are rejected.

Descriptors expose `name`, `group`, `group_path`, `qualified_name`, `reference`,
`supported`, `unsupported_reason`, `test_model`, and test operations:

- `operators()` lists the compatible operators.
- `create_test(**data)` constructs and validates a compatible test.
- `validate(test)` checks compatibility and metadata-dependent operands.
- `test_schema()` describes a complete executable test.
- `describe_test_inputs(current_data)` describes inputs for the current draft.

Classification item trees and property measure metadata stay on their concrete
descriptors. Refer to [classification utilities](classifications.md) for tree
operations; measure metadata does not perform numeric unit conversion.

## Input descriptions

The normal schema starts with the descriptor's test model JSON Schema.
Field-specific descriptors can enrich it, for example with classification item
UUID choices. `describe_test_inputs()` derives editable fields from that schema
and the test model's `input_availability()` rules for the current partial data.
This lets the UI change required/forbidden operands when the operator changes.

`TestInputs` contains:

| Member | Meaning |
| --- | --- |
| `fields` | Tuple of visible `TestInput` records |
| `definitions` | Shared JSON Schema definitions needed by fragments |
| `forbidden_fields` | Payload keys that must be removed for the selected mode/operator |

Each `TestInput` has `name`, `schema`, and `required`. These are framework-neutral
descriptions; the consumer decides which controls to render. An editor must
remove forbidden fields instead of saving stale operands as `null`.

### Element-type choices and executable schema

The element-type descriptor lists five named presets first (All Types, 3D Types,
2D Types, 3D Component Types, and 3D Types with Components), then individual types. Each choice is a `oneOf` entry whose `const` is an array of
concrete type strings. For example, the main-plus-components preset is presented
with a title but saves its concrete array.

The full executable schema still accepts arbitrary valid type combinations.
Adding preset choices to the input fragment does not restrict saved queries to
the preset menu.

```python
from dataclasses import replace
from multiconn_archicad.utilities.queries import ElementTypeInfo

field = ElementTypeInfo()
description = field.describe_test_inputs({"kind": "element_type", "types": ["Wall"]})
types_input = next(item for item in description.fields if item.name == "types")

# Demonstrate the same immutable-record update used by the descriptor.
original_schema = dict(types_input.schema)
changed_input = replace(types_input, schema={**types_input.schema, "title": "Choose types"})
changed_description = replace(description, fields=(changed_input,))
assert changed_description.fields[0].schema["title"] == "Choose types"
assert types_input.schema == original_schema
```

`dataclasses.replace()` creates a new record with the named members changed and
the others retained. Here the dictionary unpack creates a new schema dictionary;
the original input/description remain unchanged. Replacement is shallow, so
nested objects not explicitly copied can still be shared.

## Editable rows

Import `QueryRow`, `QueryRows`, `validate_row`, and `build_query` from
`multiconn_archicad.utilities.queries.editing`.

An executable query must be valid. An editor also needs to save incomplete
predicates and temporarily unmatched parentheses. `QueryRows` supplies that
draft shape without introducing a second handwritten predicate hierarchy:

```python
from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query

wall_row = QueryRow(
    open_parentheses=1,
    predicate={"kind": "element_type", "test": {"kind": "element_type", "types": ["Wall"]}},
    join_next="or",
)
door_row = QueryRow(
    close_parentheses=1,
    predicate={"kind": "element_type", "test": {"kind": "element_type", "types": ["Door"]}},
)
draft = QueryRows(rows=[wall_row, door_row])
```

Each row has nonnegative `open_parentheses`/`close_parentheses` counts, a generic
JSON `predicate` dictionary, and `join_next` (`"and"` by default, or `"or"`).
Rows are mutable with assignment validation; drafts can contain incomplete
predicate data. Group predicates belong in the compiled expression, not inside
a row's leaf payload. The final row's connector is retained but ignored.

Each row also has a private UUID exposed by `.row_id`. It identifies a live row
for diagnostics and bindings and is omitted from JSON. A deep model copy retains
it; `.duplicate()` copies the payload with a new ID. Reloading saved JSON creates
new IDs. Do not treat row IDs as persisted query identities.

```python
saved = draft.model_dump_json(indent=2)
loaded = QueryRows.model_validate_json(saved, context={"require_schema_version": True})
assert loaded.rows[0].predicate == wall_row.predicate
assert loaded.rows[0].row_id != wall_row.row_id
```

Drafts and executable queries share `schema_version`, currently `"1.0"`.
Draft JSON is not executable-query JSON. Keep the draft when the user needs to
resume editing, and compile it when execution is requested.

## Compile and validate a draft

```python
from multiconn_archicad.utilities.queries import validate_query

built = build_query(loaded)
assert built.query is not None, built.issues
validate_query(built.query, []).raise_for_errors()  # Type-only example.
print(built.query.model_dump_json(indent=2))
```

Compilation applies AND before OR; parentheses override precedence. Closing
parentheses are applied before the outgoing connector. `build_query()` returns
either a complete query with a read-only expression-location-to-row-ID map, or
`query=None` and issues. It does not return a partially executable expression.

Build issue codes are `empty_expression`, `unmatched_open`, `unmatched_close`,
`group_in_row`, and `invalid_predicate`. Issues include a row ID when applicable,
location, code, and message. `validate_row(row)` checks an individual leaf's
structural validity; it cannot validate parentheses against neighboring rows or
project metadata.

Compilation is offline and structural. Follow it with metadata validation, or
let bound execution discover and validate current references. For a metadata
issue, use `built.row_id_at(issue.location)` to locate the responsible row;
deeper test-field locations resolve to their containing leaf row. Query-wide
issues need a document-level display.

## Extension boundaries

`TestRegistry.from_union(PropertyTest)` derives property-family matching from
the authoritative union. Matching no family produces an unsupported descriptor;
matching multiple families raises `AmbiguousPropertyTypeError`. Adding a family
requires its typed model/operator/metadata rules and registry/union integration,
not only another dropdown option.

`ContextBuilder` prepares deduplicated source requests before evaluation.
`PROPERTY_VALUES`, `TYPE_MEMBERSHIP`, `CLASSIFICATION_FIELDS`, and
`CLASSIFICATION_VALUES` provide shared execution data. A prepared context can
also be supplied completed synthetic data for offline evaluation. Missing
prepared keys are execution-input errors, not unavailable property values.
Keep reads in bound utilities/context sources and evaluation in predicates.

Before extending the public predicate model or candidate scope, review the
[development decisions](../development/element_queries_plan.md). Current
offline examples cover [field descriptors](../../examples/element_query_fields.py),
[row compilation](../../examples/element_query_rows.py), and
[batched evaluation](../../examples/element_query_predicates.py).
