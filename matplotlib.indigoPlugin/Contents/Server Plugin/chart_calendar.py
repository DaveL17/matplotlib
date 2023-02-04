# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Creates the calendar charts
Given the unique nature of calendar charts, we use a separate method to
construct them.
"""

# Built-in Modules
import calendar
import datetime as dt
import json
import sys
import traceback
# Third-party Modules
from matplotlib import pyplot as plt
# My modules
import chart_tools

LOG        = chart_tools.LOG
PAYLOAD    = chart_tools.payload
PROPS      = PAYLOAD['props']
CHART_NAME = PROPS['name']
P_DICT     = PAYLOAD['p_dict']
PLUG_DICT  = PAYLOAD['prefs']

LOG['Threaddebug'].append("chart_calendar.py called.")
plt.style.use(f"Stylesheets/{PROPS['id']}_stylesheet")

if PLUG_DICT['verboseLogging']:
    LOG['Threaddebug'].append(f"{PAYLOAD}")

try:

    def __init__():
        ...

    fmt = {
        'short': {
            0: ["M", "T", "W", "T", "F", "S", "S"],
            6: ["S", "M", "T", "W", "T", "F", "S"]
        },
        'mid': {
            0: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            6: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        },
        'long': {
            0: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
            6: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        }
    }

    first_day   = int(PROPS.get('firstDayOfWeek', 6))
    day_format  = PROPS.get('dayOfWeekFormat', 'mid')
    days_labels = fmt[day_format][first_day]

    my_cal = calendar.Calendar(first_day)  # first day is Sunday = 6, Monday = 0
    today  = dt.datetime.today()
    cal    = my_cal.monthdatescalendar(today.year, today.month)

    try:
        height = int(PROPS.get('customSizeHeight', 200)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 2

    try:
        width = int(PROPS.get('customSizeWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # =============================  Plot Months Row  =============================
    month_row = ax.table(
        cellText=[" "],
        colLabels=[dt.datetime.strftime(today, "%B")],
        loc='top',
        bbox=[0, 0.5, 1, .5]  # bbox = [left, bottom, width, height]
    )
    chart_tools.format_axis(ax_obj=month_row)

    # =============================  Plot Days Rows  ==============================
    # final_cal contains just the date value from the date object
    final_cal = [[_.day if _.month == today.month else "" for _ in thing] for thing in cal]

    days_rows = ax.table(
        cellText=final_cal,
        colLabels=days_labels,
        loc='top',
        cellLoc=PROPS.get('dayOfWeekAlignment', 'right'),
        bbox=[0, -0.5, 1, 1.25]
    )
    chart_tools.format_axis(ax_obj=days_rows)

    # =========================  Highlight Today's Date  ==========================
    t = dt.datetime.now().day  # today's date
    all_cal = [days_labels] + final_cal  # days rows plus dates rows

    # Find the index of today's date (t) in all_cal
    highlight_date = [(i, all_cal.index(t)) for i, all_cal in enumerate(all_cal) if t in all_cal][0]

    # Set the cell facecolor
    highlight_color = P_DICT.get('todayHighlight', '#555555')
    days_rows.get_celld()[highlight_date].set_facecolor(highlight_color)

    # =============================  Plot the Chart  ==============================
    # Note that subplots_adjust affects the space surrounding the subplots and not the fig.
    # plt.subplots_adjust(
    #     top=0.97,
    #     bottom=0.34,
    #     left=0.02,
    #     right=0.98,
    #     hspace=None,
    #     wspace=None
    # )

    chart_tools.save(logger=LOG)

except Exception as sub_error:
    tb = traceback.format_exc()
    tb_type = sys.exc_info()[1]
    LOG['Debug'].append(f"[{CHART_NAME}] {tb}")
    LOG['Critical'].append(f"[{CHART_NAME}] Error type: {tb_type} in {__file__.split('/')[-1]}")

json.dump(LOG, sys.stdout, indent=4)
