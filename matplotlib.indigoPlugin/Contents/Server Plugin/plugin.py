#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
matplotlib plugin
author: DaveL17

The matplotlib plugin is used to produce various types of charts and graphics
for use on Indigo control pages. The key benefits of the plugin are its ability
to make global changes to all generated charts (i.e., fonts, colors) and its
relative simplicity.  It contains direct support for some automated charts (for
example, it can create Fantastic Weather plugin forecast charts if linked to
the proper Fantastic Weather devices.
"""

# =================================== Notes ===================================
# - Memory Leak
#   There is a known issue with the version of Matplotlib shipping at the time
#   this plugin was developed that caused a memory leak that would ultimately
#   cause the plugin to crash. Two significant steps were taken to address
#   this. First, we import 'matplotlib.use('AGG')' which is thought to isolate
#   the leak. Second, we run each plot update in its own process and then
#   ultimately destroy the process when it's finished. These two steps seem to
#   allow the plugin to run indefinitely without running out of resources.

# =================================== TO DO ===================================

# TODO: NEW -- Create a new device to create a horizontal bar chart (i.e., like
#              device battery levels.)
# TODO: NEW -- Create an "error" chart with min/max/avg
# TODO: NEW -- Create a floating bar chart
# TODO: NEW -- Create generic weather forecast charts to support any weather
#              services
# TODO: NEW -- Standard chart types with pre-populated data that link to types
#              of Indigo devices.
# TODO: NEW -- Add config dialog to rcparams device that's generated
#              automatically?
# TODO: Support substitutions for certain fields (like save location).
# TODO: Try to address annotation collisions.
# TODO: Iterate CSV engine devices and warn if any are writing to same file.
# TODO: Wrap long names for battery health device?
# TODO: Add facility to have different Y1 and Y2. Add a new group of controls
#       (like Y1) for Y2 and then have a control to allow user to elect when Y
#       axis to assign the line to.
# TODO: Remove matplotlib_version.html after deprecation
# TODO: if the csv save location is a share, and the share is unreachable, it
#       blows up.
# TODO: Add validation that will not allow custom tick locations to be outside
#       the boundaries of the axis min/max.
# TODO: Add adjustment factor to scatter charts
# TODO: Move more plotting stuff to methods
# ================================== IMPORTS ==================================

try:
    import indigo
except ImportError as error:
    pass

# Built-in modules
from ast import literal_eval
import csv
import datetime as dt
from dateutil.parser import parse as date_parse
import logging
import multiprocessing
import numpy as np
import os
import traceback
import unicodedata

import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
from matplotlib import rcParams
try:
    import matplotlib.pyplot as plt
except ImportError:
    indigo.server.log(u"There was an error importing necessary Matplotlib components. Please reboot your server and try to re-enable the plugin.", isError=True)
import matplotlib.patches as patches
import matplotlib.dates as mdate
import matplotlib.ticker as mtick
import matplotlib.font_manager as mfont

# Third-party modules
# try:
#     import pydevd  # To support remote debugging
# except ImportError as error:
#     pass

# My modules
import DLFramework.DLFramework as Dave
import maintenance

# =================================== HEADER ==================================

__author__    = Dave.__author__
__copyright__ = Dave.__copyright__
__license__   = Dave.__license__
__build__     = Dave.__build__
__title__     = "Matplotlib Plugin for Indigo Home Control"
__version__   = "0.7.47"

# =============================================================================

install_path = indigo.server.getInstallFolderPath()

kDefaultPluginPrefs = {
    u'backgroundColor': "00 00 00",
    u'backgroundColorOther': False,
    u'chartPath': u"{0}/IndigoWebServer/images/controls/static/".format(install_path),
    u'chartResolution': 100,
    u'dataPath': u"{0}/Logs/com.fogbert.indigoplugin.matplotlib/".format(install_path),
    u'dpiWarningFlag': False,
    u'enableCustomLineSegments': False,
    u'faceColor': "00 00 00",
    u'faceColorOther': False,
    u'fontColor': "FF FF FF",
    u'fontColorAnnotation': "FF FF FF",
    u'fontMain': "Arial",
    u'forceOriginLines': False,
    u'gridColor': "88 88 88",
    u'gridStyle': ":",
    u'legendFontSize': 6,
    u'lineWeight': "1.0",
    u'logEachChartCompleted': True,
    u'mainFontSize': 10,
    u'promoteCustomLineSegments': False,
    u'rectChartHeight': 250,
    u'rectChartWideHeight': 250,
    u'rectChartWideWidth': 1000,
    u'rectChartWidth': 600,
    u'refreshInterval': 900,
    u'showDebugLevel': 30,
    u'snappyConfigMenus': False,
    u'spineColor': "88 88 88",
    u'sqChartSize': 250,
    u'tickColor': "88 88 88",
    u'tickFontSize': 8,
    u'tickSize': 4,
    u'verboseLogging': False
}


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        # ======================== Initialize Global Variables ========================
        self.pluginIsInitializing  = True   # Flag signaling that __init__ is in process
        self.pluginIsShuttingDown  = False  # Flag signaling that the plugin is shutting down.
        self.skipRefreshDateUpdate = False  # Flag that we have called for a manual chart refresh

        self.final_data = []

        # ========================== Initialize DLFramework ===========================
        self.Fogbert  = Dave.Fogbert(self)  # Plugin functional framework
        self.evalExpr = Dave.evalExpr(self)  # Formula evaluation framework

        # Log pluginEnvironment information when plugin is first started
        self.Fogbert.pluginEnvironmentLogger()

        # Maintenance of plugin props and device prefs
        self.maintain = maintenance.Maintain(self)

        # =========================== Log More Plugin Info ============================
        self.pluginEnvironmentLogger()

        # ============================= Initialize Logger =============================
        self.plugin_file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug_level = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debug_level)

        # Set private log handler based on plugin preference
        if self.pluginPrefs.get('verboseLogging', False):
            self.plugin_file_handler.setLevel(5)
            self.logger.warning(u"Verbose logging is on. It is best to leave this turned off unless directed.")
        else:
            self.plugin_file_handler.setLevel(10)

        # =================== Conform Custom Colors to Color Picker ===================
        # See method for more info.
        self.convert_custom_colors()

        # ============================ Clean Plugin Prefs =============================
        # Remove legacy cruft from plugin prefs. We do devices later.
        # self.pluginPrefs = self.__clean_prefs(self.pluginPrefs)
        # indigo.server.savePluginPrefs()

        # ============================= Remote Debug Hook =============================
        # try:
        #     pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)
        # except:
        #     pass

        self.pluginIsInitializing = False

    def __del__(self):
        indigo.PluginBase.__del__(self)

    # =============================================================================
    # ============================== Indigo Methods ===============================
    # =============================================================================
    def closedDeviceConfigUi(self, values_dict=None, user_cancelled=False, type_id="", dev_id=0):

        dev = indigo.devices[dev_id]

        if not user_cancelled:
            self.logger.threaddebug(u"[{0}] Final device values_dict: {1}".format(dev.name, dict(values_dict)))
            self.logger.threaddebug(u"Configuration complete.")
        else:
            self.logger.threaddebug(u"User cancelled.")

        return True

    # =============================================================================
    def closedPrefsConfigUi(self, values_dict=None, user_cancelled=False):

        if not user_cancelled:

            if values_dict['verboseLogging']:
                self.plugin_file_handler.setLevel(5)
                self.logger.warning(u"Verbose logging is on. It is best not to leave this turned on for very long.")
            else:
                self.plugin_file_handler.setLevel(10)
                self.logger.info(u"Verbose logging is off.  It is best to leave this turned off unless directed.")

            self.logger.threaddebug(u"Configuration complete.")

        else:
            self.logger.threaddebug(u"User cancelled.")

        return True

    # =============================================================================
    def deviceStartComm(self, dev):

        # If we're coming here from a sleep state, we need to ensure that the plugin
        # shutdown global is in its proper state.
        self.pluginIsShuttingDown = False

        # If chartLastUpdated is empty, set it to the epoch
        if dev.deviceTypeId != 'csvEngine' and dev.states['chartLastUpdated'] == "":
            dev.updateStateOnServer(key='chartLastUpdated', value='1970-01-01 00:00:00.000000')
            self.logger.threaddebug(u"CSV last update unknown. Coercing update.")

        # If the refresh interval is greater than zero
        # Note that we check for the existence of the device state before trying to
        # update it due to how Indigo processes devices when their source plugin has
        # been changed (i.e., assigning an existing device to a new plugin instance.)

        if 'onOffState' in dev.states:

            if dev.deviceTypeId != 'rcParamsDevice' and int(dev.pluginProps['refreshInterval']) > 0:
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Enabled'}])

            # If the device is set to manual only.
            elif int(dev.pluginProps['refreshInterval']) == 0 or dev.pluginProps['refreshInterval'] == '':
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Manual'}])

            else:
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': ' '}])

        dev.stateListOrDisplayStateIdChanged()
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    def deviceStopComm(self, dev):

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    def getDeviceConfigUiValues(self, values_dict, type_id="", dev_id=0):

        dev = indigo.devices[int(dev_id)]

        self.logger.threaddebug(u"[{0}] Getting device config props: {1}".format(dev.name, dict(values_dict)))

        try:

            # ===================== Prepare CSV Engine Config Window ======================
            # Put certain props in a state that we expect when the config dialog is first
            # opened.
            if type_id == "csvEngine":
                values_dict['addItemFieldsCompleted'] = False
                values_dict['addKey']                 = ""
                values_dict['addSource']              = ""
                values_dict['addSourceFilter']        = "A"
                values_dict['addState']               = ""
                values_dict['addValue']               = ""
                values_dict['csv_item_list']          = ""
                values_dict['editKey']                = ""
                values_dict['editSource']             = ""
                values_dict['editSourceFilter']       = "A"
                values_dict['editState']              = ""
                values_dict['editValue']              = ""
                values_dict['isColumnSelected']       = False
                values_dict['previousKey']            = ""

                return values_dict

            # # ============================= Fix Custom Colors =============================
            # # For existing devices
            # if dev.configured:
            #
            #     # Update legacy color values from hex to raw (#FFFFFF --> FF FF FF)
            #     for prop in values_dict:
            #         if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', unicode(values_dict[prop])):
            #             s = values_dict[prop]
            #             values_dict[prop] = u'{0} {1} {2}'.format(s[0:3], s[3:5], s[5:7]).replace('#', '')

            # ========================== Set Config UI Defaults ===========================
            # For new devices, force certain defaults that don't carry from devices.xml.
            # This seems to be especially important for menu items built with callbacks and
            # colorpicker controls that don't appear to accept defaultValue.
            if not dev.configured:

                values_dict['refreshInterval'] = '900'

                # ============================ Bar Charting Device ============================
                if type_id == "barChartingDevice":

                    for _ in range(1, 5, 1):
                        values_dict['bar{0}Color'.format(_)]  = 'FF FF FF'
                        values_dict['bar{0}Source'.format(_)] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # =========================== Battery Health Device ===========================
                if type_id == "batteryHealthDevice":
                    values_dict['healthyColor']     = '00 00 CC'
                    values_dict['cautionLevel']     = '10'
                    values_dict['cautionColor']     = 'FF FF 00'
                    values_dict['warningLevel']     = '5'
                    values_dict['warningColor']     = 'FF 00 00'
                    values_dict['showBatteryLevel'] = 'true'

                # ========================== Calendar Charting Device =========================
                if type_id == "calendarChartingDevice":
                    values_dict['fontSize'] = 12

                # ============================ Line Charting Device ===========================
                if type_id == "lineChartingDevice":

                    for _ in range(1, 7, 1):
                        values_dict['line{0}BestFit'.format(_)]      = False
                        values_dict['line{0}BestFitColor'.format(_)] = 'FF 00 00'
                        values_dict['line{0}Color'.format(_)]        = 'FF FF FF'
                        values_dict['line{0}Marker'.format(_)]       = 'None'
                        values_dict['line{0}MarkerColor'.format(_)]  = 'FF FF FF'
                        values_dict['line{0}Source'.format(_)]       = 'None'
                        values_dict['line{0}Style'.format(_)]        = '-'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # =========================== Multiline Text Device ===========================
                if type_id == "multiLineText":
                    values_dict['textColor']  = "FF 00 FF"
                    values_dict['thing']      = 'None'
                    values_dict['thingState'] = 'None'

                # =========================== Polar Charting Device ===========================
                if type_id == "polarChartingDevice":
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['currentWindColor']    = 'FF 33 33'
                    values_dict['maxWindColor']        = '33 33 FF'
                    values_dict['radiiValue']          = 'None'
                    values_dict['thetaValue']          = 'None'

                # ========================== Scatter Charting Device ==========================
                if type_id == "scatterChartingDevice":

                    for _ in range(1, 5, 1):
                        values_dict['line{0}BestFit'.format(_)]      = False
                        values_dict['line{0}BestFitColor'.format(_)] = 'FF 00 00'
                        values_dict['group{0}Color'.format(_)]       = 'FF FF FF'
                        values_dict['group{0}Marker'.format(_)]      = '.'
                        values_dict['group{0}MarkerColor'.format(_)] = 'FF FF FF'
                        values_dict['group{0}Source'.format(_)]      = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ========================== Weather Forecast Device ==========================
                if type_id == "forecastChartingDevice":

                    for _ in range(1, 3, 1):
                        values_dict['line{0}Marker'.format(_)]      = 'None'
                        values_dict['line{0}MarkerColor'.format(_)] = 'FF FF FF'
                        values_dict['line{0}Style'.format(_)]       = '-'

                    values_dict['customLineStyle']      = '-'
                    values_dict['customTickFontSize']   = 8
                    values_dict['customTitleFontSize']  = 10
                    values_dict['forecastSourceDevice'] = 'None'
                    values_dict['line1Color']           = 'FF 33 33'
                    values_dict['line2Color']           = '00 00 FF'
                    values_dict['line3Color']           = '99 CC FF'
                    values_dict['line3MarkerColor']     = 'FF FF FF'
                    values_dict['xAxisBins']            = 'daily'
                    values_dict['xAxisLabelFormat']     = '%A'
                    values_dict['showDaytime']          = 'true'
                    values_dict['daytimeColor']         = '33 33 33'

            if self.pluginPrefs.get('enableCustomLineSegments', False):
                values_dict['enableCustomLineSegmentsSetting'] = True
                self.logger.threaddebug(u"Enabling advanced feature: Custom Line Segments.")
            else:
                values_dict['enableCustomLineSegmentsSetting'] = False

            # If Snappy Config Menus are enabled, reset all device config dialogs to a
            # minimized state (all sub-groups minimized upon open.) Otherwise, leave them
            # where they are.
            if self.pluginPrefs.get('snappyConfigMenus', False):
                self.logger.threaddebug(u"Enabling advanced feature: Snappy Config Menus.")

                for key in ('barLabel1', 'barLabel2', 'barLabel3', 'barLabel4',
                            'lineLabel1', 'lineLabel2', 'lineLabel3', 'lineLabel4', 'lineLabel5', 'lineLabel6',
                            'groupLabel1', 'groupLabel1', 'groupLabel2', 'groupLabel3', 'groupLabel4',
                            'xAxisLabel', 'xAxisLabel', 'y2AxisLabel', 'yAxisLabel', ):
                    if key in values_dict.keys():
                        values_dict[key] = False

            return values_dict

        except KeyError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"[{0}] Error: {1}. See plugin log for more information.".format(dev.name, sub_error))

        return True

    # =============================================================================
    def getDeviceStateList(self, dev):

        state_list = indigo.PluginBase.getDeviceStateList(self, dev)

        if dev.deviceTypeId == 'rcParamsDevice':

            for key in rcParams.iterkeys():
                key = key.replace('.', '_')
                dynamic_state = self.getDeviceStateDictForStringType(key, key, key)
                state_list.append(dynamic_state)
                state_list.append(self.getDeviceStateDictForStringType('onOffState', 'onOffState', 'onOffState'))

            return state_list

        else:
            return state_list

    # =============================================================================
    def getMenuActionConfigUiValues(self, menu_id=0):

        settings       = indigo.Dict()
        error_msg_dict = indigo.Dict()

        self.logger.threaddebug(u"Getting menu action config prefs: {0}".format(dict(settings)))

        settings['enableCustomLineSegments']  = self.pluginPrefs.get('enableCustomLineSegments', False)
        settings['promoteCustomLineSegments'] = self.pluginPrefs.get('promoteCustomLineSegments', False)
        settings['snappyConfigMenus']         = self.pluginPrefs.get('snappyConfigMenus', False)
        settings['forceOriginLines']          = self.pluginPrefs.get('forceOriginLines', False)

        return settings, error_msg_dict

    # =============================================================================
    def getPrefsConfigUiValues(self):

        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        self.logger.threaddebug(u"Getting plugin Prefs: {0}".format(dict(plugin_prefs)))

        # Establish a set of defaults for select plugin settings. Only those settings that are populated dynamically need to be set here (the others can be set directly by the XML.)
        defaults_dict = {'backgroundColor': '00 00 00',
                         'backgroundColorOther': '00 00 00',
                         'faceColor': '00 00 00',
                         'faceColorOther': '00 00 00',
                         'fontColor': 'FF FF FF',
                         'fontColorAnnotation': 'FF FF FF',
                         'fontMain': 'Arial',
                         'gridColor': '88 88 88',
                         'gridStyle': ':',
                         'legendFontSize': '6',
                         'mainFontSize': '10',
                         'spineColor': '88 88 88',
                         'tickColor': '88 88 88',
                         'tickFontSize': '8'}

        # Try to assign the value from plugin_prefs. If it doesn't work, add the key, value pair based on the defaults_dict above.
        # This should only be necessary the first time the plugin is configured.
        for key, value in defaults_dict.items():
            plugin_prefs[key] = plugin_prefs.get(key, value)

        return plugin_prefs

    # =============================================================================
    def runConcurrentThread(self):

        self.sleep(0.5)

        while True:
            if not self.pluginIsShuttingDown:

                # ========================== Clean Up Old Processes ===========================
                # If all goes according to plan, this will join() all completed processes. Any
                # processes that are still running (if any) will be listed to the log.
                zombies = multiprocessing.active_children()

                if len(zombies) > 0:
                    self.logger.threaddebug(u"Active child processes: {0}".format(zombies))

                # =============================== Refresh Cycle ===============================
                self.csv_refresh()
                self.refreshTheCharts()
                self.sleep(15)

    # =============================================================================
    def sendDevicePing(self, dev_id=0, suppress_logging=False):

        indigo.server.log(u"Matplotlib Plugin devices do not support the ping function.")

        return {'result': 'Failure'}

    # =============================================================================
    def startup(self):

        self.maintain.clean_props()

    # =============================================================================
    def shutdown(self):

        self.logger.threaddebug(u"Shutdown call.")
        self.pluginIsShuttingDown = True

    # =============================================================================
    def validatePrefsConfigUi(self, values_dict=None):

        changed_keys   = ()
        config_changed = False
        error_msg_dict = indigo.Dict()

        self.debug_level = int(values_dict['showDebugLevel'])
        self.indigo_log_handler.setLevel(self.debug_level)

        self.logger.threaddebug(u"Validating plugin configuration parameters.")

        # ================================= Data Path =================================
        for path_prop in ('chartPath', 'dataPath'):
            try:
                if not values_dict[path_prop].endswith('/'):
                    error_msg_dict[path_prop]       = u"The path must end with a forward slash '/'."
                    error_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                    return False, values_dict, error_msg_dict

            except AttributeError:
                error_msg_dict[path_prop]       = u"The path must end with a forward slash '/'."
                error_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                return False, values_dict, error_msg_dict

        # ============================= Chart Resolution ==============================
        # Note that chart resolution includes a warning feature that will pass the
        # value after the warning is cleared.
        try:
            # If value is null, a null string, or all whitespace.
            if not values_dict['chartResolution'] or values_dict['chartResolution'] == "" or str(values_dict['chartResolution']).isspace():
                values_dict['chartResolution'] = "100"
                self.logger.warning(u"No resolution value entered. Resetting resolution to 100 DPI.")

            # If warning flag and the value is potentially too small.
            elif values_dict['dpiWarningFlag'] and 0 < int(values_dict['chartResolution']) < 80:
                error_msg_dict['chartResolution'] = u"It is recommended that you enter a value of 80 or more for best results."
                error_msg_dict['showAlertText']   = u"Chart Resolution Warning.\n\nIt is recommended that you enter a value of 80 or more for best results."
                values_dict['dpiWarningFlag']      = False
                return False, values_dict, error_msg_dict

            # If no warning flag and the value is good.
            elif not values_dict['dpiWarningFlag'] or int(values_dict['chartResolution']) >= 80:
                pass

            else:
                error_msg_dict['chartResolution'] = u"The chart resolution value must be greater than 0."
                error_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nThe chart resolution must be an integer greater than zero."
                return False, values_dict, error_msg_dict

        except ValueError:
            error_msg_dict['chartResolution'] = u"The chart resolution value must be an integer."
            error_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nThe chart resolution must be an integer greater than zero."
            return False, values_dict, error_msg_dict

        # ============================= Chart Dimensions ==============================
        for dimension_prop in ('rectChartHeight', 'rectChartWidth', 'rectChartWideHeight', 'rectChartWideWidth', 'sqChartSize'):
            try:
                if float(values_dict[dimension_prop]) < 75:
                    error_msg_dict[dimension_prop]  = u"The dimension value must be greater than 75 pixels."
                    error_msg_dict['showAlertText'] = u"Dimension Error.\n\nThe dimension value must be greater than 75 pixels"
                    return False, values_dict, error_msg_dict
            except ValueError:
                error_msg_dict[dimension_prop]  = u"The dimension value must be a real number."
                error_msg_dict['showAlertText'] = u"Dimension Error.\n\nThe dimension value must be a real number."
                return False, values_dict, error_msg_dict

        # ================================ Line Weight ================================
        try:
            if float(values_dict['lineWeight']) <= 0:
                error_msg_dict['lineWeight']    = u"The line weight value must be greater than zero."
                error_msg_dict['showAlertText'] = u"Line Weight Error.\n\nThe line weight value must be greater than zero"
                return False, values_dict, error_msg_dict
        except ValueError:
            error_msg_dict['lineWeight']    = u"The line weight value must be a real number."
            error_msg_dict['showAlertText'] = u"Line Weight Error.\n\nThe line weight value must be a real number"
            return False, values_dict, error_msg_dict

        # TODO: consider adding this feature to DLFramework and including in all plugins.
        # ============================== Log All Changes ==============================
        # Log any changes to the plugin preferences.
        for key in values_dict.keys():
            try:
                if values_dict[key] != self.pluginPrefs[key]:
                    config_changed = True
                    changed_keys += (u"{0}".format(key), u"Old: {0}".format(self.pluginPrefs[key]), u"New: {0}".format(values_dict[key]),)
            # Missing keys will be config dialog format props like labels and separators
            except KeyError:
                pass

        if config_changed:
            self.logger.threaddebug(u"values_dict changed: {0}".format(changed_keys))

        values_dict['dpiWarningFlag'] = True
        self.logger.threaddebug(u"Preferences validated successfully.")
        return True, values_dict

    # =============================================================================
    def validateDeviceConfigUi(self, values_dict=None, type_id="", dev_id=0):

        error_msg_dict = indigo.Dict()
        dev = indigo.devices[int(dev_id)]

        self.logger.threaddebug(u"Validating device configuration parameters.")

        # ================================= Bar Chart =================================
        if type_id == 'barChartingDevice':

            bar_1_source = values_dict['bar1Source']

            # Must select at least one source (bar 1)
            if bar_1_source == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, values_dict, error_msg_dict

            try:
                # Bar width must be greater than 0. Will also trap strings.
                bar_width = float(values_dict['barWidth'])

                if not bar_width >= 0:
                    raise ValueError

            except ValueError:
                error_msg_dict['barWidth'] = u"You must enter a bar width greater than 0."
                error_msg_dict['showAlertText'] = u"Bar Width Error.\n\nYou must enter a bar width greater than 0."
                return False, values_dict, error_msg_dict

        # =========================== Battery Health Chart ============================
        if type_id == 'batteryHealthDevice':

            for prop in ('cautionLevel', 'warningLevel'):
                try:
                    # Bar width must be greater than 0. Will also trap strings.
                    alert_level = float(values_dict[prop])

                    if not 0 <= alert_level <= 100:
                        raise ValueError

                except ValueError:
                    error_msg_dict[prop] = u"Alert levels must between 0 and 100 (integer)."
                    error_msg_dict['showAlertText'] = u"Alert Level Error.\n\nYou must enter an alert level between 0 and 100 (integer)."
                    return False, values_dict, error_msg_dict

        # ============================== Calendar Chart ===============================
        # There are currently no unique validation steps needed for calendar devices
        if type_id == 'calendarChartingDevice':
            pass

        # ================================ CSV Engine =================================
        if type_id == 'csvEngine':

            # ========================== Number of Observations ===========================
            try:
                # Will catch strings and floats cast as strings
                obs = int(values_dict['numLinesToKeep'])

                # Must be 1 or greater
                if obs < 1:
                    raise ValueError

            except ValueError:
                error_msg_dict['numLinesToKeep'] = u"The observation value must be a whole number integer greater than zero."
                error_msg_dict['showAlertText'] = u"Observation Value Error.\n\nThe observation value must be a whole number integer greater than zero."
                return False, values_dict, error_msg_dict

            # ================================= Duration ==================================
            try:
                duration = float(values_dict['numLinesToKeepTime'])

                # Must be zero or greater
                if duration < 0:
                    raise ValueError

            except ValueError:
                error_msg_dict['numLinesToKeepTime'] = u"The duration value must be an integer or float greater than zero."
                error_msg_dict['showAlertText'] = u"Duration Value Error.\n\nThe observation value must be an integer or float greater than zero."
                return False, values_dict, error_msg_dict

            self.logger.threaddebug(u"[{0}] Settings validated successfully.".format(dev.name))

            # ============================= Refresh Interval ==============================
            try:
                refresh = int(values_dict['refreshInterval'])

                # Must be zero or greater
                if refresh < 0:
                    raise ValueError

            except ValueError:
                error_msg_dict['refreshInterval'] = u"The refresh interval must be a whole number integer and greater than zero."
                error_msg_dict['showAlertText'] = u"Refresh interval Value Error.\n\nThe observation value must be a whole number integer and greater than zero."
                return False, values_dict, error_msg_dict

            # =============================== Data Sources ================================
            try:
                sources = literal_eval(values_dict['columnDict'])

                # columnDict may contain a place-holder dict with one entry, so we test for
                # that.
                if len(sources.keys()) < 2:
                    for key in sources.keys():
                        if sources[key] == ('None', 'None', 'None'):
                            raise ValueError

                    # If columnDict has no keys, we know that won't work either.
                    if len(sources.keys()) == 0:
                        raise ValueError

            except ValueError:
                error_msg_dict['addSource'] = u"You must create at least one CSV data source."
                error_msg_dict['showAlertText'] = u"You must create at least one CSV data source. If you have filled in the entries, you may have forgotten to click the 'Add Item' button."
                return False, values_dict, error_msg_dict

        # ================================ Line Chart =================================
        if type_id == 'lineChartingDevice':

            # There must be at least 1 source selected
            if values_dict['line1Source'] == 'None':
                error_msg_dict['line1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, values_dict, error_msg_dict

            # Iterate for each line group (1-6).
            for line in range(1, 7, 1):

                # Line adjustment values
                for char in values_dict['line{0}adjuster'.format(line)]:
                    if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                        error_msg_dict['line{0}adjuster'.format(line)] = u"Valid operators are +, -, *, /"
                        error_msg_dict['showAlertText'] = u"Adjuster Error.\n\nValid operators are +, -, *, /."
                        return False, values_dict, error_msg_dict

                # Fill is illegal for the steps line type
                if values_dict['line{0}Style'.format(line)] == 'steps' and values_dict['line{0}Fill'.format(line)]:
                    error_msg_dict['line{0}Fill'.format(line)] = u"Fill is not supported for the Steps line type."
                    error_msg_dict['line{0}Style'.format(line)] = u"Fill is not supported for the Steps line type."
                    error_msg_dict['showAlertText'] = u"Settings Conflict.\n\nFill is not supported for the Steps line style. Select a different line style or turn off the fill setting."
                    return False, values_dict, error_msg_dict

        # ============================== Multiline Text ===============================
        if type_id == 'multiLineText':

            for prop in ('thing', 'thingState'):

                # A data source must be selected
                if not values_dict[prop] or values_dict[prop] == 'None':
                    error_msg_dict[prop] = u"You must select a data source."
                    error_msg_dict['showAlertText'] = u"Source Error.\n\nYou must select a text source for charting."
                    return False, values_dict, error_msg_dict

            try:
                # Number of characters. Will catch strings and floats
                characters = int(values_dict['numberOfCharacters'])

                # Must be zero or greater
                if characters < 1:
                    raise ValueError

            except ValueError:
                error_msg_dict['numberOfCharacters'] = u"The number of characters must be a positive number greater than zero (integer)."
                error_msg_dict['showAlertText'] = u"Number of Characters Error.\n\nThe number of characters must be a positive number greater than zero (integer)."
                return False, values_dict, error_msg_dict

            # Figure width and height.
            for prop in ('figureWidth', 'figureHeight'):
                try:
                    # Will catch strings and floats
                    figure_size = int(values_dict[prop])

                    # Must be zero or greater
                    if figure_size < 1:
                        raise ValueError

                except ValueError:
                    error_msg_dict[prop] = u"The figure width and height must be positive whole numbers greater than zero (pixels)."
                    error_msg_dict['showAlertText'] = u"Figure Dimensions Error.\n\nThe figure width and height must be positive whole numbers greater than zero (pixels)."
                    return False, values_dict, error_msg_dict

            # Font size
            try:
                # Will catch strings
                font_size = float(values_dict['multilineFontSize'])

                # Must be zero or greater
                if font_size < 0:
                    raise ValueError

            except ValueError:
                error_msg_dict['multilineFontSize'] = u"The font size must be a positive real number greater than zero."
                error_msg_dict['showAlertText'] = u"Font Size Error.\n\nThe font size must be a positive real number greater than zero."
                return False, values_dict, error_msg_dict

        # ================================ Polar Chart ================================
        if type_id == 'polarChartingDevice':

            if not values_dict['thetaValue']:
                error_msg_dict['thetaValue'] = u"You must select a direction source."
                error_msg_dict['showAlertText'] = u"Direction Source Error.\n\nYou must select a direction source for charting."
                return False, values_dict, error_msg_dict

            if not values_dict['radiiValue']:
                error_msg_dict['radiiValue'] = u"You must select a magnitude source."
                error_msg_dict['showAlertText'] = u"Magnitude Source Error.\n\nYou must select a magnitude source for charting."
                return False, values_dict, error_msg_dict

            # Number of observations
            try:
                # Will catch strings and floats
                num_obs = int(values_dict['numObs'])

                # Must be 1 or greater
                if num_obs < 1:
                    error_msg_dict['numObs'] = u"You must specify at least 1 observation (must be a whole number integer)."
                    error_msg_dict['showAlertText'] = u"Number of Observations Error.\n\nYou must specify at least 1 observation (must be a whole number integer)."
                    return False, values_dict, error_msg_dict

            except ValueError:
                error_msg_dict['numObs'] = u"The number of observations must be a whole number integer)."
                error_msg_dict['showAlertText'] = u"Number of Observations Error.\n\nThe number of observations must be a whole number integer)."
                return False, values_dict, error_msg_dict

        # =============================== Scatter Chart ===============================
        if type_id == 'scatterChartingDevice':

            if not values_dict['group1Source']:
                error_msg_dict['group1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, values_dict, error_msg_dict

        # =============================== Weather Chart ===============================
        if type_id == 'forecastChartingDevice':

            if not values_dict['forecastSourceDevice']:
                error_msg_dict['forecastSourceDevice'] = u"You must select a weather forecast source device."
                error_msg_dict['showAlertText'] = u"Forecast Device Source Error.\n\nYou must select a weather forecast source device for charting."
                return False, values_dict, error_msg_dict

        # ============================== All Chart Types ==============================
        # The following validation blocks are applied to all graphical chart device
        # types.

        # ========================== Chart Custom Dimensions ==========================
        # Check to see that custom chart dimensions conform to valid types
        for custom_dimension_prop in ('customSizeHeight', 'customSizeWidth', 'customSizePolar'):
            try:
                if custom_dimension_prop in values_dict.keys() and values_dict[custom_dimension_prop] != 'None' and float(values_dict[custom_dimension_prop]) < 75:
                    error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be greater than 75 pixels."
                    error_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is less than 75 pixels."
                    return False, values_dict, error_msg_dict

            except ValueError:
                error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be a real number."
                error_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is not a real number."
                values_dict[custom_dimension_prop]     = 'None'
                return False, values_dict, error_msg_dict

        # ================================ Axis Limits ================================
        # Check to see that each axis limit matches one of the accepted formats
        for limit_prop in ('yAxisMax', 'yAxisMin', 'y2AxisMax', 'y2AxisMin'):

            # We only do these if the device has these props.
            if limit_prop in values_dict.keys():

                # Y axis limits can not be empty.
                if values_dict[limit_prop] == '' or values_dict[limit_prop].isspace():
                    self.logger.warning(u"Limits can not be empty. Setting empty limits to \"None.\"")
                    values_dict[limit_prop] = "None"

                # Y axis limits must be a value that can float.
                try:
                    if values_dict[limit_prop] not in ('None', '0'):
                        float(values_dict[limit_prop])

                except ValueError:
                    error_msg_dict[limit_prop]      = u"The axis limit must be a real number or None."
                    error_msg_dict['showAlertText'] = u"Axis limit Error.\n\n" \
                                                      u"A valid axis limit must be in the form of a real number or None ({0} = {1}).".format(limit_prop, values_dict[limit_prop])
                    values_dict[limit_prop] = 'None'
                    return False, values_dict, error_msg_dict

        self.logger.threaddebug(u"Preferences validated successfully.")
        return True, values_dict, error_msg_dict

    # =============================================================================
    def __log_dicts(self, dev=None):
        """
        Write parameters dicts to log under verbose logging

        Simple method to write rcParm and kwarg dicts to debug log.

        -----

        :param dev:
        """

        self.logger.threaddebug(u"[{0:<19}] Props: {1}".format(dev.name, dict(dev.ownerProps)))

    # =============================================================================
    def dummyCallback(self, values_dict=None, type_id="", target_id=0):
        """
        Dummy callback method to force dialog refreshes

        The purpose of the dummyCallback method is to provide something for
        configuration dialogs to call in order to force a refresh of any dynamic
        controls (dynamicReload=True).

        -----

        :param unicode type_id:
        :param class 'indigo.Dict' values_dict:
        :param int target_id:
        """

        pass

    # =============================================================================
    def advancedSettingsExecuted(self, values_dict=None, menu_id=0):
        """
        Save advanced settings menu items to plugin props for storage

        The advancedSettingsExecuted() method is a place where advanced settings will
        be controlled. This method takes the returned values and sends them to the
        pluginPrefs for permanent storage. Note that valuesDict here is for the menu,
        not all plugin prefs.

        -----

        :param class 'indigo.Dict' values_dict:
        :param int menu_id:
        """

        self.pluginPrefs['enableCustomLineSegments']  = values_dict['enableCustomLineSegments']
        self.pluginPrefs['promoteCustomLineSegments'] = values_dict['promoteCustomLineSegments']
        self.pluginPrefs['snappyConfigMenus']         = values_dict['snappyConfigMenus']
        self.pluginPrefs['forceOriginLines']          = values_dict['forceOriginLines']

        self.logger.threaddebug(u"Advanced settings menu final prefs: {0}".format(dict(values_dict)))
        return True

    # =============================================================================
    def advancedSettingsMenu(self, values_dict=None, type_id="", dev_id=0):
        """
        Write advanced settings menu selections to the log

        The advancedSettingsMenu() method is called when actions are taken within the
        Advanced Settings Menu item from the plugin menu.

        -----

        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int dev_id:
        """
        self.logger.threaddebug(u"Advanced settings menu final prefs: {0}".format(dict(values_dict)))
        return

    def commsKillAll(self):
        """
        Deactivate communication with all plugin devices

        commsKillAll() sets the enabled status of all plugin devices to false.

        -----

        """
        self.logger.info(u"Stopping communication with all plugin devices.")

        for dev in indigo.devices.itervalues("self"):
            try:
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                indigo.device.enable(dev, value=False)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.error(u"Exception when trying to kill all comms. Error: {0}. See plugin log for more information.".format(sub_error))

    # =============================================================================
    def commsUnkillAll(self):
        """
        Establish communication for all disabled plugin devices

        commsUnkillAll() sets the enabled status of all plugin devices to true.

        -----

        """

        self.logger.info(u"Starting communication with all plugin devices.")

        for dev in indigo.devices.itervalues("self"):
            try:
                indigo.device.enable(dev, value=True)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.error(u"Exception when trying to kill all comms. Error: {0}. See plugin log for more information.".format(sub_error))

    # =============================================================================
    def convert_custom_colors(self):
        """
        Convert legacy custom hex color values to raw color values

        Initially, the plugin was constructed with a standard set of colors that could
        be overwritten by selecting a custom color value. With the inclusion of the
        color picker control, this is no longer needed. So we try to set the color
        field to the custom value. This block is for plugin color preferences. Example:
        convert '#FFFFFF' to 'FF FF FF'.

        -----

        """

        if '#custom' in self.pluginPrefs.values():

            self.logger.threaddebug(u"Converting legacy custom color values.")

            for pref in self.pluginPrefs:
                if 'color' in pref.lower():
                    if self.pluginPrefs[pref] in['#custom', 'custom']:
                        self.logger.threaddebug(u"Adjusting existing color preferences to new color picker.")
                        if self.pluginPrefs['{0}Other'.format(pref)]:
                            self.pluginPrefs[pref] = self.pluginPrefs['{0}Other'.format(pref)]
                        else:
                            self.pluginPrefs[pref] = 'FF FF FF'

    # =============================================================================
    def csv_item_add(self, values_dict=None, type_id="", dev_id=0):
        """
        Add new item to CSV engine

        The csv_item_add() method is called when the user clicks on the 'Add Item'
        button in the CSV Engine config dialog.

        -----

        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int dev_id:
        """

        dev = indigo.devices[int(dev_id)]
        self.logger.threaddebug(u"[{0}] csv item add values_dict: {1}".format(dev.name, dict(values_dict)))

        error_msg_dict = indigo.Dict()

        try:
            column_dict = literal_eval(values_dict['columnDict'])  # Convert column_dict from a string to a literal dict
            lister = [0]
            num_lister = []

            # ================================ Validation =================================
            # Add data item validation.  Will not allow add until all three conditions are
            # met.
            if values_dict['addValue'] == "":
                error_msg_dict['addValue'] = u"Please enter a title value for your CSV data element."
                error_msg_dict['showAlertText'] = u"Title Error.\n\nA title is required for each CSV data element."
                return values_dict, error_msg_dict

            if values_dict['addSource'] == "":
                error_msg_dict['addSource'] = u"Please select a device or variable as a source for your CSV data element."
                error_msg_dict['showAlertText'] = u"ID Error.\n\nA source is required for each CSV data element."
                return values_dict, error_msg_dict

            if values_dict['addState'] == "":
                error_msg_dict['addState'] = u"Please select a value source for your CSV data element."
                error_msg_dict['showAlertText'] = u"Data Error.\n\nA data value is required for each CSV data element."
                return values_dict, error_msg_dict

            [lister.append(key.lstrip('k')) for key in sorted(column_dict.keys())]  # Create a list of existing keys with the 'k' lopped off
            [num_lister.append(int(item)) for item in lister]  # Change each value to an integer for evaluation
            next_key = u'k{0}'.format(int(max(num_lister)) + 1)  # Generate the next key
            column_dict[next_key] = (values_dict['addValue'], values_dict['addSource'], values_dict['addState'])  # Save the tuple of properties

            # Remove any empty entries as they're not going to do any good anyway.
            new_dict = {}

            for k, v in column_dict.iteritems():
                if v != (u"", u"", u"") and v != ('None', 'None', 'None'):
                    new_dict[k] = v
                else:
                    self.logger.info(u"Pruning CSV Engine.")

            values_dict['columnDict'] = str(new_dict)  # Convert column_dict back to a string and prepare it for storage.

        except AttributeError, sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"[{0}] Error adding CSV item: {1}. See plugin log for more information.".format(dev.name, sub_error))

        # If the appropriate CSV file doesn't exist, create it and write the header line.
        file_name = values_dict['addValue']
        full_path = "{0}{1}.csv".format(self.pluginPrefs['dataPath'], file_name.encode("utf-8"))

        if not os.path.isfile(full_path):

            with open(full_path, 'w') as outfile:
                outfile.write(u"{0},{1}\n".format('Timestamp', file_name).encode("utf-8"))

        # Wipe the field values clean for the next element to be added.
        for key in ('addSourceFilter', 'editSourceFilter'):
            values_dict[key] = "A"

        for key in ('addValue', 'addSource', 'addState'):
            values_dict[key] = u""

        return values_dict, error_msg_dict

    # =============================================================================
    def csv_item_delete(self, values_dict=None, type_id="", dev_id=0):
        """
        Deletes items from the CSV Engine configuration dialog

        The csv_item_delete() method is called when the user clicks on the "Delete
        Item" button in the CSV Engine config dialog.

        -----

        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int dev_id:
        """

        dev = indigo.devices[int(dev_id)]
        self.logger.threaddebug(u"[{0}] csv item delete values_dict: {1}".format(dev.name, dict(values_dict)))

        column_dict = literal_eval(values_dict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            values_dict["editKey"] = values_dict["csv_item_list"]
            del column_dict[values_dict['editKey']]

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"[{0}] Error deleting CSV item: {1}. See plugin log for more information.".format(dev.name, sub_error))

        values_dict['csv_item_list'] = ""
        values_dict['editKey']     = ""
        values_dict['editSource']  = ""
        values_dict['editState']   = ""
        values_dict['editValue']   = ""
        values_dict['previousKey'] = ""
        values_dict['columnDict']  = str(column_dict)  # Convert column_dict back to a string for storage.

        return values_dict

    # =============================================================================
    def csv_item_list(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Construct the list of CSV items

        The csv_item_list() method generates the list of Item Key : Item Value
        pairs that will be presented in the CVS Engine device config dialog. It's
        called at open and routinely as changes are made in the dialog.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        dev = indigo.devices[int(target_id)]

        try:
            values_dict['columnDict'] = values_dict.get('columnDict', '{}')  # Returning an empty dict seems to work and may solve the 'None' issue
            column_dict = literal_eval(values_dict['columnDict'])  # Convert column_dict from a string to a literal dict.
            prop_list   = [(key, "{0}".format(value[0].encode("utf-8"))) for key, value in column_dict.items()]

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"[{0}] Error generating CSV item list: {0}. See plugin log for more information.".format(dev.name, sub_error))
            prop_list = []

        result = sorted(prop_list, key=lambda tup: tup[1].lower())  # Return a list sorted by the value and not the key. Case insensitive sort.
        return result

    # =============================================================================
    def csv_item_update(self, values_dict=None, type_id="", dev_id=0):
        """
        Updates items from the CSV Engine configuration dialog

        When the user selects the 'Update Item' button, update the dict of CSV engine
        items.

        -----

        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int dev_id:
        """

        dev = indigo.devices[dev_id]
        self.logger.threaddebug(u"[{0}] csv item update values_dict: {1}".format(dev.name, dict(values_dict)))

        error_msg_dict = indigo.Dict()
        column_dict  = literal_eval(values_dict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            key = values_dict['editKey']
            previous_key = values_dict['previousKey']
            if key != previous_key:
                if key in column_dict:
                    error_msg_dict['editKey'] = u"New key ({0}) already exists in the global properties, please use a different key value".format(key)
                    values_dict['editKey']   = previous_key
                else:
                    del column_dict[previous_key]
            else:
                column_dict[key]            = (values_dict['editValue'], values_dict['editSource'], values_dict['editState'])
                values_dict['csv_item_list'] = ""
                values_dict['editKey']       = ""
                values_dict['editSource']    = ""
                values_dict['editState']     = ""
                values_dict['editValue']     = ""

            if not len(error_msg_dict):
                values_dict['previousKey'] = key

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"[{0}] Error updating CSV item: {1}. See plugin log for more information.".format(dev.name, sub_error))

        # Remove any empty entries as they're not going to do any good anyway.
        new_dict = {}

        for k, v in column_dict.iteritems():
            if v != ('', '', ''):
                new_dict[k] = v
        column_dict = new_dict

        # Convert column_dict back to a string for storage.
        values_dict['columnDict'] = str(column_dict)

        return values_dict, error_msg_dict

    # =============================================================================
    def csv_item_select(self, values_dict=None, type_id="", dev_id=0):
        """
        Populates CSV engine controls for updates and deletions

        The csv_item_select() method is called when the user actually selects something
        within the CSV engine Item List dropdown menu. When the user selects an item
        from the Item List, we populate the Title, ID, and Data controls with the
        relevant Item properties.

        -----

        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int dev_id:
        """

        dev = indigo.devices[int(dev_id)]
        self.logger.threaddebug(u"[{0}] csv item select values_dict: {1}".format(dev.name, dict(values_dict)))

        try:
            column_dict                    = literal_eval(values_dict['columnDict'])
            values_dict['editKey']          = values_dict['csv_item_list']
            values_dict['editSource']       = column_dict[values_dict['csv_item_list']][1]
            values_dict['editState']        = column_dict[values_dict['csv_item_list']][2]
            values_dict['editValue']        = column_dict[values_dict['csv_item_list']][0]
            values_dict['isColumnSelected'] = True
            values_dict['previousKey']      = values_dict['csv_item_list']

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"[{0}] There was an error establishing a connection with the item you chose: {1}. See plugin log for more information.".format(dev.name, sub_error))
        return values_dict

    # =============================================================================
    def csv_refresh(self):
        """
        Refreshes data for all CSV custom devices

        The csv_refresh() method manages CSV files through CSV Engine custom devices.

        -----

        """

        for dev in indigo.devices.itervalues("self"):

            refresh_interval = int(dev.pluginProps['refreshInterval'])

            if dev.deviceTypeId == 'csvEngine' and dev.enabled:

                try:
                    last_updated = date_parse(dev.states['csvLastUpdated'])

                except ValueError:
                    last_updated = date_parse('1970-01-01 00:00')

                diff = dt.datetime.now() - last_updated
                refresh_needed = diff > dt.timedelta(seconds=refresh_interval)

                if refresh_needed and refresh_interval != 0:

                    self.__log_dicts(dev)

                    dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                    # {key: (Item Name, Source ID, Source State)}
                    csv_dict_str = dev.pluginProps['columnDict']

                    # Convert column_dict from a string to a literal dict.
                    csv_dict = literal_eval(csv_dict_str)

                    self.logger.threaddebug(u"[{0}] Refreshing CSV Device: {1}".format(dev.name, dict(csv_dict)))
                    self.csv_refresh_process(dev, csv_dict)

    # =============================================================================
    def csv_refresh_process(self, dev, csv_dict):
        """
        The csv_refresh_process() method processes CSV update requests

         We import shutil here so that users who don't use CSV Engines don't need
         to import it.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict csv_dict:
        :return:
        """

        try:

            import shutil

            target_lines = int(dev.pluginProps.get('numLinesToKeep', '300'))
            delta        = float(dev.pluginProps.get('numLinesToKeepTime', '72'))
            cycle_time   = dt.datetime.now()

            # Read through the dict and construct headers and data
            for k, v in sorted(csv_dict.items()):

                # Create a path variable that is based on the target folder and the CSV item name.
                full_path = u"{0}{1}.csv".format(self.pluginPrefs['dataPath'], v[0])
                backup    = u"{0}{1} copy.csv".format(self.pluginPrefs['dataPath'], v[0])

                # ============================= Create (if needed) ============================
                # If the appropriate CSV file doesn't exist, create it and write the header
                # line.
                if not os.path.isdir(self.pluginPrefs['dataPath']):
                    try:
                        os.makedirs(self.pluginPrefs['dataPath'])
                        self.logger.warning(u"Target data folder does not exist. Creating it.")

                    except IOError:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.critical(u"[{0}] Target data folder does not exist and the plugin is unable to create it. See plugin log for more information.".format(dev.name))

                if not os.path.isfile(full_path):
                    self.logger.debug(u"CSV does not exist. Creating: {0}".format(full_path))
                    csv_file = open(full_path, 'w')
                    csv_file.write('{0},{1}\n'.format('Timestamp', v[0].encode("utf-8")))
                    csv_file.close()
                    self.sleep(1)

                # =============================== Create Backup ===============================
                # Make a backup of the CSV file in case something goes wrong.
                try:
                    shutil.copyfile(full_path, backup)

                except ImportError as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.error(u"[{0}] The CSV Engine facility requires the shutil module: {1}. See plugin log for more information.".format(dev.name, sub_error))

                except Exception as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.error(u"[{0}] Unable to backup CSV file: {1}. See plugin log for more information.".format(dev.name, sub_error))

                # ================================= Load Data =================================
                # Read CSV data into dataframe
                with open(full_path) as in_file:
                    raw_data = [row for row in csv.reader(in_file, delimiter=',')]

                # Split the headers and the data
                column_names = raw_data[:1]
                data         = raw_data[1:]

                # Coerce header 0 to be 'Timestamp'
                if column_names[0][0] != u'Timestamp':
                    column_names[0][0] = u'Timestamp'

                # ============================== Limit for Time ===============================
                # Limit data by time
                if delta > 0:
                    cut_off = dt.datetime.now() - dt.timedelta(hours=delta)
                    time_data = [row for row in data if date_parse(row[0]) >= cut_off]

                    # If all records are older than the delta, return the original data (so
                    # there's something to chart) and send a warning to the log.
                    if len(time_data) == 0:
                        self.logger.debug(u"[{0} - {1}] all CSV data are older than the time limit. Returning original data.".format(dev.name, column_names[0][1].decode('utf-8')))
                    else:
                        data = time_data

                # ============================ Add New Observation ============================
                # Determine if the thing to be written is a device or variable.
                try:
                    state_to_write = u""

                    if not v[1]:
                        self.logger.warning(u"Found CSV Data element with missing source ID. Please check to ensure all CSV sources are properly configured.")

                    elif int(v[1]) in indigo.devices:
                        state_to_write = u"{0}".format(indigo.devices[int(v[1])].states[v[2]])

                    elif int(v[1]) in indigo.variables:
                        state_to_write = u"{0}".format(indigo.variables[int(v[1])].value)

                    else:
                        self.logger.critical(u"The settings for CSV Engine data element '{0}' are not valid: [dev: {1}, state/value: {2}]".format(v[0], v[1], v[2]))

                    # Give matplotlib something it can chew on if the value to be saved is 'None'
                    if state_to_write in ('None', None, u""):
                        state_to_write = 'NaN'

                    # Add the newest observation to the end of the data list.
                    now = dt.datetime.strftime(cycle_time, '%Y-%m-%d %H:%M:%S.%f')
                    data.append([now, state_to_write])

                except ValueError as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.error(u"[{0}] Invalid Indigo ID: {1}. See plugin log for more information.".format(dev.name, sub_error))

                except Exception as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.error(u"[{0}] Invalid CSV definition: {1}".format(dev.name, sub_error))

                # ============================= Limit for Length ==============================
                # The dataframe (with the newest observation included) may now be too long.
                # If it is, we trim it for length.
                if 0 <= target_lines < len(data):
                    data = data[len(data) - target_lines:]

                # ================================ Write Data =================================
                # Write CSV data to file

                with open(full_path, 'w') as out_file:
                    writer = csv.writer(out_file, delimiter=',')
                    writer.writerows(column_names)
                    writer.writerows(data)

                # =============================== Delete Backup ===============================
                # If all has gone well, delete the backup.
                try:
                    os.remove(backup)

                except Exception as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.error(u"[{0}] Unable to delete backup file. {1}".format(dev.name, sub_error))

            dev.updateStatesOnServer([{'key': 'csvLastUpdated', 'value': u"{0}".format(dt.datetime.now())},
                                      {'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])

            self.logger.info(u"[{0}] CSV data updated successfully.".format(dev.name))
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

        except ValueError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"[{0}] Error: {1}".format(dev.name, sub_error))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"[{0}] Error: {1}".format(dev.name, sub_error))

    # =============================================================================
    def csv_refresh_device_action(self, plugin_action, dev, caller_waiting_for_result=False):
        """
        Perform a manual refresh of a single CSV Device

        The csv_refresh_device_action() method will allow for the update of a single
        CSV Engine device. This method will update all CSV sources associated with the
        selected CSV Engine device each time the Action item is called. Only CSV Engine
        devices set to a manual refresh interval will be presented.

        -----

        :param class 'indigo.PluginAction' plugin_action:
        :param class 'indigo.Device' dev:
        :param bool caller_waiting_for_result:
        :return:
        """

        dev = indigo.devices[int(plugin_action.props['targetDevice'])]

        if dev.enabled:

            # {key: (Item Name, Source ID, Source State)}
            csv_dict_str = dev.pluginProps['columnDict']

            # Convert column_dict from a string to a literal dict.
            csv_dict = literal_eval(csv_dict_str)

            self.csv_refresh_process(dev, csv_dict)

        else:
            self.logger.warning(u'CSV data not updated. Reason: target device disabled.')

    # =============================================================================
    def csv_refresh_source_action(self, plugin_action, dev, caller_waiting_for_result=False):
        """
        Perform a manual refresh of a single CSV Source

        The csv_refresh_source_action() method will allow for the update of a single
        CSV source from a CSV Engine device. When creating a new Action item, the user
        selects a target CSV Engine device and then the available CSV sources will be
        displayed. The user selects a single CSV source that will be updated each time
        the Action is called. Only CSV Engine devices set to a manual refresh interval
        will be presented.

        -----

        :param class 'indigo.PluginAction' plugin_action:
        :param class 'indigo.Device' dev:
        :param bool caller_waiting_for_result:

        :return:
        """

        dev_id = int(plugin_action.props['targetDevice'])
        dev    = indigo.devices[dev_id]

        if dev.enabled:
            target_source = plugin_action.props['targetSource']
            temp_dict     = literal_eval(dev.pluginProps['columnDict'])
            foo           = {target_source: temp_dict[target_source]}

            self.csv_refresh_process(dev, foo)
            self.logger.info(u"CSV refresh source action complete.")

        else:
            self.logger.warning(u'CSV data not updated. Reason: target device disabled.')

    # =============================================================================
    def csv_source(self, type_id="", values_dict=None, dev_id=0, target_id=0):
        """
        Construct a list of devices and variables for the CSV engine

        Constructs a list of devices and variables for the user to select within the
        CSV engine configuration dialog box. Devices and variables are listed in
        alphabetical order with devices first and then variables. Devices are prepended
        with '(D)' and variables with '(V)'. Category labels are also included for
        visual clarity.

        -----

        :param unicode type_id:
        :param class 'indigo.Dict' values_dict:
        :param int dev_id:
        :param int target_id:
        """

        list_ = list()

        if values_dict.get('addSourceFilter', 'A') == "D":
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{0}".format(dev.name))) for dev in indigo.devices.iter()]

        elif values_dict.get('addSourceFilter', 'A') == "V":
            [list_.append(t) for t in [(u"-3", u"%%separator%%"), (u"-4", u"%%disabled:Variables%%"), (u"-5", u"%%separator%%")]]
            [list_.append((var.id, u"{0}".format(var.name))) for var in indigo.variables.iter()]

        else:
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{0}".format(dev.name))) for dev in indigo.devices.iter()]

            [list_.append(t) for t in [(u"-3", u"%%separator%%"), (u"-4", u"%%disabled:Variables%%"), (u"-5", u"%%separator%%")]]
            [list_.append((var.id, u"{0}".format(var.name))) for var in indigo.variables.iter()]

        return list_

    # =============================================================================
    def csv_source_edit(self, type_id="", values_dict=None, dev_id=0, target_id=0):
        """
        Construct a list of devices and variables for the CSV engine

        Constructs a list of devices and variables for the user to select within the
        CSV engine configuration dialog box. Devices and variables are listed in
        alphabetical order with devices first and then variables. Devices are prepended
        with '(D)' and variables with '(V)'. Category labels are also included for
        visual clarity.

        -----

        :param unicode type_id:
        :param class 'indigo.Dict' values_dict:
        :param int dev_id:
        :param int target_id:
        """

        list_ = list()

        if values_dict.get('editSourceFilter', 'A') == "D":
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{0}".format(dev.name))) for dev in indigo.devices.iter()]

        elif values_dict.get('editSourceFilter', 'A') == "V":
            [list_.append(t) for t in [(u"-3", u"%%separator%%"), (u"-4", u"%%disabled:Variables%%"), (u"-5", u"%%separator%%")]]
            [list_.append((var.id, u"{0}".format(var.name))) for var in indigo.variables.iter()]

        else:
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{0}".format(dev.name))) for dev in indigo.devices.iter()]

            [list_.append(t) for t in [(u"-3", u"%%separator%%"), (u"-4", u"%%disabled:Variables%%"), (u"-5", u"%%separator%%")]]
            [list_.append((var.id, u"{0}".format(var.name))) for var in indigo.variables.iter()]

        return list_

    # =============================================================================
    def get_csv_device_list(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of CSV Engine devices set to manual refresh

        The get_csv_device_list() method returns a list of CSV Engine devices with a
        manual refresh interval.

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param target_id:
        :return:
        """

        # Return a list of tuples that contains only CSV devices set to manual refresh
        # (refreshInterval = 0) for config menu.
        return [(dev.id, dev.name) for dev in indigo.devices.iter("self") if dev.deviceTypeId == "csvEngine" and dev.pluginProps['refreshInterval'] == "0"]

    # =============================================================================
    def get_csv_source_list(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of CSV sources from CSV Engine devices set to manual refresh

        The get_csv_source_list() method returns a list of CSV sources for the target
        CSV Engine device.

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param target_id:
        :return:
        """

        if not values_dict:
            return []

        # Once user selects a device ( see get_csv_device_list() ), populate the dropdown
        # menu.
        else:
            target_device = int(values_dict['targetDevice'])
            dev           = indigo.devices[target_device]
            dev_dict      = literal_eval(dev.pluginProps['columnDict'])

            return [(k, dev_dict[k][0]) for k in dev_dict]

    # =============================================================================
    def deviceStateValueListAdd(self, type_id="", values_dict=None, dev_id=0, target_id=0):
        """
        Formulates list of device states for CSV engine

        Once a user selects a device or variable within the CSV engine configuration
        dialog, we need to obtain the relevant device states to chose from. If the
        user selects a variable, we simply return the variable value identifier. The
        return is a list of tuples of the form:

        -----

        :param unicode type_id:
        :param class 'indigo.Dict' values_dict:
        :param int dev_id:
        :param int target_id:
        """

        if values_dict['addSource'] != u'':
            try:
                # User has selected an Indigo device element and then set the filter to Variables only.
                if int(values_dict['addSource']) in indigo.devices and values_dict['addSourceFilter'] == "V":
                    return [('None', u'Please select a data source first')]

                # User has selected an Indigo device element and the filter is set to Devices only or Show All.
                elif int(values_dict['addSource']) in indigo.devices and values_dict['addSourceFilter'] != "V":
                    dev = indigo.devices[int(values_dict['addSource'])]
                    return [x for x in dev.states.keys() if ".ui" not in x]

                elif int(values_dict['addSource']) in indigo.variables and values_dict['addSourceFilter'] != "D":
                    return [('value', 'value')]

                elif int(values_dict['addSource']) in indigo.variables and values_dict['addSourceFilter'] == "D":
                    return [('None', u'Please select a data source first')]

            except ValueError:
                return [('None', u'Please select a data source first')]

        else:
            return [('None', u'Please select a data source first')]

    # =============================================================================
    def deviceStateValueListEdit(self, type_id="", values_dict=None, dev_id=0, target_id=0):
        """
        Formulates list of device states for CSV engine

        Once a user selects a device or variable within the CSV engine configuration
        dialog, we need to obtain the relevant device states to chose from. If the
        user selects a variable, we simply return the variable value identifier. The
        return is a list of tuples of the form:

        -----

        :param unicode type_id:
        :param class 'indigo.Dict' values_dict:
        :param int dev_id:
        :param int target_id:
        """

        if values_dict['editSource'] != u'':
            try:
                # User has selected an Indigo device element and then set the filter to Variables only.
                if int(values_dict['editSource']) in indigo.devices and values_dict['editSourceFilter'] == "V":
                    return [('None', u'Please select a data source first')]

                # User has selected an Indigo device element and the filter is set to Devices only or Show All.
                elif int(values_dict['editSource']) in indigo.devices and values_dict['editSourceFilter'] != "V":
                    dev = indigo.devices[int(values_dict['editSource'])]
                    return [x for x in dev.states.keys() if ".ui" not in x]

                elif int(values_dict['editSource']) in indigo.variables and values_dict['editSourceFilter'] != "D":
                    return [('value', 'value')]

                elif int(values_dict['editSource']) in indigo.variables and values_dict['editSourceFilter'] == "D":
                    return [('None', u'Please select a data source first')]

            except ValueError:
                return [('None', u'Please select a data source first')]

        else:
            return [('None', u'Please select a data source first')]

    # =============================================================================
    def formatMarkers(self, p_dict):
        """
        Format matplotlib markers

        The devices.xml file cannot contain '<' or '>' as a value, as this conflicts
        with the construction of the XML code. Matplotlib needs these values for
        select built-in marker styles, so we need to change them to what MPL is
        expecting.

        -----

        :param p_dict:
        """

        markers     = ('line1Marker', 'line2Marker', 'line3Marker', 'line4Marker', 'line5Marker',
                       'line6Marker', 'group1Marker', 'group2Marker', 'group3Marker', 'group4Marker')
        marker_dict = {"PIX": ",", "TL": "<", "TR": ">"}

        for marker in markers:
            try:
                if p_dict[marker] in marker_dict.keys():
                    p_dict[marker] = marker_dict[p_dict[marker]]

            except KeyError:
                pass

        return p_dict

    # =============================================================================
    def generatorDeviceStates(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of device states for the provided device or variable id.

        The generatorDeviceStates() method returns a list of device states each list
        includes only states for the selected device. If a variable id is provided, the
        list returns one element.

        Returns:
          [('dev state name', 'dev state name'), ('dev state name', 'dev state name')]
        or
          [('value', 'value')]

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        try:
            dev_id = values_dict['thing']
            return self.Fogbert.generatorStateOrValue(dev_id)
        except KeyError:
            return [("Select a Source Above", "Select a Source Above")]

    # =============================================================================
    def generatorDeviceList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of Indigo variables.

        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::

            [(dev.id, dev.name), (dev.id, dev.name)].

        The list is generated within the DLFramework module.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.deviceList()

    # =============================================================================
    def generatorDeviceAndVariableList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Create a list of devices and variables for config menu controls

        Provides a list of Indigo devices and variables for various dropdown menus. The
        method is agnostic as to whether the devices and variables are enabled or
        disabled. All devices are listed first and then all variables. The method
        returns a list of tuples in the form::

            [(dev.id, dev.name), (var.id, var.name)].

        It prepends (D) or (V) to make it easier to distinguish between the two.

        The list is generated within the DLFramework module.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.deviceAndVariableList()

    # =============================================================================
    def generatorVariableList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of Indigo variables.

        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::

            [(var.id, var.name), (var.id, var.name)].

        The list is generated within the DLFramework module.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.variableList()

    # =============================================================================
    def getAxisList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of axis formats.

        Returns a list of Python date formatting strings for use in plotting date
        labels.  The list does not include all Python format specifiers.

        -----

        :param str filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        axis_list_menu = [("None", "None"),
                          ("-1", "%%separator%%"),
                          ("%I:%M", "01:00"),
                          ("%l:%M %p", "1:00 pm"),
                          ("%H:%M", "13:00"),
                          ("%a", "Sun"),
                          ("%A", "Sunday"),
                          ("%b", "Jan"),
                          ("%B", "January"),
                          ("%d", "16"),
                          ("%Y", "2016"),
                          ("%b %d", "Jan 16"),
                          ("%b %d %Y", "Jan 16 2019"),
                          ("%y %b", "16 Jan"),
                          ("%Y %b %d", "2019 Jan 16")]

        return axis_list_menu

    # =============================================================================
    def getBatteryDeviceList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Create a list of battery-powered devices

        Creates a list of tuples that contains the device ID and device name of all
        Indigo devices that report a batterLevel device property that is not None.
        If no devices meet the criteria, a single tuple is returned as a place-
        holder.

        -----
        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        batt_list = [(dev.id, dev.name) for dev in indigo.devices.iter() if dev.batteryLevel is not None]

        if len(batt_list) == 0:
            batt_list = [(-1, 'No battery devices detected.'), ]

        return batt_list

    # =============================================================================
    def getBinList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of bins for the X axis.

        Returns a list of bins for the X axis. We assume time, so only time-based bins
        are provided. The list is constrained.
        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        bin_list_menu = [("quarter-hourly", "Every 15 Minutes"),
                         ("half-hourly", "Every 30 Minutes"),
                         ("hourly", "Every Hour"),
                         ("hourly_4", "Every 4 Hours"),
                         ("hourly_8", "Every 8 Hours"),
                         ("hourly_12", "Every 12 Hours"),
                         ("daily", "Every Day"),
                         ("weekly", "Every Week"),
                         ("monthly", "Every Month"),
                         ("yearly", "Every Year")]

        return bin_list_menu

# =============================================================================
    def getFileList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Get list of CSV files for various dropdown menus.

        Generates a list of CSV source files that are located in the folder specified
        within the plugin configuration dialog. If the method is unable to find any CSV
        files, an empty list is returned.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        file_name_list_menu = []
        source_path = self.pluginPrefs.get('dataPath', '{0}/com.fogbert.indigoplugin.matplotlib/'.format(indigo.server.getLogsFolderPath()))

        try:
            import glob
            import os

            for file_name in glob.glob(u"{0}{1}".format(source_path, '*.csv')):
                final_filename = os.path.basename(file_name)
                file_name_list_menu.append((final_filename, final_filename[:-4]))

            # Sort the file list
            file_name_list_menu = sorted(file_name_list_menu, key=lambda s: s[0].lower())  # Case insensitive sort

            # Add 'None' as an option, and show it first in list
            file_name_list_menu = file_name_list_menu + [(u"-5", u"%%separator%%"), (u"None", u"None")]

        except IOError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"Error generating file list: {0}. See plugin log for more information.".format(sub_error))

        # return sorted(file_name_list_menu, key=lambda s: s[0].lower())  # Case insensitive sort
        return file_name_list_menu

    # =============================================================================
    def getFontList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Provide a list of font names for various dropdown menus.

        Note that these are the fonts that Matplotlib can see, not necessarily all of
        the fonts installed on the system. If matplotlib can't find any fonts, then a
        default list of fonts that matplotlib supports natively are provided.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        font_menu = []

        try:
            from os import path

            for font in mfont.findSystemFonts(fontpaths=None, fontext='ttf'):
                font_name = path.splitext(path.basename(font))[0]
                if font_name not in font_menu:
                    font_menu.append(font_name)

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"Error building font list.  Returning generic list. {0}. See plugin log for more information.".format(sub_error))

            font_menu = ['Arial',
                         'Apple Chancery',
                         'Andale Mono',
                         'Bitstream Vera Sans',
                         'Bitstream Vera Sans Mono',
                         'Bitstream Vera Serif',
                         'Century Schoolbook L',
                         'Charcoal',
                         'Chicago',
                         'Comic Sans MS',
                         'Courier',
                         'Courier New',
                         'cursive',
                         'fantasy',
                         'Felipa',
                         'Geneva',
                         'Helvetica',
                         'Humor Sans',
                         'Impact',
                         'Lucida Grande',
                         'Lucid',
                         'New Century Schoolbook',
                         'Nimbus Mono L',
                         'Sand',
                         'Script MT',
                         'Textile',
                         'Verdana',
                         'Western',
                         'Zapf Chancery']

        return sorted(font_menu)

    # =============================================================================
    def getFontSizeList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of font sizes.

        Provides a list of font size values for various dropdown menus. The list is
        constrained to values that are reasonably attractive (6pt - 20pt).

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return [(str(_), str(_)) for _ in np.arange(6, 21)]

    # =============================================================================
    def getForecastSource(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of WUnderground devices for forecast chart devices

        Generates and returns a list of potential forecast devices for the forecast
        devices type. Presently, the plugin only works with WUnderground devices, but
        the intention is to expand the list of compatible devices going forward.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        forecast_source_menu = []

        # We accept both WUnderground (legacy) and Fantastic Weather devices. We have to
        # construct these one at a time.
        try:
            for dev in indigo.devices.itervalues("com.fogbert.indigoplugin.fantasticwWeather"):
                if dev.deviceTypeId in ('Daily', 'Hourly'):
                    forecast_source_menu.append((dev.id, dev.name))

            for dev in indigo.devices.itervalues("com.fogbert.indigoplugin.wunderground"):
                if dev.deviceTypeId in ('wundergroundTenDay', 'wundergroundHourly'):
                    forecast_source_menu.append((dev.id, dev.name))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.error(u"Error getting list of forecast devices: {0}. See plugin log for more information.".format(sub_error))

        self.logger.threaddebug(u"Forecast device list generated successfully: {0}".format(forecast_source_menu))
        self.logger.threaddebug(u"forecast_source_menu: {0}".format(forecast_source_menu))

        return sorted(forecast_source_menu, key=lambda s: s[1].lower())

    # =============================================================================
    def getLineList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of line styles.

        Provide a list of matplotlib line styles for various dropdown menus. This is
        not an exhaustive list of styles that the current version of matplotlib
        supports; rather, a subset that are known to work with earlier versions that
        ship with OS X.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return [("None", "None"),
                ("-1", "%%separator%%"),
                ("--", "Dashed"),
                (":", "Dotted"),
                ("-.", "Dot Dash"),
                ("-", "Solid"),
                ("steps", "Steps"),
                ("steps-mid", "Steps Mid"),
                ("steps-post", "Steps Post")]

    # =============================================================================
    def getMarkerList(self, filter="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of marker styles.

        Provide a list of matplotlib marker styles for various dropdown menus. This is
        not an exhaustive list of styles that the current version of matplotlib
        supports; rather, a subset that are known to work with earlier versions that
        ship with OS X.

        -----

        :param unicode filter:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return [("None", "None"),
                ("-1", "%%separator%%"),
                ("o", "Circle"),
                ("D", "Diamond"),
                ("d", "Diamond (Thin)"),
                ("h", "Hexagon 1"),
                ("H", "Hexagon 2"),
                ("-", "Horizontal Line"),
                ("8", "Octagon"),
                ("p", "Pentagon"),
                ("PIX", "Pixel"),
                ("+", "Plus"),
                (".", "Point"),
                ("*", "Star"),
                ("s", "Square"),
                ("v", "Triangle Down"),
                ("TL", "Triangle Left"),
                ("TR", "Triangle Right"),
                ("1", "Tri Down"),
                ("2", "Tri Up"),
                ("3", "Tri Left"),
                ("4", "Tri Right"),
                ("|", "Vertical Line"),
                ("x", "X")]

    # =============================================================================
    def plotActionTest(self, plugin_action, dev, caller_waiting_for_result=False):
        """
        Plugin API handler

        A container for simple API calls to the matplotlib plugin. All payload elements
        are required, although kwargs can be an empty dict if no kwargs desired. If
        caller is waiting for a result (recommended), returns a dict.

        Receives::

            payload = {'x_values': [1, 2, 3],
                       'y_values': [2, 4, 6],
                       'kwargs': {'linestyle': 'dashed',
                                  'color': 'b',
                                  'marker': 's',
                                  'markerfacecolor': 'b'},
                       'path': '/full/path/name/',
                       'filename': 'chart_filename.png'}

        -----

        :param class 'indigo.PluginAction' plugin_action:
        :param class 'indigo.Device' dev:
        :param bool caller_waiting_for_result:
        """

        self.logger.threaddebug(u"Scripting payload: {0}".format(dict(plugin_action.props)))

        try:
            plt.plot(plugin_action.props['x_values'], plugin_action.props['y_values'], **plugin_action.props['kwargs'])
            plt.savefig(u"{0}{1}".format(plugin_action.props['path'], plugin_action.props['filename']))
            plt.close('all')

        except Exception as sub_error:
            if caller_waiting_for_result:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.error(u"[{0}] Error: {0}. See plugin log for more information.".format(dev.name, sub_error))
                return {'success': False, 'message': u"{0}".format(sub_error)}

        if caller_waiting_for_result:
            return {'success': True, 'message': u"Success"}

    # =============================================================================
    def pluginEnvironmentLogger(self):
        """
        Log information about the plugin resource environment.

        Write select information about the environment that the plugin is running in.
        This method is only called once, when the plugin is first loaded (or reloaded).

        -----

        :var int chart_devices:
        :var int csv_devices:
        """

        chart_devices = 0
        csv_engines   = 0

        # ========================== Get Plugin Device Load ===========================
        for dev in indigo.devices.iter('self'):
            if dev.ownerProps['isChart']:
                chart_devices += 1
            elif dev.deviceTypeId == 'csvEngine':
                csv_engines += 1

        self.logger.info(u"")
        self.logger.info(u"{0:{1}^135}".format(" Matplotlib Environment ", "="))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib version:", plt.matplotlib.__version__))
        self.logger.info(u"{0:<31} {1}".format("Numpy version:", np.__version__))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib RC Path:", plt.matplotlib.matplotlib_fname()))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin log location:", indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')))
        self.logger.info(u"{0:<31} {1}".format("Number of Chart Devices:", chart_devices))
        self.logger.info(u"{0:<31} {1}".format("Number of CSV Engine Devices:", csv_engines))
        self.logger.threaddebug(u"{0:<31} {1}".format("Matplotlib base rcParams:", dict(rcParams)))  # rcParams is a dict containing all of the initial matplotlibrc settings
        self.logger.threaddebug(u"{0:<31} {1}".format('Initial Plugin Prefs:', dict(self.pluginPrefs)))
        self.logger.info(u"{0:{1}^135}".format("", "="))

    # =============================================================================
    def pluginErrorHandler(self, sub_error):
        """
        Centralized handling of traceback messages

        Centralized handling of traceback messages formatted for pretty display in the
        plugin log file. If sent here, they will not be displayed in the Indigo Events
        log. Use the following syntax to send exceptions here::

            self.pluginErrorHandler(traceback.format_exc())

        -----

        :param traceback object sub_error:
        """

        sub_error = sub_error.splitlines()
        self.logger.critical(u"{0:!^80}".format(" TRACEBACK "))

        for line in sub_error:
            self.logger.critical(u"!!! {0}".format(line))

        self.logger.critical(u"!" * 80)

    # =============================================================================
    def processLogQueue(self, dev, return_queue):
        """
        Process output of multiprocessing queue messages

        The processLogQueue() method accepts a multiprocessing queue that contains log
        messages. The method parses those messages across the various self.logger.x
        calls.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param class 'multiprocessing.queues.Queue' return_queue:
        """

        # ======================= Process Output Queue ========================
        if dev.deviceTypeId != 'rcParamsDevice':
            result = return_queue.get()

            for event in result['Log']:
                for thing in result['Log'][event]:
                    if event == 'Threaddebug':
                        self.logger.threaddebug(u"[{0}] {1}".format(dev.name, thing))

                    elif event == 'Debug':
                        self.logger.debug(u"[{0}] {1}".format(dev.name, thing))

                    elif event == 'Info':
                        self.logger.info(u"[{0}] {1}".format(dev.name, thing))

                    elif event == 'Warning':
                        self.logger.warning(u"[{0}] {1}".format(dev.name, thing))

                    else:
                        self.logger.critical(u"[{0}] {1}".format(dev.name, thing))

            if result['Error']:
                self.logger.warning(u"[{0}] {1}".format(dev.name, result['Message']))
            else:
                self.logger.info(u"[{0}] {1}".format(dev.name, result['Message']))

    # =============================================================================
    def rcParamsDeviceUpdate(self, dev):
        """
        Update rcParams device with updated state values

        Push the rcParams settings to the rcParams Device. The state names have already
        been created by getDeviceStateList() which will ensure that future rcParams
        will be picked up if they're ever added to the file.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        """

        state_list = []
        for key, value in rcParams.iteritems():
            key = key.replace('.', '_')
            state_list.append({'key': key, 'value': str(value)})
            dev.updateStatesOnServer(state_list)

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])

    # =============================================================================
    def refreshAChartAction(self, plugin_action):
        """
        Refreshes an individual plugin chart device.

        Process Indigo Action item call for a chart refresh. Passes the id of the
        device called from the action. This method is a handler to pass along the
        action call. The action will refresh only the specified chart.

        -----

        :param class 'indigo.PluginAction' plugin_action:
        """

        # Indigo will trap if device is disabled.
        dev = indigo.devices[plugin_action.deviceId]
        self.refreshTheCharts([dev])

    # =============================================================================
    def refresh_the_charts_now(self):
        """
        Refresh all enabled charts

        Refresh all enabled charts based on some user action (like an Indigo menu
        call).

        -----

        :return:
        """
        self.skipRefreshDateUpdate = True
        devices_to_refresh = [dev for dev in indigo.devices.itervalues('self') if dev.enabled and dev.deviceTypeId != 'csvEngine']
        self.refreshTheCharts(devices_to_refresh)
        self.logger.info(u"{0:{1}^80}".format(' Redraw Charts Now Menu Action Complete ', '='))

    # =============================================================================
    def refreshTheCharts(self, dev_list=None):
        """
        Refreshes all the plugin chart devices.

        Iterate through each chart device and refresh the image. Only enabled chart
        devices will be refreshed.

        -----

        :param list dev_list: list of devices to be refreshed.
        """

        return_queue = multiprocessing.Queue()

        k_dict  = {}  # A dict of kwarg dicts
        p_dict  = dict(self.pluginPrefs)  # A dict of plugin preferences (we set defaults and override with pluginPrefs).

        try:
            p_dict['font_style']  = 'normal'
            p_dict['font_weight'] = 'normal'
            p_dict['tick_bottom'] = 'on'
            p_dict['tick_left']   = 'on'
            p_dict['tick_right']  = 'off'
            p_dict['tick_top']    = 'off'

            # ============================ rcParams overrides =============================
            plt.rcParams['grid.linestyle']   = self.pluginPrefs.get('gridStyle', ':')
            plt.rcParams['lines.linewidth']  = float(self.pluginPrefs.get('lineWeight', '1'))
            plt.rcParams['savefig.dpi']      = int(self.pluginPrefs.get('chartResolution', '100'))
            plt.rcParams['xtick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
            plt.rcParams['ytick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
            plt.rcParams['xtick.minor.size'] = plt.rcParams['xtick.major.size'] / 2
            plt.rcParams['ytick.minor.size'] = plt.rcParams['ytick.major.size'] / 2
            plt.rcParams['xtick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))
            plt.rcParams['ytick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))

            plt.rcParams['grid.color']  = r"#{0}".format(self.pluginPrefs.get('gridColor', '88 88 88').replace(' ', '').replace('#', ''))
            plt.rcParams['xtick.color'] = r"#{0}".format(self.pluginPrefs.get('tickColor', '88 88 88').replace(' ', '').replace('#', ''))
            plt.rcParams['ytick.color'] = r"#{0}".format(self.pluginPrefs.get('tickColor', '88 88 88').replace(' ', '').replace('#', ''))

            p_dict['faceColor']           = r"#{0}".format(self.pluginPrefs.get('faceColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            p_dict['fontColor']           = r"#{0}".format(self.pluginPrefs.get('fontColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            p_dict['fontColorAnnotation'] = r"#{0}".format(self.pluginPrefs.get('fontColorAnnotation', 'FF FF FF').replace(' ', '').replace('#', ''))
            p_dict['gridColor']           = r"#{0}".format(self.pluginPrefs.get('gridColor', '88 88 88').replace(' ', '').replace('#', ''))
            p_dict['spineColor']          = r"#{0}".format(self.pluginPrefs.get('spineColor', '88 88 88').replace(' ', '').replace('#', ''))

            # ============================= Background color ==============================
            if not self.pluginPrefs.get('backgroundColorOther', 'false'):
                p_dict['transparent_charts'] = False
                p_dict['backgroundColor']    = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            elif self.pluginPrefs.get('backgroundColorOther', 'false') == 'false':
                p_dict['transparent_charts'] = False
                p_dict['backgroundColor']    = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            else:
                p_dict['transparent_charts'] = True
                p_dict['backgroundColor'] = '#000000'

            # ============================== Plot Area color ==============================
            if not self.pluginPrefs.get('faceColorOther', 'false'):
                p_dict['transparent_filled'] = True
                p_dict['faceColor']          = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
            elif self.pluginPrefs.get('faceColorOther', 'false') == 'false':
                p_dict['transparent_filled'] = True
                p_dict['faceColor']          = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
            else:
                p_dict['transparent_filled'] = False
                p_dict['faceColor'] = '#000000'

            # A list of chart ids may be passed to the method. In that case, refresh only
            # those charts. Otherwise, chart_id is None and we evaluate all of the charts
            # to see if they need to be updated.
            if not dev_list:

                dev_list = []

                for dev in indigo.devices.itervalues('self'):
                    refresh_interval = int(dev.pluginProps['refreshInterval'])

                    if dev.deviceTypeId != 'csvEngine' and refresh_interval > 0 and dev.enabled:

                        diff = dt.datetime.now() - date_parse(dev.states['chartLastUpdated'])
                        refresh_needed = diff > dt.timedelta(seconds=refresh_interval)

                        if refresh_needed:
                            dev_list.append(dev)

            for dev in dev_list:

                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                # ============================= Custom Font Sizes =============================
                # Custom font sizes for retina/non-retina adjustments.
                try:
                    if dev.pluginProps['customSizeFont']:
                        p_dict['mainFontSize'] = int(dev.pluginProps['customTitleFontSize'])
                        plt.rcParams['xtick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                        plt.rcParams['ytick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                except KeyError:
                    # Not all devices may support this feature.
                    pass

                # ================================== kwargs ===================================
                # Note: PyCharm wants attribute values to be strings. This is not always what
                # Matplotlib wants (i.e., bbox alpha and linewidth should be floats.)
                k_dict['k_annotation_battery'] = {'bbox': dict(boxstyle='round,pad=0.3', facecolor=p_dict['faceColor'], edgecolor=p_dict['spineColor'], alpha=0.75, linewidth=0.5),
                                                  'color': p_dict['fontColorAnnotation'], 'size': plt.rcParams['xtick.labelsize'], 'horizontalalignment': 'center',
                                                  'textcoords': 'offset points', 'verticalalignment': 'center', 'zorder': 25}
                k_dict['k_annotation']   = {'bbox': dict(boxstyle='round,pad=0.3', facecolor=p_dict['faceColor'], edgecolor=p_dict['spineColor'], alpha=0.75, linewidth=0.5),
                                            'color': p_dict['fontColorAnnotation'], 'size': plt.rcParams['xtick.labelsize'], 'horizontalalignment': 'center',
                                            'textcoords': 'offset points', 'verticalalignment': 'center'}
                k_dict['k_bar']          = {'alpha': 1.0, 'zorder': 10}
                k_dict['k_base_font']    = {'size': float(p_dict['mainFontSize']), 'weight': p_dict['font_weight']}
                k_dict['k_calendar']     = {'verticalalignment': 'top'}
                k_dict['k_custom']       = {'alpha': 1.0, 'zorder': 3}
                k_dict['k_fill']         = {'alpha': 0.7, 'zorder': 10}
                k_dict['k_grid_fig']     = {'which': 'major', 'zorder': 1}
                k_dict['k_line']         = {'alpha': 1.0}
                k_dict['k_major_x']      = {'bottom': p_dict['tick_bottom'], 'reset': False, 'top': p_dict['tick_top'], 'which': 'major'}
                k_dict['k_major_y']      = {'left': p_dict['tick_left'], 'reset': False, 'right': p_dict['tick_right'], 'which': 'major'}
                k_dict['k_major_y2']     = {'left': p_dict['tick_left'], 'reset': False, 'right': p_dict['tick_right'], 'which': 'major'}
                k_dict['k_max']          = {'linestyle': 'dotted', 'marker': None, 'alpha': 1.0, 'zorder': 1}
                k_dict['k_min']          = {'linestyle': 'dotted', 'marker': None, 'alpha': 1.0, 'zorder': 1}
                k_dict['k_minor_x']      = {'bottom': p_dict['tick_bottom'], 'reset': False, 'top': p_dict['tick_top'], 'which': 'minor'}
                k_dict['k_minor_y']      = {'left': p_dict['tick_left'], 'reset': False, 'right': p_dict['tick_right'], 'which': 'minor'}
                k_dict['k_minor_y2']     = {'left': p_dict['tick_left'], 'reset': False, 'right': p_dict['tick_right'], 'which': 'minor'}
                k_dict['k_rgrids']       = {'angle': 67, 'color': p_dict['fontColor'], 'horizontalalignment': 'left', 'verticalalignment': 'center'}
                k_dict['k_title_font']   = {'color': p_dict['fontColor'], 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                            'weight': p_dict['font_weight'], 'visible': True}
                k_dict['k_x_axis_font']  = {'color': p_dict['fontColor'], 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                            'weight': p_dict['font_weight'], 'visible': True}
                k_dict['k_y_axis_font']  = {'color': p_dict['fontColor'], 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                            'weight': p_dict['font_weight'], 'visible': True}
                k_dict['k_y2_axis_font'] = {'color': p_dict['fontColor'], 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                            'weight': p_dict['font_weight'], 'visible': True}

                # If the user has selected transparent in the plugin menu, we account for that here when setting up the kwargs for savefig().
                if p_dict['transparent_charts']:
                    k_dict['k_plot_fig'] = {'bbox_extra_artists': None, 'bbox_inches': None, 'format': None, 'frameon': None, 'orientation': None, 'pad_inches': None, 'papertype': None,
                                            'transparent': p_dict['transparent_charts']}
                else:
                    k_dict['k_plot_fig'] = {'bbox_extra_artists': None, 'bbox_inches': None, 'edgecolor': p_dict['backgroundColor'], 'facecolor': p_dict['backgroundColor'],
                                            'format': None, 'frameon': None, 'orientation': None, 'pad_inches': None, 'papertype': None, 'transparent': p_dict['transparent_charts']}

                # ========================== matplotlib.rc overrides ==========================
                plt.rc('font', **k_dict['k_base_font'])

                p_dict.update(dev.pluginProps)

                for _ in ('bar_colors', 'customTicksLabelY', 'customTicksY', 'data_array', 'dates_to_plot', 'headers', 'wind_direction', 'wind_speed',
                          'x_obs1', 'x_obs2', 'x_obs3', 'x_obs4', 'x_obs5', 'x_obs6',
                          'y_obs1', 'y_obs1_max', 'y_obs1_min',
                          'y_obs2', 'y_obs2_max', 'y_obs2_min',
                          'y_obs3', 'y_obs3_max', 'y_obs3_min',
                          'y_obs4', 'y_obs4_max', 'y_obs4_min',
                          'y_obs5', 'y_obs5_max', 'y_obs5_min',
                          'y_obs6', 'y_obs6_max', 'y_obs6_min'):
                    p_dict[_] = []

                p_dict['fileName']  = ''
                p_dict['headers_1'] = ()  # Tuple
                p_dict['headers_2'] = ()  # Tuple

                try:
                    kv_list = list()  # A list of state/value pairs used to feed updateStatesOnServer()
                    kv_list.append({'key': 'onOffState', 'value': True, 'uiValue': 'Updated'})
                    p_dict.update(dev.pluginProps)

                    # ======================= Limit number of observations ========================
                    try:
                        p_dict['numObs'] = int(p_dict['numObs'])

                    except KeyError:
                        # Only some devices will have their own numObs.
                        pass

                    except ValueError as sub_error:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.warning(u"[{0}] The number of observations must be a positive number: {1}. See plugin log for more information.".format(dev.name, sub_error))

                    # ============================ Custom Square Size =============================
                    try:
                        if p_dict['customSizePolar'] == 'None':
                            pass

                        else:
                            p_dict['sqChartSize'] = float(p_dict['customSizePolar'])

                    except ValueError as sub_error:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.warning(u"[{0}] Custom size must be a positive number or None: {1}".format(dev.name, sub_error))

                    except KeyError:
                        pass

                    # ============================= Extra Wide Chart ==============================
                    try:
                        if p_dict.get('rectWide', False):
                            p_dict['chart_height'] = float(p_dict['rectChartWideHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWideWidth'])

                        else:
                            p_dict['chart_height'] = float(p_dict['rectChartHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWidth'])

                    except KeyError:
                        # Not all devices will have these keys
                        pass

                    # ================================ Custom Size ================================
                    # If the user has specified a custom size, let's override
                    # with their custom setting.
                    if p_dict.get('customSizeChart', False):
                        try:
                            if p_dict['customSizeHeight'] != 'None':
                                p_dict['chart_height'] = float(p_dict['customSizeHeight'])

                            if p_dict['customSizeWidth'] != 'None':
                                p_dict['chart_width'] = float(p_dict['customSizeWidth'])

                        except KeyError:
                            # Not all devices will have these keys
                            pass

                    # ============================== Best Fit Lines ===============================
                    # Set the defaults for best fit lines in p_dict.
                    for _ in range(1, 7, 1):
                        p_dict['line{0}BestFitColor'.format(_)] = dev.pluginProps.get('line{0}BestFitColor'.format(_), 'FF 00 00')

                    # ============================== Phantom Labels ===============================
                    # Since users may or may not include axis labels and
                    # because we want to ensure that all plot areas present
                    # in the same way, we need to create 'phantom' labels that
                    # are plotted but not visible.  Setting the font color to
                    # 'None' will effectively hide them.
                    try:
                        if p_dict['customAxisLabelX'].isspace() or p_dict['customAxisLabelX'] == '':
                            p_dict['customAxisLabelX'] = 'null'
                            k_dict['k_x_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                                          'weight': p_dict['font_weight'], 'visible': True}
                    except KeyError:
                        # Not all devices will contain these keys
                        pass

                    try:
                        if p_dict['customAxisLabelY'].isspace() or p_dict['customAxisLabelY'] == '':
                            p_dict['customAxisLabelY'] = 'null'
                            k_dict['k_y_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                                          'weight': p_dict['font_weight'], 'visible': True}
                    except KeyError:
                        # Not all devices will contain these keys
                        pass

                    try:
                        if 'customAxisLabelY2' in p_dict.keys():  # Not all devices that get to this point will support Y2.
                            if p_dict['customAxisLabelY2'].isspace() or p_dict['customAxisLabelY2'] == '':
                                p_dict['customAxisLabelY2'] = 'null'
                                k_dict['k_y2_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']),
                                                               'fontstyle': p_dict['font_style'], 'weight': p_dict['font_weight'], 'visible': True}
                    except KeyError:
                        # Not all devices will contain these keys
                        pass

                    # ================================ Annotations ================================
                    # If the user wants annotations, we need to hide the line
                    # markers as we don't want to plot one on top of the other.
                    for line in range(1, 7, 1):
                        try:
                            if p_dict['line{0}Annotate'.format(line)] and p_dict['line{0}Marker'.format(line)] != 'None':
                                p_dict['line{0}Marker'.format(line)] = 'None'
                                self.logger.warning(u"[{0}] Line {1} marker is suppressed to display annotations. "
                                                    u"To see the marker, disable annotations for this line.".format(dev.name, line))
                        except KeyError:
                            # Not all devices will contain these keys
                            pass

                    # =============================== Line Markers ================================
                    # Some line markers need to be adjusted due to their inherent value. For
                    # example, matplotlib uses '<', '>' and '.' as markers but storing these values
                    # will blow up the XML.  So we need to convert them. (See self.formatMarkers()
                    # method.)
                    p_dict = self.formatMarkers(p_dict)

                    # Note that the logging of p_dict and k_dict are handled within the thread.
                    self.logger.threaddebug(u"{0:*^80}".format(u" Generating Chart: {0} ".format(dev.name)))
                    self.__log_dicts(dev)

                    # ============================== rcParams Device ==============================
                    if dev.deviceTypeId == 'rcParamsDevice':
                        self.rcParamsDeviceUpdate(dev)

                    # For the time being, we're running each device through its
                    # own process synchronously; parallel processing may come later.

                    # ================================ Bar Charts =================================
                    if dev.deviceTypeId == 'barChartingDevice':

                        if __name__ == '__main__':
                            p_bar = multiprocessing.Process(name='p_bar', target=MakeChart(self).chart_bar, args=(dev, p_dict, k_dict, return_queue,))
                            p_bar.start()

                    # =========================== Battery Health Chart ============================
                    if dev.deviceTypeId == 'batteryHealthDevice':

                        device_dict  = {}
                        exclude_list = [int(_) for _ in dev.pluginProps.get('excludedDevices', [])]

                        for batt_dev in indigo.devices.itervalues():
                            try:
                                if batt_dev.batteryLevel is not None and batt_dev.id not in exclude_list:
                                    device_dict[batt_dev.name] = batt_dev.states['batteryLevel']

                                # The following line is used for testing the battery health code; it isn't needed in production.
                                # device_dict = {'Device 1': '50', 'Device 2': '77', 'Device 3': '9', 'Device 4': '4', 'Device 5': '92', 'Device 6': '72', 'Device 7': '47', 'Device 8': '92', 'Device 9': '72', 'Device 10': '47'}

                            except Exception as sub_error:
                                self.pluginErrorHandler(traceback.format_exc())
                                self.logger.error(u"[{0}] Error reading battery devices: {1}".format(batt_dev.name, sub_error))

                        if device_dict == {}:
                            device_dict['No Battery Devices'] = 0

                        if __name__ == '__main__':
                            p_battery = multiprocessing.Process(name='p_battery', target=MakeChart(self).chart_battery_health, args=(dev, device_dict, p_dict, k_dict, return_queue,))
                            p_battery.start()

                    # ============================== Calendar Charts ==============================
                    if dev.deviceTypeId == "calendarChartingDevice":

                        if __name__ == '__main__':
                            p_calendar = multiprocessing.Process(name='p_calendar', target=MakeChart(self).chart_calendar, args=(dev, p_dict, k_dict, return_queue,))
                            p_calendar.start()

                    # ================================ Line Charts ================================
                    if dev.deviceTypeId == "lineChartingDevice":

                        if __name__ == '__main__':
                            p_line = multiprocessing.Process(name='p_line', target=MakeChart(self).chart_line, args=(dev, p_dict, k_dict, return_queue,))
                            p_line.start()

                    # ============================== Multiline Text ===============================
                    if dev.deviceTypeId == 'multiLineText':

                        # Get the text to plot. We do this here so we don't need to send all the
                        # devices and variables to the method (the process does not have access to the
                        # Indigo server).
                        if int(p_dict['thing']) in indigo.devices:
                            text_to_plot = unicode(indigo.devices[int(p_dict['thing'])].states[p_dict['thingState']])

                        elif int(p_dict['thing']) in indigo.variables:
                            text_to_plot = unicode(indigo.variables[int(p_dict['thing'])].value)

                        else:
                            text_to_plot = u"Unable to reconcile plot text. Confirm device settings."
                            self.logger.info(u"Presently, the plugin only supports device state and variable values.")

                        if __name__ == '__main__':
                            p_multiline = multiprocessing.Process(name='p_multiline',
                                                                  target=MakeChart(self).chart_multiline_text,
                                                                  args=(dev, p_dict, k_dict, text_to_plot, return_queue,))
                            p_multiline.start()

                    # =============================== Polar Charts ================================
                    if dev.deviceTypeId == "polarChartingDevice":

                        if __name__ == '__main__':
                            p_polar = multiprocessing.Process(name='p_polar', target=MakeChart(self).chart_polar, args=(dev, p_dict, k_dict, return_queue,))
                            p_polar.start()

                    # ============================== Scatter Charts ===============================
                    if dev.deviceTypeId == "scatterChartingDevice":

                        if __name__ == '__main__':
                            p_scatter = multiprocessing.Process(name='p_scatter', target=MakeChart(self).chart_scatter, args=(dev, p_dict, k_dict, return_queue,))
                            p_scatter.start()

                    # ========================== Weather Forecast Charts ==========================
                    if dev.deviceTypeId == "forecastChartingDevice":

                        dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                        state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states
                        sun_rise_set = [str(indigo.server.calculateSunrise()), str(indigo.server.calculateSunset())]

                        if __name__ == '__main__':
                            p_weather = multiprocessing.Process(name='p_weather',
                                                                target=MakeChart(self).chart_weather_forecast,
                                                                args=(dev, dev_type, p_dict, k_dict, state_list, sun_rise_set, return_queue,))
                            p_weather.start()

                    # ========================= Process the output queue ==========================
                    self.processLogQueue(dev, return_queue)

                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    # If we have manually asked for all charts to update, don't refresh the last
                    # update time so that the charts will update on their own at the next refresh
                    # cycle.
                    if not self.skipRefreshDateUpdate:
                        kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

                    dev.updateStatesOnServer(kv_list)

                except RuntimeError as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.critical(u"[{0}] Critical Error: {1}. See plugin log for more information.".format(dev.name, sub_error))
                    self.logger.critical(u"Skipping device.")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

            # Ensure the flag is in the proper state for the next automatic refresh.
            self.skipRefreshDateUpdate = False

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"[{0}] Error: {0}. See plugin log for more information.".format(unicode(sub_error)))

    # =============================================================================
    def refreshTheChartsAction(self, plugin_action):
        """
        Called by an Indigo Action item.

        Allows the plugin to call the refreshTheCharts() method from an Indigo Action
        item. This action will refresh all charts.

        -----

        :param class 'indigo.PluginAction' plugin_action:
        """
        self.skipRefreshDateUpdate = True
        devices_to_refresh = [dev for dev in indigo.devices.itervalues('self') if dev.enabled and dev.deviceTypeId != 'csvEngine']

        self.refreshTheCharts(devices_to_refresh)

        self.logger.info(u"{0:{1}^80}".format(' Refresh Action Complete ', '='))


class MakeChart(object):

    def __init__(self, plugin):
        self.final_data = []
        self.host_plugin = plugin

    # =============================================================================
    def chart_bar(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the bar charts

        All steps required to generate bar charts.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            num_obs                   = p_dict['numObs']
            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            for _ in range(1, 5, 1):
                p_dict['bar{0}Color'.format(_)] = r"#{0}".format(p_dict['bar{0}Color'.format(_)].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ================================ Format Axes ================================
            self.format_axis_x_ticks(ax, p_dict, k_dict, log)
            self.format_axis_y(ax, p_dict, k_dict, log)

            for thing in range(1, 5, 1):

                # If the bar color is the same as the background color, alert the user.
                if p_dict['bar{0}Color'.format(thing)] == p_dict['backgroundColor']:
                    log['Info'].append(u"[{0}] Bar {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, thing))

                # If the bar is suppressed, remind the user they suppressed it.
                if p_dict['suppressBar{0}'.format(thing)]:
                    log['Info'].append(u"[{0}] Bar {1} is suppressed by user setting. You can re-enable it in the device configuration menu.".format(dev.name, thing))

                # Plot the bars.  If 'suppressBar{thing} is True, we skip it.
                if p_dict['bar{0}Source'.format(thing)] not in ("", "None") and not p_dict['suppressBar{0}'.format(thing)]:

                    # Get the data and grab the header.
                    data_column, log = self.get_data(u'{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"), p_dict['bar{0}Source'.format(thing)]), log)
                    log['Threaddebug'].append(u"Data for bar {0}: {1}".format(thing, data_column))

                    # Pull the headers
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(thing)].append(element[0])
                        p_dict['y_obs{0}'.format(thing)].append(float(element[1]))

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(thing)], log)

                    # If the user sets the width to 0, this will perform an introspection of the
                    # dates to plot and get the minimum of the difference between the dates.
                    if float(p_dict['barWidth']) == 0.0:
                        width = np.min(np.diff(dates_to_plot)) * 0.8
                    else:
                        width = float(p_dict['barWidth'])

                    # Plot the bar.
                    # Note: hatching is not supported in the PNG backend.
                    ax.bar(dates_to_plot[num_obs * -1:], p_dict['y_obs{0}'.format(thing)][num_obs * -1:], align='center', width=width,
                           color=p_dict['bar{0}Color'.format(thing)], edgecolor=p_dict['bar{0}Color'.format(thing)], **k_dict['k_bar'])

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)][num_obs * -1:]]

                    # If annotations desired, plot those too.
                    if p_dict['bar{0}Annotate'.format(thing)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(thing)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # ============================== Y1 Axis Min/Max ==============================
            log = self.format_axis_y1_min_max(p_dict, log)

            # =============================== X Axis Label ================================
            self.format_axis_x_label(dev, p_dict, k_dict, log)

            # =============================== Y Axis Label ================================
            # self.format_axis_y1_label(p_dict, k_dict, log)

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ============================= Legend Properties =============================
            # Legend should be plotted before any other lines are plotted (like averages or
            # custom line segments).

            if p_dict['showLegend']:

                # Amend the headers if there are any custom legend entries defined.
                counter = 1
                final_headers = []
                headers = [_.decode('utf-8') for _ in p_dict['headers']]
                for header in headers:
                    if p_dict['bar{0}Legend'.format(counter)] == "":
                        final_headers.append(header)
                    else:
                        final_headers.append(p_dict['bar{0}Legend'.format(counter)])
                    counter += 1

                legend = ax.legend(final_headers, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # =============================== Min/Max Lines ===============================
            # Note that these need to be plotted after the legend is
            # established, otherwise some of the characteristics of the min/max
            # lines will take over the legend props.
            for thing in range(1, 5, 1):
                if p_dict['plotBar{0}Min'.format(thing)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(thing)][num_obs * -1:]), color=p_dict['bar{0}Color'.format(thing)], **k_dict['k_min'])
                if p_dict['plotBar{0}Max'.format(thing)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(thing)][num_obs * -1:]), color=p_dict['bar{0}Color'.format(thing)], **k_dict['k_max'])
                if self.host_plugin.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            # =========================== Custom Line Segments ============================
            self.plot_custom_line_segments(ax, p_dict, k_dict)

            # =============================== Format Grids ================================
            self.format_grids(p_dict, k_dict, log)

            # ================================ Chart Title ================================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ============================== Custom Y Ticks ===============================
            self.format_axis_y_ticks(p_dict, k_dict, log)

            # ================================ Save Image =================================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)

            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors. See plugin log for more information.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_battery_health(self, dev, device_dict, p_dict, k_dict, return_queue):
        """
        Creates the battery health charts

        The chart_battery_health method creates battery health charts. These chart
        types are dynamic and are created "on the fly" rather than through direct
        user input.

        :param class 'indigo.Device' dev: indigo device instance
        :param dict device_dict: dictionary of battery device names and battery levels
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue:
        :return:
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            bar_colors    = []
            caution_color = r"#{0}".format(p_dict['cautionColor'].replace(' ', '').replace('#', ''))
            caution_level = int(p_dict['cautionLevel'])
            font_color    = p_dict['fontColor']
            font_size     = plt.rcParams['ytick.labelsize']
            healthy_color = r"#{0}".format(p_dict['healthyColor'].replace(' ', '').replace('#', ''))
            level_box     = p_dict['showBatteryLevelBackground']
            show_level    = p_dict['showBatteryLevel']
            warning_color = r"#{0}".format(p_dict['warningColor'].replace(' ', '').replace('#', ''))
            warning_level = int(p_dict['warningLevel'])
            x_values      = []
            y_text        = []

            for key, value in sorted(device_dict.iteritems(), reverse=True):
                try:
                    x_values.append(float(value))

                except ValueError:
                    x_values.append(0)

                y_text.append(key)

                # =========================== Calculate Bar Colors ============================
                # Create a list of colors for the bars based on battery health
                try:
                    battery_level = float(value)

                except ValueError:
                    battery_level = 0

                if battery_level <= warning_level:
                    bar_colors.append(warning_color)

                elif warning_level < battery_level <= caution_level:
                    bar_colors.append(caution_color)

                else:
                    bar_colors.append(healthy_color)

            # Create a range of values to plot on the Y axis, since we can't plot on device names.
            y_values = np.arange(len(y_text))

            # ============================== Plot the Figure ==============================
            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # Adding 1 to the y_axis pushes the bar to spot 1 instead of spot 0 -- getting it off the axis.
            ax.barh((y_values + 1), x_values, color=bar_colors, align='center', linewidth=0, **k_dict['k_bar'])

            # ================================ Data Labels ================================
            # Plot data labels inside or outside depending on bar length

            # With annotation background
            if show_level and level_box:
                for _ in range(len(y_values)):
                    if x_values[_] >= caution_level:
                        plt.annotate(u"{0}".format(int(x_values[_])), xy=((x_values[_] - 6), (y_values[_]) + 0.88), xytext=(11, 2), **k_dict['k_annotation_battery'])
                    else:
                        plt.annotate(u"{0}".format(int(x_values[_])), xy=((x_values[_] + 1), (y_values[_]) + 0.88), xytext=(3, 2), **k_dict['k_annotation_battery'])

            # Without annotation background
            elif show_level:
                for _ in range(len(y_values)):
                    if x_values[_] >= caution_level:
                        plt.annotate(u"{0:>3}".format(int(x_values[_])), xy=((x_values[_] - 6), (y_values[_]) + 0.88),
                                     xycoords='data', textcoords='data', fontsize=font_size, color=font_color, zorder=25)
                    else:
                        plt.annotate(u"{0}".format(int(x_values[_])), xy=((x_values[_] + 1), (y_values[_]) + 0.88),
                                     xycoords='data', textcoords='data', fontsize=font_size, color=font_color, zorder=25)

            # ================================ Chart Title ================================
            plt.suptitle(p_dict['chartTitle'], **k_dict['k_title_font'])

            # =============================== Format Grids ================================
            if dev.ownerProps.get('showxAxisGrid', False):
                for _ in (20, 40, 60, 80):
                    ax.axvline(x=_, color=p_dict['gridColor'], linestyle=self.host_plugin.pluginPrefs.get('gridStyle', ':'))

            # =============================== X Axis Label ================================
            self.format_axis_x_label(dev, p_dict, k_dict, log)
            ax.xaxis.set_ticks_position('bottom')

            # ============================== X Axis Min/Max ===============================
            # We want the X axis scale to always be 0-100.
            plt.xlim(xmin=0, xmax=100)

            # =============================== Y Axis Label ================================
            # Hide major tick labels and right side ticks.
            ax.set_yticklabels('')
            ax.yaxis.set_ticks_position('left')

            # Customize minor tick label position and assign device names to the
            # minor ticks
            ax.set_yticks([n for n in range(1, len(y_values) + 1)], minor=True)
            ax.set_yticklabels(y_text, minor=True)

            # ============================== Y Axis Min/Max ===============================
            # We never want the Y axis to go lower than 0.
            plt.ylim(ymin=0)

            # ================================== Spines ===================================
            # Hide all but the bottom spine.
            for spine in ('left', 'top', 'right'):
                ax.spines[spine].set_visible(False)

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ================================ Save Image =================================
            # Output the file
            plt.tight_layout()
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_calendar(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the calendar charts

        Given the unique nature of calendar charts, we use a separate method to
        construct them.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue: return queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            import calendar
            calendar.setfirstweekday(int(dev.pluginProps['firstDayOfWeek']))
            today = dt.datetime.today()
            cal   = calendar.month(today.year, today.month)
            size  = float(self.host_plugin.pluginPrefs.get('sqChartSize', 250))

            ax = self.make_chart_figure(size, size, p_dict)

            ax.text(0, 1, cal, transform=ax.transAxes, color=p_dict['fontColor'], fontname='Andale Mono', fontsize=dev.pluginProps['fontSize'], backgroundcolor=p_dict['faceColor'],
                    bbox=dict(pad=3), **k_dict['k_calendar'])
            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            ax.axis('off')

            # ================================ Save Image =================================
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.9, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_line(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the line charts

        All steps required to generate line charts.

        -----

        :param class 'indigo.Device'e dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            for _ in range(1, 7, 1):
                p_dict['line{0}Color'.format(_)]        = r"#{0}".format(p_dict['line{0}Color'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}MarkerColor'.format(_)]  = r"#{0}".format(p_dict['line{0}MarkerColor'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}BestFitColor'.format(_)] = r"#{0}".format(p_dict['line{0}BestFitColor'.format(_)].replace(' ', '').replace('#', ''))

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ================================ Format Axes ================================
            self.format_axis_x_ticks(ax, p_dict, k_dict, log)
            self.format_axis_y(ax, p_dict, k_dict, log)

            for line in range(1, 7, 1):

                # If line color is the same as the background color, alert the user.
                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Warning'].append(u"[{0}] Line {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, line))

                # If the line is suppressed, remind the user they suppressed it.
                if p_dict['suppressLine{0}'.format(line)]:
                    log['Info'].append(u"[{0}] Line {1} is suppressed by user setting. You can re-enable it in the device configuration menu.".format(dev.name, line))

                # ============================== Plot the Lines ===============================
                # Plot the lines. If p_dict['suppressLine{0}'] is True, we skip it.
                if p_dict['line{0}Source'.format(line)] not in ("", "None") and not p_dict['suppressLine{0}'.format(line)]:

                    data_column, log = self.get_data('{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"), p_dict['line{0}Source'.format(line)].encode("utf-8")), log)
                    log['Threaddebug'].append(u"Data for Line {0}: {1}".format(line, data_column))

                    # Pull the headers
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(line)].append(element[0])
                        p_dict['y_obs{0}'.format(line)].append(float(element[1]))

                    # ============================= Adjustment Factor =============================
                    if dev.pluginProps['line{0}adjuster'.format(line)] != "":
                        temp_list = []
                        for obs in p_dict['y_obs{0}'.format(line)]:
                            expr = u'{0}{1}'.format(obs, dev.pluginProps['line{0}adjuster'.format(line)])
                            temp_list.append(self.host_plugin.evalExpr.eval_expr(expr))
                        p_dict['y_obs{0}'.format(line)] = temp_list

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(line)], log)

                    ax.plot_date(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                                 marker=p_dict['line{0}Marker'.format(line)], markeredgecolor=p_dict['line{0}MarkerColor'.format(line)],
                                 markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=10, **k_dict['k_line'])

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Fill'.format(line)]:
                        ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                    # ================================ Annotations ================================
                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # ============================== Y1 Axis Min/Max ==============================
            # Min and Max are not 'None'.
            log = self.format_axis_y1_min_max(p_dict, log)

            # Transparent Chart Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

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
                legend = ax.legend(final_headers, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=5, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            for line in range(1, 7, 1):
                # Note that we do these after the legend is drawn so that these lines
                # don't affect the legend.

                # We need to reload the dates to ensure that they match the line being plotted
                dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(line)], log)

                # =============================== Best Fit Line ===============================
                if dev.pluginProps.get('line{0}BestFit'.format(line), False):
                    self.plot_best_fit_line_segments(ax, dates_to_plot, line, p_dict)

                [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                # =============================== Fill Between ================================
                if p_dict['line{0}Fill'.format(line)]:
                    ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                # =============================== Min/Max Lines ===============================
                if p_dict['plotLine{0}Min'.format(line)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_min'])
                if p_dict['plotLine{0}Max'.format(line)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_max'])
                if self.host_plugin.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plot_custom_line_segments(ax, p_dict, k_dict)

            self.format_grids(p_dict, k_dict, log)

            # ================================ Chart Title ================================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # =============================== X Axis Label ================================
            self.format_axis_x_label(dev, p_dict, k_dict, log)

            # =============================== Y Axis Label ================================
            self.format_axis_y1_label(p_dict, k_dict, log)

            # ============================== Custom Y Ticks ===============================
            self.format_axis_y_ticks(p_dict, k_dict, log)

            # ================================ Save Image =================================
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_multiline_text(self, dev, p_dict, k_dict, text_to_plot, return_queue):
        """
        Creates the multiline text charts

        Given the unique nature of multiline text charts, we use a separate method
        to construct them.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param unicode text_to_plot: the text to be plotted
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            import textwrap

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))
            p_dict['textColor']       = r"#{0}".format(p_dict['textColor'].replace(' ', '').replace('#', ''))
            p_dict['figureWidth']     = float(dev.pluginProps['figureWidth'])
            p_dict['figureHeight']    = float(dev.pluginProps['figureHeight'])

            # If the value to be plotted is empty, use the default text from the device
            # configuration.
            if len(text_to_plot) <= 1:
                text_to_plot = unicode(p_dict['defaultText'])

            else:
                # The clean_string method tries to remove some potential ugliness from the text
                # to be plotted. It's optional--defaulted to on. No need to call this if the
                # default text is used.
                if p_dict['cleanTheText']:
                    text_to_plot = self.clean_string(text_to_plot)

            log['Threaddebug'].append(u"Data: {0}".format(text_to_plot))

            # Wrap the text and prepare it for plotting.
            text_to_plot = textwrap.fill(text_to_plot, int(p_dict['numberOfCharacters']), replace_whitespace=p_dict['cleanTheText'])

            ax = self.make_chart_figure(p_dict['figureWidth'], p_dict['figureHeight'], p_dict)

            ax.text(0.01, 0.95, text_to_plot, transform=ax.transAxes, color=p_dict['textColor'], fontname=p_dict['fontMain'], fontsize=p_dict['multilineFontSize'],
                    verticalalignment='top')

            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)

            if not p_dict['textAreaBorder']:
                [s.set_visible(False) for s in ax.spines.values()]

            # Transparent Charts Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ================================ Chart Title ================================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ================================ Save Image =================================
            plt.subplots_adjust(top=0.9, bottom=0.05, left=0.02, right=0.98, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_polar(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the polar charts

        Note that the polar chart device can be used for other things, but it is coded
        like a wind rose which makes it easier to understand what's happening. Note
        that it would be possible to convert wind direction names (north-northeast) to
        an ordinal degree value, however, it would be very difficult to contend with
        all of the possible international Unicode values that could be passed to the
        device. Better to make it the responsibility of the user to convert their data
        to degrees.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            num_obs                    = p_dict['numObs']
            p_dict['backgroundColor']  = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']        = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))
            p_dict['currentWindColor'] = r"#{0}".format(p_dict['currentWindColor'].replace(' ', '').replace('#', ''))
            p_dict['maxWindColor']     = r"#{0}".format(p_dict['maxWindColor'].replace(' ', '').replace('#', ''))

            # ============================== Column Headings ==============================
            # Pull the column headings for the labels, then delete the row from
            # self.final_data.
            theta_path = '{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'], p_dict['thetaValue'].encode('utf-8'))  # The name of the theta file.
            radii_path = '{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'], p_dict['radiiValue'].encode('utf-8'))  # The name of the radii file.

            if theta_path != 'None' and radii_path != 'None':

                # Get the data.
                theta, log = self.get_data(theta_path, log)
                self.final_data.append(theta)
                radii, log = self.get_data(radii_path, log)
                self.final_data.append(radii)

                log['Threaddebug'].append(u"Data: {0}".format(self.final_data))

                # Pull out the header information out of the data.
                del self.final_data[0][0]
                del self.final_data[1][0]

                # Create lists of data to plot (string -> float).
                [p_dict['wind_direction'].append(float(item[1])) for item in self.final_data[0]]
                [p_dict['wind_speed'].append(float(item[1])) for item in self.final_data[1]]

                # Get the length of the lists
                len_wind_dir = len(p_dict['wind_direction'])
                len_wind_spd = len(p_dict['wind_speed'])

                # If the number of observations we have is greater than the number we want, we
                # need to slice the lists to use the last n observations.
                if len_wind_dir > num_obs:
                    p_dict['wind_direction'] = p_dict['wind_direction'][num_obs * -1:]

                if len_wind_spd > num_obs:
                    p_dict['wind_speed'] = p_dict['wind_speed'][num_obs * -1:]

                # If at this point we still don't have an equal number of observations for both
                # theta and radii, we shouldn't plot the chart.
                if len(p_dict['wind_direction']) != len(p_dict['wind_speed']):
                    log['Warning'].append(u"[{0}] Insufficient number of observations to plot.".format(dev.name))
                    return_queue.put({'Error': False, 'Log': log, 'Message': 'Skipped.', 'Name': dev.name})
                    return

                # Create the array of grey scale for the intermediate lines and set the last
                # one red. (MPL will accept string values '0' - '1' as grey scale, so we create
                # a number of greys based on 1.0 / number of observations.)
                color_increment = 1.0 / num_obs
                color = color_increment
                for item in range(0, num_obs, 1):
                    p_dict['bar_colors'].append("%0.3f" % color)
                    color += color_increment
                p_dict['bar_colors'][num_obs - 1] = p_dict['currentWindColor']

                # Change the default bar color for the max to user preference.
                max_wind_speed = max(p_dict['wind_speed'])
                p_dict['bar_colors'][p_dict['wind_speed'].index(max_wind_speed)] = p_dict['maxWindColor']

                # Polar plots are in radians (not degrees.)
                p_dict['wind_direction'] = np.radians(p_dict['wind_direction'])
                wind = zip(p_dict['wind_direction'], p_dict['wind_speed'], p_dict['bar_colors'])

                # ============================== Customizations ===============================
                size = float(p_dict['sqChartSize']) / int(plt.rcParams['savefig.dpi'])
                plt.figure(figsize=(size, size))
                ax = plt.subplot(111, polar=True)                                 # Create subplot
                plt.grid(color=plt.rcParams['grid.color'])                        # Color the grid
                ax.set_theta_zero_location('N')                                   # Set zero to North
                ax.set_theta_direction(-1)                                        # Reverse the rotation
                ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])  # Customize the xtick labels
                ax.spines['polar'].set_visible(False)                             # Show or hide the plot spine
                ax.set_axis_bgcolor(p_dict['faceColor'])                          # Color the background of the plot area.

                # ============================== Create the Plot ==============================
                # Note: zorder of the plot must be >2.01 for the plot to be above the grid (the
                # grid defaults to z = 2.)
                for w in wind:
                    ax.plot((0, w[0]), (0, w[1]), color=w[2], linewidth=2, zorder=3)

                # Right-size the grid (must be done after the plot), and customize the tick
                # labels. The default covers anything over 50.
                ticks = np.arange(20, 100, 20)
                grids = range(20, 120, 20)

                if max_wind_speed <= 5:
                    ticks = np.arange(1, 5, 1)
                    grids = range(1, 6, 1)

                elif 5 < max_wind_speed <= 10:
                    ticks = np.arange(2, 10, 2)
                    grids = range(2, 12, 2)

                elif 10 < max_wind_speed <= 20:
                    ticks = np.arange(5, 20, 5)
                    grids = range(5, 30, 5)

                elif 20 < max_wind_speed <= 30:
                    ticks = np.arange(6, 30, 6)
                    grids = range(6, 36, 6)

                elif 30 < max_wind_speed <= 40:
                    ticks = np.arange(8, 40, 8)
                    grids = range(8, 48, 8)

                elif 40 < max_wind_speed <= 50:
                    ticks = np.arange(10, 50, 10)
                    grids = range(10, 60, 10)

                elif 50 < max_wind_speed:
                    plt.text(0.5, 0.5, u"Holy crap!", color='FF FF FF', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes,
                             bbox=dict(facecolor='red', alpha='0.5'))

                ax.yaxis.set_ticks(ticks)
                ax.set_rgrids(grids, **k_dict['k_rgrids'])

                # If the user wants to hide tick labels, lets do that.
                if p_dict['xHideLabels']:
                    ax.axes.xaxis.set_ticklabels([])
                if p_dict['yHideLabels']:
                    ax.axes.yaxis.set_ticklabels([])

                # ========================== Current Obs / Max Wind ===========================
                # Note that we reduce the value of the circle plot so that it appears when
                # transparent charts are enabled (otherwise the circle is obscured. The
                # transform can be done one of two ways: access the private attribute
                # "ax.transData._b", or "ax.transProjectionAffine + ax.transAxes".
                fig = plt.gcf()
                max_wind_circle = plt.Circle((0, 0), (max(p_dict['wind_speed']) * 0.99), transform=ax.transProjectionAffine + ax.transAxes, fill=False, edgecolor=p_dict['maxWindColor'],
                                             linewidth=2, alpha=1, zorder=9)
                fig.gca().add_artist(max_wind_circle)

                last_wind_circle = plt.Circle((0, 0), (p_dict['wind_speed'][-1] * 0.99), transform=ax.transProjectionAffine + ax.transAxes, fill=False,
                                              edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=10)
                fig.gca().add_artist(last_wind_circle)

                # ================================== No Wind ==================================
                # If latest obs is a speed of zero, plot something that we can see.
                if p_dict['wind_speed'][-1] == 0:
                    zero_wind_circle = plt.Circle((0, 0), 0.15, transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['currentWindColor'],
                                                  edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=12)
                    fig.gca().add_artist(zero_wind_circle)

                # ========================== Transparent Chart Fill ===========================
                if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                    ylim = ax.get_ylim()
                    patch = plt.Circle((0, 0), ylim[1], transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['faceColor'], linewidth=1, alpha=1, zorder=1)
                    fig.gca().add_artist(patch)

                # ============================= Legend Properties =============================
                # Legend should be plotted before any other lines are plotted (like averages or
                # custom line segments).

                if p_dict['showLegend']:
                    legend = ax.legend(([u"Current", u"Maximum"]), loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                    legend.legendHandles[0].set_color(p_dict['currentWindColor'])
                    legend.legendHandles[1].set_color(p_dict['maxWindColor'])
                    [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                    frame = legend.get_frame()
                    frame.set_alpha(0)

                # =============================== Display Grids ===============================
                # Grids are always on for polar wind charts.

                # ================================ Chart Title ================================
                plt.title(p_dict['chartTitle'], position=(0, 1.0), **k_dict['k_title_font'])

                # ================================ Save Image =================================
                # plt.tight_layout(pad=1)
                plt.subplots_adjust(top=0.95, bottom=0.15, left=0.15, right=0.85, hspace=None, wspace=None)
                self.save_chart_image(plt, p_dict, k_dict)

                # Prepare log for output.
                if log['Warning'] or log['Critical']:
                    return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
                else:
                    return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_scatter(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the scatter charts

        All steps required to generate scatter charts.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            # ============================= p_dict Overrides ==============================
            for _ in range(1, 5, 1):
                p_dict['group{0}Color'.format(_)]       = r"#{0}".format(p_dict['group{0}Color'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['group{0}MarkerColor'.format(_)] = r"#{0}".format(p_dict['group{0}MarkerColor'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}BestFitColor'.format(_)] = r"#{0}".format(p_dict['line{0}BestFitColor'.format(_)].replace(' ', '').replace('#', 'FF 00 00'))

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ================================ Format Axes ================================
            self.format_axis_x_ticks(ax, p_dict, k_dict, log)
            self.format_axis_y(ax, p_dict, k_dict, log)

            for thing in range(1, 5, 1):

                # If dot color is the same as the background color, alert the user.
                if p_dict['group{0}Color'.format(thing)] == p_dict['backgroundColor']:
                    log['Debug'].append(u"[{0}] Group {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, thing))

                # If the group is suppressed, remind the user they suppressed it.
                if p_dict['suppressGroup{0}'.format(thing)]:
                    log['Info'].append(u"[{0}] Group {1} is suppressed by user setting. You can re-enable it in the device configuration menu.".format(dev.name, thing))

                # ============================== Plot the Points ==============================
                # Plot the groups. If p_dict['suppressGroup{0}'] is True, we skip it.
                if p_dict['group{0}Source'.format(thing)] not in ("", "None") and not p_dict['suppressGroup{0}'.format(thing)]:

                    # There is a bug in matplotlib (fixed in newer versions) where points would not
                    # plot if marker set to 'none'. This overrides the behavior.
                    if p_dict['group{0}Marker'.format(thing)] == u'None':
                        p_dict['group{0}Marker'.format(thing)] = '.'
                        p_dict['group{0}MarkerColor'.format(thing)] = p_dict['group{0}Color'.format(thing)]

                    data_column, log = self.get_data('{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"),
                                                                     p_dict['group{0}Source'.format(thing)].encode("utf-8")), log)
                    log['Threaddebug'].append(u"Data for group {0}: {1}".format(thing, data_column))

                    # Pull the headers
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(thing)].append(element[0])
                        p_dict['y_obs{0}'.format(thing)].append(float(element[1]))

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(thing)], log)

                    # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
                    ax.scatter(dates_to_plot, p_dict['y_obs{0}'.format(thing)], c=p_dict['group{0}Color'.format(thing)], marker=p_dict['group{0}Marker'.format(thing)],
                               edgecolor=p_dict['group{0}MarkerColor'.format(thing)], linewidths=0.75, zorder=10, **k_dict['k_line'])

                    # =============================== Best Fit Line ===============================
                    if dev.pluginProps.get('line{0}BestFit'.format(thing), False):
                        self.plot_best_fit_line_segments(ax, dates_to_plot, thing, p_dict)

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)]]

            # ============================== Y1 Axis Min/Max ==============================
            # Min and Max are not 'None'.
            log = self.format_axis_y1_min_max(p_dict, log)

            # ================================== Legend ===================================
            if p_dict['showLegend']:

                # Amend the headers if there are any custom legend entries defined.
                counter = 1
                legend_styles = []
                final_headers = []

                headers = [_.decode('utf-8') for _ in p_dict['headers']]
                for header in headers:

                    if p_dict['group{0}Legend'.format(counter)] == "":
                        final_headers.append(header)
                    else:
                        final_headers.append(p_dict['group{0}Legend'.format(counter)])

                    legend_styles.append(tuple(plt.plot([], color=p_dict['group{0}MarkerColor'.format(counter)], linestyle='', marker=p_dict['group{0}Marker'.format(counter)],
                                         markerfacecolor=p_dict['group{0}Color'.format(counter)], markeredgewidth=.8, markeredgecolor=p_dict['group{0}MarkerColor'.format(counter)])))
                    counter += 1

                legend = ax.legend(legend_styles, final_headers, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, numpoints=1, markerscale=0.6,
                                   prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # ================================= Min / Max =================================
            for thing in range(1, 5, 1):
                if p_dict['plotGroup{0}Min'.format(thing)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(thing)]), color=p_dict['group{0}Color'.format(thing)], **k_dict['k_min'])
                if p_dict['plotGroup{0}Max'.format(thing)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(thing)]), color=p_dict['group{0}Color'.format(thing)], **k_dict['k_max'])
                if self.host_plugin.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plot_custom_line_segments(ax, p_dict, k_dict)

            self.format_grids(p_dict, k_dict, log)

            # ================================ Chart Title ================================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # =============================== X Axis Label ================================
            self.format_axis_x_label(dev, p_dict, k_dict, log)

            # =============================== Y Axis Label ================================
            # self.format_axis_y1_label(p_dict, k_dict, log)

            # ============================== Custom Y Ticks ===============================
            self.format_axis_y_ticks(p_dict, k_dict, log)

            # ================================ Save Image =================================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, ValueError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def chart_weather_forecast(self, dev, dev_type, p_dict, k_dict, state_list, sun_rise_set, return_queue):
        """
        Creates the weather charts

        Given the unique nature of weather chart construction, we have a separate
        method for these charts. Note that it is not currently possible within the
        multiprocessing framework used to query the indigo server, so we need to
        send everything we need through the method call.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param unicode dev_type: device type name
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param class 'indigo.Dict' state_list: the data to plot
        :param list sun_rise_set: tuple of sunrise/sunset times
        :param class 'multiprocessing.queues.Queue' return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            p_dict['backgroundColor']  = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']        = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))
            p_dict['line1Color']       = r"#{0}".format(p_dict['line1Color'].replace(' ', '').replace('#', ''))
            p_dict['line2Color']       = r"#{0}".format(p_dict['line2Color'].replace(' ', '').replace('#', ''))
            p_dict['line3Color']       = r"#{0}".format(p_dict['line3Color'].replace(' ', '').replace('#', ''))
            p_dict['line1MarkerColor'] = r"#{0}".format(p_dict['line1MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['line2MarkerColor'] = r"#{0}".format(p_dict['line2MarkerColor'].replace(' ', '').replace('#', ''))

            dates_to_plot = p_dict['dates_to_plot']

            for line in range(1, 4, 1):

                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Debug'].append(u"[{0}] A line color is the same as the background color (so you will not be able to see it).".format(dev.name))

            # ========================== Fantastic Hourly Device ==========================
            if dev_type == 'Hourly':

                for counter in range(1, 25, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)

                    epoch = state_list['h{0}_epoch'.format(counter)]
                    time_stamp = dt.datetime.fromtimestamp(epoch)
                    time_stamp = dt.datetime.strftime(time_stamp, "%Y-%m-%d %H:%M")
                    p_dict['x_obs1'].append(time_stamp)

                    p_dict['y_obs1'].append(state_list['h{0}_temperature'.format(counter)])
                    p_dict['y_obs3'].append(state_list['h{0}_precipChance'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'], log)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('Temperature',)  # Note that the trailing comma is required to ensure that Matplotlib interprets the legend as a tuple.
                    p_dict['headers_2']    = ('Precipitation',)
                    p_dict['daytimeColor'] = r"#{0}".format(p_dict['daytimeColor'].replace(' ', '').replace('#', ''))

            # ======================== WUnderground Hourly Device =========================
            elif dev_type == 'wundergroundHourly':

                for counter in range(1, 25, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['h{0}_timeLong'.format(counter)])
                    p_dict['y_obs1'].append(state_list['h{0}_temp'.format(counter)])
                    p_dict['y_obs3'].append(state_list['h{0}_precip'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'], log)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('Temperature',)  # Note that the trailing comma is required to ensure that Matplotlib interprets the legend as a tuple.
                    p_dict['headers_2']    = ('Precipitation',)
                    p_dict['daytimeColor'] = r"#{0}".format(p_dict['daytimeColor'].replace(' ', '').replace('#', ''))

            # ========================== Fantastic Daily Device ===========================
            elif dev_type == 'Daily':

                for counter in range(1, 9, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['d{0}_date'.format(counter)])
                    p_dict['y_obs1'].append(state_list['d{0}_temperatureHigh'.format(counter)])
                    p_dict['y_obs2'].append(state_list['d{0}_temperatureLow'.format(counter)])
                    p_dict['y_obs3'].append(state_list['d{0}_precipChance'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'], log)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('High Temperature', 'Low Temperature',)
                    p_dict['headers_2']    = ('Precipitation',)

            # ======================== WUnderground Ten Day Device ========================
            elif dev_type == 'wundergroundTenDay':

                for counter in range(1, 11, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['d{0}_date'.format(counter)])
                    p_dict['y_obs1'].append(state_list['d{0}_high'.format(counter)])
                    p_dict['y_obs2'].append(state_list['d{0}_low'.format(counter)])
                    p_dict['y_obs3'].append(state_list['d{0}_pop'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'], log)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('High Temperature', 'Low Temperature',)
                    p_dict['headers_2']    = ('Precipitation',)

            else:
                log['Warning'].append(u"This device type only supports Fantastic Weather (v0.1.05 or later) and WUnderground forecast devices.")

            log['Threaddebug'].append(u"p_dict: {0}".format(p_dict))

            # ==================================== AX1 ====================================
            ax1 = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.format_axis_x_ticks(ax1, p_dict, k_dict, log)
            self.format_axis_y(ax1, p_dict, k_dict, log)

            # ============================ Precipitation Bars =============================
            # The width of the bars is a percentage of a day, so we need to
            # account for instances where the unit of time could be hours to
            # months or years.

            # Plot precipitation bars
            if p_dict['y_obs3']:
                if len(dates_to_plot) <= 15:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=((1.0 / len(dates_to_plot)) * 5), zorder=10)
                else:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=(1.0 / (len(dates_to_plot) * 1.75)), zorder=10)

                # Precipitation bar annotations
                if p_dict['line3Annotate']:
                    for xy in zip(dates_to_plot, p_dict['y_obs3']):
                        ax1.annotate('%.0f' % xy[1], xy=(xy[0], 5), xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # ============================== Precip Min/Max ===============================
            if p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] != 'None':
                y2_axis_min = float(p_dict['y2AxisMin'])
                y2_axis_max = float(p_dict['y2AxisMax'])

            elif p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] == 'None':
                y2_axis_min = float(p_dict['y2AxisMin'])
                y2_axis_max = max(p_dict['y_obs3'])

            elif p_dict['y2AxisMin'] == 'None' and p_dict['y2AxisMax'] != 'None':
                y2_axis_min = 0
                y2_axis_max = float(p_dict['y2AxisMax'])

            else:
                if max(p_dict['y_obs3']) - min(p_dict['y_obs3']) == 0:
                    y2_axis_min = 0
                    y2_axis_max = 1
                elif max(p_dict['y_obs3']) != 0 and min(p_dict['y_obs3']) != 0 and 0 < max(p_dict['y_obs3']) - min(p_dict['y_obs3']) <= 1:
                    y2_axis_min = min(p_dict['y_obs3']) * (1 - (1 / min(p_dict['y_obs3']) ** 1.25))
                    y2_axis_max = max(p_dict['y_obs3']) * (1 + (1 / max(p_dict['y_obs3']) ** 1.25))
                else:
                    if min(p_dict['y_obs3']) < 0:
                        y2_axis_min = min(p_dict['y_obs3']) * 1.5
                    else:
                        y2_axis_min = min(p_dict['y_obs3']) * 0.75
                    if max(p_dict['y_obs3']) < 0:
                        y2_axis_max = 0
                    else:
                        y2_axis_max = max(p_dict['y_obs3']) * 1.10

            plt.ylim(ymin=y2_axis_min, ymax=y2_axis_max)

            # =============================== X1 Axis Label ===============================
            self.format_axis_x_label(dev, p_dict, k_dict, log)

            # =============================== Y1 Axis Label ===============================
            # Note we're plotting Y2 label on ax1. We do this because we want the
            # precipitation bars to be under the temperature plot but we want the
            # precipitation scale to be on the right side.
            plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])
            ax1.yaxis.set_label_position('right')

            # ============================= Legend Properties =============================
            # (note that we need a separate instance of this code for each subplot. This
            # one controls the precipitation subplot.) Legend should be plotted before any
            # other lines are plotted (like averages or custom line segments).

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_2']]
                legend = ax1.legend(headers, loc='upper right', bbox_to_anchor=(1.0, -0.12), ncol=1, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)  # Note: frame alpha should be an int and not a string.

            self.format_grids(p_dict, k_dict, log)

            # ========================== Transparent Charts Fill ==========================
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax1.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax1.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ============================= Sunrise / Sunset ==============================
            # Note that this highlights daytime hours on the chart.

            daylight = dev.pluginProps.get('showDaytime', True)

            if daylight and dev_type in ('Hourly', 'wundergroundHourly'):

                sun_rise, sun_set = self.format_dates(sun_rise_set, log)

                min_dates_to_plot = np.amin(dates_to_plot)
                max_dates_to_plot = np.amax(dates_to_plot)

                # We will only highlight daytime if the current values for sunrise and sunset
                # fall within the limits of dates_to_plot. We add and subtract one second for
                # each to account for microsecond rounding.
                if (min_dates_to_plot - 1) < sun_rise < (max_dates_to_plot + 1) and (min_dates_to_plot - 1) < sun_set < (max_dates_to_plot + 1):

                    # If sunrise is less than sunset, they are on the same day so we fill in
                    # between the two.
                    if sun_rise < sun_set:
                        ax1.axvspan(sun_rise, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

                    # If sunrise is greater than sunset, the next sunrise is tomorrow
                    else:
                        ax1.axvspan(min_dates_to_plot, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)
                        ax1.axvspan(sun_rise, max_dates_to_plot, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

            # ==================================== AX2 ====================================

            # ============================= Temperatures Plot =============================
            # Create a second plot area and plot the temperatures.
            ax2 = ax1.twinx()
            ax2.margins(0.04, 0.05)  # This needs to remain or the margins get screwy (they don't carry over from ax1).

            for line in range(1, 3, 1):
                if p_dict['y_obs{0}'.format(line)]:
                    ax2.plot(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                             marker=p_dict['line{0}Marker'.format(line)], markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=(10 - line), **k_dict['k_line'])

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax2.annotate('%.0f' % xy[1], xy=xy, xytext=(0, 0), zorder=(11 - line), **k_dict['k_annotation'])

            self.format_axis_x_ticks(ax2, p_dict, k_dict, log)
            self.format_axis_y(ax2, p_dict, k_dict, log)

            self.plot_custom_line_segments(ax2, p_dict, k_dict)

            plt.autoscale(enable=True, axis='x', tight=None)

            # Note that we plot the bar plot so that it will be under the line plot, but we still want the temperature scale on the left and the percentages on the right.
            ax1.yaxis.tick_right()
            ax2.yaxis.tick_left()

            # ========================= Temperature Axis Min/Max ==========================
            if p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] != 'None':
                y_axis_min = float(p_dict['yAxisMin'])
                y_axis_max = float(p_dict['yAxisMax'])

            elif p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] == 'None':
                y_axis_min = float(p_dict['yAxisMin'])
                y_axis_max = max(p_dict['data_array'])

            elif p_dict['yAxisMin'] == 'None' and p_dict['yAxisMax'] != 'None':
                y_axis_min = min(p_dict['data_array'])
                y_axis_max = float(p_dict['yAxisMax'])

            else:
                if max(p_dict['data_array']) - min(p_dict['data_array']) == 0:
                    y_axis_min = 0
                    y_axis_max = 1
                elif max(p_dict['data_array']) != 0 and min(p_dict['data_array']) != 0 and 0 < max(p_dict['data_array']) - min(p_dict['data_array']) <= 1:
                    y_axis_min = min(p_dict['data_array']) * (1 - (1 / min(p_dict['data_array']) ** 1.25))
                    y_axis_max = max(p_dict['data_array']) * (1 + (1 / max(p_dict['data_array']) ** 1.25))
                else:
                    if min(p_dict['data_array']) < 0:
                        y_axis_min = min(p_dict['data_array']) * 1.5
                    else:
                        y_axis_min = min(p_dict['data_array']) * 0.75
                    if max(p_dict['data_array']) < 0:
                        y_axis_max = 0
                    else:
                        y_axis_max = max(p_dict['data_array']) * 1.10
            plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

            # =============================== Y2 Axis Label ===============================
            # Note we're plotting Y1 label on ax2. We do this because we want the
            # temperature lines to be over the precipitation bars but we want the
            # temperature scale to be on the left side.
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])  # Note we're plotting Y1 label on ax2
            ax2.yaxis.set_label_position('left')

            # ================================ Chart Title ================================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ============================= Legend Properties =============================
            # (note that we need a separate instance of this code for each subplot. This
            # one controls the temperatures subplot.) Legend should be plotted before any
            # other lines are plotted (like averages or custom line segments).

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_1']]
                legend = ax2.legend(headers, loc='upper left', bbox_to_anchor=(0.0, -0.12), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            self.format_grids(p_dict, k_dict, log)

            # ================================ Save Image =================================
            plt.tight_layout(pad=1)
            plt.subplots_adjust(bottom=0.2)
            self.save_chart_image(plt, p_dict, k_dict)

            # Prepare log for output.
            if log['Warning'] or log['Critical']:
                return_queue.put({'Error': True, 'Log': log, 'Message': 'chart updated with errors.', 'Name': dev.name})
            else:
                return_queue.put({'Error': False, 'Log': log, 'Message': 'chart updated successfully.', 'Name': dev.name})

        except (KeyError, ValueError) as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Warning'].append(u"This device type only supports Fantastic Weather (v0.1.05 or later) and WUnderground forecast devices.")
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            return_queue.put({'Error': True, 'Log': log, 'Message': u"{0}. See plugin log for more information.".format(sub_error), 'Name': dev.name})

    # =============================================================================
    def clean_string(self, val):
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

    # =============================================================================
    def convert_the_data(self, final_data, log, data_source):
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
                     'unlocked': 0, 'up': 1, 'down': 0, '1': 1, '0': 0, 'heat': 1}
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

        # We have converted all nonsense numbers to '-99.0'. Let's replace
        # those with 'NaN' for charting.
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
            log['Warning'].append(u'CSV file does not have sufficient information to make a useful plot. File: {0}'.format(data_source))

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

        return final_data, log

    # =============================================================================
    def format_axis_x_label(self, dev, p_dict, k_dict, log):
        """
        Format X axis label visibility and properties

        If the user chooses to display a legend, we don't want an axis label because
        they will fight with each other for space.

        -----

        :param class 'indigo.Device' dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: logging dict
        :return unicode result:
        """

        try:
            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
                return u"[{0}] No call for legend. Formatting X label.".format(dev.name)

            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ('', 'null'):
                return u"[{0}] X axis label is suppressed to make room for the chart legend.".format(dev.name)

            return ''

        except (ValueError, TypeError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting X labels: showLegend = {0}".format(p_dict['showLegend']))
            log['Threaddebug'].append(u"Problem formatting X labels: customAxisLabelX = {0}".format(p_dict['customAxisLabelX']))
            log['Threaddebug'].append(u"Problem formatting X labels: k_x_axis_font = {0}".format(k_dict['k_x_axis_font']))

    # =============================================================================
    def format_axis_x_scale(self, x_axis_bins, log):
        """
        Format X axis scale based on user setting

        The format_axis_x_scale() method sets the bins for the X axis. Presently, we
        assume a date-based X axis.

        -----

        :param list x_axis_bins:
        :param dict log: logging dict
        """

        try:
            if x_axis_bins == 'quarter-hourly':
                plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
                plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 96)))
            if x_axis_bins == 'half-hourly':
                plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
                plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 48)))
            elif x_axis_bins == 'hourly':
                plt.gca().xaxis.set_major_locator(mdate.HourLocator(interval=4))
                plt.gca().xaxis.set_minor_locator(mdate.HourLocator(byhour=range(0, 24, 24)))
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
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting X axis scale: x_axis_bins = {0}".format(x_axis_bins))

    # =============================================================================
    def format_axis_x_ticks(self, ax, p_dict, k_dict, log):
        """
        Format X axis tick properties

        Controls the format and placement of the tick marks on the X axis.

        -----

        :param class 'matplotlib.axes.AxesSubplot' ax:
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: Logging dict
        """

        try:
            ax.tick_params(axis='x', **k_dict['k_major_x'])
            ax.tick_params(axis='x', **k_dict['k_minor_x'])
            ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
            self.format_axis_x_scale(p_dict['xAxisBins'], log)  # Set the scale for the X axis. We assume a date.

            # If the x axis format has been set to None, let's hide the labels.
            if p_dict['xAxisLabelFormat'] == "None":
                ax.axes.xaxis.set_ticklabels([])

            return ax

        except (ValueError, TypeError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting X ticks: k_major_x = {0}".format(k_dict['k_major_x']))
            log['Threaddebug'].append(u"Problem formatting X ticks: k_minor_x = {0}".format(k_dict['k_minor_x']))
            log['Threaddebug'].append(u"Problem formatting X ticks: xAxisLabelFormat = {0}".format(mdate.DateFormatter(p_dict['xAxisLabelFormat'])))
            log['Threaddebug'].append(u"Problem formatting X ticks: xAxisBins = {0}".format(p_dict['xAxisBins']))

    # =============================================================================
    def format_axis_y(self, ax, p_dict, k_dict, log):
        """
        Format Y1 axis display properties

        Controls the format and properties of the Y axis.

        -----

        :param class 'matplotlib.axes.AxesSubplot' ax:
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: Logging dict
        """

        try:
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

            return ax

        except (ValueError, TypeError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting Y ticks: k_major_y = {0}".format(k_dict['k_major_y']))
            log['Threaddebug'].append(u"Problem formatting Y ticks: k_minor_x = {0}".format(k_dict['k_minor_y']))
            log['Threaddebug'].append(u"Problem formatting Y ticks: xAxisLabelFormat = {0}".format(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision'])))))
            log['Threaddebug'].append(u"Problem formatting Y ticks: yMirrorValues = {0}".format(p_dict['yMirrorValues']))
            log['Threaddebug'].append(u"Problem formatting Y ticks: yMirrorValuesAlsoY1 = {0}".format(p_dict['yMirrorValuesAlsoY1']))

    # =============================================================================
    def format_axis_y1_min_max(self, p_dict, log):
        """
        Format Y1 axis range limits

        Setting the limits before the plot turns off autoscaling, which causes the
        limit that's not set to behave weirdly at times. This block is meant to
        overcome that weirdness for something more desirable.

        -----

        :param dict p_dict: plotting parameters
        :param dict log: Logging dict
        """

        try:

            y_min = min(p_dict['data_array'])
            y_max = max(p_dict['data_array'])

            # Since the min / max is used here only for chart boundaries, we "trick"
            # Matplotlib by using a number that's very nearly zero.
            if y_min == 0:
                y_min = 0.000001

            if y_max == 0:
                y_max = 0.000001

            # Y min
            if isinstance(p_dict['yAxisMin'], unicode) and p_dict['yAxisMin'].lower() == 'none':
                y_axis_min = y_min * (1 - (1 / y_min ** 1.25))
            else:
                y_axis_min = float(p_dict['yAxisMin'])

            # Y max
            if isinstance(p_dict['yAxisMax'], unicode) and p_dict['yAxisMax'].lower()== 'none':
                y_axis_max = y_max * (1 + (1 / y_max ** 1.25))
            else:
                y_axis_max = float(p_dict['yAxisMax'])

            plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

            return log

        except (ValueError, TypeError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting Y1 Min/Max: yAxisMax = {0}".format(p_dict['yAxisMax']))
            log['Threaddebug'].append(u"Problem formatting Y1 Min/Max: yAxisMin = {0}".format(p_dict['yAxisMin']))
            log['Threaddebug'].append(u"Problem formatting Y1 Min/Max: Data Min/Max = {0}/{1}".format(min(p_dict['data_array']), max(p_dict['data_array'])))
            log['Warning'].append(u"Error setting axis limits for Y1. Will rely on Matplotlib to determine limits.")

    # =============================================================================
    def format_axis_y1_label(self, p_dict, k_dict, log):
        """
        Format Y1 axis labels

        Controls the format and placement of labels for the Y1 axis.

        -----

        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: logging dict
        """

        try:
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

        except (ValueError, TypeError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting Y1 axis label: customAxisLabelY = {0}".format(p_dict['customAxisLabelY']))
            log['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = {0}".format(k_dict['k_y_axis_font']))

    # =============================================================================
    def format_axis_y_ticks(self, p_dict, k_dict, log):
        """
        Format Y axis tick marks

        Controls the format and placement of Y ticks.

        -----

        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: logging dict
        """
        # TODO: why are we plotting the Y axis label in a ticks method?

        custom_ticks_marks  = p_dict['customTicksY'].strip()
        custom_ticks_labels = p_dict['customTicksLabelY'].strip()

        try:
            # The label for the Y axis.
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

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
            log['Threaddebug'].append(u"Problem formatting Y axis ticks: customAxisLabelY = {0}".format(p_dict['customAxisLabelY']))
            log['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = {0}".format(k_dict['k_y_axis_font']))
            log['Threaddebug'].append(u"Problem formatting Y1 axis label: customTicksY = {0}".format(p_dict['customTicksY']))
            self.host_plugin.pluginErrorHandler(traceback.format_exc())

    # =============================================================================
    # TODO: this is currently unused.
    def format_axis_y2_label(self, p_dict, k_dict, log):
        """
        Format Y2 axis properties

        Controls the format and placement of labels for the Y2 axis.

        -----

        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: logging dict
        """

        try:
            plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])

        except (KeyError, ValueError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting Y2 axis label: customAxisLabelY2 = {0}".format(p_dict['customAxisLabelY2']))
            log['Threaddebug'].append(u"Problem formatting Y1 axis label: k_y_axis_font = {0}".format(k_dict['k_y_axis_font']))

    # =============================================================================
    def format_dates(self, list_of_dates, log):
        """
        Convert date strings to date objects

        Convert string representations of date values to values to mdate values for
        charting.

        -----

        :param list list_of_dates:
        :param dict log: logging dict
        """

        dates_to_plot   = []
        dates_to_plot_m = []

        try:
            dates_to_plot = [date_parse(obs) for obs in list_of_dates]
            dates_to_plot_m = mdate.date2num(dates_to_plot)

            return dates_to_plot_m

        except (KeyError, ValueError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting dates: list_of_dates = {0}".format(list_of_dates))
            log['Threaddebug'].append(u"Problem formatting dates: dates_to_plot = {0}".format(dates_to_plot))
            log['Threaddebug'].append(u"Problem formatting dates: dates_to_plot_m = {0}".format(dates_to_plot_m))

    # =============================================================================
    def format_grids(self, p_dict, k_dict, log):
        """
        Format matplotlib grids

        Format grids for visibility and properties.

        -----

        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param dict log: logging dict

        """

        try:
            if p_dict['showxAxisGrid']:
                plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

            if p_dict['showyAxisGrid']:
                plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

        except (KeyError, ValueError):
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            log['Threaddebug'].append(u"Problem formatting grids: showxAxisGrid = {0}".format(p_dict['showxAxisGrid']))
            log['Threaddebug'].append(u"Problem formatting grids: k_grid_fig = {0}".format(k_dict['k_grid_fig']))

    # =============================================================================
    def get_data(self, data_source, log):
        """
        Retrieve data from CSV file.

        Reads data from source CSV file and returns a list of tuples for charting. The
        data are provided as unicode strings [('formatted date', 'observation'), ...]

        -----

        :param unicode data_source:
        :param dict log:
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
            final_data, log = self.convert_the_data(final_data, log, data_source)

            return final_data, log

        # If we can't find the target CSV file, we create a phony proxy which the plugin
        # can process without dying.
        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            final_data.extend([('timestamp', 'placeholder'), (now_text, 0)])
            log['Warning'].append(u"Error downloading CSV data: {0}. See plugin log for more information.".format(sub_error))

            return final_data, log

    # =============================================================================
    def make_chart_figure(self, width, height, p_dict):
        """
        Create the matplotlib figure object and create the main axes element.

        Create the figure object for charting and include one axes object. The method
        also add a few customizations when defining the objects.

        -----

        :param float width:
        :param float height:
        :param dict p_dict: plotting parameters
        """

        dpi = plt.rcParams['savefig.dpi']
        height = float(height)
        width = float(width)

        fig = plt.figure(1, figsize=(width / dpi, height / dpi))
        ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
        ax.margins(0.04, 0.05)
        [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

        return ax

    # =============================================================================
    def plot_best_fit_line_segments(self, ax, dates_to_plot, line, p_dict):
        """
        Adds best fit line segments to plots

        The plot_best_fit_line_segments method provides a utility to add "best fit lines"
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

            ax.plot(np.unique(dates_to_plot), np.poly1d(np.polyfit(dates_to_plot, p_dict['y_obs{0}'.format(line)], 1))(np.unique(dates_to_plot)), color=color, zorder=1)

            return ax

        except TypeError as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            self.host_plugin.logger.threaddebug(u"p_dict: {0}.".format(p_dict))
            self.host_plugin.logger.threaddebug(u"dates_to_plot: {0}.".format(dates_to_plot))
            self.host_plugin.logger.warning(u"There is a problem with the best fit line segments settings. Error: {0}. See plugin log for more information.".format(sub_error))

    # =============================================================================
    def plot_custom_line_segments(self, ax, p_dict, k_dict):
        """
        Chart custom line segments handler

        Process any custom line segments and add them to the
        matplotlib axes object.

        -----

        :param class 'matplotlib.axes.AxesSubplot' ax:
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        """

        # Plot the custom lines if needed.  Note that these need to be plotted after
        # the legend is established, otherwise some of the characteristics of the
        # min/max lines will take over the legend props.

        if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ("", "None"):

            try:
                constants_to_plot = literal_eval(p_dict['customLineSegments'])

                cls = ax

                for element in constants_to_plot:
                    if type(element) == tuple:
                        cls = ax.axhline(y=element[0], color=element[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        # If we want to promote custom line segments, we need to add them to the list that's used to calculate the Y axis limits.
                        if self.host_plugin.pluginPrefs.get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(element[0])
                    else:
                        cls = ax.axhline(y=constants_to_plot[0], color=constants_to_plot[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        if self.host_plugin.pluginPrefs.get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(constants_to_plot[0])

                return cls

            except Exception as sub_error:
                self.host_plugin.pluginErrorHandler(traceback.format_exc())
                self.host_plugin.logger.warning(u"There is a problem with the custom line segments settings. {0}. See plugin log for more information.".format(sub_error))

                return ax

    # =============================================================================
    def save_chart_image(self, plot, p_dict, k_dict):
        """
        Save the chart figure to a file.

        Uses the matplotlib savefig module to write the chart to a file.

        -----

        :param module plot:
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        """

        try:
            if p_dict['chartPath'] != '' and p_dict['fileName'] != '':
                plot.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

                plot.clf()
                plot.close('all')

        except RuntimeError as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            self.host_plugin.logger.warning(u"Matplotlib encountered a problem trying to save the image. Error: {0}. See plugin log for more information.".format(sub_error))

    # =============================================================================
