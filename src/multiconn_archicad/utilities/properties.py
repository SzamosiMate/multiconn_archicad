"""Read, write, and inspect property values and metadata."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from multiconn_archicad.errors import BatchWriteError
from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.identifiers import (
    ElementIdLike,
    PropertyIdLike,
    PropertyUserId,
    normalize_element_ids,
    normalize_property_id,
    normalize_property_ids,
    to_official_property_id,
)
from multiconn_archicad.utilities.results import (
    BatchGrid,
    BatchResult,
    BatchResult2D,
    BatchRow,
    SlotState,
    extract_error,
)

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


def _extract_property_value(item: tapir.PropertyValueArrayItem) -> str:
    return item.propertyValue.value


def _to_prop_value(val: Any) -> tapir.PropertyValue:
    return val if isinstance(val, tapir.PropertyValue) else tapir.PropertyValue(value="" if val is None else str(val))


def _coerce_property_matrix(
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any], expected_rows: int, expected_width: int,
) -> BatchGrid[Any]:
    """Validate grid dimensions and coerce raw rows or BatchResult2D into a verified BatchGrid."""
    if expected_width <= 0:
        raise ValueError("At least one property must be specified.")

    if isinstance(values_matrix, BatchResult2D):
        if len(values_matrix.rows) != expected_rows:
            raise ValueError(f"Expected {expected_rows} rows in values_matrix, got {len(values_matrix.rows)}.")
        for row_index, row in enumerate(values_matrix.rows):
            if len(row) != expected_width:
                raise ValueError(f"Row {row_index} contains {len(row)} values, expected {expected_width}.")
        return values_matrix if isinstance(values_matrix, BatchGrid) else BatchGrid(values_matrix.rows, width=expected_width)

    if len(values_matrix) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows in values_matrix, got {len(values_matrix)}.")

    for row_index, row in enumerate(values_matrix):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise TypeError(f"Row {row_index} in values_matrix must be a sequence.")
        if len(row) != expected_width:
            raise ValueError(f"Expected {expected_width} values per row, got {len(row)} at row {row_index}.")

    return BatchGrid.from_rows(values_matrix, width=expected_width)


def _validate_and_coerce_matrix(
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any], *, allow_errors: bool = True,
) -> tuple[list[tapir.ElementIdArrayItem], list[tapir.PropertyIdArrayItem], BatchGrid[Any]]:
    """Centralized validation of identifiers and dimensions, coercing values to a verified BatchGrid."""
    norm_elements = normalize_element_ids(elements)
    norm_properties = normalize_property_ids(properties)
    matrix = _coerce_property_matrix(values_matrix, len(norm_elements), len(norm_properties))
    if not allow_errors:
        matrix.raise_for_non_success("Dense property write input")
    return norm_elements, norm_properties, matrix


def _validate_matrix_input(
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
) -> tuple[list[tapir.ElementIdArrayItem], list[tapir.PropertyIdArrayItem]]:
    """Validate dimensions and successful cell states for a dense write."""
    norm_elements, norm_properties, _ = _validate_and_coerce_matrix(
        elements, properties, values_matrix, allow_errors=False
    )
    return norm_elements, norm_properties


def _validate_flat_input(elements: Sequence[ElementIdLike], values: Sequence[Any]) -> list[tapir.ElementIdArrayItem]:
    """Validate caller-owned dimensions and typed input errors for a flat write."""
    norm_elements = normalize_element_ids(elements)
    if len(norm_elements) != len(values):
        raise ValueError(f"Expected {len(norm_elements)} rows in values, got {len(values)}.")
    BatchResult.from_items(values).raise_for_errors("Property write input")
    return norm_elements


def _property_dict_keys(properties: Sequence[PropertyIdLike], property_names: Sequence[str] | None) -> list[str]:
    keys = (
        list(property_names)
        if property_names is not None
        else [str(normalize_property_id(property_id).propertyId.guid) for property_id in properties]
    )
    if len(keys) != len(properties):
        raise ValueError("property_names length must match properties length.")
    return keys


def create_element_property_values(
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
) -> list[tapir.ElementPropertyValue]:
    """Build a row-major payload for every element and property pair.

    Args:
        elements: Element IDs defining matrix rows.
        properties: Property IDs defining matrix columns.
        values_matrix: One value per element and property, as rows or a 2D
            result. Every cell must be successful.

    Returns:
        Payload items ordered by element, then property.

    Raises:
        ValueError: If matrix dimensions do not match the identifiers or no
            properties are supplied.
        BatchNotFullySuccessfulError: If any input cell is not successful.

    Notes:
        Existing ``PropertyValue`` models pass through. ``None`` becomes an
        empty string; other values use ``str`` without numeric formatting or
        unit conversion. All non-success input cells are rejected.
    """
    norm_elements, norm_props, matrix = _validate_and_coerce_matrix(
        elements, properties, values_matrix, allow_errors=False
    )

    payload: list[tapir.ElementPropertyValue] = []
    for elem_idx, row in enumerate(matrix.rows):
        for prop_idx, slot in enumerate(row.slots):
            payload.append(
                tapir.ElementPropertyValue(
                    elementId=norm_elements[elem_idx].elementId,
                    propertyId=norm_props[prop_idx].propertyId,
                    propertyValue=_to_prop_value(slot.value),
                )
            )
    return payload


def create_element_property_values_flat(
    elements: Sequence[ElementIdLike], property_id: PropertyIdLike, values: Sequence[Any]
) -> list[tapir.ElementPropertyValue]:
    """Build a payload for one property across the supplied elements.

    Args:
        elements: Element IDs in payload order.
        property_id: Property ID applied to each element.
        values: One value per element.

    Returns:
        Payload items in element order.

    Raises:
        ValueError: If there is not one value per element.
        BatchOperationError: If a value is a typed API error.

    Notes:
        Existing ``PropertyValue`` models pass through. ``None`` becomes an
        empty string; other values use ``str`` without numeric formatting or
        unit conversion. Typed API errors are rejected.
    """
    pid = normalize_property_id(property_id).propertyId
    norm_elements = _validate_flat_input(elements, values)
    return [
        tapir.ElementPropertyValue(elementId=e.elementId, propertyId=pid, propertyValue=_to_prop_value(v))
        for e, v in zip(norm_elements, values)
    ]


def create_element_property_values_sparse(
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
) -> list[tapir.ElementPropertyValue]:
    """Build a sparse row-major payload from successful matrix cells.

    Args:
        elements: Element IDs defining matrix rows.
        properties: Property IDs defining matrix columns.
        values_matrix: Rows or a 2D result aligned with the IDs.

    Returns:
        Payload items for successful cells only, ordered by element and then
        property. Error, upstream-failed, and filtered cells are omitted.

    Notes:
        Value conversion follows ``create_element_property_values``.
    """
    norm_elements, norm_props, matrix = _validate_and_coerce_matrix(
        elements, properties, values_matrix, allow_errors=True
    )

    return [
        tapir.ElementPropertyValue(
            elementId=norm_elements[elem_idx].elementId,
            propertyId=norm_props[prop_idx].propertyId,
            propertyValue=_to_prop_value(value),
        )
        for (elem_idx, prop_idx), value in matrix.iter_successes()
    ]


def get_possible_enum_values(property_definition: official.PropertyDefinition) -> list[str]:
    """Return allowed enum display strings from a property definition.

    Return an empty list when the definition has no enum values.
    """
    if not property_definition.possibleEnumValues:
        return []
    return [item.enumValue.displayValue for item in property_definition.possibleEnumValues]


class PropertyUtilities:
    """Read, write, and inspect properties through one Unified API instance.

    Property reads return Archicad display strings without parsing or unit
    conversion. Property data is not cached.
    """

    def __init__(self, api: UnifiedApi):
        """Bind property operations to ``api``."""
        self._api = api

    def _get_raw_property_values(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike]
    ) -> list[tapir.ErrorItem | tapir.PropertyValuesArrayItem]:
        return self._api.tapir.property.get_property_values_of_elements(
            normalize_element_ids(elements), normalize_property_ids(properties)
        )

    def resolve_property_ids_result(
        self, property_user_ids: Sequence[PropertyUserId]
    ) -> BatchResult[tapir.PropertyIdArrayItem]:
        """Resolve property user IDs while retaining per-ID lookup failures.

        Args:
            property_user_ids: Built-in or user-defined property identifiers.

        Returns:
            A 1D result aligned with ``property_user_ids``.
        """
        raw = self._api.official.property.get_property_ids(list(property_user_ids))
        return BatchResult.from_items(raw, accessor=normalize_property_id)

    def resolve_property_ids(self, property_user_ids: Sequence[PropertyUserId]) -> list[tapir.PropertyIdArrayItem]:
        """Resolve property user IDs and return their Tapir IDs.

        Args:
            property_user_ids: Built-in or user-defined property identifiers.

        Raises:
            BatchOperationError: If Archicad reports a lookup failure.
        """
        res = self.resolve_property_ids_result(property_user_ids)
        res.raise_for_errors("Property ID resolution")
        return list(res.successes)

    def resolve_property_id(self, property_user_id: PropertyUserId) -> tapir.PropertyIdArrayItem:
        """Resolve one property user ID to a Tapir property ID.

        Raises:
            BatchOperationError: If Archicad reports a lookup failure.
        """
        return self.resolve_property_ids([property_user_id])[0]

    def get_property_values_per_element_result(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike]
    ) -> BatchGrid[str]:
        """Read a grid of property display strings, retaining API failures.

        Args:
            elements: Element IDs defining result rows.
            properties: Property IDs defining result columns.

        Returns:
            A rectangular grid of returned element outcomes. Whole-row API
            failures fill their row with errors; property errors remain in
            their cells. For nonempty element input, rows align with elements.

        Notes:
            Values remain display strings; they are not parsed or converted to
            standard units. Archicad is queried even when ``elements`` is empty.

        Raises:
            ValueError: If no properties are supplied.
        """
        items = self._get_raw_property_values(elements, properties)
        rows = [item if extract_error(item) else item.propertyValues for item in items]
        return BatchGrid.from_rows(rows, width=len(properties), accessor=_extract_property_value)

    def get_property_values_per_element(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike]
    ) -> list[list[str]]:
        """Read property display strings as a list of rows.

        Args:
            elements: Element IDs defining result rows.
            properties: Property IDs defining result columns.

        Returns:
            An N x M list aligned by element and property.

        Raises:
            ValueError: If no properties are supplied.
            BatchOperationError: If Archicad reports any row or cell error.

        Notes:
            Values remain display strings; they are not parsed or converted to
            standard units.
        """
        res = self.get_property_values_per_element_result(elements, properties)
        res.raise_for_errors("Batch property values read")
        return [[slot.value for slot in row] for row in res.rows]

    def get_flat_property_values_result(
        self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike
    ) -> BatchResult[str]:
        """Read one property's display string for each element.

        Args:
            elements: Element IDs in result order.
            property_id: Property to read.

        Returns:
            A 1D result containing returned per-element outcomes; API failures
            remain error slots.

        Notes:
            Values remain display strings; they are not parsed or converted to
            standard units. Archicad is queried even when ``elements`` is empty.
        """
        property_values = self._get_raw_property_values(elements, [property_id])
        items = [item if extract_error(item) else item.propertyValues[0] for item in property_values]
        return BatchResult.from_items(items, accessor=_extract_property_value)

    def get_flat_property_values(self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike) -> list[str]:
        """Read one property's display string for each element.

        Args:
            elements: Element IDs in result order.
            property_id: Property to read.

        Returns:
            Display strings in element order.

        Raises:
            BatchOperationError: If Archicad reports a per-element error.

        Notes:
            Values remain display strings; they are not parsed or converted to
            standard units.
        """
        res = self.get_flat_property_values_result(elements, property_id)
        res.raise_for_errors("Single property read")
        return res.successes

    def get_property_values_dict_per_element_result(
        self,
        elements: Sequence[ElementIdLike],
        properties: Sequence[PropertyIdLike],
        property_names: Sequence[str] | None = None,
    ) -> BatchResult[dict[str, str]]:
        """Read property values into one dictionary per element.

        Args:
            elements: Element IDs defining result rows.
            properties: Property IDs defining dictionary values.
            property_names: Keys in property order. When omitted, use property
                GUID strings.

        Returns:
            A 1D result aligned with ``elements``. Each successful row becomes
            a dictionary from the supplied keys and values; duplicate keys
            overwrite earlier values. A row or cell failure becomes one
            aggregate error slot. Use
            ``get_property_values_per_element_result`` to inspect cells.
        """
        keys = _property_dict_keys(properties, property_names)
        matrix = self.get_property_values_per_element_result(elements, properties)
        return matrix.aggregate_rows().map(lambda values: dict(zip(keys, values)))

    def get_property_values_dict_per_element(
        self,
        elements: Sequence[ElementIdLike],
        properties: Sequence[PropertyIdLike],
        property_names: Sequence[str] | None = None,
    ) -> list[dict[str, str]]:
        """Read one complete property dictionary per element.

        Args:
            elements: Element IDs defining result order.
            properties: Property IDs defining dictionary values.
            property_names: Keys in property order, or property GUID strings
                when omitted.

        Raises:
            BatchOperationError: If any element row contains a property error.
        """
        res = self.get_property_values_dict_per_element_result(elements, properties, property_names)
        res.raise_for_errors("Property dictionary read")
        return res.successes

    def set_property_values_per_element_result(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
    ) -> BatchGrid[tapir.SuccessfulExecutionResult]:
        """Write a dense matrix of property display values.

        Args:
            elements: Element IDs defining result rows.
            properties: Property IDs defining result columns.
            values_matrix: One value per element and property. Every input cell
                must be successful.

        Returns:
            A rectangular grid aligned by element and property. API failures
            remain in the affected cells. Empty element input returns an empty
            grid and does not send a write request when properties are supplied.

        Raises:
            ValueError: If no properties are supplied or matrix dimensions do
                not match the identifiers.
            BatchNotFullySuccessfulError: If any input cell is not successful.

        Notes:
            Successful writes are not rolled back when another cell fails.
            Value conversion follows ``create_element_property_values``.
        """
        n_props = len(properties)
        payload = create_element_property_values(elements, properties, values_matrix)
        raw_res = self._api.tapir.property.set_property_values_of_elements(payload) if payload else []
        grouped = [raw_res[i * n_props : (i + 1) * n_props] for i in range(len(elements))]
        return BatchGrid.from_rows(grouped, width=n_props)

    def set_property_values_per_element(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
    ) -> None:
        """Write a dense matrix of property display values.

        Args:
            elements: Element IDs defining matrix rows.
            properties: Property IDs defining matrix columns.
            values_matrix: One value per element and property. Every input cell
                must be successful.

        Raises:
            BatchWriteError: If Archicad reports a failed write.

        Notes:
            Writes are not atomic. Successful cells are not rolled back if a
            different cell fails.
        """
        res = self.set_property_values_per_element_result(elements, properties, values_matrix)
        if res.has(SlotState.ERROR):
            raise BatchWriteError("Batch property values write", res)

    def set_property_values_per_element_sparse_result(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
    ) -> BatchGrid[tapir.SuccessfulExecutionResult]:
        """Write successful cells from a sparse property-value matrix.

        Args:
            elements: Element IDs defining result rows.
            properties: Property IDs defining result columns.
            values_matrix: Rows or a 2D result aligned with the IDs.

        Returns:
            A grid aligned with the input. API outcomes fill attempted cells;
            input errors become upstream-failed and filtered cells stay
            filtered. If no cell is successful, no write request is sent.

        Raises:
            ValueError: If no properties are supplied or matrix dimensions do
                not match the identifiers.

        Notes:
            Successful writes are not rolled back when another cell fails.
        """
        norm_elements, norm_props, matrix = _validate_and_coerce_matrix(
            elements, properties, values_matrix, allow_errors=True
        )
        payload = create_element_property_values_sparse(norm_elements, norm_props, matrix)
        raw_res = self._api.tapir.property.set_property_values_of_elements(payload) if payload else []
        return matrix.project_successes(raw_res)

    def set_property_values_per_element_sparse(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
    ) -> None:
        """Write successful cells from a sparse property-value matrix.

        Args:
            elements: Element IDs defining matrix rows.
            properties: Property IDs defining matrix columns.
            values_matrix: Rows or a 2D result aligned with the IDs.

        Raises:
            BatchWriteError: If Archicad reports a failed attempted write.

        Notes:
            All non-success input cells are omitted from the request. Writes are
            not atomic; successful cells are not rolled back if another fails.
        """
        res = self.set_property_values_per_element_sparse_result(elements, properties, values_matrix)
        if res.has(SlotState.ERROR):
            raise BatchWriteError("Sparse batch property values write", res)

    def set_flat_property_values_result(
        self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike, values: Sequence[Any],
    ) -> BatchResult[tapir.SuccessfulExecutionResult]:
        """Write one property's display value for each element.

        Args:
            elements: Element IDs defining result order.
            property_id: Property to write.
            values: One value per element.

        Returns:
            A 1D result aligned with ``elements``. API failures remain error
            slots. Empty input returns an empty result without sending a write.

        Notes:
            Successful writes are not rolled back if another write fails.
            Value conversion follows ``create_element_property_values_flat``.
        """
        payload = create_element_property_values_flat(elements, property_id, values)
        raw_res = self._api.tapir.property.set_property_values_of_elements(payload) if payload else []
        return BatchResult.from_items(raw_res)

    def set_flat_property_values_sparse_result(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: BatchResult[Any],
    ) -> BatchResult[tapir.SuccessfulExecutionResult]:
        """Write successful values and preserve the input slot positions.

        Args:
            elements: Element IDs aligned with ``values``.
            property_id: Property to write.
            values: Per-element values and states.

        Returns:
            A 1D result aligned with ``elements``. Successful inputs receive API
            outcomes. Input errors and upstream failures become upstream-failed;
            filtered slots remain filtered. If no input slot succeeds, no write
            request is sent.

        Raises:
            ValueError: If the number of values does not match the elements.

        Notes:
            Successful writes are not rolled back if another write fails.
        """
        matrix = BatchGrid(
            tuple(BatchRow((slot,)) for slot in values.slots),
            width=1,
        )
        return self.set_property_values_per_element_sparse_result(
            elements, [property_id], matrix
        ).flatten()

    def set_flat_property_values_sparse(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: BatchResult[Any],
    ) -> None:
        """Write successful values from a 1D result.

        Args:
            elements: Element IDs aligned with ``values``.
            property_id: Property to write.
            values: Per-element values and states.

        Raises:
            BatchWriteError: If Archicad reports a failed attempted write.

        Notes:
            All non-success input slots are skipped. Writes are not atomic;
            successful values are not rolled back if another write fails.
        """
        res = self.set_flat_property_values_sparse_result(elements, property_id, values)
        if res.has(SlotState.ERROR):
            raise BatchWriteError("Sparse single property write", res)

    def set_flat_property_values(
        self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike, values: Sequence[Any],
    ) -> None:
        """Write one property's display value for each element.

        Args:
            elements: Element IDs in write order.
            property_id: Property to write.
            values: One value per element.

        Raises:
            BatchWriteError: If Archicad reports a failed write.

        Notes:
            Writes are not atomic. Successful values are not rolled back if
            another write fails.
        """
        res = self.set_flat_property_values_result(elements, property_id, values)
        if res.has(SlotState.ERROR):
            raise BatchWriteError("Single property write", res)

    def get_property_details_result(
        self, properties: Sequence[PropertyIdLike]
    ) -> BatchResult[official.PropertyDefinition]:
        """Look up property definitions while retaining per-property failures.

        Args:
            properties: Property IDs in result order.

        Returns:
            A 1D result aligned with ``properties``.
        """
        property_definitions = self._api.official.property.get_details_of_properties(
            [to_official_property_id(p) for p in properties]
        )
        return BatchResult.from_items(property_definitions, accessor=lambda item: item.propertyDefinition)

    def get_property_details(self, properties: Sequence[PropertyIdLike]) -> list[official.PropertyDefinition]:
        """Return property definitions in input order.

        Args:
            properties: Property IDs to inspect.

        Raises:
            BatchOperationError: If Archicad reports a lookup failure.
        """
        res = self.get_property_details_result(properties)
        res.raise_for_errors("Property details inspection")
        return list(res.successes)

    def get_property_types_result(self, properties: Sequence[PropertyIdLike]) -> BatchResult[str]:
        """Look up property type names while retaining per-property failures.

        Args:
            properties: Property IDs in result order.

        Returns:
            A 1D result aligned with ``properties``.
        """
        return self.get_property_details_result(properties).map(lambda d: d.type)

    def get_property_types(self, properties: Sequence[PropertyIdLike]) -> list[str]:
        """Return property type names in input order.

        Args:
            properties: Property IDs to inspect.

        Raises:
            BatchOperationError: If Archicad reports a lookup failure.
        """
        res = self.get_property_types_result(properties)
        res.raise_for_errors("Property types inspection")
        return list(res.successes)
