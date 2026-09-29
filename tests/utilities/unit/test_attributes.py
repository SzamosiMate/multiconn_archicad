from __future__ import annotations

from collections.abc import Sequence
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from multiconn_archicad.errors import BatchOperationError
from multiconn_archicad.models.tapir import types as tapir
from multiconn_archicad.utilities.namespaces.attributes import AttributeUtilities


def _attribute_id(value: UUID | None = None) -> tapir.AttributeId:
    return tapir.AttributeId(guid=value or uuid4())


def _header(name: str, attribute_id: tapir.AttributeId | None = None) -> tapir.AttributeHeader:
    return tapir.AttributeHeader(attributeId=attribute_id or _attribute_id(), index=1, name=name, modificationTime=0)


def _combination_layer(
    attribute_id: tapir.AttributeId, *, hidden: bool = False, locked: bool = False
) -> tapir.LayersOfLayerCombinationItem:
    return tapir.LayersOfLayerCombinationItem(
        attributeId=attribute_id,
        isHidden=hidden,
        isLocked=locked,
        isWireframe=False,
        intersectionGroupNr=1,
    )


def _combination(layers: Sequence[tapir.LayersOfLayerCombinationItem]) -> tapir.LayerCombinationAttribute:
    return tapir.LayerCombinationAttribute(
        layerCombination=tapir.LayerCombinationAttributeDetails(
            attributeId=_attribute_id(), name="Plan", layers=list(layers)
        )
    )


def _layer(attribute_id: tapir.AttributeId, name: str) -> tapir.LayerAttribute:
    return tapir.LayerAttribute(attributeId=attribute_id, index=1, name=name)


def _error(message: str) -> tapir.ErrorItem:
    return tapir.ErrorItem(error=tapir.Error(code=7, message=message))


def test_get_layer_names_returns_visible_layers_in_order_and_keeps_locked_layers():
    api = MagicMock()
    combination_id = _attribute_id()
    hidden_id, locked_id, built_in_id = _attribute_id(), _attribute_id(), _attribute_id()
    api.tapir.attribute.get_attributes_by_type.return_value = tapir.AttributeHeadersWrapper(
        attributes=[_header("Other"), _header("Plan", combination_id)]
    )
    api.tapir.attribute.get_layer_combinations.return_value = [
        _combination(
            [
                _combination_layer(hidden_id, hidden=True),
                _combination_layer(locked_id, locked=True),
                _combination_layer(built_in_id),
            ]
        )
    ]
    api.tapir.attribute.get_layers.return_value = [
        _layer(locked_id, "Locked but visible"),
        _layer(built_in_id, "Archicad Built-in Layer"),
    ]

    result = AttributeUtilities(api).get_layer_names_of_combination("Plan")

    assert result == ["Locked but visible", "Archicad Built-in Layer"]
    api.tapir.attribute.get_layer_combinations.assert_called_once_with(
        [tapir.AttributeIdArrayItem(attributeId=combination_id)]
    )
    api.tapir.attribute.get_layers.assert_called_once_with(
        [tapir.AttributeIdArrayItem(attributeId=locked_id), tapir.AttributeIdArrayItem(attributeId=built_in_id)]
    )


def test_get_layers_of_combination_returns_empty_when_no_named_detail_exists():
    api = MagicMock()
    api.tapir.attribute.get_attributes_by_type.return_value = tapir.AttributeHeadersWrapper(
        attributes=[_header("Other")]
    )
    api.tapir.attribute.get_layer_combinations.return_value = []

    assert AttributeUtilities(api).get_layers_of_combination("Plan") == []


def test_get_layer_names_raises_for_a_layer_detail_error():
    api = MagicMock()
    layer_id = _attribute_id()
    api.tapir.attribute.get_attributes_by_type.return_value = tapir.AttributeHeadersWrapper(
        attributes=[_header("Plan")]
    )
    api.tapir.attribute.get_layer_combinations.return_value = [_combination([_combination_layer(layer_id)])]
    api.tapir.attribute.get_layers.return_value = [_error("layers failed")]

    with pytest.raises(BatchOperationError, match="layers failed"):
        AttributeUtilities(api).get_layer_names_of_combination("Plan")
