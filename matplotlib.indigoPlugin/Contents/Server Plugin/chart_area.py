#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the Area charts
All steps required to generate area charts.
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

log             = chart_tools.log
payload         = chart_tools.payload
p_dict          = payload['p_dict']
k_dict          = payload['k_dict']
plug_dict       = payload['prefs']
props           = payload['props']
chart_name      = props['name']
x_obs           = ''
y_obs_tuple     = ()  # Y values
y_obs_tuple_rel = {}  # Y values relative to chart (cumulative value)
y_colors_tuple  = ()  # Y area colors

log['Threaddebug'].append(u"chart_area.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass

    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax, p_dict=p_dict, k_dict=k_dict, logger=log)

    for area in range(1, 9, 1):

        suppress_area = p_dict.get('suppressArea{i}'.format(i=area), False)

        # If the area is suppressed, remind the user they suppressed it.
        if suppress_area:
            chart_tools.log['Info'].append(u"[{name}] Area {i} is suppressed by user setting. You can re-enable it in "
                                           u"the device configuration menu.".format(name=chart_name, i=area))

        # ============================== Plot the Areas ===============================
        # Plot the areas. If suppress_area is True, we skip it.
        if p_dict['area{i}Source'.format(i=area)] not in (u"", u"None") and not suppress_area:

            # If area color is the same as the background color, alert the user.
            if p_dict['area{i}Color'.format(i=area)] == p_dict['backgroundColor'] and not suppress_area:
                chart_tools.log['Warning'].append(u"[{name}] Area {i} color is the same as the background color (so "
                                                  u"you may not be able to see it).".format(name=chart_name, i=area))

            data_path   = plug_dict['dataPath'].encode("utf-8")
            area_source = p_dict['area{i}Source'.format(i=area)].encode("utf-8")
            data_column = chart_tools.get_data(data_source='{path}{source}'.format(path=data_path, source=area_source),
                                               logger=log
                                               )

            if plug_dict['verboseLogging']:
                chart_tools.log['Threaddebug'].append(u"[{n}] Data for Area {a}: {c}".format(n=chart_name,
                                                                                             a=area,
                                                                                             c=data_column
                                                                                             )
                                                      )

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{i}'.format(i=area)].append(element[0])
                p_dict['y_obs{i}'.format(i=area)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if props['area{i}adjuster'.format(i=area)] != "":
                temp_list = []
                for obs in p_dict['y_obs{i}'.format(i=area)]:
                    expr = u'{o}{p}'.format(o=obs, p=props['area{i}adjuster'.format(i=area)])
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                p_dict['y_obs{i}'.format(i=area)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{i}'.format(i=area)]

            try:
                limit = float(props['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = p_dict['y_obs{i}'.format(i=area)]
                new_old = props['limitDataRange']

                x_index = 'x_obs{i}'.format(i=area)
                y_index = 'y_obs{i}'.format(i=area)
                p_dict[x_index], p_dict[y_index] = chart_tools.prune_data(x_data=dates_to_plot,
                                                                          y_data=y_obs,
                                                                          limit=limit,
                                                                          new_old=new_old,
                                                                          logger=log)

            # ======================== Convert Dates for Charting =========================
            p_dict['x_obs{i}'.format(i=area)] = \
                chart_tools.format_dates(list_of_dates=p_dict['x_obs{i}'.format(i=area)], logger=log)

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=area)]]

            # We need to plot all the stacks at once, so we create some tuples to hold the data we need later.
            y_obs_tuple += (p_dict['y_obs{i}'.format(i=area)],)
            y_colors_tuple += (p_dict['area{i}Color'.format(i=area)],)
            x_obs = p_dict['x_obs{i}'.format(i=area)]

            # ================================ Annotations ================================

            # New annotations code begins here - DaveL17 2019-06-05
            for _ in range(1, area + 1, 1):

                tup = ()

                # We start with the ordinal list and create a tuple to hold all the lists that come before it.
                for k in range(_, 0, -1):

                    tup += (p_dict['y_obs{i}'.format(i=k)],)

                # The relative value is the sum of each list element plus the ones that come before it
                # (i.e., tup[n][0] + tup[n-1][0] + tup[n-2][0]
                y_obs_tuple_rel['y_obs{i}'.format(i=area)] = [sum(t) for t in zip(*tup)]

            if p_dict['area{i}Annotate'.format(i=area)]:
                for xy in zip(p_dict['x_obs{i}'.format(i=area)], y_obs_tuple_rel['y_obs{i}'.format(i=area)]):
                    ax.annotate(u"{i}".format(i=xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

    y_data = chart_tools.hide_anomalies(data=y_obs_tuple[0], props=props, logger=log)
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
            if p_dict['area{i}Legend'.format(i=counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['area{i}Legend'.format(i=counter)])
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
                           bbox_to_anchor=(0.5, -0.15),
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

        suppress_area = p_dict.get('suppressArea{i}'.format(i=area), False)

        if p_dict['area{i}Source'.format(i=area)] not in (u"", u"None") and not suppress_area:
            # Note that we do these after the legend is drawn so that these areas don't
            # affect the legend.

            # We need to reload the dates to ensure that they match the area being plotted
            # dates_to_plot = self.format_dates(p_dict['x_obs{i}'.format(i=area)])

            # =============================== Best Fit Line ===============================
            if props.get('line{i}BestFit'.format(i=area), False):
                chart_tools.format_best_fit_line_segments(ax=ax,
                                                          dates_to_plot=p_dict['x_obs{i}'.format(i=area)],
                                                          line=area,
                                                          p_dict=p_dict,
                                                          logger=log)

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=area)]]

            # =============================== Min/Max Lines ===============================
            if p_dict['plotArea{i}Min'.format(i=area)]:
                ax.axhline(y=min(y_obs_tuple_rel['y_obs{i}'.format(i=area)]),
                           color=p_dict['area{i}Color'.format(i=area)],
                           **k_dict['k_min']
                           )
            if p_dict['plotArea{i}Max'.format(i=area)]:
                ax.axhline(y=max(y_obs_tuple_rel['y_obs{i}'.format(i=area)]),
                           color=p_dict['area{i}Color'.format(i=area)],
                           **k_dict['k_max']
                           )
            if plug_dict.get('forceOriginLines', True):
                ax.axhline(y=0,
                           color=p_dict['spineColor']
                           )

            # ================================== Markers ==================================
            # Note that stackplots don't support markers, so we need to plot a line (with
            # no width) on the plot to receive the markers.
            if p_dict['area{i}Marker'.format(i=area)] != 'None':
                ax.plot_date(p_dict['x_obs{i}'.format(i=area)], y_obs_tuple_rel['y_obs{i}'.format(i=area)],
                             marker=p_dict['area{i}Marker'.format(i=area)],
                             markeredgecolor=p_dict['area{i}MarkerColor'.format(i=area)],
                             markerfacecolor=p_dict['area{i}MarkerColor'.format(i=area)],
                             zorder=11,
                             lw=0
                             )

            if p_dict['line{i}Style'.format(i=area)] != 'None':
                ax.plot_date(p_dict['x_obs{i}'.format(i=area)], y_obs_tuple_rel['y_obs{i}'.format(i=area)],
                             zorder=10,
                             lw=1,
                             ls='-',
                             marker=None,
                             color=p_dict['line{i}Color'.format(i=area)]
                             )

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
