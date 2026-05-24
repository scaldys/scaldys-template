"""Side panel shown/hidden when the sidebar play button is toggled.

Replace the placeholder content with application-specific controls such as a
playback queue, a tree of items to process, or any secondary navigation widget.
"""

from typing import Any

import ttkbootstrap as tb


class PlayPanel(tb.Frame):
    """Collapsible side panel positioned between the sidebar and the main content.

    Toggled via :py:meth:`~scaldys_template.tk.app.Application.toggle_play_frame`.
    """

    def __init__(self, master: tb.Window, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._initialize()

    def _initialize(self) -> None:
        tb.Label(self, text="Play Panel", padding=(10, 5)).pack(side="top", fill="x")
        tb.Separator(self, orient="horizontal").pack(fill="x", padx=5)
        # Replace this placeholder with your playback controls or tree widget.
        tb.Label(self, text="(placeholder)", foreground="gray", padding=(10, 5)).pack(
            side="top", fill="x"
        )
