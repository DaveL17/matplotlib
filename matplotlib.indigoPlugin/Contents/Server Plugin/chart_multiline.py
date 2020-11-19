#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Creates the multiline text charts

-----
"""

# import calendar
# import datetime as dt
import sys
import textwrap

import pickle

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

payload = chart_tools.payload

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

    payload['p_dict']['backgroundColor'] = chart_tools.fix_rgb(c=payload['p_dict']['backgroundColor'])
    payload['p_dict']['faceColor'] = chart_tools.fix_rgb(c=payload['p_dict']['faceColor'])
    payload['p_dict']['textColor'] = chart_tools.fix_rgb(c=payload['p_dict']['textColor'])
    payload['p_dict']['figureWidth'] = float(payload['props']['figureWidth'])
    payload['p_dict']['figureHeight'] = float(payload['props']['figureHeight'])

    try:
        height = int(payload['props'].get('figureHeight', 300)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        height = 3

    try:
        width = int(payload['props'].get('figureWidth', 500)) / int(plt.rcParams['savefig.dpi'])
    except ValueError:
        width = 5

    try:
        fig = plt.figure(figsize=(width, height))
        ax = fig.add_subplot(111)
        ax.axis('off')

        # If the value to be plotted is empty, use the default text from the device
        # configuration.
        text_to_plot = payload['data']
        if len(text_to_plot) <= 1:
            text_to_plot = unicode(payload['p_dict']['defaultText'])

        else:
            # The clean_string method tries to remove some potential ugliness from the text
            # to be plotted. It's optional--defaulted to on. No need to call this if the
            # default text is used.
            if payload['p_dict']['cleanTheText']:
                text_to_plot = clean_string(text_to_plot)

        chart_tools.log['Threaddebug'].append(u"Data: {0}".format(text_to_plot))

        # Wrap the text and prepare it for plotting.
        text_to_plot = textwrap.fill(text_to_plot,
                                     int(payload['p_dict']['numberOfCharacters']),
                                     replace_whitespace=payload['p_dict']['cleanTheText']
                                     )

        ax.text(0.01, 0.95,
                text_to_plot,
                transform=ax.transAxes,
                color=payload['p_dict']['textColor'],
                fontname=payload['p_dict']['fontMain'],
                fontsize=payload['p_dict']['multilineFontSize'],
                verticalalignment='top'
                )

        ax.axes.get_xaxis().set_visible(False)
        ax.axes.get_yaxis().set_visible(False)

        if not payload['p_dict']['textAreaBorder']:
            [s.set_visible(False) for s in ax.spines.values()]

        # Transparent Charts Fill
        if payload['p_dict']['transparent_charts'] and payload['p_dict']['transparent_filled']:
            ax.add_patch(patches.Rectangle((0, 0), 1, 1,
                                           transform=ax.transAxes,
                                           facecolor=payload['p_dict']['faceColor'],
                                           zorder=1
                                           )
                         )

        # =============================== Format Title ================================
        chart_tools.format_title(payload['p_dict'], payload['k_dict'], loc=(0.05, 0.98), align='center')

    except (KeyError, IndexError, ValueError, UnicodeEncodeError):
        pass

    except Exception as sub_error:
        pass

    # Note that subplots_adjust affects the space surrounding the subplots and not
    # the fig.
    plt.subplots_adjust(top=0.98,
                        bottom=0.05,
                        left=0.02,
                        right=0.98,
                        hspace=None,
                        wspace=None
                        )

    chart_tools.save()

except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
    pass
