"""Comprehensive ttkbootstrap widget showcase.

``ExampleFrame`` demonstrates every major widget category available in
ttkbootstrap.  It is intended as a living reference: delete sections that are
not relevant to your project and replace them with your own content.
"""

import tkinter as tk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import (
    BOTH,
    CENTER,
    DANGER,
    DISABLED,
    END,
    HEADINGS,
    HORIZONTAL,
    INFO,
    LEFT,
    LINK,
    NE,
    NW,
    OUTLINE,
    RIGHT,
    ROUND,
    SECONDARY,
    SQUARE,
    STRIPED,
    SUCCESS,
    TOGGLE,
    TOOLBUTTON,
    TOP,
    WARNING,
    X,
    YES,
)

# ---------------------------------------------------------------------------
# Module-level constant (removed from inside _initialize)
# ---------------------------------------------------------------------------

_ZEN = """\
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!\
"""


class ExampleFrame(tb.Frame):
    """Widget showcase frame.

    Parameters
    ----------
    master:
        Parent widget.
    on_theme_change:
        Optional callback invoked after the user selects a new theme.
        Use this to let the parent (``Application``) update its own
        theme-dependent styles.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_theme_change: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_theme_change = on_theme_change
        self._initialize()

    # ------------------------------------------------------------------
    # Top-level layout
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        self._create_theme_selector()
        tb.Separator(self).pack(fill=X, pady=10, padx=10)

        lframe = tb.Frame(self, padding=5)
        lframe.pack(side=LEFT, fill=BOTH, expand=YES)

        rframe = tb.Frame(self, padding=5)
        rframe.pack(side=RIGHT, fill=BOTH, expand=YES)

        self._create_color_swatches(lframe)
        self._create_checkbuttons(lframe)
        self._create_treeview_and_notebook(lframe)
        self._create_text_widget(lframe)
        self._create_scales_and_meters(lframe)

        self._create_button_gallery(rframe)
        self._create_input_widgets(rframe)

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _create_theme_selector(self) -> None:
        """Theme-switcher row at the top of the frame."""
        style = tb.Style()
        theme_names = style.theme_names()

        container = tb.Frame(self, padding=(10, 10, 10, 0))
        container.pack(fill=X, expand=YES)

        # StringVar shared between the large label and the combobox so both
        # update automatically when a new theme is selected.
        self._theme_var = tk.StringVar(value=style.theme.name)

        tb.Label(container, textvariable=self._theme_var, font="-size 24 -weight bold").pack(
            side=LEFT
        )
        tb.Label(container, text="Select a theme:").pack(side=RIGHT)

        theme_cbo = tb.Combobox(container, textvariable=self._theme_var, values=theme_names)
        theme_cbo.pack(padx=10, side=RIGHT)
        theme_cbo.current(theme_names.index(style.theme.name))

        def on_theme_selected(_event: tk.Event) -> None:  # type: ignore[type-arg]
            new_theme = theme_cbo.get()
            style.theme_use(new_theme)
            self._theme_var.set(new_theme)
            theme_cbo.selection_clear()
            self.focus_set()
            if self._on_theme_change:
                self._on_theme_change()

        theme_cbo.bind("<<ComboboxSelected>>", on_theme_selected)

    def _create_color_swatches(self, parent: tb.Frame) -> None:
        """Row of buttons showing each theme colour."""
        style = tb.Style()
        group = tb.Labelframe(parent, text="Theme color options", padding=10)
        group.pack(fill=X, side=TOP)

        for color in style.colors:
            tb.Button(group, text=color, bootstyle=color).pack(
                side=LEFT, expand=YES, padx=5, fill=X
            )

    def _create_checkbuttons(self, parent: tb.Frame) -> None:
        """Checkbuttons and radiobuttons in all states."""
        group = tb.Labelframe(parent, text="Checkbuttons & radiobuttons", padding=10)
        group.pack(fill=X, pady=10, side=TOP)

        check1 = tb.Checkbutton(group, text="selected")
        check1.pack(side=LEFT, expand=YES, padx=5)
        check1.invoke()

        check2 = tb.Checkbutton(group, text="deselected")
        check2.pack(side=LEFT, expand=YES, padx=5)

        tb.Checkbutton(group, text="disabled", state=DISABLED).pack(side=LEFT, expand=YES, padx=5)

        radio1 = tb.Radiobutton(group, text="selected", value=1)
        radio1.pack(side=LEFT, expand=YES, padx=5)
        radio1.invoke()

        tb.Radiobutton(group, text="deselected", value=2).pack(side=LEFT, expand=YES, padx=5)
        tb.Radiobutton(group, text="disabled", value=3, state=DISABLED).pack(
            side=LEFT, expand=YES, padx=5
        )

    def _create_treeview_and_notebook(self, parent: tb.Frame) -> None:
        """Treeview (table) and tabbed notebook side by side."""
        container = tb.Frame(parent)
        container.pack(pady=5, fill=X, side=TOP)

        table_data = [
            ("South Island, New Zealand", 1),
            ("Paris", 2),
            ("Bora Bora", 3),
            ("Maui", 4),
            ("Tahiti", 5),
        ]

        tv = tb.Treeview(container, columns=[0, 1], show=HEADINGS, height=5)
        for row in table_data:
            tv.insert("", END, values=row)
        tv.selection_set("I001")
        tv.heading(0, text="City")
        tv.heading(1, text="Rank")
        tv.column(0, width=300)
        tv.column(1, width=70, anchor=CENTER)
        tv.pack(side=LEFT, anchor=NE, fill=X)

        nb = tb.Notebook(container)
        nb.pack(side=LEFT, padx=(10, 0), expand=YES, fill=BOTH)
        nb.add(
            tb.Label(nb, text="This is a notebook tab.\nYou can put any widget here."),
            text="Tab 1",
            sticky=NW,
        )
        nb.add(tb.Label(nb, text="A second notebook tab."), text="Tab 2", sticky=NW)
        nb.add(tb.Frame(nb), text="Tab 3")
        nb.add(tb.Frame(nb), text="Tab 4")
        nb.add(tb.Frame(nb), text="Tab 5")

    def _create_text_widget(self, parent: tb.Frame) -> None:
        """Scrollable text widget pre-filled with the Zen of Python."""
        txt = tb.Text(parent, height=5, width=50, wrap="none")
        txt.insert(END, _ZEN)
        txt.pack(side=LEFT, anchor=NW, pady=5, fill=BOTH, expand=YES)

    def _create_scales_and_meters(self, parent: tb.Frame) -> None:
        """Scale, progress bars, meter, and scrollbars."""
        container = tb.Frame(parent)
        container.pack(fill=BOTH, expand=YES, padx=10)

        tb.Scale(container, orient=HORIZONTAL, value=75, from_=100, to=0).pack(
            fill=X, pady=5, expand=YES
        )

        tb.Progressbar(container, orient=HORIZONTAL, value=50).pack(fill=X, pady=5, expand=YES)
        tb.Progressbar(container, orient=HORIZONTAL, value=75, bootstyle=(SUCCESS, STRIPED)).pack(
            fill=X, pady=5, expand=YES
        )

        tb.Meter(
            container,
            metersize=150,
            amountused=45,
            subtext="meter widget",
            bootstyle=INFO,
            interactive=True,
        ).pack(pady=10)

        sb1 = tb.Scrollbar(container, orient=HORIZONTAL)
        sb1.set(0.1, 0.9)
        sb1.pack(fill=X, pady=5, expand=YES)

        sb2 = tb.Scrollbar(container, orient=HORIZONTAL, bootstyle=(DANGER, ROUND))
        sb2.set(0.1, 0.9)
        sb2.pack(fill=X, pady=5, expand=YES)

    def _create_button_gallery(self, parent: tb.Frame) -> None:
        """All ttkbootstrap button styles in one group."""
        style = tb.Style()
        theme_names = style.theme_names()

        group = tb.Labelframe(parent, text="Buttons", padding=(10, 5))
        group.pack(fill=X)

        theme_menu = tb.Menu(self)
        for i, t in enumerate(theme_names):
            theme_menu.add_radiobutton(label=t, value=i)

        default = tb.Button(group, text="solid button")
        default.pack(fill=X, pady=5)
        default.focus_set()

        tb.Menubutton(group, text="solid menubutton", bootstyle=SECONDARY, menu=theme_menu).pack(
            fill=X, pady=5
        )

        cb = tb.Checkbutton(group, text="solid toolbutton", bootstyle=(SUCCESS, TOOLBUTTON))
        cb.invoke()
        cb.pack(fill=X, pady=5)

        tb.Button(group, text="outline button", bootstyle=(INFO, OUTLINE)).pack(fill=X, pady=5)
        tb.Menubutton(
            group, text="outline menubutton", bootstyle=(WARNING, OUTLINE), menu=theme_menu
        ).pack(fill=X, pady=5)
        tb.Checkbutton(
            group, text="outline toolbutton", bootstyle=(SUCCESS, OUTLINE, TOOLBUTTON)
        ).pack(fill=X, pady=5)
        tb.Button(group, text="link button", bootstyle=LINK).pack(fill=X, pady=5)

        cb1 = tb.Checkbutton(group, text="rounded toggle", bootstyle=(SUCCESS, ROUND, TOGGLE))
        cb1.invoke()
        cb1.pack(fill=X, pady=5)

        cb2 = tb.Checkbutton(group, text="squared toggle", bootstyle=(SQUARE, TOGGLE))
        cb2.invoke()
        cb2.pack(fill=X, pady=5)

    def _create_input_widgets(self, parent: tb.Frame) -> None:
        """Text entry, spinbox, combobox, and date picker."""
        style = tb.Style()
        theme_names = style.theme_names()

        group = tb.Labelframe(parent, text="Other input widgets", padding=10)
        group.pack(fill=BOTH, pady=(10, 5), expand=YES)

        entry = tb.Entry(group)
        entry.pack(fill=X)
        entry.insert(END, "entry widget")

        password = tb.Entry(group, show="•")
        password.pack(fill=X, pady=5)
        password.insert(END, "password")

        spinbox = tb.Spinbox(group, from_=0, to=100)
        spinbox.pack(fill=X)
        spinbox.set(45)

        cbo = tb.Combobox(group, text=style.theme.name, values=theme_names, exportselection=False)
        cbo.pack(fill=X, pady=5)
        cbo.current(theme_names.index(style.theme.name))

        tb.DateEntry(group).pack(fill=X)
