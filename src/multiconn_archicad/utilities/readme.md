# Architecture & Style Guide: `multiconn_archicad.utilities`

This document defines the architectural boundaries, design patterns, coding conventions, and testing strategies for the `utilities` subpackage in `multiconn_archicad`.

All contributions to `utilities` must adhere to these guidelines.

---

## 1. Mission & Scope

The `utilities` subpackage provides **Level 3 Ergonomic Sugar** on top of `UnifiedApi`.

### What Belongs in `utilities`:
* **Idiomatic Pythonic wrappers** around repetitive Archicad JSON API interactions (e.g., context managers for resource safety).
* **Batch unwrapping and type coercion** (turning known API response wrappers into Python primitives).
* **Batch result containers** (`BatchResultBase`, `BatchResult`, `BatchResult2D`, `BatchRow`, `BatchSlot`) that preserve explicit 1D and 2D alignment while isolating partial failures and non-executed cells.
* **Workflow accumulation** (`BatchRun`) that acts as an atomic ledger of pipeline steps, attributing failures and terminal execution states back to original input items.
* **Universal identifier constructors and normalizers** (e.g., GUID strings / UUIDs $\to$ typed `ElementIdArrayItem` / `PropertyIdArrayItem`).

### What Does NOT Belong in `utilities`:
* **Thin Pass-Through Wrappers:** Functions that merely forward already-constructed CAD models into single API endpoints without normalization, unnesting, or transformation are strictly prohibited.
* **Domain / Business Logic:** Company-specific layer naming, property naming conventions, or pipeline rules belong in downstream applications.
* **In-Memory Caching:** API-bound utilities do not cache CAD state. `BatchRun` is an explicit, short-lived workflow record; it is not a CAD-state cache.
* **Heavy Geometric Engines:** Zero `shapely`, CAD polygon clipping, or spatial containment routines.
* **IFC Dependencies:** Zero dependencies on `ifcopenshell`. IFC mappings belong in downstream packages.
* **Transport / Protocol Logic:** Low-level HTTP/socket handling belongs in `core` and `UnifiedApi`.

---

## 2. Core API Design Principles

### A. Bound Operations and Pure Helpers
* API-dependent operations are methods on domain groups such as `PropertyUtilities`, bound to one `UnifiedApi`. They store only the API reference and do not cache BIM data. Payload builders, identifier normalizers, and extractors remain standalone pure functions.
* **Classes:** API-bound utility groups, explicit result/run containers (`BatchResultBase`, `BatchResult`, `BatchResult2D`, `BatchRun`), and resource lifecycle context managers are permitted.
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
   * **Return Types:** Returns `BatchResult[T]` for 1D operations and `BatchResult2D[T]` for 2D matrix operations.
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
   * **Never mutate input parameters.**
2. **Return Types:**
   * Fail-fast queries return concrete collections (`list[T]`, `dict[K, V]`).
   * Diagnostic variants return `BatchResult[T]` or `BatchResult2D[T]`.

### E. Public Access and Consistent Signatures

```python
from multiconn_archicad.utilities import (
    Utilities,
    BatchResultBase,
    BatchResult,
    BatchResult2D,
    BatchRow,
    BatchSlot,
    SlotState,
    BatchError,
    BatchRun,
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
├── results.py            # BatchResultBase, BatchResult, BatchResult2D, BatchRow, BatchSlot, BatchError
├── batch_run.py          # BatchRun, BatchStep, BatchFailure, BatchOutcome, BatchReport
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
* **High-Level Sparse Writing:** `set_property_values_per_element_sparse_result(elements, properties, values_matrix)` automatically omits non-successful cells, performs the API call, and projects outcomes back onto an $N \times M$ grid.

---

## 5. Result Containers & The State-Driven Model

### A. The 4-State Slot Model (`SlotState` and `BatchSlot`)
Every cell in a 1D or 2D batch operation is an immutable `BatchSlot[T]`:

* **`SlotState.SUCCESS`**: Operation completed successfully; holds `value: T`.
* **`SlotState.ERROR`**: Direct API or execution failure; holds `error: BatchError`.
* **`SlotState.UPSTREAM_FAILED`**: Suppressed because an upstream dependency failed. **Retriable.**
* **`SlotState.FILTERED`**: Intentionally bypassed by business logic. **Non-retriable.**

Predicates: `slot.is_success`, `slot.is_error`, `slot.is_upstream_failed`, `slot.is_filtered`.

### B. Container Hierarchy: `BatchResultBase[T]`
All batch results inherit from `BatchResultBase[T]`, sharing a clean, state-driven inspection interface parameterized by `SlotState`.

Coordinates are typed as `BatchCoordinate = int | tuple[int, int]` without generic parameter bloat:

```
                    ┌────────────────────────┐
                    │  iter_slots(state)     │  <-- Foundational Primitive (Coord, BatchSlot[T])
                    └───────────┬────────────┘
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ State & Indices │    │ Payload Extract │    │  State Queries  │
│                 │    │                 │    │                 │
│ iter_indices()  │    │ iter_successes()│    │ count(state)    │
│ indices()       │    │ iter_errors()   │    │ has(state)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

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

## 6. Workflow Orchestration: `BatchRun`

`BatchRun[T]` acts as an **atomic ledger of pipeline steps**. It derives element-level outcomes directly from step results.

```python
with BatchRun(self.elements) as run:
    run.record("Step 1", step_result)
    run.record("Step 2", step2_result)

report = run.report
```

### A. Context Manager Contract & Lifecycle Rules

1. **Clean Exit (`exc is None`):** Automatically calls `run.finish()`. All processed items without errors become `SUCCEEDED`.
2. **Standard `Exception`:** Caught automatically by `__exit__`. Calls `run.abort(exc)`, sets `fatal_error`, marks in-flight items as `INCOMPLETE`, and **suppresses the exception** so the caller can handle or present `run.report` cleanly.
3. **`BaseException` (`KeyboardInterrupt`, `SystemExit`):** Never suppressed; immediately propagates.
4. **`run.report` is a Non-Mutating Snapshot:**
   * Inspecting `run.report` while the run is open returns an in-flight snapshot with `status = BatchStatus.INCOMPLETE`.
   * It **does not close** the run; further steps can still be recorded.
5. **Early Returns Inside `with`:**
   * If exiting early from inside a `with` block, explicitly call `return ExecutionReport(run.finish())` to close the run.
   * `__exit__` will safely no-op since the run is already closed.

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
* **`BatchStatus.FAILED`**: Direct API or calculation error in one or more steps. **Retriable.**
* **`BatchStatus.UPSTREAM_FAILED`**: Prevented from completing because an upstream prerequisite failed. **Retriable.**
* **`BatchStatus.FILTERED`**: 100% of operations were intentionally bypassed by business logic. **Non-retriable.**
* **`BatchStatus.INCOMPLETE`**: Pipeline was interrupted by a fatal exception before completion.

---

## 7. Common Pipeline Patterns in Practice

### Pattern 1: Paired Cell-Level 2D Copy ($N \times M \to N \times M$)
Copy independent properties across elements. Unreadable cells automatically become `UPSTREAM_FAILED` in Step 2:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        self._validate_inputs()
        if self.elements:
            # Step 1: Read source properties (N x M matrix)
            read = run.record(
                "Property read",
                self.property_utilities.get_property_values_per_element_result(
                    self.elements, self.read_properties
                ),
            )

            # Step 2: Write readable cells only (sparse write handles payload + projection)
            run.record(
                "Property write",
                self.property_utilities.set_property_values_per_element_sparse_result(
                    self.elements, self.write_properties, read
                ),
            )

    return ExecutionReport(run.report, planned_step_count=2)
```

### Pattern 2: Dependent Multi-Read $\to$ Multi-Write ($N \times M \to N \times P$)
All input properties are required to calculate derived properties:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read dimensions (N x 3 matrix)
        read = run.record(
            "Read dimensions",
            self.property_utilities.get_property_values_per_element_result(
                self.elements, [self.prop_l, self.prop_w, self.prop_h]
            ),
        )

        # Step 2: Collapse cell failures into 1D element outcomes (length N)
        valid_elements = read.aggregate_rows()

        # Step 3: Compute calculations only for 100% valid elements
        payload = [
            elem_val
            for idx, (l, w, h) in valid_elements.iter_successes()
            for elem_val in self._build_payload(self.elements[idx], float(l), float(w), float(h))
        ]
        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 4: Re-inflate flat write response into an N x 2 matrix
        write = valid_elements.project_rows(raw_res, row_length=2)
        run.record("Write Area & Volume", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

### Pattern 3: Conditional Domain Filtering ($N \to K$ subset)
Mutations apply only to elements meeting business criteria. Filtered elements are classified as `FILTERED` and excluded from retries:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        read = run.record("Read", self.property_utilities.get_property_values_per_element_result(...))

        # Filter qualifying elements
        qualifying = [
            elem for elem, row in zip(self.elements, read.rows)
            if row.is_all(SlotState.SUCCESS) and float(row[0].value) > 200.0
        ]

        # Step 2: Execute and record only for subset via duplicate-safe FIFO matching
        write_res = self.property_utilities.set_property_values_per_element_result(
            qualifying, self.write_properties, qualifying_values
        )
        run.record("Write", write_res, for_items=qualifying)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## 8. Testing Strategy

Tests run offline with real official and Tapir Pydantic models and mocked API responses:

```text
tests/utilities/unit/
├── test_identifiers.py       # Coercion and GUID normalization
├── test_batch_results.py     # BatchResultBase, BatchResult, BatchResult2D, BatchRow, BatchSlot
├── test_batch_run.py         # BatchRun lifecycle, FIFO duplicate matching, atomic abort
└── test_properties.py        # Sparse/dense builders, projection pipelines
```

The test suite enforces that:
* `count()` and `has()` work accurately across all 4 `SlotState`s.
* `run.report` remains a non-mutating snapshot during open execution.
* Calling `finish()` or `abort()` on a closed run raises `RuntimeError`.
* Context managers cleanly suppress `Exception` while preserving `fatal_error`.

---

## 9. Planned Enhancements / Roadmap

* **`utils.property.get_available_property_ids_of_elements(elements)`**: Query Archicad's `GetAllPropertyNamesOfElements` to check property availability by Classification before executing writes.
* **`elements.py`**: Batch selection getter/setter, element type filtering (e.g., 3D element queries).
* **`attributes.py`**: Layer combinations and visible layer extractors.
* **`teamwork.py`**: Context manager for safe element reservation and automatic sending.