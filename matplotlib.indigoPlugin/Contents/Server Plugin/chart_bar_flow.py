# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the flow bar charts

All steps required to generate bar charts that use flow (time-series) data.
"""

# Built-in Modules
import itertools
import json
import sys
import traceback
# Third-party Modules
import numpy as np
from matplotlib import pyplot as plt
from matplotlib import patches
# My modules
import chart_tools  # noqa

LOG        = chart_tools.LOG
PAYLOAD    = chart_tools.payload
P_DICT     = PAYLOAD['p_dict']
K_DICT     = PAYLOAD['k_dict']
PROPS      = PAYLOAD['props']
CHART_NAME = PROPS['name']
PLUG_DICT  = PAYLOAD['prefs']
BAR_COLORS = []
DATES_TO_DICT = []
X_TICKS = []

LOG['Threaddebug'].append("chart_bar_flow.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(PAYLOAD)

try:

    def __init__():
        pass

    num_obs = P_DICT['numObs']

    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    chart_tools.format_axis_y(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    for thing in range(1, 5, 1):

        suppress_bar = P_DICT.get(f'suppressBar{thing}', False)

        # p_dict[f"bar{thing}Color"] = chart_tools.fix_rgb(p_dict[f"bar{thing}Color"])

        # If the bar is suppressed, remind the user they suppressed it.
        if suppress_bar:
            LOG['Info'].append(
                f"[{CHART_NAME}] Bar {thing} is suppressed by user setting. You can re-enable it "
                f"in the device configuration menu."
            )

        # Plot the bars. If 'suppressBar{thing} is True, we skip it.
        if P_DICT[f'bar{thing}Source'] not in ("", "None") and not suppress_bar:

            # If the bar color is the same as the background color, alert the user.
            if P_DICT[f'bar{thing}Color'] == P_DICT['backgroundColor'] and not suppress_bar:
                LOG['Warning'].append(
                    f"[{CHART_NAME}] Bar {thing} color is the same as the background color (so "
                    f"you may not be able to see it)."
                )

            # Add bar color to list for later use
            BAR_COLORS.append(P_DICT[f'bar{thing}Color'])

            # Get the data and grab the header.
            dc = f"{PLUG_DICT['dataPath']}{P_DICT[f'bar{thing}Source']}"

            data_column = chart_tools.get_data(data_source=dc, logger=LOG)

            if PLUG_DICT['verboseLogging']:
                LOG['Threaddebug'].append(f"Data for bar {thing}: {data_column}")

            # Pull the headers
            P_DICT['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                P_DICT[f'x_obs{thing}'].append(element[0])
                P_DICT[f'y_obs{thing}'].append(float(element[1]))

            # ================================ Prune Data =================================
            # Prune the data if warranted
            DATES_TO_DICT = P_DICT[f'x_obs{thing}']

            # Get limit -- if blank or none then zero limit.
            try:
                limit = float(PROPS['limitDataRangeLength'])
            except ValueError:
                limit = 0

            y_obs   = P_DICT[f'y_obs{thing}']
            new_old = PROPS['limitDataRange']
            if limit > 0:
                dtp = chart_tools.prune_data(
                    x_data=DATES_TO_DICT,
                    y_data=y_obs,
                    limit=limit,
                    new_old=new_old,
                    logger=LOG
                )
                DATES_TO_DICT, y_obs = dtp

            # Convert the date strings for charting.
            DATES_TO_DICT = chart_tools.format_dates(list_of_dates=DATES_TO_DICT, logger=LOG)

            # If the user sets the width to 0, this will perform an introspection of the dates to
            # plot and get the minimum of the difference between the dates.
            try:
                if float(P_DICT['barWidth']) == 0.0:
                    width = np.min(np.diff(DATES_TO_DICT)) * 0.8
                else:
                    width = float(P_DICT['barWidth'])
            except ValueError as sub_error:
                width = 0.8

            # Early versions of matplotlib will truncate leading and trailing bars where the value
            # is zero. With this setting, we replace the Y values of zero with a very small positive
            # value (0 becomes 1e-06). We get a slice of the original data for annotations.
            annotation_values = y_obs[:]
            if P_DICT.get('showZeroBars', False):
                y_obs[num_obs * -1:] = [1e-06 if _ == 0 else _ for _ in y_obs[num_obs * -1:]]

            # Plot the bar. Note: hatching is not supported in the PNG backend.
            ax.bar(
                DATES_TO_DICT[num_obs * -1:],
                y_obs[num_obs * -1:],
                align='center',
                width=width,
                color=P_DICT[f'bar{thing}Color'],
                edgecolor=P_DICT[f'bar{thing}Color'],
                **K_DICT['k_bar']
            )

            _ = [P_DICT['data_array'].append(node) for node in y_obs[num_obs * -1:]]

            # If annotations desired, plot those too.
            if P_DICT[f'bar{thing}Annotate']:
                for xy in zip(DATES_TO_DICT, annotation_values):
                    ax.annotate(
                        xy[1],
                        xy=xy,
                        xytext=(0, 0),
                        zorder=10,
                        **K_DICT['k_annotation']
                    )

    chart_tools.format_axis_x_ticks(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y1_min_max(p_dict=P_DICT, logger=LOG)
    chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y1_label(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # Add a patch so that we can have transparent charts but a filled plot area.
    if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
        ax.add_patch(
            patches.Rectangle((0, 0), 1, 1,
                              transform=ax.transAxes,
                              facecolor=P_DICT['faceColor'],
                              zorder=1
                              )
        )

    # ============================= Legend Properties =============================
    # Legend should be plotted before any other lines are plotted (like averages or custom line
    # segments).

    if P_DICT['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []
        headers = [_ for _ in P_DICT['headers']]
        # headers = [_.decode('utf-8') for _ in P_DICT['headers']]
        for header in headers:
            if P_DICT[f'bar{counter}Legend'] == "":
                final_headers.append(header)
            else:
                final_headers.append(P_DICT[f'bar{counter}Legend'])
            counter += 1

        # Set the legend
        # Reorder the headers so that they fill by row instead of by column
        num_col = int(P_DICT['legendColumns'])
        iter_headers   = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = list(iter_headers)

        iter_colors  = itertools.chain(*[BAR_COLORS[i::num_col] for i in range(num_col)])
        final_colors = list(iter_colors)

        legend = ax.legend(
            final_headers,
            loc='upper center',
            bbox_to_anchor=(0.5, -0.15),
            ncol=int(P_DICT['legendColumns']),
            prop={'size': float(P_DICT['legendFontSize'])}
        )

        # Set legend font color
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]

        # Set legend bar colors
        num_handles = len(legend.legendHandles)
        _ = [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    # =============================== Min/Max Lines ===============================
    # Note that these need to be plotted after the legend is established, otherwise some
    # characteristics of the min/max lines will take over the legend props.
    for thing in range(1, 5, 1):
        if P_DICT[f'plotBar{thing}Min']:
            ax.axhline(
                y=min(y_obs[num_obs * -1:]),
                color=P_DICT[f'bar{thing}Color'],
                **K_DICT['k_min']
            )
        if P_DICT[f'plotBar{thing}Max']:
            ax.axhline(
                y=max(y_obs[num_obs * -1:]),
                color=P_DICT[f'bar{thing}Color'],
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
    chart_tools.format_axis_y_ticks(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
