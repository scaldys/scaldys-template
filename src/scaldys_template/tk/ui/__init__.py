"""UI component sub-package.

Exports the main frame classes so callers can import them without knowing
the internal module layout::

    from scaldys_template.tk.ui import AnalyzerFrame, ExampleFrame, PlayPanel
"""

from scaldys_template.tk.ui.analyzer.analyzer_frame import AnalyzerFrame
from scaldys_template.tk.ui.example_frame import ExampleFrame
from scaldys_template.tk.ui.play_frame import PlayPanel

__all__ = ["AnalyzerFrame", "ExampleFrame", "PlayPanel"]
