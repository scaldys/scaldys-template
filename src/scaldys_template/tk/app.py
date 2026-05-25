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
from scaldys_template.tk.ui import play_frame
from scaldys_template.tk.ui.analyzer import analyzer_frame
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
        if isinstance(self.main_content, analyzer_frame.AnalyzerFrame):
            self.main_content._on_run()

    def _cmd_save(self) -> None:
        if isinstance(self.main_content, analyzer_frame.AnalyzerFrame):
            self.main_content._on_save()

    def _cmd_load(self) -> None:
        if isinstance(self.main_content, analyzer_frame.AnalyzerFrame):
            self.main_content._on_load()

    def _cmd_reset(self) -> None:
        if isinstance(self.main_content, analyzer_frame.AnalyzerFrame):
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
        self._img_play = faw.icon_to_image(
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

        self._play_btn = tb.Button(
            buttonbar,
            text=_indent("Play"),
            image=self._img_play,
            compound="left",
            style=Styles.BARS_BUTTON,
            command=lambda: showinfo(message="Play — wire up your command here"),
        )
        self._play_btn.pack(side="left", ipadx=5, ipady=5)

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
    on_toggle_play:
        Callback invoked when the play button is clicked (toggles the play panel).
    """

    def __init__(
        self,
        master: tk.Misc,
        fg_color: str,
        bg_color: str,
        on_toggle_play: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._fg_color = fg_color
        self._bg_color = bg_color
        self._on_toggle_play = on_toggle_play
        self._has_labels = False

        self._load_icons()
        self._initialize()
        self._hide_labels()

    def _load_icons(self) -> None:
        size = 30
        self._img_left_arrow = faw.icon_to_image(
            faw.Icons.angle_left_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_right_arrow = faw.icon_to_image(
            faw.Icons.angle_right_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_left_arrows = faw.icon_to_image(
            faw.Icons.angles_left_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_right_arrows = faw.icon_to_image(
            faw.Icons.angles_right_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_hamburger = faw.icon_to_image(
            faw.Icons.bars_solid_full, fill=self._fg_color, scale_to_width=size
        )
        self._img_play = faw.icon_to_image(
            faw.Icons.circle_play_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_stop = faw.icon_to_image(
            faw.Icons.circle_stop_solid, fill=self._fg_color, scale_to_width=size
        )
        self._img_settings = faw.icon_to_image(
            faw.Icons.gear_solid, fill=self._fg_color, scale_to_width=size
        )

    def _initialize(self) -> None:
        pad: dict[str, Any] = {"ipadx": 5, "ipady": 15, "pady": 0, "fill": "x"}

        top = tb.Frame(self)
        top.pack(side="top", fill="x")

        bottom = tb.Frame(self)
        bottom.pack(side="bottom", fill="x")

        self._toggle_label_btn = tb.Button(
            top, image=self._img_right_arrows, takefocus=0, command=self._toggle_labels
        )
        # self._toggle_label_btn = tb.Button(
        #     top, image=self._img_hamburger, takefocus=0, command=self._toggle_labels
        # )
        self._toggle_label_btn.pack(side="top", **pad)

        self._play_btn = tb.Button(
            top, image=self._img_play, compound="left", takefocus=0, command=self._on_toggle_play
        )
        self._play_btn.pack(side="top", **pad)

        self._stop_btn = tb.Button(
            top,
            image=self._img_stop,
            compound="left",
            takefocus=0,
            command=lambda: showinfo(message="Stop — wire up your command here"),
        )
        self._stop_btn.pack(side="top", **pad)

        self._settings_btn = tb.Button(
            bottom,
            image=self._img_settings,
            compound="left",
            takefocus=0,
            command=lambda: showinfo(message="Settings — wire up your command here"),
        )
        self._settings_btn.pack(side="bottom", **pad)

    def _show_labels(self) -> None:
        self._toggle_label_btn.configure(
            image=self._img_left_arrows, style=Styles.BARS_BUTTON
        )
        # self._toggle_label_btn.configure(
        #     image=self._img_hamburger, style=Styles.BARS_BUTTON_RIGHT_TEXT
        # )
        self._play_btn.configure(text=_indent("Play"), style=Styles.BARS_BUTTON_LEFT_TEXT)
        self._stop_btn.configure(text=_indent("Stop"), style=Styles.BARS_BUTTON_LEFT_TEXT)
        self._settings_btn.configure(text=_indent("Settings"), style=Styles.BARS_BUTTON_LEFT_TEXT)
        self._has_labels = True

    def _hide_labels(self) -> None:
        self._toggle_label_btn.configure(
            # image=self._img_right_arrows, style=Styles.BARS_BUTTON_RIGHT_TEXT
            image=self._img_right_arrows, style=Styles.BARS_BUTTON
        )
        # self._toggle_label_btn.configure(
        #     image=self._img_hamburger, style=Styles.BARS_BUTTON
        # )
        self._play_btn.configure(text="", style=Styles.BARS_BUTTON)
        self._stop_btn.configure(text="", style=Styles.BARS_BUTTON)
        self._settings_btn.configure(text="", style=Styles.BARS_BUTTON)
        self._has_labels = False

    def _toggle_labels(self) -> None:
        if self._has_labels:
            self._hide_labels()
        else:
            self._show_labels()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class Application(tb.Window):
    """Root application window.

    Usage::

        app = Application()
        app.mainloop()
    """

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
        example frame.

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
        self.style.configure(Styles.BARS_BUTTON_LEFT_TEXT, anchor="w")
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

        # Content area: grid allows reliable show/hide of the play panel
        # without the order-sensitive pack_forget() / pack() dance.
        content = tb.Frame(self)
        content.pack(fill="both", expand=True)
        content.columnconfigure(2, weight=1)  # main content column expands
        content.rowconfigure(0, weight=1)

        self.sidebar = SideBar(
            content,
            fg_color=self.bars_fg_color,
            bg_color=self.bars_bg_color,
            on_toggle_play=self.toggle_play_frame,
            style=Styles.BARS_FRAME,
        )
        self.play_panel = play_frame.PlayPanel(content, style=Styles.BARS_FRAME)
        self.main_content = analyzer_frame.AnalyzerFrame(content)

        self.menubar.main_content = self.main_content

        self.sidebar.grid(row=0, column=0, sticky="ns", padx=0, pady=2)
        self.play_panel.grid(row=0, column=1, sticky="ns", padx=1, pady=2)
        self.play_panel.grid_remove()  # hidden by default
        self.main_content.grid(row=0, column=2, sticky="nsew")

        self._is_play_frame_visible: bool = False

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
    # Play-panel toggle
    # ------------------------------------------------------------------

    def toggle_play_frame(self) -> None:
        """Show or hide the play panel beside the sidebar."""
        if self._is_play_frame_visible:
            self.play_panel.grid_remove()
        else:
            self.play_panel.grid()
        self._is_play_frame_visible = not self._is_play_frame_visible


if __name__ == "__main__":
    app = Application()
    app.mainloop()
