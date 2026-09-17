from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

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
from multiconn_archicad.utilities.results import BatchResult, BatchResult2D, extract_error

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


def _extract_property_value(item: tapir.PropertyValueArrayItem) -> str:
    return item.propertyValue.value


def _to_prop_value(val: Any) -> tapir.PropertyValue:
    return val if isinstance(val, tapir.PropertyValue) else tapir.PropertyValue(value="" if val is None else str(val))


def _validate_matrix_input(
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike], values_matrix: Sequence[Sequence[Any]]
) -> tuple[list[tapir.ElementIdArrayItem], list[tapir.PropertyIdArrayItem]]:
    """Validate caller-owned dimensions and typed input errors for a dense write."""
    norm_elements = normalize_element_ids(elements)
    norm_properties = normalize_property_ids(properties)
    if len(norm_elements) != len(values_matrix):
        raise ValueError(f"Expected {len(norm_elements)} rows in values_matrix, got {len(values_matrix)}.")
    expected_length = len(norm_properties)
    for row_index, row in enumerate(values_matrix):
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise TypeError(f"Row {row_index} in values_matrix must be a sequence.")
        if len(row) != expected_length:
            raise ValueError(f"Expected {expected_length} values per row, got {len(row)} at row {row_index}.")
    BatchResult2D.from_rows(values_matrix, width=expected_length).raise_for_errors(
        "Property write input"
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
    elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike], values_matrix: Sequence[Sequence[Any]]
) -> list[tapir.ElementPropertyValue]:
    """Build an N x M payload using display strings.

    PropertyValue models pass through; None becomes an empty string and other
    values use str(value). No numeric formatting or unit conversion is performed.
    Typed API errors are rejected before conversion.
    """
    norm_elements, norm_props = _validate_matrix_input(elements, properties, values_matrix)

    payload: list[tapir.ElementPropertyValue] = []
    for elem, row in zip(norm_elements, values_matrix):
        for prop, val in zip(norm_props, row):
            payload.append(
                tapir.ElementPropertyValue(
                    elementId=elem.elementId,
                    propertyId=prop.propertyId,
                    propertyValue=_to_prop_value(val),
                )
            )
    return payload


def create_element_property_values_flat(
    elements: Sequence[ElementIdLike], property_id: PropertyIdLike, values: Sequence[Any]
) -> list[tapir.ElementPropertyValue]:
    """Build a single-property payload using display strings.

    PropertyValue models pass through; None becomes an empty string and other
    values use str(value). No numeric formatting or unit conversion is performed.
    Typed API errors are rejected before conversion.
    """
    pid = normalize_property_id(property_id).propertyId
    norm_elements = _validate_flat_input(elements, values)
    return [
        tapir.ElementPropertyValue(elementId=e.elementId, propertyId=pid, propertyValue=_to_prop_value(v))
        for e, v in zip(norm_elements, values)
    ]


def create_element_property_values_sparse(
    elements: Sequence[ElementIdLike],
    properties: Sequence[PropertyIdLike],
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any],
) -> list[tapir.ElementPropertyValue]:
    """Build a sparse payload from a matrix, omitting typed error cells and rows."""
    norm_elements = normalize_element_ids(elements)
    norm_props = normalize_property_ids(properties)
    matrix = _coerce_property_matrix(values_matrix, len(norm_elements), len(norm_props))

    return [
        tapir.ElementPropertyValue(
            elementId=norm_elements[elem_idx].elementId,
            propertyId=norm_props[prop_idx].propertyId,
            propertyValue=_to_prop_value(value),
        )
        for (elem_idx, prop_idx), value in matrix.iter_successes()
    ]


def _coerce_property_matrix(
    values_matrix: Sequence[Sequence[Any]] | BatchResult2D[Any], expected_rows: int, expected_width: int,
) -> BatchResult2D[Any]:
    """Validate grid dimensions and coerce raw rows or BatchResult2D into a verified BatchResult2D."""
    if expected_width <= 0:
        raise ValueError("At least one property must be specified.")

    if isinstance(values_matrix, BatchResult2D):
        if len(values_matrix.rows) != expected_rows:
            raise ValueError(
                f"Expected {expected_rows} rows in values_matrix, got {len(values_matrix.rows)}."
            )
        for row_index, row in enumerate(values_matrix.rows):
            if len(row) != expected_width:
                raise ValueError(
                    f"Row {row_index} contains {len(row)} values, expected {expected_width}."
                )
        return values_matrix

    if len(values_matrix) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} rows in values_matrix, got {len(values_matrix)}."
        )

    return BatchResult2D.from_rows(values_matrix, width=expected_width)


def get_possible_enum_values(property_definition: official.PropertyDefinition) -> list[str]:
    """Extracts allowed enum display strings from an Official PropertyDefinition."""
    if not property_definition.possibleEnumValues:
        return []
    return [item.enumValue.displayValue for item in property_definition.possibleEnumValues]


class PropertyUtilities:
    """Batch property operations bound to one UnifiedApi instance.

    Holds only the API reference; property data is not cached. Reads return Tapir
    display strings. Pure payload builders and extractors remain module functions.
    """

    def __init__(self, api: UnifiedApi):
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
        """Diagnostic batch lookup returning a BatchResult container."""
        raw = self._api.official.property.get_property_ids(list(property_user_ids))
        return BatchResult.from_items(raw, accessor=normalize_property_id)

    def resolve_property_ids(self, property_user_ids: Sequence[PropertyUserId]) -> list[tapir.PropertyIdArrayItem]:
        """Fail-fast batch lookup returning a clean list of Tapir PropertyId models."""
        res = self.resolve_property_ids_result(property_user_ids)
        res.raise_for_errors("Property ID resolution")
        return list(res.successes)

    def resolve_property_id(self, property_user_id: PropertyUserId) -> tapir.PropertyIdArrayItem:
        """Scalar convenience: resolves a single property identifier or raises."""
        return self.resolve_property_ids([property_user_id])[0]

    def get_property_values_per_element_result(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike]
    ) -> BatchResult2D[str]:
        """Read display strings: one row per element, with nested ErrorItems on failure."""
        items = self._get_raw_property_values(elements, properties)
        rows = [item if extract_error(item) else item.propertyValues for item in items]
        return BatchResult2D.from_rows(rows, width=len(properties), accessor=_extract_property_value)

    def get_property_values_per_element(
        self, elements: Sequence[ElementIdLike], properties: Sequence[PropertyIdLike]
    ) -> list[list[str]]:
        """Read an N x M matrix of display strings; raise on any reported failure.

        Values are not parsed as numbers or converted to standard units.
        """
        res = self.get_property_values_per_element_result(elements, properties)
        res.raise_for_errors("Batch property values read")
        return [[slot.success_value for slot in row] for row in res.rows]

    def get_flat_property_values_result(
        self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike
    ) -> BatchResult[str]:
        """Read one property as display strings, retaining per-element failures."""
        property_values = self._get_raw_property_values(elements, [property_id])
        items = [item if extract_error(item) else item.propertyValues[0] for item in property_values]
        return BatchResult.from_items(items, accessor=_extract_property_value)

    def get_flat_property_values(self, elements: Sequence[ElementIdLike], property_id: PropertyIdLike) -> list[str]:
        """Read one property as display strings; raise on any reported failure.

        Values are not parsed as numbers or converted to standard units.
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
        """Read property rows as dictionaries, aggregating each failed row.

        A row is all-or-nothing in this representation. The detailed matrix
        result remains available from ``get_property_values_per_element_result``;
        this convenience folds every cell or row failure into one error slot.
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
        """Read complete property rows into dictionaries; raise on failed rows."""
        res = self.get_property_values_dict_per_element_result(elements, properties, property_names)
        res.raise_for_errors("Property dictionary read")
        return res.successes

    def set_property_values_per_element_result(
        self,
        elements: Sequence[ElementIdLike],
        properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]],
    ) -> BatchResult2D[tapir.SuccessfulExecutionResult]:
        """Write display values, returning one execution-result row per element.

        Each row contains one success or failure per requested property. Partial
        failures are retained; successful writes are not rolled back by this helper.
        Values follow create_element_property_values conversion rules.
        """
        n_props = len(properties)
        payload = create_element_property_values(elements, properties, values_matrix)
        raw_res = self._api.tapir.property.set_property_values_of_elements(payload)
        grouped = [raw_res[i * n_props : (i + 1) * n_props] for i in range(len(elements))]
        return BatchResult2D.from_rows(grouped, width=n_props)

    def set_property_values_per_element(
        self,
        elements: Sequence[ElementIdLike],
        properties: Sequence[PropertyIdLike],
        values_matrix: Sequence[Sequence[Any]],
    ) -> int:
        """Write an N x M matrix of display values; raise on any reported failure.

        Returns the count of written property values when all succeed. Errors are
        checked after the batch executes; successful writes are not rolled back by
        this helper when BatchOperationError is raised. This is not an atomic write.
        """
        res = self.set_property_values_per_element_result(elements, properties, values_matrix)
        res.raise_for_errors("Batch property values write")
        return len(elements) * len(properties)

    def set_flat_property_values_result(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: Sequence[Any],
    ) -> BatchResult[tapir.SuccessfulExecutionResult]:
        """Write one property, retaining per-element success and failure results.

        Values follow create_element_property_values_flat conversion rules.
        Successful writes are not rolled back by this helper on partial failure.
        """
        payload = create_element_property_values_flat(elements, property_id, values)
        raw_res = self._api.tapir.property.set_property_values_of_elements(payload)
        return BatchResult.from_items(raw_res)

    def set_flat_property_values(
        self,
        elements: Sequence[ElementIdLike],
        property_id: PropertyIdLike,
        values: Sequence[Any],
    ) -> int:
        """Write one property across elements; raise on any reported failure.

        Returns the count of written property values when all succeed. Errors are
        checked after the batch executes; successful writes are not rolled back by
        this helper when BatchOperationError is raised. This is not an atomic write.
        """
        res = self.set_flat_property_values_result(elements, property_id, values)
        res.raise_for_errors("Single property write")
        return len(res.successes)

    def get_property_details_result(
        self, properties: Sequence[PropertyIdLike]
    ) -> BatchResult[official.PropertyDefinition]:
        """Diagnostic metadata lookup returning a BatchResult container."""
        property_definitions = self._api.official.property.get_details_of_properties(
            [to_official_property_id(p) for p in properties]
        )
        return BatchResult.from_items(property_definitions, accessor=lambda item: item.propertyDefinition)

    def get_property_details(self, properties: Sequence[PropertyIdLike]) -> list[official.PropertyDefinition]:
        """Fail-fast metadata lookup returning a clean list of PropertyDefinition models."""
        res = self.get_property_details_result(properties)
        res.raise_for_errors("Property details inspection")
        return list(res.successes)

    def get_property_types_result(self, properties: Sequence[PropertyIdLike]) -> BatchResult[str]:
        """Diagnostic data type names lookup returning a BatchResult container."""
        return self.get_property_details_result(properties).map(lambda d: d.type)

    def get_property_types(self, properties: Sequence[PropertyIdLike]) -> list[str]:
        """Fail-fast data type names lookup returning a clean list of type name strings."""
        res = self.get_property_types_result(properties)
        res.raise_for_errors("Property types inspection")
        return list(res.successes)
