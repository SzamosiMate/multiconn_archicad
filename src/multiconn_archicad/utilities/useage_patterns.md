# Batch Pipeline Usage Patterns & Cookbook

This guide shows how to combine `BatchResult`, `BatchGrid`, `BatchRow`, `PopulationResults`, and `MultiPopulationResults` in failure-tolerant Archicad scripts.

## The Core Mental Model

Every pipeline records facts about ordered populations:

```python
# Single population:
from multiconn_archicad.utilities import PopulationResults
population = PopulationResults(self.elements)

# Multiple populations:
from multiconn_archicad.utilities import MultiPopulationResults
multi = MultiPopulationResults()
sources = multi.add_population("sources", source_elements)
targets = multi.add_population("targets", target_elements)
```

The application executes each operation and decides whether to continue. Collections store result objects and their mapping to original items. When the application reaches its intended end, it takes a completed snapshot:

```python
# Single population:
report = population.snapshot(completed=True)

# Multiple populations:
reports = multi.snapshot(completed=True)
target_report = reports["targets"]
```

If processing stops early, calling `snapshot(completed=False)` marks otherwise-clean items `INCOMPLETE`; direct failures already recorded remain `FAILED`.

Every slot and item outcome has an explicit state:

| Slot / outcome | Meaning |
| :--- | :--- |
| `SUCCESS` / `SUCCEEDED` | Completed cleanly. |
| `ERROR` / `FAILED` | A direct failure was recorded. |
| `UPSTREAM_FAILED` | A prerequisite prevented execution. |
| `FILTERED` | Intentionally omitted by application logic. |
| `INCOMPLETE` | The caller declared that intended processing did not reach its end. |

---

## Pattern 1: Paired Cell-Level Copy ($N \times M \to N \times M$)

Use projections to preserve an $N \times M$ shape while writing only readable cells:

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

---

## Pattern 2: Multi-Population Cross-Copy ($N \to M$ Spatial Matching)

When reading from one population and writing to a different population, use `MultiPopulationResults` and `PopulationRelation`:

```python
def run(self) -> ExecutionReport:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", self.source_elements)
    targets = multi.add_population("targets", self.target_elements)

    # 1. Read source property data
    read_grid = sources.record(
        "Read source properties",
        self.property_utils.get_property_values_per_element_result(self.source_elements, self.props),
    )

    # 2. Match elements (returns list of (src_idx, tgt_idx) pairs)
    matched_pairs = self.compute_spatial_intersections(self.source_elements, self.target_elements)

    # 3. Register relationship directly between population variables
    matching = multi.relate(sources, targets, matched_pairs)

    # 4. Project source matrix to target shape
    #    Unmatched target elements automatically default to SlotState.FILTERED
    target_matrix = matching.project_rows(read_grid)

    # 5. Sparse write to targets (omits FILTERED cells from write payload)
    write_result = self.property_utils.set_property_values_per_element_sparse_result(
        self.target_elements, self.props, target_matrix
    )
    targets.record("Write target properties", write_result)

    return ExecutionReport(multi.snapshot(completed=True)["targets"])
```

### Unmatched Target Handling
By default, `matching.project()` and `matching.project_rows()` map unmatched targets to `SlotState.FILTERED`. This guarantees non-destructive omission.

If your workflow treats unmatched elements as missing prerequisites, pass `unmatched=SlotState.UPSTREAM_FAILED`:

```python
target_matrix = matching.project_rows(read_grid, unmatched=SlotState.UPSTREAM_FAILED)
```

---

## Pattern 3: Dependent Multi-Read to Multi-Write ($N \times M \to N \times P$)

When every input property is required, aggregate each row before calculating derived properties:

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

A failed input row becomes an upstream-failed output row.

---

## Pattern 4: Conditional Subsets ($N \to K$)

Use `for_items` when domain objects are easiest to retain. Duplicate equal objects resolve FIFO:

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

An item omitted from the terminal step is marked `FILTERED` in a completed population.

---

## Pattern 5: Cross-Population Diagnostics & Error Inspection

To understand why a target failed, inspect the relation to identify upstream source errors:

```python
reports = multi.snapshot(completed=True)
source_report = reports["sources"]
target_report = reports["targets"]

for tgt_idx, outcome in enumerate(target_report.outcomes):
    if outcome.failed or outcome.upstream_failed:
        # Which sources were linked to this target?
        src_indices = matching.sources_for_target(tgt_idx)
        for s_idx in src_indices:
            src_failures = source_report.outcomes[s_idx].failures
            for failure in src_failures:
                print(f"Target {tgt_idx} affected by Source {s_idx} [{failure.error.code}]: {failure.error.message}")
```

Direct failures always stay attached to the population where they occurred; relationship lookups preserve original error coordinates without cross-contaminating outcomes.

---

## Pattern 6: In-Progress Inspection

Snapshots neither mutate nor close the collection:

```python
multi = MultiPopulationResults()
sources = multi.add_population("sources", source_elements)
targets = multi.add_population("targets", target_elements)

before = multi.snapshot()  # all items INCOMPLETE

sources.record("Read", read_result)
matching = multi.relate(sources, targets, pairs)
midway = multi.snapshot(completed=False)

targets.record("Write", write_result)
final = multi.snapshot(completed=True)

assert len(before["sources"].steps) == 0
assert len(midway["sources"].steps) == 1
assert len(final["targets"].steps) == 1
```

---

## Pattern 7: Application-Level Exception Handling

Collections do not suppress or store exceptions. Capture partial snapshots when exceptions occur:

```python
multi = MultiPopulationResults()
sources = multi.add_population("sources", source_elements)
targets = multi.add_population("targets", target_elements)

try:
    read = sources.record("Read", property_utilities.get_property_values_per_element_result(...))
    matching = multi.relate(sources, targets, run_matching())
    targets.record("Write", perform_write(matching.project_rows(read)))
except Exception as exc:
    partial_reports = multi.snapshot(completed=False)
    raise ScriptExecutionError(partial_reports) from exc
else:
    reports = multi.snapshot(completed=True)
```

The partial report retains all facts recorded up to the moment of failure.
