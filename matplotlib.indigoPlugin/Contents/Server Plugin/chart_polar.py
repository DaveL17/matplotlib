# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the polar charts

Note that the polar chart device can be used for other things, but it is coded like a wind rose
which makes it easier to understand what's happening. Note that it would be possible to convert
wind direction names (north-northeast) to an ordinal degree value, however, it would be very
difficult to contend with the possible international Unicode values that could be passed to the
device. Better to make it the responsibility of the user to convert their data to degrees.
"""

# Built-in Modules
import json
import sys
import traceback
import numpy as np
# Third-party Modules
from matplotlib import pyplot as plt
# My modules
import chart_tools

LOG        = chart_tools.LOG
PAYLOAD    = chart_tools.payload
P_DICT     = PAYLOAD['p_dict']
K_DICT     = PAYLOAD['k_dict']
PLUG_DICT  = PAYLOAD['prefs']
PROPS      = PAYLOAD['props']
CHART_NAME = PROPS['name']
FINAL_DATA = []

LOG['Threaddebug'].append("chart_polar.py called.")
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

    num_obs = P_DICT['numObs']

    # ============================== Column Headings ==============================
    # Pull the column headings for the labels, then delete the row from self.final_data.
    # theta_path = f"{PLUG_DICT['dataPath']}{P_DICT['thetaValue'].encode('utf-8')}"
    # radii_path = f"{PLUG_DICT['dataPath']}{P_DICT['radiiValue'].encode('utf-8')}"
    theta_path = f"{PLUG_DICT['dataPath']}{P_DICT['thetaValue']}"
    radii_path = f"{PLUG_DICT['dataPath']}{P_DICT['radiiValue']}"

    if theta_path != 'None' and radii_path != 'None':

        # Get the data.
        theta = chart_tools.get_data(data_source=theta_path, logger=LOG)
        FINAL_DATA.append(theta)
        radii = chart_tools.get_data(data_source=radii_path, logger=LOG)
        FINAL_DATA.append(radii)

        LOG['Threaddebug'].append(f"[{CHART_NAME}] Data: {FINAL_DATA}")

        # Pull out the header information out of the data.
        del FINAL_DATA[0][0]
        del FINAL_DATA[1][0]

        # Create lists of data to plot (string -> float).
        _ = [P_DICT['wind_direction'].append(float(item[1])) for item in FINAL_DATA[0]]
        _ = [P_DICT['wind_speed'].append(float(item[1])) for item in FINAL_DATA[1]]

        # Get the length of the lists
        len_wind_dir = len(P_DICT['wind_direction'])
        len_wind_spd = len(P_DICT['wind_speed'])

        # If the number of observations we have is greater than the number we want, we need to
        # slice the lists to use the last n observations.
        if len_wind_dir > num_obs:
            P_DICT['wind_direction'] = P_DICT['wind_direction'][num_obs * -1:]

        if len_wind_spd > num_obs:
            P_DICT['wind_speed'] = P_DICT['wind_speed'][num_obs * -1:]

        # If at this point we still don't have an equal number of observations for both theta and
        # radii, we shouldn't plot the chart.
        if len(P_DICT['wind_direction']) != len(P_DICT['wind_speed']):
            LOG['Warning'].append(
                f"[{CHART_NAME}] Insufficient number of observations to plot. Skipped."
            )
            sys.exit()

        # Create the array of grey scale for the intermediate lines and set the last one red. (MPL
        # will accept string values '0' - '1' as grey scale, so we create a number of greys based
        # on 1.0 / number of observations.)
        color_increment = 1.0 / num_obs
        color = color_increment
        for item in range(0, num_obs, 1):
            P_DICT['bar_colors'].append(f"{color:0.3f}")
            color += color_increment
        P_DICT['bar_colors'][num_obs - 1] = P_DICT['currentWindColor']

        # Change the default bar color for the max to user preference.
        max_wind_speed = max(P_DICT['wind_speed'])
        P_DICT['bar_colors'][P_DICT['wind_speed'].index(max_wind_speed)] = P_DICT['maxWindColor']

        # Polar plots are in radians (not degrees.)
        P_DICT['wind_direction'] = np.radians(P_DICT['wind_direction'])
        wind = zip(P_DICT['wind_direction'], P_DICT['wind_speed'], P_DICT['bar_colors'])

        # ============================== Customizations ===============================
        size = float(P_DICT['sqChartSize']) / int(plt.rcParams['savefig.dpi'])
        fig = plt.figure(figsize=(size, size))
        # Create subplot
        ax = plt.subplot(111, polar=True)
        # Color the grid
        plt.grid(color=PLUG_DICT['gridColor'])
        # Set zero to North
        ax.set_theta_zero_location('N')
        # Reverse the rotation
        ax.set_theta_direction(-1)
        # Customize the xtick labels
        ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
        # Show or hide the plot spine
        ax.spines['polar'].set_visible(False)
        # Background color of the plot area.
        ax.set_facecolor(P_DICT['faceColor'])

        # ============================== Create the Plot ==============================
        # Note: zorder of the plot must be >2.01 for the plot to be above the grid (the grid
        # defaults to z = 2.)
        for w in wind:
            ax.plot((0, w[0]), (0, w[1]), color=w[2], linewidth=2, zorder=3)

        # Right-size the grid (must be done after the plot), and customize the tick labels. The
        # default covers anything over 50.
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
            plt.text(
                0.5, 0.5,
                "Holy crap!",
                color='FF FF FF',
                horizontalalignment='center',
                verticalalignment='center',
                transform=ax.transAxes,
                bbox=dict(facecolor='red', alpha='0.5')
            )

        ax.yaxis.set_ticks(ticks)
        ax.set_rgrids(grids, **K_DICT['k_rgrids'])

        # If the user wants to hide tick labels, lets do that.
        if P_DICT['xHideLabels']:
            ax.axes.xaxis.set_ticklabels([])
        if P_DICT['yHideLabels']:
            ax.axes.yaxis.set_ticklabels([])

        # ========================== Current Obs / Max Wind ===========================
        # Note that we reduce the value of the circle plot so that it appears when transparent
        # charts are enabled (otherwise the circle is obscured). The transform can be done one of
        # two ways: access the private attribute:
        # "ax.transData._b", or "ax.transProjectionAffine + ax.transAxes".
        fig = plt.gcf()
        max_wind_circle = plt.Circle(
            (0, 0),
            (max(P_DICT['wind_speed']) * 0.99),
            transform=ax.transProjectionAffine + ax.transAxes,
            fill=False,
            edgecolor=P_DICT['maxWindColor'],
            linewidth=2,
            alpha=1,
            zorder=9
        )
        fig.gca().add_artist(max_wind_circle)

        last_wind_circle = plt.Circle(
            (0, 0), (P_DICT['wind_speed'][-1] * 0.99),
            transform=ax.transProjectionAffine + ax.transAxes,
            fill=False,
            edgecolor=P_DICT['currentWindColor'],
            linewidth=2,
            alpha=1,
            zorder=10
        )
        fig.gca().add_artist(last_wind_circle)

        # ================================== No Wind ==================================
        # If latest obs is a speed of zero, plot something that we can see.
        if P_DICT['wind_speed'][-1] == 0:
            zero_wind_circle = plt.Circle(
                (0, 0), 0.15,
                transform=ax.transProjectionAffine + ax.transAxes,
                fill=True,
                facecolor=P_DICT['currentWindColor'],
                edgecolor=P_DICT['currentWindColor'],
                linewidth=2,
                alpha=1,
                zorder=12
            )
            fig.gca().add_artist(zero_wind_circle)

        # ========================== Transparent Chart Fill ===========================
        if P_DICT['transparent_charts'] and P_DICT['transparent_filled']:
            ylim = ax.get_ylim()
            patch = plt.Circle(
                (0, 0),
                ylim[1],
                transform=ax.transProjectionAffine + ax.transAxes,
                fill=True,
                facecolor=P_DICT['faceColor'],
                linewidth=1,
                alpha=1,
                zorder=1
            )
            fig.gca().add_artist(patch)

        # ============================= Legend Properties =============================
        # Legend should be plotted before any other lines are plotted (like averages or custom line
        # segments).

        if P_DICT['showLegend']:
            legend = ax.legend(
                (["Current", "Maximum"]),
                loc='upper center',
                bbox_to_anchor=(0.5, -0.05),
                ncol=2,
                prop={'size': float(P_DICT['legendFontSize'])}
            )
            legend.legendHandles[0].set_color(P_DICT['currentWindColor'])
            legend.legendHandles[1].set_color(P_DICT['maxWindColor'])
            _ = [text.set_color(P_DICT['fontColor']) for text in legend.get_texts()]
            frame = legend.get_frame()
            frame.set_alpha(0)

        chart_tools.format_title(
            p_dict=P_DICT,
            k_dict=K_DICT,
            loc=(0.025, 0.98),
            align='left',
            logger=LOG
        )

    # Note that subplots_adjust affects the space surrounding the subplots and not the fig.
    plt.subplots_adjust(
        top=0.85,
        bottom=0.15,
        left=0.15,
        right=0.85,
        hspace=None,
        wspace=None
    )

    # Set the tick label size
    font_color = PLUG_DICT['fontColor']
    if P_DICT['customSizeFont']:
        plt.xticks(fontsize=int(P_DICT['customTickFontSize']), color=font_color)
        plt.yticks(fontsize=int(P_DICT['customTickFontSize']), color=font_color)
    else:
        plt.xticks(fontsize=int(P_DICT['tickFontSize']), color=font_color)
        plt.yticks(fontsize=int(P_DICT['tickFontSize']), color=font_color)

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type}")

json.dump(LOG, sys.stdout, indent=4)
