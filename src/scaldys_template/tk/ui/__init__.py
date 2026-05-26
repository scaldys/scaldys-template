"""UI component sub-package.

Exports the main frame classes so callers can import them without knowing
the internal module layout::

    from scaldys_template.tk.ui import AnalyzerFrame, UiExamplesFrame, PlayFrame, PlayPanel
"""

from scaldys_template.tk.ui.analyzer.analyzer_frame import AnalyzerFrame
from scaldys_template.tk.ui.ui_examples_frame import UiExamplesFrame
from scaldys_template.tk.ui.play_frame import PlayFrame, PlayPanel

__all__ = ["AnalyzerFrame", "UiExamplesFrame", "PlayFrame", "PlayPanel"]
