#! /usr/bin/env python
# -*- coding: utf-8 -*-

# import calendar
# import datetime as dt
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

# import DLFramework as Dave

# Collection of logging messages.
# TODO: consider looking at Matt's logging handler and see if that's better.
log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

# Unpickle the payload data. The first element of the payload is the name
# of this script and we don't need that. As long as size isn't a limitation
# we will always send the entire payload as element 1.
try:
    payload = pickle.loads(sys.argv[1])
except IndexError:
    pass
log['Debug'].append(u'payload unpickled successfully.')

try:

    def __init__():
        pass

    # =============================================================================
    def fix_rgb(c):

        return r"#{0}".format(c.replace(' ', '').replace('#', ''))

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
    def save():
        if payload['p_dict']['chartPath'] != '' and payload['p_dict']['fileName'] != '':
            plt.savefig(u'{0}{1}'.format(payload['p_dict']['chartPath'], payload['p_dict']['fileName']),
                        **payload['k_dict']['k_plot_fig']
                        )
            log['Debug'].append(u"Chart {0} saved.".format(payload['p_dict']['fileName']))

        # Note that this garbage collection may be unneeded since the process will end.
        plt.clf()
        plt.close('all')

        # Process any standard output. For now, we can only do this once, so we should
        # combine any messages we want to send.
        pickle.dump(log, sys.stdout)

except Exception:
    pass