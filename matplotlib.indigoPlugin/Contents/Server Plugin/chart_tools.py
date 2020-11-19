#! /usr/bin/env python
# -*- coding: utf-8 -*-

# import calendar
import csv
import datetime as dt
import sys
import pickle
import unicodedata

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
        :param dict log: plugin log dict
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
            log['Warning'].append(u'CSV file is empty. File: {0}'.format(data_source))

        # ===================== CSV File has Headers but no Data ======================
        # Adds one observation. Length of CSV file goes from one to two.
        if len(final_data) < 2:
            final_data.append((now_text, 0))
            log['Warning'].append(u'CSV file does not have sufficient information to make a useful plot. '
                                  u'File: {0}'.format(data_source))

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
    def format_title(p_dict, k_dict, loc, align='center'):
        """
        Plot the figure's title
        -----
        :param p_dict:
        :param k_dict:
        :param log:
        :param loc:
        :param str align:
        :return:
        """
        try:
            plt.suptitle(p_dict['chartTitle'], position=loc, ha=align, **k_dict['k_title_font'])

        except KeyError as sub_error:
            log['Warning'].append(u"Title Error: {0}".format(sub_error))

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
        now        = dt.datetime.now()
        now_text   = dt.datetime.strftime(now, '%Y-%m-%d %H:%M:%S')

        try:
            # Get the data
            with open(data_source, "r") as data_file:
                csv_data = csv.reader(data_file, delimiter=',')

                # Convert the csv object to a list
                [final_data.append(item) for item in csv_data]

            # Process the data a bit more for charting
            final_data = convert_the_data(final_data, data_source)

            return final_data

        # If we can't find the target CSV file, we create a phony proxy which the plugin
        # can process without dying.
        except Exception as sub_error:
            final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
            log['Warning'].append(u"Error downloading CSV data: {0}. See plugin log for more "
                                  u"information.".format(sub_error))

            return final_data

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