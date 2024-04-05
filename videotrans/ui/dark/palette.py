# -*- coding: utf-8 -*-

"""QDarkStyle default dark palette."""

# Local imports
from qdarkstyle.colorsystem import Blue, Gray
from qdarkstyle.palette import Palette


class DarkPalette(Palette):
    """Dark palette variables."""

    # Identifier
    ID = 'dark'

    # Color
    COLOR_BACKGROUND_1 = Gray.B10
    COLOR_BACKGROUND_2 = Gray.B20
    COLOR_BACKGROUND_3 = Gray.B30
    COLOR_BACKGROUND_4 = Gray.B40
    COLOR_BACKGROUND_5 = Gray.B50
    COLOR_BACKGROUND_6 = Gray.B60

    COLOR_TEXT_1 = Gray.B130
    COLOR_TEXT_2 = Gray.B110
    COLOR_TEXT_3 = Gray.B90
    COLOR_TEXT_4 = Gray.B80

    COLOR_ACCENT_1 = Blue.B20
    COLOR_ACCENT_2 = Blue.B40
    COLOR_ACCENT_3 = Blue.B50
    COLOR_ACCENT_4 = Blue.B70
    COLOR_ACCENT_5 = Blue.B80

    # Color for disabled elements
    COLOR_DISABLED = Gray.B70

    OPACITY_TOOLTIP = 230
