from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Skip these tests if ttkbootstrap or tkinter is not available (e.g. headless CI without Xvfb)
pytest.importorskip("ttkbootstrap")
pytest.importorskip("tkinter")

import tkinter

try:
    root = tkinter.Tk()
    root.destroy()
except (tkinter.TclError, Exception):
    pytest.skip("Tkinter display not available", allow_module_level=True)

from scaldys_template.common.app_location import AppLocation
from scaldys_template.tk.app import Application


@pytest.mark.unit
@pytest.mark.svg
class TestToolBar:
    @pytest.fixture
    def app(
        self, isolated_app_location: dict[int, Path], monkeypatch: pytest.MonkeyPatch
    ) -> Generator[Application]:
        monkeypatch.setattr(
            "scaldys_template.tk.app.user_data_dir",
            lambda name: str(isolated_app_location[AppLocation.AppDataDir]),
        )
        with patch("scaldys_template.tk.app.set_dpi_awareness"):
            app = Application()
            yield app
            app.destroy()

    def test_toolbar_functionality(self, app: Application) -> None:
        """Verify the toolbar buttons, visibility when switching frames, and wiring."""
        # --- 1. Context Switching ---

        # Initial State (Analyzer)
        assert app.toolbar.winfo_manager() == "pack", "Toolbar should be packed by default"
        assert app.toolbar._open_btn.winfo_manager() == "pack"
        assert app.toolbar._save_btn.winfo_manager() == "pack"
        assert app.toolbar._run_btn.winfo_manager() == "pack"
        assert app.toolbar._defaults_btn.winfo_manager() == "pack"
        assert app.toolbar._sep.winfo_manager() == "pack"
        assert app.toolbar._apply_btn.winfo_manager() == "", (
            "Apply button should be hidden in analyzer"
        )
        assert app.toolbar._apply_sep.winfo_manager() == "", (
            "Apply separator should be hidden in analyzer"
        )

        assert str(app.toolbar._open_btn.cget("state")) == "normal"
        assert str(app.toolbar._run_btn.cget("state")) == "normal"

        # Switch to Editor
        app.show_editor_frame()
        assert app.toolbar.winfo_manager() == "pack", "Toolbar should still be packed in editor"
        assert app.toolbar._open_btn.winfo_manager() == "pack"
        assert app.toolbar._save_btn.winfo_manager() == "pack"

        # Analyzer group should be hidden (not packed)
        assert app.toolbar._run_btn.winfo_manager() == "", "Run button should be hidden in editor"
        assert app.toolbar._defaults_btn.winfo_manager() == "", (
            "Defaults button should be hidden in editor"
        )
        assert app.toolbar._sep.winfo_manager() == "", "Separator should be hidden in editor"

        # Apply group should be shown
        assert app.toolbar._apply_btn.winfo_manager() == "pack", (
            "Apply button should be shown in editor"
        )
        assert app.toolbar._apply_sep.winfo_manager() == "pack", (
            "Apply separator should be shown in editor"
        )

        assert str(app.toolbar._open_btn.cget("state")) == "normal"

        # Switch to UI Examples
        app.show_ui_examples_frame()
        assert app.toolbar.winfo_manager() == "", "Toolbar should be hidden in UI Examples"

        # Switch back to Analyzer
        app.show_analyzer_frame()
        assert app.toolbar.winfo_manager() == "pack", "Toolbar should be re-packed in analyzer"
        assert app.toolbar._run_btn.winfo_manager() == "pack", (
            "Run button should be re-packed in analyzer"
        )
        assert str(app.toolbar._run_btn.cget("state")) == "normal"

        # --- 2. Button Wiring ---

        # Mock the target methods
        app.app_open_file = MagicMock()
        app.app_save_file = MagicMock()
        app.analyzer_frame._on_run = MagicMock()
        app.analyzer_frame._on_reset = MagicMock()
        app.editor_frame._handle_apply = MagicMock()

        # Trigger button commands
        app.toolbar._open_btn.invoke()
        app.app_open_file.assert_called_once()

        app.toolbar._save_btn.invoke()
        app.app_save_file.assert_called_once()

        app.toolbar._run_btn.invoke()
        app.analyzer_frame._on_run.assert_called_once()

        app.toolbar._defaults_btn.invoke()
        app.analyzer_frame._on_reset.assert_called_once()

        app.toolbar._apply_btn.invoke()
        app.editor_frame._handle_apply.assert_called_once()
