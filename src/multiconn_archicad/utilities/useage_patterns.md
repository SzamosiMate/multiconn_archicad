# Batch Pipeline Usage Patterns & Cookbook

This guide shows how to combine `BatchResult`, `BatchGrid`, `RaggedBatchResult`, `BatchRow`, and the passive `PopulationResults` collection in failure-tolerant Archicad scripts.

## The Core Mental Model

Every pipeline records facts about an ordered population:

```python
from multiconn_archicad.utilities import PopulationResults

population = PopulationResults(self.elements)
```

The application executes each operation and decides whether to continue. The collection only stores result objects and their mapping to original items. When the application reaches its intended end, it asks for a completed snapshot:

```python
report = population.snapshot(completed=True)
```

If processing stops early, use `population.snapshot()` or `population.snapshot(completed=False)`. This marks otherwise-clean items `INCOMPLETE`; direct failures already recorded remain `FAILED`.

Every slot and item outcome has an explicit state:

| Slot / outcome | Meaning |
| :--- | :--- |
| `SUCCESS` / `SUCCEEDED` | Completed cleanly. |
| `ERROR` / `FAILED` | A direct failure was recorded. |
| `UPSTREAM_FAILED` | A prerequisite prevented execution. |
| `FILTERED` | Intentionally omitted by application logic. |
| `INCOMPLETE` | The caller says intended population processing did not reach its end. |

## Pattern 1: Paired Cell-Level Copy

Use projections to preserve an `N x M` shape while still writing readable cells:

```python
def run(self) -> ExecutionReport:
    population = PopulationResults(self.elements)
    self._validate_inputs()

    read = population.record(
        "Property read",
        self.property_utilities.get_property_values_per_element_result(
            self.elements, self.read_properties
        ),
    )
    payload = create_element_property_values_sparse(self.elements, self.write_properties, read)
    raw_write = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []
    population.record("Property write", read.project_successes(raw_write))

    return ExecutionReport(population.snapshot(completed=True))
```

Unread cells project to `UPSTREAM_FAILED`; readable cells retain their individual write results.

## Pattern 2: Dependent Multi-Read to Multi-Write

When every input property is required, aggregate each row before calculating:

```python
population = PopulationResults(elements)
read = population.record(
    "Read dimensions",
    property_utilities.get_property_values_per_element_result(elements, dimension_properties),
)
valid = read.aggregate_rows()

payload = []
for index, (length, width, height) in valid.iter_successes():
    payload.extend(build_payload(elements[index], length, width, height))

raw_write = api.tapir.property.set_property_values_of_elements(payload) if payload else []
population.record("Write area and volume", valid.project_rows(raw_write, row_length=2))
report = population.snapshot(completed=True)
```

A failed input row becomes an upstream-failed output row. The original read error remains attached as a direct failure for that item and therefore takes priority in the final outcome.

## Pattern 3: Conditional Subsets

Use `for_items` when domain objects are easiest to retain. Duplicate equal objects resolve FIFO, so repeated original items remain distinct:

```python
population = PopulationResults(elements)
read = population.record("Read", property_utilities.get_property_values_per_element_result(...))

qualifying = [
    element
    for element, row in zip(elements, read.rows)
    if row.is_all(SlotState.SUCCESS) and qualifies(row)
]
write = property_utilities.set_property_values_per_element_result(
    qualifying, write_properties, qualifying_values
)
population.record("Write", write, for_items=qualifying)
report = population.snapshot(completed=True)
```

Use `item_indices` when indices are already available or when the same original item deliberately receives multiple result rows:

```python
qualifying_indices = [index for index, row in enumerate(read.rows) if qualifies(row)]
qualifying = [elements[index] for index in qualifying_indices]
write = property_utilities.set_property_values_per_element_result(
    qualifying, write_properties, qualifying_values
)
population.record("Write", write, item_indices=qualifying_indices)
```

An item omitted from the last recorded step is `FILTERED` in a completed population. Within a repeated mapping, all terminal slots must be filtered for the item to be `FILTERED`; a successful terminal slot makes an intentional partial write `SUCCEEDED`.

## Pattern 4: In-Progress Inspection

Snapshots neither mutate nor close the collection:

```python
population = PopulationResults(elements)
before = population.snapshot()  # otherwise-clean outcomes are INCOMPLETE

read = population.record("Read", read_result)
after_read = population.snapshot(completed=False)

population.record("Write", read.project_successes(raw_write))
final = population.snapshot(completed=True)

assert before.steps == ()
assert len(after_read.steps) == 1
assert len(final.steps) == 2
```

Previously returned reports do not change after later recording.

## Pattern 5: Error Inspection and Application-Owned Retries

The report provides data for a retry decision but does not retry anything:

```python
report = population.snapshot(completed=True)

retriable_items = [
    outcome.original_item
    for outcome in report.outcomes
    if outcome.failed or outcome.upstream_failed
]

for outcome, failure in report.iter_failures():
    print(
        outcome.index,
        failure.step_name,
        failure.source_coordinate,
        failure.error.code,
        failure.error.message,
    )

if retriable_items:
    retry_population = PopulationResults(retriable_items)
    # The application executes and records its retry policy here.
```

`FAILED` has priority because it represents a directly recorded error. `UPSTREAM_FAILED` identifies a terminal dependency failure without a direct error. Whether either status is retriable is an application policy, not a utilities policy.

## Pattern 6: Exception Handling

`PopulationResults` is not a context manager and does not suppress or store exceptions. Keep the partial report next to the application-level exception if the caller needs both:

```python
population = PopulationResults(elements)

try:
    read = population.record("Read", property_utilities.get_property_values_per_element_result(...))
    population.record("Write", perform_write(read))
except Exception as exc:
    partial_report = population.snapshot(completed=False)
    raise ScriptExecutionError(partial_report) from exc
else:
    report = population.snapshot(completed=True)
```

The partial report reflects recorded population facts only. It has no batch-level `fatal_error` and cannot claim that a script exception occurred.

## Default Completed Outcome Interpretation

For a completed population, the reducer uses the last recorded step as the terminal step:

1. Any direct failure accumulated in any step makes the item `FAILED`.
2. Any terminal `UPSTREAM_FAILED` slot makes an otherwise-clean item `UPSTREAM_FAILED`.
3. If all terminal slots mapped to the item are `FILTERED`, it is `FILTERED`.
4. A mixture containing a terminal success is `SUCCEEDED`.
5. An item omitted from a non-empty terminal step is `FILTERED`.
6. With no steps, every item is `SUCCEEDED` when `completed=True`.

This last-step assumption is the default interpretation only. Selecting terminal steps, required/optional steps, fallbacks, retry policies, and stopping rules remain application concerns.
