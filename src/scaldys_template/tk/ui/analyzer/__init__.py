"""Signal analyzer UI sub-package.

Contains the four frames that together make up the analyzer view:
- ``AnalyzerFrame``       — top-level layout, wires the others together
- ``PlotFrame``           — embedded matplotlib plots (time / spectrum / phase)
- ``SignalParametersFrame`` — parameter entry panel
- ``ResultsTableFrame``   — tabbed results table + metrics bar
"""

from scaldys_template.tk.ui.analyzer.analyzer_frame import AnalyzerFrame
from scaldys_template.tk.ui.analyzer.plot_frame import PlotFrame
from scaldys_template.tk.ui.analyzer.results_table_frame import ResultsTableFrame
from scaldys_template.tk.ui.analyzer.signal_parameters_frame import SignalParametersFrame

__all__ = ["AnalyzerFrame", "PlotFrame", "ResultsTableFrame", "SignalParametersFrame"]
