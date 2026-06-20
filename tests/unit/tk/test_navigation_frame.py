import pytest
from typing import Generator
from pathlib import Path
from unittest.mock import patch

# Skip these tests if ttkbootstrap or tkinter is not available
pytest.importorskip("ttkbootstrap")
pytest.importorskip("tkinter")

import tkinter

try:
    root = tkinter.Tk()
    root.destroy()
except (tkinter.TclError, Exception):
    pytest.skip("Tkinter display not available", allow_module_level=True)

import ttkbootstrap as tb
from scaldys_template.tk.app import Application
from scaldys_template.common.app_location import AppLocation


@pytest.mark.unit
@pytest.mark.svg
class TestNavigationView:
    @pytest.fixture
    def app(
        self, isolated_app_location: dict[int, Path], monkeypatch: pytest.MonkeyPatch
    ) -> Generator[Application, None, None]:
        # Application calls user_data_dir(APP_NAME)
        monkeypatch.setattr(
            "scaldys_template.tk.app.user_data_dir",
            lambda name: str(isolated_app_location[AppLocation.AppDataDir]),
        )

        with patch("scaldys_template.tk.app.set_dpi_awareness"):
            app = Application()
            yield app
            app.destroy()

    def test_navigation_logic(self, app: Application) -> None:
        """
        Consolidated test for NavigationFrame and NavigationPanel to avoid Tcl issues.
        """
        # 1. Verify NavigationPanel initialization (internal to NavigationFrame)
        nav_frame = app.navigation_frame
        panel = nav_frame.panel

        assert hasattr(panel, "tree")
        assert isinstance(panel.tree, tb.Treeview)

        children = panel.tree.get_children()
        assert len(children) == 3  # Node 1, 2, 3

        # 2. Verify node selection updates content in NavigationFrame
        # Switch to navigation view first
        app.show_navigation_frame()

        # Find a leaf node in internal panel
        node_id = children[0]
        subnode_id = panel.tree.get_children(node_id)[0]
        leaf_id = panel.tree.get_children(subnode_id)[0]

        # Simulate selection
        panel.tree.selection_set(leaf_id)
        panel._handle_selection(None)

        expected_path = "Node 1 / Subnode 1.1 / Leaf 1.1.1"
        assert nav_frame.content_label.cget("text") == expected_path

        # 3. Verify Global Navigation Panel updates the frame
        global_panel = app.navigation_panel
        g_children = global_panel.tree.get_children()
        g_leaf_id = global_panel.tree.get_children(
            global_panel.tree.get_children(g_children[1])[1]
        )[1]

        # Simulate selection in global panel
        global_panel.tree.selection_set(g_leaf_id)
        global_panel._handle_selection(None)

        expected_global_path = "Node 2 / Subnode 2.2 / Leaf 2.2.2"
        assert nav_frame.content_label.cget("text") == expected_global_path
