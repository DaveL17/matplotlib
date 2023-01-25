# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the weather charts

Given the unique nature of weather chart construction, we have a separate method for these charts.
Note that it is not currently possible within the multiprocessing framework used to query the
Indigo server, so we need to send everything we need through the method call.
"""

# Built-in Modules
import json
import sys
import traceback
import datetime as dt
from copy import deepcopy
import numpy as np
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import patches

# My modules
import chart_tools  # noqa

LOG          = chart_tools.LOG
PAYLOAD      = chart_tools.payload
P_DICT       = PAYLOAD['p_dict']
K_DICT       = PAYLOAD['k_dict']
STATE_LIST   = PAYLOAD['state_list']
DEV_TYPE     = PAYLOAD['dev_type']
PROPS        = PAYLOAD['props']
CHART_NAME   = PROPS['name']
PLUG_DICT    = PAYLOAD['prefs']
SUN_RISE_SET = PAYLOAD['sun_rise_set']

LOG['Threaddebug'].append("chart_weather_forecast.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")

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

    dates_to_plot = P_DICT['dates_to_plot']

    for line in range(1, 4, 1):

        if P_DICT[f'line{line}Color'] == P_DICT['backgroundColor']:
            LOG['Debug'].append(
                f"[{CHART_NAME}] A line color is the same as the background color (so you will not "
                f"be able to see it)."
            )

    # ========================== Fantastic Hourly Device ==========================
    if DEV_TYPE == 'Hourly':

        for counter in range(1, 25, 1):
            if counter < 10:
                counter = f'0{counter}'

            epoch = STATE_LIST[f'h{counter}_epoch']
            time_stamp = dt.datetime.fromtimestamp(epoch)
            time_stamp = dt.datetime.strftime(time_stamp, "%Y-%m-%d %H:%M")
            P_DICT['x_obs1'].append(time_stamp)

            P_DICT['y_obs1'].append(STATE_LIST[f'h{counter}_temperature'])
            P_DICT['y_obs3'].append(STATE_LIST[f'h{counter}_precipChance'])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=P_DICT['x_obs1'], logger=LOG)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust
            # slightly if that's the case.
            if set(P_DICT['y_obs3']) == {0.0}:
                P_DICT['y_obs3'][0] = 1.0

            # Note that the trailing comma is required to ensure
            P_DICT['headers_1'] = ('Temperature',)
            # that Matplotlib interprets the legend as a tuple.
            P_DICT['headers_2'] = ('Precipitation',)

    # ======================== WUnderground Hourly Device =========================
    elif DEV_TYPE == 'wundergroundHourly':

        for counter in range(1, 25, 1):
            if counter < 10:
                counter = f'0{counter}'
            P_DICT['x_obs1'].append(STATE_LIST[f'h{counter}_timeLong'])
            P_DICT['y_obs1'].append(STATE_LIST[f'h{counter}_temp'])
            P_DICT['y_obs3'].append(STATE_LIST[f'h{counter}_precip'])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=P_DICT['x_obs1'], logger=LOG)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust
            # slightly if that's the case.
            if set(P_DICT['y_obs3']) == {0.0}:
                P_DICT['y_obs3'][0] = 1.0

            # Note that the trailing comma is required to ensure that Matplotlib interprets the
            # legend as a tuple.
            P_DICT['headers_1'] = ('Temperature',)
            P_DICT['headers_2'] = ('Precipitation',)

    # ========================== Fantastic Daily Device ===========================
    elif DEV_TYPE == 'Daily':

        for counter in range(1, 9, 1):
            if counter < 10:
                counter = f'0{counter}'
            P_DICT['x_obs1'].append(STATE_LIST[f'd{counter}_date'])
            P_DICT['y_obs1'].append(STATE_LIST[f'd{counter}_temperatureHigh'])
            P_DICT['y_obs2'].append(STATE_LIST[f'd{counter}_temperatureLow'])
            P_DICT['y_obs3'].append(STATE_LIST[f'd{counter}_precipChance'])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=P_DICT['x_obs1'], logger=LOG)

            # Note that bar plots behave strangely if all the y obs are zero. We need to adjust
            # slightly if that's the case.
            if set(P_DICT['y_obs3']) == {0.0}:
                P_DICT['y_obs3'][0] = 100.0

            P_DICT['headers_1'] = ('High Temperature', 'Low Temperature',)
            P_DICT['headers_2'] = ('Precipitation',)

    # ======================== WUnderground Ten Day Device ========================
    elif DEV_TYPE == 'wundergroundTenDay':

        for counter in range(1, 11, 1):
            if counter < 10:
                counter = f'0{counter}'

            P_DICT['x_obs1'].append(STATE_LIST[f'd{counter}_date'])
            P_DICT['y_obs1'].append(STATE_LIST[f'd{counter}_high'])
            P_DICT['y_obs2'].append(STATE_LIST[f'd{counter}_low'])
            P_DICT['y_obs3'].append(STATE_LIST[f'd{counter}_pop'])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=P_DICT['x_obs1'], logger=LOG)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust
            # slightly if that's the case.
            if set(P_DICT['y_obs3']) == {0.0}:
                P_DICT['y_obs3'][0] = 1.0

            P_DICT['headers_1'] = ('High Temperature', 'Low Temperature',)
            P_DICT['headers_2'] = ('Precipitation',)

    else:
        LOG['Warning'].append(
            f"[{CHART_NAME}] This device type only supports Fantastic Weather (v0.1.05 or later) "
            f"and WUnderground forecast devices."
        )

    if PLUG_DICT['verboseLogging']:
        LOG['Threaddebug'].append(f"[{CHART_NAME}] p_dict: {P_DICT}")

    ax1 = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT)
    chart_tools.format_axis_x_ticks(ax=ax1, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y(ax=ax1, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # ============================ Precipitation Bars =============================
    # The width of the bars is a percentage of a day, so we need to account for instances where the
    # unit of time could be hours to months or years.

    # Plot precipitation bars
    if P_DICT['y_obs3']:
        if len(dates_to_plot) <= 15:
            ax1.bar(
                dates_to_plot,
                P_DICT['y_obs3'],
                align='center',
                color=P_DICT['line3Color'],
                width=((1.0 / len(dates_to_plot)) * 5),
                zorder=10
            )
        else:
            ax1.bar(
                dates_to_plot,
                P_DICT['y_obs3'],
                align='center',
                color=P_DICT['line3Color'],
                width=(1.0 / (len(dates_to_plot) * 1.75)),
                zorder=10
            )

        # Precipitation bar annotations
        annotate = P_DICT['line3Annotate']
        precision = int(PROPS.get(f'line{line}AnnotationPrecision', "0"))
        if annotate:
            for xy in zip(dates_to_plot, P_DICT['y_obs3']):
                ax1.annotate(
                    f'{xy[1]:.{precision}f}',
                    xy=(xy[0], 5),
                    xytext=(0, 0),
                    zorder=10,
                    **K_DICT['k_annotation']
                )

    # ============================== Precip Min/Max ===============================
    if P_DICT['y2AxisMin'] != 'None' and P_DICT['y2AxisMax'] != 'None':
        y2_axis_min = float(P_DICT['y2AxisMin'])
        y2_axis_max = float(P_DICT['y2AxisMax'])

    elif P_DICT['y2AxisMin'] != 'None' and P_DICT['y2AxisMax'] == 'None':
        y2_axis_min = float(P_DICT['y2AxisMin'])
        y2_axis_max = max(P_DICT['y_obs3'])

    elif P_DICT['y2AxisMin'] == 'None' and P_DICT['y2AxisMax'] != 'None':
        y2_axis_min = 0
        y2_axis_max = float(P_DICT['y2AxisMax'])

    else:
        if max(P_DICT['y_obs3']) - min(P_DICT['y_obs3']) == 0:
            y2_axis_min = 0
            y2_axis_max = 1

        elif max(P_DICT['y_obs3']) != 0 and \
                min(P_DICT['y_obs3']) != 0 and \
                0 < max(P_DICT['y_obs3']) - min(P_DICT['y_obs3']) <= 1:

            y2_axis_min = min(P_DICT['y_obs3']) * (1 - (1 / min(P_DICT['y_obs3']) ** 1.25))
            y2_axis_max = max(P_DICT['y_obs3']) * (1 + (1 / max(P_DICT['y_obs3']) ** 1.25))

        else:
            if min(P_DICT['y_obs3']) < 0:
                y2_axis_min = min(P_DICT['y_obs3']) * 1.5
            else:
                y2_axis_min = min(P_DICT['y_obs3']) * 0.75
            if max(P_DICT['y_obs3']) < 0:
                y2_axis_max = 0
            else:
                y2_axis_max = max(P_DICT['y_obs3']) * 1.10

    plt.ylim(ymin=y2_axis_min, ymax=y2_axis_max)

    # =============================== X1 Axis Label ===============================
    chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # =============================== Y1 Axis Label ===============================
    # Note we're plotting Y2 label on ax1. We do this because we want the precipitation bars to be
    # under the temperature plot, but we want the precipitation scale to be on the right side.
    plt.ylabel(P_DICT['customAxisLabelY2'], **K_DICT['k_y_axis_font'])
    ax1.yaxis.set_label_position('right')

    # ============================= Legend Properties =============================
    # (note that we need a separate instance of this code for each subplot. This one controls the
    # precipitation subplot.) Legend should be plotted before any other lines are plotted (like
    # averages or custom line segments).

    if P_DICT['showLegend']:
        headers = list(P_DICT['headers_2'])
        legend = ax1.legend(
            headers,
            loc='upper right',
            bbox_to_anchor=(1.0, -0.15),
            ncol=1,
            prop={'size': float(P_DICT['legendFontSize'])}
        )
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]
        frame = legend.get_frame()
        frame.set_alpha(0)  # Note: frame alpha should be an int and not a string.

    chart_tools.format_grids(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # ========================== Transparent Charts Fill ==========================
    if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
        ax1.add_patch(
            patches.Rectangle(
                (0, 0),
                1,
                1,
                transform=ax1.transAxes,
                facecolor=P_DICT['faceColor'],
                zorder=1
            )
        )

    # ============================= Sunrise / Sunset ==============================
    # Note that this highlights daytime hours on the chart.
    daylight = PROPS.get('showDaytime', True)

    if daylight and DEV_TYPE in ('Hourly', 'wundergroundHourly'):

        sun_rise, sun_set = chart_tools.format_dates(list_of_dates=SUN_RISE_SET, logger=LOG)

        min_dates_to_plot = np.amin(dates_to_plot)
        max_dates_to_plot = np.amax(dates_to_plot)

        # We will only highlight daytime if the current values for sunrise and sunset fall within
        # the limits of dates_to_plot. We add and subtract one second for each to account for
        # microsecond rounding.
        if (min_dates_to_plot - 1) < sun_rise < (max_dates_to_plot + 1) and \
                (min_dates_to_plot - 1) < sun_set < (max_dates_to_plot + 1):

            # If sunrise is less than sunset, they are on the same day, so we fill in between the
            # two.
            if sun_rise < sun_set:
                ax1.axvspan(sun_rise, sun_set, color=P_DICT['daytimeColor'], alpha=0.15, zorder=1)

            # If sunrise is greater than sunset, the next sunrise is tomorrow
            else:
                ax1.axvspan(
                    min_dates_to_plot,
                    sun_set,
                    color=P_DICT['daytimeColor'],
                    alpha=0.15,
                    zorder=1
                )
                ax1.axvspan(
                    sun_rise,
                    max_dates_to_plot,
                    color=P_DICT['daytimeColor'],
                    alpha=0.15,
                    zorder=1
                )

    # ==================================== AX2 ====================================

    # ============================= Temperatures Plot =============================
    # Create a second plot area and plot the temperatures.
    ax2 = ax1.twinx()
    # This needs to remain or the margins get screwy (they don't carry over from ax1).
    ax2.margins(0.04, 0.05)

    for line in range(1, 3, 1):
        if P_DICT[f'y_obs{line}']:
            ax2.plot(
                dates_to_plot,
                P_DICT[f'y_obs{line}'],
                color=P_DICT[f'line{line}Color'],
                linestyle=P_DICT[f'line{line}Style'],
                marker=P_DICT[f'line{line}Marker'],\
                markerfacecolor=P_DICT[f'line{line}MarkerColor'],
                zorder=(10 - line),
                **K_DICT['k_line']
            )

            _ = [P_DICT['data_array'].append(node) for node in P_DICT[f'y_obs{line}']]

            annotate = P_DICT[f'line{line}Annotate']
            precision = int(PROPS.get(f'line{line}AnnotationPrecision', "0"))
            if annotate:
                for xy in zip(dates_to_plot, P_DICT[f'y_obs{line}']):
                    ax2.annotate(
                        f'{xy[1]:.{precision}f}',
                        xy=xy,
                        xytext=(0, 0),
                        zorder=(11 - line),
                        **K_DICT['k_annotation']
                    )

    # Take a snapshot of the data for some computations below (P_DICT['data_array'] can be modified
    # elsewhere.
    just_the_data = deepcopy(P_DICT['data_array'])

    chart_tools.format_axis_x_ticks(ax=ax2, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_axis_y(ax=ax2, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
    chart_tools.format_custom_line_segments(
        ax=ax2,
        plug_dict=PLUG_DICT,
        p_dict=P_DICT,
        k_dict=K_DICT,
        logger=LOG
    )

    plt.autoscale(enable=True, axis='x', tight=None)

    # Note that we plot the bar plot so that it will be under the line plot, but we still want the
    # temperature scale on the left and the percentages on the right.
    ax1.yaxis.tick_right()
    ax2.yaxis.tick_left()

    # ========================= Temperature Axis Min/Max ==========================
    if P_DICT['yAxisMin'] != 'None' and P_DICT['yAxisMax'] != 'None':
        y_axis_min = float(P_DICT['yAxisMin'])
        y_axis_max = float(P_DICT['yAxisMax'])

    elif P_DICT['yAxisMin'] != 'None' and P_DICT['yAxisMax'] == 'None':
        y_axis_min = float(P_DICT['yAxisMin'])
        y_axis_max = max(just_the_data)

    elif P_DICT['yAxisMin'] == 'None' and P_DICT['yAxisMax'] != 'None':
        y_axis_min = min(just_the_data)
        y_axis_max = float(P_DICT['yAxisMax'])

    else:
        if max(just_the_data) - min(just_the_data) == 0:
            y_axis_min = 0
            y_axis_max = 1

        elif max(just_the_data) != 0 and \
                min(just_the_data) != 0 and \
                0 < max(just_the_data) - min(just_the_data) <= 1:
            y_axis_min = min(just_the_data) * (1 - (1 / abs(min(just_the_data)) ** 1.25))
            y_axis_max = max(just_the_data) * (1 + (1 / abs(max(just_the_data)) ** 1.25))

        else:
            if min(just_the_data) < 0:
                y_axis_min = min(just_the_data) * 1.5
            else:
                y_axis_min = min(just_the_data) * 0.75
            if max(just_the_data) < 0:
                y_axis_max = 0
            else:
                y_axis_max = max(just_the_data) * 1.10
    plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

    # =============================== Y2 Axis Label ===============================
    # Note we're plotting Y1 label on ax2. We do this because we want the temperature lines to be
    # over the precipitation bars, but we want the temperature scale to be on the left side.

    # Note we're plotting Y1 label on ax2
    plt.ylabel(P_DICT['customAxisLabelY'], **K_DICT['k_y_axis_font'])
    ax2.yaxis.set_label_position('left')

    # ============================= Legend Properties =============================
    # (note that we need a separate instance of this code for each subplot. This one controls the
    # Temperatures subplot.) Legend should be plotted before any other lines are plotted (like
    # averages or custom line segments).

    if P_DICT['showLegend']:
        headers = list(P_DICT['headers_1'])
        legend = ax2.legend(
            headers,
            loc='upper left',
            bbox_to_anchor=(0.0, -0.15),
            ncol=2,
            prop={'size': float(P_DICT['legendFontSize'])}
        )
        _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]
        frame = legend.get_frame()
        frame.set_alpha(0)

    # We are setting these values here in a special way because it's apparently the only way to
    # overcome twinx.
    for tick in ax1.yaxis.get_major_ticks():
        tick.label1.set_fontname(PLUG_DICT['fontMain'])
        tick.label2.set_fontname(PLUG_DICT['fontMain'])
        tick.label1.set_fontsize(PLUG_DICT['tickFontSize'])
        tick.label2.set_fontsize(PLUG_DICT['tickFontSize'])
    for tick in ax2.yaxis.get_major_ticks():
        tick.label1.set_fontname(PLUG_DICT['fontMain'])
        tick.label2.set_fontname(PLUG_DICT['fontMain'])
        tick.label1.set_fontsize(PLUG_DICT['tickFontSize'])
        tick.label2.set_fontsize(PLUG_DICT['tickFontSize'])

    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.98))
    chart_tools.format_grids(p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

    # With the upgrade to matplotlib 3.5.1, tick labels were automatically being assigned to `ax`
    # (even though 'ax' is not overtly referenced). Therefore, we set them to an empty list to
    # suppress them.
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax1.tick_params(which='minor', bottom=False)

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
