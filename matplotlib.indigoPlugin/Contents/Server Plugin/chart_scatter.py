# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the scatter charts

All steps required to generate scatter charts.
"""

# Built-in Modules
import itertools
import json
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
# from matplotlib import patches as patches
from matplotlib import patches
# My modules
import chart_tools  # noqa

LOG          = chart_tools.LOG
PAYLOAD      = chart_tools.payload
P_DICT       = PAYLOAD['p_dict']
K_DICT       = PAYLOAD['k_dict']
PROPS        = PAYLOAD['props']
CHART_NAME   = PROPS['name']
PLUG_DICT    = PAYLOAD['prefs']
GROUP_COLORS = []


LOG['Threaddebug'].append("chart_scatter.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(PAYLOAD)

try:

    def __init__():
        pass


    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    for thing in range(1, 5, 1):

        suppress_group = P_DICT.get(f'suppressGroup{thing}', False)

        # If the group is suppressed, remind the user they suppressed it.
        if suppress_group:
            LOG['Info'].append(
                f"[{CHART_NAME}] Group {thing} is suppressed by user setting. You can re-enable "
                f"it in the device configuration menu."
            )

        # ============================== Plot the Points ==============================
        # Plot the groups. If suppress_group is True, we skip it.
        if P_DICT[f'group{thing}Source'] not in ("", "None") and not suppress_group:

            # If dot color is the same as the background color, alert the user.
            if P_DICT[f'group{thing}Color'] == P_DICT['backgroundColor'] and not suppress_group:
                LOG['Warning'].append(
                    f"[{CHART_NAME}] Group {thing} color is the same as the background color (so "
                    f"you may not be able to see it)."
                )

            # Add group color to list for later use
            GROUP_COLORS.append(P_DICT[f'group{thing}Color'])

            # There is a bug in matplotlib (fixed in newer versions) where points would not plot if
            # marker set to 'none'. This overrides the behavior.
            if P_DICT[f'group{thing}Marker'] == 'None':
                P_DICT[f'group{thing}Marker'] = '.'
                P_DICT[f'group{thing}MarkerColor'] = P_DICT[f'group{thing}Color']

            data_path = PLUG_DICT['dataPath']
            group_source = P_DICT[f'group{thing}Source']
            data_column = chart_tools.get_data(data_source=f'{data_path}{group_source}', logger=LOG)

            if PLUG_DICT['verboseLogging']:
                LOG['Threaddebug'].append(f"[{CHART_NAME}] Data for group {thing}: {data_column}")

            # Pull the headers
            P_DICT['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                P_DICT[f'x_obs{thing}'].append(element[0])
                P_DICT[f'y_obs{thing}'].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple binary
            # sources on the same chart.)
            if PROPS[f'group{thing}adjuster'] != "":
                temp_list = []
                for obs in P_DICT[f'y_obs{thing}']:
                    expr = f"{obs}{PROPS[f'group{thing}adjuster']}"
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                P_DICT[f'y_obs{thing}'] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = P_DICT[f'x_obs{thing}']

            try:
                limit = float(PROPS['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs   = P_DICT[f'y_obs{thing}']
                new_old = PROPS['limitDataRange']

                prune = chart_tools.prune_data(
                    x_data=dates_to_plot,
                    y_data=y_obs,
                    limit=limit,
                    new_old=new_old,
                    logger=LOG
                )
                P_DICT[f'x_obs{thing}'], P_DICT[f'y_obs{thing}'] = prune

            # Convert the date strings for charting.
            P_DICT[f'x_obs{thing}'] = \
                chart_tools.format_dates(list_of_dates=P_DICT[f'x_obs{thing}'], logger=LOG)

            y_data = chart_tools.hide_anomalies(
                data=P_DICT[f'y_obs{thing}'],
                props=PROPS,
                logger=LOG
            )

            # Note that using 'c' to set the color instead of 'color' makes a difference for some
            # reason.
            ax.scatter(
                P_DICT[f'x_obs{thing}'],
                y_data,
                color=P_DICT[f'group{thing}Color'],
                marker=P_DICT[f'group{thing}Marker'],
                edgecolor=P_DICT[f'group{thing}MarkerColor'],
                linewidths=0.75,
                zorder=10,
                **K_DICT['k_line']
            )

            # =============================== Best Fit Line ===============================
            if PROPS.get(f'line{thing}BestFit', False):
                chart_tools.format_best_fit_line_segments(
                    ax=ax,
                    dates_to_plot=P_DICT[f'x_obs{thing}'],
                    line=thing,
                    p_dict=P_DICT,
                    logger=LOG
                )

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{thing}']]

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
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
        legend_styles = []
        labels = []

        # Set legend group colors
        # Note that we do this in a slightly different order than other chart types because we use
        # legend styles for scatter charts differently than other chart types.
        num_col = int(P_DICT['legendColumns'])
        iter_colors  = itertools.chain(*[GROUP_COLORS[i::num_col] for i in range(num_col)])
        final_colors = list(iter_colors)

        headers = [_.decode('utf-8') for _ in P_DICT['headers']]
        for header in headers:

            if P_DICT[f'group{counter}Legend'] == "":
                labels.append(header)
            else:
                labels.append(P_DICT[f'group{counter}Legend'])

            legend_styles.append(
                tuple(plt.plot(
                    [],
                    color=P_DICT[f'group{counter}MarkerColor'],
                    linestyle='',
                    marker=P_DICT[f'group{counter}Marker'],
                    markerfacecolor=final_colors[counter-1],
                    markeredgewidth=.8,
                    markeredgecolor=P_DICT[f'group{counter}MarkerColor']
                )
                )
            )
            counter += 1

        # Reorder the headers so that they fill by row instead of by column
        iter_headers   = itertools.chain(*[labels[i::num_col] for i in range(num_col)])
        final_headers = list(iter_headers)

        legend = ax.legend(
            legend_styles,
            final_headers,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.15),
            ncol=int(P_DICT['legendColumns']),
            numpoints=1,
            markerscale=0.6,
            prop={'size': float(P_DICT['legendFontSize'])}
        )

        # Set legend font colors
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]

        num_handles = len(legend.legendHandles)
        _ = [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    # ================================= Min / Max =================================
    for thing in range(1, 5, 1):
        if P_DICT[f'plotGroup{thing}Min']:
            ax.axhline(
                y=min(P_DICT[f'y_obs{thing}']),
                color=P_DICT[f'group{thing}Color'],
                **K_DICT['k_min']
            )
        if P_DICT[f'plotGroup{thing}Max']:
            ax.axhline(
                y=max(P_DICT[f'y_obs{thing}']),
                color=P_DICT[f'group{thing}Color'],
                **K_DICT['k_max']
            )
        if PLUG_DICT.get('forceOriginLines', True):
            ax.axhline(y=0, color=P_DICT['spineColor'])

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
