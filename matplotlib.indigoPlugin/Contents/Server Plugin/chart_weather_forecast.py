#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the weather charts
Given the unique nature of weather chart construction, we have a separate
method for these charts. Note that it is not currently possible within the
multiprocessing framework used to query the indigo server, so we need to
send everything we need through the method call.
-----

"""

# Built-in Modules
import datetime as dt
import numpy as np
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
state_list   = payload['state_list']
dev_type     = payload['dev_type']
props        = payload['props']
chart_name   = props['name']
plug_dict    = payload['prefs']
sun_rise_set = payload['sun_rise_set']

log['Threaddebug'].append(u"chart_weather_forecast.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass

    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    dates_to_plot = p_dict['dates_to_plot']

    for line in range(1, 4, 1):

        if p_dict['line{i}Color'.format(i=line)] == p_dict['backgroundColor']:
            chart_tools.log['Debug'].append(u"[{name}] A line color is the same as the background color (so you will "
                                            u"not be able to see it).".format(name=chart_name))

    # ========================== Fantastic Hourly Device ==========================
    if dev_type == 'Hourly':

        for counter in range(1, 25, 1):
            if counter < 10:
                counter = '0{c}'.format(c=counter)

            epoch = state_list['h{c}_epoch'.format(c=counter)]
            time_stamp = dt.datetime.fromtimestamp(epoch)
            time_stamp = dt.datetime.strftime(time_stamp, "%Y-%m-%d %H:%M")
            p_dict['x_obs1'].append(time_stamp)

            p_dict['y_obs1'].append(state_list['h{c}_temperature'.format(c=counter)])
            p_dict['y_obs3'].append(state_list['h{c}_precipChance'.format(c=counter)])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=p_dict['x_obs1'], logger=log)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly
            # if that's the case.
            if set(p_dict['y_obs3']) == {0.0}:
                p_dict['y_obs3'][0] = 1.0

            p_dict['headers_1']    = ('Temperature',)  # Note that the trailing comma is required to ensure
            # that Matplotlib interprets the legend as a tuple.
            p_dict['headers_2']    = ('Precipitation',)

    # ======================== WUnderground Hourly Device =========================
    elif dev_type == 'wundergroundHourly':

        for counter in range(1, 25, 1):
            if counter < 10:
                counter = '0{c}'.format(c=counter)
            p_dict['x_obs1'].append(state_list['h{c}_timeLong'.format(c=counter)])
            p_dict['y_obs1'].append(state_list['h{t}_temp'.format(t=counter)])
            p_dict['y_obs3'].append(state_list['h{pr}_precip'.format(pr=counter)])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=p_dict['x_obs1'], logger=log)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to
            # adjust slightly if that's the case.
            if set(p_dict['y_obs3']) == {0.0}:
                p_dict['y_obs3'][0] = 1.0

            # Note that the trailing comma is required to ensure that Matplotlib interprets
            # the legend as a tuple.
            p_dict['headers_1']    = ('Temperature',)
            p_dict['headers_2']    = ('Precipitation',)

    # ========================== Fantastic Daily Device ===========================
    elif dev_type == 'Daily':

        for counter in range(1, 9, 1):
            if counter < 10:
                counter = '0{c}'.format(c=counter)
            p_dict['x_obs1'].append(state_list['d{c}_date'.format(c=counter)])
            p_dict['y_obs1'].append(state_list['d{c}_temperatureHigh'.format(c=counter)])
            p_dict['y_obs2'].append(state_list['d{c}_temperatureLow'.format(c=counter)])
            p_dict['y_obs3'].append(state_list['d{c}_precipChance'.format(c=counter)])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=p_dict['x_obs1'], logger=log)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if
            # that's the case.
            if set(p_dict['y_obs3']) == {0.0}:
                p_dict['y_obs3'][0] = 1.0

            p_dict['headers_1']    = ('High Temperature', 'Low Temperature',)
            p_dict['headers_2']    = ('Precipitation',)

    # ======================== WUnderground Ten Day Device ========================
    elif dev_type == 'wundergroundTenDay':

        for counter in range(1, 11, 1):
            if counter < 10:
                counter = '0{c}'.format(c=counter)
            p_dict['x_obs1'].append(state_list['d{c}_date'.format(c=counter)])
            p_dict['y_obs1'].append(state_list['d{c}_high'.format(c=counter)])
            p_dict['y_obs2'].append(state_list['d{c}_low'.format(c=counter)])
            p_dict['y_obs3'].append(state_list['d{c}_pop'.format(c=counter)])

            # Convert the date strings for charting.
            dates_to_plot = chart_tools.format_dates(list_of_dates=p_dict['x_obs1'], logger=log)

            # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if
            # that's the case.
            if set(p_dict['y_obs3']) == {0.0}:
                p_dict['y_obs3'][0] = 1.0

            p_dict['headers_1']    = ('High Temperature', 'Low Temperature',)
            p_dict['headers_2']    = ('Precipitation',)

    else:
        chart_tools.log['Warning'].append(u"[{n}] This device type only supports Fantastic Weather (v0.1.05 or later) "
                                          u"and WUnderground forecast devices.".format(n=chart_name))

    if plug_dict['verboseLogging']:
        chart_tools.log['Threaddebug'].append(u"[{n}] p_dict: {p}".format(n=chart_name, p=p_dict))

    ax1 = chart_tools.make_chart_figure(width=p_dict['chart_width'],
                                        height=p_dict['chart_height'],
                                        p_dict=p_dict
                                        )
    chart_tools.format_axis_x_ticks(ax=ax1, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax1, p_dict=p_dict, k_dict=k_dict, logger=log)

    # ============================ Precipitation Bars =============================
    # The width of the bars is a percentage of a day, so we need to account for
    # instances where the unit of time could be hours to months or years.

    # Plot precipitation bars
    if p_dict['y_obs3']:
        if len(dates_to_plot) <= 15:
            ax1.bar(dates_to_plot,
                    p_dict['y_obs3'],
                    align='center',
                    color=p_dict['line3Color'],
                    width=((1.0 / len(dates_to_plot)) * 5),
                    zorder=10
                    )
        else:
            ax1.bar(dates_to_plot,
                    p_dict['y_obs3'],
                    align='center',
                    color=p_dict['line3Color'],
                    width=(1.0 / (len(dates_to_plot) * 1.75)),
                    zorder=10
                    )

        # Precipitation bar annotations
        if p_dict['line3Annotate']:
            for xy in zip(dates_to_plot, p_dict['y_obs3']):
                ax1.annotate('%.0f' % xy[1],
                             xy=(xy[0], 5),
                             xytext=(0, 0),
                             zorder=10,
                             **k_dict['k_annotation']
                             )

    # ============================== Precip Min/Max ===============================
    if p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] != 'None':
        y2_axis_min = float(p_dict['y2AxisMin'])
        y2_axis_max = float(p_dict['y2AxisMax'])

    elif p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] == 'None':
        y2_axis_min = float(p_dict['y2AxisMin'])
        y2_axis_max = max(p_dict['y_obs3'])

    elif p_dict['y2AxisMin'] == 'None' and p_dict['y2AxisMax'] != 'None':
        y2_axis_min = 0
        y2_axis_max = float(p_dict['y2AxisMax'])

    else:
        if max(p_dict['y_obs3']) - min(p_dict['y_obs3']) == 0:
            y2_axis_min = 0
            y2_axis_max = 1

        elif max(p_dict['y_obs3']) != 0 and \
                min(p_dict['y_obs3']) != 0 and \
                0 < max(p_dict['y_obs3']) - min(p_dict['y_obs3']) <= 1:

            y2_axis_min = min(p_dict['y_obs3']) * (1 - (1 / min(p_dict['y_obs3']) ** 1.25))
            y2_axis_max = max(p_dict['y_obs3']) * (1 + (1 / max(p_dict['y_obs3']) ** 1.25))

        else:
            if min(p_dict['y_obs3']) < 0:
                y2_axis_min = min(p_dict['y_obs3']) * 1.5
            else:
                y2_axis_min = min(p_dict['y_obs3']) * 0.75
            if max(p_dict['y_obs3']) < 0:
                y2_axis_max = 0
            else:
                y2_axis_max = max(p_dict['y_obs3']) * 1.10

    plt.ylim(ymin=y2_axis_min, ymax=y2_axis_max)

    # =============================== X1 Axis Label ===============================
    chart_tools.format_axis_x_label(dev=props, p_dict=p_dict, k_dict=k_dict, logger=log)

    # =============================== Y1 Axis Label ===============================
    # Note we're plotting Y2 label on ax1. We do this because we want the
    # precipitation bars to be under the temperature plot but we want the
    # precipitation scale to be on the right side.
    plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])
    ax1.yaxis.set_label_position('right')

    # ============================= Legend Properties =============================
    # (note that we need a separate instance of this code for each subplot. This
    # one controls the precipitation subplot.) Legend should be plotted before any
    # other lines are plotted (like averages or custom line segments).

    if p_dict['showLegend']:
        headers = [_.decode('utf-8') for _ in p_dict['headers_2']]
        legend = ax1.legend(headers,
                            loc='upper right',
                            bbox_to_anchor=(1.0, -0.15),
                            ncol=1,
                            prop={'size': float(p_dict['legendFontSize'])}
                            )
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
        frame = legend.get_frame()
        frame.set_alpha(0)  # Note: frame alpha should be an int and not a string.

    chart_tools.format_grids(p_dict=p_dict, k_dict=k_dict, logger=log)

    # ========================== Transparent Charts Fill ==========================
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax1.add_patch(patches.Rectangle((0, 0),
                                        1,
                                        1,
                                        transform=ax1.transAxes,
                                        facecolor=p_dict['faceColor'],
                                        zorder=1
                                        )
                      )

    # ============================= Sunrise / Sunset ==============================
    # Note that this highlights daytime hours on the chart.

    daylight = props.get('showDaytime', True)

    if daylight and dev_type in ('Hourly', 'wundergroundHourly'):

        sun_rise, sun_set = chart_tools.format_dates(list_of_dates=sun_rise_set, logger=log)

        min_dates_to_plot = np.amin(dates_to_plot)
        max_dates_to_plot = np.amax(dates_to_plot)

        # We will only highlight daytime if the current values for sunrise and sunset
        # fall within the limits of dates_to_plot. We add and subtract one second for
        # each to account for microsecond rounding.
        if (min_dates_to_plot - 1) < sun_rise < (max_dates_to_plot + 1) and \
                (min_dates_to_plot - 1) < sun_set < (max_dates_to_plot + 1):

            # If sunrise is less than sunset, they are on the same day so we fill in
            # between the two.
            if sun_rise < sun_set:
                ax1.axvspan(sun_rise, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

            # If sunrise is greater than sunset, the next sunrise is tomorrow
            else:
                ax1.axvspan(min_dates_to_plot, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)
                ax1.axvspan(sun_rise, max_dates_to_plot, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

    # ==================================== AX2 ====================================

    # ============================= Temperatures Plot =============================
    # Create a second plot area and plot the temperatures.
    ax2 = ax1.twinx()
    ax2.margins(0.04, 0.05)  # This needs to remain or the margins get screwy (they don't carry over from ax1).

    for line in range(1, 3, 1):
        if p_dict['y_obs{i}'.format(i=line)]:
            ax2.plot(dates_to_plot,
                     p_dict['y_obs{i}'.format(i=line)],
                     color=p_dict['line{i}Color'.format(i=line)],
                     linestyle=p_dict['line{i}Style'.format(i=line)],
                     marker=p_dict['line{i}Marker'.format(i=line)],
                     markerfacecolor=p_dict['line{i}MarkerColor'.format(i=line)],
                     zorder=(10 - line),
                     **k_dict['k_line']
                     )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{i}'.format(i=line)]]

            if p_dict['line{i}Annotate'.format(i=line)]:
                for xy in zip(dates_to_plot, p_dict['y_obs{i}'.format(i=line)]):
                    ax2.annotate('%.0f' % xy[1],
                                 xy=xy,
                                 xytext=(0, 0),
                                 zorder=(11 - line),
                                 **k_dict['k_annotation']
                                 )

    chart_tools.format_axis_x_ticks(ax=ax2, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_axis_y(ax=ax2, p_dict=p_dict, k_dict=k_dict, logger=log)
    chart_tools.format_custom_line_segments(ax=ax2,
                                            plug_dict=plug_dict,
                                            p_dict=p_dict,
                                            k_dict=k_dict,
                                            logger=log
                                            )

    plt.autoscale(enable=True, axis='x', tight=None)

    # Note that we plot the bar plot so that it will be under the line plot, but we
    # still want the temperature scale on the left and the percentages on the
    # right.
    ax1.yaxis.tick_right()
    ax2.yaxis.tick_left()

    # ========================= Temperature Axis Min/Max ==========================
    if p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] != 'None':
        y_axis_min = float(p_dict['yAxisMin'])
        y_axis_max = float(p_dict['yAxisMax'])

    elif p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] == 'None':
        y_axis_min = float(p_dict['yAxisMin'])
        y_axis_max = max(p_dict['data_array'])

    elif p_dict['yAxisMin'] == 'None' and p_dict['yAxisMax'] != 'None':
        y_axis_min = min(p_dict['data_array'])
        y_axis_max = float(p_dict['yAxisMax'])

    else:
        if max(p_dict['data_array']) - min(p_dict['data_array']) == 0:
            y_axis_min = 0
            y_axis_max = 1

        elif max(p_dict['data_array']) != 0 and \
                min(p_dict['data_array']) != 0 and \
                0 < max(p_dict['data_array']) - min(p_dict['data_array']) <= 1:
            y_axis_min = min(p_dict['data_array']) * (1 - (1 / abs(min(p_dict['data_array'])) ** 1.25))
            y_axis_max = max(p_dict['data_array']) * (1 + (1 / abs(max(p_dict['data_array'])) ** 1.25))

        else:
            if min(p_dict['data_array']) < 0:
                y_axis_min = min(p_dict['data_array']) * 1.5
            else:
                y_axis_min = min(p_dict['data_array']) * 0.75
            if max(p_dict['data_array']) < 0:
                y_axis_max = 0
            else:
                y_axis_max = max(p_dict['data_array']) * 1.10
    plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

    # =============================== Y2 Axis Label ===============================
    # Note we're plotting Y1 label on ax2. We do this because we want the
    # temperature lines to be over the precipitation bars but we want the
    # temperature scale to be on the left side.
    plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])  # Note we're plotting Y1 label on ax2
    ax2.yaxis.set_label_position('left')

    # ============================= Legend Properties =============================
    # (note that we need a separate instance of this code for each subplot. This
    # one controls the temperatures subplot.) Legend should be plotted before any
    # other lines are plotted (like averages or custom line segments).

    if p_dict['showLegend']:
        headers = [_.decode('utf-8') for _ in p_dict['headers_1']]
        legend = ax2.legend(headers,
                            loc='upper left',
                            bbox_to_anchor=(0.0, -0.15),
                            ncol=2,
                            prop={'size': float(p_dict['legendFontSize'])}
                            )
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
        frame = legend.get_frame()
        frame.set_alpha(0)

    # We are setting these values here in a special way because it's apparently
    # the only way to overcome twinx.
    for tick in ax1.yaxis.get_major_ticks():
        tick.label1.set_fontname(plug_dict['fontMain'])
        tick.label2.set_fontname(plug_dict['fontMain'])
        tick.label1.set_fontsize(plug_dict['tickFontSize'])
        tick.label2.set_fontsize(plug_dict['tickFontSize'])
    for tick in ax2.yaxis.get_major_ticks():
        tick.label1.set_fontname(plug_dict['fontMain'])
        tick.label2.set_fontname(plug_dict['fontMain'])
        tick.label1.set_fontsize(plug_dict['tickFontSize'])
        tick.label2.set_fontsize(plug_dict['tickFontSize'])

    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.5, 0.98))
    chart_tools.format_grids(p_dict=p_dict, k_dict=k_dict, logger=log)
    plt.tight_layout(pad=1)

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
