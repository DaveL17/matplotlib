#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the polar charts
Note that the polar chart device can be used for other things, but it is coded
like a wind rose which makes it easier to understand what's happening. Note
that it would be possible to convert wind direction names (north-northeast) to
an ordinal degree value, however, it would be very difficult to contend with
all of the possible international Unicode values that could be passed to the
device. Better to make it the responsibility of the user to convert their data
to degrees.

Note: there is a fatal error with later versions of numpy (specificaly 1.16.6)
that causes polar charts to fail spectacularly during the savefig operation.
There is apparently no way to code around this.

-----

"""
# TODO: CONSIDER GNUPLOT?

# import ast
# import csv
# import datetime as dt
# from dateutil.parser import parse as date_parse
# import itertools
import numpy as np
# import operator as op
# import sys
# import pickle
# import unicodedata

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
# import matplotlib.patches as patches
# import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave


final_data = []
payload = chart_tools.payload

try:
    def __init__():
        pass

    num_obs                               = payload['p_dict']['numObs']
    payload['p_dict']['backgroundColor']  = chart_tools.fix_rgb(payload['p_dict']['backgroundColor'])
    payload['p_dict']['faceColor']        = chart_tools.fix_rgb(payload['p_dict']['faceColor'])
    payload['p_dict']['currentWindColor'] = chart_tools.fix_rgb(payload['p_dict']['currentWindColor'])
    payload['p_dict']['maxWindColor']     = chart_tools.fix_rgb(payload['p_dict']['maxWindColor'])

    # ============================== Column Headings ==============================
    # Pull the column headings for the labels, then delete the row from
    # self.final_data.
    theta_path = '{0}{1}'.format(payload['prefs']['dataPath'],
                                 payload['p_dict']['thetaValue'].encode('utf-8'))
    radii_path = '{0}{1}'.format(payload['prefs']['dataPath'],
                                 payload['p_dict']['radiiValue'].encode('utf-8'))

    if theta_path != 'None' and radii_path != 'None':

        # Get the data.
        theta = chart_tools.get_data(theta_path)
        final_data.append(theta)
        radii = chart_tools.get_data(radii_path)
        final_data.append(radii)

        chart_tools.log['Threaddebug'].append(u"Data: {0}".format(final_data))

        # Pull out the header information out of the data.
        del final_data[0][0]
        del final_data[1][0]

        # Create lists of data to plot (string -> float).
        [payload['p_dict']['wind_direction'].append(float(item[1])) for item in final_data[0]]
        [payload['p_dict']['wind_speed'].append(float(item[1])) for item in final_data[1]]

        # Get the length of the lists
        len_wind_dir = len(payload['p_dict']['wind_direction'])
        len_wind_spd = len(payload['p_dict']['wind_speed'])

        # If the number of observations we have is greater than the number we want, we
        # need to slice the lists to use the last n observations.
        if len_wind_dir > num_obs:
            payload['p_dict']['wind_direction'] = payload['p_dict']['wind_direction'][num_obs * -1:]

        if len_wind_spd > num_obs:
            payload['p_dict']['wind_speed'] = payload['p_dict']['wind_speed'][num_obs * -1:]

        # If at this point we still don't have an equal number of observations for both
        # theta and radii, we shouldn't plot the chart.
        if len(payload['p_dict']['wind_direction']) != len(payload['p_dict']['wind_speed']):
            chart_tools.log['Warning'].append(u"[{0}] Insufficient number of observations "
                                              u"to plot.".format(payload['props']['name']))
            chart_tools.log['Warning'].append(u"Skipped. {0}".format(payload['props']['name']))
            exit()

        # Create the array of grey scale for the intermediate lines and set the last
        # one red. (MPL will accept string values '0' - '1' as grey scale, so we create
        # a number of greys based on 1.0 / number of observations.)
        color_increment = 1.0 / num_obs
        color = color_increment
        for item in range(0, num_obs, 1):
            payload['p_dict']['bar_colors'].append("%0.3f" % color)
            color += color_increment
        payload['p_dict']['bar_colors'][num_obs - 1] = payload['p_dict']['currentWindColor']

        # Change the default bar color for the max to user preference.
        max_wind_speed = max(payload['p_dict']['wind_speed'])
        payload['p_dict']['bar_colors'][payload['p_dict']['wind_speed'].index(max_wind_speed)] = payload['p_dict']['maxWindColor']

        # Polar plots are in radians (not degrees.)
        payload['p_dict']['wind_direction'] = np.radians(payload['p_dict']['wind_direction'])
        wind = zip(payload['p_dict']['wind_direction'], payload['p_dict']['wind_speed'], payload['p_dict']['bar_colors'])

        # ============================== Customizations ===============================
        size = float(payload['p_dict']['sqChartSize']) / int(plt.rcParams['savefig.dpi'])
        fig = plt.figure(figsize=(size, size))
        ax = plt.subplot(111, polar=True)  # Create subplot
        plt.grid(color=plt.rcParams['grid.color'])                        # Color the grid
        ax.set_theta_zero_location('N')                                   # Set zero to North
        ax.set_theta_direction(-1)                                        # Reverse the rotation
        ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])  # Customize the xtick labels
        ax.spines['polar'].set_visible(False)                             # Show or hide the plot spine
        ax.set_axis_bgcolor(payload['p_dict']['faceColor'])               # Background color of the plot area.

        # ============================== Create the Plot ==============================
        # Note: zorder of the plot must be >2.01 for the plot to be above the grid (the
        # grid defaults to z = 2.)
        for w in wind:
            ax.plot((0, w[0]), (0, w[1]), color=w[2], linewidth=2, zorder=3)

        # Right-size the grid (must be done after the plot), and customize the tick
        # labels. The default covers anything over 50.
        ticks = np.arange(20, 100, 20)
        grids = range(20, 120, 20)

        if max_wind_speed <= 5:
            ticks = np.arange(1, 5, 1)
            grids = range(1, 6, 1)

        elif 5 < max_wind_speed <= 10:
            ticks = np.arange(2, 10, 2)
            grids = range(2, 12, 2)

        elif 10 < max_wind_speed <= 20:
            ticks = np.arange(5, 20, 5)
            grids = range(5, 30, 5)

        elif 20 < max_wind_speed <= 30:
            ticks = np.arange(6, 30, 6)
            grids = range(6, 36, 6)

        elif 30 < max_wind_speed <= 40:
            ticks = np.arange(8, 40, 8)
            grids = range(8, 48, 8)

        elif 40 < max_wind_speed <= 50:
            ticks = np.arange(10, 50, 10)
            grids = range(10, 60, 10)

        elif 50 < max_wind_speed:
            plt.text(0.5, 0.5,
                     u"Holy crap!",
                     color='FF FF FF',
                     horizontalalignment='center',
                     verticalalignment='center',
                     transform=ax.transAxes,
                     bbox=dict(facecolor='red', alpha='0.5')
                     )

        ax.yaxis.set_ticks(ticks)
        ax.set_rgrids(grids, **payload['k_dict']['k_rgrids'])

        # If the user wants to hide tick labels, lets do that.
        if payload['p_dict']['xHideLabels']:
            ax.axes.xaxis.set_ticklabels([])
        if payload['p_dict']['yHideLabels']:
            ax.axes.yaxis.set_ticklabels([])

        # ========================== Current Obs / Max Wind ===========================
        # Note that we reduce the value of the circle plot so that it appears when
        # transparent charts are enabled (otherwise the circle is obscured. The
        # transform can be done one of two ways: access the private attribute
        # "ax.transData._b", or "ax.transProjectionAffine + ax.transAxes".
        fig = plt.gcf()
        max_wind_circle = plt.Circle((0, 0),
                                     (max(payload['p_dict']['wind_speed']) * 0.99),
                                     transform=ax.transProjectionAffine + ax.transAxes,
                                     fill=False,
                                     edgecolor=payload['p_dict']['maxWindColor'],
                                     linewidth=2,
                                     alpha=1,
                                     zorder=9
                                     )
        fig.gca().add_artist(max_wind_circle)

        last_wind_circle = plt.Circle((0, 0), (payload['p_dict']['wind_speed'][-1] * 0.99),
                                      transform=ax.transProjectionAffine + ax.transAxes,
                                      fill=False,
                                      edgecolor=payload['p_dict']['currentWindColor'],
                                      linewidth=2,
                                      alpha=1,
                                      zorder=10
                                      )
        fig.gca().add_artist(last_wind_circle)

        # ================================== No Wind ==================================
        # If latest obs is a speed of zero, plot something that we can see.
        if payload['p_dict']['wind_speed'][-1] == 0:
            zero_wind_circle = plt.Circle((0, 0), 0.15,
                                          transform=ax.transProjectionAffine + ax.transAxes,
                                          fill=True,
                                          facecolor=payload['p_dict']['currentWindColor'],
                                          edgecolor=payload['p_dict']['currentWindColor'],
                                          linewidth=2,
                                          alpha=1,
                                          zorder=12
                                          )
            fig.gca().add_artist(zero_wind_circle)

        # ========================== Transparent Chart Fill ===========================
        if payload['p_dict']['transparent_charts'] and payload['p_dict']['transparent_filled']:
            ylim = ax.get_ylim()
            patch = plt.Circle((0, 0),
                               ylim[1],
                               transform=ax.transProjectionAffine + ax.transAxes,
                               fill=True,
                               facecolor=payload['p_dict']['faceColor'],
                               linewidth=1,
                               alpha=1,
                               zorder=1
                               )
            fig.gca().add_artist(patch)

        # ============================= Legend Properties =============================
        # Legend should be plotted before any other lines are plotted (like averages or
        # custom line segments).

        if payload['p_dict']['showLegend']:
            legend = ax.legend(([u"Current", u"Maximum"]),
                               loc='upper center',
                               bbox_to_anchor=(0.5, -0.05),
                               ncol=2,
                               prop={'size': float(payload['p_dict']['legendFontSize'])}
                               )
            legend.legendHandles[0].set_color(payload['p_dict']['currentWindColor'])
            legend.legendHandles[1].set_color(payload['p_dict']['maxWindColor'])
            [text.set_color(payload['p_dict']['fontColor']) for text in legend.get_texts()]
            frame = legend.get_frame()
            frame.set_alpha(0)

        chart_tools.format_title(payload['p_dict'], payload['k_dict'], loc=(0.025, 0.98), align='left')

    # Note that subplots_adjust affects the space surrounding the subplots and
    # not the fig.
    plt.subplots_adjust(top=0.85,
                        bottom=0.15,
                        left=0.15,
                        right=0.85,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save()

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    chart_tools.log['Critical'].append(sub_error)

except EOFError as err:
    chart_tools.log['Critical'].append(err)
