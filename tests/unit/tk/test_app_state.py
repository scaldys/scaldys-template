import pytest
from unittest.mock import patch

# Skip these tests if ttkbootstrap or tkinter is not available (e.g. headless CI without Xvfb)
pytest.importorskip("ttkbootstrap")
pytest.importorskip("tkinter")

from scaldys_template.tk.app import Application
from scaldys_template.tk.styles import Styles
from scaldys_template.common.app_location import AppLocation


@pytest.mark.unit
class TestApplicationState:
    @pytest.fixture
    def app(self, isolated_app_location, monkeypatch):
        # Application calls user_data_dir(APP_NAME)
        # We want to ensure it uses a temporary directory.
        monkeypatch.setattr(
            "scaldys_template.tk.app.user_data_dir",
            lambda name: str(isolated_app_location[AppLocation.AppDataDir]),
        )

        # We also want to avoid any potential issues with DPI awareness in test environment
        with patch("scaldys_template.tk.app.set_dpi_awareness"):
            app = Application()
            yield app
            app.destroy()

    def test_sidebar_and_view_switching(self, app):
        """
        Verify the sidebar state, button selection logic, and view switching.
        Consolidated into a single test to avoid global state issues with multiple
        Tkinter/ttkbootstrap windows in the same process.
        """
        # 1. Initial State
        assert app.sidebar._has_labels is True, "Sidebar should start with labels shown"
        assert app.sidebar._active_button == app.sidebar._analyzer_btn, (
            "Analyzer should be selected by default"
        )
        assert app.sidebar._analyzer_btn.cget("style") == Styles.BARS_BUTTON_SELECTED_LEFT_TEXT, (
            "Analyzer button should have selected style"
        )
        assert "Analyzer" in app.sidebar._analyzer_btn.cget("text"), (
            "Analyzer button should have text"
        )

        # 2. Switch to UI Examples
        app.show_ui_examples_frame()
        assert app.sidebar._active_button == app.sidebar._ui_examples_btn, (
            "UI Examples should be selected"
        )
        assert app.sidebar._ui_examples_btn.cget("style") == Styles.BARS_BUTTON_SELECTED_LEFT_TEXT
        assert app.sidebar._analyzer_btn.cget("style") == Styles.BARS_BUTTON_LEFT_TEXT, (
            "Analyzer button should be unselected"
        )

        # 3. Switch to Navigation
        app.show_navigation_frame()
        assert app.sidebar._active_button == app.sidebar._navigation_btn, "Navigation should be selected"
        assert app.sidebar._navigation_btn.cget("style") == Styles.BARS_BUTTON_SELECTED_LEFT_TEXT
        assert app.sidebar._ui_examples_btn.cget("style") == Styles.BARS_BUTTON_LEFT_TEXT

        # 4. Toggle Labels (Hide)
        app.sidebar._toggle_labels()
        assert app.sidebar._has_labels is False
        assert app.sidebar._navigation_btn.cget("text") == "", "Button text should be empty when hidden"
        assert app.sidebar._navigation_btn.cget("style") == Styles.BARS_BUTTON_SELECTED_LEFT_TEXT, (
            "Style should be preserved when labels are hidden"
        )

        # 5. Toggle Labels (Show)
        app.sidebar._toggle_labels()
        assert app.sidebar._has_labels is True
        assert "Navigation" in app.sidebar._navigation_btn.cget("text"), "Button text should be restored"
        assert app.sidebar._navigation_btn.cget("style") == Styles.BARS_BUTTON_SELECTED_LEFT_TEXT
