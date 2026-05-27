"""Main Tkinter application window and top-level UI components.

Entry point::

    app = Application()
    app.mainloop()
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.messagebox import showinfo
import ttkbootstrap as tb
from platformdirs import user_data_dir
from pydantic import ValidationError

from scaldys_template.__about__ import APP_NAME
import scaldys_template.tk.fontawesome_icons as faw
from scaldys_template.common.app_location import AppLocation
from scaldys_template.core.parameter_store import load_parameters, save_parameters
from scaldys_template.core.signal_model import SignalParameters
from scaldys_template.tk.styles import Styles
from scaldys_template.tk.ui import navigation_frame, EditorFrame, UiExamplesFrame, NavigationFrame, NavigationPanel
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

    def __init__(self, master: tk.Misc, app: "Application", **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._app = app
        self.main_content: tb.Frame | None = None  # kept for legacy show_*_frame callers
        self._recent_menu_nt: tk.Menu | None = None
        self._recent_menu_std: tk.Menu | None = None
        self._initialize()

    def _initialize(self) -> None:
        if os.name == "nt":
            self._build_windows_menubar()
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
            label="Open…", accelerator="Ctrl+O", command=self._cmd_open
        )
        file_menu.add_command(
            label="Save", accelerator="Ctrl+S", command=self._cmd_save
        )
        file_menu.add_command(label="Save As…", command=self._cmd_save_as)
        file_menu.add_separator()

        self._recent_menu_nt = tb.Menu(
            file_menu, tearoff=0, relief=tk.SOLID, borderwidth=0, autostyle=True
        )
        self._populate_recent_menu(self._recent_menu_nt)
        file_menu.add_cascade(label="Recent Files", menu=self._recent_menu_nt)

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
        file_menu.add_command(label="Open…", accelerator="Ctrl+O", command=self._cmd_open)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self._cmd_save)
        file_menu.add_command(label="Save As…", command=self._cmd_save_as)
        file_menu.add_separator()

        self._recent_menu_std = tk.Menu(file_menu, tearoff=0)
        self._populate_recent_menu(self._recent_menu_std)
        file_menu.add_cascade(label="Recent Files", menu=self._recent_menu_std)

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
    # Recent Files helpers
    # ------------------------------------------------------------------

    def _populate_recent_menu(self, menu: tk.Menu) -> None:
        """Repopulate *menu* from the application's recent-files list."""
        menu.delete(0, "end")
        recent = self._app._recent_files
        if not recent:
            menu.add_command(label="(empty)", state="disabled")
            return
        for path in recent:
            menu.add_command(
                label=str(path),
                command=lambda p=path: self._app.app_open_recent_file(p),  # type: ignore[misc]
            )

    def rebuild_recent_files_menu(self) -> None:
        """Repopulate both platform recent-files menus after the list changes."""
        for menu in (self._recent_menu_nt, self._recent_menu_std):
            if menu is not None:
                self._populate_recent_menu(menu)

    # ------------------------------------------------------------------
    # Menu command helpers
    # ------------------------------------------------------------------

    def _cmd_run(self) -> None:
        self._app.analyzer_frame._on_run()

    def _cmd_open(self) -> None:
        self._app.app_open_file()

    def _cmd_save(self) -> None:
        self._app.app_save_file()

    def _cmd_save_as(self) -> None:
        self._app.app_save_file_as()

    def _cmd_reset(self) -> None:
        self._app.analyzer_frame._on_reset()

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
    on_show_editor:
        Callback invoked when the editor button is clicked (shows the editor frame).
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
        on_show_editor: Callable[[], None],
        on_show_ui_examples: Callable[[], None],
        on_show_navigation: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._fg_color = fg_color
        self._bg_color = bg_color
        self._on_show_analyzer = on_show_analyzer
        self._on_show_editor = on_show_editor
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
        self._img_file = faw.icon_to_image(
            faw.Icons.file_lines_regular, fill=self._fg_color, scale_to_width=size
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

        self._editor_btn = tb.Button(
            top,
            image=self._img_file,
            compound="left",
            takefocus=0,
            command=self._on_show_editor,
        )
        self._editor_btn.pack(side="top", **pad)

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
            (self._editor_btn, "Editor"),
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

    def select_editor(self) -> None:
        """Highlight the editor button."""
        self.set_active_button(self._editor_btn)

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
    editor_frame: EditorFrame
    ui_examples_frame: UiExamplesFrame
    navigation_frame: NavigationFrame
    main_content: AnalyzerFrame | EditorFrame | UiExamplesFrame | NavigationFrame
    bars_fg_color: str
    bars_bg_color: str

    def __init__(self) -> None:
        set_dpi_awareness()
        super().__init__(themename="darkly")

        self.title(APP_NAME)
        self.minsize(1100, 650)

        # OS-appropriate directory for user config/data (logs, settings, cache, …)
        self.user_data_dir: Path = Path(user_data_dir(APP_NAME))

        self.current_file: Path | None = None
        self._recent_files: list[Path] = []

        self.apply_custom_styling()
        self._setup_layout()
        self._load_recent_files()
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
        self.menubar = MenuBar(self, app=self)
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
            on_show_editor=self.show_editor_frame,
            on_show_ui_examples=self.show_ui_examples_frame,
            on_show_navigation=self.show_navigation_frame,
            style=Styles.BARS_FRAME,
        )
        self.navigation_panel = navigation_frame.NavigationPanel(
            content, on_node_select=self._on_global_node_select, style=Styles.BARS_FRAME
        )

        self.analyzer_frame = AnalyzerFrame(
            content,
            on_params_changed=lambda p: self.update_parameters(p, "analyzer"),
        )
        self.editor_frame = EditorFrame(content, on_apply=self._apply_editor_json)
        self.ui_examples_frame = UiExamplesFrame(content, on_theme_change=self.apply_custom_styling)
        self.navigation_frame = NavigationFrame(content, on_theme_change=self.apply_custom_styling)

        self.main_content = self.analyzer_frame
        self.menubar.main_content = self.main_content
        self.sidebar.select_analyzer()

        # Populate editor with the initial default parameters
        self.editor_frame.set_json(SignalParameters().model_dump_json(indent=2))

        self.sidebar.grid(row=0, column=0, sticky="ns", padx=0, pady=2)

        self.analyzer_frame.grid(row=0, column=2, sticky="nsew")

        self.editor_frame.grid(row=0, column=2, sticky="nsew")
        self.editor_frame.grid_remove()

        self.ui_examples_frame.grid(row=0, column=2, sticky="nsew")
        self.ui_examples_frame.grid_remove()

        self.navigation_frame.grid(row=0, column=2, sticky="nsew")
        self.navigation_frame.grid_remove()

        self.navigation_panel.grid(row=0, column=1, sticky="ns", padx=1, pady=2)
        self.navigation_panel.grid_remove()  # hidden by default

        self._is_navigation_panel_visible: bool = False

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
        self.bind_all("<F5>", lambda _event: self.analyzer_frame._on_run())
        self.bind_all("<Control-s>", lambda _event: self.app_save_file())
        self.bind_all("<Control-S>", lambda _event: self.app_save_file())
        self.bind_all("<Control-o>", lambda _event: self.app_open_file())
        self.bind_all("<Control-O>", lambda _event: self.app_open_file())

    # ------------------------------------------------------------------
    # Recent Files persistence
    # ------------------------------------------------------------------

    @property
    def _recent_files_path(self) -> Path:
        return AppLocation.get_directory(AppLocation.AppDataDir) / "recent_files.json"

    def _load_recent_files(self) -> None:
        try:
            text = self._recent_files_path.read_text(encoding="utf-8")
            raw: list[str] = json.loads(text)
            self._recent_files = [Path(p) for p in raw if isinstance(p, str)]
        except (OSError, json.JSONDecodeError, TypeError):
            self._recent_files = []
        self.menubar.rebuild_recent_files_menu()

    def _save_recent_files(self) -> None:
        try:
            path = self._recent_files_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps([str(p) for p in self._recent_files], indent=2), encoding="utf-8"
            )
        except OSError as exc:
            logger.warning("Could not save recent files list: %s", exc)

    def add_recent_file(self, path: Path) -> None:
        """Prepend *path* to the recent-files list (max 10 entries, no duplicates)."""
        self._recent_files = [path] + [p for p in self._recent_files if p != path]
        self._recent_files = self._recent_files[:10]
        self._save_recent_files()
        self.menubar.rebuild_recent_files_menu()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def app_open_file(self) -> None:
        """Show an open-file dialog and load the selected JSON parameter file."""
        path_str = filedialog.askopenfilename(
            title="Open Parameters",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        self.app_open_recent_file(Path(path_str))

    def app_open_recent_file(self, path: Path) -> None:
        """Load parameters from *path* (used for both Open and Recent Files)."""
        try:
            params = load_parameters(path)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Open Error", str(exc))
            return
        self.current_file = path
        self.add_recent_file(path)
        self.update_parameters(params, "file")

    def app_save_file(self) -> None:
        """Save to the current file, or fall back to Save As… if none is set."""
        if self.current_file:
            self._do_save(self.current_file)
        else:
            self.app_save_file_as()

    def app_save_file_as(self) -> None:
        """Show a save-file dialog and write the current parameters."""
        path_str = filedialog.asksaveasfilename(
            title="Save Parameters",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path_str:
            return
        self._do_save(Path(path_str))

    def _do_save(self, path: Path) -> None:
        params = self.analyzer_frame.get_parameters()
        if params is None:
            return
        try:
            save_parameters(params, path)
        except OSError as exc:
            messagebox.showerror("Save Error", str(exc))
            return
        self.current_file = path
        self.add_recent_file(path)

    # ------------------------------------------------------------------
    # View switching
    # ------------------------------------------------------------------

    def _hide_all_content_frames(self) -> None:
        """Remove all content frames from the grid."""
        self.analyzer_frame.grid_remove()
        self.editor_frame.grid_remove()
        self.ui_examples_frame.grid_remove()
        self.navigation_frame.grid_remove()
        self.navigation_panel.grid_remove()

    def show_analyzer_frame(self) -> None:
        """Switch the main content area to the AnalyzerFrame."""
        self.sidebar.select_analyzer()
        self._hide_all_content_frames()
        self.analyzer_frame.grid()
        self.main_content = self.analyzer_frame  # type: ignore[assignment]
        self.menubar.main_content = self.main_content

    def show_editor_frame(self) -> None:
        """Switch the main content area to the EditorFrame."""
        self.sidebar.select_editor()
        self._hide_all_content_frames()
        self.editor_frame.grid()
        self.main_content = self.editor_frame  # type: ignore[assignment]
        self.menubar.main_content = self.main_content

    def show_ui_examples_frame(self) -> None:
        """Switch the main content area to the UiExamplesFrame."""
        self.sidebar.select_ui_examples()
        self._hide_all_content_frames()
        self.ui_examples_frame.grid()
        self.main_content = self.ui_examples_frame  # type: ignore[assignment]
        self.menubar.main_content = self.main_content

    def show_navigation_frame(self) -> None:
        """Switch the main content area to the NavigationFrame."""
        self.sidebar.select_navigation()
        if self.main_content != self.navigation_frame:
            self._hide_all_content_frames()
            self.navigation_frame.grid()
            self.main_content = self.navigation_frame  # type: ignore[assignment]
            self.menubar.main_content = self.main_content

    # ------------------------------------------------------------------
    # Parameter synchronization
    # ------------------------------------------------------------------

    def update_parameters(self, params: SignalParameters, source: str) -> None:
        """Synchronize *params* across all views.

        Parameters
        ----------
        params:
            New parameter set to broadcast.
        source:
            Origin of the change.  ``"analyzer"`` skips updating the analyzer
            widgets (they are already up to date); ``"editor"`` skips updating
            the editor text.  Any other value (e.g. ``"file"``) updates both.
        """
        if source != "analyzer":
            self.analyzer_frame.set_parameters(params)
        if source != "editor":
            self.editor_frame.set_json(params.model_dump_json(indent=2))

    def _apply_editor_json(self, json_text: str) -> None:
        """Parse *json_text* from the Editor and synchronize both views."""
        try:
            data = json.loads(json_text)
            params = SignalParameters.model_validate(data)
        except json.JSONDecodeError as exc:
            self.editor_frame.show_error(f"Invalid JSON: {exc}")
            return
        except ValidationError as exc:
            first = exc.errors()[0]
            msg = first.get("msg", str(exc))
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, "):]
            self.editor_frame.show_error(msg)
            return
        # Re-populate both views with canonical params (normalizes formatting in editor)
        self.editor_frame.show_error("")
        self.analyzer_frame.set_parameters(params)
        self.editor_frame.set_json(params.model_dump_json(indent=2))

    # ------------------------------------------------------------------
    # Navigation-panel toggle
    # ------------------------------------------------------------------

    def toggle_navigation_frame(self) -> None:
        """Show or hide the navigation panel beside the sidebar."""
        if self._is_navigation_panel_visible:
            self.navigation_panel.grid_remove()
        else:
            self.navigation_panel.grid()
        self._is_navigation_panel_visible = not self._is_navigation_panel_visible

    def _on_global_node_select(self, hierarchy: str) -> None:
        """Handle node selection from the global navigation panel."""
        if hasattr(self.main_content, "update_content"):
            self.main_content.update_content(hierarchy)  # type: ignore[attr-defined]


if __name__ == "__main__":
    app = Application()
    app.mainloop()
