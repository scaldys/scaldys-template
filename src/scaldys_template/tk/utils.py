"""Windows-specific GUI utilities.

All public functions degrade gracefully on non-Windows platforms — wrap
platform-specific calls in ``try/except Exception`` so the module is safe to
import anywhere.
"""

import ctypes as ct
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import tkinter as tk


def set_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness on Windows 10+.

    Call once before creating any Tkinter windows.  Has no effect on
    other platforms.
    """
    try:
        from ctypes import windll  # type: ignore[attr-defined]

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def dark_title_bar(window: "tk.Wm") -> None:
    """Apply a dark title bar on Windows 11+.

    The window must already be visible; call after ``window.update()``.
    Has no effect on other platforms.

    References
    ----------
    https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    """
    try:
        window.update()  # type: ignore[attr-defined]
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute  # type: ignore[attr-defined]
        hwnd = ct.windll.user32.GetParent(window.winfo_id())  # type: ignore[attr-defined]
        value = ct.c_int(2)
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ct.byref(value), ct.sizeof(value))
    except Exception:
        pass
