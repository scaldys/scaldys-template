import pytest
from unittest.mock import MagicMock, patch

from scaldys_template.tk import utils


@pytest.mark.unit
class TestZoom:
    def test_set_dpi_awareness_graceful_when_unavailable(self) -> None:
        with patch("ctypes.windll", create=True, side_effect=AttributeError):
            utils.set_dpi_awareness()

    def test_dark_title_bar_calls_windows_api(self) -> None:
        mock_window = MagicMock()
        mock_window.winfo_id.return_value = 42

        mock_set_window_attribute = MagicMock()
        mock_dwmapi = MagicMock()
        mock_dwmapi.DwmSetWindowAttribute = mock_set_window_attribute
        mock_user32 = MagicMock()
        mock_user32.GetParent.return_value = 100
        mock_windll = MagicMock()
        mock_windll.dwmapi = mock_dwmapi
        mock_windll.user32 = mock_user32

        with patch("scaldys_template.tk.utils.ct.windll", mock_windll, create=True):
            utils.dark_title_bar(mock_window)

        mock_window.update.assert_called_once()
        mock_user32.GetParent.assert_called_once_with(42)
        mock_set_window_attribute.assert_called_once()
