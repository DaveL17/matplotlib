# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Title Placeholder

Body placeholder
"""
# Built-in Modules
import ast
import csv
import json
import sys
import traceback
import unicodedata
import datetime as dt
import operator as op
import numpy as np
from dateutil.parser import parse as date_parse

# Third-party Modules
# Note the order and structure of matplotlib imports is intentional.
import matplotlib
# Note: this statement must be run before any other matplotlib imports are done.
matplotlib.use('AGG')
from matplotlib import pyplot as plt
from matplotlib import dates as mdate
from matplotlib import ticker as mtick

# My modules

# Collection of logging messages.
LOG = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

# Unpack the payload data. The first element of the payload is the name of this script (we don't
# need that). As long as size isn't a limitation we will always send the entire payload as element
# 1.
try:
    payload = json.loads(sys.argv[1].encode("utf-8"))
    LOG['Debug'].append(f"[{payload['props']['name']}] payload unpacked successfully.")
except IndexError:
    pass


def __init__():
    """
    Title Placeholder

    Body placeholder
    :return:
    """


# =============================================================================
def convert_the_data(final_data, data_source, logger):
    """
    Convert data into form that matplotlib can understand

    Matplotlib can't plot values like 'Open' and 'Closed', so we convert them for plotting. We do
    this on the fly, and we don't change the underlying data in any way. Further, some data can be
    presented that should not be charted. For example, the WUnderground plugin will present '-99.0'
    when WUnderground is not able to deliver a rational value. Therefore, we convert '-99.0' to NaN
    values.
    -----
    :param logger:
    :param list final_data: the data to be charted
    :param str data_source:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] "
                        f"Coercing chart data to chart-able values where needed.")
    converter = {
        'true': 1, 'false': 0, 'open': 1, 'closed': 0, 'on': 1, 'off': 0, 'locked': 1,
        'unlocked': 0, 'up': 1, 'down': 0, '1': 1, '0': 0, 'heat': 1, 'armed': 1, 'disarmed': 0
    }
    now = dt.datetime.now()
    now_text = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    # =============================================================================
    def is_number(s):
        """
        Title Placeholder

        Body placeholder
        :param s:
        :return:
        """
        try:
            float(s)
            return True

        except ValueError:
            pass

        try:
            unicodedata.numeric(s)
            return True

        except (TypeError, ValueError):
            pass

        return False

    for value in final_data:
        if value[1].lower() in converter:
            value[1] = converter[value[1].lower()]

    # We have converted all nonsense numbers to '-99.0'. Let's replace those with
    # 'NaN' for charting.
    final_data = [[n[0], 'NaN'] if n[1] == '-99.0' else n for n in final_data]

    # ================================ Process CSV ================================
    # If the CSV file is missing data or is completely empty, we generate a phony one and alert the
    # user. This helps avoid nasty surprises down the line.

    # ============================= CSV File is Empty =============================
    # Adds header and one observation. Length of CSV file goes from zero to two.
    if len(final_data) < 1:
        final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
        logger['Warning'].append(
            f"[{payload['props']['name']}] CSV file is empty. File: {data_source}"
        )

    # ===================== CSV File has Headers but no Data ======================
    # Adds one observation. Length of CSV file goes from one to two.
    if len(final_data) < 2:
        final_data.append((now_text, 0))
        logger['Warning'].append(
            f"[{payload['props']['name']}] CSV file does not have sufficient information to make "
            f"a useful plot. File: {data_source}"
        )

    # =============================== Malformed CSV ===============================
    # Test to see if any data element is a valid numeric and replace it with 'NaN' if it isn't.

    # Preserve the header row.
    headers = final_data[0]
    del final_data[0]

    # Data element contains an invalid string element. All proper strings like 'off' and 'true'
    # should already have been converted with self.convert_the_data() above.
    final_data = [(item[0], 'NaN') if not is_number(item[1]) else item for item in final_data]

    # Put the header row back in.
    final_data.insert(0, headers)

    return final_data


# =============================================================================
def eval_expr(expr):
    """
    Title Placeholder

    Body placeholder
    :param expr:
    :return:
    """
    LOG['Debug'].append(f"[{payload['props']['name']}] Evaluating expressions.")
    return eval_(ast.parse(expr, mode='eval').body)


# =============================================================================
def eval_(mode):
    """
    Title Placeholder

    Body placeholder
    :param mode:
    :return:
    """
    operators = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
        ast.BitXor: op.xor, ast.USub: op.neg
    }

    if isinstance(mode, ast.Num):  # <number>
        value = mode.n
    elif isinstance(mode, ast.BinOp):  # <left> <operator> <right>
        value = operators[type(mode.op)](eval_(mode=mode.left), eval_(mode=mode.right))
    elif isinstance(mode, ast.UnaryOp):  # <operator> <operand> e.g., -1
        value = operators[type(mode.op)](eval_(mode=mode.operand))
    else:
        raise TypeError(mode)

    return value

# =============================================================================
def fix_rgb(color):
    """
    Title Placeholder

    Body placeholder
    :param color:
    :return:
    """
    LOG['Debug'].append(f"[{payload['props']['name']}] Coercing colors to #RRBBGG.")
    rgb = color.replace(' ', '').replace('#', '')
    return f"#{rgb}"


# =============================================================================
def format_axis(ax_obj):
    """
    Set various axis properties

    Note that this method purposefully accesses protected members of the _text class.
    -----
    :param class 'matplotlib.table.Table' ax_obj: matplotlib table object
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Setting axis properties.")
    ax_props = ax_obj.properties()
    ax_cells = ax_props['children']
    for cell in ax_cells:
        cell.set_facecolor(payload['p_dict']['faceColor'])
        cell._text.set_color(payload['p_dict']['fontColor'])
        cell._text.set_fontname(payload['p_dict']['fontMain'])
        cell._text.set_fontsize(int(payload['props']['fontSize']))
        cell.set_linewidth(int(plt.rcParams['lines.linewidth']))

        # This may not be supportable without including fonts with the plugin.
        # cell._text.set_fontstretch(1000)

        # Controls grid display
        if payload['props'].get('calendarGrid', True):
            cell.set_edgecolor(payload['p_dict']['spineColor'])
        else:
            cell.set_edgecolor(payload['p_dict']['faceColor'])


# =============================================================================
def format_axis_x_label(dev, p_dict, k_dict, logger):  # noqa
    """
    Format X axis label visibility and properties

    If the user chooses to display a legend, we don't want an axis label because they will fight
    with each other for space.
    -----
    :param dict logger:
    :param dict dev: device props
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :return unicode result:
    """
    try:
        font_main           = p_dict.get('fontMain', 'Arial')  # Main font style
        font_size           = int(p_dict.get('tickFontSize', '8'))  # Main font size
        custom_size_font    = p_dict.get('customSizeFont', False)  # Use custom font sizes?  Bool
        custom_axis_label_x = p_dict.get('customAxisLabelX', '')
        custom_font_size    = int(p_dict.get('customTickFontSize', '8'))
        show_legend         = p_dict.get('showLegend', False)  # Show legend?  Bool

        # The label of the X axis ticks (not the axis label)
        if custom_size_font:
            plt.xticks(fontname=font_main, fontsize=custom_font_size)
        else:
            plt.xticks(fontname=font_main, fontsize=font_size)

        if not show_legend:
            # The label of the X axis (not the tick labels)
            plt.xlabel(custom_axis_label_x, **k_dict['k_x_axis_font'])

            if p_dict['verboseLogging']:
                logger['Threaddebug'].append(
                    f"[{payload['props']['name']}] No call for legend. Formatting X label."
                )

        if show_legend and custom_axis_label_x.strip(' ') not in ('', 'null'):
            logger['Debug'].append(
                f"[{payload['props']['name']}] X axis label is suppressed to make room for the "
                f"chart legend."
            )

    except (ValueError, TypeError) as err:
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting X labels.\n{err}"
        )

    except RuntimeError as err:
        if "exceeds Locator.MAXTICKS" in traceback.format_exc(err):
            logger['Critical'].append(
                f"[{payload['props']['name']}] Chart data will produce too many X axis ticks. "
                f"Check source data."
            )


# =============================================================================
def format_axis_x_min_max(p_dict, logger):
    """
    Format x-axis range limits

    Setting the limits before the plot turns off autoscaling, which causes the limit that's not set
    to behave weirdly at times. This block is meant to overcome that weirdness for something more
    desirable.
    -----
    :param dict p_dict: plotting parameters
    :param dict logger:
    """

    try:

        x_min = min(p_dict['data_array'])
        x_max = max(p_dict['data_array'])
        x_min_wanted = p_dict['xAxisMin']
        x_max_wanted = p_dict['xAxisMax']

        # Since the min / max is used here only for chart boundaries, we "trick" Matplotlib by
        # using a number that's very nearly zero.
        if x_min == 0:
            x_min = 0.000001

        if x_max == 0:
            x_max = 0.000001

        # Y min
        if isinstance(x_min_wanted, str) and x_min_wanted.lower() == 'none':
            if x_min > 0:
                x_axis_min = x_min * (1 - (1 / abs(x_min) ** 1.25))
            else:
                x_axis_min = x_min * (1 + (1 / abs(x_min) ** 1.25))
        else:
            x_axis_min = float(x_min_wanted)

        # Y max
        if isinstance(x_max_wanted, str) and x_max_wanted.lower() == 'none':
            if x_max > 0:
                x_axis_max = x_max * (1 + (1 / abs(x_max) ** 1.25))
            else:
                x_axis_max = x_max * (1 - (1 / abs(x_max) ** 1.25))

        else:
            x_axis_max = float(x_max_wanted)

        plt.xlim(xmin=x_axis_min, xmax=x_axis_max)

    except (ValueError, TypeError) as err:
        logger['Warning'].append(
            f"[{payload['props']['name']}] Error setting axis limits for x axis. Will rely on "
            f"matplotlib to determine limits. ({err})"
        )


# =============================================================================
def format_axis_x_scale(x_axis_bins, logger):
    """
    Format X axis scale based on user setting

    The format_axis_x_scale() method sets the bins for the X axis. Presently, we assume a date-based
    X axis.
    -----
    :param dict logger:
    :param list x_axis_bins:
    """

    try:
        if x_axis_bins == 'quarter-hourly':
            plt.gca().xaxis.set_major_locator(mdate.MinuteLocator(interval=15))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 1)))
        if x_axis_bins == 'half-hourly':
            plt.gca().xaxis.set_major_locator(mdate.MinuteLocator(interval=30))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 1)))
        elif x_axis_bins == 'hourly':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=1))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 24)))
        elif x_axis_bins == 'hourly_2':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=2))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 8)))
        elif x_axis_bins == 'hourly_4':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 8)))
        elif x_axis_bins == 'hourly_8':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 4)))
        elif x_axis_bins == 'hourly_12':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 2)))
        elif x_axis_bins == 'daily':
            plt.gca().xaxis.set_major_locator(mdate.DayLocator(interval=1))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 6)))
        elif x_axis_bins == 'weekly':
            plt.gca().xaxis.set_major_locator(mdate.DayLocator(interval=7))
            plt.gca().xaxis.set_minor_locator(mdate.DayLocator(interval=1))
        elif x_axis_bins == 'monthly':
            plt.gca().xaxis.set_major_locator(mdate.MonthLocator(interval=1))
            plt.gca().xaxis.set_minor_locator(mdate.DayLocator(interval=1))
        elif x_axis_bins == 'yearly':
            plt.gca().xaxis.set_major_locator(mdate.YearLocator())
            plt.gca().xaxis.set_minor_locator(mdate.MonthLocator(interval=12))

    except (ValueError, TypeError):
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting X axis scale: x_axis_bins = "
            f"{x_axis_bins}"
        )


# =============================================================================
def format_axis_x_ticks(ax, p_dict, k_dict, logger):
    """
    Format X axis tick properties

    Controls the format and placement of the tick marks on the X axis.
    -----
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    try:
        # This should skip for devices that don't have date-based X axes.
        # if 'xAxisLabelFormat' in p_dict.keys():
        if 'xAxisLabelFormat' in p_dict:
            ax.tick_params(axis='x', **k_dict['k_major_x'])
            ax.tick_params(axis='x', **k_dict['k_minor_x'])
            ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
            format_axis_x_scale(x_axis_bins=p_dict.get('xAxisBins', '%A'), logger=LOG)

            # If the x-axis format has been set to None, let's hide the labels.
            if p_dict['xAxisLabelFormat'] == "None":
                ax.axes.xaxis.set_ticklabels([])

        return ax

    except (ValueError, TypeError):
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting X ticks Labels: {k_dict['k_major_x']}"
            f"\n{p_dict['xAxisLabelFormat']}\n{p_dict['xAxisBins']}"
        )


# =============================================================================
def format_axis_y_ticks(p_dict, k_dict, logger):
    """
    Format Y axis tick marks

    Controls the format and placement of Y ticks.
    -----
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    custom_ticks_marks = p_dict['customTicksY'].strip()
    custom_ticks_labels = p_dict['customTicksLabelY'].strip()

    try:
        # Get the default tick values and labels (which we'll replace as needed.)
        marks, labels = plt.yticks()

        # If the user has not set custom tick values or labels, we're done.
        if custom_ticks_marks.lower() in ('none', '') \
                and custom_ticks_labels.lower() in ('none', ''):
            return

        # If tick locations defined but tick labels are empty, let's use the tick
        # locations as the tick labels
        if custom_ticks_marks.lower() not in ('none', '') \
                and custom_ticks_labels.lower() in ('none', ''):
            custom_ticks_labels = custom_ticks_marks

        # Replace default Y tick values with the custom ones.
        if custom_ticks_marks.lower() not in ('none', '') \
                and not custom_ticks_marks.isspace():
            marks = [float(_) for _ in custom_ticks_marks.split(",")]

        # Replace the default Y tick labels with the custom ones.
        if custom_ticks_labels.lower() not in ('none', '') \
                and not custom_ticks_labels.isspace():
            labels = [f"{_.strip()}" for _ in custom_ticks_labels.split(",")]

        plt.yticks(marks, labels)

    except (KeyError, ValueError):
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting Y axis  ticks: customAxisLabelY = "
            f"{p_dict['customAxisLabelY']}"
        )
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting Y1 axis label: k_y_axis_font = "
            f"{k_dict['k_y_axis_font']}"
        )
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting Y1 axis label: customTicksY = "
            f"{p_dict['customTicksY']}"
        )


# =============================================================================
def format_axis_y(ax, p_dict, k_dict, logger):
    """
    Format Y1 axis display properties

    Controls the format and properties of the Y axis.
    -----
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """
    # TODO: Balance the axis methods.  We should have:
    #       x_label
    #       x_scale
    #       x_ticks
    #       y1_label
    #       y1_scale
    #       y1_ticks
    #       y1_min_max
    #       y2_label
    #       y2_scale
    #       y2_ticks
    #       y2_min_max

    try:
        ax.tick_params(axis='y', **k_dict['k_major_y'])
        ax.tick_params(axis='y', **k_dict['k_minor_y'])
        ax.yaxis.set_major_formatter(
            mtick.FormatStrFormatter(f"%.{int(p_dict.get('yAxisPrecision', '0'))}f")
        )

        # Mirror Y axis values on Y2. Not all charts will support this option.
        try:
            if p_dict['yMirrorValues']:
                ax.tick_params(labelright=True)

                # A user may want tick labels only on Y2.
                if not p_dict['yMirrorValuesAlsoY1']:
                    ax.tick_params(labelleft=False)

        except KeyError:
            pass

        return ax

    except (ValueError, TypeError):
        name = payload['props']['name']
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y ticks: k_major_y = {k_dict['k_major_y']}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y ticks: k_minor_x = {k_dict['k_minor_y']}"
        )
        lbl_fmt = mtick.FormatStrFormatter(
            f"[{name}] %.{int(p_dict['yAxisPrecision'])}f"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y ticks: xAxisLabelFormat = {lbl_fmt}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y ticks: yMirrorValues = {p_dict['yMirrorValues']}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y ticks: yMirrorValuesAlsoY1 = "
            f"{p_dict['yMirrorValuesAlsoY1']}"
        )


# =============================================================================
def format_axis_y1_label(p_dict, k_dict, logger):
    """
    Format Y1 axis labels
    Controls the format and placement of labels for the Y1 axis.
    -----
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    font_main = p_dict.get('fontMain', 'Arial')  # Main font style

    try:
        plt.ylabel(p_dict.get('customAxisLabelY', ''), **k_dict['k_y_axis_font'])

        if p_dict['customSizeFont']:
            plt.yticks(fontname=font_main, fontsize=int(p_dict['customTickFontSize']))
        else:
            plt.yticks(fontname=font_main, fontsize=int(p_dict['tickFontSize']))

    except (ValueError, TypeError):
        name = payload['props']['name']
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y1 axis label: customAxisLabelY "
            f"= {p_dict['customAxisLabelY']}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting Y1 axis label: k_y_axis_font = "
            f"{k_dict['k_y_axis_font']}"
        )


# =============================================================================
def format_axis_y1_min_max(p_dict, logger):
    """
    Format Y1 axis range limits

    Setting the limits before the plot turns off autoscaling, which causes the limit that's not set
    to behave weirdly at times. This block is meant to overcome that weirdness for something more
    desirable.
    -----
    :param dict p_dict: plotting parameters
    :param dict logger:
    """

    try:

        y_min = min(p_dict['data_array'])
        y_max = max(p_dict['data_array'])
        y_min_wanted = p_dict['yAxisMin']
        y_max_wanted = p_dict['yAxisMax']

        # Since the min / max is used here only for chart boundaries, we "trick" Matplotlib by
        # using a number that's very nearly zero.
        if y_min == 0:
            y_min = 0.000001

        if y_max == 0:
            y_max = 0.000001

        # Y min
        if isinstance(y_min_wanted, str) and y_min_wanted.lower() == 'none':
            if y_min > 0:
                y_axis_min = y_min * (1 - (1 / abs(y_min) ** 1.25))
            else:
                y_axis_min = y_min * (1 + (1 / abs(y_min) ** 1.25))
        else:
            y_axis_min = float(y_min_wanted)

        # Y max
        if isinstance(y_max_wanted, str) and y_max_wanted.lower() == 'none':
            if y_max > 0:
                y_axis_max = y_max * (1 + (1 / abs(y_max) ** 1.25))
            else:
                y_axis_max = y_max * (1 - (1 / abs(y_max) ** 1.25))

        else:
            y_axis_max = float(y_max_wanted)

        plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

    except (ValueError, TypeError):
        logger['Warning'].append(
            f"[{payload['props']['name']}] Error setting axis limits for Y1. Will rely on "
            f"Matplotlib to determine limits."
        )


# =============================================================================
# this is currently unused.
def format_axis_y2_label(p_dict, k_dict, logger):
    """
    Format Y2 axis properties

    Controls the format and placement of labels for the Y2 axis.
    -----
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    font_main = p_dict.get('fontMain', 'Arial')  # Main font style

    try:
        plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])

        if p_dict['customSizeFont']:
            plt.yticks(fontname=font_main, fontsize=int(p_dict['customTickFontSize']))
        else:
            plt.yticks(fontname=font_main, fontsize=int(p_dict['tickFontSize']))

    except (KeyError, ValueError) as err:
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting axis labels: {err}"
        )


# =============================================================================
def format_best_fit_line_segments(ax, dates_to_plot, line, p_dict, logger):
    """
    Adds best fit line segments to plots

    The format_best_fit_line_segments method provides a utility to add "best fit lines" to select
    types of charts (best fit lines are not appropriate for all chart types).
    -----
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :return numpy.ndarray dates_to_plot:
    :param int line:
    :param dict p_dict: plotting parameters
    :return ax:
    :param dict logger:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Formatting best fit line segments.")
    try:
        color = p_dict.get(f'line{line}BestFitColor', '#FF0000')

        ax.plot(
            np.unique(dates_to_plot),
            np.poly1d(np.polyfit(dates_to_plot, p_dict[f'y_obs{line}'], 1))
            (np.unique(dates_to_plot)),
            color=color,
            zorder=1
        )

        return ax

    except TypeError as sub_error:
        name = payload['props']['name']
        logger['Threaddebug'].append(f"[{name}] p_dict: {p_dict}.")
        logger['Threaddebug'].append(f"[{name} dates_to_plot: {dates_to_plot}.")
        logger['Warning'].append(
            f"[{name} There is a problem with the best fit line segments settings. "
            f"Error: {sub_error}. See plugin log for more information."
        )


# =============================================================================
def format_custom_line_segments(ax, plug_dict, p_dict, k_dict, logger, orient="horiz"):
    """
    Chart custom line segments handler

    Process any custom line segments and add them to the matplotlib axes object.
    -----
    :param dict plug_dict:
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    :param str orient: orientation of custom line segments
    """

    # Plot the custom lines if needed.  Note that these need to be plotted after the legend is
    # established, otherwise some characteristics of the min/max lines will take over the legend
    # props.

    if p_dict['verboseLogging']:
        logger['Debug'].append(f"[{payload['props']['name']}] Formatting custom line segments.")
        logger['Debug'].append(f"Custom Segments Payload: {p_dict['customLineSegments']}")

    if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ("", "None"):
        try:
            # constants_to_plot will be (val, rgb) or ((val, rgb), (val, rgb))
            constants_to_plot = p_dict['customLineSegments']
            cls = ax

            # If a single tuple comes in, we need to tuple the tuple.  (a, b) --> ((a, b),)
            if not isinstance(constants_to_plot[0], tuple):
                constants_to_plot = (constants_to_plot,)

            for element in constants_to_plot:

                # ===============================  Horizontal  ================================
                if orient == 'horiz':
                    if isinstance(element, tuple):
                        cls = ax.axhline(
                            element[0],
                            color=element[1],
                            linestyle=p_dict['customLineStyle'],
                            marker='',
                            **k_dict['k_custom']
                        )

                    # If we want to promote custom line segments, we need to add them to the list
                    # that's used to calculate the Y axis limits.
                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(element[0])

                # ================================  Vertical  =================================
                elif orient == 'vert':
                    if isinstance(element, tuple):
                        cls = ax.axvline(
                            element[0],
                            color=element[1],
                            linestyle=p_dict['customLineStyle'],
                            marker='',
                            **k_dict['k_custom']
                        )

                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(element[0])

                # ==================================  Other  ==================================
                else:
                    cls = ax.axhline(
                        y=constants_to_plot[0],
                        color=constants_to_plot[1],
                        linestyle=p_dict['customLineStyle'],
                        marker='',
                        **k_dict['k_custom']
                    )

                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(constants_to_plot[0])

            return cls

        except Exception as sub_error:
            logger['Warning'].append(
                f"[{payload['props']['name']}] There is a problem with the custom line segments "
                f"settings. {sub_error}. See plugin log for more information."
            )


# =============================================================================
def format_dates(list_of_dates, logger):
    """
    Convert date strings to date objects

    Convert string representations of date values to mdate values for charting.
    -----
    :param list list_of_dates:
    :param dict logger:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Formatting dates.")
    dates_to_plot = []
    dates_to_plot_m = []

    try:
        dates_to_plot = [date_parse(obs) for obs in list_of_dates]
        dates_to_plot_m = mdate.date2num(dates_to_plot)

        return dates_to_plot_m

    except (KeyError, ValueError):
        name = payload['props']['name']
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting dates: list_of_dates = {list_of_dates}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting dates: dates_to_plot = {dates_to_plot}"
        )
        logger['Threaddebug'].append(
            f"[{name}] Problem formatting dates: dates_to_plot_m = {dates_to_plot_m}"
        )


# =============================================================================
def format_grids(p_dict, k_dict, logger):
    """
    Format matplotlib grids

    Format grids for visibility and properties.
    -----
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Formatting grids.")

    try:
        if p_dict['showxAxisGrid']:
            plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

        if p_dict['showyAxisGrid']:
            plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    except (KeyError, ValueError):
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}]Problem formatting grids: showxAxisGrid = "
            f"{p_dict['showxAxisGrid']}"
        )
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting grids: k_grid_fig = "
            f"{k_dict['k_grid_fig']}"
        )


# =============================================================================
def format_title(p_dict, k_dict, loc, align='center', logger=None):
    """
    Plot the figure's title
    -----
    :param p_dict:
    :param k_dict:
    :param loc:
    :param str align:
    :param dict logger:
    :return:
    """
    try:
        plt.suptitle(p_dict['chartTitle'], position=loc, ha=align, **k_dict['k_title_font'])
    except KeyError as sub_error:
        logger['Warning'].append(f"[{payload['props']['name']}] Title Error: {sub_error}")


# =============================================================================
def get_data(data_source, logger):
    """
    Retrieve data from CSV file.

    Reads data from source CSV file and returns a list of tuples for charting. The data are
    provided as unicode strings [('formatted date', 'observation'), ...]
    -----
    :param unicode data_source:
    :param dict logger:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Retrieving CSV data.")

    final_data = []
    now = dt.datetime.now()
    now_text = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    try:
        # Get the data
        with open(data_source, "r", encoding="utf-8") as data_file:
            csv_data = csv.reader(data_file, delimiter=',')

            # Convert the csv object to a list
            _ = [final_data.append(item) for item in csv_data]

        # Process the data a bit more for charting
        final_data = convert_the_data(final_data=final_data, data_source=data_source, logger=LOG)

        return final_data

    # If we can't find the target CSV file, we create a phony proxy which the plugin can process
    # without dying.
    except Exception as sub_error:
        final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
        logger['Warning'].append(
            f"[{payload['props']['name']}] Error downloading CSV data: {sub_error}. See plugin "
            f"log for more information."
        )

        return final_data


# =============================================================================
def hide_anomalies(data, props=True, logger=[]):
    """Detect outliers in data and replace them with 'NaN'.

    Credit: https://gist.github.com/wmlba/89bc2f4556b8ee397ca7a5017b497657#file-outlier_std-py
    -----
    :param list data:
    :param dict props:
    :param dict logger:
    """
    LOG['Debug'].append(f"[{payload['props']['name']}] Identifying and disguising anomalous data.")

    anomalies = []

    std_val = int(props.get('filterAnomalies', "0"))

    if std_val > 0:
        # Set upper and lower limit to 2 standard deviations
        data_std  = np.std(data)
        data_mean = np.mean(data)
        filter_val   = data_std * std_val

        lower_limit = data_mean - filter_val
        upper_limit = data_mean + filter_val

        # Generate outliers
        for outlier in data:
            if outlier > upper_limit or outlier < lower_limit:
                anomalies.append(outlier)

        final_data = [_ if _ not in anomalies else 'NaN' for _ in data]

        if 'NaN' in final_data:
            logger['Warning'].append(
                f"[{payload['props']['name']}] Outliers in data are hidden (greater than "
                f"{std_val} standard deviations [{filter_val}])."
            )
        value = final_data

    else:
        value = data

    return value

# =============================================================================
def make_chart_figure(width, height, p_dict):
    """
    Create the matplotlib figure object and create the main axes element.

    Create the figure object for charting and include one axes object. The method also add a few
    customizations when defining the objects.
    -----
    :param float width:
    :param float height:
    :param dict p_dict: plotting parameters
    """

    dpi = float(plt.rcParams['savefig.dpi'])
    height = float(height)
    width = float(width)

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, facecolor=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    _ = [ax.spines[spine].set_color(p_dict['spineColor'])
         for spine in ('top', 'bottom', 'left', 'right')
         ]

    return ax


# =============================================================================
def prune_data(x_data, y_data, limit, new_old, logger):  # noqa
    """
    Prune data to display subset of available data

    The prune_data() method is used to show a subset of available data. Users enter a number of
    days into a device config dialog, the method then drops any observations that are outside that
    window.
    -----
    :rtype: object
    :param list x_data:
    :param list y_data:
    :param int limit:
    :param unicode new_old:
    :param dict logger:
    :return:
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Pruning data as needed.")

    now = dt.datetime.now()
    delta = now - dt.timedelta(days=limit)
    logger['Debug'].append(
        f"[{payload['props']['name']}] Pruning chart data: {delta} through {now}."
    )

    # Convert dates from string to datetime for filters
    for i, x in enumerate(x_data):
        x_data[i] = dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f')

    # Create numpy arrays from the data
    x_obs_d = np.array(x_data)
    y_obs_d = np.array(y_data)

    # Get the indexes of the date data that fits the time window
    idx = np.where((x_obs_d >= delta) & (x_obs_d <= now))

    # Keep only the indexed observations, and put them back into lists
    final_x = x_obs_d[idx].tolist()
    final_y = y_obs_d[idx].tolist()

    # If final_x is of length zero, no observations fit the requested time
    # mask. We return empty lists so that there's something to chart.
    if len(final_x) == 0:
        logger['Warning'].append(
            f"[{payload['props']['name']}] All data outside time series limits. No observations "
            f"to return."
        )
        final_x = [dt.datetime.now()]
        final_y = [0]

    # Return dates back to string form (they get processed later by matplotlib) mdate.
    for i, x in enumerate(final_x):
        final_x[i] = dt.datetime.strftime(x, '%Y-%m-%d %H:%M:%S.%f')

    return final_x, final_y


# =============================================================================
def save(logger):
    """
    Title Placeholder

    Body placeholder
    -----
    :param logger:
    :return:
    """
    try:
        if payload['p_dict']['chartPath'] != '' and payload['p_dict']['fileName'] != '':
            plt.tight_layout()
            plt.savefig(
                f"{payload['p_dict']['chartPath']}{payload['p_dict']['fileName']}",
                **payload['k_dict']['k_plot_fig']
            )
            logger['Debug'].append(f"[{payload['props']['name']}] Chart file saved to disk.")

        else:
            logger['Warning'].append(f"[{payload['props']['name']}] Chart not saved.")

        # Note that this garbage collection may be unneeded since the process will end.
        plt.clf()
        plt.close('all')

    except RuntimeError as err:
        # There are too many observations in the CSV data.
        if "exceeds Locator.MAXTICKS" in traceback.format_exc(err):
            logger['Critical'].append(f"[{payload['props']['name']}] Chart not saved. [Too many observeations.]")
