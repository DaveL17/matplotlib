# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the multiline text charts

Given the unique nature of multiline text charts, we use a separate method to construct them.
"""

# Built-in Modules
import json
import sys
import textwrap
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import patches
# My Modules
import chart_tools  # noqa

LOG          = chart_tools.LOG
PAYLOAD      = chart_tools.payload
P_DICT       = PAYLOAD['p_dict']
K_DICT       = PAYLOAD['k_dict']
PROPS        = PAYLOAD['props']
CHART_NAME   = PROPS['name']
PLUG_DICT    = PAYLOAD['prefs']
TEXT_TO_PLOT = PAYLOAD['data']

LOG['Threaddebug'].append("chart_multiline.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")

try:

    def __init__():
        """
        Title Placeholder

        Body placeholder
        :return:
        """

    def clean_string(val):
        """
        Cleans long strings of whitespace and formats certain characters

        The clean_string(self, val) method is used to scrub multiline text elements in order to
        try to make them more presentable. The need is easily seen by looking at the rough text
        that is provided by the U.S. National Weather Service, for example.
        -----
        :param unicode val:
        :return val:
        """

        # List of (elements, replacements)
        clean_list = (
            (' am ', ' AM '),
            (' pm ', ' PM '),
            ('*', ' '),
            ('\u000A', ' '),
            ('...', ' '),
            ('/ ', '/'),
            (' /', '/'),
            ('/', ' / ')
        )

        # Take the old, and replace it with the new.
        for (old, new) in clean_list:
            val = val.replace(old, new)

        val = ' '.join(val.split())  # Eliminate spans of whitespace.

        return val

    P_DICT['figureWidth'] = float(PROPS['figureWidth'])
    P_DICT['figureHeight'] = float(PROPS['figureHeight'])

    try:
        height = int(PROPS.get('figureHeight', 300)) / int(plt.rcParams['savefig.dpi'])
        if height < 1:
            height = 1
            LOG['Warning'].append(
                f"[{CHART_NAME}] Height: Pixels / DPI can not be less than one. Coercing to one."
            )
    except ValueError:
        height = 3

    try:
        width = int(PROPS.get('figureWidth', 500)) / int(plt.rcParams['savefig.dpi'])
        if width < 1:
            width = 1
            LOG['Warning'].append(
                f"[{CHART_NAME}] Width: Pixels / DPI can not be less than one. Coercing to one."
            )
    except ValueError:
        width = 5

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # If the value to be plotted is empty, use the default text from the device configuration.
    if len(TEXT_TO_PLOT) <= 1:
        TEXT_TO_PLOT = P_DICT['defaultText']

    else:
        # The clean_string method tries to remove some potential ugliness from the text to be
        # plotted. It's optional--defaulted to on. No need to call this if the default text is used.
        if P_DICT['cleanTheText']:
            TEXT_TO_PLOT = clean_string(val=TEXT_TO_PLOT)

    if PLUG_DICT['verboseLogging']:
        LOG['Threaddebug'].append(f"[{CHART_NAME}] Data: {TEXT_TO_PLOT}")

    # Wrap the text and prepare it for plotting.
    TEXT_TO_PLOT = textwrap.fill(
        text=TEXT_TO_PLOT,
        width=int(P_DICT['numberOfCharacters']),
        replace_whitespace=P_DICT['cleanTheText']
    )

    ax.text(
        0.01, 0.95,
        TEXT_TO_PLOT,
        transform=ax.transAxes,
        fontname=P_DICT['fontMain'],
        verticalalignment='top'
    )

    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    if not P_DICT['textAreaBorder']:
        _ = [s.set_visible(False) for s in ax.spines.values()]

    # Transparent Charts Fill
    if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
        ax.add_patch(
            patches.Rectangle(
                (0, 0), 1, 1,
                transform=ax.transAxes,
                # facecolor=P_DICT['faceColor'],
                zorder=1
            )
        )

    # =============================== Format Title ================================
    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.98), align='center')

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
