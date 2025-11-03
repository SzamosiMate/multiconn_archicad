import sys
import pytest


pytestmark = [pytest.mark.integration]

try:
    import pywinauto
    PYWINAUTO_INSTALLED = True
except ImportError:
    PYWINAUTO_INSTALLED = False

@pytest.mark.skipif(PYWINAUTO_INSTALLED, reason="Skipping because pywinauto IS installed. Test runs on CI.")
def test_platform_specific_error_messages():
    """
    Verifies the correct error messages for platform-specific objects.
    - On Windows, it checks for the 'pip install' message (assumes extras are not installed).
    - On macOS, it checks for the 'Windows-only' message.
    """
    # ARRANGE:
    from multiconn_archicad import WinDialogHandler, win_int_handler_factory

    # ACT & ASSERT
    if sys.platform == "win32":
        expected_message = "pip install multiconn_archicad[dialog-handlers]"

        with pytest.raises(ImportError) as exc_info:
            WinDialogHandler(win_int_handler_factory)
        assert expected_message in str(exc_info.value)

    else:
        expected_message = "only available on Windows"

        with pytest.raises(ImportError) as exc_info:
            WinDialogHandler(win_int_handler_factory)
        assert expected_message in str(exc_info.value)
