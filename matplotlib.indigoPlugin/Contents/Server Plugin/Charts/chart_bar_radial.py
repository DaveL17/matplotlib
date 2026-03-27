# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the radial bar (donut) charts.

Renders a single value as a radial/donut-style bar chart using a pie chart with a hole cut out. The filled portion
represents the plotted value; the remainder represents the balance up to the scale maximum. See also
https://stackoverflow.com/a/49733577/2827397
"""

import json
import sys
import traceback
from typing import Dict, List
# Third-party Modules
from matplotlib import pyplot as plt
# My modules
import chart_tools  # noqa


LOG: Dict[str, List[str]] = chart_tools.LOG
PAYLOAD: dict             = chart_tools.payload
PLOT_VALUE: float         = PAYLOAD['data']
P_DICT: dict              = PAYLOAD['p_dict']
K_DICT: dict              = PAYLOAD['k_dict']
PROPS: dict               = PAYLOAD['props']
CHART_NAME: str           = PROPS['name']
PLUG_DICT: dict           = PAYLOAD['prefs']
# ================================== Globals ==================================
COLOR_LIGHT: str  = P_DICT['bar_1']
COLOR_DARK: str   = P_DICT['bar_2']
COLOR_FONT: str   = P_DICT['fontColor']
COLOR_BORDER: str = P_DICT['gridColor']
FONT_MAIN: str    = P_DICT['fontMain']
PRECISION: int    = P_DICT['precision']
ICON_HEIGHT: int  = P_DICT['sqChartSize']
ICON_WIDTH: int   = P_DICT['sqChartSize']
SLICE_WIDTH: float = 0.35
PLOT_SCALE: float  = float(PAYLOAD.get('scale', P_DICT['scale']))
ZERO_LOC: int      = int(P_DICT['startAngle'])

LOG['Threaddebug'].append("chart_bar_radial.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")
LOG['Threaddebug'].append(f"Value: {PLOT_VALUE} Scale: {PLOT_SCALE}")

try:

    def __init__() -> None:
        """Initialize the radial bar chart module (no-op placeholder)."""

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
    kwargs     = {"colors": [COLOR_LIGHT, COLOR_DARK], "startangle": ZERO_LOC}
    outside, _ = ax.pie(
        [PLOT_VALUE, PLOT_SCALE - PLOT_VALUE],
        radius=1,
        pctdistance=(1 - SLICE_WIDTH / 2),
        labels=['', ''],
        **kwargs
    )
    plt.setp(outside, width=SLICE_WIDTH, edgecolor=COLOR_BORDER)

    kwargs = {'color': COLOR_FONT,
              'fontname': FONT_MAIN,
              'fontweight': 'bold',
              'size': size_font,
              'va': 'center',
              }
    # =================================== Text ====================================
    ax.text(0, 0, str(f"{PLOT_VALUE:0.{PRECISION}f}"), ha='center', **kwargs)

    # ============================= Format Plot Area ==============================
    # Reduce whitespace around figure

    # RGBA setting background as transparent
    plt.rcParams.update({"savefig.facecolor": (0.0, 0.0, 1.0, 0.0)})

    chart_tools.save(logger=LOG)

except Exception:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type} in {__file__.rsplit('/', maxsplit=1)[-1]}")

json.dump(LOG, sys.stdout, indent=4)
