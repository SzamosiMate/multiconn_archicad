# Element query definitions

Stages 1-10 provide query models, JSON serialization, JSON Schema, test-family
behavior, uniform field information, batch property discovery, and query-wide
context validation, plus individual property comparisons. The catalogue,
validator, and comparisons can use supplied metadata/values offline. The bound
property utility can fetch a fresh metadata/value batch from Archicad. The query
tree can evaluate supplied per-element data. The bound element utility searches
Archicad directly or filters an existing population with the same query.

Import the public models from `multiconn_archicad.utilities.queries`.

## Stage 7 behavior decisions

The query contract follows Archicad Find and Select: normal AND/OR, negative operators
on individual tests, case-insensitive text with significant whitespace, and
ordinary numeric comparisons without added tolerance or display rounding.
Unavailable properties make every operation false except `not available`.
All six common user-defined-property state operations are deferred.

Text, numeric and Boolean comparisons, property-condition handling, and recursive group
evaluation and the bound execution APIs are implemented. General
`Negate` / `"not"` predicates have been removed; JSON using `"kind": "not"` is
rejected at any depth. The complete record of
default/custom/undefined behavior, Tapir error paths, and retrieval limits is in the
[stage 7 reference](../../docs/ELEMENT_QUERY_ARCHICAD_BEHAVIOR.md).

## Constructing a query in Python

This describes walls taller than three metres whose description starts with
`External`. The property GUIDs are placeholders, not built-in property aliases.

```python
from uuid import UUID

from multiconn_archicad.utilities.queries import (
    AllOf,
    ElementTypePredicate,
    NumberOperator,
    NumberTest,
    PropertyPredicate,
    Query,
    TextOperator,
    TextTest,
)

query = Query(
    where=AllOf(
        items=(
            ElementTypePredicate(types=("Wall",)),
            PropertyPredicate(
                field_id=UUID("22222222-2222-4222-8222-222222222222"),
                test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3),
            ),
            PropertyPredicate(
                field_id=UUID("11111111-1111-4111-8111-111111111111"),
                test=TextTest(operator=TextOperator.STARTS_WITH, value="External"),
            ),
        )
    )
)

serialized = query.model_dump_json(indent=2)
restored = Query.model_validate_json(serialized)
assert restored == query
```

The executable equivalent is [the schema example](../../examples/element_query_schema.py).
`ElementTypePredicate` also accepts the existing Tapir `ElementType` enum members.
Python sequences supplied to collection fields become immutable tuples; the JSON
representation uses arrays.

## Operator enums

Each family declares one operator `StrEnum`: `TextOperator` or `NumberOperator`.
Python code can use named members, while JSON uses their readable string values.
Pydantic parses those values into enum members. `kind` remains a fixed `Literal`
discriminator.

```python
from multiconn_archicad.utilities.queries import NumberOperator, NumberTest

test = NumberTest(operator=NumberOperator.GREATER_THAN, value=3)
assert test.operator is NumberOperator.GREATER_THAN
assert test.model_dump(mode="json")["operator"] == "is greater than"
```

`operators()` iterates the enum declared by the model's `operator` field and
returns a tuple of readable strings for UI/MCP consumers. JSON Schema represents
operator enums in `$defs`, referenced from each test's operator field. There is
no Literal-operator fallback, migration alias, or transitional schema support.
This is an unreleased design; refactor its models and examples directly.

## Serialized query

The Python example produces this JSON:

```json
{
  "schema_version": "1.0",
  "where": {
    "kind": "all",
    "items": [
      {
        "kind": "element_type",
        "types": ["Wall"]
      },
      {
        "kind": "property",
        "field_id": "22222222-2222-4222-8222-222222222222",
        "test": {
          "kind": "number",
          "operator": "is greater than",
          "value": 3.0
        }
      },
      {
        "kind": "property",
        "field_id": "11111111-1111-4111-8111-111111111111",
        "test": {
          "kind": "text",
          "operator": "starts with",
          "value": "External"
        }
      }
    ]
  }
}
```

`Query.model_validate(payload)` parses a Python dictionary.
`Query.model_validate_json(text)` parses JSON. `model_dump(mode="json")` returns a
dictionary containing JSON-compatible values, including strings for UUIDs and
element types, and arrays for predicate collections.

## Boolean composition

`AllOf` and `AnyOf` can contain property predicates, element-type predicates, or
other groups. Negative comparisons use a test's operator:

```python
from multiconn_archicad.utilities.queries import (
    AllOf, AnyOf, ElementTypePredicate, PropertyPredicate, Query, TextTest,
)

query = Query(
    where=AllOf(
        items=(
            AnyOf(
                items=(
                    ElementTypePredicate(types=("Door",)),
                    ElementTypePredicate(types=("Window",)),
                )
            ),
            PropertyPredicate(
                field_id="11111111-1111-4111-8111-111111111111",
                test=TextTest(operator="does not contain", value="Temporary"),
            ),
        )
    )
)
```

This describes doors or windows whose referenced text property does not contain
`Temporary`. An unavailable property makes that negative comparison false, just
like every other implemented property operation. There is no general negation
node and no automatic rewriting of saved `"not"` queries. This removes an initial,
unreleased schema sketch; the default version string remains `"1.0"`.

## Structure-validation contract

- Text operands must be strings. Numbers, booleans, bytes, and null are rejected.
- Boolean operands must be actual booleans (`true` / `false` in JSON). Numbers
  and strings such as `1` or `"False"` are rejected. `BooleanTest` supports scalar
  Boolean properties with `is` / `is not`, both built-in and user-defined.
- Numeric operands accept finite integer or real numbers. Booleans, numeric strings,
  null, NaN, and infinities are rejected. Integer operands are stored as floats.
- `NumberTest` supports scalar integer and real properties, regardless of measure
  type. Measured values use SI units implicitly: metres for length, square metres
  for area, cubic metres for volume, and radians for angle. Plain numbers are
  unitless. There is no `unit` field.
- Zero and negative numeric operands and empty text operands are structurally valid.
- Integer properties may use fractional comparison thresholds, such as greater
  than `2.5`. Lists and numeric enumeration choices do not use `NumberTest`.
- Property identifiers accept UUID objects or valid UUID strings. Identifiers are
  not resolved against a project at this stage.
- Element types accept Tapir enum members or their exact serialized strings.
- Unknown fields, operators, discriminator values, and element types are rejected.
- Property/boolean predicates in a union need an explicit `kind` in incoming
  dictionaries/JSON. Concrete Python constructors supply their own `kind` default.
- `all`, `any`, and element-type collections must contain at least one item.
- The envelope defaults to `schema_version: "1.0"`, from the public
  `QUERY_SCHEMA_VERSION` constant. Parsing retains a plain string. Before any API
  reads, execution requires two non-negative integer components (`major.minor`),
  the same major as the executor, and an equal or older minor. Compare components
  numerically: a `1.10` executor accepts `1.9`. Breaking changes increment the
  major; backwards-compatible changes increment the minor. No migration occurs.
  Malformed versions raise `ValueError`; unsupported versions raise
  `UnsupportedQueryVersionError` with `requested_version` and `supported_version`.
  Version parsing/comparison uses the existing `packaging.version.Version`
  dependency; the query-specific helper restricts syntax and supported versions.
- Models are frozen, and collection fields are tuples. Reconstruct a model to
  validate an edit. Pydantic's unchecked APIs such as `model_construct()` and
  `model_copy(update=...)` are not validation entry points for untrusted input.

Text operators are `is`, `is not`, `contains`, `does not contain`, `starts with`,
and `ends with`. Numeric operators are `is`, `is not`, `is greater than`,
`is greater than or equal to`, `is less than`, and `is less than or equal to`.
Their spellings are part of the serialized contract. Text comparisons are
case-insensitive with significant whitespace. Numeric comparisons use actual
numeric values without added tolerance or display rounding. Parsing preserves
the supplied text operand; case folding belongs to evaluation, not serialization.

For example, this fails during structure validation because a numeric test does
not offer the `contains` operator:

```python
NumberTest.model_validate({"operator": "contains", "value": 3})
# Raises pydantic.ValidationError.
```

Selecting a text test for a real length property is a different error. The explicit
property-context validation below detects that against supplied metadata.

## Test-family behavior and explicit validation

The two validation steps have distinct entry points:

1. Constructing a test, or calling `model_validate()`/`model_validate_json()`,
   invokes Pydantic's structure validation: operator choices, operand types, and
   finite numbers.
2. Calling `test.validate_for(details)` explicitly checks property compatibility
   and any metadata-dependent operand rules. It does not fetch metadata.

Each family implements `validate_for()` explicitly. Text, numeric and Boolean tests reuse
their `accepts()` rule to check the property's type; their operands were checked
when constructing the model. Future enumeration families will additionally check
the selected value against the property's available choices. The base method is
abstract, so a new family cannot inherit a silent no-op.

Families raise `InvalidPropertyTestError` for expected property incompatibility or
metadata-dependent operand restrictions. It derives from `ValueError`, so existing
broad exception handlers remain compatible. Custom `validate_for()` implementations
should use this exception for expected validation failures; unrelated errors are
not interpreted as user-query problems.

For an offline example:

```python
from multiconn_archicad.models.tapir.types import PropertyDetails
from multiconn_archicad.utilities.queries import NumberTest, TextTest

details = PropertyDetails.model_validate({
    "propertyId": {"guid": "22222222-2222-4222-8222-222222222222"},
    "propertyType": "Custom",
    "propertyGroupName": "Example",
    "propertyName": "Height",
    "propertyCollectionType": "Single",
    "propertyValueType": "Real",
    "propertyMeasureType": "Length",
    "propertyIsEditable": True,
    "isExpressionBased": False,
})

test = NumberTest(operator="is greater than", value=3)
test.validate_for(details)  # Succeeds: this is a scalar numeric property.

print(NumberTest.accepts(details))  # True
print(NumberTest.operators())      # Readable strings, without navigating JSON Schema.
test_schema = NumberTest.schema_for(details)

wrong_test = TextTest(operator="contains", value="3")  # Structure is valid.
wrong_test.validate_for(details)  # Raises InvalidPropertyTestError: incompatible property type.
```

The shared `PropertyTestModel` interface exposes:

| Method | Responsibility |
| --- | --- |
| `operators()` | Return the operator enum's readable values as an immutable tuple |
| `accepts(details)` | Declare metadata compatibility for discovery and validation |
| `validate_for(details)` | Explicitly validate the selected test against property metadata |
| `schema_for(details)` | Describe a compatible test, with metadata-specific choices when needed |
| `evaluate(raw_value)` | Compare one successful read string, returning `BatchSlot[bool]` |

`schema_for()` first checks compatibility and then returns JSON Schema. A family
can override it to enrich available values from metadata. Measure information
stays in `PropertyDetails`; selecting the numeric family does not discard it.

## Individual property comparisons

Family `evaluate()` methods compare supplied strings without fetching metadata or
calling Archicad. They do not repeat property-context validation; validate against
the catalogue before evaluating actual values.

```python
from multiconn_archicad.utilities.queries import NumberTest, TextTest

height = NumberTest(operator="is greater than", value=3)
assert height.evaluate("3.5").value is True
assert height.evaluate("2.5").value is False
assert height.evaluate("not a number").is_error

description = TextTest(operator="is", value="External")
assert description.evaluate("EXTERNAL").value is True
assert description.evaluate(" External").value is False
```

Numeric families call `float(raw_value)` directly, without unit inference,
rounding, tolerance, or localized-number parsing. A conversion `ValueError`
becomes an error slot. Other unexpected exceptions propagate. Text operations
use `str.casefold()` on both strings and preserve whitespace and the serialized
operand. Successful comparisons always return `SUCCESS(True)` or
`SUCCESS(False)`; a false leaf is not a `FILTERED` slot.

Use `evaluate_property()` to interpret the existing property utilities' read
conditions before invoking a family:

```python
from multiconn_archicad.utilities import (
    BatchSlot, PropertyUnavailableError, PropertyUndefinedError,
)
from multiconn_archicad.utilities.queries import TextTest, evaluate_property

test = TextTest(operator="is not", value="Temporary")
assert evaluate_property(test, BatchSlot.success("External")).value is True

unavailable = PropertyUnavailableError.from_message("Unavailable")
assert evaluate_property(test, BatchSlot.failure(unavailable)).value is False

undefined = PropertyUndefinedError.from_message("Undefined")
result = evaluate_property(test, BatchSlot.failure(undefined))
assert result.is_success
assert result.value is False
```

The helper accepts completed read slots (`SUCCESS` or `ERROR`). Skipped
`FILTERED`/`UPSTREAM_FAILED` slots have no read value and are rejected, rather than
silently treated as a non-match. Both unavailability and undefined bypass the
family and produce false for every implemented operator, including negative
ones. Property utilities keep the two distinct error types; query evaluation
interprets both as false. All other read failures retain their original error
objects. The helper does not enforce query-wide
fatal-error policy; that belongs to the future execution boundary.

The [offline comparison example](../../examples/element_query_evaluation.py)
demonstrates matches, non-matches, conversion errors, unavailability, and undefined
values. These are individual property tests, not a query-tree executor.

## Family registry

Build a registry from the same `PropertyTest` union used by `PropertyPredicate`:

```python
from multiconn_archicad.utilities.queries import PropertyTest, TestRegistry

registry = TestRegistry.from_union(PropertyTest)
family = registry.resolve(details)  # NumberTest for the example above.

print(family.operators())
test = family.model_validate({"operator": "is greater than", "value": 3})
test.validate_for(details)
test_schema = family.schema_for(details)
```

Resolution uses each family's `accepts()` method. The registry stores an immutable
tuple of model classes, not project metadata. `registry.families` exposes those
classes for inspection. It does not fetch properties or traverse a query.

- No compatible family raises `UnsupportedPropertyTypeError`.
- Multiple compatible families raise `AmbiguousPropertyTypeError`, rather than
  selecting the first registered match.
- Both errors derive from `ValueError` and include property context.

`from_union()` uses `TypeForm[PropertyTestModel]` so mypy also rejects unions with
unrelated types. This requires mypy 2.2 or newer, without an experimental flag.
Runtime checks still reject non-union expressions and abstract family members.
The TypeForm backport is imported from `typing_extensions` for Python 3.12-3.14.
The static regression fixture can be checked with:

```console
python -m mypy --follow-imports=silent --warn-unused-ignores tests/utilities/typing/query_registry.py
```

It includes valid unions and expected type errors for unrelated members; unused
ignore checks ensure that those invalid forms remain rejected by the type checker.

The default union contains `TextTest`, `NumberTest` and `BooleanTest`.
Enumerations, GUID properties and lists remain unsupported for now.

### Boolean properties

Boolean tests use a Boolean operand and readable operator enum:

```python
from multiconn_archicad.utilities.queries import BooleanOperator, BooleanTest

test = BooleanTest(operator=BooleanOperator.IS_NOT, value=False)
assert test.evaluate("True").value is True
assert test.evaluate("False").value is False
```

In query JSON, a Boolean property leaf looks like this (replace the GUID with an
actual property reference):

```json
{
  "kind": "property",
  "field_id": "33333333-3333-4333-8333-333333333333",
  "test": {"kind": "boolean", "operator": "is", "value": true}
}
```

Tapir returns scalar Boolean values as the exact strings `"True"` and `"False"`.
The family explicitly decodes those strings. Other successful strings become
conversion errors, retained in diagnostic query outcomes. Undefined or unavailable
properties still evaluate to false for both operators, including `is not`.

Discovery selects this family from the property's Single/Boolean metadata;
`field.operators()` returns `("is", "is not")`, `field.test_schema()` describes a
Boolean operand, and `field.create_test(operator="is", value=True)` validates it.
The existing shared property source performs retrieval; no extra Boolean API
call or executor branch is needed.

### Adding a family

Implement a concrete `PropertyTestModel` subclass with `accepts()`,
`validate_for()` and `evaluate()`, declare its operator enum and operand fields,
and include it in `PropertyTest` in `models.py`. Override `schema_for()` when
choices depend on property metadata. Query parsing, JSON Schema and a newly
created registry then use that declaration automatically. Export the public
family/operator types from the queries module.

This is static schema extension, not runtime mutation of an existing query model.
The registry tests demonstrate an additional GUID family using a separate union
and Pydantic `TypeAdapter`; that family is not part of the default query schema.

## Uniform field information

`FieldInfo` defines the shared interface for field sources and implements test
construction, operator discovery and default schema generation. `PropertyInfo`
selects a property family through its registry; `ClassificationInfo` supplies
classification choices and tree-aware reference validation. Both use models from
`models.py`, inheriting common configuration/operator discovery from `TestModel`.
Descriptors perform no API calls. Using `details` from the offline example above:

```python
import json

from multiconn_archicad.utilities.queries import (
    PropertyInfo,
    PropertyPredicate,
    PropertyTest,
    Query,
    TestRegistry,
)

registry = TestRegistry.from_union(PropertyTest)
height = PropertyInfo(details, registry)

print(height.name)            # Height
print(height.group)           # Example
print(height.qualified_name)  # Example / Height
print(height.property_id)     # The property's UUID, independent of its name.
print(height.operators())     # Direct readable choices for the selected family.

test = height.create_test(operator="is greater than", value=3)
# create_test has validated both the test structure and the property's context.

height.validate(test)  # For independently constructed/existing test objects.

predicate = PropertyPredicate.model_validate({**height.reference, "test": test})
query = Query(where=predicate)
serialized_query = query.model_dump_json()

serialized_description = json.dumps(height.describe())
```

The [field-information example](../../examples/element_query_fields.py) runs this
flow with complete synthetic metadata, without a running Archicad.

| Member | Meaning |
| --- | --- |
| `name` | Upstream property name, preserved unchanged |
| `group` | Upstream property group, preserved unchanged |
| `qualified_name` | Derived `group / name`, or just `name` for an empty group |
| `reference` | Fresh JSON-friendly identity: `kind` and the property GUID |
| `supported` | Whether this field has an implemented test family |
| `unsupported_reason` | Why the field is unsupported, or `None` |
| `operators()` | The selected family's readable operator strings |
| `create_test(**data)` | Structure validation followed by property-context validation |
| `validate(test)` | Check an existing test's family and property-context rules |
| `test_schema()` | Metadata-aware schema, or `None` for an unsupported field |
| `describe()` | JSON-friendly reference, names, operators, test schema, and property measure type |

The runtime `PropertyInfo` also exposes its selected `test_model` and a copy of
its `details` snapshot. Measure metadata remains available in those details even
though all scalar quantities share `NumberTest`.

Property descriptions also expose `measure_type` as the upstream string:
`Length`, `Area`, `Volume`, `Angle`, `Default`, or `Undefined`. For example,
`height.describe()["measure_type"]` is `"Length"`. Both supported and unsupported
properties include it, including in `catalogue.describe()`. `Default` and
`Undefined` are preserved without inferring a physical quantity. This describes
the measure category; numeric query operands still use the existing SI convention.

`describe()` returns a separate discovery description, not a serialized Python
object or an executable query. Its `reference` can be combined with a test to
construct the existing property-predicate shape; query JSON is unchanged. Clients
can use the direct `operators` list without navigating the schema.

Names are display labels, not identities. Two properties with identical labels
remain distinct by GUID. Technical names and underscores are not split or
rewritten. Metadata is deep-copied at construction, and `details` returns a copy,
so external edits do not invalidate the selected family. Create a new
`PropertyInfo` to refresh the snapshot.

Constructing `PropertyInfo` directly with unsupported or ambiguous metadata
retains the registry's distinct errors. Batch discovery handles unsupported types
as described below.
`create_test()` raises Pydantic `ValidationError` for malformed test structure;
`validate()` rejects a mismatched family with `InvalidPropertyTestError` and delegates further
rules to the family's explicit `validate_for()` method.

Other field sources can implement `FieldInfo` with different references and test
models. Classification fields use `group = Classifications` and `name = system
name`, with all eight Archicad operations supported by ClassificationPredicate.
See [Classification utilities](classifications.md) for full JSON/Python examples,
operand rules and classification-specific Boolean behavior.

## Batch property discovery

For an existing `Utilities` instance bound to one `UnifiedApi`:

```python
catalogue = utilities.property.discover_query_fields()

for field in catalogue.search("height", supported_only=True):
    print(field.qualified_name, field.operators())

field = catalogue["22222222-2222-4222-8222-222222222222"]  # Use an actual project GUID.
if field.supported:
    test = field.create_test(operator="is greater than", value=3)
else:
    print(field.unsupported_reason)
```

`discover_query_fields()` calls Tapir `GetAllProperties` once and adapts the full
metadata batch. It reads no element values and does not use official property
name resolution. Both built-in and custom properties retain their upstream names,
groups, GUIDs, source types, measures, and other metadata.

The catalogue is a metadata snapshot with no project or connection binding.
Explicitly call discovery again after switching projects or changing metadata.
The old catalogue remains an independent snapshot.

For offline adaptation, use the same catalogue directly:

```python
from multiconn_archicad.utilities.queries import PropertyCatalogue, PropertyTest, TestRegistry

catalogue = PropertyCatalogue(
    property_details,  # An iterable of Tapir PropertyDetails models.
    TestRegistry.from_union(PropertyTest),
)
```

The [discovery example](../../examples/element_query_discovery.py) contains a
complete synthetic batch. The unit fixture
`tests/fixtures/query_property_discovery_19723.json` contains eight minimal metadata
records sampled from the saved read-only probe, so routine tests require no live
Archicad instance.

### Catalogue lookup and search

- Iteration and `catalogue.fields` preserve upstream order.
- `catalogue.supported` contains `PropertyInfo` objects; `catalogue.unsupported`
  contains `UnsupportedPropertyInfo` objects.
- `catalogue[id]` accepts shared `PropertyIdLike` inputs and raises `KeyError` for
  an unknown GUID. `catalogue.get(id)` returns `None` for an unknown GUID. Both
  reject malformed identifiers.
- `catalogue.search(text)` performs case-insensitive substring matching against
  qualified display names, including group labels. It preserves source order.
- `group="Wall"` restricts search to that exact group. `supported_only=True`
  excludes unsupported fields. An empty search string matches all fields.
- Duplicate GUIDs are rejected instead of overwriting records. Similar names or
  identical labels never merge distinct GUIDs.
- `catalogue.describe()` returns JSON-friendly field descriptions under `fields`.

### Unsupported fields and errors

Properties without a matching test family remain visible in the catalogue. Their names, identity, and
metadata are preserved, and discovery descriptions contain:

```json
{
  "supported": false,
  "unsupported_reason": "No query test family supports property ...",
  "operators": [],
  "test_schema": null
}
```

`supported` means a test family can describe and validate the metadata. It does
not advertise query execution or retrieval support at this stage, and does not
say whether an element has a value for that property. `create_test()` and
`validate()` on an unsupported field raise
`UnsupportedPropertyTypeError`; the field is not silently treated as text or as a
non-match. Enum, GUID and list properties currently follow this policy.

Only `UnsupportedPropertyTypeError` is converted to an unsupported field record.
Ambiguous family matches, unexpected adapter errors, API failures, and malformed
API responses still raise. Supply `registry=...` to `discover_query_fields()` when
using an explicitly extended or restricted family registry.

## Query-wide context validation

Parse the query first, then validate it against an existing catalogue:

```python
from multiconn_archicad.utilities.queries import Query, validate_query

query = Query.model_validate_json(saved_query_json)
catalogue = utilities.property.discover_query_fields()
result = validate_query(query, [catalogue])

if not result.is_valid:
    for issue in result.issues:
        print(issue.path, issue.code, issue.qualified_name, issue.message)

# Optional exception-based handling retains the complete result.
result.raise_for_errors()
```

`validate_query()` only uses the supplied query and metadata snapshot. It does not
fetch metadata, read element values, evaluate boolean expressions, or build a
second query tree. Success means the query is compatible with that snapshot; it
does not verify the currently open project or supply any element values to evaluation.
This property-catalogue validation does not interpret the version string.
`validate_query_version(query.schema_version)` checks it without API access;
all bound search/filter methods run that check automatically before metadata
reads or empty-population shortcuts. Parsing alone can retain an unsupported
query version for inspection.

Pass catalogues as one explicit sequence, for example
`validate_query(query, [property_catalogue, classification_catalogue])`.
Their order does not matter. Use an empty sequence for queries needing no field
metadata. The execution layer assembles this sequence from the field families
requested by `prepare()`; validation itself never discovers catalogues.
Both property and classification predicates use `field_id`. For a property this
is its property GUID; for a classification it is the system GUID, while the test
operand identifies a classification item when required. Field descriptor
`reference` dictionaries use the same `kind` and `field_id` keys as query leaves.

`validate_query()` delegates to `query.where.validate_fields(context)`. Each leaf
passes itself and its tree location to the supplied `QueryValidationContext`,
while `AllOf` and `AnyOf` recursively collect their children's issues. The context shares captured
catalogues and common field checks; it does not accumulate issues or perform
API reads. Validation uses `validate_fields()` to distinguish metadata checks
from Pydantic's structure-validation methods.
Each catalogue declares its field `kind` (`"property"` or `"classification"`).
The context builds a read-only index by kind, then resolves each predicate's
`field_id` through the selected catalogue's shared `get_field(UUID)` method.
Duplicate catalogue kinds raise `ValueError` as ambiguous configuration.
An absent catalogue produces normal `unknown_field` issues for its references.
Leaves pass `FieldCheck(predicate=self, location=location)` to the shared check.
The `FieldPredicate` protocol supplies `kind`, `field_id` and the typed `test`,
without making predicates depend on catalogue classes.
Missing references and tests on known fields are handled separately.

Predicates can also be checked directly, optionally supplying a location prefix
when validating a subtree:

```python
from multiconn_archicad.utilities.queries import QueryValidationContext

context = QueryValidationContext([catalogue])
issues = query.where.validate_fields(context)  # Tuple of issues rooted at "where".
```

Every branch of `all` and `any` is checked. A valid earlier sibling does
not skip later branches. Negative operators do not hide context errors. Repeated
property references keep separate issues at their respective query locations.
Issue order follows the query's source order, descending through each nested group.

| Issue code | Meaning | Location |
| --- | --- | --- |
| `unknown_field` | The GUID is absent from the supplied catalogue | The leaf's `field_id` |
| `unsupported_field` | The property has no supported test family | The leaf's `test` |
| `invalid_test` | Wrong family or a metadata-dependent operand restriction failed | The leaf's `test` |

Each immutable `QueryValidationIssue` exposes:

- `location`: a tuple of keys and indices, such as `("where", "items", 1, "test")`.
- `path`: the derived readable form, such as `where.items[1].test`.
- `code`, `message`, and `reference` (for example,
  `{"kind": "property", "field_id": "..."}`).
- `name`, `group`, and derived `qualified_name`, or `None` when the property is unknown.

`QueryValidationResult.issues` is an immutable tuple, and `is_valid` is true when it
is empty. `result.describe()` returns JSON-friendly `is_valid` and `issues`; each
issue includes its structured location, readable path, field reference, and names.
This is diagnostic output, not an alternative query representation.

`raise_for_errors()` returns normally for valid queries and raises
`QueryValidationError` otherwise. The exception's `.result` retains every issue.
`InvalidFieldTestError` becomes an `invalid_test` issue, and
`UnsupportedFieldTypeError` becomes an `unsupported_field` issue. Property and
classification errors derive from the relevant shared base error. Other
exceptions, including plain `ValueError` and ambiguous registry configuration,
propagate automatically instead of becoming user-query issues.

Pydantic `ValidationError` still reports malformed query structure during parsing,
before context validation. Element-type choices are checked there and require no
property lookup. Per-element missing/unreadable value outcomes belong to
evaluation, not these metadata-validation issues.

The [offline discovery example](../../examples/element_query_discovery.py) now also
demonstrates a valid query and an unsupported property inside `any`, without a
running Archicad instance.

## Evaluating a query with supplied data

Each predicate owns `prepare(builder)` and
`evaluate(context, element_id) -> BatchSlot[bool]`. Groups recursively call their
children in both passes. Preparation collects source requirements; building the
context performs their batched reads. One context then supplies completed data
for every element in the execution. For real project data, validate the query
against its catalogue first.

```python
from uuid import UUID
from unittest.mock import MagicMock

from multiconn_archicad.models.tapir.types import ElementType
from multiconn_archicad.utilities import BatchGrid, BatchRow, BatchSlot
from multiconn_archicad.utilities.queries import (
    AllOf, AnyOf, ContextBuilder, ElementTypePredicate,
    NumberOperator, NumberTest, PropertyPredicate, Query, TextOperator, TextTest,
)

height_id = UUID("22222222-2222-4222-8222-222222222222")
description_id = UUID("11111111-1111-4111-8111-111111111111")
query = Query(where=AllOf(items=(
    ElementTypePredicate(types=(ElementType.WALL,)),
    AnyOf(items=(
        PropertyPredicate(
            field_id=height_id,
            test=NumberTest(operator=NumberOperator.GREATER_THAN, value=3),
        ),
        PropertyPredicate(
            field_id=description_id,
            test=TextTest(operator=TextOperator.STARTS_WITH, value="External"),
        ),
    )),
)))
# Supply fake read responses here; ContextBuilder uses the same source commands
# with a real UnifiedApi when connected to Archicad.
from multiconn_archicad.models.tapir.types import ElementId, ElementIdArrayItem

element_id = UUID(int=1)
candidates = [ElementIdArrayItem(elementId=ElementId(guid=element_id))]
api = MagicMock()
api.utilities.property.get_property_values_per_element_result.return_value = BatchGrid(
    rows=(BatchRow((BatchSlot.success("2.5"), BatchSlot.success("EXTERNAL wall"))),),
    width=2,
)
api.tapir.element.filter_elements.return_value = candidates

builder = ContextBuilder()
query.where.prepare(builder)
context = builder.build(api, candidates)
decision = query.where.evaluate(context, element_id)
assert decision.is_success
assert decision.value is True
```

This short wall matches because its description satisfies the OR branch. Type
predicates remain active at every level; the same values on a slab would fail.
Undefined/unavailable property slots contribute successful false values, so other
branches of `any` can still match.

`context.data(PROPERTY_VALUES)` maps property GUIDs to `ColumnData[str]`
column views. Each view retains the same `BatchGrid` and shared element-to-row
index; `.value(element_id)` returns the original slot. No per-element property
dictionary or context is created during evaluation.

`context.data(TYPE_MEMBERSHIP)` maps type frozensets to matching element-GUID
frozensets from `FilterElements`. A type predicate checks whether its element GUID
belongs to that set. Type-only/property-only queries request only the data they
use. Missing sources, keys, or element rows raise `KeyError`; skipped property
slots are rejected too. These indicate incomplete execution input, not property
unavailability.

The source objects are typed keys shared by preparation and evaluation. A
`ContextSource[Key, Value]` implements
`load(api, elements, keys) -> Mapping[Key, Value]`. Property predicates request
`builder.require(PROPERTY_VALUES, property_id)`; type predicates request
`builder.require(TYPE_MEMBERSHIP, frozenset(types))`. The builder deduplicates
keys in first-request order and invokes each source once. New predicates can
reuse a source or introduce another source class without editing the builder or
context. `builder.provide(source, key, value)` seeds already completed data so
the source only loads missing keys. Empty populations make no source reads.

Internally the context stores `Mapping[object, object]`, and the builder stores
requests of different source types in one dictionary. Two explicit casts in
`queries/context.py` recover a source's request type and payload type. Both rely
on storing and retrieving under the same source object. The generic methods
check source-specific key and value types at call sites, including seeded values;
there are no runtime type conversions. Direct construction of a context from a
raw dictionary bypasses this typed builder boundary.

Groups evaluate every child before aggregating. Real read/conversion errors are
retained even when a sibling would settle the Boolean result. Error messages
include paths such as `where.items[1].items[0].test` and property GUIDs. Aggregate
`causes` retain the original errors beneath the contextual wrappers. An optional
`path=` keyword changes the diagnostic root label; it is not part of query JSON.
Unexpected evaluator exceptions propagate.

The [offline predicate example](../../examples/element_query_predicates.py) builds
one context for four elements using fake reads. It shows nested groups, excluded
element types, undefined values inside OR, and a numeric conversion failure with
its query path. It requires no Archicad connection.

## Execution and result contract

The bound element utility validates queries, retrieves candidate/value data in
batches, and evaluates the original tree. Calls are read-only and do not change
selection. Supply a parsed `Query`; use `Query.model_validate()` or
`Query.model_validate_json()` at dictionary/JSON boundaries.

The execution flow is:

1. Check the schema version and validate against fresh field metadata if needed.
2. List search candidates within the requested scope, or normalize supplied IDs.
3. Deduplicate candidates, retaining the first occurrence and its order.
4. Narrow the working population using the safe element-type bound (`None` means
   unrestricted; an empty set means nothing can match).
5. Let predicates collect source requirements and load one shared context.
6. Evaluate the original tree for each eligible element; narrowed-out candidates
   retain `FILTERED` outcomes in their original positions.
7. Return matching IDs, an aligned diagnostic search snapshot, or filter slots
   projected back onto the supplied order and duplicates.

- Each ordinary property operation checks availability before comparison.
  Confirmed unavailability is false, including for `is not` and `does not contain`.
  It is not an inverted successful comparison or an unknown logical value.
- `all` and `any` combine successful Boolean answers normally. A false leaf need
  not exclude an element if another branch of `any` matches.
- Undefined values produce false in ordinary query comparisons, just like
  unavailability. The property-read layer keeps `PropertyUndefinedError` distinct
  from `PropertyUnavailableError`, preserving the information needed for future
  state operators. All six special state operations remain deferred.
- Command failures and invalid-query failures raise. Property GUIDs are validated
  against a fresh Tapir catalogue before execution. References absent from that
  catalogue are invalid queries. There is no additional property-existence scan
  after reading values; subsequent per-element read errors follow the ordinary
  search/filter policy.
- Other encountered per-element read/evaluation failures remain errors rather than
  Boolean false. A decisive sibling does not suppress an encountered error.
  Evaluation may skip unnecessary reads; diagnostics cover work actually done.

| A | B | `all(A, B)` | `any(A, B)` |
| --- | --- | --- | --- |
| true | true | true | true |
| true | false | false | true |
| false | true | false | true |
| false | false | false | false |

The primary entry point searches Archicad directly:

```python
matches = api.utilities.element.find_elements(query)
diagnostic = api.utilities.element.find_elements_result(query)

# Optional filtering of an existing population:
result = api.utilities.element.filter_elements_by_query_result(elements, query)
matches = api.utilities.element.filter_elements_by_query(elements, query)
```

`find_elements()` retrieves its own candidates and returns only elements with a
final true evaluation. It delegates to `find_elements_result()` and returns
`result.outcomes.successes`, omitting non-matches and ordinary per-element errors
without calling `raise_for_errors()`. Fatal failures still raise from both search
methods: invalid queries (including unsupported versions or absent property
references), transport or whole-command failures, and failed prerequisite listings.

For diagnostics, the public `FindElementsResult` retains both candidate identities
and aligned outcomes:

```python
from multiconn_archicad.utilities import FindElementsResult

result: FindElementsResult = api.utilities.element.find_elements_result(query)
matches = result.outcomes.successes

for index, slot in enumerate(result.outcomes.slots):
    if slot.is_error:
        candidate = result.candidates[index]
        print(candidate.elementId.guid, slot.error.message)
```

`candidates` is a tuple of unique IDs in first-listing order, captured after the
search's listing scope/type choices and before subsequent type narrowing.
`outcomes` is a `BatchResult[ElementIdArrayItem]` with one slot per candidate:
`SUCCESS` contains the matching candidate, `FILTERED` marks a non-match, and
`ERROR` retains its diagnostic. Narrowed-out candidates remain in the snapshot as
`FILTERED`. The constructor normalizes candidates to a tuple and rejects unequal
candidate/outcome lengths.

An empty candidate tuple means listing found no candidates. Nonempty candidates
with errors and no successes distinguish a failed evaluation from an ordinary
empty search. Diagnostics only describe this captured population: they do not
represent every project element or errors that upstream commands did not expose.
The two-field shape can support a future generic handle adapter that pages by
original index; no MCP handle system is implemented here.

Both search methods accept the same `query`, `databases`, and `filters` arguments,
with typed database wrappers and `ElementFilter` members used by Tapir listing commands.
For example:

```python
from multiconn_archicad.models.tapir.types import ElementFilter

matches = api.utilities.element.find_elements(
    query,
    filters=(ElementFilter.IS_VISIBLE_BY_LAYER,),
)
```

Search derives safe type bounds from the existing query: type predicates supply
sets, AND intersects bounds, and OR unions them. Property predicates provide no
type restriction. An unrestricted OR branch requires unrestricted listing.
Use `GetElementsByType` for finite bounds, `GetAllElements` for unrestricted
bounds, and no listing for an empty bound. Validate the entire query first.

Keep every type predicate in the original tree. For example,
`(Wall AND ID starts W) OR (Slab AND ID starts S)` can retrieve only walls/slabs,
but a slab named `W-01` must still fail. No stripping or second query tree is
needed. Search returns unique GUIDs in deterministic listing order. Databases,
visibility filters, and subelement inclusion are explicit listing options; the
default follows Tapir's current database rather than implying every database.
Type calls follow `ElementType` declaration order; each response keeps its upstream
order. Shared execution deduplicates GUIDs by first occurrence, once for reads
and evaluation. This is necessary because section elements can map to the same
owner and multiple databases can return that owner. Every listing/database
failure raises, even if other databases returned elements.

The supplied-population filter preserves input order and duplicate candidates,
with one result slot per position. Repeated reads may be deduplicated internally
without changing that alignment. Empty candidates produce an empty result after
query validation, without element-value reads.

Queries with properties discover one fresh metadata catalogue before listing or
evaluation, including when the candidate set is empty. Classification predicates
similarly discover their metadata catalogue; type-only queries need neither.
Predicates prepare requirements before validation. The same builder then carries
validated classification fields into execution. Each execution reads distinct
property GUIDs in one property-value batch and distinct classification systems in
one assignment batch. A finite overall type bound narrows candidates with
`FilterElements` before value reads, and its completed membership is provided to
the builder. The type source loads only missing membership sets. This preserves nested OR semantics without
reading full element details or carrying known types from listing. Property-only
and classification-only queries make no type-filter calls. Tapir preserves input order in these filtered
subsets. Whole-command errors raise in core; a header unreadable by
`FilterElements` is omitted from its matching subset. Execution relies on the
upstream response alignment contract rather than adding speculative shape
checks. Nothing is cached between executions.

Use the existing `BatchResult[ElementIdArrayItem]` contract:

| Final element outcome | Batch slot |
| --- | --- |
| Match | `SUCCESS`, containing the element ID |
| Definite non-match | `FILTERED` |
| Per-element read/evaluation failure | `ERROR`, retaining its diagnostic |

The diagnostic search wraps these slots together with its captured candidate
sequence. The supplied-population filter exposes the `BatchResult` directly;
its plain-list companion calls `raise_for_errors()` before returning matches.
The concise search returns successful matches while omitting per-element errors.
No new batch state or three-valued Boolean layer is introduced.

Context validation failures raise `QueryValidationError` with all query issues.
The fresh Tapir catalogue covers properties that the official property-details
command cannot describe, so execution does not add that official lookup.
Per-element errors retain query paths, GUIDs, and causes in diagnostic search
and filtering; concise search omits them, and the strict filter raises
`BatchOperationError` containing that result.

The [offline execution example](../../examples/element_query_execution.py) uses
`UnifiedApi` with a fake command transport, including normal generated-client
validation. It demonstrates concise/diagnostic search, aligned filtering with duplicate IDs, and
strict-filter failure without contacting Archicad.

Stage 8 adapts supplied successful property values: numeric values use
`float(api_value)` directly, treating the returned value as authoritative. The SI
assumption remains in place. No additional precision handling, unit conversion,
or localized-number parser is required; failed conversions remain errors.

## JSON Schema

```python
schema = Query.model_json_schema()
```

The schema contains the recursive predicate discriminators, typed operator enums,
operand shapes, UUID format, and collection-size constraints. This describes query
syntax; project metadata and per-element read availability remain separate checks.
Numeric finiteness is also
enforced by Pydantic at runtime; consumers must validate submitted queries rather
than relying on JSON Schema alone.

See the [staged implementation plan](../../docs/ELEMENT_QUERY_IMPLEMENTATION_PLAN.md)
for family behavior, property discovery, context validation, and execution.
