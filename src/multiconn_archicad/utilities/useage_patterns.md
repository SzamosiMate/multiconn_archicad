# Batch Pipeline Usage Patterns & Cookbook

This guide details the standard pipeline design patterns for `multiconn_archicad.utilities`. It explains how to combine `BatchResult`, `BatchGrid`, `RaggedBatchResult`, `BatchRow`, and `BatchRun` to write declarative, shape-preserving, and failure-tolerant Archicad automation scripts.

---

## The Core Mental Model

Every batch pipeline is anchored to a sequence of original items:
```python
with BatchRun(self.elements) as run:
    ...
```

### 1. Shape Alignment
Instead of tracking element indices or coordinates manually, steps preserve shape:
* **Cell-level ($M \to M$):** When properties are independent, results re-inflate into the source step's grid using `read.project_successes(...)`.
* **Row-level ($M \to P$):** When properties are interdependent, the input matrix is collapsed into a 1D element vector via `read.aggregate_rows()`, and re-inflated into the target width via `project_rows(..., row_length=P)`.

### 2. The 4-State Lifecycle
Every slot and element outcome is explicitly classified:

| State | Retriable? | Meaning |
| :--- | :---: | :--- |
| **`SUCCESS` / `SUCCEEDED`** | No | Completed cleanly. |
| **`ERROR` / `FAILED`** | **Yes** | Direct failure in one or more steps. |
| **`UPSTREAM_FAILED`** | **Yes** | Execution was blocked because a prerequisite step or property failed. |
| **`FILTERED`** | No | Intentionally bypassed by business logic (e.g., criteria not met). |
| **`INCOMPLETE`** | — | Pipeline aborted by a fatal exception before completion. |

---

## Quick Reference: Which Pattern Should I Use?

| Pipeline Scenario | Input $\to$ Output | Core Projection Helper | Pattern |
| :--- | :---: | :--- | :---: |
| **Property Copy / Translation** | $N \times M \to N \times M$ | `read.project_successes(raw)` | [Pattern 1](#pattern-1-paired-cell-level-2d-copy-n-times-m-to-n-times-m) |
| **Derived Calculations ($L, W, H \to \text{Area}, \text{Vol}$)** | $N \times M \to N \times P$ | `valid.project_rows(raw, row_length=P)` | [Pattern 2](#pattern-2-dependent-multi-read-to-multi-write-n-times-m-to-n-times-p) |
| **Subset Filtering (e.g. Walls $> 3\text{m}$)** | $N \to K$ subset | `run.record(..., for_items=subset)` | [Pattern 3](#pattern-3-conditional-domain-filtering-n-to-k-subset) |
| **Single Scalar Property Pipeline** | $N \times 1 \to N \times 1$ | `flat_read.project_successes(raw)` | [Pattern 4](#pattern-4-scalar-1d-pipeline-n-to-n) |
| **Branching Pipelines (Walls vs Slabs)** | $N \to \text{Sub}_A + \text{Sub}_B$ | Independent subset records | [Pattern 5](#pattern-5-branching-heterogeneous-pipelines) |

---

## Pattern 1: Paired Cell-Level 2D Copy ($N \times M \to N \times M$)

### When to use
Use when copying, translating, or synchronizing $M$ independent properties across $N$ elements (e.g., source property $j$ maps directly to target property $j$).

### Architectural Behavior
* Failures are **independent per cell**. If reading Property 1 fails on an element but Property 2 succeeds, Property 2 is still written.
* Cells that could not be read in Step 1 automatically become **`UPSTREAM_FAILED`** in Step 2.
* Step 1 returns a `BatchGrid[str]` with a fixed `width = M`.
* The write response re-inflates directly into the exact $N \times M$ shape of the read step via `read.project_successes(raw_res)`, returning a `BatchGrid`.

```
Read Step (N x 2)                  Sparse Payload       Raw Write        Projected Step 2 (N x 2)
[SUCCESS, ERROR          ]  -->   [Elem0, Prop0 ]  -->  [OK  ]   -->    [SUCCESS, UPSTREAM_FAILED]
[SUCCESS, SUCCESS        ]        [Elem1, Prop0 ]       [OK  ]          [SUCCESS, SUCCESS        ]
                                  [Elem1, Prop1 ]       [FAIL]          [SUCCESS, ERROR          ]
```

### Code Implementation

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        self._validate_inputs()
        if not self.elements:
            return ExecutionReport(run.report, planned_step_count=2)

        # Step 1: Read source properties (returns BatchGrid[str])
        read = run.record(
            "Property read",
            self.property_utilities.get_property_values_per_element_result(
                self.elements, self.read_properties
            ),
        )

        # Step 2: Build sparse payload (omits failed/unreadable cells)
        payload = create_element_property_values_sparse(self.elements, self.write_properties, read)
        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 3: Re-inflate flat write response into exact N x M BatchGrid shape
        # Unread cells automatically become UPSTREAM_FAILED
        write = read.project_successes(raw_res)
        run.record("Property write", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## Pattern 2: Dependent Multi-Read $\to$ Multi-Write ($N \times M \to N \times P$)

### When to use
Use when calculating derived properties where **all input properties are required** (e.g., reading 3 dimensions to compute 2 outputs: Area and Volume).

### Architectural Behavior
* Failures are **element-level**. If *any* input property fails to read, the calculation cannot run for that element.
* `read.aggregate_rows()` collapses the $N \times M$ matrix into an $N \times 1$ result of tuples `BatchResult[tuple[str, ...]]`. Any cell failure turns the entire row into an aggregate error.
* `valid_elements.project_rows(raw_res, row_length=P)` expands the 1D results into an $N \times P$ matrix (`BatchResult2D`). Elements that failed the read step become full rows of `UPSTREAM_FAILED`.

```
Read Step (N x 3)                  aggregate_rows (N)      project_rows (N x 2)
[SUCCESS, SUCCESS, SUCCESS]  -->  SUCCESS             -->  [SUCCESS, SUCCESS        ]
[SUCCESS, ERROR,   SUCCESS]       ERROR (aggregated)       [UPSTREAM_FAILED, UPSTREAM_FAILED]
```

### Code Implementation

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read 3 dimensions per element (returns BatchGrid[str] with width=3)
        read = run.record(
            "Read dimensions",
            self.property_utilities.get_property_values_per_element_result(
                self.elements, [self.prop_len, self.prop_w, self.prop_h]
            ),
        )

        # Step 2: Aggregate to element-level validity (BatchResult of 3-tuples)
        valid_elements = read.aggregate_rows()

        # Step 3: Compute calculations only for 100% valid elements
        payload = []
        for idx, (l, w, h) in valid_elements.iter_successes():
            elem = self.elements[idx]
            area = float(l) * float(w)
            vol = area * float(h)
            payload.extend(self._build_payload(elem, area, vol))

        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 4: Re-inflate flat write response into an N x 2 matrix
        # Failed-read elements expand into (UPSTREAM_FAILED, UPSTREAM_FAILED)
        write = valid_elements.project_rows(raw_res, row_length=2)
        run.record("Write Area & Volume", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## Pattern 3: Conditional Domain Filtering ($N \to K$ subset)

### When to use
Use when business rules filter which elements are eligible for mutation (e.g. only modifying Walls with thickness $> 200\text{mm}$, or uncommitted spaces).

### Architectural Behavior
* Elements that do not meet the criteria are classified as **`FILTERED`**.
* In the final report and summary dialog, filtered elements are clearly distinguished from errors:
  > *"15 succeeded; 0 failed; 85 filtered"*
* When retrying, `FILTERED` elements are safely ignored because their exclusion was intentional.

### Variant A: Subset Filtering via `for_items` (Item-First)
Best when filtering domain models using list comprehensions:

```python
from multiconn_archicad.utilities import SlotState

def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read classifications
        read = run.record("Read", self.property_utilities.get_property_values_per_element_result(...))

        # Filter in Python using row properties
        qualifying_elements = [
            elem for elem, row in zip(self.elements, read.rows)
            if row.is_all(SlotState.SUCCESS) and float(row[0].value) > 200.0
        ]

        # Step 2: Execute mutation only on qualifying elements
        write_res = self.property_utilities.set_property_values_per_element_result(
            qualifying_elements, self.write_properties, qualifying_values
        )

        # Record subset step using O(N) duplicate-safe FIFO alignment
        # Elements not in qualifying_elements are marked FILTERED
        run.record("Write", write_res, for_items=qualifying_elements)

    return ExecutionReport(run.report, planned_step_count=2)
```

### Variant B: Subset Filtering via `item_indices` (Index-First Fast Path)
Best when iterating over indexed slots or when avoiding duplicate object resolution entirely:

```python
from multiconn_archicad.utilities import SlotState

def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        read = run.record("Read", self.property_utilities.get_property_values_per_element_result(...))

        # Filter by index
        qualifying_indices = [
            idx for idx, row in enumerate(read.rows)
            if row.is_all(SlotState.SUCCESS) and float(row[0].value) > 200.0
        ]
        qualifying_elements = [self.elements[i] for i in qualifying_indices]

        write_res = self.property_utilities.set_property_values_per_element_result(
            qualifying_elements, self.write_properties, qualifying_values
        )

        # Zero lookup overhead, instant integer mapping:
        run.record("Write", write_res, item_indices=qualifying_indices)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## Pattern 4: Scalar 1D Pipeline ($N \to N$)

### When to use
Use for operations on a single property or scalar attribute across elements.

### Architectural Behavior
* Uses `BatchResult[T]` throughout (length $N$).
* `read.project_successes(...)` maintains 1D alignment and sets `UPSTREAM_FAILED` if the read step failed.

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read a single property across all elements (1D result)
        read = run.record(
            "Read Fire Rating",
            self.property_utilities.get_flat_property_values_result(self.elements, self.prop_fire_rating)
        )

        # Step 2: Transform successful values in Python
        payload = [
            self._to_mutation(self.elements[idx], f"FR-{val}")
            for idx, val in read.iter_successes()
        ]
        raw_res = self.api.tapir.property.set_property_values_of_elements(payload) if payload else []

        # Step 3: Re-inflate flat write response into the original 1D shape
        write = read.project_successes(raw_res)
        run.record("Write Fire Rating", write)

    return ExecutionReport(run.report, planned_step_count=2)
```

---

## Pattern 5: Branching / Heterogeneous Pipelines

### When to use
Use when a batch contains mixed categories that require different pipeline branches (e.g., Walls written in Step 2a, Slabs written in Step 2b).

### Architectural Behavior
* Each branch records its own step with `for_items` or `item_indices`.
* An element that completes its intended branch succeeds cleanly.

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Read types
        read = run.record("Read Types", self.property_utilities.get_flat_property_values_result(...))

        # Partition elements
        walls = [elem for elem, (idx, val) in zip(self.elements, read.iter_successes()) if "Wall" in val]
        slabs = [elem for elem, (idx, val) in zip(self.elements, read.iter_successes()) if "Slab" in val]

        # Step 2a: Process Walls
        if walls:
            res_walls = self.property_utilities.set_flat_property_values_result(walls, self.prop_wall, wall_vals)
            run.record("Write Wall Properties", res_walls, for_items=walls)

        # Step 2b: Process Slabs
        if slabs:
            res_slabs = self.property_utilities.set_flat_property_values_result(slabs, self.prop_slab, slab_vals)
            run.record("Write Slab Properties", res_slabs, for_items=slabs)

    return ExecutionReport(run.report, planned_step_count=3)
```

---

## Pattern 6: Error Inspection, Diagnostics & Selective Retrying

### The Retry Invariant
Never retry blindly. `BatchReport.outcomes` provides explicit predicates:
* **`outcome.failed`**: Produced an error $\to$ **Retry.**
* **`outcome.upstream_failed`**: Blocked by a prerequisite error $\to$ **Retry.**
* **`outcome.filtered`**: Intentionally excluded by domain logic $\to$ **Do NOT retry.**
* **`outcome.succeeded`**: Completed $\to$ **Do NOT retry.**

### Inspecting and Retrying

```python
report = run.finish()

# 1. Filter only retriable candidates
retriable_items = [
    outcome.original_item for outcome in report.outcomes
    if outcome.failed or outcome.upstream_failed
]

# 2. Inspect diagnostics for logs or UI
for outcome in report.outcomes:
    if outcome.failed:
        print(f"Element {outcome.index} failed with {len(outcome.failures)} error(s):")
        for failure in outcome.failures:
            print(f"  - Step '{failure.step_name}' at {failure.source_coordinate}: [{failure.error.code}] {failure.error.message}")
    elif outcome.upstream_failed:
        print(f"Element {outcome.index} was blocked by an upstream dependency failure.")

# 3. Launch an isolated retry run for retriable items
if retriable_items:
    with BatchRun(retriable_items) as retry_run:
        # Re-run pipeline steps on retriable_items only...
        ...
```

### Selecting Failed Elements in Archicad
To highlight failed elements in the Archicad 3D/floor plan view:

```python
from multiconn_archicad.utilities.identifiers import normalize_element_ids

# Unique element IDs of all elements that produced errors
failed_elements = [
    outcome.original_item
    for outcome in report.outcomes
    if outcome.failed or outcome.upstream_failed
]

# Select in CAD
if failed_elements:
    api.tapir.element.change_selection_of_elements(
        add_elements_to_selection=normalize_element_ids(failed_elements)
    )
```

---

## Pattern 7: Safe Exception Handling & Context Manager Contract

`BatchRun` acts as a context manager that handles execution safety:

```python
def run(self) -> ExecutionReport:
    with BatchRun(self.elements) as run:
        # Step 1: Pre-flight validation (raising standard Exception)
        if not self.target_property:
            raise ValueError("Target property must be specified.")

        # Step 2: API calls
        res = self.property_utilities.get_property_values_per_element_result(...)
        run.record("Read", res)

    # Clean exit: run.finish() is called automatically
    # Aborted exit: run.abort(exc) is called automatically and exc is suppressed
    return ExecutionReport(run.report)
```

### How `__exit__` behaves:
1. **Clean exit (`exc is None`):** Automatically closes the run and calls `finish()`. All processed items without errors become `SUCCEEDED`.
2. **Standard `Exception`:** 
   * Caught automatically.
   * Calls `abort(exc)`.
   * Sets `report.fatal_error = exc`.
   * Sets `report.status = BatchStatus.FAILED`.
   * Items that were not completed are marked **`INCOMPLETE`**.
   * The exception is **suppressed** so the caller cleanly falls through to display the fatal error in `ExecutionReport`.
3. **`BaseException` (`KeyboardInterrupt`, `SystemExit`):** Never suppressed; immediately propagates.
