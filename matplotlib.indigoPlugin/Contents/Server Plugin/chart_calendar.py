#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the calendar charts

Given the unique nature of calendar charts, we use a separate method to
construct them.
-----
"""

import calendar
import datetime as dt
import sys
import pickle

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

# Collection of logging messages.
# TODO: consider looking at Matt's logging handler and see if that's better.
log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

# Unpickle the payload data. The first element of the payload is the name
# of this script and we don't need that. As long as size isn't a limitation
# we will always send the entire payload as element 1.
payload = pickle.loads(sys.argv[1])
log['Debug'].append(u'payload unpickled successfully.')

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

    first_day = int(payload['props'].get('firstDayOfWeek', 6))
    day_format = payload['props'].get('dayOfWeekFormat', 'mid')
    days_labels = fmt[day_format][first_day]

    my_cal = calendar.Calendar(first_day)  # first day is Sunday = 6, Monday = 0
    today = dt.datetime.today()
    cal = my_cal.monthdatescalendar(today.year, today.month)

    try:
        height = int(payload['props'].get('customSizeHeight', 300)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 3

    try:
        width = int(payload['props'].get('customSizeWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    # final_cal contains just the date value from the date object
    final_cal = [[_.day if _.month == today.month else "" for _ in thing] for thing in cal]

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    month_row = ax.table(cellText=[" "],
                         colLabels=[dt.datetime.strftime(today, "%B")],
                         loc='top',
                         bbox=[0, 0.5, 1, .5]  # bbox = [left, bottom, width, height]
                         )
    # format_axis(month_row)
    chart_tools.format_axis(month_row)

    days_rows = ax.table(cellText=final_cal,
                         colLabels=days_labels,
                         loc='top',
                         cellLoc=payload['props'].get('dayOfWeekAlignment', 'right'),
                         bbox=[0, -0.5, 1, 1.25]
                         )
    # format_axis(days_rows)
    chart_tools.format_axis(days_rows)

    # Note that subplots_adjust affects the space surrounding the subplots and not
    # the fig.
    plt.subplots_adjust(top=0.97,
                        bottom=0.34,
                        left=0.02,
                        right=0.98,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save()

    pickle.dump(log, sys.stdout)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    pass
