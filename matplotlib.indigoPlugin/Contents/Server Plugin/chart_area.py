# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the Area charts

All steps required to generate area charts.
"""
# Built-in Modules
import itertools
import json
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import patches
# My Modules
import chart_tools

LOG             = chart_tools.LOG
PAYLOAD         = chart_tools.payload
P_DICT          = PAYLOAD['p_dict']
K_DICT          = PAYLOAD['k_dict']
PLUG_DICT       = PAYLOAD['prefs']
PROPS           = PAYLOAD['props']
CHART_NAME      = PROPS['name']
X_OBS           = ''
Y_OBS_TUPLE     = ()  # Y values
Y_OBS_TUPLE_REL = {}  # Y values relative to chart (cumulative value)
Y_COLORS_TUPLE  = ()  # Y area colors

LOG['Threaddebug'].append("chart_area.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append("!!! FOO !!!")


def __init__():
    pass


try:
    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    for area in range(1, 9, 1):

        suppress_area = P_DICT.get(f"suppressArea{area}", False)

        # If the area is suppressed, remind the user they suppressed it.
        if suppress_area:
            LOG['Info'].append(
                f"[{CHART_NAME}] Area {area} is suppressed by user setting. You can re-enable it "
                f"in the device configuration menu."
            )

        # ============================== Plot the Areas ===============================
        # Plot the areas. If suppress_area is True, we skip it.
        if P_DICT[f'area{area}Source'] not in ("", "None") and not suppress_area:

            # If area color is the same as the background color, alert the user.
            if P_DICT[f'area{area}Color'] == P_DICT['backgroundColor'] and not suppress_area:
                LOG['Warning'].append(
                    f"[{CHART_NAME}] Area {area} color is the same as the background color (so "
                    f"you may not be able to see it)."
                )

            data_path   = PLUG_DICT['dataPath']
            area_source = P_DICT[f'area{area}Source']
            data_column = chart_tools.get_data(data_source=f'{data_path}{area_source}', logger=LOG)

            if PLUG_DICT['verboseLogging']:
                LOG['Threaddebug'].append(f"[{CHART_NAME}] Data for Area {area}: {data_column}")

            # Pull the headers
            P_DICT['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                P_DICT[f'x_obs{area}'].append(element[0])
                P_DICT[f'y_obs{area}'].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple binary
            # sources on the same chart.)
            if PROPS[f'area{area}adjuster'] != "":
                temp_list = []
                for obs in P_DICT[f'y_obs{area}']:
                    expr = f"{obs}{PROPS[f'area{area}adjuster']}"
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                P_DICT[f'y_obs{area}'] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = P_DICT[f'x_obs{area}']

            try:
                limit = float(PROPS['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = P_DICT[f'y_obs{area}']
                new_old = PROPS['limitDataRange']

                x_index = f'x_obs{area}'
                y_index = f'y_obs{area}'
                P_DICT[x_index], P_DICT[y_index] = chart_tools.prune_data(
                    x_data=dates_to_plot,
                    y_data=y_obs,
                    limit=limit,
                    new_old=new_old,
                    logger=LOG
                )

            # ======================== Convert Dates for Charting =========================
            P_DICT[f'x_obs{area}'] = \
                chart_tools.format_dates(list_of_dates=P_DICT[f'x_obs{area}'], logger=LOG)

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{area}']]

            # We need to plot all the stacks at once, so we create some tuples to hold the data we
            # need later.
            Y_OBS_TUPLE += (P_DICT[f'y_obs{area}'],)
            Y_COLORS_TUPLE += (P_DICT[f'area{area}Color'],)
            X_OBS = P_DICT[f'x_obs{area}']

            # ================================ Annotations ================================

            # New annotations code begins here - DaveL17 2019-06-05
            for _ in range(1, area + 1, 1):

                tup = ()

                # We start with the ordinal list and create a tuple to hold all the lists that
                # come before it.
                for k in range(_, 0, -1):

                    tup += (P_DICT[f'y_obs{area}'],)

                # The relative value is the sum of each list element plus the ones that come before
                # it (i.e., tup[n][0] + tup[n-1][0] + tup[n-2][0]
                Y_OBS_TUPLE_REL[f'y_obs{area}'] = [sum(t) for t in zip(*tup)]

            if P_DICT[f'area{area}Annotate']:
                for xy in zip(P_DICT[f'x_obs{area}'], Y_OBS_TUPLE_REL[f'y_obs{area}']):
                    ax.annotate(
                        f"{xy[1]}",
                        xy=xy,
                        xytext=(0, 0),
                        zorder=10,
                        **K_DICT['k_annotation']
                    )

    y_data = chart_tools.hide_anomalies(data=Y_OBS_TUPLE[0], props=PROPS, logger=LOG)
    ax.stackplot(
        X_OBS,
        Y_OBS_TUPLE,
        edgecolor=None,
        colors=Y_COLORS_TUPLE,
        zorder=10,
        lw=0,
        **K_DICT['k_line']
    )

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'. The p_dict['data_array'] contains individual data points and
    # doesn't take into account the additive nature of the plot. Therefore, we get the axis scaling
    # values from the plot and then use those for min/max.
    _ = [P_DICT['data_array'].append(node) for node in ax.get_ylim()]

    chart_tools.format_axis_y1_min_max(p_dict=P_DICT, logger=LOG)

    # Transparent Chart Fill
    if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
        ax.add_patch(
            patches.Rectangle(
                (0, 0), 1, 1,
                transform=ax.transAxes,
                facecolor=P_DICT['faceColor'],
                zorder=1
            )
        )

    # ================================== Legend ===================================
    if P_DICT['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []

        headers = [_ for _ in P_DICT['headers']]
        # headers = [_.decode('utf-8') for _ in P_DICT['headers']]

        for header in headers:
            if P_DICT[f'area{counter}Legend'] == "":
                final_headers.append(header)
            else:
                final_headers.append(P_DICT[f'area{counter}Legend'])
            counter += 1

        # Set the legend
        # Reorder the headers and colors so that they fill by row instead of by column
        num_col = int(P_DICT['legendColumns'])
        iter_headers = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = list(iter_headers)

        iter_colors = itertools.chain(*[Y_COLORS_TUPLE[i::num_col] for i in range(num_col)])
        final_colors = list(iter_colors)

        # Note that the legend does not support the PolyCollection created by the stackplot.
        # Therefore, we have to use a proxy artist. https://stackoverflow.com/a/14534830/2827397
        p1 = patches.Rectangle((0, 0), 1, 1)
        p2 = patches.Rectangle((0, 0), 1, 1)

        legend = ax.legend(
            [p1, p2],
            final_headers,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.15),
            ncol=num_col,
            prop={'size': float(P_DICT['legendFontSize'])}
        )

        # Set legend font color
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]

        # Set legend area color
        num_handles = len(legend.legendHandles)
        _ = [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    for area in range(1, 9, 1):

        suppress_area = P_DICT.get(f'suppressArea{area}', False)

        if P_DICT[f'area{area}Source'] not in ("", "None") and not suppress_area:
            # Note that we do these after the legend is drawn so that these areas don't affect the
            # legend.

            # We need to reload the dates to ensure that they match the area being plotted
            # dates_to_plot = self.format_dates(p_dict[f'x_obs{area}'])

            # =============================== Best Fit Line ===============================
            if PROPS.get(f'line{area}BestFit', False):
                chart_tools.format_best_fit_line_segments(
                    ax=ax,
                    dates_to_plot=P_DICT[f'x_obs{area}'],
                    line=area,
                    p_dict=P_DICT,
                    logger=LOG
                )

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{area}']]

            # =============================== Min/Max Lines ===============================
            if P_DICT[f'plotArea{area}Min']:
                ax.axhline(
                    y=min(Y_OBS_TUPLE_REL[f'y_obs{area}']),
                    color=P_DICT[f'area{area}Color'],
                    **K_DICT['k_min']
                )
            if P_DICT[f'plotArea{area}Max']:
                ax.axhline(
                    y=max(Y_OBS_TUPLE_REL[f'y_obs{area}']),
                    color=P_DICT[f'area{area}Color'],
                    **K_DICT['k_max']
                )
            if PLUG_DICT.get('forceOriginLines', True):
                ax.axhline(
                    y=0,
                    color=P_DICT['spineColor']
                )

            # ================================== Markers ==================================
            # Note that stackplots don't support markers, so we need to plot a line (with no width)
            # on the plot to receive the markers.
            if P_DICT[f'area{area}Marker'] != 'None':
                ax.plot_date(
                    P_DICT[f'x_obs{area}'],
                    Y_OBS_TUPLE_REL[f'y_obs{area}'],
                    marker=P_DICT[f'area{area}Marker'],
                    markeredgecolor=P_DICT[f'area{area}MarkerColor'],
                    markerfacecolor=P_DICT[f'area{area}MarkerColor'],
                    zorder=11,
                    lw=0
                )

            if P_DICT[f'line{area}Style'] != 'None':
                ax.plot_date(
                    P_DICT[f'x_obs{area}'], Y_OBS_TUPLE_REL[f'y_obs{area}'],
                    zorder=10,
                    lw=1,
                    ls='-',
                    marker=None,
                    color=P_DICT[f'line{area}Color']
                )

    chart_tools.format_custom_line_segments(
        ax=ax,
        plug_dict=PLUG_DICT,
        p_dict=P_DICT,
        k_dict=K_DICT,
        logger=LOG,
        orient="horiz"
    )
    chart_tools.format_grids(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.98))
    chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y1_label(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y_ticks(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # Note that subplots_adjust affects the space surrounding the subplots and not the fig.
    plt.subplots_adjust(
        top=0.90,
        bottom=0.20,
        left=0.10,
        right=0.90,
        hspace=None,
        wspace=None
    )

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
