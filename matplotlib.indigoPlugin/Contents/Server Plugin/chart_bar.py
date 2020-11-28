#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the bar charts
All steps required to generate bar charts.
-----

"""

import itertools
import numpy as np
import sys
import pickle

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
import matplotlib.pyplot as plt
import matplotlib.patches as patches

import chart_tools

log        = chart_tools.log
payload    = chart_tools.payload
p_dict     = payload['p_dict']
k_dict     = payload['k_dict']
props      = payload['props']
plug_dict      = payload['prefs']
bar_colors = []

log['Threaddebug'].append(u"chart_bar.py called.")

try:

    def __init__():
        pass

    num_obs = p_dict['numObs']
    for color in ['backgroundColor', 'faceColor']:
        p_dict[color] = chart_tools.fix_rgb(color=p_dict[color])

    dpi = plt.rcParams['savefig.dpi']
    height = float(p_dict['chart_height'])
    width = float(p_dict['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    chart_tools.format_axis_x_ticks(ax, p_dict, k_dict, logger=log)
    chart_tools.format_axis_y(ax, p_dict, k_dict, logger=log)

    for thing in range(1, 5, 1):

        suppress_bar = p_dict.get('suppressBar{0}'.format(thing), False)

        p_dict['bar{0}Color'.format(thing)] = chart_tools.fix_rgb(p_dict['bar{0}Color'.format(thing)])

        # If the bar color is the same as the background color, alert the user.
        if p_dict['bar{0}Color'.format(thing)] == p_dict['backgroundColor'] and not suppress_bar:
            chart_tools.log['Info'].append(u"[{0}] Bar {1} color is the same as the background color (so you may not "
                                           u"be able to see it).".format(props['name'], thing))

        # If the bar is suppressed, remind the user they suppressed it.
        if suppress_bar:
            chart_tools.log['Info'].append(u"[{0}] Bar {1} is suppressed by user setting. You can re-enable it in the "
                                           u"device configuration menu.".format(props['name'], thing))

        # Plot the bars. If 'suppressBar{thing} is True, we skip it.
        if p_dict['bar{0}Source'.format(thing)] not in ("", "None") and not suppress_bar:

            # Add bar color to list for later use
            bar_colors.append(p_dict['bar{0}Color'.format(thing)])

            # Get the data and grab the header.
            dc = u'{0}{1}'.format(plug_dict['dataPath'].encode("utf-8"),
                                  p_dict['bar{0}Source'.format(thing)]
                                  )

            data_column = chart_tools.get_data(dc, logger=log)

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"Data for bar {0}: {1}".format(thing, data_column))

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{0}'.format(thing)].append(element[0])
                p_dict['y_obs{0}'.format(thing)].append(float(element[1]))

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{0}'.format(thing)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs   = p_dict['y_obs{0}'.format(thing)]
                new_old = props['limitDataRange']
                dtp = chart_tools.prune_data(dates_to_plot, y_obs, limit, new_old, logger=log)
                p_dict['x_obs{0}'.format(thing)], p_dict['y_obs{0}'.format(thing)] = dtp

            # Convert the date strings for charting.
            p_dict['x_obs{0}'.format(thing)] = chart_tools.format_dates(p_dict['x_obs{0}'.format(thing)], logger=log)

            # If the user sets the width to 0, this will perform an introspection of the
            # dates to plot and get the minimum of the difference between the dates.
            try:
                if float(p_dict['barWidth']) == 0.0:
                    width = np.min(np.diff(p_dict['x_obs{0}'.format(thing)])) * 0.8
                else:
                    width = float(p_dict['barWidth'])
            except ValueError as sub_error:
                width = 1

            # Early versions of matplotlib will truncate leading and trailing bars where the value is zero.
            # With this setting, we replace the Y values of zero with a very small positive value
            # (0 becomes 1e-06). We get a slice of the original data for annotations.
            annotation_values = p_dict['y_obs{0}'.format(thing)][:]
            if p_dict.get('showZeroBars', False):
                p_dict['y_obs{0}'.format(thing)][num_obs * -1:] = [1e-06 if _ == 0 else _ for _ in
                                                                   p_dict['y_obs{0}'.format(thing)][num_obs * -1:]]

            # Plot the bar. Note: hatching is not supported in the PNG backend.
            ax.bar(p_dict['x_obs{0}'.format(thing)][num_obs * -1:],
                   p_dict['y_obs{0}'.format(thing)][num_obs * -1:],
                   align='center',
                   width=width,
                   color=p_dict['bar{0}Color'.format(thing)],
                   edgecolor=p_dict['bar{0}Color'.format(thing)],
                   **k_dict['k_bar']
                   )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)][num_obs * -1:]]

            # If annotations desired, plot those too.
            if p_dict['bar{0}Annotate'.format(thing)]:
                # for xy in zip(p_dict['x_obs{0}'.format(thing)], p_dict['y_obs{0}'.format(thing)]):
                for xy in zip(p_dict['x_obs{0}'.format(thing)], annotation_values):
                    ax.annotate(u"{0}".format(xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

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
            if p_dict['bar{0}Legend'.format(counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['bar{0}Legend'.format(counter)])
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

    # =============================== Min/Max Lines ===============================
    # Note that these need to be plotted after the legend is established, otherwise
    # some of the characteristics of the min/max lines will take over the legend
    # props.
    for thing in range(1, 5, 1):
        if p_dict['plotBar{0}Min'.format(thing)]:
            ax.axhline(y=min(p_dict['y_obs{0}'.format(thing)][num_obs * -1:]),
                       color=p_dict['bar{0}Color'.format(thing)],
                       **k_dict['k_min']
                       )
        if p_dict['plotBar{0}Max'.format(thing)]:
            ax.axhline(y=max(p_dict['y_obs{0}'.format(thing)][num_obs * -1:]),
                       color=p_dict['bar{0}Color'.format(thing)],
                       **k_dict['k_max']
                       )
        if plug_dict.get('forceOriginLines', True):
            ax.axhline(y=0, color=p_dict['spineColor'])

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

    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    chart_tools.log['Critical'].append(u"{0}".format(sub_error))

chart_tools.log['Info'].append(u'Bar charting function complete.')
pickle.dump(chart_tools.log, sys.stdout)
