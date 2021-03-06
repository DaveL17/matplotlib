#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates a composite weather chart
The composite weather chart is a dynamic chart that allows users to add or
remove weather charts at will.  For example, the user could create one
chart that contains subplots for high temperature, wind, and precipitation.
Using the chart configuration dialog, the user would be able to add or
remove elements and the chart would adjust accordingly (additional sublplots
will be added or removed as needed.)
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
import matplotlib.dates as mdate
import matplotlib.ticker as mtick
import matplotlib.patches as patches

# My modules
import chart_tools

log              = chart_tools.log
payload          = chart_tools.payload
p_dict           = payload['p_dict']
k_dict           = payload['k_dict']
state_list       = payload['state_list']
dev_type         = payload['dev_type']
props            = payload['props']
chart_name       = props['name']
plug_dict        = payload['prefs']
dates_to_plot    = ()
dpi              = int(plt.rcParams['savefig.dpi'])
forecast_length  = {'Daily': 8, 'Hourly': 24, 'wundergroundTenDay': 10, 'wundergroundHourly': 24}
height           = int(props['height'])
humidity         = ()
precipitation    = ()
pressure         = ()
temperature_high = ()
temperature_low  = ()
width            = int(props['width'])
wind_bearing     = ()
wind_speed       = ()

log['Threaddebug'].append(u"chart_weather_composite.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass


    def format_subplot(s_plot, title="Title"):
        """Note that we have to set these for each subplot as it's rendered or else
        the settings will only be applied to the last subplot rendered."""
        s_plot.set_title(title, **k_dict['k_title_font'])  # The subplot title
        chart_tools.format_axis_x_ticks(ax=s_plot, p_dict=p_dict, k_dict=k_dict, logger=log)
        chart_tools.format_axis_y(ax=s_plot, p_dict=p_dict, k_dict=k_dict, logger=log)

        # =================================== Grids ===================================
        if p_dict['showxAxisGrid']:
            plot.xaxis.grid(True, **k_dict['k_grid_fig'])

        if p_dict['showyAxisGrid']:
            plot.yaxis.grid(True, **k_dict['k_grid_fig'])

        # ================================ Tick Labels ================================
        if props['customSizeFont']:
            s_plot.tick_params(axis='both', labelsize=int(props['customTickFontSize']))
        else:
            s_plot.tick_params(axis='both', labelsize=int(plug_dict['tickFontSize']))

    def transparent_chart_fill(s):

        if p_dict['transparent_filled']:
            s.add_patch(patches.Rectangle((0, 0), 1, 1,
                                          transform=s.transAxes,
                                          facecolor=p_dict['faceColor'],
                                          zorder=1))

    ax = chart_tools.make_chart_figure(width=p_dict['chart_width'], height=p_dict['chart_height'], p_dict=p_dict)

    # ================================ Set Up Axes ================================
    axes     = props['component_list']
    num_axes = len(axes)

    # ============================ X Axis Observations ============================
    # Daily
    if dev_type in ('Daily', 'wundergroundTenDay'):
        for _ in range(1, forecast_length[dev_type] + 1):
            dates_to_plot    += (state_list[u'd0{d}_date'.format(d=_)],)
            humidity         += (state_list[u'd0{h}_humidity'.format(h=_)],)
            pressure         += (state_list[u'd0{p}_pressure'.format(p=_)],)
            temperature_high += (state_list[u'd0{th}_temperatureHigh'.format(th=_)],)
            temperature_low  += (state_list[u'd0{tl}_temperatureLow'.format(tl=_)],)
            wind_speed       += (state_list[u'd0{ws}_windSpeed'.format(ws=_)],)
            wind_bearing     += (state_list[u'd0{wb}_windBearing'.format(wb=_)],)
            try:
                precipitation    += (state_list[u'd0{pt}_precipTotal'.format(pt=_)],)
            except KeyError:
                precipitation    += (state_list[u'd0{pr}_pop'.format(pr=_)],)

        x1 = [dt.datetime.strptime(_, '%Y-%m-%d') for _ in dates_to_plot]
        x_offset = dt.timedelta(hours=6)

    # Hourly
    else:
        for _ in range(1, forecast_length[dev_type] + 1):

            if _ <= 9:
                _ = '0{dx}'.format(dx=_)

            dates_to_plot    += (state_list[u'h{e}_epoch'.format(e=_)],)
            humidity         += (state_list[u'h{h}_humidity'.format(h=_)],)
            pressure         += (state_list[u'h{p}_pressure'.format(p=_)],)
            temperature_high += (state_list[u'h{th}_temperature'.format(th=_)],)
            temperature_low  += (state_list[u'h{tl}_temperature'.format(tl=_)],)
            wind_speed       += (state_list[u'h{ws}_windSpeed'.format(ws=_)],)
            wind_bearing     += (state_list[u'h{wb}_windBearing'.format(wb=_)],)

            try:
                precipitation    += (state_list[u'h{pi}_precipIntensity'.format(pi=_)],)
            except KeyError:
                precipitation    += (state_list[u'h{pr}_precip'.format(pr=_)],)

        x1 = [dt.datetime.fromtimestamp(_) for _ in dates_to_plot]
        x_offset = dt.timedelta(hours=1)

    # ================================ Set Up Plot ================================
    fig, subplot = plt.subplots(nrows=num_axes, sharex=True, figsize=(width / dpi, height * num_axes / dpi))

    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.5, 0.99))

    try:
        for plot in subplot:
            plot.set_axis_bgcolor(p_dict['backgroundColor'])
            [plot.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    except IndexError:
        subplot.set_axis_bgcolor(p_dict['backgroundColor'])
        [subplot.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    # ============================= Temperature High ==============================
    if 'show_high_temperature' in axes:
        subplot[0].plot(x1, temperature_high, color=p_dict['lineColor'])    # Plot it
        format_subplot(subplot[0], title="high temperature")   # Format the subplot
        transparent_chart_fill(subplot[0])

        if p_dict['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['temperature_min']))
        if p_dict['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)  # Delete the subplot for the next plot

    # ============================== Temperature Low ==============================
    if 'show_low_temperature' in axes:
        subplot[0].plot(x1, temperature_low, color=p_dict['lineColor'])
        format_subplot(subplot[0], title='low temperature')
        transparent_chart_fill(subplot[0])

        if p_dict['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['temperature_min']))
        if p_dict['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # =========================== Temperature High/Low ============================
    if 'show_high_low_temperature' in axes:
        subplot[0].plot(x1, temperature_high, color=p_dict['lineColor'])
        subplot[0].plot(x1, temperature_low, color=p_dict['lineColor'])
        format_subplot(subplot[0], title='high/low temperature')
        transparent_chart_fill(subplot[0])

        if p_dict['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['temperature_min']))
        if p_dict['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ================================= Humidity ==================================
    if 'show_humidity' in axes:
        subplot[0].plot(x1, humidity, color=p_dict['lineColor'])
        format_subplot(subplot[0], title='humidity')
        transparent_chart_fill(subplot[0])

        if p_dict['humidity_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['humidity_min']))
        if p_dict['humidity_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['humidity_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================ Barometric Pressure ============================
    if 'show_barometric_pressure' in axes:
        subplot[0].plot(x1, pressure, color=p_dict['lineColor'])
        format_subplot(subplot[0], title='barometric pressure')
        transparent_chart_fill(subplot[0])

        if p_dict['pressure_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['pressure_min']))
        if p_dict['pressure_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['pressure_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ========================== Wind Speed and Bearing ===========================
    if 'show_wind' in axes:
        data = zip(x1, wind_speed, wind_bearing)
        subplot[0].plot(x1, wind_speed, color=p_dict['lineColor'])
        subplot[0].set_ylim(0, max(wind_speed) + 1)
        transparent_chart_fill(subplot[0])

        for _ in data:
            day = mdate.date2num(_[0])
            location = _[1]

            # Points to where the wind is going to.
            subplot[0].text(day,
                            location,
                            "  .  ",
                            size=5,
                            va="center",
                            ha="center",
                            rotation=(_[2] * -1) + 90,
                            color=p_dict['lineMarkerColor'],
                            bbox=dict(boxstyle="larrow, pad=0.3",
                                      fc=p_dict['lineMarkerColor'],
                                      ec="none",
                                      alpha=0.75
                                      )
                            )

        subplot[0].set_xlim(min(x1) - x_offset, max(x1) + x_offset)
        my_fmt = mdate.DateFormatter(props['xAxisLabelFormat'])
        subplot[0].xaxis.set_major_formatter(my_fmt)
        subplot[0].set_xticks(x1)
        format_subplot(subplot[0], title='wind')

        if p_dict['wind_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['wind_min']))
        if p_dict['wind_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['wind_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================ Precipitation Line =============================
    # Precip intensity is in inches of liquid rain per hour. using a line chart.
    if 'show_precipitation' in axes:
        subplot[0].plot(x1, precipitation, color=p_dict['lineColor'])
        format_subplot(subplot[0], title='total precipitation')
        transparent_chart_fill(subplot[0])

        # Force precip to 2 decimals regardless of device setting.
        subplot[0].yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.2f"))

        if p_dict['precipitation_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['precipitation_min']))
        if p_dict['precipitation_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['precipitation_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================= Precipitation Bar =============================
    # Precip intensity is in inches of liquid rain per hour using a bar chart.
    if 'show_precipitation_bar' in axes:
        subplot[0].bar(x1, precipitation, width=0.4, align='center', color=p_dict['lineColor'])
        format_subplot(subplot[0], title='total precipitation')
        transparent_chart_fill(subplot[0])

        # Force precip to 2 decimals regardless of device setting.
        subplot[0].yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.2f"))

        if p_dict['precipitation_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(p_dict['precipitation_min']))
        if p_dict['precipitation_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(p_dict['precipitation_max']))

        # We apparently have to set this on a plot by plot basis or only the last
        # plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        [label.set_fontname(p_dict['fontMain']) for label in labels]

        # We don't use the subplot variable after this; but this command
        # will be important if we add more subplots.
        subplot = np.delete(subplot, 0)

    top_space = 1 - (50.0 / (height * num_axes))
    bottom_space = 40.0 / (height * num_axes)

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
