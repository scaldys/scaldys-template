"""Centralised ttkbootstrap style name constants.

Keep all style names here so that renaming one string is safe and
grep-able. Child widgets import ``Styles`` instead of hard-coding strings.
"""


class Styles:
    """ttkbootstrap style names used across the application."""

    # Frame backgrounds (toolbar / sidebar shared colour)
    BARS_FRAME: str = "MyBars.TFrame"
    MENUBAR_FRAME: str = "MyMnubar.TFrame"
    DROPDOWN_FRAME: str = "MyDropDwn.TFrame"

    # Buttons inside the toolbar / sidebar
    BARS_BUTTON: str = "MyBars.TButton"
    BARS_BUTTON_LEFT_TEXT: str = "MyLeftTxt.MyBars.TButton"  # icon left, text right
    BARS_BUTTON_RIGHT_TEXT: str = "MyRightTxt.MyBars.TButton"  # icon right, text left

    # Menubutton without the default dropdown arrow
    NO_ARROW_MENUBUTTON: str = "MyNoArrow.TMenubutton"
