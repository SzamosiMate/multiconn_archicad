from unittest.mock import MagicMock

from multiconn_archicad.utilities import AttributeUtilities, ElementUtilities, PropertyUtilities, Utilities, __all__


def test_utilities_binds_each_domain_group_to_the_same_api():
    api = MagicMock()

    utilities = Utilities(api)

    assert isinstance(utilities.property, PropertyUtilities)
    assert isinstance(utilities.attribute, AttributeUtilities)
    assert isinstance(utilities.element, ElementUtilities)
    assert utilities.property._api is api
    assert utilities.attribute._api is api
    assert utilities.element._api is api


def test_domain_utility_classes_are_public_exports():
    assert {"PropertyUtilities", "AttributeUtilities", "ElementUtilities"} <= set(__all__)
