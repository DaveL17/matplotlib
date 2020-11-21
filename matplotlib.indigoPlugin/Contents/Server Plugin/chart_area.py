#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the Area charts
All steps required to generate area charts.
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
import matplotlib.patches as patches
# import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave


payload         = chart_tools.payload
p_dict          = payload['p_dict']
k_dict          = payload['k_dict']
plug_dict       = payload['prefs']
props           = payload['props']
x_obs           = ''
y_obs_tuple     = ()  # Y values
y_obs_tuple_rel = {}  # Y values relative to chart (cumulative value)
y_colors_tuple  = ()  # Y area colors

try:

    def __init__():
        pass


    p_dict['backgroundColor'] = chart_tools.fix_rgb(c=p_dict['backgroundColor'])
    p_dict['faceColor']       = chart_tools.fix_rgb(c=p_dict['faceColor'])

    dpi = plt.rcParams['savefig.dpi']
    height = float(p_dict['chart_height'])
    width = float(p_dict['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict)
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict)

    for area in range(1, 9, 1):

        suppress_area = p_dict.get('suppressArea{0}'.format(area), False)

        p_dict['area{0}Color'.format(area)] = chart_tools.fix_rgb(p_dict['area{0}Color'.format(area)])
        p_dict['line{0}Color'.format(area)] = chart_tools.fix_rgb(p_dict['line{0}Color'.format(area)])
        p_dict['area{0}MarkerColor'.format(area)] = chart_tools.fix_rgb(p_dict['area{0}MarkerColor'.format(area)])

        # If area color is the same as the background color, alert the user.
        if p_dict['area{0}Color'.format(area)] == p_dict['backgroundColor'] and not suppress_area:
            chart_tools.log['Warning'].append(u"[{0}] Area {1} color is the same as the background color (so you may "
                                              u"not be able to see it).".format(props['name'], area))

        # If the area is suppressed, remind the user they suppressed it.
        if suppress_area:
            chart_tools.log['Info'].append(u"[{0}] Area {1} is suppressed by user setting. You can re-enable it in the "
                                           u"device configuration menu.".format(props['name'], area))

        # ============================== Plot the Areas ===============================
        # Plot the areas. If suppress_area is True, we skip it.
        if p_dict['area{0}Source'.format(area)] not in (u"", u"None") and not suppress_area:

            data_path   = plug_dict['dataPath'].encode("utf-8")
            area_source = p_dict['area{0}Source'.format(area)].encode("utf-8")
            data_column = chart_tools.get_data(data_source='{0}{1}'.format(data_path, area_source))
            chart_tools.log['Threaddebug'].append(u"Data for Area {0}: {1}".format(area, data_column))

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{0}'.format(area)].append(element[0])
                p_dict['y_obs{0}'.format(area)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if props['area{0}adjuster'.format(area)] != "":
                temp_list = []
                for obs in p_dict['y_obs{0}'.format(area)]:
                    expr = u'{0}{1}'.format(obs, props['area{0}adjuster'.format(area)])
                    temp_list.append(chart_tools.eval_expr(expr))
                p_dict['y_obs{0}'.format(area)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{0}'.format(area)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = p_dict['y_obs{0}'.format(area)]
                new_old = props['limitDataRange']

                x_index = 'x_obs{0}'.format(area)
                y_index = 'y_obs{0}'.format(area)
                p_dict[x_index], p_dict[y_index] = chart_tools.prune_data(x_data=dates_to_plot,
                                                                          y_data=y_obs,
                                                                          limit=limit,
                                                                          new_old=new_old
                                                                          )

            # ======================== Convert Dates for Charting =========================
            p_dict['x_obs{0}'.format(area)] = chart_tools.format_dates(p_dict['x_obs{0}'.format(area)])

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(area)]]

            # We need to plot all the stacks at once, so we create some tuples to hold the data we need later.
            y_obs_tuple += (p_dict['y_obs{0}'.format(area)],)
            y_colors_tuple += (p_dict['area{0}Color'.format(area)],)
            x_obs = p_dict['x_obs{0}'.format(area)]

            # ================================ Annotations ================================

            # New annotations code begins here - DaveL17 2019-06-05
            for _ in range(1, area + 1, 1):

                tup = ()

                # We start with the ordinal list and create a tuple to hold all the lists that come before it.
                for k in range(_, 0, -1):

                    tup += (p_dict['y_obs{0}'.format(k)],)

                # The relative value is the sum of each list element plus the ones that come before it
                # (i.e., tup[n][0] + tup[n-1][0] + tup[n-2][0]
                y_obs_tuple_rel['y_obs{0}'.format(area)] = [sum(t) for t in zip(*tup)]

            if p_dict['area{0}Annotate'.format(area)]:
                for xy in zip(p_dict['x_obs{0}'.format(area)], y_obs_tuple_rel['y_obs{0}'.format(area)]):
                    ax.annotate(u"{0}".format(xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

    ax.stackplot(x_obs,
                 y_obs_tuple,
                 edgecolor=None,
                 colors=y_colors_tuple,
                 zorder=10,
                 lw=0,
                 **k_dict['k_line']
                 )

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
    # the p_dict['data_array'] contains individual data points and doesn't take
    # into account the additive nature of the plot. Therefore, we get the axis
    # scaling values from the plot and then use those for min/max.
    [p_dict['data_array'].append(node) for node in ax.get_ylim()]

    chart_tools.format_axis_y1_min_max(p_dict=p_dict)

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
            if p_dict['area{0}Legend'.format(counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['area{0}Legend'.format(counter)])
            counter += 1

        # Set the legend
        # Reorder the headers and colors so that they fill by row instead of by column
        num_col = int(p_dict['legendColumns'])
        iter_headers = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = [_ for _ in iter_headers]

        iter_colors = itertools.chain(*[y_colors_tuple[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        # Note that the legend does not support the PolyCollection created by the
        # stackplot. Therefore we have to use a proxy artist.
        # https://stackoverflow.com/a/14534830/2827397
        p1 = patches.Rectangle((0, 0), 1, 1)
        p2 = patches.Rectangle((0, 0), 1, 1)

        legend = ax.legend([p1, p2], final_headers,
                           loc='upper center',
                           bbox_to_anchor=(0.5, -0.1),
                           ncol=num_col,
                           prop={'size': float(p_dict['legendFontSize'])}
                           )

        # Set legend font color
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]

        # Set legend area color
        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    for area in range(1, 9, 1):

        suppress_area = p_dict.get('suppressArea{0}'.format(area), False)

        if p_dict['area{0}Source'.format(area)] not in (u"", u"None") and not suppress_area:
            # Note that we do these after the legend is drawn so that these areas don't
            # affect the legend.

            # We need to reload the dates to ensure that they match the area being plotted
            # dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(area)])

            # =============================== Best Fit Line ===============================
            if props.get('line{0}BestFit'.format(area), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{0}'.format(area)],
                                                          line=area,
                                                          p_dict=p_dict
                                                          )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(area)]]

            # =============================== Min/Max Lines ===============================
            if p_dict['plotArea{0}Min'.format(area)]:
                ax.axhline(y=min(y_obs_tuple_rel['y_obs{0}'.format(area)]),
                           color=p_dict['area{0}Color'.format(area)],
                           **k_dict['k_min']
                           )
            if p_dict['plotArea{0}Max'.format(area)]:
                ax.axhline(y=max(y_obs_tuple_rel['y_obs{0}'.format(area)]),
                           color=p_dict['area{0}Color'.format(area)],
                           **k_dict['k_max']
                           )
            if plug_dict.get('forceOriginLines', True):
                ax.axhline(y=0,
                           color=p_dict['spineColor']
                           )

            # ================================== Markers ==================================
            # Note that stackplots don't support markers, so we need to plot a line (with
            # no width) on the plot to receive the markers.
            if p_dict['area{0}Marker'.format(area)] != 'None':
                ax.plot_date(p_dict['x_obs{0}'.format(area)], y_obs_tuple_rel['y_obs{0}'.format(area)],
                             marker=p_dict['area{0}Marker'.format(area)],
                             markeredgecolor=p_dict['area{0}MarkerColor'.format(area)],
                             markerfacecolor=p_dict['area{0}MarkerColor'.format(area)],
                             zorder=11,
                             lw=0
                             )

            if p_dict['line{0}Style'.format(area)] != 'None':
                ax.plot_date(p_dict['x_obs{0}'.format(area)], y_obs_tuple_rel['y_obs{0}'.format(area)],
                             zorder=10,
                             lw=1,
                             ls='-',
                             marker=None,
                             color=p_dict['line{0}Color'.format(area)]
                             )

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=plug_dict, p_dict=p_dict, k_dict=k_dict)
    chart_tools.format_grids(p_dict=p_dict, k_dict=k_dict)
    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.5, 0.98))
    chart_tools.format_axis_x_label(dev=props, p_dict=p_dict, k_dict=k_dict)
    chart_tools.format_axis_y1_label(p_dict=p_dict, k_dict=k_dict)
    chart_tools.format_axis_y_ticks(p_dict=p_dict, k_dict=k_dict)

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
