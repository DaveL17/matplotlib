# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the horizontal bar charts

All steps required to generate horizontal bar charts that use stock (time-agnostic) data.
"""

# Built-in Modules
import json
import itertools
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt  # noqa
from matplotlib import patches  # noqa
# My modules
import chart_tools  # noqa

LOG               = chart_tools.LOG
PAYLOAD           = chart_tools.payload
CHART_DATA        = PAYLOAD['data']
P_DICT            = PAYLOAD['p_dict']
K_DICT            = PAYLOAD['k_dict']
PROPS             = PAYLOAD['props']
CHART_NAME        = PROPS['name']
PLUG_DICT         = PAYLOAD['prefs']
ANNOTATION_VALUES = []
BAR_COLORS        = []
Y_LABELS          = []
Y_TICKS           = []

LOG['Threaddebug'].append("chart_bar_stock.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(PAYLOAD)

try:

    def __init__():
        """
        Title Placeholder

        Body placeholder
        :return:
        """

    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    ax.tick_params(axis='x', **K_DICT['k_major_x'])
    ax.tick_params(axis='x', **K_DICT['k_minor_x'])
    chart_tools.format_axis_y(ax=ax, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # ============================  Iterate the Bars  =============================
    for bar in CHART_DATA:
        b_num        = bar['number']
        color        = bar[f'color_{b_num}']
        suppress_bar = P_DICT.get(f'suppressBar{b_num}', False)
        Y_LABELS.append(bar[f'legend_{b_num}'])
        Y_TICKS.append(b_num)
        x_val = float(bar[f'val_{b_num}'])
        P_DICT['data_array'].append(x_val)
        BAR_COLORS.append(color)

        # ====================  Bar and Background Color the Same  ====================
        # If the bar color is the same as the background color, alert the user.
        if color == P_DICT['backgroundColor'] and not suppress_bar:
            LOG['Warning'].append(
                f"[{CHART_NAME}] Area {b_num} color is the same as the background color (so you "
                f"may not be able to see it)."
            )

        # =============================  Bar Suppressed  ==============================
        # If the bar is suppressed, remind the user they suppressed it.
        if suppress_bar:
            LOG['Info'].append(
                f"[{CHART_NAME}] Bar {b_num} is suppressed by user setting. You can  re-enable it "
                f"in the device configuration menu."
            )

        # ============================  Display Zero Bars  ============================
        # Early versions of matplotlib will truncate leading and trailing bars where the value is
        # zero. With this setting, we replace the Y values of zero with a very small positive value
        # (0 becomes 1e-06). We get a slice of the original data for annotations.
        # annotation_values.append(y_val)
        ANNOTATION_VALUES.append(bar[f'val_{b_num}'])
        if P_DICT.get('showZeroBars', False):
            if x_val == 0:
                x_val = 1e-06

        # ================================  Bar Width  ================================
        try:
            bar_width = float(P_DICT['barWidth'])
            if bar_width == 0:
                width = 0.8
            else:
                width = float(P_DICT['barWidth'])
        except ValueError:
            width = 0.8
            LOG['Warning'].append(
                f"[{CHART_NAME}] Problem setting bar width. Check value ({P_DICT['barWidth']})."
            )

        # ==============================  Plot the Bar  ===============================
        # Plot the bars. If 'suppressBar{thing} is True, we skip it.
        if not suppress_bar:
            ax.barh(
                b_num,
                width=x_val,
                height=float(P_DICT['barWidth']),
                color=color,
                align='center',
                edgecolor=color,
                **K_DICT['k_bar']
            )

        # ===============================  Annotations  ===============================
        # If annotations desired, plot those too.
        if bar[f'annotate_{b_num}'] and not suppress_bar:
            ax.annotate(
                ANNOTATION_VALUES[b_num - 1],
                xy=(x_val, b_num),
                xytext=(0, 0),
                zorder=10,
                **K_DICT['k_annotation']
            )

    # ===============================  Y Tick Bins  ===============================
    ax.set_yticks(Y_TICKS)
    ax.set_yticklabels(Y_LABELS)

    chart_tools.format_axis_x_min_max(p_dict=P_DICT, logger=LOG)
    chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # ===========================  Transparent Border  ============================
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
    # Legend should be plotted before any other lines are plotted (like averages or
    # custom line segments).
    if P_DICT['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []
        headers = [_ for _ in Y_LABELS]
        # headers = [_.decode('utf-8') for _ in Y_LABELS]
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

    chart_tools.format_custom_line_segments(
        ax=ax,
        plug_dict=PLUG_DICT,
        p_dict=P_DICT,
        k_dict=K_DICT,
        logger=LOG,
        orient="vert"
    )
    chart_tools.format_grids(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.98))
    chart_tools.format_axis_y_ticks(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y1_label(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    try:
        chart_tools.save(logger=LOG)

    except OverflowError as err:
        if "date value out of range" in traceback.format_exc(err):
            LOG['Critical'].append(
                f"[{PAYLOAD['props']['name']}] Chart not saved. Try enabling Display Zero Bars in "
                f"device settings."
            )

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
