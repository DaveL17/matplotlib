# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Small color/marker formatting utilities shared by plugin.py.

Deliberately separate from chart_tools.py: that module parses sys.argv[1] as a chart payload at
import time (it's meant to be loaded only by the chart_*.py subprocess scripts), so importing it
from plugin.py's own process risks executing that parsing against the plugin process's unrelated
argv. This module has no import-time side effects and is safe for plugin.py to import directly.
"""


def __init__() -> None:
    """Initialize the color_utils module (no-op placeholder)."""


# =============================================================================
def fix_rgb(color: str = "") -> str:  # noqa
    """Normalize a color string to the '#RRGGBB' hex format expected by matplotlib.

    Strips spaces and any leading '#' characters from the input, then prepends a single '#'.

    The leading '#' is required here: this value is used directly as a matplotlib Artist color
    kwarg (e.g. bar/line color), and matplotlib.colors.to_rgba() rejects a bare hex string
    ('FF0000' raises ValueError) but accepts the '#'-prefixed form. Don't drop the '#' -- the
    Stylesheets writer (charts_refresh(), where rcParams is serialized to a '.mplstyle' file)
    strips it back off there instead, because '#' starts a comment in that file format and a
    '#'-prefixed color would be silently dropped to matplotlib's default. The two are a matched
    pair for two different matplotlib color-format conventions, not redundant steps.

    Args:
        color (str): A color string in any format (e.g., "FF 00 00", "#FF0000").

    Returns:
        str: A normalized hex color string in '#RRGGBB' format.
    """
    rgb_fixed = color.replace(' ', '').replace('#', '')
    return f"#{rgb_fixed}"


# =============================================================================
def format_markers(p_dict: dict = None) -> dict:  # noqa
    """Convert XML-safe marker placeholder strings to the actual matplotlib marker characters.

    The Devices.xml file cannot contain '<' or '>' as values because they conflict with XML
    syntax. This method converts the safe placeholder strings ('PIX', 'TL', 'TR') to their actual
    matplotlib marker equivalents (',', '<', '>').

    Args:
        p_dict (dict): The plotting parameters dictionary containing marker key/value pairs.

    Returns:
        dict: The updated p_dict with marker values converted to matplotlib-compatible strings.
    """
    markers     = (
        'area1Marker', 'area2Marker', 'area3Marker', 'area4Marker', 'area5Marker', 'area6Marker', 'area7Marker',
        'area8Marker', 'line1Marker', 'line2Marker', 'line3Marker', 'line4Marker', 'line5Marker', 'line6Marker',
        'line7Marker', 'line8Marker', 'group1Marker', 'group2Marker', 'group3Marker', 'group4Marker'
    )

    marker_dict = {"PIX": ",", "TL": "<", "TR": ">"}

    for marker in markers:
        try:
            if p_dict[marker] in marker_dict:
                p_dict[marker] = marker_dict[p_dict[marker]]
        except KeyError:
            ...

    return p_dict
