"""Identify unsupported query versions, invalid tests, and family configuration."""

from __future__ import annotations


class UnsupportedQueryVersionError(ValueError):
    """The executor does not support a query's major/minor schema version."""

    def __init__(self, requested_version: str, supported_version: str):
        self.requested_version = requested_version
        self.supported_version = supported_version
        super().__init__(
            f"Unsupported query schema version {requested_version!r}; executor supports {supported_version!r} "
            "and earlier minor versions of the same major"
        )


class InvalidFieldTestError(ValueError):
    """A test is incompatible with the selected field or its available choices."""


class InvalidPropertyTestError(InvalidFieldTestError):
    """A test family or operand is incompatible with the selected property."""


class InvalidClassificationTestError(InvalidFieldTestError):
    """A classification test is incompatible with its supplied system metadata."""


class UnsupportedFieldTypeError(ValueError):
    """No implemented test family supports a field's metadata."""


class UnsupportedPropertyTypeError(UnsupportedFieldTypeError):
    """No registered test family accepts a property's metadata."""


class AmbiguousPropertyTypeError(ValueError):
    """Multiple registered test families accept the same property's metadata."""
