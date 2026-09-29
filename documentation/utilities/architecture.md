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
Operations over supplied items provide two companion methods when per-item diagnostics are useful. Discovery queries such as `get_3d_elements()` and layer-combination lookups return plain lists and raise on API errors; they do not need `_result` variants.

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
   * Accept liberal union types (`ElementIdLike`, `PropertyIdLike`, `AttributeIdLike`, `PropertyUserId`) defined in `identifiers.py`.
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
    PropertyUtilities,
    AttributeUtilities,
    ElementUtilities,
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

The package explicitly exports these utility groups and core containers. Import pure payload helpers (`create_element_property_values_sparse`, etc.) directly from `multiconn_archicad.utilities.namespaces.properties`.

Access bound groups through `api.utilities.property`, `api.utilities.element`, and `api.utilities.attribute`.
Import identifier aliases and normalizers directly from `multiconn_archicad.utilities.identifiers`.

---

## 3. Subpackage Directory Structure

```text
src/multiconn_archicad/utilities/
├── __init__.py               # Public export surface
├── api.py                    # Utilities domain-group container
├── identifiers.py            # ID aliases and normalizers
├── namespaces/
│   ├── __init__.py
│   ├── attributes.py         # Attribute and layer-combination lookups
│   ├── elements.py           # Element selection, filtering, and grouping
│   └── properties.py         # Property operations and payload builders
└── results/
    ├── __init__.py
    ├── batch_results.py      # Aligned 1D and 2D result containers
    ├── population.py         # PopulationResults, steps, outcomes, reports
    └── multi_population.py   # MultiPopulationResults and relations
```

---

## 4. Subpackage Modules Breakdown

### `identifiers.py` (Universal Normalizers)
Centralizes type coercion across all utilities.
* **Input aliases:** `ElementIdLike`, `PropertyIdLike`, and `AttributeIdLike` accept Official/Tapir ID models and wrappers, UUIDs, and GUID strings. `PropertyUserId` accepts Official `BuiltInPropertyUserId` / `UserDefinedPropertyUserId` models.
* **Coercion Functions:** `normalize_element_id()`, `normalize_element_ids()`, `normalize_property_id()`, `normalize_property_ids()`, `normalize_attribute_id()`, `normalize_attribute_ids()`, `to_official_property_id()`, `to_official_attribute_id()`, `split_builtin_name()`.
* Attribute normalization returns Tapir `AttributeIdArrayItem`; Official conversion returns `AttributeIdWrapperItem`.

### `namespaces/properties.py` (`PropertyUtilities` and Pure Helpers)
* Value reads return Tapir **display strings**. They do not parse numbers or normalize units.
* Writes preserve `tapir.PropertyValue` instances, convert `None` to `""`, and otherwise use `str(value)`.
* **High-Level Sparse Writing:** `set_property_values_per_element_sparse_result(elements, properties, values_matrix)` automatically omits non-successful cells, performs the API call, and projects outcomes back onto an $N \times M$ `BatchGrid`. For a single property, `set_flat_property_values_sparse_result(elements, property_id, values)` provides the same behavior directly with a `BatchResult`.

### `namespaces/attributes.py` (`AttributeUtilities`)
* `get_layer_names_of_combination(name)` returns visible layer names from an exact-name match of a saved combination. Visible locked layers and the built-in Archicad layer are included. The query does not activate the combination.
* It composes `get_layers_of_combination(name)` and the private `_get_names_of_visible_layers(layers)`. Each returns a plain list; command-level failures are raised by the core API client.
* Missing combinations and missing combination details produce `[]`. Per-layer detail errors raise a `BatchOperationError`; a combination with no visible layers returns `[]`.

### `namespaces/elements.py` (`ElementUtilities`)
* `set_selected_elements(elements)` replaces the current selection, accepting any `ElementIdLike` sequence. It compares GUIDs and sends only additions and removals in one command; if the sets already match, it sends no change command. The standard method raises on per-element failures. `set_selected_elements_result(elements)` returns a result aligned with the requested elements, counting already-selected elements as successes and preserving add failures; removal failures raise because the requested selection was not reached.
* `get_3d_elements()` queries the immutable `TYPES_3D` list with Tapir's `IS_INDEPENDENT` filter. This includes doors, windows, and openings while excluding component subelement types. It adds no current-view visibility or editability filters.
* The result is a plain element list in type/API order. Command-level failures are raised by the core API client.
* `filter_elements_by_property_values(elements, property_id, values)` filters an explicit population using exact display-string matches. Its `_result` companion preserves input alignment: matches hold element IDs, nonmatches are `FILTERED`, and property-read failures remain errors.
* `group_elements_by_property_value(elements, property_id)` returns a dictionary of display strings to element lists. It raises if a property read fails. Grouping preserves duplicate elements, first-seen key order and per-group input order. Empty display strings are valid values.
* `get_elements_in_layer_combination(name)` combines the attribute query, 3D population query, and the built-in `ModelView_LayerName` property. Its `_result` companion retains property-read failures against the queried population; prerequisites must succeed. No visible layers produces an empty standard result through normal filtering.
* Filtering with no search values marks every input `FILTERED` without reading properties. Input sequences are never mutated.

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
res.is_all(SlotState.SUCCESS)        # True only for a non-empty, fully successful result
res.raise_for_non_success()          # Raises for any non-successful slot; accepts an empty result

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
* In 1D and 2D projections, targets without a matching source receive `default_state` (default: `SlotState.FILTERED`).
* `FILTERED` guarantees safe omission: downstream sparse writers (`set_property_values_per_element_sparse_result`) will completely omit those cells from API write payloads.
* If a domain pipeline treats unmatched targets as broken prerequisites, pass `default_state=SlotState.UPSTREAM_FAILED`.

---

## 7. Usage Patterns

See [Usage Patterns](usage_patterns.md) for sparse writes, cross-population projections, conditional subsets, and error inspection examples.

---

## 8. Testing Strategy

Tests run offline with real official and Tapir Pydantic models and mocked API responses:

```text
tests/utilities/unit/
├── test_utilities_api.py     # Bound utility groups and public exports
├── test_identifiers.py       # Coercion and GUID normalization
├── test_attributes.py        # Saved combination visibility, name resolution, and layer errors
├── test_elements.py          # 3D populations, aligned filtering/grouping, and composition
├── test_batch_results.py     # BatchResultBase, BatchResult, BatchResult2D, BatchGrid, RaggedBatchResult, BatchRow, BatchSlot
├── test_population_results.py # Single-population snapshots, outcome rules, FIFO matching
├── test_multiple_populations.py # MultiPopulationResults, bounds validation, deduplication, 1D/2D projections
└── test_properties.py        # Sparse/dense builders, projection pipelines
```

The test suite enforces that:
* `count()` and `has()` work accurately across all 4 `SlotState`s.
* `MultiPopulationResults.relate()` validates index bounds against both source and target populations.
* `project()` and `project_rows()` broadcast unmatched states accurately and reject ambiguous multi-source matches.
* snapshots remain immutable after subsequent recording steps.
