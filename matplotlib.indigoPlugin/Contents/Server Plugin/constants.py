# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Repository of application constants.

The constants.py file contains all application constants and is imported as a library. References are denoted as
constants by the use of all caps.
"""

from typing import Dict, List, Tuple


# =============================================================================
def __init__() -> None:
    """Initialize the constants module (no-op placeholder)."""


CLEAN_LIST: Tuple[Tuple[str, str], ...] = (
    (' am ', ' AM '),
    (' pm ', ' PM '),
    ('*', ' '),
    ('\u000A', ' '),
    ('...', ' '),
    ('/ ', '/'),
    (' /', '/'),
    ('/', ' / ')
)

DEBUG_LABELS: Dict[int, str] = {
    10: "Debugging Messages",
    20: "Informational Messages",
    30: "Warning Messages",
    40: "Error Messages",
    50: "Critical Errors Only"
}

FONT_MENU: List[str] = [
    'Arial',
    'Apple Chancery',
    'Andale Mono',
    'Bitstream Vera Sans',
    'Bitstream Vera Sans Mono',
    'Bitstream Vera Serif',
    'Century Schoolbook L',
    'Charcoal',
    'Chicago',
    'Comic Sans MS',
    'Courier',
    'Courier New',
    'cursive',
    'fantasy',
    'Felipa',
    'Geneva',
    'Helvetica',
    'Humor Sans',
    'Impact',
    'Lucinda Grande',
    'Lucid',
    'New Century Schoolbook',
    'Nimbus Mono L',
    'Sand',
    'Script MT',
    'Textile',
    'Verdana',
    'Western',
    'Zapf Chancery'
]
