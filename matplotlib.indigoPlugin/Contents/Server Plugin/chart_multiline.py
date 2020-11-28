#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the multiline text charts
Given the unique nature of multiline text charts, we use a separate method
to construct them.
-----

"""

# import calendar
# import datetime as dt
# import pickle
# import sys
import textwrap

# Note the order and structure of matplotlib imports is intentional.
import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
# from matplotlib import rcParams
import matplotlib.pyplot as plt
import matplotlib.patches as patches
# import matplotlib.dates as mdate
# import matplotlib.ticker as mtick
# import matplotlib.font_manager as mfont

import chart_tools
# import DLFramework as Dave

log     = chart_tools.log
payload = chart_tools.payload
p_dict  = payload['p_dict']
k_dict  = payload['k_dict']
props   = payload['props']

try:

    def __init__():
        pass

    def clean_string(val):
        """
        Cleans long strings of whitespace and formats certain characters
        The clean_string(self, val) method is used to scrub multiline text elements in
        order to try to make them more presentable. The need is easily seen by looking
        at the rough text that is provided by the U.S. National Weather Service, for
        example.
        -----
        :param unicode val:
        :return val:
        """

        # List of (elements, replacements)
        clean_list = ((' am ', ' AM '),
                      (' pm ', ' PM '),
                      ('*', ' '),
                      ('\u000A', ' '),
                      ('...', ' '),
                      ('/ ', '/'),
                      (' /', '/'),
                      ('/', ' / ')
                      )

        # Take the old, and replace it with the new.
        for (old, new) in clean_list:
            val = val.replace(old, new)

        val = ' '.join(val.split())  # Eliminate spans of whitespace.

        return val

    for color in ['backgroundColor', 'faceColor', 'textColor']:
        p_dict[color] = chart_tools.fix_rgb(color=p_dict[color])

    p_dict['figureWidth'] = float(props['figureWidth'])
    p_dict['figureHeight'] = float(props['figureHeight'])

    try:
        height = int(props.get('figureHeight', 300)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 3

    try:
        width = int(props.get('figureWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    fig = plt.figure(figsize=(width, height))
    ax = fig.add_subplot(111)
    ax.axis('off')

    # If the value to be plotted is empty, use the default text from the device
    # configuration.
    text_to_plot = payload['data']
    if len(text_to_plot) <= 1:
        text_to_plot = unicode(p_dict['defaultText'])

    else:
        # The clean_string method tries to remove some potential ugliness from the text
        # to be plotted. It's optional--defaulted to on. No need to call this if the
        # default text is used.
        if p_dict['cleanTheText']:
            text_to_plot = clean_string(val=text_to_plot)

    chart_tools.log['Threaddebug'].append(u"Data: {0}".format(text_to_plot))

    # Wrap the text and prepare it for plotting.
    text_to_plot = textwrap.fill(text=text_to_plot,
                                 width=int(p_dict['numberOfCharacters']),
                                 replace_whitespace=p_dict['cleanTheText']
                                 )

    ax.text(0.01, 0.95,
            text_to_plot,
            transform=ax.transAxes,
            color=p_dict['textColor'],
            fontname=p_dict['fontMain'],
            fontsize=p_dict['multilineFontSize'],
            verticalalignment='top'
            )

    ax.axes.get_xaxis().set_visible(False)
    ax.axes.get_yaxis().set_visible(False)

    if not p_dict['textAreaBorder']:
        [s.set_visible(False) for s in ax.spines.values()]

    # Transparent Charts Fill
    if p_dict['transparent_charts'] and p_dict['transparent_filled']:
        ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                       transform=ax.transAxes,
                                       facecolor=p_dict['faceColor'],
                                       zorder=1
                                       )
                     )

    # =============================== Format Title ================================
    chart_tools.format_title(p_dict=p_dict, k_dict=k_dict, loc=(0.05, 0.98), align='center')

    # Note that subplots_adjust affects the space surrounding the subplots and not
    # the fig.
    plt.subplots_adjust(top=0.98,
                        bottom=0.05,
                        left=0.02,
                        right=0.98,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save(logger=log)

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    chart_tools.log['Critical'].append(u"{0}".format(sub_error))
