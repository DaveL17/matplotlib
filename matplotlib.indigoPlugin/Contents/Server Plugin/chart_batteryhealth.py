# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the battery health charts

The chart_battery_health method creates battery health charts. These chart types are dynamic and
are created "on the fly" rather than through direct user input.
"""

# Built-in Modules
import json
import sys
import traceback
import numpy as np
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import patches
# My modules
import chart_tools  # noqa

LOG        = chart_tools.LOG
PAYLOAD    = chart_tools.payload
P_DICT     = PAYLOAD['p_dict']
K_DICT     = PAYLOAD['k_dict']
PLUG_DICT  = PAYLOAD['prefs']
PROPS      = PAYLOAD['props']
CHART_NAME = PROPS['name']
DATA       = PAYLOAD['data']
BAR_COLORS = []
CHART_DATA = {}
X_VALUES   = []
Y_TEXT     = []

LOG['Threaddebug'].append("chart_batteryhealth.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(PAYLOAD)

try:
    rgb = P_DICT['cautionColor'].replace(' ', '').replace('#', '')
    caution_color = f"#{rgb}"
    caution_level = int(P_DICT['cautionLevel'])
    font_size     = plt.rcParams['ytick.labelsize']
    rgb = P_DICT['healthyColor'].replace(' ', '').replace('#', '')
    healthy_color = f"#{rgb}"
    level_box     = P_DICT['showBatteryLevelBackground']
    show_level    = P_DICT['showBatteryLevel']
    dead_ones     = P_DICT.get('showDeadBattery', False)
    rgb = P_DICT['warningColor'].replace(' ', '').replace('#', '')
    warning_color = f"#{rgb}"
    warning_level = int(P_DICT['warningLevel'])

    # ============================ Create Device Dict =============================
    # 'thing' is a tuple ('name', int)
    for thing in sorted(DATA.items(), reverse=True):
        CHART_DATA[thing[0]] = {}

        # Add the battery level for each device
        try:
            CHART_DATA[thing[0]]['batteryLevel'] = int(thing[1])
        except ValueError:
            CHART_DATA[thing[0]]['batteryLevel'] = 0

        # Determine the appropriate bar color for battery level
        if CHART_DATA[thing[0]]['batteryLevel'] > caution_level:
            CHART_DATA[thing[0]]['color'] = healthy_color
        elif caution_level >= CHART_DATA[thing[0]]['batteryLevel'] > warning_level:
            CHART_DATA[thing[0]]['color'] = caution_color
        else:
            CHART_DATA[thing[0]]['color'] = warning_color

        # =========================== Create Chart Elements ===========================
        BAR_COLORS.append(CHART_DATA[thing[0]]['color'])
        X_VALUES.append(CHART_DATA[thing[0]]['batteryLevel'])
        Y_TEXT.append(thing[0])

    # Create a range of values to plot on the Y axis, since we can't plot on device names.
    y_values = np.arange(len(Y_TEXT))

    # Create the chart figure
    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    # =============================== Plot the Bars ===============================
    # We add 1 to the y_axis pushes the bar to spot 1 instead of spot 0 -- getting
    # it off the origin.
    rects = ax.barh(
        (y_values + 1),
        X_VALUES,
        color=BAR_COLORS,
        align='center',
        linewidth=0,
        **K_DICT['k_bar']
    )

    # ================================ Data Labels ================================
    # Plot data labels inside or outside depending on bar length

    for rect in rects:
        width = rect.get_width()  # horizontal width of bars
        height = rect.get_height()  # vertical height of bars
        y = rect.get_y()  # Y axis position

        # With bbox.  We give a little extra room horizontally for the bbox.
        if show_level in ('true', 'True', True) and level_box:
            if width >= caution_level:
                plt.annotate(
                    f"{width:.0f}",
                    xy=(width - 3, y + height / 2),
                    fontsize=font_size,
                    fontname=P_DICT['fontMain'],
                    **K_DICT['k_annotation_battery']
                )
            else:
                plt.annotate(
                    f"{width:.0f}",
                    xy=(width + 3, y + height / 2),
                    fontsize=font_size,
                    fontname=P_DICT['fontMain'],
                    **K_DICT['k_annotation_battery']
                )

        # Without bbox.
        elif show_level in ('true', 'True', True):
            if width >= caution_level:
                plt.annotate(
                    f"{width:.0f}",
                    xy=(width - 2, y + height / 2),
                    fontsize=font_size,
                    fontname=P_DICT['fontMain'],
                    **K_DICT['k_battery']
                )
            else:
                plt.annotate(
                    f"{width:.0f}",
                    xy=(width + 2, y + height / 2),
                    fontsize=font_size,
                    fontname=P_DICT['fontMain'],
                    **K_DICT['k_battery']
                )

    # ================================ Chart Title ================================
    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.98))

    # =============================== Format Grids ================================
    if PLUG_DICT.get('showxAxisGrid', False):
        for _ in (20, 40, 60, 80):
            ax.axvline(x=_, color=P_DICT['gridColor'], linestyle=PLUG_DICT.get('gridStyle', ':'))

    chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    ax.xaxis.set_ticks_position('bottom')
    ax.tick_params(axis='x', colors=PLUG_DICT['fontColor'])

    # ============================== X Axis Min/Max ===============================
    # We want the X axis scale to always be 0-100.
    plt.xlim(xmin=0, xmax=100)

    # =============================== Y Axis Label ================================
    # Hide major tick labels and right side ticks.
    ax.set_yticklabels('')
    ax.yaxis.set_ticks_position('left')

    # Set the number of Y ticks
    ax.set_yticks(list(range(1, len(y_values) + 1)), minor=False)

    # Assign device names to the ticks (if wanted)
    if P_DICT.get('showDeviceName', True):
        ax.set_yticklabels(
            Y_TEXT,
            fontname=P_DICT['fontMain'],
            color=PLUG_DICT['fontColor'],
            fontsize=PLUG_DICT['tickFontSize'],
            minor=False
        )

    # Mark devices that have a battery level of zero by coloring their y-axis label using the same
    # warning color that is used for the bar.
    if dead_ones:
        counter = 0
        for key, value in sorted(DATA.items(), reverse=True):
            if int(value) == 0:
                ax.yaxis.get_majorticklabels()[counter].set_color(warning_color)
            counter += 1

    # ============================== Y Axis Min/Max ===============================
    # We never want the Y axis to go lower than 0.
    plt.ylim(ymin=0)

    # ================================== Spines ===================================
    # Hide all but the bottom spine.
    for spine in ('left', 'top', 'right'):
        ax.spines[spine].set_visible(False)

    # Add a patch so that we can have transparent charts but a filled plot area.
    if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
        ax.add_patch(
            patches.Rectangle(
                (0, 0), 1, 1,
                transform=ax.transAxes,
                facecolor=P_DICT['faceColor'],
                zorder=1)
        )

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
