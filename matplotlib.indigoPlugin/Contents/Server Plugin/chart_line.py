#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the line charts
All steps required to generate line charts.
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
import matplotlib.dates as mdate

# My modules
import chart_tools

log         = chart_tools.log
payload     = chart_tools.payload
p_dict      = payload['p_dict']
k_dict      = payload['k_dict']
plug_dict   = payload['prefs']
props       = payload['props']
chart_name  = props['name']
line_colors = []

log['Threaddebug'].append(u"chart_line.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass


    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

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

        suppress_line = p_dict.get('suppressLine{i}'.format(i=line), False)

        # If the line is suppressed, remind the user they suppressed it.
        if suppress_line:
            chart_tools.log['Info'].append(u"[{name}] Line {i} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(name=chart_name, i=line))

        # ============================== Plot the Lines ===============================
        # Plot the lines. If suppress_line is True, we skip it.
        if p_dict['line{i}Source'.format(i=line)] not in (u"", u"None") and not suppress_line:

            # If line color is the same as the background color, alert the user.
            if p_dict['line{i}Color'.format(i=line)] == p_dict['backgroundColor'] and not suppress_line:
                chart_tools.log['Warning'].append(u"[{name}] Area {i} color is the same as the background color (so "
                                                  u"you may not be able to see it).".format(name=chart_name, i=line))

            # Add line color to list for later use
            line_colors.append(p_dict['line{i}Color'.format(i=line)])

            data_path = plug_dict['dataPath'].encode("utf-8")
            line_source = p_dict['line{i}Source'.format(i=line)].encode("utf-8")

            # ==============================  Get the Data  ===============================
            data_column = chart_tools.get_data(data_source='{path}{source}'.format(path=data_path,
                                                                                   source=line_source),
                                               logger=log
                                               )

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"[{n}] Data for Line {i}: {c}".format(n=chart_name,
                                                                                             i=line,
                                                                                             c=data_column
                                                                                             )
                                                      )

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{i}'.format(i=line)].append(element[0])
                p_dict['y_obs{i}'.format(i=line)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if props['line{i}adjuster'.format(i=line)] != "":
                temp_list = []
                for obs in p_dict['y_obs{i}'.format(i=line)]:
                    expr = u'{o}{p}'.format(o=obs, p=props['line{i}adjuster'.format(i=line)])
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                p_dict['y_obs{i}'.format(i=line)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{i}'.format(i=line)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = p_dict['y_obs{i}'.format(i=line)]
                new_old = props['limitDataRange']

                prune = chart_tools.prune_data(x_data=dates_to_plot,
                                               y_data=y_obs,
                                               limit=limit,
                                               new_old='None',
                                               logger=log
                                               )
                p_dict['x_obs{i}'.format(i=line)], p_dict['y_obs{i}'.format(i=line)] = prune

            # ======================== Convert Dates for Charting =========================
            p_dict['x_obs{i}'.format(i=line)] = \
                chart_tools.format_dates(list_of_dates=p_dict['x_obs{i}'.format(i=line)],
                                         logger=log
                                         )

            # ===========================  Hide Anomalous Data  ===========================
            y_data = chart_tools.hide_anomalies(data=p_dict['y_obs{i}'.format(i=line)], props=props, logger=log)

            ax.plot_date(p_dict['x_obs{i}'.format(i=line)],
                         y_data,
                         color=p_dict['line{i}Color'.format(i=line)],
                         linestyle=p_dict['line{i}Style'.format(i=line)],
                         marker=p_dict['line{i}Marker'.format(i=line)],
                         markeredgecolor=p_dict['line{i}MarkerColor'.format(i=line)],
                         markerfacecolor=p_dict['line{i}MarkerColor'.format(i=line)],
                         zorder=10,
                         **k_dict['k_line']
                         )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=line)]]

            if p_dict['line{i}Fill'.format(i=line)]:
                ax.fill_between(p_dict['x_obs{i}'.format(i=line)],
                                0,
                                p_dict['y_obs{i}'.format(i=line)],
                                color=p_dict['line{i}Color'.format(i=line)],
                                **k_dict['k_fill']
                                )

            # ================================ Annotations ================================
            if p_dict['line{i}Annotate'.format(i=line)]:
                for xy in zip(p_dict['x_obs{i}'.format(i=line)], p_dict['y_obs{i}'.format(i=line)]):
                    ax.annotate(u"{a}".format(a=xy[1]),
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
            if p_dict['line{c}Legend'.format(c=counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['line{c}Legend'.format(c=counter)])
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

        suppress_line = p_dict.get('suppressLine{i}'.format(i=line), False)

        if p_dict['line{i}Source'.format(i=line)] not in (u"", u"None") and not suppress_line:

            # Note that we do these after the legend is drawn so that these lines don't
            # affect the legend.

            # =============================== Best Fit Line ===============================
            if props.get('line{i}BestFit'.format(i=line), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{i}'.format(i=line)],
                                                          line=line,
                                                          p_dict=p_dict,
                                                          logger=log)

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=line)]]

            # =============================== Fill Between ================================
            if p_dict['line{i}Fill'.format(i=line)]:
                ax.fill_between(p_dict['x_obs{i}'.format(i=line)],
                                0,
                                p_dict['y_obs{i}'.format(i=line)],
                                color=p_dict['line{i}Color'.format(i=line)],
                                **k_dict['k_fill']
                                )

            # =============================== Min/Max Lines ===============================
            if p_dict['plotLine{i}Min'.format(i=line)]:
                ax.axhline(y=min(p_dict['y_obs{i}'.format(i=line)]),
                           color=p_dict['line{i}Color'.format(i=line)],
                           **k_dict['k_min'])
            if p_dict['plotLine{i}Max'.format(i=line)]:
                ax.axhline(y=max(p_dict['y_obs{i}'.format(i=line)]),
                           color=p_dict['line{i}Color'.format(i=line)],
                           **k_dict['k_max']
                           )
            if plug_dict.get('forceOriginLines', True):
                ax.axhline(y=0, color=p_dict['spineColor'])

    chart_tools.format_custom_line_segments(ax=ax, plug_dict=plug_dict, p_dict=p_dict, k_dict=k_dict, logger=log, orient="horiz")
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
