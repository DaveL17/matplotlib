#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the scatter charts
All steps required to generate scatter charts.
-----

"""

# import ast
# import csv
# import datetime as dt
# from dateutil.parser import parse as date_parse
import itertools
# import numpy as np
# import operator as op
# import sys
# import pickle
# import unicodedata

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
# import matplotlib.patches as patches
# import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave

payload = chart_tools.payload

try:

    def __init__():
        pass

    payload['p_dict']['backgroundColor'] = chart_tools.fix_rgb(payload['p_dict']['backgroundColor'])
    payload['p_dict']['faceColor']       = chart_tools.fix_rgb(payload['p_dict']['faceColor'])
    group_colors = []

    dpi = plt.rcParams['savefig.dpi']
    height = float(payload['p_dict']['chart_height'])
    width = float(payload['p_dict']['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=payload['p_dict']['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(payload['p_dict']['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    chart_tools.format_axis_x_ticks(ax, payload['p_dict'], payload['k_dict'])
    chart_tools.format_axis_y(ax, payload['p_dict'], payload['k_dict'])

    for thing in range(1, 5, 1):

        suppress_group = payload['p_dict'].get('suppressGroup{0}'.format(thing), False)

        payload['p_dict']['group{0}Color'.format(thing)] = chart_tools.fix_rgb(payload['p_dict']['group{0}Color'.format(thing)])

        gmc2 = chart_tools.fix_rgb(payload['p_dict']['group{0}MarkerColor'.format(thing)])
        payload['p_dict']['group{0}MarkerColor'.format(thing)] = gmc2

        best_fit = chart_tools.fix_rgb(payload['p_dict']['line{0}BestFitColor'.format(thing)])
        payload['p_dict']['line{0}BestFitColor'.format(thing)] = best_fit

        # If dot color is the same as the background color, alert the user.
        if payload['p_dict']['group{0}Color'.format(thing)] == payload['p_dict']['backgroundColor'] and not \
                suppress_group:
            chart_tools.log['Debug'].append(u"[{0}] Group {1} color is the same as the background color (so you "
                                            u"may not be able to see it).".format(payload['props']['name'], thing))

        # If the group is suppressed, remind the user they suppressed it.
        if suppress_group:
            chart_tools.log['Info'].append(u"[{0}] Group {1} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(payload['props']['name'], thing))

        # ============================== Plot the Points ==============================
        # Plot the groups. If suppress_group is True, we skip it.
        if payload['p_dict']['group{0}Source'.format(thing)] not in ("", "None") and not suppress_group:

            # Add group color to list for later use
            group_colors.append(payload['p_dict']['group{0}Color'.format(thing)])

            # There is a bug in matplotlib (fixed in newer versions) where points would not
            # plot if marker set to 'none'. This overrides the behavior.
            if payload['p_dict']['group{0}Marker'.format(thing)] == u'None':
                payload['p_dict']['group{0}Marker'.format(thing)] = '.'
                payload['p_dict']['group{0}MarkerColor'.format(thing)] = payload['p_dict']['group{0}Color'.format(thing)]

            data_path = payload['prefs']['dataPath'].encode("utf-8")
            group_source = payload['p_dict']['group{0}Source'.format(thing)].encode("utf-8")
            data_column = chart_tools.get_data('{0}{1}'.format(data_path, group_source))
            chart_tools.log['Threaddebug'].append(u"Data for group {0}: {1}".format(thing, data_column))

            # Pull the headers
            payload['p_dict']['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                payload['p_dict']['x_obs{0}'.format(thing)].append(element[0])
                payload['p_dict']['y_obs{0}'.format(thing)].append(float(element[1]))

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = payload['p_dict']['x_obs{0}'.format(thing)]

            try:
                limit = float(payload['props']['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs   = payload['p_dict']['y_obs{0}'.format(thing)]
                new_old = payload['props']['limitDataRange']

                prune = chart_tools.prune_data(dates_to_plot, y_obs, limit, new_old)
                payload['p_dict']['x_obs{0}'.format(thing)], payload['p_dict']['y_obs{0}'.format(thing)] = prune

            # Convert the date strings for charting.
            payload['p_dict']['x_obs{0}'.format(thing)] = chart_tools.format_dates(payload['p_dict']['x_obs{0}'.format(thing)])

            # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
            ax.scatter(payload['p_dict']['x_obs{0}'.format(thing)],
                       payload['p_dict']['y_obs{0}'.format(thing)],
                       c=payload['p_dict']['group{0}Color'.format(thing)],
                       marker=payload['p_dict']['group{0}Marker'.format(thing)],
                       edgecolor=payload['p_dict']['group{0}MarkerColor'.format(thing)],
                       linewidths=0.75,
                       zorder=10,
                       **payload['k_dict']['k_line']
                       )

            # =============================== Best Fit Line ===============================
            if payload['props'].get('line{0}BestFit'.format(thing), False):
                chart_tools.format_best_fit_line_segments(ax,
                                                          payload['p_dict']['x_obs{0}'.format(thing)],
                                                          thing,
                                                          payload['p_dict']
                                                          )

            [payload['p_dict']['data_array'].append(node) for node in payload['p_dict']['y_obs{0}'.format(thing)]]

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
    chart_tools.format_axis_y1_min_max(payload['p_dict'])

    # ================================== Legend ===================================
    if payload['p_dict']['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        legend_styles = []
        labels = []

        # Set legend group colors
        # Note that we do this in a slightly different order than other chart types
        # because we use legend styles for scatter charts differently than other
        # chart types.
        num_col = int(payload['p_dict']['legendColumns'])
        iter_colors  = itertools.chain(*[group_colors[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        headers = [_.decode('utf-8') for _ in payload['p_dict']['headers']]
        for header in headers:

            if payload['p_dict']['group{0}Legend'.format(counter)] == "":
                labels.append(header)
            else:
                labels.append(payload['p_dict']['group{0}Legend'.format(counter)])

            legend_styles.append(tuple(plt.plot([],
                                                color=payload['p_dict']['group{0}MarkerColor'.format(counter)],
                                                linestyle='',
                                                marker=payload['p_dict']['group{0}Marker'.format(counter)],
                                                markerfacecolor=final_colors[counter-1],
                                                markeredgewidth=.8,
                                                markeredgecolor=payload['p_dict']['group{0}MarkerColor'.format(counter)]
                                                )
                                       )
                                 )
            counter += 1

        # Reorder the headers so that they fill by row instead of by column
        iter_headers   = itertools.chain(*[labels[i::num_col] for i in range(num_col)])
        final_headers = [_ for _ in iter_headers]

        legend = ax.legend(legend_styles,
                           final_headers,
                           loc='upper center',
                           bbox_to_anchor=(0.5, -0.1),
                           ncol=int(payload['p_dict']['legendColumns']),
                           numpoints=1,
                           markerscale=0.6,
                           prop={'size': float(payload['p_dict']['legendFontSize'])}
                           )

        # Set legend font colors
        [text.set_color(payload['p_dict']['fontColor']) for text in legend.get_texts()]

        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    # ================================= Min / Max =================================
    for thing in range(1, 5, 1):
        if payload['p_dict']['plotGroup{0}Min'.format(thing)]:
            ax.axhline(y=min(payload['p_dict']['y_obs{0}'.format(thing)]),
                       color=payload['p_dict']['group{0}Color'.format(thing)],
                       **payload['k_dict']['k_min']
                       )
        if payload['p_dict']['plotGroup{0}Max'.format(thing)]:
            ax.axhline(y=max(payload['p_dict']['y_obs{0}'.format(thing)]),
                       color=payload['p_dict']['group{0}Color'.format(thing)],
                       **payload['k_dict']['k_max']
                       )
        if payload['prefs'].get('forceOriginLines', True):
            ax.axhline(y=0, color=payload['p_dict']['spineColor'])

    chart_tools.format_custom_line_segments(ax, payload['prefs'], payload['p_dict'], payload['k_dict'])
    chart_tools.format_grids(payload['p_dict'], payload['k_dict'])
    chart_tools.format_title(payload['p_dict'], payload['k_dict'], loc=(0.5, 0.98))
    chart_tools.format_axis_x_label(payload['props'], payload['p_dict'], payload['k_dict'])
    chart_tools.format_axis_y1_label(payload['p_dict'], payload['k_dict'])
    chart_tools.format_axis_y_ticks(payload['p_dict'], payload['k_dict'])

    # Note that subplots_adjust affects the space surrounding the subplots and
    # not the fig.
    plt.subplots_adjust(top=0.90,
                        bottom=0.20,
                        left=0.10,
                        right=0.90,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save()

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    pass
