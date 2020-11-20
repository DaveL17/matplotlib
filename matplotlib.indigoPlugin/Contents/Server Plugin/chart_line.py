#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the line charts
All steps required to generate line charts.
-----

"""

import ast
import csv
import datetime as dt
from dateutil.parser import parse as date_parse
import itertools
import numpy as np
import operator as op
import sys
import pickle
import unicodedata

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdate
import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave

payload = chart_tools.payload
p_dict = payload['p_dict']
k_dict = payload['k_dict']

try:

    def __init__():
        pass

    # =============================================================================
    def convert_the_data(final_data, data_source):
        """
        Convert data into form that matplotlib can understand
        Matplotlib can't plot values like 'Open' and 'Closed', so we convert them for
        plotting. We do this on the fly and we don't change the underlying data in any
        way. Further, some data can be presented that should not be charted. For
        example, the WUnderground plugin will present '-99.0' when WUnderground is not
        able to deliver a rational value. Therefore, we convert '-99.0' to NaN values.
        -----
        :param list final_data: the data to be charted.
        :param unicode data_source:
        """

        converter = {'true': 1, 'false': 0, 'open': 1, 'closed': 0, 'on': 1, 'off': 0, 'locked': 1,
                     'unlocked': 0, 'up': 1, 'down': 0, '1': 1, '0': 0, 'heat': 1, 'armed': 1, 'disarmed': 0}
        now       = dt.datetime.now()
        now_text  = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

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
            chart_tools.log['Warning'].append(u'CSV file is empty. File: {0}'.format(data_source))

        # ===================== CSV File has Headers but no Data ======================
        # Adds one observation. Length of CSV file goes from one to two.
        if len(final_data) < 2:
            final_data.append((now_text, 0))
            chart_tools.log['Warning'].append(u'CSV file does not have sufficient information to make a useful plot. '
                                  u'File: {0}'.format(data_source))

        # =============================== Malformed CSV ===============================
        # Test to see if any data element is a valid numeric and replace it with 'NaN'
        # if it isn't.

        # Preserve the header row.
        _headers = final_data[0]
        del final_data[0]

        # Data element contains an invalid string element. All proper strings like
        # 'off' and 'true' should already have been converted with
        # convert_the_data() above.
        final_data = [(item[0], 'NaN') if not is_number(item[1]) else item for item in final_data]

        # Put the header row back in.
        final_data.insert(0, _headers)

        return final_data

    # =============================================================================
    def eval_expr(expr_to_eval):

        def eval_(mode):
            operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
                         ast.BitXor: op.xor, ast.USub: op.neg}

            if isinstance(mode, ast.Num):  # <number>
                return mode.n
            elif isinstance(mode, ast.BinOp):  # <left> <operator> <right>
                return operators[type(mode.op)](eval_(mode.left), eval_(mode.right))
            elif isinstance(mode, ast.UnaryOp):  # <operator> <operand> e.g., -1
                return operators[type(mode.op)](eval_(mode.operand))
            else:
                raise TypeError(mode)

        return eval_(ast.parse(expr_to_eval, mode='eval').body)

    # =============================================================================
    def format_axis_x_scale(x_axis_bins):
        """
        Format X axis scale based on user setting
        The format_axis_x_scale() method sets the bins for the X axis. Presently, we
        assume a date-based X axis.
        -----
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
            pass

    # =============================================================================
    def format_axis_y1_min_max(p_dict):
        """
        Format Y1 axis range limits
        Setting the limits before the plot turns off autoscaling, which causes the
        limit that's not set to behave weirdly at times. This block is meant to
        overcome that weirdness for something more desirable.
        -----
        :param dict p_dict: plotting parameters
        """

        try:

            y_min        = min(p_dict['data_array'])
            y_max        = max(p_dict['data_array'])
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
            chart_tools.log['Threaddebug'].append(u"Problem formatting Y1 Min/Max: yAxisMax.")

    # =============================================================================
    def format_axis_y_ticks(p_dict):
        """
        Format Y axis tick marks
        Controls the format and placement of Y ticks.
        -----
        :param dict p_dict: plotting parameters
        """

        custom_ticks_marks  = p_dict['customTicksY'].strip()
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
                labels = [u"{0}".format(_.strip()) for _ in custom_ticks_labels.split(",")]

            plt.yticks(marks, labels)

        except (KeyError, ValueError):
            chart_tools.log['Threaddebug'].append(u"Problem formatting Y axis ticks: customAxisLabelY.")

    # =============================================================================
    def format_best_fit_line_segments(ax, dates_to_plot, line, p_dict):
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
        """

        try:
            color = p_dict.get('line{0}BestFitColor'.format(line), '#FF0000')

            ax.plot(np.unique(dates_to_plot),
                    np.poly1d(np.polyfit(dates_to_plot, p_dict['y_obs{0}'.format(line)], 1))(np.unique(dates_to_plot)),
                    color=color,
                    zorder=1
                    )

            return ax

        except TypeError as sub_error:
            chart_tools.log['Warning'].append(u"There is a problem with the best fit line segments settings. Error: {0}. "
                                  u"See plugin log for more information.".format(sub_error))

    # =============================================================================
    def format_custom_line_segments(ax, plug_dict, p_dict, k_dict):
        """
        Chart custom line segments handler
        Process any custom line segments and add them to the
        matplotlib axes object.
        -----
        :param dict plug_dict:
        :param class 'matplotlib.axes.AxesSubplot' ax:
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        """

        # Plot the custom lines if needed.  Note that these need to be plotted after
        # the legend is established, otherwise some of the characteristics of the
        # min/max lines will take over the legend props.

        if p_dict['enableCustomLineSegments'] and \
                p_dict['customLineSegments'] not in ("", "None"):

            try:
                constants_to_plot = ast.literal_eval(p_dict['customLineSegments'])

                cls = ax

                for _element in constants_to_plot:
                    if type(_element) == tuple:
                        cls = ax.axhline(y=_element[0],
                                         color=_element[1],
                                         linestyle=p_dict['customLineStyle'],
                                         marker='',
                                         **k_dict['k_custom']
                                         )

                        # If we want to promote custom line segments, we need to add them to the list that's used to
                        # calculate the Y axis limits.
                        if plug_dict['prefs'].get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(_element[0])
                    else:
                        cls = ax.axhline(y=constants_to_plot[0],
                                         color=constants_to_plot[1],
                                         linestyle=p_dict['customLineStyle'],
                                         marker='',
                                         **k_dict['k_custom']
                                         )

                        if plug_dict['prefs'].get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(constants_to_plot[0])

                return cls

            except Exception as sub_error:
                chart_tools.log['Warning'].append(u"There is a problem with the custom line segments settings. {0}. See plugin "
                                      u"log for more information.".format(sub_error))

                return ax

    # =============================================================================
    def format_dates(list_of_dates):
        """
        Convert date strings to date objects
        Convert string representations of date values to values to mdate values for
        charting.
        -----
        :param list list_of_dates:
        """

        try:
            dates_to_plot = [date_parse(obs) for obs in list_of_dates]
            dates_to_plot_m = mdate.date2num(dates_to_plot)

            return dates_to_plot_m

        except (KeyError, ValueError):
            chart_tools.log['Threaddebug'].append(u"Problem formatting dates.")

    # =============================================================================
    def prune_data(x_data, y_data, day_limit):
        """
        Prune data to display subset of available data
        The prune_data() method is used to show a subset of available data. Users
        enter a number of days into a device config dialog, the method then drops
        any observations that are outside that window.
        -----
        :param list x_data:
        :param list y_data:
        :param int day_limit:
        :return:
        """

        now   = dt.datetime.now()
        delta = now - dt.timedelta(days=day_limit)
        chart_tools.log['Debug'].append(u"Pruning chart data: {0} through {1}.".format(delta, now))

        # Convert dates from string to datetime for filters
        for _, x in enumerate(x_data):
            x_data[_] = dt.datetime.strptime(x, '%Y-%m-%d %H:%M:%S.%f')

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
            chart_tools.log['Warning'].append(u"All data outside time series limits. No observations to return.")
            final_x = [dt.datetime.now()]
            final_y = [0]

        # Convert dates back to strings (they get processed later by matplotlib
        # mdate.
        for _, x in enumerate(final_x):
            final_x[_] = dt.datetime.strftime(x, '%Y-%m-%d %H:%M:%S.%f')

        return final_x, final_y

    # =============================================================================
    def get_data(data_source):
        """
        Retrieve data from CSV file.
        Reads data from source CSV file and returns a list of tuples for charting. The
        data are provided as unicode strings [('formatted date', 'observation'), ...]
        -----
        :param unicode data_source:
        """

        final_data = []
        # now        = dt.datetime.now()
        # now_text   = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

        try:
            # Get the data
            with open(data_source, "r") as data_file:
                csv_data = csv.reader(data_file, delimiter=',')

                # Convert the csv object to a list
                [final_data.append(item) for item in csv_data]

            # Process the data a bit more for charting
            final_data, convert_the_data(final_data, data_source)

            return final_data

        # If we can't find the target CSV file, we create a phony proxy which the plugin
        # can process without dying.
        except IOError as err:
            chart_tools.log['Critical'].append(u'{0}}'.format(err))

            return final_data


    p_dict['backgroundColor'] = chart_tools.fix_rgb(c=p_dict['backgroundColor'])
    p_dict['faceColor'] = chart_tools.fix_rgb(c=p_dict['faceColor'])
    line_colors = []

    dpi = plt.rcParams['savefig.dpi']
    height = float(p_dict['chart_height'])
    width = float(p_dict['chart_width'])

    fig = plt.figure(1, figsize=(width / dpi, height / dpi))
    ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
    ax.margins(0.04, 0.05)
    [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

    # ============================== Format X Ticks ===============================
    ax.tick_params(axis='x', **k_dict['k_major_x'])
    ax.tick_params(axis='x', **k_dict['k_minor_x'])
    ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
    format_axis_x_scale(p_dict['xAxisBins'])  # Set the scale for the X axis. We assume a date.

    # If the x axis format has been set to None, let's hide the labels.
    if p_dict['xAxisLabelFormat'] == "None":
        ax.axes.xaxis.set_ticklabels([])

    # =============================== Format Y Axis ===============================
    ax.tick_params(axis='y', **k_dict['k_major_y'])
    ax.tick_params(axis='y', **k_dict['k_minor_y'])
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision']))))

    # Mirror Y axis values on Y2. Not all charts will support this option.
    try:
        if p_dict['yMirrorValues']:
            ax.tick_params(labelright=True)

            # A user may want tick labels only on Y2.
            if not p_dict['yMirrorValuesAlsoY1']:
                ax.tick_params(labelleft=False)

    except KeyError:
        pass

    for line in range(1, 9, 1):

        suppress_line = p_dict.get('suppressLine{0}'.format(line), False)

        lc_index = 'line{0}Color'.format(line)
        p_dict[lc_index] = chart_tools.fix_rgb(c=p_dict[lc_index])

        lmc_index = 'line{0}MarkerColor'.format(line)
        p_dict[lmc_index] = chart_tools.fix_rgb(c=p_dict[lmc_index])

        lbf_index = 'line{0}BestFitColor'.format(line)
        p_dict[lbf_index] = chart_tools.fix_rgb(c=p_dict[lbf_index])

        # If line color is the same as the background color, alert the user.
        if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor'] and not suppress_line:
            chart_tools.log['Warning'].append(u"[{0}] Line {1} color is the same as the background color (so you may "
                                  u"not be able to see it).".format(payload['props']['name'], line))

        # If the line is suppressed, remind the user they suppressed it.
        if suppress_line:
            chart_tools.log['Info'].append(u"[{0}] Line {1} is suppressed by user setting. You can re-enable it in the "
                               u"device configuration menu.".format(payload['props']['name'], line))

        # ============================== Plot the Lines ===============================
        # Plot the lines. If suppress_line is True, we skip it.
        if p_dict['line{0}Source'.format(line)] not in (u"", u"None") and not suppress_line:

            # Add line color to list for later use
            line_colors.append(p_dict['line{0}Color'.format(line)])

            data_path = payload['prefs']['dataPath'].encode("utf-8")
            line_source = p_dict['line{0}Source'.format(line)].encode("utf-8")
            data_column = get_data('{0}{1}'.format(data_path, line_source))

            chart_tools.log['Threaddebug'].append(u"Data for Line {0}: {1}".format(line, data_column))

            # Pull the headers
            p_dict['headers'].append(data_column[0][1])
            del data_column[0]

            # Pull the observations into distinct lists for charting.
            for element in data_column:
                p_dict['x_obs{0}'.format(line)].append(element[0])
                p_dict['y_obs{0}'.format(line)].append(float(element[1]))

            # ============================= Adjustment Factor =============================
            # Allows user to shift data on the Y axis (for example, to display multiple
            # binary sources on the same chart.)
            if payload['props']['line{0}adjuster'.format(line)] != "":
                temp_list = []
                for obs in p_dict['y_obs{0}'.format(line)]:
                    expr = u'{0}{1}'.format(obs, payload['props']['line{0}adjuster'.format(line)])
                    temp_list.append(eval_expr(expr_to_eval=expr))
                p_dict['y_obs{0}'.format(line)] = temp_list

            # ================================ Prune Data =================================
            # Prune the data if warranted
            dates_to_plot = p_dict['x_obs{0}'.format(line)]

            try:
                limit = float(payload['props']['limitDataRangeLength'])
            except ValueError:
                limit = 0

            if limit > 0:
                y_obs = p_dict['y_obs{0}'.format(line)]
                new_old = payload['props']['limitDataRange']

                prune = prune_data(dates_to_plot, y_obs, limit)
                p_dict['x_obs{0}'.format(line)], p_dict['y_obs{0}'.format(line)] = prune

            # ======================== Convert Dates for Charting =========================
            p_dict['x_obs{0}'.format(line)] = format_dates(p_dict['x_obs{0}'.format(line)])

            ax.plot_date(p_dict['x_obs{0}'.format(line)],
                         p_dict['y_obs{0}'.format(line)],
                         color=p_dict['line{0}Color'.format(line)],
                         linestyle=p_dict['line{0}Style'.format(line)],
                         marker=p_dict['line{0}Marker'.format(line)],
                         markeredgecolor=p_dict['line{0}MarkerColor'.format(line)],
                         markerfacecolor=p_dict['line{0}MarkerColor'.format(line)],
                         zorder=10,
                         **k_dict['k_line']
                         )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

            if p_dict['line{0}Fill'.format(line)]:
                ax.fill_between(p_dict['x_obs{0}'.format(line)],
                                0,
                                p_dict['y_obs{0}'.format(line)],
                                color=p_dict['line{0}Color'.format(line)],
                                **k_dict['k_fill']
                                )

            # ================================ Annotations ================================
            if p_dict['line{0}Annotate'.format(line)]:
                for xy in zip(p_dict['x_obs{0}'.format(line)], p_dict['y_obs{0}'.format(line)]):
                    ax.annotate(u"{0}".format(xy[1]),
                                xy=xy,
                                xytext=(0, 0),
                                zorder=10,
                                **k_dict['k_annotation']
                                )

    # ============================== Y1 Axis Min/Max ==============================
    # Min and Max are not 'None'.
    format_axis_y1_min_max(p_dict)

    # Transparent Chart Fill
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                       transform=ax.transAxes,
                                       facecolor=p_dict['faceColor'],
                                       zorder=1
                                       )
                     )

    # ================================== Legend ===================================
    if p_dict['showLegend']:

        # Amend the headers if there are any custom legend entries defined.
        counter = 1
        final_headers = []

        headers = [_.decode('utf-8') for _ in p_dict['headers']]

        for header in headers:
            if p_dict['line{0}Legend'.format(counter)] == "":
                final_headers.append(header)
            else:
                final_headers.append(p_dict['line{0}Legend'.format(counter)])
            counter += 1

        # Set the legend
        # Reorder the headers and colors so that they fill by row instead of by column
        num_col = int(p_dict['legendColumns'])
        iter_headers = itertools.chain(*[final_headers[i::num_col] for i in range(num_col)])
        final_headers = [_ for _ in iter_headers]

        iter_colors = itertools.chain(*[line_colors[i::num_col] for i in range(num_col)])
        final_colors = [_ for _ in iter_colors]

        legend = ax.legend(final_headers,
                           loc='upper center',
                           bbox_to_anchor=(0.5, -0.1),
                           ncol=num_col,
                           prop={'size': float(p_dict['legendFontSize'])}
                           )

        # Set legend font color
        [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]

        # Set legend line color
        num_handles = len(legend.legendHandles)
        [legend.legendHandles[_].set_color(final_colors[_]) for _ in range(0, num_handles)]

        frame = legend.get_frame()
        frame.set_alpha(0)

    for line in range(1, 9, 1):

        suppress_line = p_dict.get('suppressLine{0}'.format(line), False)

        if p_dict['line{0}Source'.format(line)] not in (u"", u"None") and not suppress_line:
            # Note that we do these after the legend is drawn so that these lines don't
            # affect the legend.

            # We need to reload the dates to ensure that they match the line being plotted
            # dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(line)])

            # =============================== Best Fit Line ===============================
            if payload['props'].get('line{0}BestFit'.format(line), False):
                format_best_fit_line_segments(ax,
                                              p_dict['x_obs{0}'.format(line)],
                                              line,
                                              p_dict,
                                              )

            [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

            # =============================== Fill Between ================================
            if p_dict['line{0}Fill'.format(line)]:
                ax.fill_between(p_dict['x_obs{0}'.format(line)],
                                0,
                                p_dict['y_obs{0}'.format(line)],
                                color=p_dict['line{0}Color'.format(line)],
                                **k_dict['k_fill']
                                )

            # =============================== Min/Max Lines ===============================
            if p_dict['plotLine{0}Min'.format(line)]:
                ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]),
                           color=p_dict['line{0}Color'.format(line)],
                           **k_dict['k_min'])
            if p_dict['plotLine{0}Max'.format(line)]:
                ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]),
                           color=p_dict['line{0}Color'.format(line)],
                           **k_dict['k_max']
                           )
            if payload['prefs'].get('forceOriginLines', True):
                ax.axhline(y=0, color=p_dict['spineColor'])

    format_custom_line_segments(ax, payload['prefs'], p_dict, k_dict)

    # =============================== Format Grids ================================
    if p_dict['showxAxisGrid']:
        plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

    if p_dict['showyAxisGrid']:
        plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    # =============================== Format Title ================================
    chart_tools.format_title(p_dict, k_dict, loc=(0.05, 0.98), align='center')

    # ============================ Format X Axis Label ============================
    if not p_dict['showLegend']:
        plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
        chart_tools.log['Threaddebug'].append(u"[{0}] No call for legend. Formatting X label.".format(payload['props']['name']))

    if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ('', 'null'):
        chart_tools.log['Debug'].append(u"[{0}] X axis label is suppressed to make room "
                            u"for the chart legend.".format(payload['props']['name']))

    # ============================ Format Y1 Axis Label ============================
    plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

    format_axis_y_ticks(p_dict)

    # Note that subplots_adjust affects the space surrounding the subplots and
    # not the fig.
    plt.subplots_adjust(top=0.90,
                        bottom=0.20,
                        left=0.10,
                        right=0.90,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save()

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    pass
