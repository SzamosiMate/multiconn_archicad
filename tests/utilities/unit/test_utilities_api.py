from unittest.mock import MagicMock

from multiconn_archicad.utilities import Utilities
from multiconn_archicad.utilities.attributes import AttributeUtilities
from multiconn_archicad.utilities.elements import ElementUtilities
from multiconn_archicad.utilities.properties import PropertyUtilities


def test_utilities_binds_each_domain_group_to_the_same_api():
    api = MagicMock()

    utilities = Utilities(api)

    assert isinstance(utilities.property, PropertyUtilities)
    assert isinstance(utilities.attribute, AttributeUtilities)
    assert isinstance(utilities.element, ElementUtilities)
    assert utilities.property._api is api
    assert utilities.attribute._api is api
    assert utilities.element._api is api
