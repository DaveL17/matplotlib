# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the line charts
All steps required to generate line charts.
"""

# Built-in Modules
import itertools
import json
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import patches
from matplotlib import dates as mdate
# My modules
import chart_tools  # noqa

LOG         = chart_tools.LOG
PAYLOAD     = chart_tools.payload
P_DICT      = PAYLOAD['p_dict']
K_DICT      = PAYLOAD['k_dict']
PLUG_DICT   = PAYLOAD['prefs']
PROPS       = PAYLOAD['props']
CHART_NAME  = PROPS['name']
LINE_COLORS = []

LOG['Threaddebug'].append("chart_line.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")

try:

    def __init__():
        ...

    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT)

    # ============================== Format X Ticks ===============================
    ax.tick_params(axis='x', **K_DICT['k_major_x'])
    ax.tick_params(axis='x', **K_DICT['k_minor_x'])
    ax.xaxis.set_major_formatter(mdate.DateFormatter(P_DICT['xAxisLabelFormat']))
    chart_tools.format_axis_x_scale(x_axis_bins=P_DICT['xAxisBins'], logger=LOG)

    # If the x-axis format has been set to None, let's hide the labels.
    if P_DICT['xAxisLabelFormat'] == "None":
        ax.axes.xaxis.set_ticklabels([])

    # =============================== Format Y Axis ===============================
    chart_tools.format_axis_y(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    for line in range(1, 9, 1):

        suppress_line = P_DICT.get(f'suppressLine{line}', False)

        # If the line is suppressed, remind the user they suppressed it.
        if suppress_line:
            LOG['Info'].append(
                f"[{CHART_NAME}] Line {line} is suppressed by user setting. You can re-enable it "
                f"in the device configuration menu."
            )

        # ============================== Plot the Lines ===============================
        # Plot the lines. If suppress_line is True, we skip it.
        if P_DICT[f'line{line}Source'] not in ("", "None") and not suppress_line:

            # If line color is the same as the background color, alert the user.
            if P_DICT[f'line{line}Color'] == P_DICT['backgroundColor'] and not suppress_line:
                LOG['Warning'].append(
                    f"[{CHART_NAME}] Area {line} color is the same as the background color (so "
                    f"you may not be able to see it)."
                )

            # Add line color to list for later use
            LINE_COLORS.append(P_DICT[f'line{line}Color'])

            data_path = PLUG_DICT['dataPath']
            line_source = P_DICT[f'line{line}Source']

            # ==============================  Get the Data  ===============================
            data_column = chart_tools.get_data(data_source=f'{data_path}{line_source}', logger=LOG)

            if PLUG_DICT['verboseLogging']:
                LOG['Threaddebug'].append(f"[{CHART_NAME}] Data for Line {line}: {data_column}")

            # Pull the headers
            P_DICT['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                P_DICT[f'x_obs{line}'].append(element[0])
                P_DICT[f'y_obs{line}'].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple binary
            # sources on the same chart.)
            if PROPS.get(f'line{line}adjuster', "") != "":
                temp_list = []
                for obs in P_DICT[f'y_obs{line}']:
                    expr = f"{obs}{PROPS[f'line{line}adjuster']}"
                    temp_list.append(chart_tools.eval_expr(expr=expr))
                P_DICT[f'y_obs{line}'] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = P_DICT[f'x_obs{line}']

            try:
                limit = float(PROPS['limitDataRangeLength'])
            except (ValueError, KeyError):
                limit = 0

            if limit > 0:
                y_obs = P_DICT[f'y_obs{line}']
                new_old = PROPS['limitDataRange']

                prune = chart_tools.prune_data(x_data=dates_to_plot,
                                               y_data=y_obs,
                                               limit=limit,
                                               new_old='None',
                                               logger=LOG
                                               )
                P_DICT[f'x_obs{line}'], P_DICT[f'y_obs{line}'] = prune

            # ======================== Convert Dates for Charting =========================
            P_DICT[f'x_obs{line}'] = chart_tools.format_dates(
                list_of_dates=P_DICT[f'x_obs{line}'], logger=LOG
            )

            # ===========================  Hide Anomalous Data  ===========================
            y_data = chart_tools.hide_anomalies(
                data=P_DICT[f'y_obs{line}'],
                props=PROPS,
                logger=LOG
            )

            ax.plot_date(
                P_DICT[f'x_obs{line}'],
                y_data,
                color=P_DICT[f'line{line}Color'],
                linestyle=P_DICT[f'line{line}Style'],
                marker=P_DICT[f'line{line}Marker'],
                markeredgecolor=P_DICT[f'line{line}MarkerColor'],
                markerfacecolor=P_DICT[f'line{line}MarkerColor'],
                zorder=10,
                **K_DICT['k_line']
            )

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{line}']]

            if P_DICT[f'line{line}Fill']:
                ax.fill_between(
                    P_DICT[f'x_obs{line}'],
                    0,
                    P_DICT[f'y_obs{line}'],
                    color=P_DICT[f'line{line}Color'],
                    **K_DICT['k_fill']
                )

            # ================================ Annotations ================================
            annotate = P_DICT[f'line{line}Annotate']
            precision = int(PROPS.get(f'line{line}AnnotationPrecision', "0"))
            if annotate:
                for xy in zip(P_DICT[f'x_obs{line}'], P_DICT[f'y_obs{line}']):
                    ax.annotate(
                        f"{float(xy[1]):.{precision}f}",
                        xy=xy,
                        xytext=(0, 0),
                        zorder=10,
                        **K_DICT['k_annotation']
                    )

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
        final_headers = []

        headers = P_DICT['headers']
        # headers = [_ for _ in P_DICT['headers']]
        # headers = [_.decode('utf-8') for _ in P_DICT['headers']]

        for header in headers:
            if P_DICT[f'line{counter}Legend'] == "":
                final_headers.append(header)
            else:
                final_headers.append(P_DICT[f'line{counter}Legend'])
            counter += 1

        # Set the legend
        # Reorder the headers and colors so that they fill by row instead of by column
        num_col = int(P_DICT['legendColumns'])
        iter_headers = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = list(iter_headers)

        iter_colors = itertools.chain(*[LINE_COLORS[i::num_col] for i in range(num_col)])
        final_colors = list(iter_colors)

        legend = ax.legend(
            final_headers,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.15),
            ncol=num_col,
            prop={'size': float(P_DICT['legendFontSize'])}
        )

        # Set legend font color
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]

        # Set legend line color
        num_handles = len(legend.legendHandles)
        _ = [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    for line in range(1, 9, 1):

        suppress_line = P_DICT.get(f'suppressLine{line}', False)

        if P_DICT[f'line{line}Source'] not in ("", "None") and not suppress_line:

            # Note that we do these after the legend is drawn so that these lines don't
            # affect the legend.

            # =============================== Best Fit Line ===============================
            if PROPS.get(f'line{line}BestFit', False):
                chart_tools.format_best_fit_line_segments(
                    ax=ax,
                    dates_to_plot=P_DICT[f'x_obs{line}'],
                    line=line,
                    p_dict=P_DICT,
                    logger=LOG
                )

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{line}']]

            # =============================== Fill Between ================================
            if P_DICT[f'line{line}Fill']:
                ax.fill_between(
                    P_DICT[f'x_obs{line}'],
                    0,
                    P_DICT[f'y_obs{line}'],
                    color=P_DICT[f'line{line}Color'],
                    **K_DICT['k_fill']
                )

            # =============================== Min/Max Lines ===============================
            if P_DICT[f'plotLine{line}Min']:
                ax.axhline(
                    y=min(P_DICT[f'y_obs{line}']),
                    color=P_DICT[f'line{line}Color'],
                    **K_DICT['k_min']
                )
            if P_DICT[f'plotLine{line}Max']:
                ax.axhline(
                    y=max(P_DICT[f'y_obs{line}']),
                    color=P_DICT[f'line{line}Color'],
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

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type} in {__file__.split('/')[-1]}")

json.dump(LOG, sys.stdout, indent=4)
