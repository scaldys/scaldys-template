import pytest
import tkinter as tk
from unittest.mock import MagicMock, patch
from scaldys_template.tk.app import Application
from scaldys_template.tk.utils import update_font_scale

@pytest.mark.unit
class TestZoom:
    @patch("scaldys_template.tk.app.set_dpi_awareness")
    @patch("scaldys_template.tk.app.user_data_dir", return_value="/tmp/scaldys")
    @patch("scaldys_template.tk.app.UiExamplesFrame")  # Mock to avoid the Meter error
    @patch("scaldys_template.tk.app.AnalyzerFrame")
    @patch("scaldys_template.tk.app.NavigationFrame")
    def test_zoom_logic(self, mock_nav, mock_analyzer, mock_ui, mock_user_data, mock_dpi):
        app = Application()
        
        # Initial scale
        assert app._font_scale == 1.0
        
        # Mock event for zoom up (delta > 0)
        event_up = MagicMock(spec=tk.Event)
        event_up.delta = 120
        event_up.num = 0
        
        with patch("scaldys_template.tk.app.update_font_scale") as mock_update_font:
            app._on_zoom(event_up)
            assert app._font_scale == pytest.approx(1.1)
            mock_update_font.assert_called_once_with(pytest.approx(1.1))
            
        # Mock event for zoom down (num = 5)
        event_down = MagicMock(spec=tk.Event)
        event_down.delta = 0
        event_down.num = 5
        
        with patch("scaldys_template.tk.app.update_font_scale") as mock_update_font:
            app._on_zoom(event_down)
            assert app._font_scale == pytest.approx(1.0)
            mock_update_font.assert_called_once_with(pytest.approx(1.0))

        app.destroy()

    @patch("tkinter.font.nametofont")
    @patch("tkinter.font.names", return_value=["TkDefaultFont"])
    def test_update_font_scale_utility(self, mock_font_names, mock_nametofont):
        from scaldys_template.tk.utils import update_font_scale, _original_font_sizes
        
        # Clear state for testing
        _original_font_sizes.clear()
        
        mock_font = MagicMock()
        mock_font.actual.return_value = 10
        mock_nametofont.return_value = mock_font
        
        # First call captures original size
        update_font_scale(1.5)
        assert _original_font_sizes["TkDefaultFont"] == 10
        mock_font.configure.assert_called_with(size=15)
        
        # Second call scales from original
        update_font_scale(2.0)
        mock_font.configure.assert_called_with(size=20)
