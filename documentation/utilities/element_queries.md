# Element query definitions

Stages 1-7 provide query models, JSON serialization, JSON Schema, test-family
behavior, uniform field information, batch property discovery, and query-wide
context validation, with an agreed evaluation contract. The catalogue and validator can use supplied metadata offline.
The bound property utility can fetch a fresh metadata batch from Archicad. Query
execution is not yet implemented.

Import the public models from `multiconn_archicad.utilities.queries`.

## Stage 7 behavior decisions

The query contract follows Archicad Find and Select: normal AND/OR, negative operators
on individual tests, case-insensitive text with significant whitespace, and
ordinary numeric comparisons without added tolerance or display rounding.
Unavailable properties make every operation false except `not available`.
All six common user-defined-property state operations are deferred.

These are agreed target semantics, not implemented evaluation behavior. General
`Negate` / `"not"` predicates have been removed; JSON using `"kind": "not"` is
rejected at any depth. No query executor exists yet. The complete record of
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
    NumberTest,
    PropertyPredicate,
    Query,
    TextTest,
)

query = Query(
    where=AllOf(
        items=(
            ElementTypePredicate(types=("Wall",)),
            PropertyPredicate(
                property_id=UUID("22222222-2222-4222-8222-222222222222"),
                test=NumberTest(operator="is greater than", value=3),
            ),
            PropertyPredicate(
                property_id=UUID("11111111-1111-4111-8111-111111111111"),
                test=TextTest(operator="starts with", value="External"),
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
        "property_id": "22222222-2222-4222-8222-222222222222",
        "test": {
          "kind": "number",
          "operator": "is greater than",
          "value": 3.0
        }
      },
      {
        "kind": "property",
        "property_id": "11111111-1111-4111-8111-111111111111",
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
                property_id="11111111-1111-4111-8111-111111111111",
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
- The envelope defaults to `schema_version: "1.0"`. This is a plain string for now:
  the intended convention is major/minor, with breaking changes incrementing the
  first number and backwards-compatible changes incrementing the second. Version
  parsing and compatibility enforcement are deferred.
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

Each family implements `validate_for()` explicitly. Text and numeric tests reuse
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
| `operators()` | Return the operator Literal's choices as an immutable tuple |
| `accepts(details)` | Declare metadata compatibility for discovery and validation |
| `validate_for(details)` | Explicitly validate the selected test against property metadata |
| `schema_for(details)` | Describe a compatible test, with metadata-specific choices when needed |

`schema_for()` first checks compatibility and then returns JSON Schema. A family
can override it to enrich available values from metadata. Measure information
stays in `PropertyDetails`; selecting the numeric family does not discard it.

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

The default union contains `TextTest` and `NumberTest`. Boolean properties,
enumerations, and lists remain unsupported for now.

### Adding a family

Implement a concrete `PropertyTestModel` subclass and include it in the declared
`PropertyTest` union in `models.py`. For example, a future boolean family would
declare:

```python
from typing import Literal

from pydantic import Field

from multiconn_archicad.models.tapir.types import (
    PropertyCollectionType,
    PropertyDetails,
    PropertyValueType,
)
from multiconn_archicad.utilities.queries import PropertyTestModel


class BooleanTest(PropertyTestModel):
    kind: Literal["boolean"] = "boolean"
    operator: Literal["is", "is not"]
    value: bool = Field(strict=True)

    @classmethod
    def accepts(cls, details: PropertyDetails) -> bool:
        return (
            details.propertyCollectionType == PropertyCollectionType.SINGLE
            and details.propertyValueType == PropertyValueType.BOOLEAN
        )

    def validate_for(self, details: PropertyDetails) -> None:
        self._require_compatible_property(details)
```

The shared declaration would then become:

```python
PropertyTest = Annotated[
    TextTest | NumberTest | BooleanTest,
    Field(discriminator="kind"),
]
```

After that source change, query parsing, schema generation, and a newly created
registry all use the extended union. No generic dispatch changes are necessary.
This is static schema extension, not runtime mutation of an existing query model.
The tests demonstrate the third family using a separate union and Pydantic
`TypeAdapter`; the default query schema does not yet include boolean tests.

## Uniform field information

`FieldInfo` defines the shared interface for field sources. `PropertyInfo` is its
first implementation, using supplied `PropertyDetails` and a registry. It performs
no API calls. Using `details` from the offline example above:

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

Future field sources can implement `FieldInfo` with different reference formats
and test models, while sharing `qualified_name` and discovery serialization.
For classification fields, the planned labels remain `group = Classifications`
and `name = classification system name`; classification behavior is not yet
implemented. Query-wide validation uses the supplied catalogue as described below.

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
non-match. Boolean, enum, and list properties currently follow this policy.

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
result = validate_query(query, catalogue)

if not result.is_valid:
    for issue in result.issues:
        print(issue.path, issue.code, issue.qualified_name, issue.message)

# Optional exception-based handling retains the complete result.
result.raise_for_errors()
```

`validate_query()` only uses the supplied query and metadata snapshot. It does not
fetch metadata, read element values, evaluate boolean expressions, or build a
second query tree. Success means the query is compatible with that snapshot; it
does not verify the currently open project or imply that execution is implemented.
The plain version string is not interpreted by context validation.

Every branch of `all` and `any` is checked. A valid earlier sibling does
not skip later branches. Negative operators do not hide context errors. Repeated
property references keep separate issues at their respective query locations.
Issue order follows the query's source order, descending through each nested group.

| Issue code | Meaning | Location |
| --- | --- | --- |
| `unknown_property` | The GUID is absent from the supplied catalogue | The leaf's `property_id` |
| `unsupported_property` | The property has no supported test family | The leaf's `test` |
| `invalid_test` | Wrong family or a metadata-dependent operand restriction failed | The leaf's `test` |

Each immutable `QueryValidationIssue` exposes:

- `location`: a tuple of keys and indices, such as `("where", "items", 1, "test")`.
- `path`: the derived readable form, such as `where.items[1].test`.
- `code`, `message`, and `property_id`.
- `name`, `group`, and derived `qualified_name`, or `None` when the property is unknown.

`QueryValidationResult.issues` is an immutable tuple, and `is_valid` is true when it
is empty. `result.describe()` returns JSON-friendly `is_valid` and `issues`; each
issue includes its structured location, readable path, field reference, and names.
This is diagnostic output, not an alternative query representation.

`raise_for_errors()` returns normally for valid queries and raises
`QueryValidationError` otherwise. The exception's `.result` retains every issue.
`InvalidPropertyTestError` becomes an `invalid_test` issue, and
`UnsupportedPropertyTypeError` becomes an `unsupported_property` issue. Other
exceptions, including plain `ValueError` and ambiguous registry configuration,
propagate automatically instead of becoming user-query issues.

Pydantic `ValidationError` still reports malformed query structure during parsing,
before context validation. Element-type choices are checked there and require no
property lookup. Per-element missing/unreadable value outcomes belong to later
evaluation semantics, not these metadata-validation issues.

The [offline discovery example](../../examples/element_query_discovery.py) now also
demonstrates a valid query and an unsupported property inside `any`, without a
running Archicad instance.

## Evaluation and result contract

This section specifies the next execution stages; it does not introduce an
executor or a second query representation. Execution will use the original tree.

- Each ordinary property operation checks availability before comparison.
  Confirmed unavailability is false, including for `is not` and `does not contain`.
  It is not an inverted successful comparison or an unknown logical value.
- `all` and `any` combine successful Boolean answers normally. A false leaf need
  not exclude an element if another branch of `any` matches.
- Undefined values remain explicit `PropertyUndefinedError` failures for now;
  they are not unavailable values or ordinary strings after property adaptation.
  The six special user-defined-property state operations remain deferred.
- Command failures and invalid-query failures raise. A missing/invalid property
  GUID discovered during execution is fatal; an older catalogue is a possible
  cause. Existing general-purpose property `_result` readers retain that API
  error; it is the query executor that will enforce this query-level rule.
- Other encountered per-element read/evaluation failures remain errors rather than
  Boolean false. A decisive sibling does not suppress an encountered error.
  Evaluation may skip unnecessary reads; diagnostics cover work actually done.

| A | B | `all(A, B)` | `any(A, B)` |
| --- | --- | --- | --- |
| true | true | true | true |
| true | false | false | true |
| false | true | false | true |
| false | false | false | false |

The initial executor will filter an explicit ordered sequence of candidate IDs.
Candidate retrieval is a separate operation: databases, current selection,
visibility, and inclusion of subelements are not silently chosen by the query.
Preserve input order and duplicate candidates, with one result slot per position.
Repeated reads may be deduplicated internally without changing that alignment.
An empty candidate sequence produces an empty result after query validation,
without element-value reads.

Use the existing `BatchResult[ElementIdArrayItem]` contract:

| Final element outcome | Batch slot |
| --- | --- |
| Match | `SUCCESS`, containing the element ID |
| Definite non-match | `FILTERED` |
| Per-element read/evaluation failure | `ERROR`, retaining its diagnostic |

A future `_result` method will retain the aligned result. Its plain-list companion
will call `raise_for_errors()` before returning successful matching IDs, following
existing element utilities. No new batch state, query-specific result container,
or three-valued Boolean layer is required.

Reliable numeric retrieval is still stage 8 work: Tapir display strings do not
guarantee raw database precision or SI values. This contract does not authorize
parsing localized display text to invent typed values.

## JSON Schema

```python
schema = Query.model_json_schema()
```

The schema contains the recursive predicate discriminators, typed operator enums,
operand shapes, UUID format, and collection-size constraints. Schema publication
does not advertise an executable query capability yet. Numeric finiteness is also
enforced by Pydantic at runtime; consumers must validate submitted queries rather
than relying on JSON Schema alone.

See the [staged implementation plan](../../docs/ELEMENT_QUERY_IMPLEMENTATION_PLAN.md)
for family behavior, property discovery, context validation, and execution.
