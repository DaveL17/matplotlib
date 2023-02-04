# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates a composite weather chart

The composite weather chart is a dynamic chart that allows users to add or remove weather charts at
will.  For example, the user could create one chart that contains subplots for high temperature,
wind, and precipitation. Using the chart configuration dialog, the user would be able to add or
remove elements and the chart would adjust accordingly (additional sublplots will be added or
removed as needed.)
"""

# Built-in Modules
import json
import sys
import traceback
import datetime as dt
import numpy as np
# Third-party Modules
from matplotlib import pyplot as plt
from matplotlib import dates as mdate
from matplotlib import ticker as mtick
from matplotlib import patches
# My modules
import chart_tools  # noqa

LOG              = chart_tools.LOG
PAYLOAD          = chart_tools.payload
P_DICT           = PAYLOAD['p_dict']
K_DICT           = PAYLOAD['k_dict']
STATE_DICT       = PAYLOAD['state_list']
DEV_TYPE         = PAYLOAD['dev_type']
PROPS            = PAYLOAD['props']
CHART_NAME       = PROPS['name']
PLUG_DICT        = PAYLOAD['prefs']
DATES_TO_PLOT    = ()
FORECAST_LENGTH  = {'Daily': 8, 'Hourly': 24, 'wundergroundTenDay': 10, 'wundergroundHourly': 24}
HEIGHT           = int(PROPS['height'])
HUMIDITY         = ()
PRECIPITATION    = ()
PRESSURE         = ()
TEMPERATURE_HIGH = ()
TEMPERATURE_LOW  = ()
WIDTH            = int(PROPS['width'])
WIND_BEARING     = ()
WIND_SPEED       = ()

LOG['Threaddebug'].append("chart_weather_composite.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")
DPI              = int(plt.rcParams['savefig.dpi'])

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")

try:

    def __init__():
        ...


    def format_subplot(s_plot, title="Title"):
        """
        Title Placeholder

        Note that we have to set these for each subplot as it's rendered or else the settings will
        only be applied to the last subplot rendered.
        """
        s_plot.set_title(title, **K_DICT['k_title_font'])  # The subplot title
        chart_tools.format_axis_x_ticks(ax=s_plot, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
        chart_tools.format_axis_x_label(dev=PROPS, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)
        chart_tools.format_axis_y(ax=s_plot, p_dict=P_DICT, k_dict=K_DICT, logger=LOG)

        # =================================== Grids ===================================
        if P_DICT['showxAxisGrid']:
            plot.xaxis.grid(True, **K_DICT['k_grid_fig'])

        if P_DICT['showyAxisGrid']:
            plot.yaxis.grid(True, **K_DICT['k_grid_fig'])

        # ================================ Tick Labels ================================
        if PROPS['customSizeFont']:
            s_plot.tick_params(axis='both', labelsize=int(PROPS['customTickFontSize']))
        else:
            s_plot.tick_params(axis='both', labelsize=int(PLUG_DICT['tickFontSize']))

    def transparent_chart_fill(s):
        """
        Title Placeholder

        Body placeholder
        -----
        :param s:
        :return:
        """
        if P_DICT['transparent_filled']:
            s.add_patch(
                patches.Rectangle(
                    (0, 0), 1, 1,
                    transform=s.transAxes,
                    facecolor=P_DICT['faceColor'],
                    zorder=1
                )
            )

    ax = chart_tools.make_chart_figure(
        width=P_DICT['chart_width'], height=P_DICT['chart_height'], p_dict=P_DICT
    )

    # ================================ Set Up Axes ================================
    axes     = PROPS['component_list']
    num_axes = len(axes)

    # ============================ X Axis Observations ============================
    # Daily
    if DEV_TYPE in ('Daily', 'wundergroundTenDay'):
        for _ in range(1, FORECAST_LENGTH[DEV_TYPE] + 1):
            DATES_TO_PLOT    += (STATE_DICT[f'd0{_}_date'],)
            HUMIDITY         += (STATE_DICT[f'd0{_}_humidity'],)
            PRESSURE         += (STATE_DICT[f'd0{_}_pressure'],)
            TEMPERATURE_HIGH += (STATE_DICT[f'd0{_}_temperatureHigh'],)
            TEMPERATURE_LOW  += (STATE_DICT[f'd0{_}_temperatureLow'],)
            WIND_SPEED       += (STATE_DICT[f'd0{_}_windSpeed'],)
            WIND_BEARING     += (STATE_DICT[f'd0{_}_windBearing'],)
            try:
                PRECIPITATION    += (STATE_DICT[f'd0{_}_precipTotal'],)
            except KeyError:
                PRECIPITATION    += (STATE_DICT[f'd0{_}_pop'],)

        x1 = [dt.datetime.strptime(_, '%Y-%m-%d') for _ in DATES_TO_PLOT]
        x_offset = dt.timedelta(hours=6)

    # Hourly
    else:
        for _ in range(1, FORECAST_LENGTH[DEV_TYPE] + 1):

            if _ <= 9:
                _ = f'0{_}'

            DATES_TO_PLOT    += (STATE_DICT[f'h{_}_epoch'],)
            HUMIDITY         += (STATE_DICT[f'h{_}_humidity'],)
            PRESSURE         += (STATE_DICT[f'h{_}_pressure'],)
            TEMPERATURE_HIGH += (STATE_DICT[f'h{_}_temperature'],)
            TEMPERATURE_LOW  += (STATE_DICT[f'h{_}_temperature'],)
            WIND_SPEED       += (STATE_DICT[f'h{_}_windSpeed'],)
            WIND_BEARING     += (STATE_DICT[f'h{_}_windBearing'],)

            try:
                PRECIPITATION    += (STATE_DICT[f'h{_}_precipIntensity'],)
            except KeyError:
                PRECIPITATION    += (STATE_DICT[f'h{_}_precip'],)

        x1 = [dt.datetime.fromtimestamp(_) for _ in DATES_TO_PLOT]
        x_offset = dt.timedelta(hours=1)

    # ================================ Set Up Plot ================================
    fig, subplot = plt.subplots(
        nrows=num_axes,
        sharex='all',
        figsize=(WIDTH / DPI, HEIGHT * num_axes / DPI)
    )


    chart_tools.format_title(p_dict=P_DICT, k_dict=K_DICT, loc=(0.5, 0.99))

    try:
        for plot in subplot:
            plot.set_facecolor(P_DICT['backgroundColor'])
            _ = [plot.spines[spine].set_color(P_DICT['spineColor'])
                 for spine in ('top', 'bottom', 'left', 'right')
                 ]

    except IndexError:
        subplot.set_facecolor(P_DICT['backgroundColor'])
        _ = [subplot.spines[spine].set_color(P_DICT['spineColor'])
             for spine in ('top', 'bottom', 'left', 'right')
             ]

    # ============================= Temperature High ==============================
    if 'show_high_temperature' in axes:
        subplot[0].plot(x1, TEMPERATURE_HIGH, color=P_DICT['lineColor'])    # Plot it
        format_subplot(subplot[0], title="high temperature")   # Format the subplot
        transparent_chart_fill(subplot[0])

        if P_DICT['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['temperature_min']))
        if P_DICT['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)  # Delete the subplot for the next plot

    # ============================== Temperature Low ==============================
    if 'show_low_temperature' in axes:
        subplot[0].plot(x1, TEMPERATURE_LOW, color=P_DICT['lineColor'])
        format_subplot(subplot[0], title='low temperature')
        transparent_chart_fill(subplot[0])

        if P_DICT['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['temperature_min']))
        if P_DICT['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # =========================== Temperature High/Low ============================
    if 'show_high_low_temperature' in axes:
        subplot[0].plot(x1, TEMPERATURE_HIGH, color=P_DICT['lineColor'])
        subplot[0].plot(x1, TEMPERATURE_LOW, color=P_DICT['lineColor'])
        format_subplot(subplot[0], title='high/low temperature')
        transparent_chart_fill(subplot[0])

        if P_DICT['temperature_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['temperature_min']))
        if P_DICT['temperature_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['temperature_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ================================= Humidity ==================================
    if 'show_humidity' in axes:
        subplot[0].plot(x1, HUMIDITY, color=P_DICT['lineColor'])
        format_subplot(subplot[0], title='humidity')
        transparent_chart_fill(subplot[0])

        if P_DICT['humidity_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['humidity_min']))
        if P_DICT['humidity_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['humidity_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================ Barometric Pressure ============================
    if 'show_barometric_pressure' in axes:
        subplot[0].plot(x1, PRESSURE, color=P_DICT['lineColor'])
        format_subplot(subplot[0], title='barometric pressure')
        transparent_chart_fill(subplot[0])

        if P_DICT['pressure_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['pressure_min']))
        if P_DICT['pressure_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['pressure_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ========================== Wind Speed and Bearing ===========================
    if 'show_wind' in axes:
        data = zip(x1, WIND_SPEED, WIND_BEARING)
        subplot[0].plot(x1, WIND_SPEED, color=P_DICT['lineColor'])
        subplot[0].set_ylim(0, max(WIND_SPEED) + 1)
        transparent_chart_fill(subplot[0])

        for _ in data:
            day = mdate.date2num(_[0])
            location = _[1]

            # Points to where the wind is going to.
            subplot[0].text(
                day,
                location,
                "  .  ",
                size=5,
                va="center",
                ha="center",
                rotation=(_[2] * -1) + 90,
                color=P_DICT['lineMarkerColor'],
                bbox=dict(
                    boxstyle="larrow, pad=0.3",
                    fc=P_DICT['lineMarkerColor'],
                    ec="none",
                    alpha=0.75
                )
            )

        subplot[0].set_xlim(min(x1) - x_offset, max(x1) + x_offset)
        my_fmt = mdate.DateFormatter(PROPS['xAxisLabelFormat'])
        subplot[0].xaxis.set_major_formatter(my_fmt)
        subplot[0].set_xticks(x1)
        format_subplot(subplot[0], title='wind')

        if P_DICT['wind_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['wind_min']))
        if P_DICT['wind_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['wind_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================ Precipitation Line =============================
    # Precip intensity is in inches of liquid rain per hour. using a line chart.
    if 'show_precipitation' in axes:
        subplot[0].plot(x1, PRECIPITATION, color=P_DICT['lineColor'])
        format_subplot(subplot[0], title='total precipitation')
        transparent_chart_fill(subplot[0])

        # Force precip to 2 decimals regardless of device setting.
        subplot[0].yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))

        if P_DICT['precipitation_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['precipitation_min']))
        if P_DICT['precipitation_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['precipitation_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        subplot = np.delete(subplot, 0)

    # ============================= Precipitation Bar =============================
    # Precip intensity is in inches of liquid rain per hour using a bar chart. Note that the bar
    # chart needs Z-order of 2 in order for the bars to be visible. This isn't needed for line
    # charts.
    if 'show_precipitation_bar' in axes:
        subplot[0].bar(x1, PRECIPITATION, width=0.4, align='center', color=P_DICT['lineColor'], zorder=2)
        format_subplot(subplot[0], title='total precipitation')
        transparent_chart_fill(subplot[0])

        # Force precip to 2 decimals regardless of device setting.
        subplot[0].yaxis.set_major_formatter(mtick.FormatStrFormatter("%.2f"))

        if P_DICT['precipitation_min'] not in ("", "None"):
            subplot[0].set_ylim(bottom=float(P_DICT['precipitation_min']))
        if P_DICT['precipitation_max'] not in ("", "None"):
            subplot[0].set_ylim(top=float(P_DICT['precipitation_max']))

        # We apparently have to set this on a plot by plot basis or only the last plot is set.
        labels = subplot[0].get_xticklabels() + subplot[0].get_yticklabels()
        _ = [label.set_fontname(P_DICT['fontMain']) for label in labels]

        # We don't use the subplot variable after this; but this command will be important if we
        # add more subplots.
        subplot = np.delete(subplot, 0)

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type} in {__file__.split('/')[-1]}")

json.dump(LOG, sys.stdout, indent=4)
