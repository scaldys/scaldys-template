"""Main Tkinter application window and top-level UI components.

Entry point::

    app = Application()
    app.mainloop()
"""

import logging
import os
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter.messagebox import showinfo
import ttkbootstrap as tb
from platformdirs import user_data_dir

from scaldys_template.__about__ import APP_NAME
import scaldys_template.tk.fontawesome_icons as faw
from scaldys_template.tk.styles import Styles
from scaldys_template.tk.ui import navigation_frame, UiExamplesFrame, NavigationFrame, NavigationPanel
from scaldys_template.tk.ui.analyzer.analyzer_frame import AnalyzerFrame
from scaldys_template.tk.ui.about_dialog import AboutDialog
from scaldys_template.tk.utils import set_dpi_awareness

logger = logging.getLogger(__name__)


def _indent(text: str) -> str:
    """Prefix *text* with two spaces — used for sidebar/toolbar button labels."""
    return f"  {text}"


# ---------------------------------------------------------------------------
# MenuBar
# ---------------------------------------------------------------------------


class MenuBar(tb.Frame):
    """Application menu bar.

    On Windows a custom frame-based menubar is used so that background colours
    can be themed.  On other platforms the native ``tk.Menu`` is used instead.
    """

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.main_content: tb.Frame | None = None
        self._initialize()

    def _initialize(self) -> None:
        if os.name == "nt":
            # self._build_windows_menubar()
            self._build_standard_menubar()
        else:
            self._build_standard_menubar()

    # ------------------------------------------------------------------
    # Platform-specific builders
    # ------------------------------------------------------------------

    def _build_windows_menubar(self) -> None:
        """Custom frame-based menubar for Windows (inherits theme colours)."""
        menubar = tb.Frame(self, style=Styles.MENUBAR_FRAME)
        menubar.pack(fill="x", side="top", expand=True)

        # Left spacer (can hold an application icon)
        tb.Label(menubar, text="    ", compound="left", style=Styles.NO_ARROW_MENUBUTTON).pack(
            side="left", ipadx=5, ipady=5, padx=(1, 0)
        )

        # File menu
        file_btn = tb.Menubutton(
            menubar, text="File", compound="left", style=Styles.NO_ARROW_MENUBUTTON
        )
        file_btn.pack(side="left", ipadx=5, ipady=5, padx=(1, 0))

        file_menu = tb.Menu(menubar, tearoff=0, relief=tk.SOLID, borderwidth=0, autostyle=True)
        file_menu.add_command(
            label="Load parameters…", accelerator="Ctrl+O", command=self._cmd_load
        )
        file_menu.add_command(
            label="Save parameters…", accelerator="Ctrl+S", command=self._cmd_save
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.master.destroy)  # type: ignore[attr-defined]
        file_btn["menu"] = file_menu

        # Analyzer menu
        analyzer_btn = tb.Menubutton(
            menubar, text="Analyzer", compound="left", style=Styles.NO_ARROW_MENUBUTTON
        )
        analyzer_btn.pack(side="left", ipadx=5, ipady=5, padx=(1, 0))

        analyzer_menu = tb.Menu(menubar, tearoff=0, relief=tk.SOLID, borderwidth=0, autostyle=True)
        analyzer_menu.add_command(label="Run analysis", accelerator="F5", command=self._cmd_run)
        analyzer_menu.add_command(label="Reset to defaults", command=self._cmd_reset)
        analyzer_btn["menu"] = analyzer_menu

        # Help menu
        help_btn = tb.Menubutton(
            menubar, text="Help", compound="left", style=Styles.NO_ARROW_MENUBUTTON
        )
        help_btn.pack(side="left", ipadx=5, ipady=5, padx=(1, 0))

        help_menu = tb.Menu(menubar, tearoff=0, relief=tk.SOLID, borderwidth=0, autostyle=True)
        help_menu.add_command(label="About", command=self._cmd_about)
        help_btn["menu"] = help_menu

    def _build_standard_menubar(self) -> None:
        """Standard ``tk.Menu`` for macOS / Linux."""
        menubar = tk.Menu(self.master)  # type: ignore[arg-type]

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(
            label="Load parameters…",
            accelerator="Ctrl+O",
            command=self._cmd_load,
        )
        file_menu.add_command(
            label="Save parameters…",
            accelerator="Ctrl+S",
            command=self._cmd_save,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Ctrl+Q", command=self.master.destroy)  # type: ignore[attr-defined]
        menubar.add_cascade(label="File", menu=file_menu)

        analyzer_menu = tk.Menu(menubar, tearoff=0)
        analyzer_menu.add_command(label="Run analysis", accelerator="F5", command=self._cmd_run)
        analyzer_menu.add_command(label="Reset to defaults", command=self._cmd_reset)
        menubar.add_cascade(label="Analyzer", menu=analyzer_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._cmd_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.master.config(menu=menubar)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Menu command helpers (delegate to AnalyzerFrame if present)
    # ------------------------------------------------------------------

    def _cmd_run(self) -> None:
        if isinstance(self.main_content, AnalyzerFrame):
            self.main_content._on_run()

    def _cmd_save(self) -> None:
        if isinstance(self.main_content, AnalyzerFrame):
            self.main_content._on_save()

    def _cmd_load(self) -> None:
        if isinstance(self.main_content, AnalyzerFrame):
            self.main_content._on_load()

    def _cmd_reset(self) -> None:
        if isinstance(self.main_content, AnalyzerFrame):
            self.main_content._on_reset()

    def _cmd_about(self) -> None:
        AboutDialog(self.master)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# ToolBar
# ---------------------------------------------------------------------------


class ToolBar(tb.Frame):
    """Horizontal toolbar displayed below the menu bar.

    Parameters
    ----------
    master:
        Parent widget.
    fg_color:
        Icon / text colour derived from the active theme.
    bg_color:
        Background colour derived from the active theme.
    """

    def __init__(self, master: tk.Misc, fg_color: str, bg_color: str, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._fg_color = fg_color
        self._bg_color = bg_color
        self._load_icons()
        self._initialize()

    def _load_icons(self) -> None:
        size = 24
        self._img_navigation = faw.icon_to_image(
            faw.Icons.circle_play_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_stop = faw.icon_to_image(
            faw.Icons.circle_stop_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_settings = faw.icon_to_image(
            faw.Icons.gear_solid, fill=self._fg_color, scale_to_width=size
        )

    def _initialize(self) -> None:
        buttonbar = tb.Frame(self)
        buttonbar.pack(fill="x", side="left")

        self._navigation_btn = tb.Button(
            buttonbar,
            text=_indent("Navigation"),
            image=self._img_navigation,
            compound="left",
            style=Styles.BARS_BUTTON,
            command=lambda: showinfo(message="Navigation — wire up your command here"),
        )
        self._navigation_btn.pack(side="left", ipadx=5, ipady=5)

        self._stop_btn = tb.Button(
            buttonbar,
            text=_indent("Stop"),
            image=self._img_stop,
            compound="left",
            style=Styles.BARS_BUTTON,
            command=lambda: showinfo(message="Stop — wire up your command here"),
        )
        self._stop_btn.pack(side="left", ipadx=5, ipady=5)

        self._settings_btn = tb.Button(
            buttonbar,
            text=_indent("Settings"),
            image=self._img_settings,
            compound="left",
            style=Styles.BARS_BUTTON,
            command=lambda: showinfo(message="Settings — wire up your command here"),
        )
        self._settings_btn.pack(side="left", ipadx=5, ipady=5)


# ---------------------------------------------------------------------------
# SideBar
# ---------------------------------------------------------------------------


class SideBar(tb.Frame):
    """Vertical icon bar on the left edge of the window.

    Parameters
    ----------
    master:
        Parent widget.
    fg_color:
        Icon / text colour derived from the active theme.
    bg_color:
        Background colour derived from the active theme.
    on_show_analyzer:
        Callback invoked when the analyzer button is clicked (shows the analyzer frame).
    on_show_ui_examples:
        Callback invoked when the example button is clicked (shows the UI examples frame).
    on_show_navigation:
        Callback invoked when the navigation button is clicked (shows the navigation frame).
    """

    def __init__(
        self,
        master: tk.Misc,
        fg_color: str,
        bg_color: str,
        on_show_analyzer: Callable[[], None],
        on_show_ui_examples: Callable[[], None],
        on_show_navigation: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._fg_color = fg_color
        self._bg_color = bg_color
        self._on_show_analyzer = on_show_analyzer
        self._on_show_ui_examples = on_show_ui_examples
        self._on_show_navigation = on_show_navigation
        self._has_labels = True
        self._active_button: tb.Button | None = None

        self._load_icons()
        self._initialize()
        self._show_labels()

    def _load_icons(self) -> None:
        size = 20
        self._img_analyzer = faw.icon_to_image(
            faw.Icons.square_poll_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_left_arrow = faw.icon_to_image(
            faw.Icons.angle_left_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_right_arrow = faw.icon_to_image(
            faw.Icons.angle_right_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_hamburger = faw.icon_to_image(
            faw.Icons.bars_solid_full, fill=self._fg_color, scale_to_width=size
        )
        self._img_navigation = faw.icon_to_image(
            faw.Icons.folder_tree_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_ui_examples = faw.icon_to_image(
            faw.Icons.cubes_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_settings = faw.icon_to_image(
            faw.Icons.gear_solid, fill=self._fg_color, scale_to_width=size
        )

    def _initialize(self) -> None:
        pad: dict[str, Any] = {"ipadx": 0, "ipady": 10, "pady": 0, "fill": "x"}

        top = tb.Frame(self)
        top.pack(side="top", fill="x")

        bottom = tb.Frame(self)
        bottom.pack(side="bottom", fill="x")

        self._toggle_label_btn = tb.Button(
            top, image=self._img_hamburger, takefocus=0, command=self._toggle_labels
        )
        self._toggle_label_btn.pack(side="top", **pad)

        self._analyzer_btn = tb.Button(
            top,
            image=self._img_analyzer,
            compound="left",
            takefocus=0,
            command=self._on_show_analyzer,
        )
        self._analyzer_btn.pack(side="top", **pad)

        self._ui_examples_btn = tb.Button(
            top,
            image=self._img_ui_examples,
            compound="left",
            takefocus=0,
            command=self._on_show_ui_examples,
        )
        self._ui_examples_btn.pack(side="top", **pad)

        self._navigation_btn = tb.Button(
            top,
            image=self._img_navigation,
            compound="left",
            takefocus=0,
            command=self._on_show_navigation,
        )
        self._navigation_btn.pack(side="top", **pad)

        self._settings_btn = tb.Button(
            bottom,
            image=self._img_settings,
            compound="left",
            takefocus=0,
            command=lambda: showinfo(message="Settings — wire up your command here"),
        )
        self._settings_btn.pack(side="bottom", **pad)

    def _show_labels(self) -> None:
        self._has_labels = True
        self._toggle_label_btn.configure(
            image=self._img_hamburger, style=Styles.BARS_BUTTON_LEFT_TEXT
        )
        self._update_styles()

    def _hide_labels(self) -> None:
        self._has_labels = False
        self._toggle_label_btn.configure(
            image=self._img_hamburger, style=Styles.BARS_BUTTON_LEFT_TEXT
        )
        self._update_styles()

    def _update_styles(self) -> None:
        buttons = [
            (self._analyzer_btn, "Analyzer"),
            (self._ui_examples_btn, "UI Examples"),
            (self._navigation_btn, "Navigation"),
            (self._settings_btn, "Settings"),
        ]
        for btn, label in buttons:
            is_active = btn == self._active_button
            text = _indent(label) if self._has_labels else ""
            style = (
                Styles.BARS_BUTTON_SELECTED_LEFT_TEXT if is_active else Styles.BARS_BUTTON_LEFT_TEXT
            )
            btn.configure(text=text, style=style)

    def _toggle_labels(self) -> None:
        if self._has_labels:
            self._hide_labels()
        else:
            self._show_labels()

    def set_active_button(self, btn: tb.Button | None) -> None:
        """Highlight the specified button and un-highlight all others."""
        self._active_button = btn
        self._update_styles()

    def select_analyzer(self) -> None:
        """Highlight the analyzer button."""
        self.set_active_button(self._analyzer_btn)

    def select_ui_examples(self) -> None:
        """Highlight the UI examples button."""
        self.set_active_button(self._ui_examples_btn)

    def select_navigation(self) -> None:
        """Highlight the navigation button."""
        self.set_active_button(self._navigation_btn)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class Application(tb.Window):
    """Root application window.

    Usage::

        app = Application()
        app.mainloop()
    """

    menubar: MenuBar
    toolbar: ToolBar
    sidebar: SideBar
    navigation_panel: NavigationPanel
    analyzer_frame: AnalyzerFrame
    ui_examples_frame: UiExamplesFrame
    navigation_frame: NavigationFrame
    main_content: AnalyzerFrame | UiExamplesFrame | NavigationFrame
    bars_fg_color: str
    bars_bg_color: str

    def __init__(self) -> None:
        super().__init__(themename="darkly")
        set_dpi_awareness()

        self.title(APP_NAME)
        self.minsize(1100, 650)

        # OS-appropriate directory for user config/data (logs, settings, cache, …)
        self.user_data_dir: Path = Path(user_data_dir(APP_NAME))

        self.apply_custom_styling()
        self._setup_layout()
        self._bind_shortcuts()

        logger.info("Application '%s' started", APP_NAME)

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

    def apply_custom_styling(self) -> None:
        """Configure ttkbootstrap styles to match the current theme.

        Called once on startup and again when the user switches themes via the
        UI examples frame.

        .. note::
            Icon colours in ``ToolBar`` and ``SideBar`` are baked into the
            ``SvgImage`` objects at construction time.  They will not update
            until the application is restarted.  If live icon recolouring is
            needed, call ``_load_icons()`` on those widgets and reconfigure
            the buttons.
        """
        # Pyright can't resolve style.colors (a ttkbootstrap Colors object) or
        # style.theme (a ThemeDefinition) because they're not in the type stubs.
        # Casting them to Any locally is the clean fix.
        colors: Any = self.style.colors
        theme: Any = self.style.theme
        fg: str = colors.get("fg") if theme.type == "dark" else colors.get("bg")
        dark: str = colors.get("dark")

        self.bars_fg_color: str = fg
        self.bars_bg_color: str = dark

        self.style.configure("TMenubutton", borderwidth=0)
        self.style.configure(Styles.NO_ARROW_MENUBUTTON, arrowsize=0, borderwidth=0)
        self.style.configure(Styles.DROPDOWN_FRAME, borderwidth=0)
        self.style.configure(Styles.MENUBAR_FRAME, background=dark)
        self.style.configure(Styles.BARS_FRAME, background=dark)
        self.style.configure(Styles.BARS_BUTTON, borderwidth=0, background=dark, foreground=fg)
        self.style.configure(
            Styles.BARS_BUTTON_SELECTED,
            borderwidth=0,
            background=colors.get("primary"),
            foreground=fg,
        )
        self.style.configure(Styles.BARS_BUTTON_LEFT_TEXT, anchor="w")
        self.style.configure(
            Styles.BARS_BUTTON_SELECTED_LEFT_TEXT,
            anchor="w",
            background=colors.get("primary"),
            foreground=fg,
        )
        self.style.configure(Styles.BARS_BUTTON_RIGHT_TEXT, anchor="e")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _setup_layout(self) -> None:
        """Create and arrange all top-level UI components."""
        # Top bars use pack (no show/hide required)
        self.menubar = MenuBar(self)
        self.toolbar = ToolBar(
            self, fg_color=self.bars_fg_color, bg_color=self.bars_bg_color, style=Styles.BARS_FRAME
        )
        self.menubar.pack(side="top", fill="x")
        self.toolbar.pack(side="top", fill="x")

        # Content area: grid allows reliable show/hide of the navigation panel
        # without the order-sensitive pack_forget() / pack() dance.
        content = tb.Frame(self)
        content.pack(fill="both", expand=True)
        content.columnconfigure(2, weight=1)  # main content column expands
        content.rowconfigure(0, weight=1)

        self.sidebar = SideBar(
            content,
            fg_color=self.bars_fg_color,
            bg_color=self.bars_bg_color,
            on_show_analyzer=self.show_analyzer_frame,
            on_show_ui_examples=self.show_ui_examples_frame,
            on_show_navigation=self.show_navigation_frame,
            style=Styles.BARS_FRAME,
        )
        self.navigation_panel = navigation_frame.NavigationPanel(content, style=Styles.BARS_FRAME)

        self.analyzer_frame = AnalyzerFrame(content)
        self.ui_examples_frame = UiExamplesFrame(content, on_theme_change=self.apply_custom_styling)
        self.navigation_frame = NavigationFrame(content, on_theme_change=self.apply_custom_styling)

        self.main_content = self.analyzer_frame
        self.menubar.main_content = self.main_content
        self.sidebar.select_analyzer()

        self.sidebar.grid(row=0, column=0, sticky="ns", padx=0, pady=2)

        self.analyzer_frame.grid(row=0, column=2, sticky="nsew")

        self.ui_examples_frame.grid(row=0, column=2, sticky="nsew")
        self.ui_examples_frame.grid_remove()

        self.navigation_frame.grid(row=0, column=2, sticky="nsew")
        self.navigation_frame.grid_remove()

        self.navigation_panel.grid(row=0, column=1, sticky="ns", padx=1, pady=2)
        self.navigation_panel.grid_remove()  # hidden by default

        self._is_navigation_frame_visible: bool = False

    # ------------------------------------------------------------------
    # Keyboard shortcuts
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        """Handle the OS close button (X) and Ctrl+Q — stop the event loop cleanly."""
        logger.info("Application '%s' closing", APP_NAME)
        self.quit()  # stops mainloop(); destroy() is called by cmd_gui after mainloop returns

    def _bind_shortcuts(self) -> None:
        self.bind_all("<Control-q>", lambda _event: self._on_close())
        self.bind_all("<Control-Q>", lambda _event: self._on_close())
        self.bind_all("<F5>", lambda _event: self.menubar._cmd_run())
        self.bind_all("<Control-s>", lambda _event: self.menubar._cmd_save())
        self.bind_all("<Control-S>", lambda _event: self.menubar._cmd_save())
        self.bind_all("<Control-o>", lambda _event: self.menubar._cmd_load())
        self.bind_all("<Control-O>", lambda _event: self.menubar._cmd_load())

    # ------------------------------------------------------------------
    # View switching
    # ------------------------------------------------------------------

    def show_ui_examples_frame(self) -> None:
        """Switch the main content area to the UiExamplesFrame."""
        self.sidebar.select_ui_examples()
        self.analyzer_frame.grid_remove()
        self.navigation_frame.grid_remove()
        self.ui_examples_frame.grid()
        self.navigation_panel.grid_remove()
        self.main_content = self.ui_examples_frame  # type: ignore[assignment]
        self.menubar.main_content = self.main_content

    def show_analyzer_frame(self) -> None:
        """Switch the main content area to the AnalyzerFrame."""
        self.sidebar.select_analyzer()
        self.analyzer_frame.grid()
        self.ui_examples_frame.grid_remove()
        self.navigation_frame.grid_remove()
        self.navigation_panel.grid_remove()
        self.main_content = self.analyzer_frame  # type: ignore[assignment]
        self.menubar.main_content = self.main_content

    def show_navigation_frame(self) -> None:
        """Switch the main content area to the NavigationFrame.

        If already visible, toggle the navigation panel.
        """
        self.sidebar.select_navigation()
        if self.main_content == self.navigation_frame:
            self.navigation_frame.toggle_panel()
        else:
            self.analyzer_frame.grid_remove()
            self.ui_examples_frame.grid_remove()
            self.navigation_frame.grid()
            self.navigation_panel.grid_remove()
            self.main_content = self.navigation_frame  # type: ignore[assignment]
            self.menubar.main_content = self.main_content

    # ------------------------------------------------------------------
    # Navigation-panel toggle
    # ------------------------------------------------------------------

    def toggle_navigation_frame(self) -> None:
        """Show or hide the navigation panel beside the sidebar."""
        if self._is_navigation_frame_visible:
            self.navigation_panel.grid_remove()
        else:
            self.navigation_panel.grid()
        self._is_navigation_frame_visible = not self._is_navigation_frame_visible


if __name__ == "__main__":
    app = Application()
    app.mainloop()
