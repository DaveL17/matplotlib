#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the bar charts

All steps required to generate bar charts that use stock (time-agnostic) data.
-----

"""

# Built-in Modules
import itertools
import pickle
import sys
import traceback

# Third-party Modules
# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# My modules
import chart_tools

log               = chart_tools.log
payload           = chart_tools.payload
chart_data        = payload['data']
p_dict            = payload['p_dict']
k_dict            = payload['k_dict']
props             = payload['props']
chart_name        = props['name']
plug_dict         = payload['prefs']
annotation_values = []
bar_colors        = []
x_labels          = []
x_ticks           = []

log['Threaddebug'].append(u"chart_bar_stock.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass

    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    # ============================  Iterate the Bars  =============================
    for bar in chart_data:
        b_num        = bar['number']
        color        = bar['color_{i}'.format(i=b_num)]
        suppress_bar = p_dict.get('suppressBar{i}'.format(i=b_num), False)
        x_labels.append(bar['legend_{i}'.format(i=b_num)])
        x_ticks.append(b_num)
        y_val = float(bar['val_{i}'.format(i=b_num)])
        p_dict['data_array'].append(y_val)
        bar_colors.append(color)

        # ====================  Bar and Background Color the Same  ====================
        # If the bar color is the same as the background color, alert the user.
        if color == p_dict['backgroundColor'] and not suppress_bar:
            chart_tools.log['Info'].append(u"[{name}] Bar {i} color is the same as the background color (so you may "
                                           u"not be able to see it).".format(name=chart_name, i=b_num))

        # =============================  Bar Suppressed  ==============================
        # If the bar is suppressed, remind the user they suppressed it.
        if suppress_bar:
            chart_tools.log['Info'].append(u"[{name}] Bar {i} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(name=chart_name, i=b_num))

        # ============================  Display Zero Bars  ============================
        # Early versions of matplotlib will truncate leading and trailing bars where the value is zero.
        # With this setting, we replace the Y values of zero with a very small positive value
        # (0 becomes 1e-06). We get a slice of the original data for annotations.
        # annotation_values.append(y_val)
        annotation_values.append(bar['val_{i}'.format(i=b_num)])
        if p_dict.get('showZeroBars', False):
            if y_val == 0:
                y_val = 1e-06

        # ================================  Bar Width  ================================
        try:
            bar_width = float(p_dict['barWidth'])
            if bar_width == 0:
                width = 0.8
            else:
                width = float(p_dict['barWidth'])
        except ValueError:
            width = 0.8
            chart_tools.log['Warning'].append(u"[{n}] Problem setting bar width. Check value "
                                              u"({w}).".format(n=chart_name, w=p_dict['barWidth']))

        # ==============================  Plot the Bar  ===============================
        # Plot the bars. If 'suppressBar{thing} is True, we skip it.
        if not suppress_bar:
            ax.bar(b_num,
                   y_val,
                   width=float(p_dict['barWidth']),
                   color=color,
                   bottom=None,
                   align='center',
                   edgecolor=color,
                   **k_dict['k_bar'])

        # ===============================  Annotations  ===============================
        # If annotations desired, plot those too.
        if bar['annotate_{i}'.format(i=b_num)] and not suppress_bar:
            ax.annotate(unicode(annotation_values[b_num-1]),
                        xy=(b_num, y_val),
                        xytext=(0, 0),
                        zorder=10,
                        **k_dict['k_annotation']
                        )

    # ===============================  X Tick Bins  ===============================
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(x_labels)

    chart_tools.format_axis_y1_min_max(p_dict=p_dict, logger=log)
    chart_tools.format_axis_x_label(dev=props, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y1_label(p_dict=p_dict, k_dict=k_dict, logger=log)

    # ===========================  Transparent Border  ============================
    # Add a patch so that we can have transparent charts but a filled plot area.
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                       transform=ax.transAxes,
                                       facecolor=p_dict['faceColor'],
                                       zorder=1
                                       )
                     )

    # ============================= Legend Properties =============================
    # Legend should be plotted before any other lines are plotted (like averages or
    # custom line segments).
    if p_dict['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []
        headers = [_.decode('utf-8') for _ in x_labels]
        for header in headers:
            if p_dict['bar{c}Legend'.format(c=counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['bar{c}Legend'.format(c=counter)])
            counter += 1

        # Set the legend
        # Reorder the headers so that they fill by row instead of by column
        num_col = int(p_dict['legendColumns'])
        iter_headers   = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = [_ for _ in iter_headers]

        iter_colors  = itertools.chain(*[bar_colors[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        legend = ax.legend(final_headers,
                           loc='upper center',
                           bbox_to_anchor=(0.5, -0.1),
                           ncol=int(p_dict['legendColumns']),
                           prop={'size': float(p_dict['legendFontSize'])}
                           )

        # Set legend font color
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]

        # Set legend bar colors
        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=plug_dict, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_grids(p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.5, 0.98))
    chart_tools.format_axis_y_ticks(p_dict=p_dict, k_dict=k_dict, logger=log)

    # Note that subplots_adjust affects the space surrounding the subplots and
    # not the fig.
    plt.subplots_adjust(top=0.90,
                        bottom=0.20,
                        left=0.10,
                        right=0.90,
                        hspace=None,
                        wspace=None
                        )

    try:
        chart_tools.save(logger=log)

    except OverflowError as err:
        if "date value out of range" in traceback.format_exc(err):
            chart_tools.log['Critical'].append(u"[{name}] Chart not saved. Try enabling Display Zero Bars in "
                                               u"device settings.".format(name=payload['props']['name']))

except (KeyError, IndexError, ValueError, UnicodeEncodeError, ZeroDivisionError) as sub_error:
    tb = traceback.format_exc()
    chart_tools.log['Critical'].append(u"[{n}]\n{s}".format(n=chart_name, s=tb))

pickle.dump(chart_tools.log, sys.stdout)
