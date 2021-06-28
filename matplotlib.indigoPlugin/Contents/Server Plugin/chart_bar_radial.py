#! /usr/bin/env python
# -*- coding: utf-8 -*-

# see also https://stackoverflow.com/a/49733577/2827397

import pickle
import sys
import traceback

# Third-party Modules
# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# My modules
import chart_tools

log               = chart_tools.log
payload           = chart_tools.payload
plot_value        = payload['data']
p_dict            = payload['p_dict']
k_dict            = payload['k_dict']
props             = payload['props']
chart_name        = props['name']
plug_dict         = payload['prefs']
annotation_values = []
bar_colors        = []
x_labels          = []
x_ticks           = []

# ================================== Globals ==================================
color_light   = p_dict['bar_1']
color_dark  = p_dict['bar_2']
color_font   = p_dict['fontColor']
color_border = p_dict['gridColor']
font_main    = p_dict['fontMain']
precision    = p_dict['precision']
icon_height  = p_dict['sqChartSize']
icon_width   = p_dict['sqChartSize']
slice_width  = 0.35
plot_scale   = float(payload.get('scale', p_dict['scale']))
zero_loc = int(p_dict['startAngle'])

log['Threaddebug'].append(u"chart_bar_radial.py called.")
if plug_dict['verboseLogging']:
    chart_tools.log['Threaddebug'].append(u"{0}".format(payload))
chart_tools.log['Threaddebug'].append(u"Value: {0} Scale: {1}".format(plot_value, plot_scale))

try:

    def __init__():
        pass

    # ============================  Custom Font Size  =============================
    # User has selected a custom font size.
    if not p_dict['customSizeFont']:
        size_font = p_dict['mainFontSize']
    else:
        size_font = p_dict['customTickFontSize']

    # ================================== Figure ===================================
    ax = chart_tools.make_chart_figure(width=icon_width, height=icon_height, p_dict=p_dict)
    ax.axis('equal')

    # ========================= Plot Figure and Decorate ==========================
    kwargs     = dict(colors=[color_light, color_dark], startangle=zero_loc)
    outside, _ = ax.pie([plot_value, plot_scale-plot_value], radius=1, pctdistance=(1 - slice_width / 2), labels=['', ''], **kwargs)
    plt.setp(outside, width=slice_width, edgecolor=color_border)

    # =================================== Text ====================================
    kwargs = dict(size=size_font, fontweight='bold', va='center', color=color_font, fontname=font_main)
    ax.text(0, 0, str(u"{0:0.{1}f}".format(plot_value, precision)), ha='center', **kwargs)

    # ============================= Format Plot Area ==============================
    plt.subplots_adjust(left=0, right=1.0, top=1.0, bottom=0)  # Reduce whitespace around figure
    plt.rcParams.update({"savefig.facecolor": (0.0, 0.0, 1.0, 0.0)})  # RGBA setting background as transparent

    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError, ZeroDivisionError) as sub_error:
    tb = traceback.format_exc()
    chart_tools.log['Critical'].append(u"[{n}]\n{s}".format(n=chart_name, s=tb))

pickle.dump(chart_tools.log, sys.stdout)
