#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the battery health charts
The chart_battery_health method creates battery health charts. These chart
types are dynamic and are created "on the fly" rather than through direct
user input.
-----

"""

# import calendar
# import datetime as dt
import numpy as np
import sys
import pickle

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.patches as patches
# import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave

log           = chart_tools.log
payload       = chart_tools.payload
p_dict        = payload['p_dict']
k_dict        = payload['k_dict']
prefs         = payload['prefs']
props         = payload['props']
bar_colors    = []
chart_data    = {}
x_values      = []
y_text        = []

try:

    def __init__():
        pass

    caution_level = int(p_dict['cautionLevel'])
    font_size     = plt.rcParams['ytick.labelsize']
    level_box     = p_dict['showBatteryLevelBackground']
    show_level    = p_dict['showBatteryLevel']
    dead_ones     = p_dict.get('showDeadBattery', False)
    warning_level = int(p_dict['warningLevel'])

    for color in ['cautionColor', 'healthyColor', 'warningColor']:
        p_dict[color] = chart_tools.fix_rgb(color=p_dict[color])

    # ============================ Create Device Dict =============================
    # 'thing' here is a tuple ('name', 'battery level')
    for thing in sorted(payload['data'].iteritems(), reverse=True):
        chart_data[thing[0]] = {}

        # Add the battery level for each device
        try:
            chart_data[thing[0]]['batteryLevel'] = float(thing[1])
        except ValueError:
            chart_data[thing[0]]['batteryLevel'] = 0.0

        # Determine the appropriate bar color
        if chart_data[thing[0]]['batteryLevel'] > caution_level:
            chart_data[thing[0]]['color'] = p_dict['healthy_color']
        elif caution_level >= chart_data[thing[0]]['batteryLevel'] > warning_level:
            chart_data[thing[0]]['color'] = p_dict['caution_color']
        else:
            chart_data[thing[0]]['color'] = p_dict['warning_color']

        # =========================== Create Chart Elements ===========================
        bar_colors.append(chart_data[thing[0]]['color'])
        x_values.append(chart_data[thing[0]]['batteryLevel'])
        y_text.append(unicode(thing[0]))

    # Create a range of values to plot on the Y axis, since we can't plot on device names.
    y_values = np.arange(len(y_text))

    # Create the chart figure
    try:
        height = int(props.get('figureHeight', 300)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 3

    try:
        width = int(props.get('figureWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # =============================== Plot the Bars ===============================
    # We add 1 to the y_axis pushes the bar to spot 1 instead of spot 0 -- getting
    # it off the origin.
    rects = ax.barh((y_values + 1),
                    x_values,
                    color=bar_colors,
                    align='center',
                    linewidth=0,
                    **k_dict['k_bar']
                    )

    # ================================ Data Labels ================================
    # Plot data labels inside or outside depending on bar length

    for rect in rects:
        width  = rect.get_width()    # horizontal width of bars
        height = rect.get_height()   # vertical height of bars
        y      = rect.get_y()        # Y axis position

        # With bbox.  We give a little extra room horizontally for the bbox.
        if show_level in ('true', 'True', True) and level_box:
            if width >= caution_level:
                plt.annotate(u"{0:.0f}".format(width),
                             xy=(width - 3, y + height / 2),
                             fontsize=font_size, **k_dict['k_annotation_battery']
                             )
            else:
                plt.annotate(u"{0:.0f}".format(width),
                             xy=(width + 3, y + height / 2),
                             fontsize=font_size, **k_dict['k_annotation_battery']
                             )

        # Without bbox.
        elif show_level in ('true', 'True', True):
            if width >= caution_level:
                plt.annotate(u"{0:.0f}".format(width),
                             xy=(width - 2, y + height / 2),
                             fontsize=font_size,
                             **k_dict['k_battery']
                             )
            else:
                plt.annotate(u"{0:.0f}".format(width),
                             xy=(width + 2, y + height / 2),
                             fontsize=font_size,
                             **k_dict['k_battery']
                             )

    # ================================ Chart Title ================================
    chart_tools.format_title(p_dict, k_dict, loc=(0.05, 0.98), align='center')

    # =============================== Format Grids ================================
    if props.get('showxAxisGrid', False):
        for _ in (20, 40, 60, 80):
            ax.axvline(x=_,
                       color=p_dict['gridColor'],
                       linestyle=prefs.get('gridStyle', ':')
                       )

    # ============================ Format X Axis Label ============================
    if not p_dict['showLegend']:
        plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
        chart_tools.log['Threaddebug'].append(u"[{0}] No call for legend. Formatting "
                                              u"X label.".format(props['name']))

    if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ('', 'null'):
        chart_tools.log['Debug'].append(u"[{0}] X axis label is suppressed to make room for the chart "
                                        u"legend.".format(payload['name']))

    ax.xaxis.set_ticks_position('bottom')

    # ============================== X Axis Min/Max ===============================
    # We want the X axis scale to always be 0-100.
    plt.xlim(xmin=0, xmax=100)

    # =============================== Y Axis Label ================================
    # Hide major tick labels and right side ticks.
    ax.set_yticklabels('')
    ax.yaxis.set_ticks_position('left')

    # Customize minor tick label position
    ax.set_yticks([n for n in range(1, len(y_values) + 1)], minor=True)

    # Assign device names to the minor ticks if wanted
    if p_dict.get('showDeviceName', True):
        ax.set_yticklabels(y_text, minor=True)

    # Mark devices that have a battery level of zero by coloring their y axis label
    # using the same warning color that is used for the bar.
    if dead_ones:
        counter = 0
        for key, value in sorted(payload['data'].iteritems(), reverse=True):
            if int(value) == 0:
                ax.yaxis.get_minorticklabels()[counter].set_color(p_dict['warning_color'])
            counter += 1

    # ============================== Y Axis Min/Max ===============================
    # We never want the Y axis to go lower than 0.
    plt.ylim(ymin=0)

    # ================================== Spines ===================================
    # Hide all but the bottom spine.
    for spine in ('left', 'top', 'right'):
        ax.spines[spine].set_visible(False)

    # Add a patch so that we can have transparent charts but a filled plot area.
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                       transform=ax.transAxes,
                                       facecolor=p_dict['faceColor'],
                                       zorder=1
                                       )
                     )

    plt.subplots_adjust(top=0.98,
                        bottom=0.05,
                        left=0.02,
                        right=0.98,
                        hspace=None,
                        wspace=None
                        )

    # plt.tight_layout()
    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    chart_tools.log['Critical'].append(u"{0}".format(sub_error))

pickle.dump(chart_tools.log, sys.stdout)
