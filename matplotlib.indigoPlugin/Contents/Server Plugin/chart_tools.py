# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Shared charting utility functions used by all chart subprocess scripts.

Provides a library of functions for reading and processing CSV data, formatting matplotlib axes, ticks, grids, titles,
legends, and best-fit lines, as well as saving finished chart images to disk. Loaded by each individual chart script
via the payload mechanism.
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
from typing import Any, Dict, List, Optional, Tuple, Union
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
LOG: Dict[str, List[str]] = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

# Unpack the payload data. The first element of the payload is the name of this script (we don't need that). As long
# as size isn't a limitation we will always send the entire payload as element 1.
payload: dict = {}
try:
    payload = json.loads(sys.argv[1].encode("utf-8"))
    LOG['Debug'].append(f"[{payload['props']['name']}] payload unpacked successfully.")
except IndexError:
    ...


def __init__() -> None:
    """Initialize the chart_tools module (no-op placeholder)."""


# =============================================================================
def convert_the_data(final_data: list, data_source: str, logger: dict) -> list:
    """Convert data into a form that matplotlib can understand.

    Matplotlib can't plot values like 'Open' and 'Closed', so we convert them for plotting. We do this on the fly
    and don't change the underlying data in any way. Some data can be presented that should not be charted; for
    example, the WUnderground plugin will present '-99.0' when WUnderground is not able to deliver a rational value.
    Therefore, we convert '-99.0' to NaN values.

    Args:
        final_data (list): The raw chart data rows to be converted.
        data_source (str): The path to the CSV data source file (used in log messages).
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        list: The converted data with non-numeric and sentinel values replaced by 'NaN'.
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] "
                        f"Coercing chart data to chart-able values where needed.")
    converter = {
        'true': 1, 'false': 0, 'open': 1, 'closed': 0, 'on': 1, 'off': 0, 'locked': 1,
        'unlocked': 0, 'up': 1, 'down': 0, '1': 1, '0': 0, 'heat': 1, 'armed': 1, 'disarmed': 0,
        '- data unavailable -': 'nan', 'data unavailable': 'nan', 'NA': 'nan', 'N/A': 'nan'
    }
    now = dt.datetime.now()
    now_text = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

    # =============================================================================
    def is_number(s: Any) -> bool:
        """Return True if the given value can be interpreted as a number.

        Attempts to parse the value as a float or as a Unicode numeric character. Returns False if neither
        interpretation succeeds.

        Args:
            s: The value to test for numeric interpretability.

        Returns:
            bool: True if the value is numeric, False otherwise.
        """
        try:
            float(s)
            return True

        except ValueError:
            ...

        try:
            unicodedata.numeric(s)
            return True

        except (TypeError, ValueError):
            ...

        return False

    for value in final_data:
        if value[1].lower() in converter:
            value[1] = converter[value[1].lower()]

    # We have converted all nonsense numbers to '-99.0'. Let's replace those with 'NaN' for charting.
    final_data = [[n[0], 'NaN'] if n[1] == '-99.0' else n for n in final_data]

    # ================================ Process CSV ================================
    # If the CSV file is missing data or is completely empty, we generate a phony one and alert the user. This helps
    # avoid nasty surprises down the line.

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

    # Data element contains an invalid string element. All proper strings like 'off' and 'true' should already have
    # been converted with self.convert_the_data() above.
    final_data = [(item[0], 'NaN') if not is_number(item[1]) else item for item in final_data]

    # Put the header row back in.
    final_data.insert(0, headers)

    return final_data


# =============================================================================
def eval_expr(expr: str) -> Union[int, float]:
    """Parse and evaluate a mathematical expression string safely.

    Parses the expression using the AST module and delegates evaluation to eval_(), which supports
    basic arithmetic operators without using Python's built-in eval().

    Args:
        expr (str): A mathematical expression string to evaluate (e.g., "2 + 3 * 4").

    Returns:
        int | float: The numeric result of evaluating the expression.
    """
    # LOG['Debug'].append(f"[{payload['props']['name']}] Evaluating expressions.")
    return eval_(ast.parse(expr, mode='eval').body)


# =============================================================================
def eval_(mode: ast.AST) -> Union[int, float]:
    """Recursively evaluate an AST node as a mathematical expression.

    Handles numeric constants, binary operations (add, subtract, multiply, divide, power, XOR), and
    unary negation. Raises TypeError for unsupported node types.

    Args:
        mode (ast.AST): An AST node representing a constant, binary operation, or unary operation.

    Returns:
        int | float: The numeric result of the evaluated AST node.

    Raises:
        TypeError: If the AST node type is not supported.
    """
    operators = {
        ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
        ast.BitXor: op.xor, ast.USub: op.neg
    }

    if isinstance(mode, ast.Constant):  # <number> or other constant
        value = mode.value
    elif isinstance(mode, ast.BinOp):  # <left> <operator> <right>
        value = operators[type(mode.op)](eval_(mode=mode.left), eval_(mode=mode.right))
    elif isinstance(mode, ast.UnaryOp):  # <operator> <operand> e.g., -1
        value = operators[type(mode.op)](eval_(mode=mode.operand))
    else:
        raise TypeError(mode)

    return value


# =============================================================================
def format_axis(ax_obj: Any) -> None:
    """Set font, color, and grid properties on all cells of a matplotlib table object.

    Applies the configured face color, font color, font name, font size, and line width to each cell
    in the table. Also controls whether cell edges are drawn based on the calendarGrid preference.
    Note that this method purposefully accesses protected members of the _text class.

    Args:
        ax_obj (matplotlib.table.Table): The matplotlib table object whose cells will be formatted.
    """

    LOG['Debug'].append(f"[{payload['props']['name']}] Setting axis properties.")
    ax_props = ax_obj.properties()
    ax_cells = ax_props['children']
    for cell in ax_cells:
        cell.set_facecolor(payload['p_dict']['faceColor'])
        cell._text.set_color(payload['p_dict']['fontColor'])  # noqa
        cell._text.set_fontname(payload['p_dict']['fontMain'])  # noqa
        cell._text.set_fontsize(int(payload['props']['fontSize']))  # noqa
        cell.set_linewidth(int(plt.rcParams['lines.linewidth']))

        # This may not be supportable without including fonts with the plugin.
        # cell._text.set_fontstretch(1000)

        # Controls grid display
        if payload['props'].get('calendarGrid', True):
            cell.set_edgecolor(payload['p_dict']['spineColor'])
        else:
            cell.set_edgecolor(payload['p_dict']['faceColor'])


# =============================================================================
def format_axis_x_label(dev: Any, p_dict: dict, k_dict: dict, logger: dict) -> None:  # noqa
    """Format X-axis label visibility and tick properties.

    Applies font name, font size, and rotation to X-axis tick labels. If a legend is displayed,
    suppresses the X-axis label to prevent the two elements from competing for space. Logs a
    debug message if the label is suppressed.

    Args:
        dev (dict): Device properties dictionary (passed by Indigo, may not be used directly).
        p_dict (dict): Plotting parameters dictionary containing font, tick, and label settings.
        k_dict (dict): Plotting kwargs dictionary containing pre-built matplotlib keyword args.
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """
    try:
        font_main           = p_dict.get('fontMain', 'Arial')  # Main font style
        font_size           = int(p_dict.get('tickFontSize', '8'))  # Main font size
        custom_size_font    = p_dict.get('customSizeFont', False)  # Use custom font sizes?  Bool
        custom_axis_label_x = p_dict.get('customAxisLabelX', '')
        custom_font_size    = int(p_dict.get('customTickFontSize', '8'))
        rotate              = int(p_dict.get('xAxisRotate', 0))
        show_legend         = p_dict.get('showLegend', False)  # Show legend?  Bool

        h_align = {'-90': 'left', '-45': 'left', '0': 'center', '45': 'right', '90': 'right'}

        # The label of the X axis ticks (not the axis label)
        if custom_size_font:
            plt.xticks(
                fontname=font_main, fontsize=custom_font_size, rotation=rotate,
                ha=h_align[str(rotate)]
            )
        else:
            plt.xticks(
                fontname=font_main, fontsize=font_size, rotation=rotate, ha=h_align[str(rotate)]
            )

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

    except RuntimeError:
        # if "exceeds Locator.MAXTICKS" in traceback.format_exc(err):
        if "exceeds Locator.MAXTICKS" in traceback.format_exc():  # removes payload
            logger['Critical'].append(
                f"[{payload['props']['name']}] Chart data will produce too many X axis ticks. "
                f"Check source data."
            )


# =============================================================================
def format_axis_x_min_max(p_dict: dict, logger: dict) -> None:
    """Set explicit minimum and maximum bounds for the X axis.

    Reads the desired min/max from p_dict and applies them via plt.xlim(). When a bound is set to
    'none', a small padding is computed automatically from the data range. Setting limits before
    plotting disables autoscaling, so this method uses a nudge-from-zero trick to avoid degenerate
    limits when the data minimum or maximum is exactly zero.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'data_array', 'xAxisMin', and 'xAxisMax'.
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """

    try:

        x_min = min(p_dict['data_array'])
        x_max = max(p_dict['data_array'])
        x_min_wanted = p_dict['xAxisMin']
        x_max_wanted = p_dict['xAxisMax']

        # Since the min / max is used here only for chart boundaries, we "trick" Matplotlib by using a number that's
        # very nearly zero.
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
def format_axis_x_scale(x_axis_bins: str, logger: dict) -> None:
    """Configure the major and minor locators for a date-based X axis.

    Maps a human-readable bin name (e.g., 'hourly', 'daily', 'weekly') to the appropriate matplotlib
    date locators for both major and minor ticks. Assumes a date-based X axis.

    Args:
        x_axis_bins (str): The desired tick interval bin name. Supported values include
            'quarter-hourly', 'half-hourly', 'hourly', 'hourly_2', 'hourly_4', 'hourly_8',
            'hourly_12', 'daily', 'weekly', 'monthly', and 'yearly'.
        logger (dict): The logging message dictionary for appending warnings and debug info.
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
            plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=8))
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
def format_axis_x_ticks(ax: Any, p_dict: dict, k_dict: dict, logger: dict) -> Optional[Any]:
    """Format X-axis tick marks, date formatter, and scale locators.

    Applies major and minor tick parameters to the X axis, sets the date formatter from
    p_dict['xAxisLabelFormat'], and calls format_axis_x_scale() to configure the tick locator
    interval. If the label format is set to 'None', tick labels are hidden entirely. Only
    applies tick formatting when a date-based label format key is present in p_dict.

    Args:
        ax (matplotlib.axes.AxesSubplot): The axes object to format.
        p_dict (dict): Plotting parameters dictionary containing 'xAxisLabelFormat' and 'xAxisBins'.
        k_dict (dict): Plotting kwargs dictionary containing 'k_major_x' and 'k_minor_x' entries.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        matplotlib.axes.AxesSubplot: The formatted axes object, or None if an exception occurs.
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
def format_axis_y_ticks(p_dict: dict, k_dict: dict, logger: dict) -> None:
    """Apply custom Y-axis tick locations and labels if configured.

    Reads custom tick mark values and labels from p_dict. If neither is set, returns without
    making changes. If tick locations are provided but labels are empty, the locations are also
    used as labels. Replaces the default matplotlib Y tick marks and labels with the custom values.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'customTicksY' and 'customTicksLabelY'.
        k_dict (dict): Plotting kwargs dictionary (passed through, not directly used in this function).
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """

    try:
        custom_ticks_marks = [float(_) for _ in p_dict['customTicksY'].split(',')]
        custom_ticks_labels = list(p_dict['customTicksLabelY'].split(','))
        # Get the default tick values and labels (which we'll replace as needed.)
        marks, labels = plt.yticks()

        # If the user has not set custom tick values or labels, we're done.
        if len(custom_ticks_marks) == 0 and len(custom_ticks_labels)  == 0:
            return

        # If tick locations defined but tick labels are empty, let's use the tick locations as the tick labels
        if len(custom_ticks_marks) > 0 and len(custom_ticks_labels)  == 0:
            custom_ticks_labels = custom_ticks_marks

        # Replace default Y tick values with the custom ones.
        if custom_ticks_marks not in ('none', ''):
            marks = custom_ticks_marks

        # Replace the default Y tick labels with the custom ones.
        if custom_ticks_labels not in ('none', ''):
            labels = custom_ticks_labels

        plt.yticks(marks, labels)

    except (AttributeError, KeyError, ValueError):
        logger['Threaddebug'].append(
            f"[{payload['props']['name']}] Problem formatting Y axis ticks: customAxisLabelY = "
            f"{p_dict['customAxisLabelY']}"
        )


# =============================================================================
def format_axis_y(ax: Any, p_dict: dict, k_dict: dict, logger: dict) -> Optional[Any]:
    """Format Y-axis tick parameters, number formatter, and optional Y2 mirroring.

    Applies major and minor tick parameters to the Y axis and sets a fixed-precision number
    formatter. Optionally mirrors Y-axis tick labels on the right side (Y2), and can suppress
    the left-side labels if the user wants Y2-only display.

    Args:
        ax (matplotlib.axes.AxesSubplot): The axes object to format.
        p_dict (dict): Plotting parameters dictionary containing 'yAxisPrecision', 'yMirrorValues',
            and 'yMirrorValuesAlsoY1'.
        k_dict (dict): Plotting kwargs dictionary containing 'k_major_y' and 'k_minor_y' entries.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        matplotlib.axes.AxesSubplot: The formatted axes object, or None if an exception occurs.
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
            ...

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
def format_axis_y1_label(p_dict: dict, k_dict: dict, logger: dict) -> None:
    """Format the Y1 axis label text, font, and tick label properties.

    Sets the Y-axis label text and applies the configured font name, font size, and rotation to
    Y-axis tick labels. Uses custom font sizes when the customSizeFont preference is enabled.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'customAxisLabelY', 'fontMain',
            'customSizeFont', 'customTickFontSize', 'tickFontSize', and 'yAxisRotate'.
        k_dict (dict): Plotting kwargs dictionary containing 'k_y_axis_font' entry.
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """

    font_main = p_dict.get('fontMain', 'Arial')  # Main font style
    rotate = int(p_dict.get('yAxisRotate', 0))
    v_align = {'-90': 'center', '-45': 'bottom', '0': 'center', '45': 'top', '90': 'center'}

    try:
        plt.ylabel(p_dict.get('customAxisLabelY', ''), **k_dict['k_y_axis_font'])

        if p_dict['customSizeFont']:
            plt.yticks(
                fontname=font_main, fontsize=int(p_dict['customTickFontSize']), rotation=rotate,
                va=v_align[str(rotate)]
            )
        else:
            plt.yticks(
                fontname=font_main, fontsize=int(p_dict['tickFontSize']), rotation=rotate,
                va=v_align[str(rotate)]
            )

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
def format_axis_y1_min_max(p_dict: dict, logger: dict) -> None:
    """Set explicit minimum and maximum bounds for the Y1 axis.

    Reads the desired min/max from p_dict and applies them via plt.ylim(). When a bound is set to
    'none', a small padding is computed automatically from the data range. Setting limits before
    plotting disables autoscaling, so this method uses a nudge-from-zero trick to avoid degenerate
    limits when the data minimum or maximum is exactly zero.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'data_array', 'yAxisMin', and 'yAxisMax'.
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """

    try:

        y_min = min(p_dict['data_array'])
        y_max = max(p_dict['data_array'])
        y_min_wanted = p_dict['yAxisMin']
        y_max_wanted = p_dict['yAxisMax']

        # Since the min / max is used here only for chart boundaries, we "trick" Matplotlib by using a number that's
        # very nearly zero.
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
def format_best_fit_line_segments(ax: Any, dates_to_plot: Any, line: int, p_dict: dict, logger: dict) -> Optional[Any]:
    """Add a polynomial best-fit line overlay to the given axes.

    Computes a first-degree polynomial fit (linear regression) over the provided date values and
    corresponding Y observations, then plots the result as a line on the axes. Best-fit lines are
    not appropriate for all chart types.

    Args:
        ax (matplotlib.axes.AxesSubplot): The axes object to plot the best-fit line on.
        dates_to_plot (numpy.ndarray): Array of numeric date values used as the X axis for the fit.
        line (int): The line series number used to look up the color and Y data in p_dict.
        p_dict (dict): Plotting parameters dictionary containing the Y observations and best-fit
            line color keyed by line number (e.g., 'y_obs1', 'line1BestFitColor').
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        matplotlib.axes.AxesSubplot: The axes object with the best-fit line added, or None on error.
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
def format_custom_line_segments(ax: Any, plug_dict: dict, p_dict: dict, k_dict: dict, logger: dict, orient: str = "horiz") -> Optional[Any]:
    """Draw configured custom horizontal or vertical reference lines on the axes.

    Reads custom line segment definitions from p_dict and draws them as axhline (horizontal) or
    axvline (vertical) overlays using the stored color and style settings. If the
    promoteCustomLineSegments preference is enabled, the line values are also appended to
    p_dict['data_array'] so they influence axis auto-scaling.

    Args:
        ax (matplotlib.axes.AxesSubplot): The axes object to draw custom lines on.
        plug_dict (dict): Plugin preferences dictionary, checked for 'promoteCustomLineSegments'.
        p_dict (dict): Plotting parameters dictionary containing 'enableCustomLineSegments',
            'customLineSegments', 'customLineStyle', and 'data_array'.
        k_dict (dict): Plotting kwargs dictionary containing the 'k_custom' entry.
        logger (dict): The logging message dictionary for appending warnings and debug info.
        orient (str): Orientation of the custom line segments. Accepts 'horiz' (default) or 'vert'.

    Returns:
        matplotlib.lines.Line2D | None: The last drawn line artist, or None if no lines were drawn
            or an exception occurred.
    """
    # Note that these need to be plotted after the legend is established, otherwise some characteristics of the min/max
    # lines will take over the legend props.

    if p_dict['verboseLogging']:
        logger['Debug'].append(f"[{payload['props']['name']}] Formatting custom line segments.")
        logger['Debug'].append(f"Custom Segments Payload: {p_dict['customLineSegments']}")

    if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ("", "None"):
        try:
            # constants_to_plot will be (val, rgb) or ((val, rgb), (val, rgb))
            constants_to_plot = p_dict['customLineSegments']
            cls = ax

            # If a single list comes in, we need to list the list.  (a, b) --> ((a, b),)
            if not any(isinstance(el, list) for el in constants_to_plot):
                constants_to_plot = [constants_to_plot, ]

            for element in constants_to_plot:
                # ===============================  Horizontal  ================================
                if orient == 'horiz':
                    # if isinstance(element, tuple):
                    cls = ax.axhline(
                        element[0],
                        color=element[1],
                        linestyle=p_dict['customLineStyle'],
                        marker='',
                        **k_dict['k_custom']
                    )

                    # If we want to promote custom line segments, we need to add them to the list that's used to
                    # calculate the Y axis limits.
                    if plug_dict.get('promoteCustomLineSegments', False):
                        p_dict['data_array'].append(element[0])

                # ================================  Vertical  =================================
                elif orient == 'vert':
                    # if isinstance(element, tuple):
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
def format_dates(list_of_dates: list, logger: dict) -> Optional[np.ndarray]:
    """Convert a list of date strings to matplotlib numeric date values.

    Parses each date string using dateutil and converts the resulting datetime objects to
    matplotlib date numbers via mdate.date2num(), which are the values expected by matplotlib
    for date-based X axes.

    Args:
        list_of_dates (list): A list of date strings to parse and convert.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        numpy.ndarray | None: An array of matplotlib numeric date values, or None if an error occurs.
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
def format_grids(p_dict: dict, k_dict: dict, logger: dict) -> None:
    """Enable X and/or Y axis grid lines based on the configured preferences.

    Checks the showxAxisGrid and showyAxisGrid flags in p_dict and enables the corresponding
    matplotlib grid lines using the style properties from k_dict.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'showxAxisGrid' and 'showyAxisGrid'.
        k_dict (dict): Plotting kwargs dictionary containing the 'k_grid_fig' entry.
        logger (dict): The logging message dictionary for appending warnings and debug info.
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
def format_title(p_dict: dict, k_dict: dict, loc: Tuple[float, float], align: str = 'center', logger: Optional[dict] = None) -> None:
    """Render the chart's figure-level title using plt.suptitle().

    Reads the title text from p_dict['chartTitle'] and renders it at the specified figure
    position using the title font kwargs from k_dict.

    Args:
        p_dict (dict): Plotting parameters dictionary containing 'chartTitle'.
        k_dict (dict): Plotting kwargs dictionary containing the 'k_title_font' entry.
        loc (tuple): A (x, y) tuple specifying the title position in figure coordinates.
        align (str): Horizontal alignment of the title text. Defaults to 'center'.
        logger (dict): The logging message dictionary for appending warnings and debug info.
    """
    try:
        plt.suptitle(p_dict['chartTitle'], position=loc, ha=align, **k_dict['k_title_font'])
    except KeyError as sub_error:
        logger['Warning'].append(f"[{payload['props']['name']}] Title Error: {sub_error}")


# =============================================================================
def get_data(data_source: str, logger: dict) -> list:
    """Read and return chart data from a CSV file.

    Opens the CSV file at data_source, reads all rows, and passes the data through convert_the_data()
    for normalization. If the file cannot be read, returns a minimal two-row proxy dataset and logs
    a warning so that downstream chart code does not crash.

    Args:
        data_source (str): The filesystem path to the CSV data file to read.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        list: A list of rows (as lists) in the form [['timestamp', 'placeholder'], ...], with
            non-numeric and sentinel values normalized to 'NaN'.
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

    # If we can't find the target CSV file, we create a phony proxy which the plugin can process without dying.
    except Exception as sub_error:
        final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
        logger['Warning'].append(
            f"[{payload['props']['name']}] Error downloading CSV data: {sub_error}. See plugin "
            f"log for more information."
        )

        return final_data


# =============================================================================
def hide_anomalies(data: Any = None, props: dict = None, logger: dict = None) -> Union[list, Any]:
    """Detect outliers in data and replace them with 'NaN'.

    Computes the mean and standard deviation of the input data and replaces any values that fall
    outside the configured number of standard deviations with 'NaN'. If the filterAnomalies
    preference is 0 or not set, the data is returned unchanged.

    Credit: https://gist.github.com/wmlba/89bc2f4556b8ee397ca7a5017b497657#file-outlier_std-py

    Args:
        data (tuple): The sequence of numeric values to inspect for anomalies.
        props (dict): Device properties dictionary containing the 'filterAnomalies' threshold.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        list | tuple: The data with outliers replaced by 'NaN', or the original data if filtering
            is disabled.
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
def make_chart_figure(width: Union[int, float], height: Union[int, float], p_dict: dict) -> Any:
    """Create the matplotlib figure and primary axes object for a chart.

    Constructs a single-subplot figure sized in inches based on the given pixel dimensions and the
    current DPI setting. Applies the configured face color and spine color to the axes, and adds a
    small margin around the plot area.

    Args:
        width (float): The desired chart width in pixels.
        height (float): The desired chart height in pixels.
        p_dict (dict): Plotting parameters dictionary containing 'faceColor' and 'spineColor'.

    Returns:
        matplotlib.axes.AxesSubplot: The configured primary axes object.
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
def prune_data(x_data: list, y_data: list, limit: Union[int, float], new_old: str, logger: dict) -> Tuple[list, list]:  # noqa
    """Trim data to only include observations within a recent time window.

    Filters x_data and y_data to keep only the observations that fall within the past `limit` days
    from now. If no observations remain after filtering, returns a single synthetic observation at
    the current time with value 0 and logs a warning.

    Args:
        x_data (list): A list of timestamp strings in '%Y-%m-%d %H:%M:%S.%f' format.
        y_data (list): A list of corresponding Y values parallel to x_data.
        limit (int): The number of days back from now to retain observations.
        new_old (str): Unused parameter passed through from the caller.
        logger (dict): The logging message dictionary for appending warnings and debug info.

    Returns:
        tuple: A two-element tuple of (final_x, final_y), each a list of observations within the
            time window, with timestamps returned as '%Y-%m-%d %H:%M:%S.%f' strings.
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

    # If final_x is of length zero, no observations fit the requested time mask. We return empty lists so that there's
    # something to chart.
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
def save(logger: dict) -> None:
    """Save the completed matplotlib figure to disk and release figure resources.

    Applies tight layout and subplot margin adjustments appropriate for the chart type, then saves
    the figure to the path and filename specified in the payload. Logs a warning if the chart is not
    saved due to missing path or filename. Clears and closes the figure to free memory. Logs a
    critical error if the chart exceeds matplotlib's MAXTICKS limit.

    Args:
        logger (dict): The logging message dictionary for appending warnings, debug info, and
            critical errors.
    """
    try:
        top_margin    = 0.9
        bottom_margin = 0.2
        if payload['props']['chart_type'] == 'calendar':
            bottom_margin = 0.34
        elif payload['props']['chart_type'] == 'composite forecast':
            top_margin = 0.93
            bottom_margin = 0.05

        if payload['p_dict']['chartPath'] != '' and payload['p_dict']['fileName'] != '':
            plt.tight_layout()
            plt.subplots_adjust(top=top_margin, bottom=bottom_margin)
            plt.savefig(
                f"{payload['p_dict']['chartPath']}{payload['p_dict']['fileName']}",
                **payload['k_dict']['k_plot_fig']
            )
            logger['Debug'].append(f"[{payload['props']['name']}] Chart file saved to disk.")

        else:
            if payload['props']['isChart']:
                logger['Warning'].append(f"[{payload['props']['name']}] Chart not saved.")

        # Note that this garbage collection may be unneeded since the process will end.
        plt.clf()
        plt.close('all')

    except RuntimeError as err:
        # There are too many observations in the CSV data.
        # if "exceeds Locator.MAXTICKS" in traceback.format_exc(err):
        if "exceeds Locator.MAXTICKS" in traceback.format_exc():  # removes payload
            logger['Critical'].append(f"[{payload['props']['name']}] Chart not saved. [Too many observations.]")
