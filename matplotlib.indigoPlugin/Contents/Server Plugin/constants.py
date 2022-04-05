# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Repository of application constants

The constants.py file contains all application constants and is imported as a library. References
are denoted as constants by the use of all caps.
"""


# =============================================================================
def __init__():
    """
    Title Placeholder

    Body placeholder
    :return:
    """


CLEAN_LIST = (
    (' am ', ' AM '),
    (' pm ', ' PM '),
    ('*', ' '),
    ('\u000A', ' '),
    ('...', ' '),
    ('/ ', '/'),
    (' /', '/'),
    ('/', ' / ')
)

DEBUG_LABELS = {
    10: "Debugging Messages",
    20: "Informational Messages",
    30: "Warning Messages",
    40: "Error Messages",
    50: "Critical Errors Only"
}

FONT_MENU = [
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
