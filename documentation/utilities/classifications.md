# Classification utilities

`api.utilities.classification` discovers classification systems and their item
trees and reads element assignments. Metadata uses the official commands; value
reads use Tapir, which supports hierarchical subelements.

Classification support uses the same query modules and abstractions as properties:

- `models.py`: `ClassificationTest` shares immutable configuration and operator
  discovery through `TestModel`, also used by property test families.
- `fields.py`: `ClassificationInfo` and its immutable item records. `FieldInfo`
  implements test construction, operator discovery and default schema generation;
  concrete descriptors supply metadata validation and operand choices.
- `discovery.py`: `ClassificationCatalogue` and `PropertyCatalogue` extend
  `FieldCatalogue`, sharing ordered storage, duplicate checking, lookup, search,
  support filtering and descriptions. Each source normalizes its own identifiers.

The former `queries/classifications.py` module has been removed.

## Metadata and field discovery

```python
catalogue = api.utilities.classification.discover_query_fields()
# Or request only selected systems:
catalogue = api.utilities.classification.discover_query_fields([system_id])
field = catalogue[system_id]

print(field.group)           # Classifications
print(field.name)            # Name of the selected classification system
print(field.qualified_name)  # Classifications / system name
print(field.operators())

item = field.item(item_id)
print(item.code, item.name, item.parent_id, item.children)
branch = field.descendant_ids(item_id, include_self=True)
```

Discovery reads the system list once, then one complete tree per selected system.
Explicit selections preserve first-request order and load duplicate systems only
once. `None` selects all systems; `[]` returns an empty catalogue without API reads.
Missing selected systems are omitted from the catalogue. Query validation reports
references to them as `unknown_field` issues.

The returned catalogue is a disconnected snapshot. Item lookup, descendant
traversal, schema generation and search make no API calls. Re-run discovery to
refresh it. Systems are returned in API order and items in depth-first tree order.
Item GUIDs, codes and names remain separate: a classification item can have an
empty name and a useful code such as `Wall`.

`field.items` returns immutable item records. `field.details` returns a copy of
the upstream system metadata. Caller changes to API models, returned details or
JSON descriptions cannot change the snapshot.

```python
fields = catalogue.search("archicad", group="Classifications")
description = catalogue.describe()  # JSON-friendly metadata, choices and trees
assert catalogue.search("", supported_only=True) == catalogue.supported
```

Field descriptors also support test construction and reference validation:

```python
test = field.create_test(operator="is in branch of", value=item_id)
field.validate(test)
schema = field.test_schema()
```

`ClassificationTest` has `kind="classification"` and a readable
`ClassificationOperator`. Operand rules are validated at construction and
represented in JSON Schema:

| Operator | Operand | Unclassified element |
| --- | --- | --- |
| `is` | Item UUID | false |
| `is not` | Item UUID | true |
| `has value` | No `value` field | false |
| `has no value` | No `value` field | true |
| `is in branch of` | Item UUID | false |
| `is not in branch of` | Item UUID | true |
| `is direct child of` | Item UUID | false |
| `is not direct child of` | Item UUID | true |

Branch membership includes the selected item itself and all descendants. Direct
child matching includes only immediate children, excluding the selected item.
These rules were confirmed by the user against Archicad on 2026-11-01.

Presence tests omit `value` entirely; supplying even `null` is rejected. Other
operators require a UUID. Serialization omits the absent operand, so presence
tests round-trip through JSON. The field schema adds available item choices using
`oneOf` entries with UUID constants and code/name titles. Unknown operators,
extra fields and malformed UUIDs fail Pydantic validation. A UUID outside the
selected system raises `InvalidClassificationTestError`. Empty systems still
support presence tests, but have no valid item operands.

## Query execution and validation

```python
from multiconn_archicad.utilities.queries import (
    ClassificationPredicate, ClassificationTest, Query,
)

query = Query(where=ClassificationPredicate(
    field_id=system_id,
    test=ClassificationTest(operator="is in branch of", value=item_id),
))
matches = api.utilities.element.find_elements(query)
diagnostics = api.utilities.element.find_elements_result(query)
```

The same predicate works inside `AllOf`/`AnyOf` and with supplied-population
filtering. It imposes no element-type bound. Search listing and database/filter
scope follow the existing element-query APIs, including subelements.

The equivalent presence-test JSON is:

```json
{
  "schema_version": "1.0",
  "where": {
    "kind": "classification",
    "field_id": "632c30e5-2b82-4a75-bfad-d52febce9a4a",
    "test": {"kind": "classification", "operator": "has no value"}
  }
}
```

Replace identifiers with those discovered in the target project. Offline
validation uses the predicate methods and shared diagnostics:

```python
from multiconn_archicad.utilities.queries import validate_query

validate_query(query, [catalogue]).raise_for_errors()
# Mixed queries: validate_query(query, [property_catalogue, catalogue])
```

Bound search/filter calls discover required metadata families and validate every
branch before candidate listing or empty/impossible-population returns. Missing
systems produce `unknown_field`; missing item operands produce `invalid_test`.
Command/discovery failures raise. Each execution discovers trees only for the
classification systems referenced by the query.

The prepared ContextBuilder retains this metadata for execution through
`CLASSIFICATION_FIELDS`, avoiding a second discovery. `CLASSIFICATION_VALUES`
reads all distinct requested system GUIDs in one assignment batch. Both property
and classification reads use typed `ColumnData[T]` views over their original
grids. Repeated predicates for one system share the same assignment column.

Read errors retain their causes and predicate path/system GUID, even alongside
a decisive Boolean sibling. They do not become unclassified values. Search's
concise method omits per-element errors; diagnostic search and filter results
retain them, and strict filtering raises. This differs from property unavailable
conditions: a successfully unclassified assignment matches negative classification
comparisons, whereas an unavailable property comparison remains false.

See the [offline classification example](../../examples/element_query_classifications.py).

## Aligned assignment reads

```python
result = api.utilities.classification.get_classifications_per_element_result(
    elements,
    [system_a, system_b],
)

for row in result.rows:
    for slot in row:
        if slot.is_error:
            print(slot.error.code, slot.error.message)
        else:
            print(slot.value)  # Assigned item UUID, or None for unclassified
```

One Tapir command reads the complete element-by-system grid. Rows align with
elements and columns with systems; order and duplicates are preserved on both
axes. Successful all-zero or omitted item identifiers become successful `None`
values. They are not errors or filtered slots. Actual cell failures remain
`BatchError` values; whole-row errors retain their cause and fill that row.
Whole-command and transport failures raise.

For callers requiring a complete value matrix, the strict method delegates to
the diagnostic method and raises `BatchOperationError` for row/cell errors:

```python
values = api.utilities.classification.get_classifications_per_element(
    elements, [system_a, system_b],
)
# Example: [[wall_item_id, None], [None, another_item_id]]
```

Both methods require at least one system. Empty element input returns an empty
grid/value list without making an assignment request. Reads do not implicitly
discover systems or fetch item trees.

Element identifiers accept the existing `ElementIdLike` inputs. System and item
lookups accept UUIDs, UUID strings and the corresponding official/Tapir ID or
ID-array-item models, through the new classification identifier normalizers.

## Classification response schema correction

Tapir 1.7.3 returns each successful `classificationIds` entry directly as
`classificationSystemId` / `classificationItemId`. Its released documentation
schema incorrectly references a `classificationId` wrapper. A local schema patch
corrects that reference, and the Pydantic/TypedDict models are regenerated from
it. The utility uses the normal typed client; it does not parse raw HTTP responses
or accept a second response shape.
