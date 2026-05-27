"""JSON parameter editor frame."""

from __future__ import annotations

import tkinter as tk
from typing import Any, Callable

import ttkbootstrap as tb
from ttkbootstrap.constants import BOTH, YES

__all__ = ["EditorFrame"]


class EditorFrame(tb.Frame):
    """Text-based JSON editor for ``SignalParameters``.

    Parameters
    ----------
    master:
        Parent widget.
    on_apply:
        Callback invoked with the raw JSON text when the user clicks "Apply".
        The caller is responsible for parsing, validating, and syncing state.
    **kwargs:
        Passed to ``tb.Frame``.
    """

    def __init__(
        self,
        master: tk.Misc,
        on_apply: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, **kwargs)
        self._on_apply = on_apply
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Header row: title
        header = tb.Frame(self, padding=(8, 8, 8, 4))
        header.pack(fill="x")
        tb.Label(header, text="JSON Editor", font=("TkDefaultFont", 10, "bold")).pack(side="left")

        # Text widget with scrollbars (grid-based to allow both axes)
        text_frame = tb.Frame(self, padding=(8, 0, 8, 0))
        text_frame.pack(fill=BOTH, expand=YES)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._text = tk.Text(
            text_frame,
            wrap="none",
            font=("Courier New", 10),
            undo=True,
        )
        scroll_y = tb.Scrollbar(text_frame, orient="vertical", command=self._text.yview)
        scroll_x = tb.Scrollbar(text_frame, orient="horizontal", command=self._text.xview)
        self._text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self._text.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        # Status label for validation / parse errors
        self._status_var = tk.StringVar()
        tb.Label(
            self,
            textvariable=self._status_var,
            bootstyle="danger",
            wraplength=500,
            padding=(8, 2, 8, 6),
        ).pack(fill="x")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_json(self, text: str) -> None:
        """Replace the editor contents with *text* and clear any error message."""
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._status_var.set("")

    def get_json(self) -> str:
        """Return the current editor contents (trailing newline stripped)."""
        return self._text.get("1.0", "end-1c")

    def show_error(self, message: str) -> None:
        """Display *message* in the status label; pass an empty string to clear it."""
        self._status_var.set(message)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_apply(self) -> None:
        if self._on_apply is not None:
            self._on_apply(self.get_json())
