"""UI component sub-package.

Exports the main frame classes so callers can import them without knowing
the internal module layout::

    from scaldys_template.tk.ui import AnalyzerFrame, EditorFrame, UiExamplesFrame, NavigationFrame, NavigationPanel
"""

from scaldys_template.tk.ui.analyzer.analyzer_frame import AnalyzerFrame
from scaldys_template.tk.ui.editor_frame import EditorFrame
from scaldys_template.tk.ui.ui_examples_frame import UiExamplesFrame
from scaldys_template.tk.ui.navigation_frame import NavigationFrame, NavigationPanel

__all__ = ["AnalyzerFrame", "EditorFrame", "UiExamplesFrame", "NavigationFrame", "NavigationPanel"]
