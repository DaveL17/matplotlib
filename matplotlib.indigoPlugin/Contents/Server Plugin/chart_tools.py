#! /usr/bin/env python
# -*- coding: utf-8 -*-

import ast
import csv
import datetime as dt
from dateutil.parser import parse as date_parse
import numpy as np
import operator as op
import pickle
import sys
import unicodedata

# Note the order and structure of matplotlib imports is intentional.
import matplotlib

matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
# import matplotlib.patches as patches
import matplotlib.dates as mdate
import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

# import DLFramework as Dave

# Collection of logging messages.
log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

# Unpickle the payload data. The first element of the payload is the name
# of this script and we don't need that. As long as size isn't a limitation
# we will always send the entire payload as element 1.
try:
    payload = pickle.loads(sys.argv[1])
except IndexError:
    pass

log['Debug'].append(u'payload unpickled successfully.')


def __init__():
    pass


# =============================================================================
def convert_the_data(final_data, data_source, logger):
    """
    Convert data into form that matplotlib can understand
    Matplotlib can't plot values like 'Open' and 'Closed', so we convert them for
    plotting. We do this on the fly and we don't change the underlying data in any
    way. Further, some data can be presented that should not be charted. For
    example, the WUnderground plugin will present '-99.0' when WUnderground is not
    able to deliver a rational value. Therefore, we convert '-99.0' to NaN values.
    -----
    :param logger:
    :param list final_data: the data to be charted.
    :param unicode data_source:
    """

    converter = {'true': 1, 'false': 0, 'open': 1, 'closed': 0, 'on': 1, 'off': 0, 'locked': 1,
                 'unlocked': 0, 'up': 1, 'down': 0, '1': 1, '0': 0, 'heat': 1, 'armed': 1, 'disarmed': 0}
    now = dt.datetime.now()
    now_text = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    def is_number(s):
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
        if value[1].lower() in converter.keys():
            value[1] = converter[value[1].lower()]

    # We have converted all nonsense numbers to '-99.0'. Let's replace those with
    # 'NaN' for charting.
    final_data = [[n[0], 'NaN'] if n[1] == '-99.0' else n for n in final_data]

    # ================================ Process CSV ================================
    # If the CSV file is missing data or is completely empty, we generate a phony
    # one and alert the user. This helps avoid nasty surprises down the line.

    # ============================= CSV File is Empty =============================
    # Adds header and one observation. Length of CSV file goes from zero to two.
    if len(final_data) < 1:
        final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
        logger['Warning'].append(u'CSV file is empty. File: {d}'.format(d=data_source))

    # ===================== CSV File has Headers but no Data ======================
    # Adds one observation. Length of CSV file goes from one to two.
    if len(final_data) < 2:
        final_data.append((now_text, 0))
        logger['Warning'].append(u'CSV file does not have sufficient information to make a useful plot. '
                                 u'File: {d}'.format(d=data_source))

    # =============================== Malformed CSV ===============================
    # Test to see if any data element is a valid numeric and replace it with 'NaN'
    # if it isn't.

    # Preserve the header row.
    headers = final_data[0]
    del final_data[0]

    # Data element contains an invalid string element. All proper strings like
    # 'off' and 'true' should already have been converted with
    # self.convert_the_data() above.
    final_data = [(item[0], 'NaN') if not is_number(item[1]) else item for item in final_data]

    # Put the header row back in.
    final_data.insert(0, headers)

    return final_data


# =============================================================================
def eval_expr(expr):
    return eval_(ast.parse(expr, mode='eval').body)


# =============================================================================
def eval_(mode):
    operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
                 ast.BitXor: op.xor, ast.USub: op.neg}

    if isinstance(mode, ast.Num):  # <number>
        return mode.n
    elif isinstance(mode, ast.BinOp):  # <left> <operator> <right>
        return operators[type(mode.op)](eval_(mode=mode.left), eval_(mode=mode.right))
    elif isinstance(mode, ast.UnaryOp):  # <operator> <operand> e.g., -1
        return operators[type(mode.op)](eval_(mode=mode.operand))
    else:
        raise TypeError(mode)


# =============================================================================
def fix_rgb(color):
    return r"#{c}".format(c=color.replace(' ', '').replace('#', ''))


# =============================================================================
def format_axis(ax_obj):
    """
    Set various axis properties
    Note that this method purposefully accesses protected members of the _text class.
    -----
    :param class 'matplotlib.table.Table' ax_obj: matplotlib table object
    """

    ax_props = ax_obj.properties()
    ax_cells = ax_props['child_artists']
    for cell in ax_cells:
        cell.set_facecolor(payload['p_dict']['faceColor'])
        cell._text.set_color(payload['p_dict']['fontColor'])
        cell._text.set_fontname(payload['p_dict']['fontMain'])
        cell._text.set_fontsize(int(payload['props']['fontSize']))
        cell.set_linewidth(int(plt.rcParams['lines.linewidth']))

        # TODO: This may not be supportable without including fonts with the plugin.
        # cell._text.set_fontstretch(1000)

        # Controls grid display
        if payload['props'].get('calendarGrid', True):
            cell.set_edgecolor(payload['p_dict']['spineColor'])
        else:
            cell.set_edgecolor(payload['p_dict']['faceColor'])


# =============================================================================
def format_axis_x_label(dev, p_dict, k_dict, logger):
    """
    Format X axis label visibility and properties
    If the user chooses to display a legend, we don't want an axis label because
    they will fight with each other for space.
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
                logger['Threaddebug'].append(u"[{name}] No call for legend. Formatting X "
                                             u"label.".format(name=dev['name']))

        if show_legend and custom_axis_label_x.strip(' ') not in ('', 'null'):
            logger['Debug'].append(u"[{name}] X axis label is suppressed to make room for the chart "
                                   u"legend.".format(name=dev['name']))

    except (ValueError, TypeError):
        logger['Threaddebug'].append(u"Problem formatting X labels")


# =============================================================================
def format_axis_x_scale(x_axis_bins, logger):
    """
    Format X axis scale based on user setting
    The format_axis_x_scale() method sets the bins for the X axis. Presently, we
    assume a date-based X axis.
    -----
    :param dict logger:
    :param list x_axis_bins:
    """

    try:
        if x_axis_bins == 'quarter-hourly':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 96)))
        if x_axis_bins == 'half-hourly':
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
            plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 48)))
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
        logger['Threaddebug'].append(u"Problem formatting X axis scale: x_axis_bins = {b}".format(b=x_axis_bins))


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
        ax.tick_params(axis='x', **k_dict['k_major_x'])
        ax.tick_params(axis='x', **k_dict['k_minor_x'])
        ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
        format_axis_x_scale(x_axis_bins=p_dict['xAxisBins'], logger=log)

        # If the x axis format has been set to None, let's hide the labels.
        if p_dict['xAxisLabelFormat'] == "None":
            ax.axes.xaxis.set_ticklabels([])

        return ax

    except (ValueError, TypeError):
        logger['Threaddebug'].append(u"Problem formatting X ticks: k_major_x = "
                                     u"{k}".format(k=k_dict['k_major_x']))
        logger['Threaddebug'].append(u"Problem formatting X ticks: k_minor_x = "
                                     u"{k}".format(k=k_dict['k_minor_x']))
        logger['Threaddebug'].append(u"Problem formatting X ticks: xAxisLabelFormat = "
                                     u"{k}".format(k=mdate.DateFormatter(p_dict['xAxisLabelFormat'])))
        logger['Threaddebug'].append(u"Problem formatting X ticks: xAxisBins = "
                                     u"{k}".format(k=p_dict['xAxisBins']))


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
        if custom_ticks_marks.lower() in ('none', '') and custom_ticks_labels.lower() in ('none', ''):
            return

        # If tick locations defined but tick labels are empty, let's use the tick
        # locations as the tick labels
        if custom_ticks_marks.lower() not in ('none', '') and custom_ticks_labels.lower() in ('none', ''):
            custom_ticks_labels = custom_ticks_marks

        # Replace default Y tick values with the custom ones.
        if custom_ticks_marks.lower() not in ('none', '') and not custom_ticks_marks.isspace():
            marks = [float(_) for _ in custom_ticks_marks.split(",")]

        # Replace the default Y tick labels with the custom ones.
        if custom_ticks_labels.lower() not in ('none', '') and not custom_ticks_labels.isspace():
            labels = [u"{t}".format(t=_.strip()) for _ in custom_ticks_labels.split(",")]

        plt.yticks(marks, labels)

    except (KeyError, ValueError):
        logger['Threaddebug'].append(u"Problem formatting Y axis ticks: customAxisLabelY = "
                                     u"{c}".format(c=p_dict['customAxisLabelY']))
        logger['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = "
                                     u"{k}".format(k=k_dict['k_y_axis_font']))
        logger['Threaddebug'].append(u"Problem formatting Y1 axis label: customTicksY = "
                                     u"{ct}".format(ct=p_dict['customTicksY']))


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
        ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{p}f".format(p=int(p_dict['yAxisPrecision']))))

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
        logger['Threaddebug'].append(u"Problem formatting Y ticks: k_major_y = "
                                     u"{k}".format(k=k_dict['k_major_y']))
        logger['Threaddebug'].append(u"Problem formatting Y ticks: k_minor_x = "
                                     u"{k}".format(k=k_dict['k_minor_y']))
        lbl_fmt = mtick.FormatStrFormatter(u"%.{p}f".format(p=int(p_dict['yAxisPrecision'])))
        logger['Threaddebug'].append(u"Problem formatting Y ticks: xAxisLabelFormat = "
                                     u"{f}".format(f=lbl_fmt))
        logger['Threaddebug'].append(u"Problem formatting Y ticks: yMirrorValues = "
                                     u"{mv}".format(mv=p_dict['yMirrorValues']))
        logger['Threaddebug'].append(u"Problem formatting Y ticks: yMirrorValuesAlsoY1 = "
                                     u"{mv}".format(mv=p_dict['yMirrorValuesAlsoY1']))


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
        logger['Threaddebug'].append(u"Problem formatting Y1 axis label: customAxisLabelY = "
                                     u"{c}".format(c=p_dict['customAxisLabelY']))
        logger['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = "
                                     u"{k}".format(k=k_dict['k_y_axis_font']))


# =============================================================================
def format_axis_y1_min_max(p_dict, logger):
    """
    Format Y1 axis range limits
    Setting the limits before the plot turns off autoscaling, which causes the
    limit that's not set to behave weirdly at times. This block is meant to
    overcome that weirdness for something more desirable.
    -----
    :param dict p_dict: plotting parameters
    :param dict logger:
    """

    try:

        y_min = min(p_dict['data_array'])
        y_max = max(p_dict['data_array'])
        y_min_wanted = p_dict['yAxisMin']
        y_max_wanted = p_dict['yAxisMax']

        # Since the min / max is used here only for chart boundaries, we "trick"
        # Matplotlib by using a number that's very nearly zero.
        if y_min == 0:
            y_min = 0.000001

        if y_max == 0:
            y_max = 0.000001

        # Y min
        if isinstance(y_min_wanted, unicode) and y_min_wanted.lower() == 'none':
            if y_min > 0:
                y_axis_min = y_min * (1 - (1 / abs(y_min) ** 1.25))
            else:
                y_axis_min = y_min * (1 + (1 / abs(y_min) ** 1.25))
        else:
            y_axis_min = float(y_min_wanted)

        # Y max
        if isinstance(y_max_wanted, unicode) and y_max_wanted.lower() == 'none':
            if y_max > 0:
                y_axis_max = y_max * (1 + (1 / abs(y_max) ** 1.25))
            else:
                y_axis_max = y_max * (1 - (1 / abs(y_max) ** 1.25))

        else:
            y_axis_max = float(y_max_wanted)

        plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

    except (ValueError, TypeError):
        logger['Threaddebug'].append(u"Problem formatting Y1 Min/Max: yAxisMax = "
                                     u"{ymax}".format(ymax=p_dict['yAxisMax']))
        logger['Threaddebug'].append(u"Problem formatting Y1 Min/Max: yAxisMin = "
                                     u"{ymin}".format(ymin=p_dict['yAxisMin']))
        logger['Threaddebug'].append(u"Problem formatting Y1 Min/Max: Data Min/Max = "
                                     u"{d}/{m}".format(d=min(p_dict['data_array']), m=max(p_dict['data_array'])))
        logger['Warning'].append(u"Error setting axis limits for Y1. Will rely on Matplotlib to determine limits.")


# =============================================================================
# TODO: this is currently unused.
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

    except (KeyError, ValueError):
        logger['Threaddebug'].append(u"Problem formatting Y2 axis label: customAxisLabelY2 = "
                                     u"{c}".format(c=p_dict['customAxisLabelY2']))
        logger['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = "
                                     u"{k}".format(k=k_dict['k_y_axis_font']))


# =============================================================================
def format_best_fit_line_segments(ax, dates_to_plot, line, p_dict, logger):
    """
    Adds best fit line segments to plots
    The format_best_fit_line_segments method provides a utility to add "best fit lines"
    to select types of charts (best fit lines are not appropriate for all chart
    types.
    -----
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :param 'numpy.ndarray' dates_to_plot:
    :param int line:
    :param dict p_dict: plotting parameters
    :return ax:
    :param dict logger:
    """

    try:
        color = p_dict.get('line{i}BestFitColor'.format(i=line), '#FF0000')

        ax.plot(np.unique(dates_to_plot),
                np.poly1d(np.polyfit(dates_to_plot, p_dict['y_obs{i}'.format(i=line)], 1))(np.unique(dates_to_plot)),
                color=color,
                zorder=1
                )

        return ax

    except TypeError as sub_error:
        logger['Threaddebug'].append(u"p_dict: {p}.".format(p=p_dict))
        logger['Threaddebug'].append(u"dates_to_plot: {d}.".format(d=dates_to_plot))
        logger['Warning'].append(u"There is a problem with the best fit line segments settings. Error: {s}. "
                                 u"See plugin log for more information.".format(s=sub_error))


# =============================================================================
def format_custom_line_segments(ax, plug_dict, p_dict, k_dict, logger):
    """
    Chart custom line segments handler
    Process any custom line segments and add them to the
    matplotlib axes object.
    -----
    :param dict plug_dict:
    :param class 'matplotlib.axes.AxesSubplot' ax:
    :param dict p_dict: plotting parameters
    :param dict k_dict: plotting kwargs
    :param dict logger:
    """

    # Plot the custom lines if needed.  Note that these need to be plotted after
    # the legend is established, otherwise some of the characteristics of the
    # min/max lines will take over the legend props.

    if p_dict['enableCustomLineSegments'] and \
            p_dict['customLineSegments'] not in ("", "None"):

        try:
            # constants_to_plot ill be (val, rgb) or ((val, rgb), (val, rgb))
            # constants_to_plot = ast.literal_eval(p_dict['customLineSegments'])
            constants_to_plot = p_dict['customLineSegments']

            cls = ax

            for element in constants_to_plot:

                if isinstance(element, tuple):
                    cls = ax.axhline(y=element[0],
                                     color=element[1],
                                     linestyle=p_dict['customLineStyle'],
                                     marker='',
                                     **k_dict['k_custom']
                                     )

                    # If we want to promote custom line segments, we need to add them to the list that's used to
                    # calculate the Y axis limits.
                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(element[0])
                else:
                    cls = ax.axhline(y=constants_to_plot[0],
                                     color=constants_to_plot[1],
                                     linestyle=p_dict['customLineStyle'],
                                     marker='',
                                     **k_dict['k_custom']
                                     )

                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(constants_to_plot[0])

            return cls

        except Exception as sub_error:
            logger['Warning'].append(u"There is a problem with the custom line segments settings. {s}. See plugin "
                                     u"log for more information.".format(s=sub_error))

            return ax


# =============================================================================
def format_dates(list_of_dates, logger):
    """
    Convert date strings to date objects
    Convert string representations of date values to values to mdate values for
    charting.
    -----
    :param list list_of_dates:
    :param dict logger:
    """

    dates_to_plot = []
    dates_to_plot_m = []

    try:
        dates_to_plot = [date_parse(obs) for obs in list_of_dates]
        dates_to_plot_m = mdate.date2num(dates_to_plot)

        return dates_to_plot_m

    except (KeyError, ValueError):
        logger['Threaddebug'].append(u"Problem formatting dates: list_of_dates = {d}".format(d=list_of_dates))
        logger['Threaddebug'].append(u"Problem formatting dates: dates_to_plot = {d}".format(d=dates_to_plot))
        logger['Threaddebug'].append(u"Problem formatting dates: dates_to_plot_m = {d}".format(d=dates_to_plot_m))


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

    try:
        if p_dict['showxAxisGrid']:
            plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

        if p_dict['showyAxisGrid']:
            plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    except (KeyError, ValueError):
        logger['Threaddebug'].append(u"Problem formatting grids: showxAxisGrid = {g}".format(g=p_dict['showxAxisGrid']))
        logger['Threaddebug'].append(u"Problem formatting grids: k_grid_fig = {k}".format(k=k_dict['k_grid_fig']))


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
        logger['Warning'].append(u"Title Error: {s}".format(s=sub_error))


# =============================================================================
def get_data(data_source, logger):
    """
    Retrieve data from CSV file.
    Reads data from source CSV file and returns a list of tuples for charting. The
    data are provided as unicode strings [('formatted date', 'observation'), ...]
    -----
    :param unicode data_source:
    :param dict logger:
    """

    final_data = []
    now = dt.datetime.now()
    now_text = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    try:
        # Get the data
        with open(data_source, "r") as data_file:
            csv_data = csv.reader(data_file, delimiter=',')

            # Convert the csv object to a list
            [final_data.append(item) for item in csv_data]

        # Process the data a bit more for charting
        final_data = convert_the_data(final_data=final_data, data_source=data_source, logger=log)

        return final_data

    # If we can't find the target CSV file, we create a phony proxy which the plugin
    # can process without dying.
    except Exception as sub_error:
        final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
        logger['Warning'].append(u"Error downloading CSV data: {s}. See plugin log for more "
                                 u"information.".format(s=sub_error))

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
    anomalies = []

    if props.get('filterAnomalies', False):
        # Set upper and lower limit to 2 standard deviations
        data_std  = np.std(data)
        data_mean = np.mean(data)
        four_std   = data_std * 4

        lower_limit = data_mean - four_std
        upper_limit = data_mean + four_std

        # Generate outliers
        for outlier in data:
            if outlier > upper_limit or outlier < lower_limit:
                anomalies.append(outlier)

        final_data = [_ if _ not in anomalies else 'NaN' for _ in data]

        if 'NaN' in final_data:
            logger['Warning'].append(u"[{n}] Outliers in data are hidden (greater than {std} standard "
                                     u"deviations [{a}]).".format(n=props['name'], std=4, a=four_std))
        return final_data

    else:
        return data


# =============================================================================
def make_chart_figure(width, height, p_dict):
    """
    Create the matplotlib figure object and create the main axes element.
    Create the figure object for charting and include one axes object. The method
    also add a few customizations when defining the objects.
    -----
    :param float width:
    :param float height:
    :param dict p_dict: plotting parameters
    """

    dpi = plt.rcParams['savefig.dpi']
    height = float(height)
    width = float(width)

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    return ax


# =============================================================================
def prune_data(x_data, y_data, limit, new_old, logger):
    """
    Prune data to display subset of available data
    The prune_data() method is used to show a subset of available data. Users
    enter a number of days into a device config dialog, the method then drops
    any observations that are outside that window.
    -----
    :rtype: object
    :param list x_data:
    :param list y_data:
    :param int limit:
    :param unicode new_old:
    :param dict logger:
    :return:
    """

    now = dt.datetime.now()
    delta = now - dt.timedelta(days=limit)
    logger['Debug'].append(u"Pruning chart data: {d} through {n}.".format(d=delta, n=now))

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
        logger['Warning'].append(u"All data outside time series limits. No observations to return.")
        final_x = [dt.datetime.now()]
        final_y = [0]

    # Convert dates back to strings (they get processed later by matplotlib
    # mdate.
    for i, x in enumerate(final_x):
        final_x[i] = dt.datetime.strftime(x, '%Y-%m-%d %H:%M:%S.%f')

    return final_x, final_y


# =============================================================================
def save(logger):
    try:
        if payload['p_dict']['chartPath'] != '' and payload['p_dict']['fileName'] != '':
            plt.savefig(u'{p}{f}'.format(p=payload['p_dict']['chartPath'],
                                         f=payload['p_dict']['fileName']),
                        **payload['k_dict']['k_plot_fig']
                        )
            logger['Debug'].append(u"Chart {name} saved.".format(name=payload['p_dict']['fileName']))
        # Note that this garbage collection may be unneeded since the process will end.
        plt.clf()
        plt.close('all')

    except RuntimeError as err:
        if "exceeds Locator.MAXTICKS" in err:
            logger['critical'].append(u"Chart not saved (too many observations to plot. Check source data.")
