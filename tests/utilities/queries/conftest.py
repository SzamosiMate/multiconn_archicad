"""Fresh offline project for each execution contract test."""

import pytest

from .support import FakeProject


@pytest.fixture
def project():
    project = FakeProject()
    yield project
    # All bound query operations are read-only, including exceptional paths.
    project.api.tapir.element.change_selection_of_elements.assert_not_called()
