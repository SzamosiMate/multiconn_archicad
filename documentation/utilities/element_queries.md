# Element queries

Use element queries to find matching Archicad elements or filter IDs you already
have. Start here for scripts. The [query reference](element_query_reference.md)
defines the detailed contracts; [query editing](element_query_editing.md) covers
field-driven editors and unfinished drafts.

## Requirements and current limits

- Install the query-capable version of `multiconn_archicad` in your environment
  and Tapir **2.0.0 or newer** in the target Archicad instance. Query discovery and
  execution check this requirement.
- The default search covers the **main/floor-plan database**, regardless of the
  active window. It covers all stories and adds no visibility/editability filter.
  This is the supported first-release search scope.
- Property tests currently support scalar text, integer/real numbers, and
  Boolean values. Classification and element-type predicates are also available.
- Numeric query reads request precise, locale-independent strings from Tapir.
  Quantity operands use **SI units, except angles use degrees**. Comparisons
  currently use exact floating-point equality/ordering without tolerance or
  rounding; canonical formatting does not remove arithmetic or unit-conversion
  roundoff. See the [numeric comparison contract](element_query_reference.md#comparisons-and-property-conditions).

Searches are read-only and do not change selection. Supplied-population filters
evaluate their input IDs without listing a new floor-plan population.

## Find elements

This complete example finds walls and doors in the default scope. It needs an
open Archicad project with the required Tapir version; it needs no property GUIDs.

```python
from multiconn_archicad import MultiConn
from multiconn_archicad.utilities.queries import (
    ElementTypePredicate,
    ElementTypeTest,
    Query,
)

connection = MultiConn()
header = connection.primary
if header is None:
    raise RuntimeError("Open an Archicad project with Tapir first.")
api = header.unified

query = Query(
    where=ElementTypePredicate(test=ElementTypeTest(types=("Wall", "Door")))
)
matches = api.utilities.element.find_elements(query)
print(f"Matches: {len(matches)}")
for element in matches:
    print(element.elementId.guid)
```

The following live examples continue with `api` from this setup. A query's type
tuple means membership in any listed type. `find_elements()` returns unique
matching IDs and omits ordinary per-element evaluation errors. Use
[diagnostic search](#inspect-failures) when an empty result needs explanation.

## Combine conditions

Use `AllOf` for AND and `AnyOf` for OR. Groups can be nested:

```python
from multiconn_archicad.utilities.queries import AllOf, AnyOf

query = Query(
    where=AllOf(
        items=(
            ElementTypePredicate(test=ElementTypeTest(types=("Wall", "Door", "Slab"))),
            AnyOf(
                items=(
                    ElementTypePredicate(test=ElementTypeTest(types=("Wall",))),
                    ElementTypePredicate(test=ElementTypeTest(types=("Door",))),
                )
            ),
        )
    )
)
matches = api.utilities.element.find_elements(query)  # Walls or doors; slabs fail.
```

Negative comparisons belong to individual tests, such as `is not` and
`does not contain`. Their behavior for unavailable properties is described in
the [comparison reference](element_query_reference.md#comparisons-and-property-conditions).

## Discover properties and classifications

Property labels are project-dependent. Discover the fields and retain their
GUIDs rather than treating a display name as an identifier:

```python
properties = api.utilities.property.discover_query_fields()
for field in properties.search("description", supported_only=True):
    print(field.property_id, field.qualified_name, field.operators())

classifications = api.utilities.classification.discover_query_fields()
for system in classifications:
    print(system.system_id, system.name)
    for item in system.items:
        print(" ", item.item_id, item.code, item.name)
```

Adapt the search text to your project/language. Different GUIDs can share the
same name. This example requires exactly one supported text match; if there are
several, select the intended field by a discovered GUID instead:

```python
from multiconn_archicad.utilities.queries import PropertyPredicate, TextTest

choices = [
    field for field in properties.search("description", supported_only=True)
    if field.test_model is TextTest
]
if len(choices) != 1:
    raise ValueError("Choose the intended text property by its discovered GUID.")
description = choices[0]

query = Query(
    where=AllOf(
        items=(
            ElementTypePredicate(test=ElementTypeTest(types=("Wall",))),
            PropertyPredicate(
                field_id=description.property_id,
                test=description.create_test(operator="starts with", value="External"),
            ),
        )
    )
)
matches = api.utilities.element.find_elements(query)
```

Classification predicates use the **system GUID** as `field_id` and an item GUID
as the operand when required. See [classification operators and examples](classifications.md#query-execution-and-validation).

## Use element-type presets

The presets are immutable type tuples usable directly in `ElementTypeTest`:

```python
from multiconn_archicad.utilities.queries import TYPES_3D_WITH_COMPONENTS

query = Query(
    where=ElementTypePredicate(test=ElementTypeTest(types=TYPES_3D_WITH_COMPONENTS))
)
matches = api.utilities.element.find_elements(query)
```

| Constant | Contents | Editor label |
| --- | --- | --- |
| `TYPES_ALL` | All 2D and 3D preset types, including components | All Types |
| `TYPES_3D` | Main model types used by `get_3d_elements()` | 3D Types |
| `TYPES_2D` | Drafting, annotations, markers, drawings, and individual cameras | 2D Types |
| `TYPES_3D_COMPONENTS` | Stair, railing, curtain-wall, beam, and column component types | 3D Component Types |
| `TYPES_3D_WITH_COMPONENTS` | Main types plus component types | 3D Types with Components |

The editor lists these groups first, followed by individual types. `All Types`
is the union of the 2D and 3D sets, including components; `Unknown`, `Group`,
`Hotlink`, and `CamSet` are outside all presets. Individual
`Camera` is in `TYPES_2D`. See the [constant definitions](../../src/multiconn_archicad/utilities/queries/element_types.py)
for complete membership. Presets save their concrete types, not a preset name.
Type membership is separate from independence filtering: explicit components
remain eligible under the default filters.

## Filter IDs you already have

```python
selected = api.tapir.element.get_selected_elements()
query = Query(where=ElementTypePredicate(test=ElementTypeTest(types=("Wall",))))
result = api.utilities.element.filter_elements_by_query_result(selected, query)
matching_selected = result.successes
```

Filter results preserve the supplied order and duplicate positions. The
plain-list companion, `filter_elements_by_query(selected, query)`, raises if any
element has an evaluation error. This differs from concise search, which omits
ordinary per-element errors. Neither filter method changes the selection.

## Inspect failures

```python
diagnostic = api.utilities.element.find_elements_result(query)
print("Candidates:", len(diagnostic.candidates))
print("Matches:", len(diagnostic.outcomes.successes))
for candidate, slot in zip(diagnostic.candidates, diagnostic.outcomes.slots):
    if slot.is_error:
        print(candidate.elementId.guid, slot.error.message)
```

`SUCCESS` contains a match, `FILTERED` means a non-match, and `ERROR` retains a
per-element failure. Invalid queries, failed listings, and whole-command or
transport errors raise from both search methods. An empty match list therefore
does not by itself establish that every candidate was successfully evaluated.
See [results and failures](element_query_reference.md#results-and-failures).

## Save and load queries

```python
saved_query = query.model_dump_json(indent=2)
restored = Query.model_validate_json(
    saved_query, context={"require_schema_version": True}
)
assert restored == query
```

Keep `schema_version` in saved data. Parsing checks structure and version
presence; execution checks compatibility and current project references.
Property and classification GUIDs are project-specific. Saving a query does not
save a metadata snapshot or its matches. See [serialization](element_query_reference.md#serialization-and-compatibility)
and [editable drafts](element_query_editing.md#editable-rows).

## Runnable offline examples

These examples use synthetic metadata or a fake transport and require no
Archicad instance. Run them from the repository environment, for example
`python examples/element_query_execution.py`.

| Example | Demonstrates |
| --- | --- |
| [Execution](../../examples/element_query_execution.py) | Concise/diagnostic search and strict/aligned filtering through the generated client |
| [Query schema](../../examples/element_query_schema.py) | Construction, JSON, and validation |
| [Fields](../../examples/element_query_fields.py) | Field descriptors and compatible tests |
| [Discovery](../../examples/element_query_discovery.py) | Catalogue lookup and unsupported metadata |
| [Classifications](../../examples/element_query_classifications.py) | Classification trees and assignments |
| [Editable rows](../../examples/element_query_rows.py) | Draft repair, persistence, and compilation |
| [Property evaluation](../../examples/element_query_evaluation.py) | Comparisons and property conditions |
| [Predicate evaluation](../../examples/element_query_predicates.py) | Nested groups and batched context data |

For implementation decisions and later additions, see the
[development plan](../development/element_queries_plan.md).
