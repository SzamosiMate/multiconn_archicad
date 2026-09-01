import pytest
from unittest.mock import MagicMock

from multiconn_archicad.conn_header import ConnHeader
from multiconn_archicad.basic_types import TapirInfo, APIResponseError, Port
from multiconn_archicad.errors import AddOnCommandUnavailable, ArchicadAPIError

pytestmark = [
    pytest.mark.usefixtures("archicad_api"),
    pytest.mark.integration,
]


def test_get_tapir_info_success():
    header = ConnHeader(port=Port(19723), initialize=False)
    header.core.post_tapir_command = MagicMock(return_value={"version": "1.5.8"})

    tapir_info = header.get_tapir_info(timeout=5.0)

    assert isinstance(tapir_info, TapirInfo)
    assert tapir_info.version == "1.5.8"
    assert tapir_info.is_installed is True
    assert tapir_info.is_supported is True


def test_get_tapir_info_addon_unavailable_fallback():
    header = ConnHeader(port=Port(19723), initialize=False)
    # Simulate Archicad responding with error code 4010 -> AddOnCommandUnavailable
    header.core.post_tapir_command = MagicMock(
        side_effect=AddOnCommandUnavailable("Add-on is not installed or command not found")
    )

    tapir_info = header.get_tapir_info(timeout=5.0)

    # Must resolve cleanly to TapirInfo.not_installed(), NOT APIResponseError
    assert isinstance(tapir_info, TapirInfo)
    assert tapir_info.is_installed is False
    assert tapir_info.version is None


def test_get_tapir_info_transport_error():
    header = ConnHeader(port=Port(19723), initialize=False)
    header.core.post_tapir_command = MagicMock(
        side_effect=ArchicadAPIError(code=5000, message="Transport Failure")
    )

    result = header.get_tapir_info(timeout=5.0)

    assert isinstance(result, APIResponseError)
    assert result.code == 5000
    assert "Transport Failure" in result.message