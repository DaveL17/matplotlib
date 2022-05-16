# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Title Placeholder

Body placeholder
see also https://stackoverflow.com/a/49733577/2827397
"""

import json
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
# from matplotlib import patches
# My modules
import chart_tools  # noqa

LOG               = chart_tools.LOG
PAYLOAD           = chart_tools.payload
PLOT_VALUE        = PAYLOAD['data']
P_DICT            = PAYLOAD['p_dict']
K_DICT            = PAYLOAD['k_dict']
PROPS             = PAYLOAD['props']
CHART_NAME        = PROPS['name']
PLUG_DICT         = PAYLOAD['prefs']
ANNOTATION_VALUES = []
BAR_COLORS        = []
X_LABELS          = []
X_TICKS           = []

# ================================== Globals ==================================
COLOR_LIGHT   = P_DICT['bar_1']
COLOR_DARK  = P_DICT['bar_2']
COLOR_FONT   = P_DICT['fontColor']
COLOR_BORDER = P_DICT['gridColor']
FONT_MAIN    = P_DICT['fontMain']
PRECISION    = P_DICT['precision']
ICON_HEIGHT  = P_DICT['sqChartSize']
ICON_WIDTH   = P_DICT['sqChartSize']
SLICE_WIDTH  = 0.35
PLOT_SCALE   = float(PAYLOAD.get('scale', P_DICT['scale']))
ZERO_LOC = int(P_DICT['startAngle'])

LOG['Threaddebug'].append("chart_bar_radial.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(PAYLOAD)
LOG['Threaddebug'].append(f"Value: {PLOT_VALUE} Scale: {PLOT_SCALE}")

try:

    def __init__():
        """
        Title Placeholder

        Body placeholder
        :return:
        """

    # ============================  Custom Font Size  =============================
    # User has selected a custom font size.
    if not P_DICT['customSizeFont']:
        size_font = P_DICT['mainFontSize']
    else:
        size_font = P_DICT['customTickFontSize']

    # ================================== Figure ===================================
    ax = chart_tools.make_chart_figure(width=ICON_WIDTH, height=ICON_HEIGHT, p_dict=P_DICT)
    ax.axis('equal')

    # ========================= Plot Figure and Decorate ==========================
    kwargs     = dict(colors=[COLOR_LIGHT, COLOR_DARK], startangle=ZERO_LOC)
    outside, _ = ax.pie(
        [PLOT_VALUE, PLOT_SCALE - PLOT_VALUE],
        radius=1,
        pctdistance=(1 - SLICE_WIDTH / 2),
        labels=['', ''],
        **kwargs
    )
    plt.setp(outside, width=SLICE_WIDTH, edgecolor=COLOR_BORDER)

    # =================================== Text ====================================
    kwargs = dict(
        size=size_font,
        fontweight='bold',
        va='center',
        color=COLOR_FONT,
        fontname=FONT_MAIN
    )
    ax.text(0, 0, str(f"{PLOT_VALUE:0.{PRECISION}f}"), ha='center', **kwargs)

    # ============================= Format Plot Area ==============================
    # Reduce whitespace around figure

    # RGBA setting background as transparent
    plt.rcParams.update({"savefig.facecolor": (0.0, 0.0, 1.0, 0.0)})

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
