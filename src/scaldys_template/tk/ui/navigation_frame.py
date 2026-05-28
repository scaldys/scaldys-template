"""Side panel and main frame for the Navigation view.

The Navigation view consists of a NavigationPanel on the left and a main content area.
"""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, TOP, X, YES

from scaldys_template.tk.styles import Styles


class NavigationPanel(tb.Frame):
    """Side panel positioned between the sidebar and the main content.

    In the Navigation view, it is always visible and resizable.
    As a global panel, it can be toggled via
    :py:meth:`~scaldys_template.tk.app.Application.toggle_navigation_frame`.
    """

    def __init__(
        self, master: tk.Misc, on_node_select: Callable[[str], None] | None = None, **kwargs: Any
    ) -> None:
        """Initialize the NavigationPanel.

        Args:
            master: Parent widget.
            on_node_select: Callback function called with the selected node's hierarchy path.
            **kwargs: Additional keyword arguments for the tb.Frame.
        """
        # Pop on_theme_change if it exists to avoid TclError
        kwargs.pop("on_theme_change", None)
        super().__init__(master, **kwargs)
        self._on_node_select = on_node_select
        self._initialize()

    def _initialize(self) -> None:
        tb.Label(self, text="Navigation Panel", padding=(10, 5)).pack(side="top", fill="x")
        tb.Separator(self, orient="horizontal").pack(fill="x", padx=5)

        # Treeview
        self.tree = tb.Treeview(self, show="tree", bootstyle="secondary")
        self.tree.pack(side="top", fill="both", expand=True, padx=5, pady=5)

        # Populate dummy nodes (3 levels)
        for i in range(1, 4):
            parent = self.tree.insert("", "end", text=f"Node {i}", open=True)
            for j in range(1, 4):
                child = self.tree.insert(parent, "end", text=f"Subnode {i}.{j}")
                for k in range(1, 4):
                    self.tree.insert(child, "end", text=f"Leaf {i}.{j}.{k}")

        self.tree.bind("<<TreeviewSelect>>", self._handle_selection)

    def _handle_selection(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if not self._on_node_select:
            return

        selection = self.tree.selection()
        if not selection:
            return

        node_id = selection[0]
        hierarchy = []
        curr = node_id
        while curr:
            hierarchy.append(self.tree.item(curr, "text"))
            curr = self.tree.parent(curr)

        hierarchy.reverse()
        path = " / ".join(hierarchy)
        self._on_node_select(path)


class NavigationFrame(tb.Frame):
    """Main Navigation view frame.

    Similar to AnalyzerFrame or UiExamplesFrame, it acts as a top-level content widget.
    It contains a NavigationPanel on the left and a central frame.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_theme_change: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_theme_change = on_theme_change
        self._build()

    def _build(self) -> None:
        # Top header bar
        self.header = tb.Frame(self, padding=(10, 5))
        self.header.pack(side=TOP, fill=X)

        tb.Label(self.header, text="Navigation View", font="-size 18 -weight bold").pack(side=LEFT)

        # Main content area - PanedWindow for resizable NavigationPanel
        self.content_area = tk.PanedWindow(
            self, orient="horizontal", sashrelief="raised", sashwidth=4
        )
        self.content_area.pack(side=TOP, fill=BOTH, expand=YES)

        # Left side: NavigationPanel
        self.panel = NavigationPanel(
            self.content_area, on_node_select=self.update_content, style=Styles.BARS_FRAME
        )

        # Main central frame
        self.main_area = tb.Frame(self.content_area, padding=20)
        self.content_label = tb.Label(
            self.main_area,
            text="Main Navigation Content (Empty)",
            bootstyle="secondary",
            anchor="center",
        )
        self.content_label.pack(expand=YES, fill="both")

        # Add panes to the PanedWindow
        self.content_area.add(self.panel, width=250)
        self.content_area.add(self.main_area, stretch="always")

    def update_content(self, hierarchy: str) -> None:
        """Update the main content label with the selected node hierarchy."""
        self.content_label.configure(text=hierarchy, bootstyle="default")
