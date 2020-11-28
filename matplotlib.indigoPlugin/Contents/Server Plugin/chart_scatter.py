#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the scatter charts
All steps required to generate scatter charts.
-----

"""

import itertools
import sys
import pickle

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
import matplotlib.pyplot as plt

import chart_tools

log          = chart_tools.log
payload      = chart_tools.payload
p_dict       = payload['p_dict']
k_dict       = payload['k_dict']
props        = payload['props']
plug_dict        = payload['prefs']
group_colors = []


log['Threaddebug'].append(u"chart_scatter.py called.")

try:

    def __init__():
        pass


    for color in ['backgroundColor', 'faceColor']:
        p_dict[color] = chart_tools.fix_rgb(color=p_dict[color])

    dpi = plt.rcParams['savefig.dpi']
    height = float(p_dict['chart_height'])
    width = float(p_dict['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    for thing in range(1, 5, 1):

        suppress_group = p_dict.get('suppressGroup{0}'.format(thing), False)

        p_dict['group{0}Color'.format(thing)] = chart_tools.fix_rgb(p_dict['group{0}Color'.format(thing)])

        gmc2 = chart_tools.fix_rgb(p_dict['group{0}MarkerColor'.format(thing)])
        p_dict['group{0}MarkerColor'.format(thing)] = gmc2

        best_fit = chart_tools.fix_rgb(p_dict['line{0}BestFitColor'.format(thing)])
        p_dict['line{0}BestFitColor'.format(thing)] = best_fit

        # If dot color is the same as the background color, alert the user.
        if p_dict['group{0}Color'.format(thing)] == p_dict['backgroundColor'] and not \
                suppress_group:
            chart_tools.log['Debug'].append(u"[{0}] Group {1} color is the same as the background color (so you "
                                            u"may not be able to see it).".format(props['name'], thing))

        # If the group is suppressed, remind the user they suppressed it.
        if suppress_group:
            chart_tools.log['Info'].append(u"[{0}] Group {1} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(props['name'], thing))

        # ============================== Plot the Points ==============================
        # Plot the groups. If suppress_group is True, we skip it.
        if p_dict['group{0}Source'.format(thing)] not in ("", "None") and not suppress_group:

            # Add group color to list for later use
            group_colors.append(p_dict['group{0}Color'.format(thing)])

            # There is a bug in matplotlib (fixed in newer versions) where points would not
            # plot if marker set to 'none'. This overrides the behavior.
            if p_dict['group{0}Marker'.format(thing)] == u'None':
                p_dict['group{0}Marker'.format(thing)] = '.'
                p_dict['group{0}MarkerColor'.format(thing)] = p_dict['group{0}Color'.format(thing)]

            data_path = plug_dict['dataPath'].encode("utf-8")
            group_source = p_dict['group{0}Source'.format(thing)].encode("utf-8")
            data_column = chart_tools.get_data('{0}{1}'.format(data_path, group_source), logger=log)

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"Data for group {0}: {1}".format(thing, data_column))

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

                prune = chart_tools.prune_data(dates_to_plot, y_obs, limit, new_old, logger=log)
                p_dict['x_obs{0}'.format(thing)], p_dict['y_obs{0}'.format(thing)] = prune

            # Convert the date strings for charting.
            p_dict['x_obs{0}'.format(thing)] = chart_tools.format_dates(p_dict['x_obs{0}'.format(thing)], logger=log)

            # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
            ax.scatter(p_dict['x_obs{0}'.format(thing)],
                       p_dict['y_obs{0}'.format(thing)],
                       c=p_dict['group{0}Color'.format(thing)],
                       marker=p_dict['group{0}Marker'.format(thing)],
                       edgecolor=p_dict['group{0}MarkerColor'.format(thing)],
                       linewidths=0.75,
                       zorder=10,
                       **k_dict['k_line']
                       )

            # =============================== Best Fit Line ===============================
            if props.get('line{0}BestFit'.format(thing), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{0}'.format(thing)],
                                                          line=thing,
                                                          p_dict=p_dict,
                                                          logger=log
                                                          )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)]]

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
    chart_tools.format_axis_y1_min_max(p_dict, logger=log)

    # ================================== Legend ===================================
    if p_dict['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        legend_styles = []
        labels = []

        # Set legend group colors
        # Note that we do this in a slightly different order than other chart types
        # because we use legend styles for scatter charts differently than other
        # chart types.
        num_col = int(p_dict['legendColumns'])
        iter_colors  = itertools.chain(*[group_colors[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        headers = [_.decode('utf-8') for _ in p_dict['headers']]
        for header in headers:

            if p_dict['group{0}Legend'.format(counter)] == "":
                labels.append(header)
            else:
                labels.append(p_dict['group{0}Legend'.format(counter)])

            legend_styles.append(tuple(plt.plot([],
                                                color=p_dict['group{0}MarkerColor'.format(counter)],
                                                linestyle='',
                                                marker=p_dict['group{0}Marker'.format(counter)],
                                                markerfacecolor=final_colors[counter-1],
                                                markeredgewidth=.8,
                                                markeredgecolor=p_dict['group{0}MarkerColor'.format(counter)]
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
                           ncol=int(p_dict['legendColumns']),
                           numpoints=1,
                           markerscale=0.6,
                           prop={'size': float(p_dict['legendFontSize'])}
                           )

        # Set legend font colors
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]

        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    # ================================= Min / Max =================================
    for thing in range(1, 5, 1):
        if p_dict['plotGroup{0}Min'.format(thing)]:
            ax.axhline(y=min(p_dict['y_obs{0}'.format(thing)]),
                       color=p_dict['group{0}Color'.format(thing)],
                       **k_dict['k_min']
                       )
        if p_dict['plotGroup{0}Max'.format(thing)]:
            ax.axhline(y=max(p_dict['y_obs{0}'.format(thing)]),
                       color=p_dict['group{0}Color'.format(thing)],
                       **k_dict['k_max']
                       )
        if plug_dict.get('forceOriginLines', True):
            ax.axhline(y=0, color=p_dict['spineColor'])

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=plug_dict, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_grids(p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.5, 0.98))
    chart_tools.format_axis_x_label(dev=props, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y1_label(p_dict=p_dict, k_dict=k_dict, logger=log)
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

chart_tools.log['Info'].append(u"[{0}] chart refreshed.".format(props['name']))
pickle.dump(chart_tools.log, sys.stdout)
