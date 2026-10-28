# Element query definitions

Stages 1-4 provide query models, JSON serialization, JSON Schema, explicit
test-family behavior, family dispatch, and uniform field information against
supplied property metadata.
They do not connect to Archicad, discover fields, resolve query references, or
execute queries. Parsing checks structure; property-context validation is a
separate call.

Import the public models from `multiconn_archicad.utilities.queries`.

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

`AllOf`, `AnyOf`, and `Negate` can contain any predicate, including another group:

```python
from multiconn_archicad.utilities.queries import AnyOf, ElementTypePredicate, Negate, Query

query = Query(
    where=Negate(
        item=AnyOf(
            items=(
                ElementTypePredicate(types=("Door",)),
                ElementTypePredicate(types=("Window",)),
            )
        )
    )
)
```

This describes elements that are neither doors nor windows. Evaluation, including
the behavior of negation on unreadable values, belongs to a later stage.

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
Their spellings are part of the serialized contract. Case sensitivity and numeric
comparison tolerances will be defined with the evaluator.

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
wrong_test.validate_for(details)  # Raises ValueError: incompatible property type.
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
| `operators()` | The selected family's readable operator strings |
| `create_test(**data)` | Structure validation followed by property-context validation |
| `validate(test)` | Check an existing test's family and property-context rules |
| `test_schema()` | Metadata-aware schema for the supported test |
| `describe()` | JSON-friendly reference, names, operators, and test schema |

The runtime `PropertyInfo` also exposes its selected `test_model` and a copy of
its `details` snapshot. Measure metadata remains available in those details even
though all scalar quantities share `NumberTest`.

`describe()` returns a separate discovery description, not a serialized Python
object or an executable query. Its `reference` can be combined with a test to
construct the existing property-predicate shape; query JSON is unchanged. Clients
can use the direct `operators` list without navigating the schema.

Names are display labels, not identities. Two properties with identical labels
remain distinct by GUID. Technical names and underscores are not split or
rewritten. Metadata is deep-copied at construction, and `details` returns a copy,
so external edits do not invalidate the selected family. Create a new
`PropertyInfo` to refresh the snapshot.

Unsupported and ambiguous metadata retain the registry's distinct errors.
`create_test()` raises Pydantic `ValidationError` for malformed test structure;
`validate()` rejects a mismatched family with `ValueError` and delegates further
rules to the family's explicit `validate_for()` method.

Future field sources can implement `FieldInfo` with different reference formats
and test models, while sharing `qualified_name` and discovery serialization.
For classification fields, the planned labels remain `group = Classifications`
and `name = classification system name`; classification behavior is not yet
implemented. Batch discovery and query-wide validation remain later stages.

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
