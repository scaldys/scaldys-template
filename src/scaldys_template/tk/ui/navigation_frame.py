"""Side panel and main frame for the Navigation view.

The Navigation view consists of a NavigationPanel on the left and a main content area.
"""

import tkinter as tk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, LEFT, TOP, X, YES

import scaldys_template.tk.fontawesome_icons as faw
from scaldys_template.tk.styles import Styles


class NavigationPanel(tb.Frame):
    """Collapsible side panel positioned between the sidebar and the main content.

    Toggled via :py:meth:`~scaldys_template.tk.app.Application.toggle_navigation_frame`
    or via the toggle control in :py:class:`NavigationFrame`.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        # Pop on_theme_change if it exists to avoid TclError
        kwargs.pop("on_theme_change", None)
        super().__init__(master, **kwargs)
        self._initialize()

    def _initialize(self) -> None:
        tb.Label(self, text="Navigation Panel", padding=(10, 5)).pack(side="top", fill="x")
        tb.Separator(self, orient="horizontal").pack(fill="x", padx=5)
        # Replace this placeholder with your playback controls or tree widget.
        tb.Label(self, text="(placeholder)", foreground="gray", padding=(10, 5)).pack(
            side="top", fill="x"
        )


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
        self._is_panel_visible = True
        self._load_icons()
        self._build()

    def _load_icons(self) -> None:
        """Load icons for the internal toggle button."""
        style = tb.Style()
        colors: Any = style.colors
        fg = colors.fg

        size = 16
        self._img_left = faw.icon_to_image(faw.Icons.angle_left_solid, fill=fg, scale_to_width=size)
        self._img_right = faw.icon_to_image(
            faw.Icons.angle_right_solid, fill=fg, scale_to_width=size
        )

    def _build(self) -> None:
        # Top header bar
        self.header = tb.Frame(self, padding=(10, 5))
        self.header.pack(side=TOP, fill=X)

        tb.Label(self.header, text="Navigation View", font="-size 18 -weight bold").pack(side=LEFT)
        
        self.toggle_btn = tb.Button(
            self.header,
            image=self._img_left,
            style=Styles.BARS_BUTTON,
            command=self.toggle_panel,
        )
        self.toggle_btn.pack(side=LEFT, padx=(20, 0))

        # Main content area
        self.content_area = tb.Frame(self)
        self.content_area.pack(side=TOP, fill=BOTH, expand=YES)

        # Left side: NavigationPanel
        self.panel = NavigationPanel(self.content_area, style=Styles.BARS_FRAME)
        self.panel.pack(side=LEFT, fill="y")

        # Main central frame
        self.main_area = tb.Frame(self.content_area, padding=20)
        self.main_area.pack(side=LEFT, fill=BOTH, expand=YES)

        tb.Label(self.main_area, text="Main Navigation Content (Empty)", foreground="gray").pack(
            expand=YES
        )

    def toggle_panel(self) -> None:
        """Toggle the visibility of the internal navigation panel."""
        if self._is_panel_visible:
            self.panel.pack_forget()
            self.toggle_btn.configure(image=self._img_right)
        else:
            self.main_area.pack_forget()
            self.panel.pack(side=LEFT, fill="y")
            self.main_area.pack(side=LEFT, fill=BOTH, expand=YES)
            self.toggle_btn.configure(image=self._img_left)

        self._is_panel_visible = not self._is_panel_visible
