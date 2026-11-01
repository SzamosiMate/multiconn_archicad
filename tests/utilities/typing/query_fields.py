"""Check that shared field/catalogue behavior preserves concrete public types."""

from typing import assert_type
from uuid import UUID

from multiconn_archicad.utilities.queries import (
    ClassificationCatalogue,
    ClassificationInfo,
    ClassificationTest,
    PropertyCatalogue,
    PropertyInfo,
    PropertyTestModel,
    UnsupportedPropertyInfo,
)


def check_field_types(properties: PropertyCatalogue, classifications: ClassificationCatalogue, guid: UUID) -> None:
    assert_type(properties.get(guid), PropertyInfo | UnsupportedPropertyInfo | None)
    assert_type(properties.supported, tuple[PropertyInfo, ...])
    assert_type(properties.unsupported, tuple[UnsupportedPropertyInfo, ...])
    assert_type(classifications.get(guid), ClassificationInfo | None)
    assert_type(classifications.search("example"), tuple[ClassificationInfo, ...])
    assert_type(classifications.supported, tuple[ClassificationInfo, ...])
    assert_type(classifications[guid].create_test(operator="is", value=guid), ClassificationTest)
    assert_type(properties[guid].create_test(operator="is", value=1), PropertyTestModel)
