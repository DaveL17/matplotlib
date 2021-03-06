#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the flow bar charts

All steps required to generate bar charts that use flow (time-series) data.
-----

"""

# Built-in Modules
import itertools
import numpy as np
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

log        = chart_tools.log
payload    = chart_tools.payload
p_dict     = payload['p_dict']
k_dict     = payload['k_dict']
props      = payload['props']
chart_name = props['name']
plug_dict  = payload['prefs']
bar_colors = []
dates_to_plot = []
x_ticks = []

log['Threaddebug'].append(u"chart_bar_flow.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass

    num_obs = p_dict['numObs']

    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    for thing in range(1, 5, 1):

        suppress_bar = p_dict.get('suppressBar{i}'.format(i=thing), False)

        # p_dict['bar{i}Color'.format(i=thing)] = chart_tools.fix_rgb(p_dict['bar{i}Color'.format(i=thing)])

        # If the bar is suppressed, remind the user they suppressed it.
        if suppress_bar:
            chart_tools.log['Info'].append(u"[{name}] Bar {i} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(name=chart_name, i=thing))

        # Plot the bars. If 'suppressBar{thing} is True, we skip it.
        if p_dict['bar{i}Source'.format(i=thing)] not in ("", "None") and not suppress_bar:

            # If the bar color is the same as the background color, alert the user.
            if p_dict['bar{i}Color'.format(i=thing)] == p_dict['backgroundColor'] and not suppress_bar:
                chart_tools.log['Warning'].append(u"[{name}] Bar {i} color is the same as the background color (so "
                                                  u"you may not be able to see it).".format(name=chart_name, i=thing))

            # Add bar color to list for later use
            bar_colors.append(p_dict['bar{i}Color'.format(i=thing)])

            # Get the data and grab the header.
            dc = u'{path}{source}'.format(path=plug_dict['dataPath'].encode("utf-8"),
                                          source=p_dict['bar{i}Source'.format(i=thing)]
                                          )

            data_column = chart_tools.get_data(data_source=dc, logger=log)

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"Data for bar {i}: {c}".format(i=thing, c=data_column))

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{i}'.format(i=thing)].append(element[0])
                p_dict['y_obs{i}'.format(i=thing)].append(float(element[1]))

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{i}'.format(i=thing)]

            # Get limit -- if blank or none then zero limit.
            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            y_obs   = p_dict['y_obs{i}'.format(i=thing)]
            new_old = props['limitDataRange']
            if limit > 0:
                dtp = chart_tools.prune_data(x_data=dates_to_plot,
                                             y_data=y_obs,
                                             limit=limit,
                                             new_old=new_old,
                                             logger=log
                                             )
                dates_to_plot, y_obs = dtp

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=dates_to_plot, logger=log)

            # If the user sets the width to 0, this will perform an introspection of the
            # dates to plot and get the minimum of the difference between the dates.
            try:
                if float(p_dict['barWidth']) == 0.0:
                    width = np.min(np.diff(dates_to_plot)) * 0.8
                else:
                    width = float(p_dict['barWidth'])
            except ValueError as sub_error:
                width = 0.8

            # Early versions of matplotlib will truncate leading and trailing bars where the value is zero.
            # With this setting, we replace the Y values of zero with a very small positive value
            # (0 becomes 1e-06). We get a slice of the original data for annotations.
            annotation_values = y_obs[:]
            if p_dict.get('showZeroBars', False):
                y_obs[num_obs * -1:] = [1e-06 if _ == 0 else _ for _ in y_obs[num_obs * -1:]]

            # Plot the bar. Note: hatching is not supported in the PNG backend.
            ax.bar(dates_to_plot[num_obs * -1:],
                   y_obs[num_obs * -1:],
                   align='center',
                   width=width,
                   color=p_dict['bar{i}Color'.format(i=thing)],
                   edgecolor=p_dict['bar{i}Color'.format(i=thing)],
                   **k_dict['k_bar']
                   )

            [p_dict['data_array'].append(node) for node in y_obs[num_obs * -1:]]

            # If annotations desired, plot those too.
            if p_dict['bar{i}Annotate'.format(i=thing)]:
                for xy in zip(dates_to_plot, annotation_values):
                    ax.annotate(u"{i}".format(i=xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y1_min_max(p_dict=p_dict, logger=log)
    chart_tools.format_axis_x_label(dev=props, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y1_label(p_dict=p_dict, k_dict=k_dict, logger=log)

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
        headers = [_.decode('utf-8') for _ in p_dict['headers']]
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
                           bbox_to_anchor=(0.5, -0.15),
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

    # =============================== Min/Max Lines ===============================
    # Note that these need to be plotted after the legend is established, otherwise
    # some of the characteristics of the min/max lines will take over the legend
    # props.
    for thing in range(1, 5, 1):
        if p_dict['plotBar{i}Min'.format(i=thing)]:
            ax.axhline(y=min(y_obs[num_obs * -1:]),
                       color=p_dict['bar{i}Color'.format(i=thing)],
                       **k_dict['k_min']
                       )
        if p_dict['plotBar{i}Max'.format(i=thing)]:
            ax.axhline(y=max(y_obs[num_obs * -1:]),
                       color=p_dict['bar{i}Color'.format(i=thing)],
                       **k_dict['k_max']
                       )
        if plug_dict.get('forceOriginLines', True):
            ax.axhline(y=0, color=p_dict['spineColor'])

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=plug_dict, p_dict=p_dict, k_dict=k_dict, logger=log, orient="horiz")
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

    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    tb = traceback.format_exc()
    chart_tools.log['Critical'].append(u"[{n}] {s}".format(n=chart_name, s=tb))

pickle.dump(chart_tools.log, sys.stdout)
