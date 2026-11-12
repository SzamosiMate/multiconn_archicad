# Element query reference

This page describes the current engine contract. Start with the
[practical guide](element_queries.md) for complete script examples, or
[query editing](element_query_editing.md) for discovery and editor integration.
Future work lives in the [development plan](../development/element_queries_plan.md).

## Query structure

Import executable models from `multiconn_archicad.utilities.queries`.

| Model | Required data | Meaning |
| --- | --- | --- |
| `Query` | `where` | Versioned executable expression |
| `PropertyPredicate` | `field_id`, `test` | Property GUID and a compatible property test |
| `ClassificationPredicate` | `field_id`, `test` | Classification system GUID and classification test |
| `ElementTypePredicate` | `test` | Membership in the test's concrete type tuple |
| `AllOf` | Nonempty `items` | All children must match |
| `AnyOf` | Nonempty `items` | At least one child must match |

Each predicate and test has a `kind` discriminator. Python constructors supply
the default discriminator; JSON must contain it. Query/test models are frozen,
reject unknown fields, and validate on construction. Collections use tuples in
Python and arrays in JSON. Groups may nest. There is no general negation node;
negative comparisons are operators on individual test families.

```python
from multiconn_archicad.utilities.queries import ElementTypePredicate, ElementTypeTest, Query

query = Query(where=ElementTypePredicate(test=ElementTypeTest(types=("Wall", "Door"))))
assert query.schema_version == "1.0"
```

`ElementTypeTest` accepts valid individual types and combinations, including the
[five presets](element_queries.md#use-element-type-presets). The presets are
convenience values; a query stores concrete types and has no preset identifier.

## Comparisons and property conditions

| Test family | Operators | Operand |
| --- | --- | --- |
| `TextTest` | `is`, `is not`, `contains`, `does not contain`, `starts with`, `ends with` | String |
| `NumberTest` | `is`, `is not`, `is greater than`, `is greater than or equal to`, `is less than`, `is less than or equal to` | Finite number |
| `BooleanTest` | `is`, `is not` | Boolean |
| `ClassificationTest` | Equality, presence, branch, direct-child comparisons | Item UUID when required; see [classification operator table](classifications.md#metadata-and-field-discovery) |
| `ElementTypeTest` | Membership through `types` | Concrete element-type tuple |

Text comparisons use Unicode `casefold()`. Whitespace is significant. For
example, `External` equals `EXTERNAL`, but not ` External `. Serialization keeps
the original operand; it does not save the case-folded form.

Numeric operands accept finite integers/floats, excluding Booleans. Strings,
`null`, NaN, and infinity are rejected. Comparisons use ordinary numeric equality
and ordering without tolerance or rounding. The current value reader passes
Tapir's string to `float()`; it performs no locale parsing or unit conversion.
Consequently, `"3,00"` is an evaluation error. Metadata retains the measure type,
but that does not guarantee canonical numeric values. Canonical SI reads and the
angle operand contract are [deferred](../development/element_queries_plan.md#canonical-numeric-property-reads).

Boolean operands must be actual Booleans. Tapir value strings are interpreted
using its `"True"`/`"False"` representation.

Property discovery supports scalar single-string, integer/real, and Boolean
properties. Enumeration, GUID, and list-valued properties remain discoverable
as unsupported metadata, with an explanation. They cannot be executed using
these tests.

**Unavailable and undefined property values make every currently supported
property comparison false, including negative comparisons.** They do not mean
that `is not` matches. Other read/parse failures remain errors. Property-state
operators such as an availability test are not currently implemented.

A successfully unclassified assignment has different semantics: it matches
negative classification comparisons and `has no value`. An assignment read
error remains an error. Branch matching includes the chosen item; direct-child
matching excludes it. See [classification semantics](classifications.md).

## Validation

There are three distinct boundaries:

1. Model construction checks shape, discriminators, operators, and operands.
2. `validate_query()` checks references and test compatibility against supplied
   metadata snapshots. It makes no API calls.
3. Bound discovery/search/filter methods check the supported Tapir version;
   execution also checks query-schema compatibility and discovers current
   referenced fields before evaluating candidates.

```python
from multiconn_archicad.utilities.queries import validate_query

# This query references only built-in element-type metadata.
validation = validate_query(query, [])
assert validation.is_valid
validation.raise_for_errors()
```

For property/classification expressions, pass their catalogues or a
`QueryFieldCatalogue`. Validation visits all branches, even branches that cannot
match or inputs with no elements. Issue codes are `unknown_field`,
`unsupported_field`, and `invalid_test`. Each issue includes its expression
location, field reference, message, and available display metadata.
`raise_for_errors()` raises `QueryValidationError` with the validation result.

Duplicate property/system identities in a catalogue are invalid. Duplicate
display labels are allowed: labels are not identities. A compatible test model
alone does not prove an operand belongs to the chosen classification system.

## Search scope and candidate collection

`api.utilities.element.find_elements(query)` and `find_elements_result(query)`
share the same candidate listing and evaluation path. Query execution requires
Tapir **2.0.0 or newer**.

Default listing arguments are:

| Setting | Default |
| --- | --- |
| Databases | Main/floor-plan database, explicitly identified by GUID `d5d16dd4-093f-4674-895d-410d634d8c7e` |
| Filters | `IncludeSubElemObjects` and `IsIndependent` |

The default is independent of the active window. No additional visibility or
editability filter is added. Explicit structural component types can still be
queried: independence is not a general exclusion of every hierarchical child.

The existing keyword arguments `databases=` and `filters=` are advanced listing
overrides. `None` selects the respective default. A supplied sequence replaces
that default; it is not merged with it. Empty sequences are forwarded to Tapir,
so they should not be used as a synonym for a documented default. The supported
first-release query workflow is floor-plan search. Cross-database predicates,
provenance, and mixed-branch scope semantics remain deferred; see the
[database plan](../development/element_queries_plan.md#database-predicates-and-candidate-scope).

The engine derives a safe element-type upper bound from the expression. AND
intersects bounds; OR unions them, with an unrestricted alternative making the
bound unrestricted. A finite bound uses typed listing; an unrestricted bound
uses general listing. An impossible bound avoids listing after validation.
The original expression is always evaluated, preserving branch relationships.

Candidate GUIDs are deduplicated in first-listing order. Typed requests follow
the element enum's declaration order. Required property/system reads are
deduplicated and batched; repeated predicates share prepared columns.

`get_3d_elements()` is a separate convenience utility with a main-3D type
whitelist. It retains its existing current-database behavior. It uses both flags
on Tapir **1.5.3+**, and `IsIndependent` alone on older versions. Do not infer its
database scope or IFC-export eligibility from the query defaults.

## Results and failures

| Method on `api.utilities.element` | Return / error policy |
| --- | --- |
| `find_elements(query)` | Matching unique IDs; omits ordinary per-element errors |
| `find_elements_result(query)` | `FindElementsResult`: candidates plus aligned diagnostic outcomes |
| `filter_elements_by_query(elements, query)` | Matching supplied IDs; raises `BatchOperationError` if any element has an evaluation error |
| `filter_elements_by_query_result(elements, query)` | Aligned `BatchResult`, preserving per-element errors |

For diagnostic search, `len(result.candidates) == len(result.outcomes.slots)`.
For supplied filtering, outcomes align with the original sequence, including
duplicates. Successful slots hold matching element IDs; `FILTERED` slots are
non-matches; `ERROR` slots retain failures and their causes. Use `.successes`
for the matching values.

Supplied filtering does not collect a new population, apply the floor-plan
listing default, or change selection. Neither search method changes selection.

Invalid queries and query-wide failures raise from all methods. This includes
metadata discovery, transport, whole-command errors, and unsuccessful database
listings, even if another database succeeded. The core client already raises
whole-command Tapir errors; diagnostic outcomes represent element-level failures.

Groups evaluate child outcomes before aggregation. A decisive Boolean sibling
does not hide another child's error. An unavailable property is an ordinary
false result; a failed property read is not. Error details retain predicate
paths and field identities. At leaf level, successful `False` becomes a filtered
element only when the final result is translated to matching IDs.

## Serialization and compatibility

```python
from multiconn_archicad.utilities.queries import validate_query_version

payload = query.model_dump_json(indent=2)
loaded = Query.model_validate_json(payload, context={"require_schema_version": True})
validate_query_version(loaded.schema_version)
assert loaded == query
```

The current `QUERY_SCHEMA_VERSION` is `"1.0"`. Compatibility requires a valid
nonnegative `major.minor` string, the same major, and an equal or older minor.
Malformed versions raise `ValueError`; unsupported versions raise
`UnsupportedQueryVersionError`.

`require_schema_version` requires an explicit version when loading saved data;
it does not itself establish compatibility for an executable `Query`.
Execution checks compatibility before API reads, including for empty inputs.
Editable `QueryRows` checks compatibility when constructed or loaded as well.

Saved queries contain definitions, not metadata snapshots or results. GUIDs may
be invalid in another project or after project changes. Validate them against
fresh discovery before use. Executable queries and editable rows share the
library schema version; the row document is a separate shape for unfinished
input, described in [query editing](element_query_editing.md#editable-rows).
