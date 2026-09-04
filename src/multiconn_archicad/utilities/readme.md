### Naming and Placement

In open-source SDKs and client libraries, there is a clear distinction between **workflow contributions** and **architectural standards**:

* **`CONTRIBUTING.md`** (in repository root): Intended for project setup, running tests, linter commands (Ruff/Black), Git branch naming, and how to submit a Pull Request.
* **Architecture / Design Guidelines**:
  1. **Option A (Recommended): `src/multiconn_archicad/helpers/README.md`**  
     Placing this directly inside the `helpers/` folder means anyone browsing or working on the code sees the architectural contracts immediately.
  2. **Option B: `docs/design/helpers_architecture.md` (or `ARCHITECTURE.md`)**  
     Standard for libraries with comprehensive Sphinx/MkDocs documentation (similar to Azure SDK's *Python Design Guidelines*).

> **Best Practice:** Put the full architecture document at **`src/multiconn_archicad/helpers/README.md`** (or `docs/architecture/helpers.md`), and add a pointer in the root `CONTRIBUTING.md`:
> ```markdown
> ### Contributing to `helpers`
> Before adding or modifying utilities, read the [Helpers Architecture & Style Guide](src/multiconn_archicad/helpers/README.md).
> ```

---

Here is the consolidated, production-ready **Architecture and Style Guide** ready to drop into the repository:

```markdown
# Architecture & Style Guide: `multiconn_archicad.helpers`

This document defines the architectural boundaries, design patterns, and coding conventions for the `helpers` subpackage in `multiconn_archicad`. 

All contributions to `helpers` must adhere to these guidelines.

---

## 1. Mission & Scope

The `helpers` package provides **Level 3 Ergonomic Sugar** on top of `UnifiedApi`.

### What Belongs in `helpers`:
* **Idiomatic Pythonic wrappers** around repetitive Archicad JSON API interactions (e.g., context managers for resource safety).
* **Batch unwrapping and type coercion** (flattening deeply nested property responses into Python primitives).
* **Batch result containers (`BatchResult`)** that preserve 1:1 index alignment while isolating partial failures.
* **Universal identifier constructors and resolvers** (e.g., human-readable name $\to$ `PropertyId`).

### What Does NOT Belong in `helpers`:
* **Domain / Business Logic:** Company-specific layer naming, property names, or pipeline rules belong in downstream applications.
* **Heavy Geometric Engines:** No `shapely`, CAD polygon clipping, or spatial containment routines.
* **IFC Dependencies:** Zero dependencies on `ifcopenshell`. IFC mappings belong in downstream packages (e.g., `ifc_core`).
* **Transport / Protocol Logic:** Low-level HTTP/socket handling belongs in `core` and `UnifiedApi`.

---

## 2. Core API Design Principles

### A. Functions First, Classes by Exception
* **Default to Pure Functions:** 90% of helpers should be stateless, standalone functions.
* **When Classes are Permitted:**
  1. **Resource Lifecycle (Context Managers):** e.g., `TeamworkReserve`.
  2. **Explicit, Opt-In Caching:** e.g., `PropertyDefinitionsCache(api)` to avoid querying definitions multiple times in a single session.
* **No "Active Record" Objects:** Never wrap an Archicad element in a stateful class with instance methods (e.g., `element.get_property()`). This encourages iterative $N+1$ socket calls, severely degrading CAD performance.

### B. Batch-First by Default
Archicad JSON API is optimized for bulk operations. 
* **Rule:** Never design a helper that takes only a single element if a batch equivalent is possible.
* **Always accept sequences:** Accept `Sequence[ElementIdLike]`, not individual IDs.

### C. Immutability & Parameter Typing (Postel's Law)
*"Be liberal in what you accept, and conservative in what you send."*

1. **Input Parameters:**
   * Always annotate collection inputs as read-only abstractions: `Sequence[T]` or `Mapping[K, V]` from `collections.abc`.
   * **Never mutate input parameters.** Never pop, append, or modify input dictionaries/models in-place.
2. **Return Types:**
   * Always return concrete, predictable collections: `list[T]`, `dict[K, V]`, or `BatchResult[T]`.
   * Never return abstract types like `Sequence[T]` or `Iterable[T]`.

### D. Consistent Signatures
Every helper interacting with Archicad **must take `api: UnifiedApi` as its first parameter**:
```python
def helper_name(api: UnifiedApi, elements: Sequence[...], ...) -> BatchResult[...]:
    ...
```

---

## 3. Subpackage Directory Structure

Helpers are organized by **developer intent / domain subject**, **never** by low-level API namespaces (`tapir` vs. `official`):

```text
src/multiconn_archicad/helpers/
├── __init__.py
├── README.md             # This document
├── results.py            # BatchResult and universal error extractor
├── properties.py         # Reading (unwrapping), writing, ID resolution
├── elements.py           # Selection get/set, element filtering
├── teamwork.py           # TeamworkReserve context manager
└── attributes.py         # Composite attribute queries (e.g. layer combinations)
```

---

## 4. Tapir vs. Official Duality

Archicad has both native official commands and Tapir extensions. Helpers bridge this gap seamlessly:

1. **Liberal Inputs (Union TypeAliases):**
   Helpers must accept either representation and coerce internally:
   ```python
   ElementIdLike: TypeAlias = Union[
       tapir_types.ElementIdArrayItem,
       official_types.ElementIdWrapperItem,
       tapir_types.ElementId,
       str,  # GUID string
   ]
   ```
2. **Conservative Outputs:**
   * Default to **`tapir_types`** models for element/property identifiers.
   * For data read operations, unwrap directly to **standard Python primitives** (`str`, `float`, `bool`, `None`), rendering the model duality irrelevant to end callers.

---

## 5. Batch Error Handling: The `BatchResult` Pattern

In batch CAD operations, round-trips are expensive. When 995 of 1,000 operations succeed and 5 fail, throwing a hard exception discards the successes, while silently dropping errors causes off-by-one index alignment bugs.

### The Contract of `BatchResult[T]`
* **Immutability:** A frozen dataclass/value object. It is **not** a `MutableSequence` (no `.append()`, `.pop()`, or in-place mutations).
* **Guaranteed Index Alignment:** `len(result.values) == len(input_elements)`. Failed operations are padded with `None` at their original index.
* **Explicit Errors:** Errors are mapped by input index in `result.errors: Mapping[int, Error]`.
* **Explicit Truthiness:** `bool(result)` evaluates to `True` **only** if there are zero errors (`is_success`).

### Implementation Reference (`results.py`):

```python
from __future__ import annotations
from typing import Generic, TypeVar, Sequence, Mapping, Any, Optional, Callable
from dataclasses import dataclass
from multiconn_archicad.models.tapir import types as tapir_types
from multiconn_archicad.models.official import types as official_types

T = TypeVar("T")

def extract_error(item: Any) -> Optional[tapir_types.Error | official_types.Error]:
    """Duck-typed error extractor supporting both Tapir and Official models."""
    if isinstance(item, (
        tapir_types.FailedExecutionResult,
        tapir_types.ErrorItem,
        official_types.ErrorItem,
    )):
        return getattr(item, "error", None)

    if getattr(item, "success", None) is False and hasattr(item, "error"):
        return item.error

    if hasattr(item, "error") and item.error is not None:
        return item.error

    return None


@dataclass(frozen=True, slots=True)
class BatchResult(Generic[T]):
    values: Sequence[T | None]
    errors: Mapping[int, Any]

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def is_success(self) -> bool:
        return len(self.errors) == 0

    @property
    def successful_values(self) -> list[T]:
        """Returns only the successful items, omitting None/failures."""
        return [v for v in self.values if v is not None]

    def raise_for_errors(self) -> None:
        """Raises a consolidated RuntimeError if any operation in the batch failed."""
        if not self.has_errors:
            return
        details = [f"  - Index {i}: [{getattr(e, 'code', 'ERR')}] {getattr(e, 'message', str(e))}" for i, e in self.errors.items()]
        raise RuntimeError(f"Batch failed with {len(self.errors)} error(s):\n" + "\n".join(details))

    def __bool__(self) -> bool:
        return self.is_success

    @classmethod
    def from_items(
        cls,
        raw_items: Sequence[Any],
        *,
        payload: Optional[Sequence[T]] = None,
        unwrap: Optional[Callable[[Any], T]] = None,
    ) -> BatchResult[T]:
        """
        Universal factory for Archicad batch responses.
        
        - Use `payload` for Writes/Mutations: maps successful positions to input items.
        - Use `unwrap` for Reads/Queries: transforms raw success responses into domain models or primitives.
        """
        values: list[T | None] = []
        errors: dict[int, Any] = {}

        for idx, item in enumerate(raw_items):
            err = extract_error(item)
            if err is not None:
                values.append(None)
                errors[idx] = err
            else:
                if payload is not None:
                    values.append(payload[idx])
                elif unwrap is not None:
                    values.append(unwrap(item))
                else:
                    values.append(item)

        return cls(values=values, errors=errors)
```

---

## 6. Authoring Helpers: Concrete Examples

### A. Writing Data (`payload` Pattern)
Archicad write endpoints return boolean execution acknowledgments (`{"success": true}`). Use `payload` to preserve what was actually written:

```python
# multiconn_archicad/helpers/properties.py

def set_property_values(
    api: UnifiedApi,
    elements: Sequence[tapir_types.ElementIdArrayItem],
    property_id: tapir_types.PropertyIdArrayItem,
    values: Sequence[Any],
) -> BatchResult[tapir_types.ElementPropertyValue]:
    """Sets property values in bulk, returning the ElementPropertyValue items that succeeded."""
    payload = [
        tapir_types.ElementPropertyValue(
            elementId=elem.elementId,
            propertyId=property_id.propertyId,
            propertyValue=tapir_types.PropertyValue(value=str(val) if val is not None else ""),
        )
        for elem, val in zip(elements, values)
    ]

    response = api.tapir.property.set_property_values_of_elements(payload)
    return BatchResult.from_items(response.executionResults, payload=payload)
```

### B. Reading Data (`unwrap` Pattern)
Archicad query endpoints return nested structures. Use `unwrap` to flatten them cleanly:

```python
# multiconn_archicad/helpers/properties.py

def get_property_values(
    api: UnifiedApi,
    elements: Sequence[tapir_types.ElementIdArrayItem],
    properties: Sequence[tapir_types.PropertyIdArrayItem],
) -> BatchResult[list[Any | None]]:
    """Reads properties in bulk, unwrapping them into a 2D matrix [element_idx][property_idx]."""
    raw_response = api.tapir.property.get_property_values_of_elements(list(elements), list(properties))

    def _unwrap_element_props(elem_wrapper: Any) -> list[Any | None]:
        row: list[Any | None] = []
        for prop in getattr(elem_wrapper, "propertyValues", []):
            if extract_error(prop) or not prop.propertyValue:
                row.append(None)
            else:
                row.append(prop.propertyValue.value)
        return row

    return BatchResult.from_items(raw_response, unwrap=_unwrap_element_props)
```

### C. Resource Lifecycle (Context Manager)
Always clean up resources and handle Teamwork synchronization on exit:

```python
# multiconn_archicad/helpers/teamwork.py

class TeamworkReserve:
    """Context manager ensuring reserved elements are released and changes are sent."""
    def __init__(
        self,
        api: UnifiedApi,
        elements: Sequence[tapir_types.ElementIdArrayItem],
        auto_send: bool = True,
    ):
        self.api = api
        self.elements = list(elements)
        self.auto_send = auto_send

    def __enter__(self) -> TeamworkReserve:
        self.result = self.api.tapir.teamwork.reserve_elements(self.elements)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.api.tapir.teamwork.release_elements(self.elements)
        if self.auto_send:
            self.api.tapir.teamwork.teamwork_send()
```
```