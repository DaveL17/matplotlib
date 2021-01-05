#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the calendar charts
Given the unique nature of calendar charts, we use a separate method to
construct them.
-----

"""

# Built-in Modules
import calendar
import datetime as dt
import pickle
import sys
import traceback

# Third-party Modules
# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
import matplotlib.pyplot as plt

# My modules
import chart_tools

log        = chart_tools.log
payload    = chart_tools.payload
props      = payload['props']
chart_name = props['name']
p_dict     = payload['p_dict']
plug_dict  = payload['prefs']

log['Threaddebug'].append(u"chart_calendar.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))

try:

    def __init__():
        pass

    fmt = {'short': {0: ["M", "T", "W", "T", "F", "S", "S"],
                     6: ["S", "M", "T", "W", "T", "F", "S"]},
           'mid': {0: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                   6: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]},
           'long': {0: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
                    6: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]}
           }

    first_day   = int(props.get('firstDayOfWeek', 6))
    day_format  = props.get('dayOfWeekFormat', 'mid')
    days_labels = fmt[day_format][first_day]

    my_cal = calendar.Calendar(first_day)  # first day is Sunday = 6, Monday = 0
    today  = dt.datetime.today()
    cal    = my_cal.monthdatescalendar(today.year, today.month)

    try:
        height = int(props.get('customSizeHeight', 300)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 3

    try:
        width = int(props.get('customSizeWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # =============================  Plot Months Row  =============================
    month_row = ax.table(cellText=[" "],
                         colLabels=[dt.datetime.strftime(today, "%B")],
                         loc='top',
                         bbox=[0, 0.5, 1, .5]  # bbox = [left, bottom, width, height]
                         )
    chart_tools.format_axis(ax_obj=month_row)

    # =============================  Plot Days Rows  ==============================
    # final_cal contains just the date value from the date object
    final_cal = [[_.day if _.month == today.month else "" for _ in thing] for thing in cal]

    days_rows = ax.table(cellText=final_cal,
                         colLabels=days_labels,
                         loc='top',
                         cellLoc=props.get('dayOfWeekAlignment', 'right'),
                         bbox=[0, -0.5, 1, 1.25]
                         )
    chart_tools.format_axis(ax_obj=days_rows)

    # =========================  Highlight Today's Date  ==========================
    t = dt.datetime.now().day  # today's date
    all_cal = [days_labels] + final_cal  # days rows plus dates rows

    # Find the index of today's date (t) in all_cal
    highlight_date = [(i, all_cal.index(t)) for i, all_cal in enumerate(all_cal) if t in all_cal][0]

    # Set the cell facecolor
    highlight_color = p_dict.get('todayHighlight', '#555555')
    days_rows.get_celld()[highlight_date].set_facecolor(highlight_color)

    # =============================  Plot the Chart  ==============================
    # Note that subplots_adjust affects the space surrounding the subplots and not
    # the fig.
    plt.subplots_adjust(top=0.97,
                        bottom=0.34,
                        left=0.02,
                        right=0.98,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    tb = traceback.format_exc()
    chart_tools.log['Critical'].append(u"[{n}] {s}".format(n=chart_name, s=tb))

# ==============================  Housekeeping  ===============================
pickle.dump(chart_tools.log, sys.stdout)

