#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
matplotlib plugin
author: DaveL17

The matplotlib plugin is used to produce various types of charts and graphics
for use on Indigo control pages. The key benefits of the plugin are its ability
to make global changes to all generated charts (i.e., fonts, colors) and its
relative simplicity.  It contains direct support for some automated charts (for
example, it can create WUnderground plugin forecast charts if linked to the
proper WUnderground devices.
"""

# =================================== TO DO ===================================

# TODO: NEW -- Create a new device to create a horizontal bar chart (i.e., like device battery levels.)
# TODO: NEW -- Create a new device to plot with Y2. This is more complicated than it sounds.  Separate device type?
# TODO: NEW -- Create an "error" chart with min/max/avg
# TODO: NEW -- Standard chart types with pre-populated data that link to types of Indigo devices.

# TODO: Consider ways to make variable CSV data file lengths or user settings to vary the number of observations shown (could be date range or number of obs).
# TODO: Independent Y2 axis.
# TODO: Trap condition where there are too many observations to plot (i.e., too many x axis values). What would this mean? User could do very wide line chart
# TODO:   with extremely large number of observations.
# TODO: Possible to add custom labels to battery health chart? The rub is that when a new device is added or one's removed, the labels would no longer match up.
# TODO: Wrap long names for battery health device?
# TODO: Implement a stale data tool
# TODO: New weather forecast charts to support any weather services

# ================================== IMPORTS ==================================

# Built-in modules
from ast import literal_eval
from csv import reader
import datetime as dt
from dateutil.parser import parse as date_parse
import logging
import multiprocessing
import numpy as np
import os
import traceback
import re

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
from DLFramework import indigoPluginUpdateChecker
try:
    import indigo
except ImportError as error:
    pass
try:
    import pydevd  # To support remote debugging
except ImportError as error:
    pass

# My modules
import DLFramework.DLFramework as Dave

# =================================== HEADER ==================================

__author__    = Dave.__author__
__copyright__ = Dave.__copyright__
__license__   = Dave.__license__
__build__     = Dave.__build__
__title__     = "Matplotlib Plugin for Indigo Home Control"
__version__   = "0.7.04"

# =============================================================================

kDefaultPluginPrefs = {
    u'backgroundColor': "00 00 00",
    u'backgroundColorOther': False,
    u'chartPath': "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/images/controls/static/",
    u'chartResolution': 100,
    u'dataPath': "{0}/com.fogbert.indigoplugin.matplotlib/".format(indigo.server.getLogsFolderPath()),
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
    u'tickSize': 4
}


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.pluginIsInitializing = True
        self.pluginIsShuttingDown = False

        # ========================= Initialize Logger =========================
        self.plugin_file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug      = True
        self.debugLevel = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debugLevel)

        # ===================== Initialize Update Checker =====================
        updater_url  = "https://raw.githubusercontent.com/DaveL17/matplotlib/master/matplotlib_version.html"
        self.updater = indigoPluginUpdateChecker.updateChecker(self, updater_url)

        # ==================== Initialize Global Variables ====================
        self.final_data     = []
        self.verboseLogging = self.pluginPrefs.get('verboseLogging', False)  # From advanced settings menu

        # ====================== Initialize DLFramework =======================
        self.Fogbert  = Dave.Fogbert(self)  # Plugin functional framework
        self.evalExpr = Dave.evalExpr(self)  # Formula evaluation framework

        # Log pluginEnvironment information when plugin is first started
        self.Fogbert.pluginEnvironment()

        # Convert old debugLevel scale (low, medium, high) to new scale (1, 2, 3).
        if not int(self.pluginPrefs.get('showDebugLevel')):
            self.pluginPrefs['showDebugLevel'] = self.Fogbert.convertDebugLevel(self.debugLevel)

        # ======================= Log More Plugin Info ========================
        self.pluginEnvironmentLogger()

        # ============== Conform Custom Colors to Color Picker ================
        # See method for more info.
        self.convert_custom_colors()

        # ========================= Remote Debug Hook =========================
        # try:
        #     pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)
        # except:
        #     pass

        self.pluginIsInitializing = False

    def __del__(self):
        indigo.PluginBase.__del__(self)

# Indigo Methods ==============================================================

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):

        pass

    def closedPrefsConfigUi(self, valuesDict, userCancelled):

        pass

    def deviceStartComm(self, dev):

        # Check to see if the device profile has changed.
        dev.stateListOrDisplayStateIdChanged()

        if dev.deviceTypeId != 'csvEngine' and dev.states['chartLastUpdated'] == "":
            dev.updateStateOnServer(key='chartLastUpdated', value='1970-01-01 00:00:00.000000')

        dev.stateListOrDisplayStateIdChanged()
        dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Enabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    def deviceStopComm(self, dev):

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    def getDeviceConfigUiValues(self, valuesDict, typeId, devId):

        if self.verboseLogging:
            self.logger.threaddebug(u"pluginProps = {0}".format(dict(valuesDict)))

        dev = indigo.devices[int(devId)]

        try:

            if typeId == "csvEngine":
                valuesDict['addItemFieldsCompleted'] = False
                valuesDict['addKey']                 = ""
                valuesDict['addSource']              = ""
                valuesDict['addState']               = ""
                valuesDict['addValue']               = ""
                valuesDict['csv_item_list']          = ""
                valuesDict['editKey']                = ""
                valuesDict['editSource']             = ""
                valuesDict['editState']              = ""
                valuesDict['editValue']              = ""
                valuesDict['isColumnSelected']       = False
                valuesDict['previousKey']            = ""
                self.logger.debug(u"Analyzing CSV Engine device settings.")
                return valuesDict

            # For existing devices
            if dev.configured:

                # Update legacy color values from hex to raw (#FFFFFF --> FF FF FF)
                for prop in valuesDict:
                    if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', unicode(valuesDict[prop])):
                        s = valuesDict[prop]
                        valuesDict[prop] = u'{0} {1} {2}'.format(s[0:3], s[3:5], s[5:7]).replace('#', '')

            # For new devices, force certain defaults that don't carry from devices.xml. This seems to be especially important for
            # menu items built with callbacks and colorpicker controls that don't appear to accept defaultValue.
            if not dev.configured:

                valuesDict['refreshInterval'] = '900'

                # ============================ Bar Charting Device ============================
                if typeId == "barChartingDevice":

                    for _ in range(1, 5, 1):
                        valuesDict['bar{0}Color'.format(_)]  = 'FF FF FF'
                        valuesDict['bar{0}Source'.format(_)] = 'None'

                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                # =========================== Battery Health Device ============================
                if typeId == "batteryHealthDevice":
                    valuesDict['healthyColor']     = '00 00 CC'
                    valuesDict['cautionLevel']     = '10'
                    valuesDict['cautionColor']     = 'FF FF 00'
                    valuesDict['warningLevel']     = '5'
                    valuesDict['warningColor']     = 'FF 00 00'
                    valuesDict['showBatteryLevel'] = 'true'

                # ========================== Calendar Charting Device ==========================
                if typeId == "calendarChartingDevice":
                    valuesDict['fontSize'] = 16

                # ============================ Line Charting Device ============================
                if typeId == "lineChartingDevice":

                    for _ in range(1, 7, 1):
                        valuesDict['line{0}BestFit'.format(_)]      = False
                        valuesDict['line{0}BestFitColor'.format(_)] = 'FF 00 00'
                        valuesDict['line{0}Color'.format(_)]        = 'FF FF FF'
                        valuesDict['line{0}Marker'.format(_)]       = 'None'
                        valuesDict['line{0}MarkerColor'.format(_)]  = 'FF FF FF'
                        valuesDict['line{0}Source'.format(_)]       = 'None'
                        valuesDict['line{0}Style'.format(_)]        = '-'

                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                # =========================== Multiline Text Device ============================
                if typeId == "multiLineText":
                    valuesDict['textColor']  = "FF 00 FF"
                    valuesDict['thing']      = 'None'
                    valuesDict['thingState'] = 'None'

                # =========================== Polar Charting Device ============================
                if typeId == "polarChartingDevice":
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['currentWindColor']    = 'FF 33 33'
                    valuesDict['maxWindColor']        = '33 33 FF'
                    valuesDict['radiiValue']          = 'None'
                    valuesDict['thetaValue']          = 'None'

                # ========================== Scatter Charting Device ===========================
                if typeId == "scatterChartingDevice":

                    for _ in range(1, 5, 1):
                        valuesDict['line{0}BestFit'.format(_)]      = False
                        valuesDict['line{0}BestFitColor'.format(_)] = 'FF 00 00'
                        valuesDict['group{0}Color'.format(_)]       = 'FF FF FF'
                        valuesDict['group{0}Marker'.format(_)]      = '.'
                        valuesDict['group{0}MarkerColor'.format(_)] = 'FF FF FF'
                        valuesDict['group{0}Source'.format(_)]      = 'None'

                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                # ========================== Weather Forecast Device ===========================
                if typeId == "forecastChartingDevice":

                    for _ in range(1, 3, 1):
                        valuesDict['line{0}Color'.format(_)]       = 'FF 33 33'
                        valuesDict['line{0}Marker'.format(_)]      = 'None'
                        valuesDict['line{0}MarkerColor'.format(_)] = 'FF FF FF'
                        valuesDict['line{0}Style'.format(_)]       = '-'

                    valuesDict['customLineStyle']      = '-'
                    valuesDict['customTickFontSize']   = 8
                    valuesDict['customTitleFontSize']  = 10
                    valuesDict['forecastSourceDevice'] = 'None'
                    valuesDict['line3Color']           = '99 CC FF'
                    valuesDict['line3MarkerColor']     = 'FF FF FF'
                    valuesDict['xAxisBins']            = 'daily'
                    valuesDict['xAxisLabelFormat']     = '%A'
                    valuesDict['showDaytime']          = 'true'
                    valuesDict['daytimeColor']         = '33 33 33'

            if self.pluginPrefs.get('enableCustomLineSegments', False):
                valuesDict['enableCustomLineSegmentsSetting'] = True
                self.logger.debug(u"Enabling advanced feature: Custom Line Segments.")
            else:
                valuesDict['enableCustomLineSegmentsSetting'] = False

            # If enabled, reset all device config dialogs to a minimized state (all sub-groups minimized upon
            # open.) Otherwise, leave them where they are.
            if self.pluginPrefs.get('snappyConfigMenus', False):
                self.logger.debug(u"Enabling advanced feature: Snappy Config Menus.")

                for key in ['barLabel1', 'barLabel2', 'barLabel3', 'barLabel4',
                            'lineLabel1', 'lineLabel2', 'lineLabel3', 'lineLabel4', 'lineLabel5', 'lineLabel6',
                            'groupLabel1', 'groupLabel1', 'groupLabel2', 'groupLabel3', 'groupLabel4',
                            'xAxisLabel', 'xAxisLabel', 'y2AxisLabel', 'yAxisLabel', ]:
                    valuesDict[key] = False

            return valuesDict

        except KeyError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.debug(u"KeyError preparing device config values: {0}".format(sub_error))

        return True

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

    def getMenuActionConfigUiValues(self, menuId):

        self.logger.debug(u"{0:*^80}".format(' Advanced Settings Menu '))

        settings     = indigo.Dict()
        error_msg_dict = indigo.Dict()
        settings['enableCustomLineSegments']  = self.pluginPrefs.get('enableCustomLineSegments', False)
        settings['promoteCustomLineSegments'] = self.pluginPrefs.get('promoteCustomLineSegments', False)
        settings['snappyConfigMenus']         = self.pluginPrefs.get('snappyConfigMenus', False)
        settings['forceOriginLines']          = self.pluginPrefs.get('forceOriginLines', False)
        self.logger.debug(u"Advanced settings menu initial prefs: {0}".format(dict(settings)))

        return settings, error_msg_dict

    def getPrefsConfigUiValues(self):

        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        if self.verboseLogging:
            self.logger.debug(u"{0:=^80}".format(' Get Prefs Config UI Values '))
            self.logger.threaddebug(u"Initial plugin_prefs: {0}".format(dict(plugin_prefs)))

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

        if self.verboseLogging:
            self.logger.threaddebug(u"Updated initial plugin_prefs: {0}".format(dict(plugin_prefs)))

        return plugin_prefs

    def runConcurrentThread(self):

        self.sleep(0.5)

        while True:
            self.updater.checkVersionPoll()

            self.csv_refresh()
            self.refreshTheCharts()

            self.sleep(15)

    def startup(self):

        for dev in indigo.devices.itervalues("self"):
            props = dev.pluginProps

            # Initially, the plugin was constructed with a standard set of
            # colors that could be overwritten by electing to set a custom
            # color value. With the inclusion of the color picker control, this
            # was no longer needed. So we try to set the color field to the
            # custom value. This block is for device color preferences. They
            # should be updated whether or not the device is enabled in the
            # Indigo UI.
            if '#custom' in props.values() or 'custom' in props.values():
                for prop in props:
                    if 'color' in prop.lower():
                        if props[prop] in ['#custom', 'custom']:
                            indigo.server.log(u"Resetting device preferences for custom colors to new color picker.")
                            if props[u'{0}Other'.format(prop)]:
                                props[prop] = props[u'{0}Other'.format(prop)]
                            else:
                                props[prop] = 'FF FF FF'

            # Establish props for legacy devices
            for _ in range(1, 7, 1):
                props['line{0}Annotate'.format(_)]     = props.get('line{0}Annotate'.format(_), False)
                props['line{0}adjuster'.format(_)]     = props.get('line{0}adjuster'.format(_), "")
                props['line{0}BestFit'.format(_)]      = props.get('line{0}BestFit'.format(_), "")
                props['line{0}BestFitColor'.format(_)] = props.get('line{0}BestFitColor'.format(_), "FF 00 00")
                props['line{0}Color'.format(_)]        = props.get('line{0}Color'.format(_), "FF 00 00")
                props['line{0}Fill'.format(_)]         = props.get('line{0}Fill'.format(_), "")
                props['line{0}MarkerColor'.format(_)]  = props.get('line{0}MarkerColor'.format(_), "FF 00 00")
                props['line{0}Source'.format(_)]       = props.get('line{0}Source'.format(_), "")
                props['plotLine{0}Max'.format(_)]      = props.get('plotLine{0}Max'.format(_), False)
                props['plotLine{0}Min'.format(_)]      = props.get('plotLine{0}Min'.format(_), False)

            # Establishes props.isChart for legacy devices
            props_dict = {'csvEngine': False,
                          'barChartingDevice': True,
                          'batteryHealthDevice': True,
                          'calendarChartingDevice': True,
                          'lineChartingDevice': True,
                          'rcParamsDevice': False,
                          'multiLineText': True,
                          'polarChartingDevice': True,
                          'scatterChartingDevice': True,
                          'forecastChartingDevice': True}

            props['isChart'] = props_dict[dev.deviceTypeId]

            # Establish refresh interval for legacy devices. If the prop isn't present, we
            # set it equal to the user's current global refresh rate.
            if 'refreshInterval' not in props.keys():
                props['refreshInterval'] = self.pluginPrefs.get('refreshInterval', 900)

            dev.replacePluginPropsOnServer(props)

        self.updater.checkVersionPoll()
        self.logger.debug(u"{0}{1}".format("Log Level = ", self.debugLevel))

    def shutdown(self):

        self.logger.debug(u"{0:*^40}".format(' Shut Down '))
        self.pluginIsShuttingDown = True

    def validatePrefsConfigUi(self, valuesDict):

        self.debugLevel = int(valuesDict['showDebugLevel'])
        self.indigo_log_handler.setLevel(self.debugLevel)

        error_msg_dict = indigo.Dict()

        # ======================= Data and Chart Paths ========================
        for path_prop in ['chartPath', 'dataPath']:
            try:
                if not valuesDict[path_prop].endswith('/'):
                    error_msg_dict[path_prop]       = u"The path must end with a forward slash '/'."
                    error_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                    return False, valuesDict, error_msg_dict
            except AttributeError:
                self.pluginErrorHandler(traceback.format_exc())
                error_msg_dict[path_prop]       = u"The  path must end with a forward slash '/'."
                error_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                return False, valuesDict, error_msg_dict

        # ========================= Chart Resolution ==========================
        # Note that chart resolution includes a warning feature that will pass
        # the value after the warning is cleared.
        try:
            # If value is null, a null string, or all whitespace.
            if not valuesDict['chartResolution'] or valuesDict['chartResolution'] == "" or str(valuesDict['chartResolution']).isspace():
                valuesDict['chartResolution'] = "100"
                self.logger.warning(u"No resolution value entered. Resetting resolution to 100 DPI.")
            # If warning flag and the value is potentially too small.
            elif valuesDict['dpiWarningFlag'] and 0 < int(valuesDict['chartResolution']) < 80:
                error_msg_dict['chartResolution'] = u"It is recommended that you enter a value of 80 or more for best results."
                error_msg_dict['showAlertText']   = u"Chart Resolution Warning.\n\nIt is recommended that you enter a value of 80 or more for best results."
                valuesDict['dpiWarningFlag']      = False
                return False, valuesDict, error_msg_dict

            # If no warning flag and the value is good.
            elif not valuesDict['dpiWarningFlag'] or int(valuesDict['chartResolution']) >= 80:
                pass
            else:
                error_msg_dict['chartResolution'] = u"The chart resolution value must be greater than 0."
                error_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nYou have entered a chart resolution value that is less than 0."
                return False, valuesDict, error_msg_dict
        except ValueError:
            self.pluginErrorHandler(traceback.format_exc())
            error_msg_dict['chartResolution'] = u"The chart resolution value must be an integer."
            error_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nYou have entered a chart resolution value that is not an integer."
            return False, valuesDict, error_msg_dict

        # ========================= Chart Dimensions ==========================
        for dimension_prop in ['rectChartHeight', 'rectChartWidth', 'rectChartWideHeight', 'rectChartWideWidth', 'sqChartSize']:
            try:
                if float(valuesDict[dimension_prop]) < 75:
                    error_msg_dict[dimension_prop]  = u"The dimension value must be greater than 75 pixels."
                    error_msg_dict['showAlertText'] = u"Dimension Error.\n\nYou have entered a dimension value that is less than 75 pixels."
                    return False, valuesDict, error_msg_dict
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                error_msg_dict[dimension_prop]  = u"The dimension value must be a real number."
                error_msg_dict['showAlertText'] = u"Dimension Error.\n\nYou have entered a dimension value that is not a real number."
                return False, valuesDict, error_msg_dict

        # ============================ Line Weight ============================
        try:
            if float(valuesDict['lineWeight']) <= 0:
                error_msg_dict['lineWeight']    = u"The line weight value must be greater than 0."
                error_msg_dict['showAlertText'] = u"Line Weight Error.\n\nYou have entered a line weight value that is less than 0."
                return False, valuesDict, error_msg_dict
        except ValueError:
            self.pluginErrorHandler(traceback.format_exc())
            error_msg_dict['lineWeight']    = u"The line weight value must be a real number."
            error_msg_dict['showAlertText'] = u"Line Weight Error.\n\nYou have entered a line weight value that is not a real number."
            return False, valuesDict, error_msg_dict

        valuesDict['dpiWarningFlag'] = True
        self.logger.debug(u"Plugin preferences validated.")
        return True, valuesDict

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):

        error_msg_dict = indigo.Dict()
        dev = indigo.devices[int(devId)]

        # ============================ CSV Engine =============================
        if typeId == 'csvEngine':
            # None at this time.
            self.logger.debug(u"{0} settings validated.".format(dev.name))
            return True, valuesDict

        # ===================== Multiline Text Validation =====================
        # Note that multiline text devices don't require the same validation as
        # the graphical chart types require.
        if typeId == 'multiLineText':

            if not valuesDict['thing']:
                error_msg_dict['thing'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Source Error.\n\nYou must select a text source for charting."
                return False, valuesDict, error_msg_dict

            if not valuesDict['thingState']:
                error_msg_dict['thingState'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Text to Chart Error.\n\nYou must select a text source for charting."
                return False, valuesDict, error_msg_dict

            self.logger.debug(u"{0} settings validated.".format(dev.name))
            return True, valuesDict

        # ======================= Bar Chart Validation ========================
        if typeId == 'barChartingDevice':
            if valuesDict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

        # ======================= Line Chart Validation =======================
        if typeId == 'lineChartingDevice':
            if valuesDict['line1Source'] == 'None':
                error_msg_dict['line1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

            for line in range(1, 7, 1):
                for char in valuesDict['line{0}adjuster'.format(line)]:
                    if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                        error_msg_dict['line{0}adjuster'.format(line)] = u"Valid operators are +, -, *, /"
                        error_msg_dict['showAlertText'] = u"Adjuster Error.\n\nValid operators are +, -, *, /."
                        return False, valuesDict, error_msg_dict

                if valuesDict['line{0}Style'.format(line)] == 'steps' and valuesDict['line{0}Fill'.format(line)]:
                    error_msg_dict['line{0}Fill'.format(line)] = u"Fill is not supported for the Steps line type."
                    error_msg_dict['line{0}Style'.format(line)] = u"Fill is not supported for the Steps line type."
                    error_msg_dict['showAlertText'] = u"Settings Conflict.\n\nFill is not supported for the Steps line style. Select a different line style or turn off the fill setting."
                    return False, valuesDict, error_msg_dict

        # ====================== Polar Chart Validation =======================
        if typeId == 'polarChartingDevice':
            if not valuesDict['thetaValue']:
                error_msg_dict['thetaValue'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Direction Source Error.\n\nYou must select a direction source for charting."
                return False, valuesDict, error_msg_dict

            if not valuesDict['radiiValue']:
                error_msg_dict['radiiValue'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Magnitude Source Error.\n\nYou must select a magnitude source for charting."
                return False, valuesDict, error_msg_dict

        # ===================== Scatter Chart Validation ======================
        if typeId == 'scatterChartingDevice':
            if not valuesDict['group1Source']:
                error_msg_dict['group1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

        # ===================== Weather Chart Validation ======================
        if typeId == 'forecastChartingDevice':
            if not valuesDict['forecastSourceDevice']:
                error_msg_dict['forecastSourceDevice'] = u"You must select a weather forecast source device."
                error_msg_dict['showAlertText'] = u"Forecast Device Source Error.\n\nYou must select a weather forecast source device for charting."
                return False, valuesDict, error_msg_dict

        # ========================== All Chart Types ==========================
        # The following validation blocks are applied to all graphical chart
        # device types.

        # ====================== Chart Custom Dimensions ======================
        # Check to see that custom chart dimensions conform to valid types
        for custom_dimension_prop in ['customSizeHeight', 'customSizeWidth', 'customSizePolar']:
            try:
                if custom_dimension_prop in valuesDict.keys() and valuesDict[custom_dimension_prop] != 'None' and float(valuesDict[custom_dimension_prop]) < 75:
                    error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be greater than 75 pixels."
                    error_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is less than 75 pixels."
                    return False, valuesDict, error_msg_dict
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be a real number."
                error_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is not a real number."
                valuesDict[custom_dimension_prop] = 'None'
                return False, valuesDict, error_msg_dict

        # ============================ Axis Limits ============================
        # Check to see that each axis limit matches one of the accepted formats
        for limit_prop in ['yAxisMax', 'yAxisMin', 'y2AxisMax', 'y2AxisMin']:
            try:
                if limit_prop in valuesDict.keys() and valuesDict[limit_prop] not in ['None', '0']:
                    float(valuesDict[limit_prop])
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                error_msg_dict[limit_prop]      = u"An axis limit must be a real number or None."
                error_msg_dict['showAlertText'] = u"Axis limit Error.\n\nA valid axis limit must be in the form of a real number or None."
                valuesDict[limit_prop] = 'None'
                return False, valuesDict, error_msg_dict

        self.logger.debug(u"{0} settings validated.".format(dev.name))
        return True, valuesDict

# Matplotlib Plugin methods ===================================================

    def _dummyCallback(self, valuesDict=None, typeId="", targetId=0):
        """
        Dummy callback method to force dialog refreshes

        The purpose of the _dummyCallback method is to provide something for
        configuration dialogs to call in order to force a refresh of any dynamic
        controls (dynamicReload=True).

        -----

        :param str typeId:
        :param indigo.Dict valuesDict:
        :param int devId:
        """

        pass

    def advancedSettingsExecuted(self, valuesDict, menuId):
        """
        Save advanced settings menu items to plugin props for storage

        The advancedSettingsExecuted() method is a place where advanced settings will
        be controlled. This method takes the returned values and sends them to the
        pluginPrefs for permanent storage. Note that valuesDict here is for the menu,
        not all plugin prefs.

        -----

        :param indigo.Dict valuesDict:
        :param int menuId:
        """

        self.pluginPrefs['enableCustomLineSegments']  = valuesDict['enableCustomLineSegments']
        self.pluginPrefs['promoteCustomLineSegments'] = valuesDict['promoteCustomLineSegments']
        self.pluginPrefs['snappyConfigMenus']         = valuesDict['snappyConfigMenus']
        self.pluginPrefs['forceOriginLines']          = valuesDict['forceOriginLines']

        self.logger.debug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        return True

    def advancedSettingsMenu(self, valuesDict, typeId="", devId=None):
        """
        Write advanced settings menu selections to the log

        The advancedSettingsMenu() method is called when actions are taken within the
        Advanced Settings Menu item from the plugin menu.

        -----

        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int devId:
        """

        self.logger.threaddebug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        return

    def checkVersionNow(self):
        """
        Initiate plugin version update checker

        The checkVersionNow() method will call the Indigo Plugin Update Checker based
        on a user request.

        -----

        """

        self.updater.checkVersionNow()

    def commsKillAll(self):
        """
        Deactivate communication with all plugin devices

        commsKillAll() sets the enabled status of all plugin devices to false.

        -----

        """

        for dev in indigo.devices.itervalues("self"):
            try:
                indigo.device.enable(dev, value=False)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Exception when trying to kill all comms. Error: {0}".format(sub_error))

    def commsUnkillAll(self):
        """
        Establish communication for all disabled plugin devices

        commsUnkillAll() sets the enabled status of all plugin devices to true.

        -----

        """

        for dev in indigo.devices.itervalues("self"):
            try:
                indigo.device.enable(dev, value=True)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Exception when trying to kill all comms. Error: {0}".format(sub_error))

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
            for pref in self.pluginPrefs:
                if 'color' in pref.lower():
                    if self.pluginPrefs[pref] in['#custom', 'custom']:
                        self.logger.info(u"Adjusting existing color preferences to new color picker.")
                        if self.pluginPrefs['{0}Other'.format(pref)]:
                            self.pluginPrefs[pref] = self.pluginPrefs['{0}Other'.format(pref)]
                        else:
                            self.pluginPrefs[pref] = 'FF FF FF'

    def csv_item_add(self, valuesDict, typeId="", devId=None):
        """
        Add new item to CSV engine

        The csv_item_add() method is called when the user clicks on the 'Add Item'
        button in the CSV Engine config dialog.

        -----

        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int devId:
        """

        self.logger.debug(u"{0:*^40}".format(' CSV Device Add Item List Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        error_msg_dict = indigo.Dict()

        try:
            column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict
            lister = [0]
            num_lister = []

            # Add data item validation.  Will not allow add until all three conditions are met.
            if valuesDict['addValue'] == "":
                error_msg_dict['addValue'] = u"Please enter a title value for your CSV data element."
                error_msg_dict['showAlertText'] = u"Title Error.\n\nA title is required for each CSV data element."
                return valuesDict, error_msg_dict

            if valuesDict['addSource'] == "":
                error_msg_dict['addSource'] = u"Please select a device or variable as a source for your CSV data element."
                error_msg_dict['showAlertText'] = u"ID Error.\n\nA source is required for each CSV data element."
                return valuesDict, error_msg_dict

            if valuesDict['addState'] == "":
                error_msg_dict['addState'] = u"Please select a value source for your CSV data element."
                error_msg_dict['showAlertText'] = u"Data Error.\n\nA data value is required for each CSV data element."
                return valuesDict, error_msg_dict

            [lister.append(key.lstrip('k')) for key in sorted(column_dict.keys())]  # Create a list of existing keys with the 'k' lopped off
            [num_lister.append(int(item)) for item in lister]  # Change each value to an integer for evaluation
            next_key = u'k{0}'.format(int(max(num_lister)) + 1)  # Generate the next key
            column_dict[next_key] = (valuesDict['addValue'], valuesDict['addSource'], valuesDict['addState'])  # Save the tuple of properties

            # Remove any empty entries as they're not going to do any good anyway.
            new_dict = {}

            for k, v in column_dict.iteritems():
                if v != (u"", u"", u"") and v != ('None', 'None', 'None'):
                    new_dict[k] = v
                else:
                    self.logger.info(u"Pruning CSV Engine.")

            valuesDict['columnDict'] = str(new_dict)  # Convert column_dict back to a string and prepare it for storage.

        except AttributeError, sub_error:
            self.logger.warning(u"Error adding item. {0}".format(sub_error))

        # NEW =================================================================
        # If the appropriate CSV file doesn't exist, create it and write the header line.

        file_name = valuesDict['addValue']
        full_path = "{0}{1}.csv".format(self.pluginPrefs['dataPath'], valuesDict['addValue'].encode("utf-8"))

        if not os.path.isfile(full_path):

            with open(full_path, 'w') as outfile:
                outfile.write(u"{0},{1}\n".format('Timestamp', file_name))
        # NEW =================================================================

        # Wipe the field values clean for the next element to be added.
        for key in ['addValue', 'addSource', 'addState']:
            valuesDict[key] = u""

        return valuesDict, error_msg_dict

    def csv_item_delete(self, valuesDict, typeId="", devId=None):
        """
        Deletes items from the CSV Engine configuration dialog

        The csv_item_delete() method is called when the user clicks on the "Delete
        Item" button in the CSV Engine config dialog.

        -----

        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int devId:
        """

        self.logger.debug(u"{0:*^40}".format(' CSV Device Delete Item List Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            valuesDict["editKey"] = valuesDict["csv_item_list"]
            del column_dict[valuesDict['editKey']]
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error deleting column. {0}".format(sub_error))

        valuesDict['csv_item_list'] = ""
        valuesDict['editKey']     = ""
        valuesDict['editSource']  = ""
        valuesDict['editState']   = ""
        valuesDict['editValue']   = ""
        valuesDict['previousKey'] = ""
        valuesDict['columnDict']  = str(column_dict)  # Convert column_dict back to a string for storage.

        return valuesDict

    def csv_item_list(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Construct the list of CSV items

        The csv_item_list() method generates the list of Item Key : Item Value
        pairs that will be presented in the CVS Engine device config dialog. It's
        called at open and routinely as changes are made in the dialog.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        self.logger.debug(u"{0:*^40}".format(' CSV Device Item List Generated '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        try:
            valuesDict['columnDict'] = valuesDict.get('columnDict', '{}')  # Returning an empty dict seems to work and may solve the 'None' issue
            column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.
            prop_list   = [(key, "{0}".format(value[0].encode("utf-8"))) for key, value in column_dict.items()]

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error generating item list. {0}".format(sub_error))
            prop_list = []

        return sorted(prop_list, key=lambda tup: tup[1])  # Return a list sorted by the value and not the key.

    def csv_item_update(self, valuesDict, typeId="", devId=None):
        """
        Updates items from the CSV Engine configuration dialog

        When the user selects the 'Update Item' button, update the dict of CSV engine
        items.

        -----

        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int devId:
        """

        self.logger.debug(u"{0:*^40}".format(' Update Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        error_msg_dict = indigo.Dict()
        column_dict  = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            key = valuesDict['editKey']
            previous_key = valuesDict['previousKey']
            if key != previous_key:
                if key in column_dict:
                    error_msg_dict['editKey'] = u"New key ({0}) already exists in the global properties, please use a different key value".format(key)
                    valuesDict['editKey']   = previous_key
                else:
                    del column_dict[previous_key]
            else:
                column_dict[key]          = (valuesDict['editValue'], valuesDict['editSource'], valuesDict['editState'])
                valuesDict['csv_item_list'] = ""
                valuesDict['editKey']     = ""
                valuesDict['editSource']  = ""
                valuesDict['editState']   = ""
                valuesDict['editValue']   = ""

            if not len(error_msg_dict):
                valuesDict['previousKey'] = key

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Something went wrong: {0}".format(sub_error))

        # Remove any empty entries as they're not going to do any good anyway.
        new_dict = {}

        for k, v in column_dict.iteritems():
            if v != ('', '', ''):
                new_dict[k] = v
        column_dict = new_dict

        valuesDict['columnDict'] = str(column_dict)  # Convert column_dict back to a string for storage.

        return valuesDict, error_msg_dict

    def csv_item_select(self, valuesDict, typeId="", devId=None):
        """
        Populates CSV engine controls for updates and deletions

        The csv_item_select() method is called when the user actually selects something
        within the CSV engine Item List dropdown menu. When the user selects an item
        from the Item List, we populate the Title, ID, and Data controls with the
        relevant Item properties.

        -----

        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int devId:
        """

        self.logger.debug(u"{0:*^40}".format(' Select Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        try:
            column_dict                    = literal_eval(valuesDict['columnDict'])
            valuesDict['editKey']          = valuesDict['csv_item_list']
            valuesDict['editSource']       = column_dict[valuesDict['csv_item_list']][1]
            valuesDict['editState']        = column_dict[valuesDict['csv_item_list']][2]
            valuesDict['editValue']        = column_dict[valuesDict['csv_item_list']][0]
            valuesDict['isColumnSelected'] = True
            valuesDict['previousKey']      = valuesDict['csv_item_list']
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"There was an error establishing a connection with the item you chose. {0}".format(sub_error))
        return valuesDict

    def csv_refresh(self):
        """
        Refreshes data for all CSV custom devices

        The csv_refresh() method manages CSV files through CSV Engine custom devices.

        -----

        """

        for dev in indigo.devices.itervalues("self"):

            if dev.deviceTypeId == 'csvEngine' and dev.enabled:

                diff = dt.datetime.now() - dt.datetime.strptime(dev.states['csvLastUpdated'], "%Y-%m-%d %H:%M:%S.%f")
                refresh_needed = diff > dt.timedelta(seconds=int(dev.pluginProps['refreshInterval']))

                if refresh_needed:

                    dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                    csv_dict_str = dev.pluginProps['columnDict']   # {key: (Item Name, Source ID, Source State)}
                    csv_dict     = literal_eval(csv_dict_str)  # Convert column_dict from a string to a literal dict.

                    # Read through the dict and construct headers and data
                    for k, v in sorted(csv_dict.items()):

                        # Create a path variable that is based on the target folder and the CSV item name.
                        full_path = "{0}{1}.csv".format(self.pluginPrefs['dataPath'], v[0].encode("utf-8"))

                        # If the appropriate CSV file doesn't exist, create it and write the header line.
                        if not os.path.isfile(full_path):
                            csv_file = open(full_path, 'w')
                            csv_file.write('{0},{1}\n'.format('Timestamp', v[0].encode("utf-8")))
                            csv_file.close()

                        # Determine the length of the CSV file and truncate if needed.
                        backup = "{0}{1} copy.csv".format(self.pluginPrefs['dataPath'], v[0].encode("utf-8"))
                        target_lines = int(dev.pluginProps['numLinesToKeep']) - 1

                        # Make a backup of the CSV file in case something goes wrong.
                        try:
                            import shutil
                            shutil.copyfile(full_path, backup)
                        except ImportError as sub_error:
                            self.pluginErrorHandler(traceback.format_exc())
                            self.logger.warning(u"The CSV Engine facility requires the shutil module. {0}".format(sub_error))
                        except Exception as sub_error:
                            self.pluginErrorHandler(traceback.format_exc())
                            self.logger.critical(u"Unable to backup CSV file. {0}".format(sub_error))

                        # Open the original file in read-only mode and count the number of lines.
                        with open(full_path, 'r') as orig_file:
                            lines = orig_file.readlines()
                            orig_num_lines = sum(1 for _ in lines)

                        # Write the file (retaining the header line and the last target_lines).
                        if orig_num_lines > target_lines:
                            with open(full_path, 'w') as new_file:
                                new_file.writelines(lines[0:1])
                                new_file.writelines(lines[(orig_num_lines - target_lines): orig_num_lines])

                        # If all has gone well, delete the backup.
                        try:
                            os.remove(backup)
                        except Exception as sub_error:
                            self.pluginErrorHandler(traceback.format_exc())
                            self.logger.warning(u"Unable to delete backup file. {0}".format(sub_error))

                        # Determine if the thing to be written is a device or variable.
                        try:
                            if not v[1]:
                                self.logger.warning(u"Found CSV Data element with missing source ID. Please check to ensure all CSV sources are properly configured.")
                            elif int(v[1]) in indigo.devices:
                                state_to_write = u"{0}".format(indigo.devices[int(v[1])].states[v[2]])
                            elif int(v[1]) in indigo.variables:
                                state_to_write = u"{0}".format(indigo.variables[int(v[1])].value)
                            else:
                                state_to_write = u""
                                self.logger.critical(u"The settings for CSV Engine data element '{0}' are not valid: [dev: {1}, state/value: {2}]".format(v[0], v[1], v[2]))

                            # Give matplotlib something it can chew on if the value to be saved is 'None'
                            if state_to_write in ['None', None]:
                                state_to_write = 'NaN'

                            # Write the latest value to the file.
                            timestamp = u"{0}".format(indigo.server.getTime().strftime('%Y-%m-%d %H:%M:%S.%f'))
                            csv_file = open(full_path, 'a')
                            csv_file.write("{0},{1}\n".format(timestamp, state_to_write))
                            csv_file.close()

                        except ValueError as sub_error:
                            self.pluginErrorHandler(traceback.format_exc())
                            self.logger.warning(u"Invalid Indigo ID. {0}".format(sub_error))
                        except Exception as sub_error:
                            self.pluginErrorHandler(traceback.format_exc())
                            self.logger.warning(u"Invalid CSV definition. {0}".format(sub_error))

                    dev.updateStatesOnServer([{'key': 'csvLastUpdated', 'value': u"{0}".format(dt.datetime.now())},
                                              {'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])
                    self.logger.info(u"[{0}] updated successfully.".format(dev.name))
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

            else:
                pass

    def csv_source(self, typeId, valuesDict, devId, targetId):
        """
        Construct a list of devices and variables for the CSV engine

        Constructs a list of devices and variables for the user to select within the
        CSV engine configuration dialog box. Devices and variables are listed in
        alphabetical order with devices first and then variables. Devices are prepended
        with '(D)' and variables with '(V)'. Category labels are also included for
        visual clarity.

        -----

        :param str typeId:
        :param indigo.Dict valuesDict:
        :param int devId:
        :param int targetId:
        """

        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        list_ = list()

        [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
        [list_.append((dev.id, u"(D) {0}".format(dev.name))) for dev in indigo.devices.iter()]

        [list_.append(t) for t in [(u"-3", u"%%separator%%"), (u"-4", u"%%disabled:Variables%%"), (u"-5", u"%%separator%%")]]
        [list_.append((var.id, u"(V) {0}".format(var.name))) for var in indigo.variables.iter()]

        return list_

    def deviceStateValueList(self, typeId, valuesDict, devId, targetId):
        """
        Formulates list of device states for CSV engine

        Once a user selects a device or variable within the CSV engine configuration
        dialog, we need to obtain the relevant device states to chose from. If the
        user selects a variable, we simply return the variable value identifier. The
        return is a list of tuples of the form:

        -----

        :param str typeId:
        :param indigo.Dict valuesDict:
        :param int devId:
        :param int targetId:
        """

        if valuesDict['addSource'] != u'':
            try:
                if int(valuesDict['addSource']) in indigo.devices:
                    dev = indigo.devices[int(valuesDict['addSource'])]
                    return [x for x in dev.states.keys() if ".ui" not in x]
                elif int(valuesDict['addSource']) in indigo.variables:
                    return [('value', 'value')]
                else:
                    return [('None', 'Enter a Valid ID Number')]
            except ValueError:
                return [('None', 'Enter a Valid ID Number')]

        if valuesDict['editSource'] != u'':
            try:
                if int(valuesDict['editSource']) in indigo.devices:
                    dev = indigo.devices[int(valuesDict['editSource'])]
                    return [x for x in dev.states.keys() if ".ui" not in x]
                elif int(valuesDict['editSource']) in indigo.variables:
                    return [('value', 'value')]
                else:
                    return [('None', 'Enter a Valid ID Number')]
            except ValueError:
                return [('None', 'Enter a Valid ID Number')]
        else:
            return [('None', 'Please select a source ID first')]

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

        markers     = ['line1Marker', 'line2Marker', 'line3Marker', 'line4Marker', 'line5Marker', 'line6Marker', 'group1Marker', 'group2Marker', 'group3Marker', 'group4Marker']
        marker_dict = {"PIX": ",", "TL": "<", "TR": ">"}

        for marker in markers:
            try:
                if p_dict[marker] in marker_dict.keys():
                    p_dict[marker] = marker_dict[p_dict[marker]]
            except KeyError:
                pass

        return p_dict

    def generatorDeviceStates(self, filter="", valuesDict=None, typeId="", targetId=0):
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

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        try:
            dev_id = valuesDict['thing']
            return self.Fogbert.generatorStateOrValue(dev_id)
        except KeyError:
            return [("Select a Source Above", "Select a Source Above")]

    def generatorDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of Indigo variables.

        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::

            [(dev.id, dev.name), (dev.id, dev.name)].

        The list is generated within the DLFramework module.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        return self.Fogbert.deviceList()

    def generatorDeviceAndVariableList(self, filter="", valuesDict=None, typeId="", targetId=0):
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

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        return self.Fogbert.deviceAndVariableList()

    def generatorVariableList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of Indigo variables.

        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::

            [(var.id, var.name), (var.id, var.name)].

        The list is generated within the DLFramework module.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        return self.Fogbert.variableList()

    def getAxisList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of axis formats.

        Returns a list of Python date formatting strings for use in plotting date
        labels.  The list does not include all Python format specifiers.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
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
                          ("%y", "16"),
                          ("%Y", "2016")]

        return axis_list_menu

    def getBatteryDeviceList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Create a list of battery-powered devices

        Creates a list of tuples that contains the device ID and device name of all
        Indigo devices that report a batterLevel device property that is not None.
        If no devices meet the criteria, a single tuple is returned as a place-
        holder.

        -----
        :param Indigo filter filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        batt_list = [(dev.id, dev.name) for dev in indigo.devices.iter() if dev.batteryLevel is not None]

        if len(batt_list) == 0:
            batt_list = [(-1, 'No battery devices detected.'), ]

        return batt_list

    def getBinList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of bins for the X axis.

        Returns a list of bins for the X axis. We assume time, so only time-based bins
        are provided. The list is constrained.
        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
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

    def getFileList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Get list of CSV files for various dropdown menus.

        Generates a list of CSV source files that are located in the folder specified
        within the plugin configuration dialog. If the method is unable to find any CSV
        files, an empty list is returned.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        file_name_list_menu = []
        source_path = self.pluginPrefs.get('dataPath', '{0}/com.fogbert.indigoplugin.matplotlib/'.format(indigo.server.getLogsFolderPath()))

        try:
            import glob
            import os

            for file_name in glob.glob(u"{0}{1}".format(source_path, '*.csv')):
                final_filename = os.path.basename(file_name)
                file_name_list_menu.append((final_filename, final_filename[:-4]))
            file_name_list_menu.append('None')

        except IOError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"Error generating file list: {0}".format(sub_error))

        if self.verboseLogging:
            self.logger.threaddebug(u"File name list menu: {0}".format(file_name_list_menu))

        # return sorted(file_name_list_menu)
        return sorted(file_name_list_menu, key=lambda s: s[0].lower())  # Case insensitive sort

    def getFontList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Provide a list of font names for various dropdown menus.

        Note that these are the fonts that Matplotlib can see, not necessarily all of
        the fonts installed on the system. If matplotlib can't find any fonts, then a
        default list of fonts that matplotlib supports natively are provided.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
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
            self.logger.warning(u"Error building font list.  Returning generic list. {0}".format(sub_error))

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

    def getFontSizeList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of font sizes.

        Provides a list of font size values for various dropdown menus. The list is
        constrained to values that are reasonably attractive (6pt - 20pt).

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        return [(str(_), str(_)) for _ in np.arange(6, 21)]

    def getForecastSource(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Return a list of WUnderground devices for forecast chart devices

        Generates and returns a list of potential forecast devices for the forecast
        devices type. Presently, the plugin only works with WUnderground devices, but
        the intention is to expand the list of compatible devices going forward.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
        """

        self.logger.debug(u"{0:*^40}".format(' Get Forecast Source '))

        forecast_source_menu = []

        try:
            for dev in indigo.devices.itervalues("com.fogbert.indigoplugin.wunderground"):
                if dev.deviceTypeId in ['wundergroundTenDay', 'wundergroundHourly']:
                    forecast_source_menu.append((dev.id, dev.name))
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error getting list of forecast devices. {0}".format(sub_error))

        self.logger.threaddebug(u"Forecast device list generated successfully: {0}".format(forecast_source_menu))
        self.logger.threaddebug(u"forecast_source_menu: {0}".format(forecast_source_menu))

        return forecast_source_menu

    def getLineList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of line styles.

        Provide a list of matplotlib line styles for various dropdown menus. This is
        not an exhaustive list of styles that the current version of matplotlib
        supports; rather, a subset that are known to work with earlier versions that
        ship with OS X.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
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

    def getMarkerList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """
        Returns a list of marker styles.

        Provide a list of matplotlib marker styles for various dropdown menus. This is
        not an exhaustive list of styles that the current version of matplotlib
        supports; rather, a subset that are known to work with earlier versions that
        ship with OS X.

        -----

        :param str filter:
        :param indigo.Dict valuesDict:
        :param str typeId:
        :param int targetId:
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

    def plotActionTest(self, pluginAction, dev, callerWaitingForResult):
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

        :param indigo.pluginAction pluginAction:
        :param indigo.Device dev:
        :param bool callerWaitingForResult:
        """

        try:
            plt.plot(pluginAction.props['x_values'], pluginAction.props['y_values'], **pluginAction.props['kwargs'])
            plt.savefig(u"{0}{1}".format(pluginAction.props['path'], pluginAction.props['filename']))
            plt.close('all')

        except Exception as err:
            if callerWaitingForResult:
                self.logger.critical(u"Error: {0}".format(err))
                return {'success': False, 'message': u"{0}".format(err)}

        if callerWaitingForResult:
            return {'success': True, 'message': u"Success"}

    def pluginEnvironmentLogger(self):
        """
        Log information about the plugin resource environment.

        Write select information about the environment that the plugin is running in.
        This method is only called once, when the plugin is first loaded (or reloaded).

        -----

        """

        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Matplotlib Environment "))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib version:", plt.matplotlib.__version__))
        self.logger.info(u"{0:<31} {1}".format("Numpy version:", np.__version__))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin version:", self.pluginVersion))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib RC Path:", plt.matplotlib.matplotlib_fname()))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin log location:", indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')))
        if self.verboseLogging:
            self.logger.debug(u"{0:<31} {1}".format("Matplotlib base rcParams:", dict(rcParams)))  # rcParams is a dict containing all of the initial matplotlibrc settings
        self.logger.info(u"{0:=^130}".format(""))

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
        self.logger.threaddebug(u"{0:!^80}".format(" TRACEBACK "))
        for line in sub_error:
            self.logger.threaddebug(u"!!! {0}".format(line))
        self.logger.threaddebug(u"!" * 80)

    def processLogQueue(self, dev, return_queue):
        """
        Process output of multiprocessing queue messages

        The processLogQueue() method accepts a multiprocessing queue that contains log
        messages. The method parses those messages across the various self.logger.x
        calls.

        -----

        :param indigo.Device dev:
        :param multiprocessing.queues.Queue return_queue:
        """

        # ======================= Process Output Queue ========================
        if dev.deviceTypeId != 'rcParamsDevice':
            result = return_queue.get()

            for event in result['Log']:
                for thing in result['Log'][event]:
                    if event == 'Threaddebug':
                        self.logger.threaddebug(thing)
                    elif event == 'Debug':
                        self.logger.debug(thing)
                    elif event == 'Info':
                        self.logger.info(thing)
                    elif event == 'Warning':
                        self.logger.warning(thing)
                    else:
                        self.logger.critical(thing)

            if result['Error']:
                self.logger.critical(u"[{0}] {1}".format(dev.name, result['Message']))
            else:
                self.logger.info(u"[{0}] {1}".format(dev.name, result['Message']))

    def rcParamsDeviceUpdate(self, dev):
        """
        Update rcParams device with updated state values

        Push the rcParams settings to the rcParams Device. The state names have already
        been created by getDeviceStateList() which will ensure that future rcParams
        will be picked up if they're ever added to the file.

        -----

        :param indigo.Device dev:
        """

        state_list = []
        for key, value in rcParams.iteritems():
            key = key.replace('.', '_')
            state_list.append({'key': key, 'value': str(value)})
            dev.updateStatesOnServer(state_list)

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])

    def refreshAChartAction(self, pluginAction):
        """
        Refreshes an individual plugin chart device.

        Process Indigo Action item call for a chart refresh. Passes the id of the
        device called from the action. This method is a handler to pass along the
        action call. The action will refresh only the specified chart.

        -----

        :param indigo.pluginAction pluginAction:
        """

        self.logger.info(u"{0:=^80}".format(' Refresh Single Chart Action '))
        self.refreshTheCharts(pluginAction.deviceId)

    def refreshTheCharts(self, chart_id=None):
        """
        Refreshes all the plugin chart devices.

        Iterate through each chart device and refresh the image. Only enabled chart
        devices will be refreshed.

        -----

        :param int chart_id: the dev.id for the chart to be refreshed.
        """

        self.verboseLogging = self.pluginPrefs.get('verboseLogging', False)
        return_queue = multiprocessing.Queue()

        k_dict  = {}  # A dict of kwarg dicts
        p_dict  = dict(self.pluginPrefs)  # A dict of plugin preferences (we set defaults and override with pluginPrefs).

        if self.verboseLogging:
            self.logger.threaddebug(u"{0:<19}{1}".format("Starting rcParams: ", dict(plt.rcParams)))
            self.logger.threaddebug(u"{0:<19}{1}".format("Starting p_dict: ", p_dict))

        try:
            p_dict['font_style']  = 'normal'
            p_dict['font_weight'] = 'normal'
            p_dict['tick_bottom'] = 'on'
            p_dict['tick_left']   = 'on'
            p_dict['tick_right']  = 'off'
            p_dict['tick_top']    = 'off'

            # ======================== rcParams overrides =========================
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

            # ========================= Background color ==========================
            if not self.pluginPrefs.get('backgroundColorOther', 'false'):
                p_dict['transparent_charts'] = False
                p_dict['backgroundColor']    = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            elif self.pluginPrefs.get('backgroundColorOther', 'false') == 'false':
                p_dict['transparent_charts'] = False
                p_dict['backgroundColor']    = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
            else:
                p_dict['transparent_charts'] = True
                p_dict['backgroundColor'] = '#000000'

            # ========================== Plot Area color ==========================
            if not self.pluginPrefs.get('faceColorOther', 'false'):
                p_dict['transparent_filled'] = True
                p_dict['faceColor']          = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
            elif self.pluginPrefs.get('faceColorOther', 'false') == 'false':
                p_dict['transparent_filled'] = True
                p_dict['faceColor']          = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
            else:
                p_dict['transparent_filled'] = False
                p_dict['faceColor'] = '#000000'

            if self.verboseLogging:
                self.logger.threaddebug(u"{0:<19}{1}".format("Updated rcParams:  ", dict(plt.rcParams)))
                self.logger.threaddebug(u"{0:<19}{1}".format("Updated p_dict: ", p_dict))

            # A specific chart id may be passed to the method. In that case, refresh only
            # that chart. Otherwise, chart_id is None and we refresh all of the charts.
            if not chart_id:

                devices_to_refresh = []
                for dev in indigo.devices.itervalues('self'):

                    if dev.deviceTypeId != 'csvEngine' and dev.enabled:

                        diff = dt.datetime.now() - dt.datetime.strptime(dev.states['chartLastUpdated'], "%Y-%m-%d %H:%M:%S.%f")
                        refresh_needed = diff > dt.timedelta(seconds=int(dev.pluginProps['refreshInterval']))

                        if refresh_needed:
                            devices_to_refresh.append(dev)

            else:

                devices_to_refresh = [indigo.devices[int(chart_id)]]

            for dev in devices_to_refresh:

                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                # ===================== Custom Font Sizes =====================
                # Custom font sizes for retina/non-retina adjustments.
                try:
                    if dev.pluginProps['customSizeFont']:
                        p_dict['mainFontSize'] = int(dev.pluginProps['customTitleFontSize'])
                        plt.rcParams['xtick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                        plt.rcParams['ytick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                except KeyError:
                    # Not all devices may support this feature.
                    pass

                # ========================== kwargs ===========================
                # Note: PyCharm wants attribute values to be strings. This is not always what
                # Matplotlib wants (i.e., bbox alpha and linewidth should be floats.)
                k_dict['k_annotation']   = {'bbox': dict(boxstyle='round,pad=0.3', facecolor=p_dict['faceColor'], edgecolor=p_dict['spineColor'], alpha=0.75, linewidth=0.5),
                                            'color': p_dict['fontColorAnnotation'], 'size': plt.rcParams['xtick.labelsize'], 'horizontalalignment': 'center', 'textcoords': 'offset points',
                                            'verticalalignment': 'center'}
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
                    k_dict['k_plot_fig'] = {'bbox_extra_artists': None, 'bbox_inches': None, 'edgecolor': p_dict['backgroundColor'], 'facecolor': p_dict['backgroundColor'], 'format': None,
                                            'frameon': None, 'orientation': None, 'pad_inches': None, 'papertype': None, 'transparent': p_dict['transparent_charts']}

                # ================== matplotlib.rc overrides ==================
                plt.rc('font', **k_dict['k_base_font'])

                p_dict.update(dev.pluginProps)

                for _ in ['bar_colors', 'customTicksLabelY', 'customTicksY', 'data_array', 'dates_to_plot', 'headers', 'wind_direction', 'wind_speed',
                          'x_obs1', 'x_obs2', 'x_obs3', 'x_obs4', 'x_obs5', 'x_obs6',
                          'y_obs1', 'y_obs1_max', 'y_obs1_min',
                          'y_obs2', 'y_obs2_max', 'y_obs2_min',
                          'y_obs3', 'y_obs3_max', 'y_obs3_min',
                          'y_obs4', 'y_obs4_max', 'y_obs4_min',
                          'y_obs5', 'y_obs5_max', 'y_obs5_min',
                          'y_obs6', 'y_obs6_max', 'y_obs6_min']:
                    p_dict[_] = []

                p_dict['fileName']  = ''
                p_dict['headers_1'] = ()  # Tuple
                p_dict['headers_2'] = ()  # Tuple

                try:
                    kv_list = list()  # A list of state/value pairs used to feed updateStatesOnServer()
                    kv_list.append({'key': 'onOffState', 'value': True, 'uiValue': 'Updated'})
                    p_dict.update(dev.pluginProps)

                    # ============= Limit number of observations ==============
                    try:
                        p_dict['numObs'] = int(p_dict['numObs'])
                    except KeyError:
                        # Only some devices will have their own numObs.
                        pass
                    except ValueError:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.warning(u"The number of observations must be a positive number.")

                    # ================== Custom Square Size ===================
                    try:
                        if p_dict['customSizePolar'] == 'None':
                            pass
                        else:
                            p_dict['sqChartSize'] = float(p_dict['customSizePolar'])
                    except KeyError:
                        pass
                    except ValueError:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.warning(u"Custom size must be a positive number or None.")

                    # =================== Extra Wide Chart ====================
                    try:
                        if p_dict['rectWide']:
                            p_dict['chart_height'] = float(p_dict['rectChartWideHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWideWidth'])
                        else:
                            p_dict['chart_height'] = float(p_dict['rectChartHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWidth'])
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                    # ====================== Custom Size ======================
                    # If the user has specified a custom size, let's override
                    # with their custom setting.
                    try:
                        if p_dict['customSizeHeight'] != 'None':
                            p_dict['chart_height'] = float(p_dict['customSizeHeight'])
                        if p_dict['customSizeWidth'] != 'None':
                            p_dict['chart_width'] = float(p_dict['customSizeWidth'])
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                    # ==================== Best Fit Lines =====================
                    # Set the defaults for best fit lines in p_dict.
                    for _ in range(1, 7, 1):
                        p_dict['line{0}BestFitColor'.format(_)] = dev.pluginProps.get('line{0}BestFitColor'.format(_), 'FF 00 00')

                    # ==================== Phantom Labels =====================
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
                        self.pluginErrorHandler(traceback.format_exc())

                    try:
                        if p_dict['customAxisLabelY'].isspace() or p_dict['customAxisLabelY'] == '':
                            p_dict['customAxisLabelY'] = 'null'
                            k_dict['k_y_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                                          'weight': p_dict['font_weight'], 'visible': True}
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                    try:
                        if 'customAxisLabelY2' in p_dict.keys():  # Not all devices that get to this point will support Y2.
                            if p_dict['customAxisLabelY2'].isspace() or p_dict['customAxisLabelY2'] == '':
                                p_dict['customAxisLabelY2'] = 'null'
                                k_dict['k_y2_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']),
                                                               'fontstyle': p_dict['font_style'], 'weight': p_dict['font_weight'], 'visible': True}
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())
                        pass

                    # ====================== Annotations ======================
                    # If the user wants annotations, we need to hide the line
                    # markers as we don't want to plot one on top of the other.
                    for line in range(1, 7, 1):
                        try:
                            if p_dict['line{0}Annotate'.format(line)] and p_dict['line{0}Marker'.format(line)] != 'None':
                                p_dict['line{0}Marker'.format(line)] = 'None'
                                self.logger.warning(u"{0}: Line {1} marker is suppressed to display annotations. "
                                                    u"To see the marker, disable annotations for this line.".format(dev.name, line))
                        except KeyError:
                            self.logger.debug(u"[{0}] No corresponding annotation: 'line{1}Marker'".format(dev.name, line))

                    # ===================== Line Markers ======================
                    # Some line markers need to be adjusted due to their inherent value. For
                    # example, matplotlib uses '<', '>' and '.' as markers but storing these
                    # values will blow up the XML.  So we need to convert them. (See
                    # self.formatMarkers() method.)
                    p_dict = self.formatMarkers(p_dict)

                    if self.verboseLogging:
                        self.logger.debug(u"")
                        self.logger.debug(u"{0:*^80}".format(u" Generating Chart: {0} ".format(dev.name)))

                    # ==================== rcParams Device ====================
                    if dev.deviceTypeId == 'rcParamsDevice':
                        self.rcParamsDeviceUpdate(dev)

                    # For the time being, we're running each device through its
                    # own process synchronously; parallel processing may come later.

                    # ====================== Bar Charts =======================
                    if dev.deviceTypeId == 'barChartingDevice':

                        if __name__ == '__main__':
                            p_bar = multiprocessing.Process(name='p_bar', target=MakeChart(self).chart_bar, args=(dev, p_dict, k_dict, return_queue,))
                            p_bar.start()
                            p_bar.join()

                    # ================= Battery Health Chart ==================
                    if dev.deviceTypeId == 'batteryHealthDevice':

                        device_dict  = {}
                        exclude_list = [int(_) for _ in dev.pluginProps.get('excludedDevices', [])]

                        try:
                            for batt_dev in indigo.devices.itervalues():
                                if batt_dev.batteryLevel is not None and batt_dev.id not in exclude_list:
                                    device_dict[batt_dev.name] = batt_dev.states['batteryLevel']

                            if device_dict == {}:
                                device_dict['No Battery Devices'] = 0

                            # The following line is used for testing the battery health code; it isn't needed in production.
                            # device_dict = {'Device 1': '50', 'Device 2': '77', 'Device 3': '9', 'Device 4': '4', 'Device 5': '92'}

                        except Exception as sub_error:
                            indigo.server.log(u"Error reading battery devices: {0}".format(sub_error))

                        if __name__ == '__main__':
                            p_battery = multiprocessing.Process(name='p_battery', target=MakeChart(self).chart_battery_health, args=(dev, device_dict, p_dict, k_dict, return_queue,))
                            p_battery.start()
                            p_battery.join()

                    # ==================== Calendar Charts ====================
                    if dev.deviceTypeId == "calendarChartingDevice":

                        if __name__ == '__main__':
                            p_calendar = multiprocessing.Process(name='p_calendar', target=MakeChart(self).chart_calendar, args=(dev, p_dict, k_dict, return_queue,))
                            p_calendar.start()
                            p_calendar.join()

                    # ====================== Line Charts ======================
                    if dev.deviceTypeId == "lineChartingDevice":

                        if __name__ == '__main__':
                            p_line = multiprocessing.Process(name='p_line', target=MakeChart(self).chart_line, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_line.start()
                            p_line.join()

                    # ==================== Multiline Text =====================
                    if dev.deviceTypeId == 'multiLineText':

                        # Get the text to plot. We do this here so we don't need to send all the
                        # devices and variables to the method (the process does not have access to the
                        # Indigo server).
                        if int(p_dict['thing']) in indigo.devices:
                            text_to_plot = unicode(indigo.devices[int(p_dict['thing'])].states[p_dict['thingState']])
                            if self.verboseLogging:
                                self.logger.debug(u"Data retrieved successfully: {0}".format(text_to_plot))
                        elif int(p_dict['thing']) in indigo.variables:
                            text_to_plot = unicode(indigo.variables[int(p_dict['thing'])].value)
                            if self.verboseLogging:
                                self.logger.debug(u"Data retrieved successfully: {0}".format(text_to_plot))
                        else:
                            text_to_plot = u"Unable to reconcile plot text. Confirm device settings."
                            self.logger.info(u"Presently, the plugin only supports device state and variable values.")

                        if __name__ == '__main__':
                            p_multiline = multiprocessing.Process(name='p_multiline', target=MakeChart(self).chart__multiline_text, args=(dev, p_dict, k_dict, text_to_plot, return_queue,))
                            p_multiline.start()
                            p_multiline.join()

                    # ===================== Polar Charts ======================
                    if dev.deviceTypeId == "polarChartingDevice":

                        if __name__ == '__main__':
                            p_polar = multiprocessing.Process(name='p_polar', target=MakeChart(self).chart_polar, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_polar.start()
                            p_polar.join()

                    # ==================== Scatter Charts =====================
                    if dev.deviceTypeId == "scatterChartingDevice":

                        if __name__ == '__main__':
                            p_scatter = multiprocessing.Process(name='p_scatter', target=MakeChart(self).chart_scatter, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_scatter.start()
                            p_scatter.join()

                    # ================ Weather Forecast Charts ================
                    if dev.deviceTypeId == "forecastChartingDevice":

                        dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                        state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states
                        sun_rise_set = (str(indigo.server.calculateSunrise()), str(indigo.server.calculateSunset()))

                        if __name__ == '__main__':
                            p_weather = multiprocessing.Process(name='p_weather', target=MakeChart(self).chart_weather_forecast, args=(dev, dev_type, p_dict, k_dict, state_list, sun_rise_set, return_queue,))
                            p_weather.start()
                            p_weather.join()

                    # =============== Process the output queue ================
                    self.processLogQueue(dev, return_queue)

                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})
                    dev.updateStatesOnServer(kv_list)

                except RuntimeError as sub_error:
                    self.logger.critical(u"[{0}] Critical Error: {1}".format(dev.name, sub_error))
                    self.logger.critical(u"Skipping device.")
                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

        except Exception as sub_error:
            self.logger.threaddebug(u"{0}".format(unicode(sub_error)))

    def refreshTheChartsAction(self, action):
        """
        Called by an Indigo Action item.

        Allows the plugin to call the refreshTheCharts() method from an Indigo Action
        item. This action will refresh all charts.

        -----

        :param indigo.PluginAction action:
        """

        self.refreshTheCharts()
        self.logger.info(u"{0:=^80}".format(' Cycle complete. '))

class MakeChart(object):

    def __init__(self, plugin):
        self.final_data = []
        self.host_plugin = plugin

    def _log_dicts(self, p_dict=None, k_dict=None):
        """
        Write parameters dicts to log under verbose logging

        Simple method to write rcParm and kwarg dicts to debug log.

        -----

        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        """

        if self.host_plugin.verboseLogging:
            self.host_plugin.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", p_dict))
            self.host_plugin.logger.threaddebug(u"{0:<19}{1}".format("k_dict: ", k_dict))

    def chart_bar(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the bar charts

        All steps required to generate bar charts.

        -----

        :param indigo.Device dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param indigo.List kv_list: device state values for updating
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            self._log_dicts(p_dict, k_dict)

            num_obs                   = p_dict['numObs']
            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            for _ in range(1, 5, 1):
                p_dict['bar{0}Color'.format(_)] = r"#{0}".format(p_dict['bar{0}Color'.format(_)].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ========================= Format Axes ===========================
            self.format_axis_x_ticks(ax, p_dict, k_dict)
            self.format_axis_y(ax, p_dict, k_dict)

            for thing in range(1, 5, 1):

                # If the bar color is the same as the background color, alert the user.
                if p_dict['bar{0}Color'.format(thing)] == p_dict['backgroundColor']:
                    log['Info'].append(u"[{0}] Bar {0} color is the same as the background color (so you may not be able to see it).".format(dev.name, thing))

                # Plot the bars
                if p_dict['bar{0}Source'.format(thing)] not in ["", "None"]:

                    # Get the data and grab the header.
                    data_column = self.get_data(u'{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"), p_dict['bar{0}Source'.format(thing)]))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(thing)].append(element[0])
                        p_dict['y_obs{0}'.format(thing)].append(float(element[1]))

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(thing)])

                    # Plot the bar.
                    # Note: hatching is not supported in the PNG backend.
                    ax.bar(dates_to_plot[num_obs * -1:], p_dict['y_obs{0}'.format(thing)][num_obs * -1:], align='center', width=float(p_dict['barWidth']),
                           color=p_dict['bar{0}Color'.format(thing)], edgecolor=p_dict['bar{0}Color'.format(thing)], **k_dict['k_bar'])

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)][num_obs * -1:]]

                    # If annotations desired, plot those too.
                    if p_dict['bar{0}Annotate'.format(thing)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(thing)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # ======================== Y1 Axis Min/Max ========================
            self.format_axis_y1_min_max(p_dict)

            # ========================= X Axis Label ==========================
            self.format_axis_x_label(dev, p_dict, k_dict)

            # ========================= Y Axis Label ==========================
            self.format_axis_y1_label(p_dict, k_dict)

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ====================== Legend Properties ========================
            # Legend should be plotted before any other lines are plotted (like
            #  averages or custom line segments).
            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

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

            # ======================== Min/Max Lines ==========================
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

            # ===================== Custom Line Segments ======================
            self.plot_custom_line_segments(ax, p_dict, k_dict)

            # ========================== Format Grids =========================
            self.format_grids(p_dict, k_dict)

            # ========================== Chart Title ==========================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ======================= Custom Y Ticks ==========================
            self.format_axis_y_ticks(p_dict, k_dict)

            # ========================== Save Image ===========================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Error ({1})".format(dev.name, sub_error)})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart_battery_health(self, dev, device_dict, p_dict, k_dict, return_queue):
        """
        Creates the battery health charts

        The chart_battery_health method creates battery health charts. These chart
        types are dynamic and are created "on the fly" rather than through direct
        user input.

        :param dev:
        :param device_dict:
        :param p_dict:
        :param k_dict:
        :param return_queue:
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

                # =================== Calculate Bar Colors ====================
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

            # ======================== Plot the Figure ========================
            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # Adding 1 to the y_axis pushes the bar to spot 1 instead of spot 0 -- getting it off the axis.
            ax.barh((y_values + 1), x_values, color=bar_colors, align='center', linewidth=0, **k_dict['k_bar'])

            # ========================== Data Labels ==========================
            # Plot data labels inside or outside depending on bar length
            if show_level:
                for _ in range(len(y_values)):
                    if x_values[_] >= caution_level:
                        plt.annotate(u"{0:>3}".format(int(x_values[_])), xy=((x_values[_] - 6), (y_values[_]) + 0.88), xycoords='data', textcoords='data', fontsize=font_size, color=font_color, zorder=25)
                    else:
                        plt.annotate(u"{0}".format(int(x_values[_])), xy=((x_values[_] + 1), (y_values[_]) + 0.88), xycoords='data', textcoords='data', fontsize=font_size, color=font_color, zorder=25)

            # ========================== Chart Title ==========================
            # plt.title(p_dict['chartTitle'], location='center', **k_dict['k_title_font'])
            plt.suptitle(p_dict['chartTitle'], **k_dict['k_title_font'])

            # ========================== Format Grids =========================
            if dev.ownerProps.get('showxAxisGrid', False):
                for _ in (20, 40, 60, 80):
                    ax.axvline(x=_, color=p_dict['gridColor'], linestyle=self.host_plugin.pluginPrefs.get('gridStyle', ':'))

            # ========================= X Axis Label ==========================
            self.format_axis_x_label(dev, p_dict, k_dict)
            ax.xaxis.set_ticks_position('bottom')

            # ======================== X Axis Min/Max =========================
            # We want the X axis scale to always be 0-100.
            plt.xlim(xmin=0, xmax=100)

            # ========================= Y Axis Label ==========================
            # Hide major tick labels and right side ticks.
            ax.set_yticklabels('')
            ax.yaxis.set_ticks_position('left')

            # Customize minor tick label position and assign device names to the
            # minor ticks
            ax.set_yticks([n for n in range(1, len(y_values) + 1)], minor=True)
            ax.set_yticklabels(y_text, minor=True)

            # ======================== Y Axis Min/Max =========================
            # We never want the Y axis to go lower than 0.
            plt.ylim(ymin=0)

            # ============================ Spines =============================
            # Hide all but the bottom spine.
            for spine in ('left', 'top', 'right'):
                ax.spines[spine].set_visible(False)

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Output the file
            plt.tight_layout()
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart_calendar(self, dev, p_dict, k_dict, return_queue):
        """
        Creates the calendar charts

        Given the unique nature of calendar charts, we use a separate method to
        construct them.

        -----

        :param indigo.devices() dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param multiprocessing.Queue() return_queue: return queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            self._log_dicts(p_dict, k_dict)

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

            # ========================== Save Image ===========================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.9, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart_line(self, dev, p_dict, k_dict, kv_list, return_queue):
        """
        Creates the line charts

        All steps required to generate line charts.

        -----

        :param indigo.Device dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param indigo.List kv_list: device state values for updating
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            self._log_dicts(p_dict, k_dict)

            for _ in range(1, 7, 1):
                p_dict['line{0}Color'.format(_)]        = r"#{0}".format(p_dict['line{0}Color'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}MarkerColor'.format(_)]  = r"#{0}".format(p_dict['line{0}MarkerColor'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}BestFitColor'.format(_)] = r"#{0}".format(p_dict['line{0}BestFitColor'.format(_)].replace(' ', '').replace('#', ''))

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ========================= Format Axes ===========================
            self.format_axis_x_ticks(ax, p_dict, k_dict)
            self.format_axis_y(ax, p_dict, k_dict)

            for line in range(1, 7, 1):

                # If line color is the same as the background color, alert the user.
                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Warning'].append(u"[{0}] Line {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, line))

                # ====================== Plot the lines =======================
                if p_dict['line{0}Source'.format(line)] not in ["", "None"]:

                    data_column = self.get_data('{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"), p_dict['line{0}Source'.format(line)].encode("utf-8")))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(line)].append(element[0])
                        p_dict['y_obs{0}'.format(line)].append(float(element[1]))

                    # ==================== Adjustment Factor ====================
                    if dev.pluginProps['line{0}adjuster'.format(line)] != "":
                        temp_list = []
                        for obs in p_dict['y_obs{0}'.format(line)]:
                            expr = u'{0}{1}'.format(obs, dev.pluginProps['line{0}adjuster'.format(line)])
                            temp_list.append(self.host_plugin.evalExpr.eval_expr(expr))
                        p_dict['y_obs{0}'.format(line)] = temp_list

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(line)])

                    ax.plot_date(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                                 marker=p_dict['line{0}Marker'.format(line)], markeredgecolor=p_dict['line{0}MarkerColor'.format(line)],
                                 markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=10, **k_dict['k_line'])

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Fill'.format(line)]:
                        ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                    # ====================== Annotations ======================
                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # ======================== Y1 Axis Min/Max ========================
            # Min and Max are not 'None'.
            self.format_axis_y1_min_max(p_dict)

            # Transparent Chart Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Legend
            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

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
                # Note that we do these after the legend is drawn so that these lines don't affect the legend.

                # ===================== Best Fit Line =====================
                if dev.pluginProps.get('line{0}BestFit'.format(line), False):
                    self.plot_best_fit_line_segments(ax, dates_to_plot, line, p_dict)

                [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                # ======================== Min/Max Lines ==========================
                if p_dict['line{0}Fill'.format(line)]:
                    ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                if p_dict['plotLine{0}Min'.format(line)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_min'])
                if p_dict['plotLine{0}Max'.format(line)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_max'])
                if self.host_plugin.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plot_custom_line_segments(ax, p_dict, k_dict)

            self.format_grids(p_dict, k_dict)

            # ========================== Chart Title ==========================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ========================= X Axis Label ==========================
            self.format_axis_x_label(dev, p_dict, k_dict)

            # ========================= Y Axis Label ==========================
            self.format_axis_y1_label(p_dict, k_dict)

            # ======================= Custom Y Ticks ==========================
            self.format_axis_y_ticks(p_dict, k_dict)

            # ========================== Save Image ===========================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart__multiline_text(self, dev, p_dict, k_dict, text_to_plot, return_queue):
        """
        Creates the multiline text charts

        Given the unique nature of multiline text charts, we use a separate method
        to construct them.

        -----

        :param indigo.Device dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param str text_to_plot: the text to be plotted
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            import textwrap

            self._log_dicts(p_dict, k_dict)

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))
            p_dict['textColor']       = r"#{0}".format(p_dict['textColor'].replace(' ', '').replace('#', ''))
            p_dict['figureWidth']     = float(dev.pluginProps['figureWidth'])
            p_dict['figureHeight']    = float(dev.pluginProps['figureHeight'])

            # If the value to be plotted is empty, use the default text from the device configuration.
            if len(text_to_plot) <= 1:
                text_to_plot = unicode(p_dict['defaultText'])
            else:
                # The clean_string method tries to remove some potential ugliness from the text to be plotted. It's optional--defaulted to on. No need to call this if the default text
                # is used.
                if p_dict['cleanTheText']:
                    text_to_plot = self.clean_string(text_to_plot)

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

            # ========================== Chart Title ==========================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ========================== Save Image ===========================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.05, left=0.02, right=0.98, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart_polar(self, dev, p_dict, k_dict, kv_list, return_queue):
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

        :param indigo.Device dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param list kv_list: device state values for updating
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            self._log_dicts(p_dict, k_dict)

            num_obs                    = p_dict['numObs']
            p_dict['backgroundColor']  = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']        = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))
            p_dict['currentWindColor'] = r"#{0}".format(p_dict['currentWindColor'].replace(' ', '').replace('#', ''))
            p_dict['maxWindColor']     = r"#{0}".format(p_dict['maxWindColor'].replace(' ', '').replace('#', ''))

            # ====================== Column Headings ======================
            # Pull the column headings for the labels, then delete the row
            # from self.final_data.
            theta_path = '{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'], p_dict['thetaValue'])  # The name of the theta file.
            radii_path = '{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'], p_dict['radiiValue'])  # The name of the radii file.

            if theta_path != 'None' and radii_path != 'None':

                # Get the data.
                self.final_data.append(self.get_data(theta_path))
                self.final_data.append(self.get_data(radii_path))

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

                # ====================== Customizations =======================
                size = float(p_dict['sqChartSize']) / int(plt.rcParams['savefig.dpi'])
                plt.figure(figsize=(size, size))
                ax = plt.subplot(111, polar=True)                                 # Create subplot
                plt.grid(color=plt.rcParams['grid.color'])                        # Color the grid
                ax.set_theta_zero_location('N')                                   # Set zero to North
                ax.set_theta_direction(-1)                                        # Reverse the rotation
                ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])  # Customize the xtick labels
                ax.spines['polar'].set_visible(False)                             # Show or hide the plot spine
                ax.set_axis_bgcolor(p_dict['faceColor'])                          # Color the background of the plot area.

                # ====================== Create the Plot ======================
                # Note: zorder of the plot must be >2.01 for the plot to be
                # above the grid (the grid defaults to z = 2.)
                for w in wind:
                    ax.plot((0, w[0]), (0, w[1]), color=w[2], linewidth=2, zorder=3)

                # Right-size the grid (must be done after the plot), and customize the tick labels.
                if max(p_dict['wind_speed']) <= 5:
                    ax.yaxis.set_ticks(np.arange(1, 5, 1))
                    ax.set_rgrids([1, 2, 3, 4, 5], **k_dict['k_rgrids'])
                elif 5 < max(p_dict['wind_speed']) <= 10:
                    ax.yaxis.set_ticks(np.arange(2, 10, 2))
                    ax.set_rgrids([2, 4, 6, 8, 10], **k_dict['k_rgrids'])
                elif 10 < max(p_dict['wind_speed']) <= 20:
                    ax.yaxis.set_ticks(np.arange(5, 20, 5))
                    ax.set_rgrids([5, 10, 15, 20, 25], **k_dict['k_rgrids'])
                elif 20 < max(p_dict['wind_speed']) <= 50:
                    ax.yaxis.set_ticks(np.arange(10, 50, 10))
                    ax.set_rgrids([10, 20, 30, 40, 50], **k_dict['k_rgrids'])
                elif 50 < max(p_dict['wind_speed']):
                    plt.text(0.5, 0.5, u"Holy crap!", color='FF FF FF', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes,
                             bbox=dict(facecolor='red', alpha='0.5'))

                # If the user wants to hide tick labels, lets do that.
                if p_dict['xHideLabels']:
                    ax.axes.xaxis.set_ticklabels([])
                if p_dict['yHideLabels']:
                    ax.axes.yaxis.set_ticklabels([])

                # ================== Current Obs / Max Wind ===================
                # Note that we reduce the value of the circle plot so that it
                # appears when transparent charts are enabled (otherwise the
                # circle is obscured. The transform can be done one of two
                # ways: access the private attribute "ax.transData._b", or
                # "ax.transProjectionAffine + ax.transAxes".
                fig = plt.gcf()
                max_wind_circle = plt.Circle((0, 0), (max(p_dict['wind_speed']) * 0.99), transform=ax.transProjectionAffine + ax.transAxes, fill=False, edgecolor=p_dict['maxWindColor'],
                                             linewidth=2, alpha=1, zorder=9)
                fig.gca().add_artist(max_wind_circle)

                last_wind_circle = plt.Circle((0, 0), (p_dict['wind_speed'][-1] * 0.99), transform=ax.transProjectionAffine + ax.transAxes, fill=False,
                                              edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=10)
                fig.gca().add_artist(last_wind_circle)

                # ========================== No Wind ==========================
                # If latest obs is a speed of zero, plot something that we can
                # see.
                if p_dict['wind_speed'][-1] == 0:
                    zero_wind_circle = plt.Circle((0, 0), 0.15, transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['currentWindColor'],
                                                  edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=12)
                    fig.gca().add_artist(zero_wind_circle)

                # ================== Transparent Chart Fill ===================
                if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                    ylim = ax.get_ylim()
                    patch = plt.Circle((0, 0), ylim[1], transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['faceColor'], linewidth=1, alpha=1, zorder=1)
                    fig.gca().add_artist(patch)

                # ===================== Legend Properties =====================
                if self.host_plugin.verboseLogging:
                    log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

                if p_dict['showLegend']:
                    legend = ax.legend(([u"Current", u"Maximum"]), loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                    legend.legendHandles[0].set_color(p_dict['currentWindColor'])
                    legend.legendHandles[1].set_color(p_dict['maxWindColor'])
                    [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                    frame = legend.get_frame()
                    frame.set_alpha(0)

                # ======================= Display Grids =======================
                # Grids are always on for polar wind charts.
                if self.host_plugin.verboseLogging:
                    log['Debug'].append(u"Display grids[X / Y]: always on")

                # ======================== Chart Title ========================
                plt.title(p_dict['chartTitle'], position=(0, 1.0), **k_dict['k_title_font'])

                # ========================== Save Image ===========================
                # plt.tight_layout(pad=1)
                plt.subplots_adjust(top=0.95, bottom=0.15, left=0.15, right=0.85, hspace=None, wspace=None)
                self.save_chart_image(plt, p_dict, k_dict)

                return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(traceback.format_exc()), 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chart_scatter(self, dev, p_dict, k_dict, kv_list, return_queue):
        """
        Creates the scatter charts

        All steps required to generate scatter charts.

        -----

        :param indigo.Device dev: indigo device instance
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param list kv_list: device state values for updating
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            self._log_dicts(p_dict, k_dict)

            # ======================= p_dict Overrides ========================
            for _ in range(1, 5, 1):
                p_dict['group{0}Color'.format(_)]       = r"#{0}".format(p_dict['group{0}Color'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['group{0}MarkerColor'.format(_)] = r"#{0}".format(p_dict['group{0}MarkerColor'.format(_)].replace(' ', '').replace('#', ''))
                p_dict['line{0}BestFitColor'.format(_)] = r"#{0}".format(p_dict['line{0}BestFitColor'.format(_)].replace(' ', '').replace('#', 'FF 00 00'))

            p_dict['backgroundColor'] = r"#{0}".format(p_dict['backgroundColor'].replace(' ', '').replace('#', ''))
            p_dict['faceColor']       = r"#{0}".format(p_dict['faceColor'].replace(' ', '').replace('#', ''))

            ax = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            # ========================= Format Axes ===========================
            self.format_axis_x_ticks(ax, p_dict, k_dict)
            self.format_axis_y(ax, p_dict, k_dict)

            for thing in range(1, 5, 1):

                # If dot color is the same as the background color, alert the user.
                if p_dict['group{0}Color'.format(thing)] == p_dict['backgroundColor']:
                    log['Debug'].append(u"[{0}] Group {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, thing))

                # ====================== Plot the Points ======================
                if p_dict['group{0}Source'.format(thing)] not in ["", "None"]:

                    # There is a bug in matplotlib (fixed in newer versions) where points would not
                    # plot if marker set to 'none'. This overrides the behavior.
                    if p_dict['group{0}Marker'.format(thing)] == u'None':
                        p_dict['group{0}Marker'.format(thing)] = '.'
                        p_dict['group{0}MarkerColor'.format(thing)] = p_dict['group{0}Color'.format(thing)]

                    data_column = self.get_data('{0}{1}'.format(self.host_plugin.pluginPrefs['dataPath'].encode("utf-8"), p_dict['group{0}Source'.format(thing)].encode("utf-8")))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(thing)].append(element[0])
                        p_dict['y_obs{0}'.format(thing)].append(float(element[1]))

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs{0}'.format(thing)])

                    # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
                    ax.scatter(dates_to_plot, p_dict['y_obs{0}'.format(thing)], c=p_dict['group{0}Color'.format(thing)], marker=p_dict['group{0}Marker'.format(thing)],
                               edgecolor=p_dict['group{0}MarkerColor'.format(thing)], linewidths=0.75, zorder=10, **k_dict['k_line'])

                    # ===================== Best Fit Line =====================
                    if dev.pluginProps.get('line{0}BestFit'.format(thing), False):
                        self.plot_best_fit_line_segments(ax, dates_to_plot, thing, p_dict)

                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(thing)]]

            # ======================== Y1 Axis Min/Max ========================
            # Min and Max are not 'None'.
            self.format_axis_y1_min_max(p_dict)

            # ============================ Legend =============================
            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

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

            # ========================== Min / Max ==========================
            for thing in range(1, 5, 1):
                if p_dict['plotGroup{0}Min'.format(thing)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(thing)]), color=p_dict['group{0}Color'.format(thing)], **k_dict['k_min'])
                if p_dict['plotGroup{0}Max'.format(thing)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(thing)]), color=p_dict['group{0}Color'.format(thing)], **k_dict['k_max'])
                if self.host_plugin.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plot_custom_line_segments(ax, p_dict, k_dict)

            self.format_grids(p_dict, k_dict)

            # ======================== Chart Title ========================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ========================= X Axis Label ==========================
            self.format_axis_x_label(dev, p_dict, k_dict)

            # ========================= Y Axis Label ==========================
            self.format_axis_y1_label(p_dict, k_dict)

            # ======================= Custom Y Ticks ==========================
            self.format_axis_y_ticks(p_dict, k_dict)

            # ========================== Save Image ===========================
            # plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.2, left=0.1, right=0.92, hspace=None, wspace=None)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, ValueError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

    def chart_weather_forecast(self, dev, dev_type, p_dict, k_dict, state_list, sun_rise_set, return_queue):
        """
        Creates the weather charts

        Given the unique nature of weather chart construction, we have a separate
        method for these charts. Note that it is not currently possible within the
        multiprocessing framework used to query the indigo server, so we need to
        send everything we need through the method call.

        -----

        :param indigo.Device dev: indigo device instance
        :param str dev_type: device type name
        :param dict p_dict: plotting parameters
        :param dict k_dict: plotting kwargs
        :param list state_list: the data to plot
        :param tuple sun_rise_set: tuple of sunrise/sunset times
        :param multiprocessing.queues.Queue return_queue: logging queue
        """

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:

            self._log_dicts(p_dict, k_dict)

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

            # ========================= Hourly Device =========================
            if dev_type == 'wundergroundHourly':
                pass
                for counter in range(1, 25, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['h{0}_timeLong'.format(counter)])
                    p_dict['y_obs1'].append(state_list['h{0}_temp'.format(counter)])
                    p_dict['y_obs3'].append(state_list['h{0}_precip'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'])

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('Temperature',)  # Note that the trailing comma is required to ensure that Matplotlib interprets the legend as a tuple.
                    p_dict['headers_2']    = ('Precipitation',)
                    p_dict['daytimeColor'] = r"#{0}".format(p_dict['daytimeColor'].replace(' ', '').replace('#', ''))

            # ======================== Ten Day Device =========================
            elif dev_type == 'wundergroundTenDay':
                pass
                for counter in range(1, 11, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['d{0}_date'.format(counter)])
                    p_dict['y_obs1'].append(state_list['d{0}_high'.format(counter)])
                    p_dict['y_obs2'].append(state_list['d{0}_low'.format(counter)])
                    p_dict['y_obs3'].append(state_list['d{0}_pop'.format(counter)])

                    # Convert the date strings for charting.
                    dates_to_plot = self.format_dates(p_dict['x_obs1'])

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1']    = ('High Temperature', 'Low Temperature',)
                    p_dict['headers_2']    = ('Precipitation',)

            else:
                log['Warning'].append(u"This device type only supports WUnderground plugin forecast devices.")

# ============================= AX1 ==============================
            ax1 = self.make_chart_figure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.format_axis_x_ticks(ax1, p_dict, k_dict)
            self.format_axis_y(ax1, p_dict, k_dict)

            # ====================== Precipitation Bars =======================
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

            # ======================== Precip Min/Max =========================
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

            # ========================= X1 Axis Label ==========================
            self.format_axis_x_label(dev, p_dict, k_dict)

            # ========================= Y1 Axis Label ==========================
            # Note we're plotting Y2 label on ax1. We do this because we want the
            # precipitation bars to be under the temperature plot but we want the
            # precipitation scale to be on the right side.
            plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])
            ax1.yaxis.set_label_position('right')

            # ======================= Legend Properties =======================
            # (note that we need a separate instance of this code for each
            # subplot. This one controls the precipitation subplot.)
            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Display legend 1: {0}".format(p_dict['showLegend']))

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_2']]
                legend = ax1.legend(headers, loc='upper right', bbox_to_anchor=(1.0, -0.12), ncol=1, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)  # Note: frame alpha should be an int and not a string.

            self.format_grids(p_dict, k_dict)

            # ==================== Transparent Charts Fill ====================
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax1.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax1.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # ======================= Sunrise / Sunset ========================
            # Note that this highlights daytime.

            daylight = dev.pluginProps.get('showDaytime', True)

            if daylight and dev_type == 'wundergroundHourly':
                sun_rise, sun_set = self.format_dates(sun_rise_set)
                if self.host_plugin.verboseLogging:
                    log['Debug'].append(u"Sunrise > Sunset: {0}".format(sun_rise > sun_set))

                min_dates_to_plot = np.amin(dates_to_plot)
                max_dates_to_plot = np.amax(dates_to_plot)

                # We will only highlight daytime if the current values for sunrise and sunset
                # fall within the limits of dates_to_plot. We add and subtract one second for
                # each to account for microsecond rounding.
                if (min_dates_to_plot - 1) < sun_rise < (max_dates_to_plot + 1) and (min_dates_to_plot - 1) < sun_set < (max_dates_to_plot + 1):

                    if self.host_plugin.verboseLogging:
                        log['Debug'].append(u"Highlighting daytime.")
                    # If sunrise is less than sunset, they are on the same day so we fill in
                    # between the two.
                    if sun_rise < sun_set:
                        ax1.axvspan(sun_rise, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

                    # If sunrise is greater than sunset, the next sunrise is tomorrow
                    else:
                        ax1.axvspan(min_dates_to_plot, sun_set, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)
                        ax1.axvspan(sun_rise, max_dates_to_plot, color=p_dict['daytimeColor'], alpha=0.15, zorder=1)

# ============================= AX2 ==============================

            # ======================= Temperatures Plot =======================
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

            self.format_axis_x_ticks(ax2, p_dict, k_dict)
            self.format_axis_y(ax2, p_dict, k_dict)

            self.plot_custom_line_segments(ax2, p_dict, k_dict)

            plt.autoscale(enable=True, axis='x', tight=None)

            # Note that we plot the bar plot so that it will be under the line plot, but we still want the temperature scale on the left and the percentages on the right.
            ax1.yaxis.tick_right()
            ax2.yaxis.tick_left()

            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Y1 Max: {0}  Y1 Min: {1}  Y1 Diff: {2}".format(max(p_dict['data_array']),
                                                                                     min(p_dict['data_array']),
                                                                                     max(p_dict['data_array']) - min(p_dict['data_array'])))

            # =================== Temperature Axis Min/Max ====================
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

            # ========================= Y2 Axis Label ==========================
            # Note we're plotting Y1 label on ax2. We do this because we want the
            # temperature lines to be over the precipitation bars but we want the
            # temperature scale to be on the left side.
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])  # Note we're plotting Y1 label on ax2
            ax2.yaxis.set_label_position('left')

            # ========================== Chart Title ==========================
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # ======================= Legend Properties =======================
            # (note that we need a separate instance of this code for each
            # subplot. This one controls the temperatures subplot.)
            if self.host_plugin.verboseLogging:
                log['Debug'].append(u"Display legend 2: {0}".format(p_dict['showLegend']))

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_1']]
                legend = ax2.legend(headers, loc='upper left', bbox_to_anchor=(0.0, -0.12), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            self.format_grids(p_dict, k_dict)

            # ========================== Save Image ===========================
            plt.tight_layout(pad=1)
            plt.subplots_adjust(bottom=0.2)
            self.save_chart_image(plt, p_dict, k_dict)

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, ValueError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

        except Exception as sub_error:
            log['Critical'].append(u"[{0}] Fatal error: {1}".format(dev.name, sub_error))
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def clean_string(self, val):
        """
        Cleans long strings of whitespace and formats certain characters

        The clean_string(self, val) method is used to scrub multiline text elements in
        order to try to make them more presentable. The need is easily seen by looking
        at the rough text that is provided by the U.S. National Weather Service, for
        example.

        -----

        :param str val:
        """

        if self.host_plugin.verboseLogging:
            self.host_plugin.logger.debug(u"Length of initial string: {0}".format(len(val)))

        # List of (elements, replacements)
        clean_list = [(' am ', ' AM '), (' pm ', ' PM '), ('*', ' '), ('\u000A', ' '), ('...', ' '), ('/ ', '/'), (' /', '/'), ('/', ' / ')]

        # Take the old, and replace it with the new.
        for (old, new) in clean_list:
            val = val.replace(old, new)

        val = ' '.join(val.split())  # Eliminate spans of whitespace.

        if self.host_plugin.verboseLogging:
            self.host_plugin.logger.debug(u"Length of final string: {0}".format(len(val)))

        return val

    def convert_the_data(self, final_data):
        """
        Convert data into form that matplotlib can understand

        Matplotlib can't plot values like 'Open' and 'Closed', so we convert them for
        plotting. We do this on the fly and we don't change the underlying data in any
        way. Further, some data can be presented that should not be charted. For
        example, the WUnderground plugin will present '-99.0' when WUnderground is not
        able to deliver a rational value. Therefore, we convert '-99.0' to NaN values.

        -----

        :param list final_data: the data to be charted.
        """

        converter = {'true': 1,
                     'false': 0,
                     'open': 1,
                     'closed': 0,
                     'on': 1,
                     'off': 0,
                     'locked': 1,
                     'unlocked': 0,
                     'up': 1,
                     'down': 0,
                     '1': 1,
                     '0': 0,
                     'heat': 1}

        for value in final_data:
            if value[1].lower() in converter.keys():
                value[1] = converter[value[1].lower()]

        # We have converted all nonsense numbers to '-99.0'. Let's replace
        # those with 'NaN' for charting.
        final_data = [[n[0], 'NaN'] if n[1] == '-99.0' else n for n in final_data]
        return final_data

    def format_axis_x_label(self, dev, p_dict, k_dict):
        """
        Format X axis label visibility and properties

        If the user chooses to display a legend, we don't want an axis label because
        they will fight with each other for space.

        -----

        :param indigo.Device dev:
        :param dict p_dict:
        :param dict k_dict:
        :return unicode result:
        """

        if not p_dict['showLegend']:
            plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            return u"[{0}] No call for legend. Formatting X label.".format(dev.name)

        if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
            return u"[{0}] X axis label is suppressed to make room for the chart legend.".format(dev.name)

        return ''

    def format_axis_x_scale(self, x_axis_bins):
        """
        Format X axis scale based on user setting

        The format_axis_x_scale() method sets the bins for the X axis. Presently, we
        assume a date-based X axis.

        -----

        :param list x_axis_bins:
        """

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

    def format_axis_x_ticks(self, ax, p_dict, k_dict):
        """
        Format X axis tick properties

        Controls the format and placement of the tick marks on the X axis.

        -----

        :param ax:
        :param dict p_dict:
        :param dict k_dict:
        """

        ax.tick_params(axis='x', **k_dict['k_major_x'])
        ax.tick_params(axis='x', **k_dict['k_minor_x'])
        ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
        self.format_axis_x_scale(p_dict['xAxisBins'])  # Set the scale for the X axis. We assume a date.

        # If the x axis format has been set to None, let's hide the labels.
        if p_dict['xAxisLabelFormat'] == "None":
            ax.axes.xaxis.set_ticklabels([])

        return ax

    def format_axis_y(self, ax, p_dict, k_dict):
        """
        Format Y1 axis display properties

        Controls the format and properties of the Y axis.

        -----

        :param ax:
        :param dict p_dict:
        :param dict k_dict:
        """

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

    def format_axis_y1_min_max(self, p_dict):
        """
        Format Y1 axis range limits

        Setting the limits before the plot turns off autoscaling, which causes the
        limit that's not set to behave weirdly at times. This block is meant to
        overcome that weirdness for something more desirable.

        -----

        :param dict p_dict:
        """

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
                y_axis_min = min(p_dict['data_array']) * 0.98
                y_axis_max = max(p_dict['data_array']) * 1.02

        plt.ylim(ymin=y_axis_min, ymax=y_axis_max)

    def format_axis_y1_label(self, p_dict, k_dict):
        """
        Format Y1 axis labels

        Controls the format and placement of labels for the Y1 axis.

        -----

        :param dict p_dict:
        :param dict k_dict:
        """

        plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

    def format_axis_y_ticks(self, p_dict, k_dict):
        """
        Format Y axis tick marks

        Controls the format and placement of Y ticks.

        -----

        :param dict p_dict:
        :param dict k_dict:
        """

        plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])
        try:
            marks = [float(_) for _ in p_dict['customTicksY'].split(",")]
            if p_dict['customTicksLabelY'] == "":
                labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksY'].split(",")]
            else:
                labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksLabelY'].split(",")]
            plt.yticks(marks, labels)
        except Exception:
            pass

    def format_axis_y2_label(self, p_dict, k_dict):
        """
        Format Y2 axis properties

        Controls the format and placement of labels for the Y2 axis.

        -----

        :param dict p_dict:
        :param dict k_dict:
        """

        plt.ylabel(p_dict['customAxisLabelY2'], **k_dict['k_y_axis_font'])

    def format_dates(self, list_of_dates):
        """
        Convert date strings to date objects

        Convert string representations of date values to values to mdate values for
        charting.

        -----

        :param list_of_dates:
        """

        dates_to_plot = [date_parse(obs) for obs in list_of_dates]
        dates_to_plot = mdate.date2num(dates_to_plot)

        return dates_to_plot

    def format_grids(self, p_dict, k_dict):
        """
        Format matplotlib grids

        Format grids for visibility and properties.

        -----

        :param dict p_dict:
        :param dict k_dict:

        """

        if p_dict['showxAxisGrid']:
            plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])

        if p_dict['showyAxisGrid']:
            plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    def get_data(self, data_source):
        """
        Retrieve data from CSV file.

        Reads data from source CSV file and returns a list of tuples for charting. The
        data are provided as unicode strings [('formatted date', 'observation'), ...]

        -----

        :param str data_source:
        """

        final_data = []
        try:
            data_file  = open(data_source, "r")
            csv_data   = reader(data_file, delimiter=',')
            [final_data.append(item) for item in csv_data]
            data_file.close()
            final_data = self.convert_the_data(final_data)
            if self.host_plugin.verboseLogging:
                self.host_plugin.logger.debug(str(final_data))
                self.host_plugin.logger.debug(u"Data retrieved successfully: {0}".format(data_source.decode("utf-8")))

        except Exception as sub_error:
            self.host_plugin.pluginErrorHandler(traceback.format_exc())
            self.host_plugin.logger.warning(u"Error downloading CSV data. Skipping: {0}".format(sub_error))

        if self.host_plugin.verboseLogging:
            self.host_plugin.logger.threaddebug(u"{0:<19}{1}".format("Final data: ", final_data))

        return final_data

    def make_chart_figure(self, width, height, p_dict):
        """
        Create the matplotlib figure object and create the main axes element.

        Create the figure object for charting and include one axes object. The method
        also add a few customizations when defining the objects.

        -----

        :param float width:
        :param float height:
        :param dict p_dict:
        """

        dpi = plt.rcParams['savefig.dpi']
        height = float(height)
        width = float(width)

        fig = plt.figure(1, figsize=(width / dpi, height / dpi))
        ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
        ax.margins(0.04, 0.05)
        [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]
        return ax

    def plot_best_fit_line_segments(self, ax, dates_to_plot, line, p_dict):
        """
        Adds best fit line segments to plots

        The plot_best_fit_line_segments method provides a utility to add "best fit lines"
        to select types of charts (best fit lines are not appropriate for all chart
        types.

        -----

        """
        color = p_dict.get('line{0}BestFitColor'.format(line), '#FF0000')

        ax.plot(np.unique(dates_to_plot), np.poly1d(np.polyfit(dates_to_plot, p_dict['y_obs{0}'.format(line)], 1))(np.unique(dates_to_plot)), color=color, zorder=1)

        return ax

    def plot_custom_line_segments(self, ax, p_dict, k_dict):
        """
        Chart custom line segments handler

        Process any custom line segments and add them to the
        matplotlib axes object.

        -----

        :param matplotlib.axes.AxesSubplot ax:
        :param dict p_dict:
        :param dict k_dict:
        """

        # Plot the custom lines if needed.  Note that these need to be plotted after
        # the legend is established, otherwise some of the characteristics of the
        # min/max lines will take over the legend props.
        if self.host_plugin.verboseLogging:
            self.host_plugin.logger.debug(u"Custom line segments ({0}): {1}".format(p_dict['enableCustomLineSegments'], p_dict['customLineSegments']))

        if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ["", "None"]:
            try:
                constants_to_plot = literal_eval(p_dict['customLineSegments'])
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
                self.host_plugin.logger.warning(u"There is a problem with the custom segments settings. {0}".format(sub_error))

    def save_chart_image(self, plt, p_dict, k_dict):
        """
        Save the chart figure to a file.

        Uses the matplotlib savefig module to write the chart to a file.

        -----

        :param matplotlib object plt:
        :param dict p_dict:
        :param dict k_dict:
        """

        if p_dict['chartPath'] != '' and p_dict['fileName'] != '':
            plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')
