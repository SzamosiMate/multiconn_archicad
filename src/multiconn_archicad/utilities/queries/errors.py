"""Expected failures when a property test is checked against metadata."""
from __future__ import annotations


class InvalidPropertyTestError(ValueError):
    """A test family or operand is incompatible with the selected property."""


class UnsupportedPropertyTypeError(ValueError):
    """No registered test family accepts a property's metadata."""


class AmbiguousPropertyTypeError(ValueError):
    """Multiple registered test families accept the same property's metadata."""
