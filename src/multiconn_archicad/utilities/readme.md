# Architecture & Style Guide: `multiconn_archicad.utilities`

This document defines the architectural boundaries, design patterns, coding conventions, and testing strategies for the `utilities` subpackage in `multiconn_archicad`.

All contributions to `utilities` must adhere to these guidelines.

---

## 1. Mission & Scope

The `utilities` subpackage provides **Level 3 Ergonomic Sugar** on top of `UnifiedApi`.

### What Belongs in `utilities`:
* **Idiomatic Pythonic wrappers** around repetitive Archicad JSON API interactions (e.g., context managers for resource safety).
* **Batch unwrapping and type coercion** (turning known API response wrappers into Python primitives).
* **Batch result containers** (`BatchResultBase`, `BatchResult`, `BatchResult2D`, `BatchGrid`, `RaggedBatchResult`, `BatchRow`, `BatchSlot`) that preserve explicit 1D and 2D alignment while isolating partial failures and non-executed cells.
* **Population result accumulation** (`PopulationResults`) that passively records pipeline steps, attributes failures to original input items, and produces immutable report snapshots.
* **Universal identifier constructors and normalizers** (e.g., GUID strings / UUIDs $\to$ typed `ElementIdArrayItem` / `PropertyIdArrayItem`).

### What Does NOT Belong in `utilities`:
* **Thin Pass-Through Wrappers:** Functions that merely forward already-constructed CAD models into single API endpoints without normalization, unnesting, or transformation are strictly prohibited.
* **Domain / Business Logic:** Company-specific layer naming, property naming conventions, or pipeline rules belong in downstream applications.
* **Execution orchestration:** Script execution, exception handling, stopping decisions, retries, timing/history, and progress events belong in downstream applications. `PopulationResults` only records facts supplied by the caller.
* **In-Memory Caching:** API-bound utilities do not cache CAD state. `PopulationResults` is an explicit, short-lived data collection; it is not a CAD-state cache.
* **Heavy Geometric Engines:** Zero `shapely`, CAD polygon clipping, or spatial containment routines.
* **IFC Dependencies:** Zero dependencies on `ifcopenshell`. IFC mappings belong in downstream packages.
* **Transport / Protocol Logic:** Low-level HTTP/socket handling belongs in `core` and `UnifiedApi`.

---

## 2. Core API Design Principles

### A. Bound Operations and Pure Helpers
* API-dependent operations are methods on domain groups such as `PropertyUtilities`, bound to one `UnifiedApi`. They store only the API reference and do not cache BIM data. Payload builders, identifier normalizers, and extractors remain standalone pure functions.
* **Classes:** API-bound utility groups, explicit result containers (`BatchResultBase`, `BatchResult`, `BatchResult2D`, `BatchGrid`, `RaggedBatchResult`, `BatchRow`, `PopulationResults`), and resource lifecycle context managers are permitted.
* **No "Active Record" Objects:** Never wrap an Archicad element in a stateful class with instance methods (e.g., `element.get_property()`). This encourages iterative $N+1$ socket calls, severely degrading CAD performance.

### B. The Dedicated Dual-Method Convention
To serve both fast-prototyping scripts and large-scale, eager batch pipelines (e.g., 100k+ elements), bulk operations provide two companion methods:

1. **Standard Method (`<name>`):**
   * **Target:** Simple scripts and rapid prototypes that require a clean result or an exception.
   * **Behavior:** **Raises on reported failure.** After the batch response arrives, any element or inner property failure raises a descriptive `BatchOperationError`. Writes may already have partially succeeded; these helpers provide no rollback or atomicity.
   * **Return Types:** Plain Python types (`list[T]`, scalar primitives) for queries, and **`int` (count of written property values)** for writes.
   * **Implementation:** A clean façade over `<name>_result(...)` calling `.raise_for_errors()`.
2. **Diagnostic Variant (`<name>_result`):**
   * **Target:** Telemetry, automated QA checkers, GUI viewers, and multi-step eager batch pipelines.
   * **Behavior:** **Retains reported partial failures.** Preserves 1:1 index alignment and stores structured `BatchError` entries. Invalid inputs, transport failures, and whole-command errors can still raise.
   * **Return Types:** Returns `BatchResult[T]` for 1D operations, `BatchGrid[T]` for fixed-width 2D operations (e.g., element property matrices), and `RaggedBatchResult[T]` for variable row-length collections.
3. **Scalar Convenience (`<name>` singular):**
   * Provided where intuitive (e.g., `resolve_property_id`), simply delegating to the batch form: `self.resolve_property_ids([uid])[0]`.

### C. Batch-First by Default
Archicad JSON API is optimized for bulk operations.
* **Rule:** Never design a utility that takes only a single element if a batch equivalent is possible.
* **Always accept sequences:** Accept `Sequence[ElementIdLike]`, not individual IDs.

### D. Immutability & Liberal Inputs (Postel's Law)
*"Be liberal in what you accept, and conservative in what you send."*

1. **Input Parameters:**
   * Accept liberal union types (`ElementIdLike`, `PropertyIdLike`, `PropertyUserId`) defined in `identifiers.py`.
   * Annotate collection inputs as read-only abstractions: `Sequence[T]` or `Mapping[K, V]` from `collections.abc`.
   * Accept `BatchResult2D[Any]` or `Sequence[Sequence[Any]]` for 2D inputs.
   * **Never mutate input parameters.**
2. **Return Types:**
   * Fail-fast queries return concrete collections (`list[T]`, `dict[K, V]`).
   * Diagnostic variants return concrete batch containers: `BatchResult[T]`, `BatchGrid[T]`, or `RaggedBatchResult[T]`.

### E. Public Access and Consistent Signatures

```python
from multiconn_archicad.utilities import (
    Utilities,
    BatchResultBase,
    BatchResult,
    BatchResult2D,
    BatchGrid,
    RaggedBatchResult,
    BatchRow,
    BatchSlot,
    SlotState,
    BatchError,
    PopulationResults,
    BatchStatus,
    BatchOperationError,
)
```

The package explicitly exports these core containers. Import pure payload helpers (`create_element_property_values_sparse`, etc.) directly from `multiconn_archicad.utilities.properties`.

---

## 3. Subpackage Directory Structure

```text
src/multiconn_archicad/utilities/
├── __init__.py           # Public export surface
├── api.py                # Utilities domain-group container
├── readme.md             # This document
├── results.py            # BatchResultBase, BatchResult, BatchResult2D, BatchGrid, RaggedBatchResult, BatchRow, BatchSlot, BatchError
├── batch_run.py          # PopulationResults, report models, record mapping, and pure reducers
├── identifiers.py        # Liberal type aliases & universal ID normalizers
├── properties.py         # Batch property reading, writing, and inspection
├── elements.py           # Planned: selection get/set, type filtering
├── teamwork.py           # Planned: TeamworkReserve context manager
└── attributes.py         # Planned: composite attribute queries
```

---

## 4. Subpackage Modules Breakdown

### `identifiers.py` (Universal Normalizers)
Centralizes type coercion across all utilities.
* **Input aliases:** `ElementIdLike` and `PropertyIdLike` accept models, UUIDs, and GUID strings. `PropertyUserId` accepts Official `BuiltInPropertyUserId` / `UserDefinedPropertyUserId` models.
* **Coercion Functions:** `normalize_element_id()`, `normalize_element_ids()`, `normalize_property_id()`, `normalize_property_ids()`, `to_official_property_id()`, `split_builtin_name()`.

### `properties.py` (`PropertyUtilities` and Pure Helpers)
* Value reads return Tapir **display strings**. They do not parse numbers or normalize units.
* Writes preserve `tapir.PropertyValue` instances, convert `None` to `""`, and otherwise use `str(value)`.
* **High-Level Sparse Writing:** `set_property_values_per_element_sparse_result(elements, properties, values_matrix)` automatically omits non-successful cells, performs the API call, and projects outcomes back onto an $N \times M$ `BatchGrid`.

---

## 5. Result Containers & The State-Driven Model

### A. The 4-State Slot Model (`SlotState` and `BatchSlot`)
Every cell in a 1D or 2D batch operation is an immutable `BatchSlot[T]`:

* **`SlotState.SUCCESS`**: Operation completed successfully; holds `value: T`.
* **`SlotState.ERROR`**: Direct API or execution failure; holds `error: BatchError`.
* **`SlotState.UPSTREAM_FAILED`**: Suppressed because an upstream dependency failed.
* **`SlotState.FILTERED`**: Intentionally bypassed by business logic.

Predicates: `slot.is_success`, `slot.is_error`, `slot.is_upstream_failed`, `slot.is_filtered`.

### B. Container Hierarchy: `BatchResultBase[T]`
All batch results inherit from `BatchResultBase[T]`, sharing a clean, state-driven inspection interface parameterized by `SlotState`.

```
                    ┌────────────────────────┐
                    │    BatchResultBase     │
                    └───────────┬────────────┘
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
  ┌─────────────┐        ┌──────────────┐        ┌───────────┐
  │ BatchResult │        │BatchResult2D │        │ BatchRow  │
  │    (1D)     │        │  (2D Base)   │        │           │
  └─────────────┘        └──────┬───────┘        └───────────┘
                     ┌──────────┴──────────┐
                     ▼                     ▼
              ┌─────────────┐     ┌───────────────────┐
              │  BatchGrid  │     │ RaggedBatchResult │
              │(Rectangular)│     │     (Ragged)      │
              └─────────────┘     └───────────────────┘
```

#### 2D Subclasses:
1. **`BatchGrid[T]`:** Represents a rectangular matrix where every row has identical width (`self.width: int`).
   * Constructed via `BatchGrid.from_rows(raw_rows, width=M)`.
   * Enforces dimension consistency and expands whole-row API errors into $M$ error slots.
   * Returned by all fixed-width matrix operations in `PropertyUtilities`.
2. **`RaggedBatchResult[T]`:** Represents a 2D result where rows may have varying lengths.
   * Constructed via `RaggedBatchResult.from_ragged_rows(raw_rows)`.
   * Defaults whole-row errors to 1 error slot if row length cannot be inferred.

#### Unified Query API:
```python
# 1. Zero-allocation counting (O(N) generator sum, no list allocation)
res.count()                          # Total slots/cells
res.count(SlotState.SUCCESS)         # Succeeded count
res.count(SlotState.ERROR)           # Direct error count
res.count(SlotState.UPSTREAM_FAILED) # Upstream blocked count
res.count(SlotState.FILTERED)        # Filtered count

# 2. Boolean checks
res.has(SlotState.ERROR)             # True if any errors exist
res.is_all(SlotState.SUCCESS)        # True if 100% succeeded

# 3. Uniform index queries (same signature for all states)
res.indices(SlotState.ERROR)         # tuple of coordinates matching state
res.iter_indices(SlotState.FILTERED) # generator yielding coordinates

# 4. Payload extraction
for coord, val in res.iter_successes(): ...  # Yields (coord, T)
for coord, err in res.iter_errors(): ...     # Yields (coord, BatchError)
```

---

## 6. Passive Population Reporting: `PopulationResults`

`PopulationResults[T]` records ordered results and their mappings back to the original population. It does not execute work, manage a lifecycle, catch exceptions, or decide whether processing should stop.

```python
population = PopulationResults(self.elements)
population.record("Step 1", step_result)
population.record("Step 2", step2_result)

# The application supplies whether its intended population processing completed.
report = population.snapshot(completed=True)
```

### A. Snapshot and Completion Rules

1. **Snapshots are immutable:** A snapshot owns tuple copies of its steps and outcomes. Recording another step does not change an earlier report.
2. **Snapshots do not close the collection:** Callers can continue recording after any snapshot.
3. **Completion is explicit:** `snapshot()` defaults to `completed=False`; otherwise-clean items are `INCOMPLETE`. `snapshot(completed=True)` applies the default terminal interpretation.
4. **Completion does not mean success:** Direct failures still produce `FAILED`, and terminal slots can produce `UPSTREAM_FAILED` or `FILTERED`.
5. **Exceptions remain application-owned:** If a script exception interrupts processing, the application may inspect `snapshot(completed=False)` and must propagate, store, or present the exception itself. `BatchReport` has no `fatal_error`.

### B. Minimal `BatchStep[T]`
`BatchStep` holds step provenance and the result object (`result: BatchResultBase[T]`). It contains **no pass-through GUI properties**. Callers query `step.result` directly:

```python
# Downstream inspection:
step.result.count(SlotState.SUCCESS)
step.result.has(SlotState.ERROR)

# Direct failure provenance mapped to original items:
for original_item_idx, failure in step.iter_failures():
    print(original_item_idx, failure.source_coordinate, failure.error)
```

### C. Truthful Status Classification
`BatchOutcome.status` accurately classifies why an element did or did not complete:

* **`BatchStatus.SUCCEEDED`**: Completed the pipeline cleanly.
* **`BatchStatus.FAILED`**: Direct API or calculation error in one or more steps.
* **`BatchStatus.UPSTREAM_FAILED`**: Prevented from completing because an upstream prerequisite failed.
* **`BatchStatus.FILTERED`**: All slots mapped in the terminal step were filtered, or the item was omitted from a non-empty terminal step.

These statuses describe recorded facts. Retry and stopping policy belongs to the application.
* **`BatchStatus.INCOMPLETE`**: The caller declared that intended processing of the population did not complete.

---

## 7. Common Pipeline Patterns in Practice

### Pattern 1: Paired Cell-Level 2D Copy ($N \times M \to N \times M$)
Copy independent properties across elements. Unreadable cells automatically become `UPSTREAM_FAILED` in Step 2:

```python
def run(self) -> ExecutionReport:
    population = PopulationResults(self.elements)
    self._validate_inputs()
    if self.elements:
        read = population.record(
            "Property read",
            self.property_utilities.get_property_values_per_element_result(
                self.elements, self.read_properties
            ),
        )
        population.record(
            "Property write",
            self.property_utilities.set_property_values_per_element_sparse_result(
                self.elements, self.write_properties, read
            ),
        )

    return ExecutionReport(population.snapshot(completed=True), planned_step_count=2)
```

### Pattern 2: Dependent Multi-Read $\to$ Multi-Write ($N \times M \to N \times P$)
All input properties are required to calculate derived properties:

```python
def run(self) -> ExecutionReport:
    population = PopulationResults(self.elements)
    read = population.record(
        "Read dimensions",
        self.property_utilities.get_property_values_per_element_result(
            self.elements, [self.prop_l, self.prop_w, self.prop_h]
        ),
    )
    valid_elements = read.aggregate_rows()
    payload = [
        elem_val
        for idx, (l, w, h) in valid_elements.iter_successes()
        for elem_val in self._build_payload(self.elements[idx], float(l), float(w), float(h))
    ]
    raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []
    population.record("Write Area & Volume", valid_elements.project_rows(raw_res, row_length=2))
    return ExecutionReport(population.snapshot(completed=True), planned_step_count=2)
```

### Pattern 3: Conditional Domain Filtering ($N \to K$ subset)
Mutations apply only to elements meeting business criteria. Filtered elements are classified as `FILTERED` and excluded from retries:

```python
def run(self) -> ExecutionReport:
    population = PopulationResults(self.elements)
    read = population.record("Read", self.property_utilities.get_property_values_per_element_result(...))
    qualifying = [
        elem for elem, row in zip(self.elements, read.rows)
        if row.is_all(SlotState.SUCCESS) and float(row[0].value) > 200.0
    ]
    write_res = self.property_utilities.set_property_values_per_element_result(
        qualifying, self.write_properties, qualifying_values
    )
    population.record("Write", write_res, for_items=qualifying)
    return ExecutionReport(population.snapshot(completed=True), planned_step_count=2)
```

---

## 8. Testing Strategy

Tests run offline with real official and Tapir Pydantic models and mocked API responses:

```text
tests/utilities/unit/
├── test_identifiers.py       # Coercion and GUID normalization
├── test_batch_results.py     # BatchResultBase, BatchResult, BatchResult2D, BatchGrid, RaggedBatchResult, BatchRow, BatchSlot
├── test_population_results.py # Passive snapshots, outcome rules, FIFO matching, atomic records
└── test_properties.py        # Sparse/dense builders, projection pipelines
```

The test suite enforces that:
* `count()` and `has()` work accurately across all 4 `SlotState`s.
* `BatchGrid` validates rectangular row lengths and non-positive widths.
* `RaggedBatchResult` correctly accommodates variable row lengths.
* snapshots remain unchanged after later records and do not prevent further recording.
* `completed=False` and `completed=True` preserve the documented default outcome rules.
* invalid record inputs do not append partial steps, and duplicate mappings remain FIFO-safe.

---

## 9. Planned Enhancements / Roadmap

* **`utils.property.get_available_property_ids_of_elements(elements)`**: Query Archicad's `GetAllPropertyNamesOfElements` to check property availability by Classification before executing writes.
* **`elements.py`**: Batch selection getter/setter, element type filtering (e.g., 3D element queries).
* **`attributes.py`**: Layer combinations and visible layer extractors.
* **`teamwork.py`**: Context manager for safe element reservation and automatic sending.
