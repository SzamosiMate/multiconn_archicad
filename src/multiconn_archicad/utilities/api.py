"""Group element, property, and attribute utilities for one Unified API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .attributes import AttributeUtilities
from .elements import ElementUtilities
from .properties import PropertyUtilities

if TYPE_CHECKING:
    from multiconn_archicad.clients.unified_api.api import UnifiedApi


class Utilities:
    """Expose domain utility groups bound to one Unified API instance.

    Attributes:
        property: Property reads, writes, and metadata lookups.
        attribute: Attribute and layer-combination lookups.
        element: Element queries and selection operations.
    """

    def __init__(self, api: UnifiedApi):
        """Create utility groups that use ``api`` for their operations."""
        self.property = PropertyUtilities(api)
        self.attribute = AttributeUtilities(api)
        self.element = ElementUtilities(api)
