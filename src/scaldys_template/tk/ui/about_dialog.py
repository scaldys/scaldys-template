# -*- coding: utf-8 -*-
"""About dialog for the application."""

import webbrowser
from pathlib import Path
from typing import Any

import tkinter as tk
import ttkbootstrap as tb

from scaldys_template.__about__ import APP_NAME, ORGANIZATION_NAME, PACKAGE_NAME, VERSION
import scaldys_template.tk.fontawesome_icons as faw

_TEMPLATE_URL = "https://github.com/scaldys/scaldys-template"
_PROJECT_URL = "https://github.com/scaldys/scaldys-project"
_COPYRIGHT = f"\u00a9 2024\u20262026 {ORGANIZATION_NAME}"
_LICENSE = "MIT License"


def _load_app_icon(size: int) -> Any:
    """Try to load the application .ico as a PhotoImage; return ``None`` on failure."""
    try:
        import sys
        from PIL import Image, ImageTk  # type: ignore[import-untyped]

        candidates: list[Path] = []

        # PyInstaller frozen bundle (_MEIPASS is injected at runtime)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass is not None:
            candidates.append(Path(meipass) / "scaldys-template.ico")

        # Development layout: this file lives at
        #   src/scaldys_template/tk/ui/about_dialog.py
        # Four parents up → project root
        candidates.append(
            Path(__file__).parents[4] / "packaging" / "windows" / "scaldys-template.ico"
        )

        # Image.Resampling.LANCZOS (Pillow ≥ 9.1); fall back to the legacy int alias
        resample = getattr(Image, "Resampling", Image).LANCZOS  # type: ignore[attr-defined]

        for path in candidates:
            if path.exists():
                img = Image.open(path).convert("RGBA").resize((size, size), resample)
                return ImageTk.PhotoImage(img)
    except Exception:
        pass
    return None


class AboutDialog(tk.Toplevel):
    """Modal About dialog showing application metadata and project links."""

    def __init__(self, master: tk.Misc, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self.title(f"About {APP_NAME}")
        self.resizable(False, False)
        self.grab_set()  # make modal
        self._build()
        self._center()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        outer = tb.Frame(self, padding=24)
        outer.pack(fill="both", expand=True)

        # ── Icon + title ────────────────────────────────────────────
        header = tb.Frame(outer)
        header.pack(pady=(0, 4))

        icon_size = 48
        self._icon_image = _load_app_icon(icon_size)
        if self._icon_image is None:
            # Fallback: use the gear SVG already bundled with the app
            self._icon_image = faw.icon_to_image(
                faw.Icons.gear_solid, fill="white", scale_to_width=icon_size
            )

        tb.Label(header, image=self._icon_image).pack()
        tb.Label(header, text=APP_NAME, font=("", 16, "bold")).pack(pady=(10, 0))
        tb.Label(header, text=f"Version {VERSION}", bootstyle="fg").pack(pady=(2, 0))

        tb.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        # ── Description + author ────────────────────────────────────
        _description = self._read_description()
        if _description:
            tb.Label(outer, text=_description, wraplength=360, justify="center").pack()
            tb.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        # ── Copyright + licence ─────────────────────────────────────
        tb.Label(
            outer,
            text=f"{_COPYRIGHT}\u2003\u00b7\u2003{_LICENSE}",
            bootstyle="fg",
        ).pack()

        tb.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        # ── Project links ───────────────────────────────────────────
        links = tb.Frame(outer)
        links.pack()

        self._add_link_row(links, "Based on:", "scaldys-template", _TEMPLATE_URL)
        self._add_link_row(links, "Compliant with:", "scaldys-project", _PROJECT_URL)

        tb.Separator(outer, orient="horizontal").pack(fill="x", pady=14)

        # ── Close button ────────────────────────────────────────────
        tb.Button(
            outer,
            text="Close",
            command=self.destroy,
            bootstyle="primary",
            width=12,
        ).pack(pady=(18, 0))

    def _add_link_row(self, parent: tb.Frame, label: str, link_text: str, url: str) -> None:
        """Add a labelled, clickable hyperlink row."""
        import tkinter.font as tkfont

        row = tb.Frame(parent)
        row.pack(anchor="w", pady=3)

        tb.Label(row, text=label).pack(side="left")

        lnk = tb.Label(
            row,
            text=f"  {link_text}  \u2197",
            bootstyle="info",
            cursor="hand2",
        )
        lnk.pack(side="left")

        # Build underline/normal font variants from TkDefaultFont so the size
        # never changes on hover.
        _base = tkfont.nametofont("TkDefaultFont").copy()
        _underline = _base.copy()
        _underline.configure(underline=True)

        lnk.bind("<Button-1>", lambda _e, u=url: webbrowser.open(u))
        lnk.bind("<Enter>", lambda _e: lnk.configure(font=_underline))
        lnk.bind("<Leave>", lambda _e: lnk.configure(font=_base))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_description() -> str:
        """Return the package Summary from importlib.metadata, or empty string."""
        try:
            from importlib.metadata import metadata

            return metadata(PACKAGE_NAME).get("Summary", "")
        except Exception:
            return ""

    def _center(self) -> None:
        """Centre the dialog over its parent window."""
        self.update_idletasks()
        master = self.master
        x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
        y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
