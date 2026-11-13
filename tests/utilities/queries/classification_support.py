"""Exercise classification discovery, snapshots and assignment grids offline."""

from unittest.mock import MagicMock
from uuid import UUID

import pytest

from multiconn_archicad.models.official import types as official
from multiconn_archicad.utilities import Utilities

SYSTEM, OTHER_SYSTEM, ROOT, CHILD, GRANDCHILD, LEAF, ELEMENT, OTHER_ELEMENT, MISSING = [
    UUID(int=i) for i in range(1, 10)
]


def system(guid=SYSTEM, name="Example"):
    return official.ClassificationSystem.model_validate(
        {
            "classificationSystemId": {"guid": guid},
            "name": name,
            "description": "Description",
            "source": "Example",
            "version": "1",
            "date": "2026-11-01",
        }
    )


def node(guid, code, children=None, name=""):
    return {
        "classificationItem": {
            "classificationItemId": {"guid": guid},
            "id": code,
            "name": name,
            "description": "Item description",
            "children": children,
        }
    }


@pytest.fixture
def tree():
    return [
        official.ClassificationItemArrayItem.model_validate(
            node(
                ROOT,
                "Elements",
                [
                    node(CHILD, "Wall", [node(GRANDCHILD, "Partition")]),
                    node(LEAF, "Slab", name="Slabs"),
                ],
            )
        )
    ]


@pytest.fixture
def api(tree):
    api = MagicMock()
    api.utilities = Utilities(api)
    api.official.classification.get_all_classification_systems.return_value = [system(), system(OTHER_SYSTEM, "Other")]
    api.official.classification.get_all_classifications_in_system.return_value = tree
    return api
