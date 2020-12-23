#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the scatter charts
All steps required to generate scatter charts.
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

log          = chart_tools.log
payload      = chart_tools.payload
p_dict       = payload['p_dict']
k_dict       = payload['k_dict']
props        = payload['props']
chart_name   = props['name']
plug_dict    = payload['prefs']
group_colors = []


log['Threaddebug'].append(u"chart_scatter.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass


    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    for thing in range(1, 5, 1):

        suppress_group = p_dict.get('suppressGroup{i}'.format(i=thing), False)

        # If the group is suppressed, remind the user they suppressed it.
        if suppress_group:
            chart_tools.log['Info'].append(u"[{name}] Group {i} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(name=chart_name, i=thing))

        # ============================== Plot the Points ==============================
        # Plot the groups. If suppress_group is True, we skip it.
        if p_dict['group{i}Source'.format(i=thing)] not in ("", "None") and not suppress_group:

            # If dot color is the same as the background color, alert the user.
            if p_dict['group{i}Color'.format(i=thing)] == p_dict['backgroundColor'] and not suppress_group:
                chart_tools.log['Warning'].append(u"[{name}] Group {i} color is the same as the background color (so "
                                                  u"you may not be able to see it).".format(name=chart_name, i=thing))

            # Add group color to list for later use
            group_colors.append(p_dict['group{i}Color'.format(i=thing)])

            # There is a bug in matplotlib (fixed in newer versions) where points would not
            # plot if marker set to 'none'. This overrides the behavior.
            if p_dict['group{i}Marker'.format(i=thing)] == u'None':
                p_dict['group{i}Marker'.format(i=thing)] = '.'
                p_dict['group{i}MarkerColor'.format(i=thing)] = p_dict['group{i}Color'.format(i=thing)]

            data_path = plug_dict['dataPath'].encode("utf-8")
            group_source = p_dict['group{i}Source'.format(i=thing)].encode("utf-8")
            data_column = chart_tools.get_data(data_source='{d}{g}'.format(d=data_path, g=group_source), logger=log)

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"[{n}] Data for group {i}: {c}".format(n=chart_name,
                                                                                              i=thing,
                                                                                              c=data_column
                                                                                              )
                                                      )

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{i}'.format(i=thing)].append(element[0])
                p_dict['y_obs{i}'.format(i=thing)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if props['group{i}adjuster'.format(i=thing)] != "":
                temp_list = []
                for obs in p_dict['y_obs{i}'.format(i=thing)]:
                    expr = u'{o}{p}'.format(o=obs, p=props['group{i}adjuster'.format(i=thing)])
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                p_dict['y_obs{i}'.format(i=thing)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{i}'.format(i=thing)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs   = p_dict['y_obs{i}'.format(i=thing)]
                new_old = props['limitDataRange']

                prune = chart_tools.prune_data(x_data=dates_to_plot,
                                               y_data=y_obs,
                                               limit=limit,
                                               new_old=new_old,
                                               logger=log
                                               )
                p_dict['x_obs{i}'.format(i=thing)], p_dict['y_obs{i}'.format(i=thing)] = prune

            # Convert the date strings for charting.
            p_dict['x_obs{i}'.format(i=thing)] = \
                chart_tools.format_dates(list_of_dates=p_dict['x_obs{i}'.format(i=thing)],
                                         logger=log
                                         )

            y_data = chart_tools.hide_anomalies(data=p_dict['y_obs{i}'.format(i=thing)], props=props, logger=log)

            # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
            ax.scatter(p_dict['x_obs{i}'.format(i=thing)],
                       y_data,
                       c=p_dict['group{i}Color'.format(i=thing)],
                       marker=p_dict['group{i}Marker'.format(i=thing)],
                       edgecolor=p_dict['group{i}MarkerColor'.format(i=thing)],
                       linewidths=0.75,
                       zorder=10,
                       **k_dict['k_line']
                       )

            # =============================== Best Fit Line ===============================
            if props.get('line{i}BestFit'.format(i=thing), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{i}'.format(i=thing)],
                                                          line=thing,
                                                          p_dict=p_dict,
                                                          logger=log
                                                          )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=thing)]]

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

            if p_dict['group{c}Legend'.format(c=counter)] == "":
                labels.append(header)
            else:
                labels.append(p_dict['group{c}Legend'.format(c=counter)])

            legend_styles.append(tuple(plt.plot([],
                                                color=p_dict['group{c}MarkerColor'.format(c=counter)],
                                                linestyle='',
                                                marker=p_dict['group{c}Marker'.format(c=counter)],
                                                markerfacecolor=final_colors[counter-1],
                                                markeredgewidth=.8,
                                                markeredgecolor=p_dict['group{c}MarkerColor'.format(c=counter)]
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
        if p_dict['plotGroup{i}Min'.format(i=thing)]:
            ax.axhline(y=min(p_dict['y_obs{i}'.format(i=thing)]),
                       color=p_dict['group{i}Color'.format(i=thing)],
                       **k_dict['k_min']
                       )
        if p_dict['plotGroup{i}Max'.format(i=thing)]:
            ax.axhline(y=max(p_dict['y_obs{i}'.format(i=thing)]),
                       color=p_dict['group{i}Color'.format(i=thing)],
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
    tb = traceback.format_exc()
    chart_tools.log['Critical'].append(u"[{n}] {s}".format(n=chart_name, s=tb))

pickle.dump(chart_tools.log, sys.stdout)
