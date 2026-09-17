# Architecture & Style Guide: `multiconn_archicad.utilities`

This document defines the architectural boundaries, design patterns, coding conventions, and testing strategies for the `utilities` subpackage in `multiconn_archicad`.

All contributions to `utilities` must adhere to these guidelines.

---

## 1. Mission & Scope

The `utilities` subpackage provides **Level 3 Ergonomic Sugar** on top of `UnifiedApi`.

### What Belongs in `utilities`:
* **Idiomatic Pythonic wrappers** around repetitive Archicad JSON API interactions (e.g., context managers for resource safety).
* **Batch unwrapping and type coercion** (turning known API response wrappers into Python primitives).
* **Batch result containers** (`BatchResult`, `BatchResult2D`, `BatchRow`, `BatchSlot`) that preserve explicit 1D and 2D alignment while isolating partial failures and non-executed cells.
* **Workflow accumulation** (`BatchRun`) that acts as an atomic ledger of pipeline steps, attributing failures and terminal execution states back to original input items.
* **Universal identifier constructors and normalizers** (e.g., GUID strings / UUIDs $\to$ typed `ElementIdArrayItem` / `PropertyIdArrayItem`).

### What Does NOT Belong in `utilities`:
* **Thin Pass-Through Wrappers:** Functions that merely forward already-constructed CAD models into single API endpoints without normalization, unnesting, or transformation are strictly prohibited.
* **Domain / Business Logic:** Company-specific layer naming, property naming conventions, or pipeline rules belong in downstream applications.
* **In-Memory Caching:** API-bound utilities do not cache CAD state. `BatchRun` is an explicit, short-lived workflow record; it is not a CAD-state cache. Caching policies belong in UI view-models or application pipelines using `functools` or `cachetools`.
* **Heavy Geometric Engines:** Zero `shapely`, CAD polygon clipping, or spatial containment routines.
* **IFC Dependencies:** Zero dependencies on `ifcopenshell`. IFC mappings belong in downstream packages.
* **Transport / Protocol Logic:** Low-level HTTP/socket handling belongs in `core` and `UnifiedApi`.

---

## 2. Core API Design Principles

### A. Bound Operations and Pure Helpers
* API-dependent operations are methods on domain groups such as `PropertyUtilities`, bound to one `UnifiedApi`. They store only the API reference and do not cache BIM data. Payload builders, identifier normalizers, and extractors remain standalone pure functions.
* **Classes:** API-bound utility groups, explicit result/run containers (`BatchResult`, `BatchResult2D`, `BatchRun`), and resource lifecycle context managers (e.g., planned `TeamworkReserve`) are permitted.
* **No "Active Record" Objects:** Never wrap an Archicad element in a stateful class with instance methods (e.g., `element.get_property()`). This encourages iterative $N+1$ socket calls, severely degrading CAD performance.

### B. The Dedicated Dual-Method Convention
To serve both fast-prototyping scripts and large-scale, eager batch pipelines (e.g., 100k+ elements), bulk operations provide two companion methods:

1. **Standard Method (`<name>`):**
   * **Target:** Simple scripts and rapid prototypes that require a clean result or an exception.
   * **Behavior:** **Raises on reported failure.** After the batch response arrives, any element or inner property failure raises a descriptive `BatchOperationError`. Writes may already have partially succeeded; these helpers provide no rollback or atomicity.
   * **Return Types:** Plain Python types (`list[T]`, scalar primitives) for queries, and **`int` (count of written property values for property setters)** for writes.
   * **Implementation:** A clean façade over `<name>_result(...)` calling `.raise_for_errors()`.
2. **Diagnostic Variant (`<name>_result`):**
   * **Target:** Telemetry, automated QA checkers, GUI viewers, and multi-step eager batch pipelines.
   * **Behavior:** **Retains reported partial failures.** Preserves 1:1 index alignment and stores structured `BatchError` entries. Invalid inputs, transport failures, and whole-command errors can still raise.
   * **Return Types:** Returns `BatchResult[T]` for one-dimensional operations and `BatchResult2D[T]` for matrix operations.
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
   * **Never mutate input parameters.** Never pop, append, or modify input collections in-place.
2. **Return Types:**
   * Fail-fast queries return concrete collections (`list[T]`, `dict[K, V]`).
   * Property mutations return `int` (written property value count) when all succeed.
   * Diagnostic variants return `BatchResult[T]` or `BatchResult2D[T]`, matching the operation shape.
   * Default to standard Python primitives (`str`, `float`, `int`, `bool`, `None`) or standard typed models.

### E. Public Access and Consistent Signatures

Use `header.unified.utilities.property` (or `api.utilities.property` for a standalone `UnifiedApi`).

```python
from multiconn_archicad.utilities import Utilities, BatchResult, BatchResult2D, BatchRun
from multiconn_archicad.utilities.properties import create_element_property_values_flat

utils = api.utilities
values = utils.property.get_flat_property_values(elements, property_id)
result = utils.property.set_flat_property_values_result(elements, property_id, values)

# Explicit binding is also available, including for tests:
utils = Utilities(api)

# Pure builders do not need a connection:
payload = create_element_property_values_flat(elements, property_id, values)
```

The package explicitly exports `Utilities`, `BatchResult`, `BatchResult2D`, `BatchRow`, `BatchSlot`, `SlotState`, `BatchError`, `BatchRun`, `BatchStatus`, and `BatchOperationError`. Import pure helpers directly from their defining modules.

---

## 3. Code Style & Conciseness Guidelines

1. **Horizontal Signatures by Default:**
   Do not split parameters vertically across lines unless there are 5+ parameters. Keep signatures compact and horizontal.
2. **Compose Over Re-inventing Loops:**
   High-level utilities compose over core engines. 1D flat helpers (`get_flat_property_values`, `set_flat_property_values`) delegate directly to optimized batch payloads without duplicating parsing logic.
3. **Strict Typing Over Loose Duck-Typing:**
   When an API response returns typed Pydantic models (e.g., `official.PropertyDefinition`), access fields directly (`prop_def.possibleEnumValues`). Do not use defensive `getattr(...)` chains when schemas are guaranteed.
4. **Concise Idioms, Not Code-Golf:**
   Prefer clean list comprehensions and named helper functions (`accessor=normalize_property_id`) over complex multi-nested comprehensions.

---

## 4. Subpackage Directory Structure

```text
src/multiconn_archicad/utilities/
├── __init__.py           # Public export surface
├── api.py                # Utilities domain-group container
├── readme.md             # This document
├── results.py            # BatchResult, BatchResult2D, BatchRow, BatchSlot, BatchError
├── batch_run.py          # BatchRun and workflow outcome records
├── identifiers.py        # Liberal type aliases & universal ID normalizers
├── properties.py         # Batch property reading, writing, and inspection
├── elements.py           # Planned: selection get/set, type filtering
├── teamwork.py           # Planned: TeamworkReserve context manager
└── attributes.py         # Planned: composite attribute queries
```

---

## 5. Subpackage Modules Breakdown

### `identifiers.py` (Universal Normalizers)
Centralizes type coercion across all utilities.
* **Input aliases:** `ElementIdLike` and `PropertyIdLike` accept models, UUIDs, and GUID strings. `PropertyUserId` accepts Official `BuiltInPropertyUserId` / `UserDefinedPropertyUserId` models; name tuples are not supported.
* **Coercion Functions:** `normalize_element_id()`, `normalize_element_ids()`, `normalize_property_id()`, `normalize_property_ids()`, `to_official_property_id()`, `split_builtin_name()`.

### `properties.py` (`PropertyUtilities` and Pure Helpers)

#### Value representation and result shape
Value reads return Tapir **display strings**, including numeric properties. They do not parse numbers or normalize units. Code performing calculations must explicitly interpret the returned text. Writes preserve `tapir.PropertyValue` instances, convert `None` to `""`, and otherwise use `str(value)`. 

* **Dense Payload Builders:** `create_element_property_values` and `create_element_property_values_flat` reject direct typed API errors with `BatchOperationError`.
* **Sparse Payload Builder:** `create_element_property_values_sparse` derives `(element_index, property_index)` coordinates from a matrix or `BatchResult2D` and omits failed or skipped cells/rows so that only attempted work is sent to Archicad.

---

## 6. Batch Error Handling, Results & Pipeline Orchestration

### A. The 4-State Slot Model (`SlotState` and `BatchSlot`)
Every cell in a 1D or 2D batch operation is represented by an immutable `BatchSlot[T]`, governed by an explicit `SlotState`:

* **`SlotState.SUCCESS`**: Operation completed successfully; holds `value: T`.
* **`SlotState.ERROR`**: Direct API or execution failure; holds `error: BatchError`.
* **`SlotState.UPSTREAM_FAILED`**: Execution was suppressed because an upstream prerequisite or dependency failed. **Retriable.**
* **`SlotState.FILTERED`**: Execution was intentionally bypassed by domain logic (e.g. element did not meet filter criteria). **Non-retriable.**

Convenience predicates:
* `slot.is_success`, `slot.is_error`, `slot.is_upstream_failed`, `slot.is_filtered`.
* `slot.is_skipped`: Returns `True` if the slot was not executed (`is_upstream_failed or is_filtered`).

### B. Containers: `BatchResult`, `BatchResult2D`, and `BatchRow`
* **`BatchSlot[T]`**: Immutable scalar cell outcome.
* **`BatchRow[T]`**: Immutable row container holding ordered `BatchSlot[T]` cells and an optional whole-row `error: BatchError | None`. Provides row-level queries (`row.is_all_success`, `row.is_upstream_failed`, `row.is_filtered`, `row.is_skipped`, `row.aggregate()`).
* **`BatchResult[T]`**: Immutable 1D result container of slots.
* **`BatchResult2D[T]`**: Immutable ragged or regular 2D matrix composed of `BatchRow[T]` instances.

### C. Shape-Preserving Projection (`project_*`)
Instead of manually matching coordinates, flattening lists, and maintaining parallel tracking arrays, step outputs re-inflate flat responses directly back into the exact matrix or vector shape of prior steps:

1. **`BatchResult.project_successes(raw_items) -> BatchResult[U]` ($1\text{D} \to 1\text{D}$):**
   Re-inflates flat responses into this 1D shape. Consumes raw items only for `SUCCESS` slots. Slots that experienced an error or upstream failure become `UPSTREAM_FAILED`; filtered slots become `FILTERED`.
2. **`BatchResult.project_rows(raw_items, row_length) -> BatchResult2D[U]` ($1\text{D} \to 2\text{D}$):**
   Expands a 1D element-level result into an $N \times \text{row\_length}$ matrix. Successful slots expand into newly parsed rows; failed/blocked slots expand into `UPSTREAM_FAILED` rows; filtered slots expand into `FILTERED` rows.
3. **`BatchResult2D.project_successes(raw_items) -> BatchResult2D[U]` ($2\text{D} \to 2\text{D}$):**
   Re-inflates flat responses across successful cells in row-major order. Cells that failed upstream or were blocked become `UPSTREAM_FAILED`.

### D. Workflow Orchestration: `BatchRun`
`BatchRun[T]` acts as an **atomic ledger of pipeline steps**. It does not duplicate error arrays; instead, it derives element-level outcomes directly from the step results.

```python
with BatchRun(elements) as run:
    # Record steps atomically
    run.record("Step Name", step_result)
report = run.report
```

#### Context Manager Contract
* Automatically closes and calls `finish()` when exiting cleanly.
* On standard `Exception`, catches and calls `abort(exc)`, sets `fatal_error`, suppresses the exception, and marks in-flight elements as `INCOMPLETE`.
* `BaseException` (e.g. `KeyboardInterrupt`, `SystemExit`) is never swallowed.

#### Step Recording & Duplicate-Safe FIFO Alignment
`run.record(name, result, *, item_indices=None, for_items=None)` records a step:
* **Full Step (default):** When `item_indices` and `for_items` are omitted, `result` length must match `len(original_items)`.
* **Subset by Item (`for_items`):** Resolves unhashable models (e.g. mutable Pydantic `ElementIdArrayItem`) in **$O(N)$ time** using structural fingerprinting (`repr`) and duplicate-safe FIFO queues.
* **Subset by Index (`item_indices`):** Direct integer index mapping when caller already has index offsets.

### E. Truthful Status Classification & Retry Strategy
`BatchOutcome.status` accurately classifies why an element did or did not complete:

* **`BatchStatus.SUCCEEDED`**: Completed the pipeline cleanly. If an element had some properties filtered out and the remaining succeeded, it is considered `SUCCEEDED`.
* **`BatchStatus.FAILED`**: Produced a direct API or calculation error in one or more steps. **Retriable.**
* **`BatchStatus.UPSTREAM_FAILED`**: Was prevented from completing because an upstream prerequisite failed. **Retriable.**
* **`BatchStatus.FILTERED`**: 100% of the element's operations were intentionally bypassed by domain logic. **Non-retriable.**
* **`BatchStatus.INCOMPLETE`**: Run was interrupted by a fatal exception or inspected mid-flight.

A retry loop targets retriable elements without re-running intentionally filtered elements:
```python
retriable_elements = [
    outcome.original_item for outcome in report.outcomes
    if outcome.failed or outcome.upstream_failed
]
```

---

## 7. Common Pipeline Patterns in Practice

### Pattern A: Paired Cell-Level 2D Copy ($N \times M \to N \times M$)
Unreadable cells in Step 1 automatically become `UPSTREAM_FAILED` in Step 2 without manual coordinate bookkeeping:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read properties (N x M matrix)
        read = run.record(
            "Property read",
            self.property_utilities.get_property_values_per_element_result(
                self.elements, self.read_properties
            ),
        )

        # Step 2: Write readable cells only (sparse builder derives coordinates)
        payload = create_element_property_values_sparse(self.elements, self.write_properties, read)
        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 3: Re-inflate flat write response back into the exact N x M matrix shape
        write = read.project_successes(raw_res)
        run.record("Property write", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

### Pattern B: Dependent Multi-Read $\to$ Multi-Write ($N \times M \to N \times P$)
Step 1 is evaluated at the element level; Step 2 writes $P$ properties for valid elements and inflates to $N \times P$:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read dimensions (N x 3 matrix)
        read = run.record("Read dimensions", self.property_utilities.get_property_values_per_element_result(
            self.elements, [self.prop_l, self.prop_w, self.prop_h]
        ))

        # Collapse cell failures into 1D element outcomes (length N)
        valid_elements = read.aggregate_rows()

        # Step 2: Compute 2 output properties (Area, Volume) for valid elements
        payload = [
            elem_val
            for idx, (l, w, h) in valid_elements.iter_successes()
            for elem_val in self._build_area_and_volume(self.elements[idx], float(l), float(w), float(h))
        ]
        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 3: Re-inflate flat write response into an N x 2 matrix
        write = valid_elements.project_rows(raw_res, row_length=2)
        run.record("Write Area & Volume", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

### Pattern C: Arbitrary Python Filtering on a Subset (`for_items`)
Step 2 runs only on a filtered subset; non-qualifying elements are recorded as `FILTERED`:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read properties for all elements
        read = run.record("Read", self.property_utilities.get_property_values_per_element_result(...))

        # Filter using row predicates
        qualifying_elements = [
            elem for elem, row in zip(self.elements, read.rows)
            if row.is_all_success and float(row[0].success_value) > 3.0
        ]

        # Step 2: Run only for qualifying elements
        write_res = self.property_utilities.set_property_values_per_element_result(
            qualifying_elements, self.write_properties, qualifying_values
        )

        # Record subset step using O(N) duplicate-safe FIFO alignment
        run.record("Property write", write_res, for_items=qualifying_elements)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## 8. Testing Strategy

Tests run offline with real official and Tapir Pydantic models and mocked API responses:

```text
tests/utilities/unit/
├── test_identifiers.py
├── test_batch_results.py     # 1D/2D result, BatchRow, BatchSlot
├── test_batch_run.py         # BatchRun
└── test_properties.py        # payloads, row aggregation, and projection pipelines
```

The result tests cover direct typed errors, ragged and whole-row matrix failures, `BatchRow` encapsulation, 1D/2D projections, FIFO duplicate safety in `for_items`, outcome state derivation (`UPSTREAM_FAILED` vs `FILTERED`), and context manager idempotency.

---

## 9. Planned Enhancements / Roadmap

* **`utils.property.get_available_property_ids_of_elements(elements)`**: Query Archicad's `GetAllPropertyNamesOfElements` to check property availability by Classification before executing writes.
* **`elements.py`**: Batch selection getter/setter, element type filtering (e.g., 3D element queries).
* **`attributes.py`**: Layer combinations and visible layer extractors.
* **`teamwork.py`**: Context manager for safe element reservation and automatic sending.