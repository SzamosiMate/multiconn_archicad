"""Normalize element, property, and attribute identifiers across API models."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Union
from uuid import UUID

from multiconn_archicad.models.official import types as official
from multiconn_archicad.models.tapir import types as tapir

# ==============================================================================
# Liberal Input Type Aliases
# ==============================================================================

ElementIdLike = Union[
    tapir.ElementIdArrayItem,
    official.ElementIdArrayItem,
    tapir.ElementId,
    official.ElementId,
    str,
    UUID,
]

PropertyIdLike = Union[
    tapir.PropertyIdArrayItem,
    official.PropertyIdArrayItem,
    tapir.PropertyId,
    official.PropertyId,
    str,
    UUID,
]

AttributeIdLike = Union[
    tapir.AttributeIdArrayItem,
    official.AttributeIdWrapperItem,
    tapir.AttributeId,
    official.AttributeId,
    str,
    UUID,
]

PropertyUserId = Union[
    official.UserDefinedPropertyUserId,
    official.BuiltInPropertyUserId,
]


# ==============================================================================
# Identifier Normalizers
# ==============================================================================


def _to_uuid(val: str | UUID) -> UUID:
    return val if isinstance(val, UUID) else UUID(str(val).strip())


def normalize_element_id(element: ElementIdLike) -> tapir.ElementIdArrayItem:
    """Convert an element identifier to a Tapir array-item model.

    Args:
        element: A supported Tapir or Official ID model, UUID, or UUID string.

    Raises:
        TypeError: If ``element`` is not a supported identifier type.
        ValueError: If a string is not a valid UUID.
    """
    if isinstance(element, tapir.ElementIdArrayItem):
        return element
    if isinstance(element, official.ElementIdArrayItem):
        return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=element.elementId.guid))
    if isinstance(element, (tapir.ElementId, official.ElementId)):
        return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=element.guid))
    if isinstance(element, (UUID, str)):
        return tapir.ElementIdArrayItem(elementId=tapir.ElementId(guid=_to_uuid(element)))
    raise TypeError(f"Unsupported element ID type: {type(element)!r}")


def normalize_element_ids(elements: Sequence[ElementIdLike]) -> list[tapir.ElementIdArrayItem]:
    """Convert element identifiers to Tapir array-item models in input order."""
    return [normalize_element_id(e) for e in elements]


def normalize_property_id(property_id: PropertyIdLike) -> tapir.PropertyIdArrayItem:
    """Convert a property identifier to a Tapir array-item model.

    Args:
        property_id: A supported Tapir or Official ID model, UUID, or UUID string.

    Raises:
        TypeError: If ``property_id`` is not a supported identifier type.
        ValueError: If a string is not a valid UUID.
    """
    if isinstance(property_id, tapir.PropertyIdArrayItem):
        return property_id
    if isinstance(property_id, official.PropertyIdArrayItem):
        return tapir.PropertyIdArrayItem(propertyId=tapir.PropertyId(guid=property_id.propertyId.guid))
    if isinstance(property_id, (tapir.PropertyId, official.PropertyId)):
        return tapir.PropertyIdArrayItem(propertyId=tapir.PropertyId(guid=property_id.guid))
    if isinstance(property_id, (UUID, str)):
        return tapir.PropertyIdArrayItem(propertyId=tapir.PropertyId(guid=_to_uuid(property_id)))
    raise TypeError(f"Unsupported property ID type: {type(property_id)!r}")


def normalize_property_ids(properties: Sequence[PropertyIdLike]) -> list[tapir.PropertyIdArrayItem]:
    """Convert property identifiers to Tapir array-item models in input order."""
    return [normalize_property_id(p) for p in properties]


def normalize_attribute_id(attribute_id: AttributeIdLike) -> tapir.AttributeIdArrayItem:
    """Convert an attribute identifier to a Tapir array-item model.

    Args:
        attribute_id: A supported Tapir or Official ID model, UUID, or UUID string.

    Raises:
        TypeError: If ``attribute_id`` is not a supported identifier type.
        ValueError: If a string is not a valid UUID.
    """
    if isinstance(attribute_id, tapir.AttributeIdArrayItem):
        return attribute_id
    if isinstance(attribute_id, official.AttributeIdWrapperItem):
        return tapir.AttributeIdArrayItem(attributeId=tapir.AttributeId(guid=attribute_id.attributeId.guid))
    if isinstance(attribute_id, (tapir.AttributeId, official.AttributeId)):
        return tapir.AttributeIdArrayItem(attributeId=tapir.AttributeId(guid=attribute_id.guid))
    if isinstance(attribute_id, (UUID, str)):
        return tapir.AttributeIdArrayItem(attributeId=tapir.AttributeId(guid=_to_uuid(attribute_id)))
    raise TypeError(f"Unsupported attribute ID type: {type(attribute_id)!r}")


def normalize_attribute_ids(attributes: Sequence[AttributeIdLike]) -> list[tapir.AttributeIdArrayItem]:
    """Convert attribute identifiers to Tapir array-item models in input order."""
    return [normalize_attribute_id(attribute) for attribute in attributes]


def to_official_property_id(property_id: PropertyIdLike) -> official.PropertyIdArrayItem:
    """Convert a supported property identifier to an Official array-item model."""
    if isinstance(property_id, official.PropertyIdArrayItem):
        return property_id
    guid = normalize_property_id(property_id).propertyId.guid
    return official.PropertyIdArrayItem(propertyId=official.PropertyId(guid=guid))


def to_official_attribute_id(attribute_id: AttributeIdLike) -> official.AttributeIdWrapperItem:
    """Convert a supported attribute identifier to an Official wrapper model."""
    if isinstance(attribute_id, official.AttributeIdWrapperItem):
        return attribute_id
    guid = normalize_attribute_id(attribute_id).attributeId.guid
    return official.AttributeIdWrapperItem(attributeId=official.AttributeId(guid=guid))


def split_builtin_name(non_localized_name: str) -> tuple[str, str]:
    """Split a built-in property name at its first underscore.

    Raises:
        ValueError: If the name has no non-empty text on both sides of an
            underscore.
    """
    match = re.search(r"(.+?(?=_))_(.+)", non_localized_name)
    if not match:
        raise ValueError(f"BuiltIn name '{non_localized_name}' cannot be split (missing '_' separator).")
    return match.group(1), match.group(2)
