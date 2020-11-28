#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the line charts
All steps required to generate line charts.
-----

"""

# import ast
# import csv
# import datetime as dt
# from dateutil.parser import parse as date_parse
import itertools
# import numpy as np
# import operator as op
import sys
import pickle
# import unicodedata

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave


log         = chart_tools.log
payload     = chart_tools.payload
p_dict      = payload['p_dict']
k_dict      = payload['k_dict']
prefs       = payload['prefs']
props       = payload['props']
line_colors = []


try:

    def __init__():
        pass


    for color in ['backgroundColor', 'faceColor']:
        p_dict[color] = chart_tools.fix_rgb(color=p_dict[color])

    dpi    = plt.rcParams['savefig.dpi']
    height = float(p_dict['chart_height'])
    width  = float(p_dict['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax  = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    # ============================== Format X Ticks ===============================
    ax.tick_params(axis='x', **k_dict['k_major_x'])
    ax.tick_params(axis='x', **k_dict['k_minor_x'])
    ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
    chart_tools.format_axis_x_scale(x_axis_bins=p_dict['xAxisBins'], logger=log)

    # If the x axis format has been set to None, let's hide the labels.
    if p_dict['xAxisLabelFormat'] == "None":
        ax.axes.xaxis.set_ticklabels([])

    # =============================== Format Y Axis ===============================
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    for line in range(1, 9, 1):

        suppress_line = p_dict.get('suppressLine{0}'.format(line), False)

        lc_index = 'line{0}Color'.format(line)
        p_dict[lc_index] = chart_tools.fix_rgb(color=p_dict[lc_index])

        lmc_index = 'line{0}MarkerColor'.format(line)
        p_dict[lmc_index] = chart_tools.fix_rgb(color=p_dict[lmc_index])

        lbf_index = 'line{0}BestFitColor'.format(line)
        p_dict[lbf_index] = chart_tools.fix_rgb(color=p_dict[lbf_index])

        # If line color is the same as the background color, alert the user.
        if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor'] and not suppress_line:
            chart_tools.log['Warning'].append(u"[{0}] Line {1} color is the same as the background color (so you may "
                                              u"not be able to see it).".format(props['name'], line))

        # If the line is suppressed, remind the user they suppressed it.
        if suppress_line:
            chart_tools.log['Info'].append(u"[{0}] Line {1} is suppressed by user setting. You can re-enable it in the "
                                           u"device configuration menu.".format(props['name'], line))

        # ============================== Plot the Lines ===============================
        # Plot the lines. If suppress_line is True, we skip it.
        if p_dict['line{0}Source'.format(line)] not in (u"", u"None") and not suppress_line:

            # Add line color to list for later use
            line_colors.append(p_dict['line{0}Color'.format(line)])

            data_path = prefs['dataPath'].encode("utf-8")
            line_source = p_dict['line{0}Source'.format(line)].encode("utf-8")
            data_column = chart_tools.get_data('{0}{1}'.format(data_path, line_source), logger=log)

            chart_tools.log['Threaddebug'].append(u"Data for Line {0}: {1}".format(line, data_column))

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{0}'.format(line)].append(element[0])
                p_dict['y_obs{0}'.format(line)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if props['line{0}adjuster'.format(line)] != "":
                temp_list = []
                for obs in p_dict['y_obs{0}'.format(line)]:
                    expr = u'{0}{1}'.format(obs, props['line{0}adjuster'.format(line)])
                    temp_list.append(chart_tools.eval_expr(chart_tools.eval_expr(expr)))
                p_dict['y_obs{0}'.format(line)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{0}'.format(line)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = p_dict['y_obs{0}'.format(line)]
                new_old = props['limitDataRange']

                prune = chart_tools.prune_data(dates_to_plot, y_obs, limit, new_old='None', logger=log)
                p_dict['x_obs{0}'.format(line)], p_dict['y_obs{0}'.format(line)] = prune

            # ======================== Convert Dates for Charting =========================
            p_dict['x_obs{0}'.format(line)] = chart_tools.format_dates(p_dict['x_obs{0}'.format(line)], logger=log)

            ax.plot_date(p_dict['x_obs{0}'.format(line)],
                         p_dict['y_obs{0}'.format(line)],
                         color=p_dict['line{0}Color'.format(line)],
                         linestyle=p_dict['line{0}Style'.format(line)],
                         marker=p_dict['line{0}Marker'.format(line)],
                         markeredgecolor=p_dict['line{0}MarkerColor'.format(line)],
                         markerfacecolor=p_dict['line{0}MarkerColor'.format(line)],
                         zorder=10,
                         **k_dict['k_line']
                         )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

            if p_dict['line{0}Fill'.format(line)]:
                ax.fill_between(p_dict['x_obs{0}'.format(line)],
                                0,
                                p_dict['y_obs{0}'.format(line)],
                                color=p_dict['line{0}Color'.format(line)],
                                **k_dict['k_fill']
                                )

            # ================================ Annotations ================================
            if p_dict['line{0}Annotate'.format(line)]:
                for xy in zip(p_dict['x_obs{0}'.format(line)], p_dict['y_obs{0}'.format(line)]):
                    ax.annotate(u"{0}".format(xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
    chart_tools.format_axis_y1_min_max(p_dict=p_dict, logger=log)

    # Transparent Chart Fill
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                       transform=ax.transAxes,
                                       facecolor=p_dict['faceColor'],
                                       zorder=1
                                       )
                     )

    # ================================== Legend ===================================
    if p_dict['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []

        headers = [_.decode('utf-8') for _ in p_dict['headers']]

        for header in headers:
            if p_dict['line{0}Legend'.format(counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['line{0}Legend'.format(counter)])
            counter += 1

        # Set the legend
        # Reorder the headers and colors so that they fill by row instead of by column
        num_col = int(p_dict['legendColumns'])
        iter_headers = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = [_ for _ in iter_headers]

        iter_colors = itertools.chain(*[line_colors[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        legend = ax.legend(final_headers,
                           loc='upper center',
                           bbox_to_anchor=(0.5, -0.1),
                           ncol=num_col,
                           prop={'size': float(p_dict['legendFontSize'])}
                           )

        # Set legend font color
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]

        # Set legend line color
        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    for line in range(1, 9, 1):

        suppress_line = p_dict.get('suppressLine{0}'.format(line), False)

        if p_dict['line{0}Source'.format(line)] not in (u"", u"None") and not suppress_line:
            # Note that we do these after the legend is drawn so that these lines don't
            # affect the legend.

            # We need to reload the dates to ensure that they match the line being plotted
            # dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(line)])

            # =============================== Best Fit Line ===============================
            if props.get('line{0}BestFit'.format(line), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{0}'.format(line)],
                                                          line=line,
                                                          p_dict=p_dict,
                                                          logger=log)

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

            # =============================== Fill Between ================================
            if p_dict['line{0}Fill'.format(line)]:
                ax.fill_between(p_dict['x_obs{0}'.format(line)],
                                0,
                                p_dict['y_obs{0}'.format(line)],
                                color=p_dict['line{0}Color'.format(line)],
                                **k_dict['k_fill']
                                )

            # =============================== Min/Max Lines ===============================
            if p_dict['plotLine{0}Min'.format(line)]:
                ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]),
                           color=p_dict['line{0}Color'.format(line)],
                           **k_dict['k_min'])
            if p_dict['plotLine{0}Max'.format(line)]:
                ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]),
                           color=p_dict['line{0}Color'.format(line)],
                           **k_dict['k_max']
                           )
            if prefs.get('forceOriginLines', True):
                ax.axhline(y=0, color=p_dict['spineColor'])

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=prefs, p_dict=p_dict, k_dict=k_dict, logger=log)

    # =============================== Format Grids ================================
    if p_dict['showxAxisGrid']:
        plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

    if p_dict['showyAxisGrid']:
        plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    # =============================== Format Title ================================
    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.05, 0.98), align='center')

    # ============================ Format X Axis Label ============================
    if not p_dict['showLegend']:
        plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
        chart_tools.log['Threaddebug'].append(u"[{0}] No call for legend. Formatting "
                                              u"X label.".format(props['name']))

    if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ('', 'null'):
        chart_tools.log['Debug'].append(u"[{0}] X axis label is suppressed to make room "
                                        u"for the chart legend.".format(props['name']))

    # ============================ Format Y1 Axis Label ============================
    plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

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

pickle.dump(chart_tools.log, sys.stdout)
