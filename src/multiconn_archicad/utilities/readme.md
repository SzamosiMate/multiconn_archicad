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
* **Population result accumulation** (`PopulationResults`, `MultiPopulationResults`, `PopulationRelation`) that passively records pipeline steps, attributes failures to original input items, maps relationships across populations, and produces immutable report snapshots.
* **Universal identifier constructors and normalizers** (e.g., GUID strings / UUIDs $\to$ typed `ElementIdArrayItem` / `PropertyIdArrayItem`).

### What Does NOT Belong in `utilities`:
* **Thin Pass-Through Wrappers:** Functions that merely forward already-constructed CAD models into single API endpoints without normalization, unnesting, or transformation are strictly prohibited.
* **Domain / Business Logic:** Company-specific layer naming, property naming conventions, or pipeline rules belong in downstream applications.
* **Execution orchestration:** Script execution, exception handling, stopping decisions, retries, timing/history, and progress events belong in downstream applications. `PopulationResults` and `MultiPopulationResults` only record facts supplied by the caller.
* **In-Memory Caching:** API-bound utilities do not cache CAD state. Collections are explicit, short-lived data containers; they are not BIM-state caches.
* **Heavy Geometric Engines:** Zero `shapely`, CAD polygon clipping, or spatial containment routines.
* **IFC Dependencies:** Zero dependencies on `ifcopenshell`. IFC mappings belong in downstream packages.
* **Transport / Protocol Logic:** Low-level HTTP/socket handling belongs in `core` and `UnifiedApi`.

---

## 2. Core API Design Principles

### A. Bound Operations and Pure Helpers
* API-dependent operations are methods on domain groups such as `PropertyUtilities`, bound to one `UnifiedApi`. They store only the API reference and do not cache BIM data. Payload builders, identifier normalizers, and extractors remain standalone pure functions.
* **Classes:** API-bound utility groups, explicit result containers (`BatchResultBase`, `BatchResult`, `BatchResult2D`, `BatchGrid`, `RaggedBatchResult`, `BatchRow`, `BatchSlot`, `PopulationResults`, `MultiPopulationResults`, `PopulationRelation`), and resource lifecycle context managers are permitted.
* **No "Active Record" Objects:** Never wrap an Archicad element in a stateful class with instance methods (e.g., `element.get_property()`). This encourages iterative $N+1$ socket calls, severely degrading CAD performance.

### B. The Dedicated Dual-Method Convention
To serve both fast-prototyping scripts and large-scale, eager batch pipelines (e.g., 100k+ elements), bulk operations provide two companion methods:

1. **Standard Method (`<name>`):**
   * **Target:** Simple scripts and rapid prototypes that require a clean result or an exception.
   * **Behavior:** **Raises on reported failure.** After the batch response arrives, any element or inner property failure raises a descriptive `BatchOperationError`. Writes may already have partially succeeded; these helpers provide no rollback or atomicity.
   * **Return Types:** Plain Python types (`list[T]`, scalar primitives) for queries. Successful writes return `None`; failed writes raise `BatchWriteError` with the complete typed result attached.
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
    MultiPopulationResults,
    PopulationRelation,
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
├── population_results.py # PopulationResults, MultiPopulationResults, PopulationRelation, BatchReport, and reducers
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
* **High-Level Sparse Writing:** `set_property_values_per_element_sparse_result(elements, properties, values_matrix)` automatically omits non-successful cells, performs the API call, and projects outcomes back onto an $N \times M$ `BatchGrid`. For a single property, `set_flat_property_values_sparse_result(elements, property_id, values)` provides the same behavior directly with a `BatchResult`.

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

## 6. Passive Population Reporting & Multi-Population Relations

### A. Single Population: `PopulationResults`
`PopulationResults[T]` passively records pipeline steps and attributes failures to original input items:

```python
population = PopulationResults(self.elements)
population.record("Step 1", step_result)
population.record("Step 2", step2_result)

# The application supplies whether its intended population processing completed.
report = population.snapshot(completed=True)
```

1. **Snapshots are immutable:** A snapshot owns tuple copies of its steps and outcomes. Recording another step does not change an earlier report.
2. **Completion is explicit:** `snapshot(completed=False)` marks otherwise-clean items `INCOMPLETE`. `snapshot(completed=True)` evaluates terminal outcomes.
3. **Exceptions are application-owned:** `BatchReport` has no `fatal_error`. Interrupted executions produce partial snapshots while domain runners handle exceptions.

### B. Truthful Status Classification
`BatchOutcome.status` classifies why an element did or did not complete:
* **`BatchStatus.SUCCEEDED`**: Completed the pipeline cleanly.
* **`BatchStatus.FAILED`**: Direct error in one or more recorded steps.
* **`BatchStatus.UPSTREAM_FAILED`**: Prevented from completing because an upstream prerequisite failed.
* **`BatchStatus.FILTERED`**: All terminal slots were filtered, or the item was omitted from a non-empty terminal step.
* **`BatchStatus.INCOMPLETE`**: The caller declared that intended processing did not reach its end.

### C. Multi-Population Registry: `MultiPopulationResults`
When a script reads one population and writes to another (e.g., spatial matching, region queries), `MultiPopulationResults` acts as a passive registry:

```python
multi = MultiPopulationResults()
sources = multi.add_population("sources", source_elements)
targets = multi.add_population("targets", target_elements)

# Snapshot returns a mapping of BatchReports
reports = multi.snapshot(completed=True)
sources_report = reports["sources"]
targets_report = reports["targets"]
```

### D. Explicit Relationships: `PopulationRelation`
Relationships connect populations using original-item index pairs:

```python
# Matching returns a sequence of (source_idx, target_idx) pairs
matching = multi.relate(sources, targets, matched_pairs)

# 1. Bidirectional index queries
target_indices = matching.targets_for_source(source_index=0)
source_indices = matching.sources_for_target(target_index=3)

# 2. Result projections (aligning source reads to target dimensions)
target_values = matching.project(source_values)          # 1D projection
target_grid = matching.project_rows(source_read_matrix)  # 2D grid projection
```

#### Unmatched Replacement & Safe Omission
* In 1D and 2D projections, targets without a matching source receive `unmatched` (default: `SlotState.FILTERED`).
* `FILTERED` guarantees safe omission: downstream sparse writers (`set_property_values_per_element_sparse_result`) will completely omit those cells from API write payloads.
* If a domain pipeline treats unmatched targets as broken prerequisites, pass `unmatched=SlotState.UPSTREAM_FAILED`.

---

## 7. Common Pipeline Patterns in Practice

### Pattern 1: Paired Cell-Level 2D Copy ($N \times M \to N \times M$)
```python
def run(self) -> ExecutionReport:
    population = PopulationResults(self.elements)
    read = population.record(
        "Property read",
        self.property_utilities.get_property_values_per_element_result(self.elements, self.read_properties),
    )
    population.record(
        "Property write",
        self.property_utilities.set_property_values_per_element_sparse_result(self.elements, self.write_properties, read),
    )
    return ExecutionReport(population.snapshot(completed=True), planned_step_count=2)
```

### Pattern 2: Multi-Population Cross-Copy ($N \to M$ Spatial Match)
```python
def run(self) -> ExecutionReport:
    multi = MultiPopulationResults()
    sources = multi.add_population("sources", self.source_elements)
    targets = multi.add_population("targets", self.target_elements)

    # 1. Read source data
    read_grid = sources.record(
        "Read sources",
        self.property_utilities.get_property_values_per_element_result(self.source_elements, self.properties),
    )

    # 2. Calculate and register spatial match pairs [(src_idx, tgt_idx), ...]
    matching = multi.relate(sources, targets, self.match_geometry())

    # 3. Project source grid to target coordinates (unmatched elements default to FILTERED)
    target_aligned_grid = matching.project_rows(read_grid)

    # 4. Sparse write to targets (propagates UPSTREAM_FAILED and FILTERED cleanly)
    targets.record(
        "Write targets",
        self.property_utilities.set_property_values_per_element_sparse_result(
            self.target_elements, self.properties, target_aligned_grid
        ),
    )

    return ExecutionReport(multi.snapshot(completed=True)["targets"])
```

### Pattern 3: Conditional Domain Filtering ($N \to K$ subset)
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
├── test_population_results.py # Single-population snapshots, outcome rules, FIFO matching
├── test_multi_population.py  # MultiPopulationResults, bounds validation, deduplication, 1D/2D projections
└── test_properties.py        # Sparse/dense builders, projection pipelines
```

The test suite enforces that:
* `count()` and `has()` work accurately across all 4 `SlotState`s.
* `PopulationRelation.relate()` validates index bounds against both source and target populations.
* `project()` and `project_rows()` broadcast unmatched states accurately and reject ambiguous multi-source matches.
* snapshots remain immutable after subsequent recording steps.
