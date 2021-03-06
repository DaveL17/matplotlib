#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
matplotlib plugin
author: DaveL17
The matplotlib plugin is used to produce various types of charts and graphics
for use on Indigo control pages. The key benefits of the plugin are its ability
to make global changes to all generated charts (i.e., fonts, colors) and its
relative simplicity. It contains direct support for some automated charts (for
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

# TODO: NEW -- "Error" chart with min/max/avg
# TODO: NEW -- Floating bar chart
# TODO: NEW -- Generic weather forecast charts to support any weather services and drop support for WU and FW.
# TODO: NEW -- Standard chart types with pre-populated data that link to types of Indigo devices.
# TODO: NEW -- Bar gauge chart (i.e., semi-circle)
# TODO: NEW -- Chart with axes (scales) 3 and 4.
#              (see: https://matplotlib.org/3.1.1/gallery/ticks_and_spines/multiple_yaxis_with_spines.html)

# TODO: Try to address annotation collisions.
# TODO: Allow scripting control or a tool to repopulate color controls so that you can change all
#       bars/lines/scatter etc in one go.
# TODO: Consider adding a leading zero obs when date range limited data is less than the specified
#       date range (so the chart always shows the specified date range.)
# TODO: When the number of bars to be plotted is less than the number of bars requested (because
#       there isn't enough data), the bars plot funny.
# TODO: Improve reaction when data location is unavailable. Maybe get it out of csv_refresh_process
#       and don't even cycle the plugin when the location is gone.
# TODO: Change chart features based on underlying data. (i.e., stock bar chart)
# TODO: Move more code out of plugin.py
# TODO: Move multiline text font color to theme color
# TODO: Move multiline text font size to theme size

# ================================== IMPORTS ==================================

try:
    import indigo
except ImportError as error:
    pass

# Built-in modules
import ast
import copy
import csv
import datetime as dt
from dateutil.parser import parse as date_parse
import xml.etree.ElementTree as eTree
import json
import logging
import numpy as np
import operator as op
import os
import pickle
from queue import Queue
import re
import shutil
import subprocess
import threading
import traceback

import matplotlib
matplotlib.use('AGG')  # Note: this statement must be run before any other matplotlib imports are done.
from matplotlib import rcParams
try:
    import matplotlib.pyplot as plt
except ImportError:
    indigo.server.log(u"There was an error importing necessary Matplotlib components. Please reboot your server and "
                      u"try to re-enable the plugin.", isError=True)
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
__title__     = u"Matplotlib Plugin for Indigo"
__version__   = u"0.9.47"

# =============================================================================

install_path = indigo.server.getInstallFolderPath()

kDefaultPluginPrefs = {
    u'backgroundColor': "00 00 00",
    u'backgroundColorOther': False,
    u'chartPath': u"{path}/IndigoWebServer/images/controls/static/".format(path=install_path),
    u'chartResolution': 100,
    u'dataPath': u"{path}/Logs/com.fogbert.indigoplugin.matplotlib/".format(path=install_path),
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
    u'showDebugLevel': 30,  # comes from template_debugging.xml
    # u'snappyConfigMenus': False,
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
        self.dev_var_list = []  # List of devices and variables (updated in getDeviceConfigUiValues)
        self.refresh_queue = Queue()

        # ========================== Initialize DLFramework ===========================
        self.Fogbert = Dave.Fogbert(self)           # Plugin functional framework
        self.Fogbert.pluginEnvironmentLogger()      # Log universal pluginEnvironment information
        self.maintain = maintenance.Maintain(self)  # Maintenance of plugin props and device prefs

        # =========================== Log More Plugin Info ============================
        self.pluginEnvironmentLogger()  # Additional information relative to this plugin

        # ============================= Initialize Logger =============================
        fmt = '%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s'
        self.plugin_file_handler.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug_level = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debug_level)

        # Set private log handler based on plugin preference
        if self.pluginPrefs.get('verboseLogging', False):
            self.plugin_file_handler.setLevel(5)
            self.logger.warning(u"Verbose logging is on. It is best to leave this turned off unless directed.")
        else:
            self.plugin_file_handler.setLevel(10)

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
            self.logger.threaddebug(u"[{n}] Final device values_dict: {v}".format(n=dev.name, v=dict(values_dict)))
            self.logger.threaddebug(u"Configuration complete.")
        else:
            self.logger.threaddebug(u"User cancelled.")

        if dev.configured and dev.deviceTypeId not in ("rcParamsDevice", "csvEngine"):
            self.refresh_queue.put([dev])

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

        self.logger.debug(u"[{n}] Starting chart device.".format(n=dev.name))
        # If we're coming here from a sleep state, we need to ensure that the plugin
        # shutdown global is in its proper state.
        self.pluginIsShuttingDown = False
        self.maintain.clean_props(dev)
        dev.stateListOrDisplayStateIdChanged()
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    def deviceStopComm(self, dev):

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    def getActionConfigUiValues(self, values_dict, type_id="", dev_id=0):

        # ===========================  Apply Theme Action  ============================
        if type_id == "themeApplyAction":
            return values_dict

        # ==================================  Else  ===================================
        if len(values_dict) == 0:
            return self.pluginPrefs
        else:
            return values_dict

    # =============================================================================
    def getDeviceConfigUiValues(self, values_dict, type_id="", dev_id=0):

        dev = indigo.devices[int(dev_id)]
        self.dev_var_list = self.generatorDeviceAndVariableList()

        self.logger.threaddebug(u"[{n}] Getting device config props: {v}".format(n=dev.name, v=dict(values_dict)))

        try:

            # ===========================  CSV Engine Defaults  ===========================
            # Put certain props in a state that we expect when the config dialog is first
            # opened. These settings are regardless of whether the device has been
            # initially configured or not.
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

            # ======================  Open Config on Chart Controls  ======================
            # Ensure that every time a device config dialog is opened, it reverts to the
            # 'Chart Controls' settings group.
            if 'settingsGroup' in values_dict.keys():
                values_dict['settingsGroup'] = u'ch'

            # ========================== Set Config UI Defaults ===========================
            # For new devices, force certain defaults in case they don't carry from
            # Devices.xml. This seems to be especially important for menu items built with
            # callbacks and colorpicker controls that don't accept defaultValue (Indigo
            # version 7.5 adds support for colorpicker defaultValue.
            if not dev.configured:

                values_dict['refreshInterval'] = '900'

                # ============================ Line Charting Device ===========================
                if type_id == "areaChartingDevice":

                    for _ in range(1, 9, 1):
                        values_dict['area{i}Color'.format(i=_)]       = 'FF FF FF'
                        values_dict['area{i}Marker'.format(i=_)]      = 'None'
                        values_dict['area{i}MarkerColor'.format(i=_)] = 'FF FF FF'
                        values_dict['area{i}Source'.format(i=_)]      = 'None'
                        values_dict['area{i}Style'.format(i=_)]       = '-'
                        values_dict['line{i}Color'.format(i=_)]       = 'FF FF FF'
                        values_dict['line{i}Style'.format(i=_)]       = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ================================  Flow Bar  =================================
                if type_id == "barChartingDevice":

                    for _ in range(1, 5, 1):
                        values_dict['bar{i}Color'.format(i=_)]  = 'FF FF FF'
                        values_dict['bar{i}Source'.format(i=_)] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ================================  Stock Bar  ================================
                if type_id == "barStockChartingDevice":

                    for _ in range(1, 6, 1):
                        values_dict['bar{i}Color'.format(i=_)]  = 'FF FF FF'
                        values_dict['bar{i}Source'.format(i=_)] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisLabelFormat']    = 'None'

                # ================================  Stock Bar H ===============================
                if type_id == "barStockHorizontalChartingDevice":

                    for _ in range(1, 6, 1):
                        values_dict['bar{i}Color'.format(i=_)]  = 'FF FF FF'
                        values_dict['bar{i}Source'.format(i=_)] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisLabelFormat']    = 'None'

                # ================================  Raidal Bar ================================
                if type_id == "radialBarChartingDevice":

                    values_dict['bar_1']  = '00 FF 00'
                    values_dict['bar_2']  = '33 33 33'
                    values_dict['bar1Source'] = 'None'

                # =========================== Battery Health Device ===========================
                if type_id == "batteryHealthDevice":
                    values_dict['cautionColor']               = 'FF FF 00'
                    values_dict['cautionLevel']               = '10'
                    values_dict['healthyColor']               = '00 00 CC'
                    values_dict['showBatteryLevel']           = True
                    values_dict['showBatteryLevelBackground'] = False
                    values_dict['showDeadBattery']            = False
                    values_dict['warningColor']               = 'FF 00 00'
                    values_dict['warningLevel']               = '5'

                # ========================== Calendar Charting Device =========================
                if type_id == "calendarChartingDevice":
                    values_dict['fontSize'] = 12
                    values_dict['todayHighlight'] = "55 55 55"

                # ============================ Line Charting Device ===========================
                if type_id == "lineChartingDevice":

                    for _ in range(1, 9, 1):
                        values_dict['line{i}BestFit'.format(i=_)]      = False
                        values_dict['line{i}BestFitColor'.format(i=_)] = 'FF 00 00'
                        values_dict['line{i}Color'.format(i=_)]        = 'FF FF FF'
                        values_dict['line{i}Marker'.format(i=_)]       = 'None'
                        values_dict['line{i}MarkerColor'.format(i=_)]  = 'FF FF FF'
                        values_dict['line{i}Source'.format(i=_)]       = 'None'
                        values_dict['line{i}Style'.format(i=_)]        = '-'

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
                        values_dict['line{i}BestFit'.format(i=_)]      = False
                        values_dict['line{i}BestFitColor'.format(i=_)] = 'FF 00 00'
                        values_dict['group{i}Color'.format(i=_)]       = 'FF FF FF'
                        values_dict['group{i}Marker'.format(i=_)]      = '.'
                        values_dict['group{i}MarkerColor'.format(i=_)] = 'FF FF FF'
                        values_dict['group{i}Source'.format(i=_)]      = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ========================== Weather Forecast Device ==========================
                if type_id == "forecastChartingDevice":

                    for _ in range(1, 3, 1):
                        values_dict['line{i}Marker'.format(i=_)]      = 'None'
                        values_dict['line{i}MarkerColor'.format(i=_)] = 'FF FF FF'
                        values_dict['line{i}Style'.format(i=_)]       = '-'

                    values_dict['customLineStyle']      = '-'
                    values_dict['customTickFontSize']   = 8
                    values_dict['customTitleFontSize']  = 10
                    values_dict['daytimeColor']         = '33 33 33'
                    values_dict['forecastSourceDevice'] = 'None'
                    values_dict['line1Color']           = 'FF 33 33'
                    values_dict['line2Color']           = '00 00 FF'
                    values_dict['line3Color']           = '99 CC FF'
                    values_dict['line3MarkerColor']     = 'FF FF FF'
                    values_dict['showDaytime']          = 'true'
                    values_dict['xAxisBins']            = 'daily'
                    values_dict['xAxisLabelFormat']     = '%A'

            # ========================= Composite Forecast Device =========================
            if type_id == "compositeForecastDevice":
                values_dict['lineColor']        = "00 00 FF"
                values_dict['lineMarkerColor']  = "FF 00 00"
                values_dict['xAxisLabelFormat'] = "%A"

            if self.pluginPrefs.get('enableCustomLineSegments', False):
                values_dict['enableCustomLineSegmentsSetting'] = True
                self.logger.threaddebug(u"Enabling advanced feature: Custom Line Segments.")
            else:
                values_dict['enableCustomLineSegmentsSetting'] = False

            # If Snappy Config Menus are enabled, reset all device config dialogs to a
            # minimized state (all sub-groups minimized upon open.) Otherwise, leave them
            # where they are.
            # if self.pluginPrefs.get('snappyConfigMenus', False):
            #     self.logger.threaddebug(u"Enabling advanced feature: Snappy Config Menus.")
            #
            #     for key in ('areaLabel1', 'areaLabel2', 'areaLabel3', 'areaLabel4', 'areaLabel5', 'areaLabel6',
            #                 'areaLabel7', 'areaLabel8', 'barLabel1', 'barLabel2', 'barLabel3', 'barLabel4', 'barLabel5',
            #                 'lineLabel1', 'lineLabel2', 'lineLabel3', 'lineLabel4', 'lineLabel5', 'lineLabel6',
            #                 'lineLabel7', 'lineLabel8', 'groupLabel1', 'groupLabel1', 'groupLabel2', 'groupLabel3',
            #                 'groupLabel4', 'xAxisLabel', 'xAxisLabel', 'y2AxisLabel', 'yAxisLabel', ):
            #         if key in values_dict.keys():
            #             values_dict[key] = False

            return values_dict

        except KeyError as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.warning(u"[{n}] Error: {s}. See plugin log for more "
                                u"information.".format(n=dev.name, s=sub_error))

        return True, values_dict

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

    # =============================================================================
    def getMenuActionConfigUiValues(self, menu_id=""):

        settings       = indigo.Dict()
        error_msg_dict = indigo.Dict()

        self.logger.threaddebug(u"Getting menu action config prefs: {s}".format(s=dict(settings)))

        # =========================  Advanced Settings Menu  ==========================
        if menu_id not in ["refreshChartsNow", "themeManager"]:
            settings['enableCustomLineSegments']  = self.pluginPrefs.get('enableCustomLineSegments', False)
            settings['forceOriginLines']          = self.pluginPrefs.get('forceOriginLines', False)
            settings['promoteCustomLineSegments'] = self.pluginPrefs.get('promoteCustomLineSegments', False)
            settings['snappyConfigMenus']         = self.pluginPrefs.get('snappyConfigMenus', False)

        # ===========================  Theme Manager Menu  ============================
        # Open dialog with existing settings populated.
        if menu_id == "themeManager":
            for key in ['backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther', 'fontColor',
                        'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle', 'legendFontSize',
                        'lineWeight', 'mainFontSize', 'spineColor', 'tickColor', 'tickFontSize', 'tickSize']:

                settings[key] = self.pluginPrefs.get(key, None)

        return settings, error_msg_dict

    # =============================================================================
    def getPrefsConfigUiValues(self):

        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        self.logger.threaddebug(u"Getting plugin Prefs: {pp}".format(pp=dict(plugin_prefs)))

        # Establish a set of defaults for select plugin settings. Only those settings that are populated dynamically
        # need to be set here (the others can be set directly by the XML.)
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
                         'tickFontSize': '8'
                         }

        # Try to assign the value from plugin_prefs. If it doesn't work, add the key, value pair based on the
        # defaults_dict above. This should only be necessary the first time the plugin is configured.
        for key, value in defaults_dict.iteritems():
            plugin_prefs[key] = plugin_prefs.get(key, value)

        return plugin_prefs

    # =============================================================================
    def runConcurrentThread(self):

        self.sleep(0.5)

        while True:
            if not self.pluginIsShuttingDown:
                self.refresh_the_charts_queue()
                self.csv_refresh()
                self.charts_refresh()
                self.sleep(1)

    def sendDevicePing(self, dev_id=0, suppress_logging=False):

        indigo.server.log(u"Matplotlib Plugin devices do not support the ping function.")
        return {'result': 'Failure'}

    # =============================================================================
    def startup(self):

        # =========================== Check Indigo Version ============================
        self.Fogbert.audit_server_version(min_ver=7)

        # =========================== Check CSV Uniqueness ============================
        self.csv_check_unique()

        # ============================== Audit CSV Files ==============================
        self.audit_csv_health()

        # ============================ Audit Device Props =============================
        self.audit_device_props()

        # ============================= Audit Save Paths ==============================
        self.audit_save_paths()

        # ============================ Audit Theme Paths ==============================
        self.audit_themes_file()

    # =============================================================================
    def shutdown(self):

        self.logger.threaddebug(u"Shutdown called.")
        self.pluginIsShuttingDown = True

    # =============================================================================
    def validatePrefsConfigUi(self, values_dict=None):

        error_msg_dict = indigo.Dict()

        self.debug_level = int(values_dict['showDebugLevel'])
        self.indigo_log_handler.setLevel(self.debug_level)

        self.logger.threaddebug(u"Validating plugin configuration parameters.")

        # ================================ Data Paths =================================
        for path_prop in ('chartPath', 'dataPath'):
            try:
                if not values_dict[path_prop].endswith('/'):
                    error_msg_dict[path_prop] = u"The path must end with a forward slash '/'."

            except AttributeError:
                error_msg_dict[path_prop] = u"The path must end with a forward slash '/'."

        # =============================== Chart Colors ================================
        # Inspects various color controls and sets them to default when the value is
        # not valid hex (A-F, 0-9).
        color_dict = {'fontColorAnnotation': "FF FF FF", 'fontColor': "FF FF FF",
                      'backgroundColor': "00 00 00", 'faceColor': "00 00 00",
                      'gridColor': "88 88 88", 'spineColor': "88 88 88", 'tickColor': "88 88 88",
                      }

        for item in color_dict.keys():
            if re.search(r"^[0-9A-Fa-f]+$", values_dict[item].replace(" ", "")) is None:
                values_dict[item] = color_dict[item]
                self.logger.warning(u"Invalid color code found in plugin preferences [{i}], resetting to "
                                    u"default.".format(i=item))

        # ============================= Chart Dimensions ==============================
        for dimension_prop in ('rectChartHeight', 'rectChartWidth', 'rectChartWideHeight', 'rectChartWideWidth',
                               'sqChartSize'):

            # Remove any spaces
            try:
                values_dict[dimension_prop] = values_dict[dimension_prop].replace(" ", "")
            except AttributeError:
                pass

            try:
                if float(values_dict[dimension_prop]) < 75:
                    error_msg_dict[dimension_prop] = u"The dimension value must be greater than 75 pixels."
            except ValueError:
                error_msg_dict[dimension_prop] = u"The dimension value must be a real number."

        # ============================= Chart Resolution ==============================
        # Note that chart resolution includes a warning feature that will pass the
        # value after the warning is cleared.
        try:
            # If value is null, a null string, or all whitespace.
            if not values_dict['chartResolution'] or \
                    values_dict['chartResolution'] == "" or \
                    str(values_dict['chartResolution']).isspace():
                values_dict['chartResolution'] = "100"
                self.logger.warning(u"No resolution value entered. Resetting resolution to 100 DPI.")

            # If warning flag and the value is potentially too small.
            elif values_dict['dpiWarningFlag'] and 0 < int(values_dict['chartResolution']) < 80:
                values_dict['dpiWarningFlag'] = False
                error_msg_dict['showAlertText'] = u"It is recommended that you enter a value of 80 or more for " \
                                                  u"best results."

            else:
                pass

        except ValueError:
            error_msg_dict['chartResolution'] = u"The chart resolution value must be greater than 0."

        # ================================ Line Weight ================================
        try:
            if float(values_dict['lineWeight']) <= 0:
                error_msg_dict['lineWeight'] = u"The line weight value must be greater than zero."
        except ValueError:
            error_msg_dict['lineWeight'] = u"The line weight value must be a real number."

        if len(error_msg_dict) > 0:
            return False, values_dict, error_msg_dict

        else:
            # TODO: consider adding this feature to DLFramework and including in all plugins.
            # ============================== Log All Changes ==============================
            # Log any changes to the plugin preferences.
            changed_keys   = ()
            config_changed = False

            for key in values_dict.keys():
                try:
                    if values_dict[key] != self.pluginPrefs[key]:
                        config_changed = True
                        changed_keys += (u"{k}".format(k=key),
                                         u"Old: {k}".format(k=self.pluginPrefs[key]),
                                         u"New: {k}".format(k=values_dict[key]),)
                # Missing keys will be config dialog format props like labels and separators
                except KeyError:
                    pass

            if config_changed:
                self.logger.threaddebug(u"values_dict changed: {ck}".format(ck=changed_keys))

            values_dict['dpiWarningFlag'] = True
            self.logger.threaddebug(u"Preferences validated successfully.")
            return True, values_dict

    # =============================================================================
    def validateDeviceConfigUi(self, values_dict=None, type_id="", dev_id=0):

        error_msg_dict = indigo.Dict()
        self.logger.threaddebug(u"Validating device configuration parameters.")

        # ================================ Area Chart =================================
        if type_id == 'areaChartingDevice':

            # There must be at least 1 source selected
            if values_dict['area1Source'] == 'None':
                error_msg_dict['area1Source'] = u"You must select at least one data source."
                values_dict['settingsGroup'] = "1"

            # Iterate for each area group (1-8).
            for area in range(1, 9, 1):
                # Line adjustment values
                for char in values_dict['area{i}adjuster'.format(i=area)]:
                    if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                        error_msg_dict['area{i}adjuster'.format(i=area)] = u"Valid operators are +, -, *, /"
                        values_dict['settingsGroup'] = str(area)

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksY'] = u"Custom tick labels and custom tick locations must be the " \
                                                          u"same length."
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and custom tick locations must be the " \
                                                          u"same length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):
                    for tick in custom_ticks:
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

        # ================================  Flow Bar  =================================
        if type_id == 'barChartingDevice':

            # Must select at least one source (bar 1)
            if values_dict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                values_dict['barLabel1'] = True
                values_dict['settingsGroup'] = "1"

            try:
                # Bar width must be greater than 0. Will also trap strings.
                if not float(values_dict['barWidth']) >= 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['barWidth'] = u"You must enter a bar width greater than 0."
                values_dict['settingsGroup'] = "ch"

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and locations must be the same length."
                    error_msg_dict['customTicksY'] = u"Custom tick labels and locations must be the same length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):

                    for tick in custom_ticks:
                        # Ensure all custom tick locations are within bounds.
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

        # ================================  Stock Bar  ================================
        if type_id == 'barStockChartingDevice':

            # Must select at least one source (bar 1)
            if values_dict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                values_dict['settingsGroup'] = "1"

            try:
                # Bar width must be greater than 0. Will also trap strings.
                if not float(values_dict['barWidth']) >= 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['barWidth'] = u"You must enter a bar width greater than 0."
                values_dict['settingsGroup'] = "ch"

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and locations must be the same length."
                    error_msg_dict['customTicksY'] = u"Custom tick labels and locations must be the same length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):

                    for tick in custom_ticks:
                        # Ensure all custom tick locations are within bounds.
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

            # Test the selected values to ensure that they can be charted (int, float, bool)
            for source in ['bar1Value', 'bar2Value', 'bar3Value', 'bar4Value', 'bar5Value']:

                # Pull the number out of the source key
                n = re.search('[0-9]', source)

                # Get the id of the bar source
                if values_dict['bar{0}Source'.format(n.group(0))] != "None":
                    source_id = int(values_dict['bar{0}Source'.format(n.group(0))])

                    # By definition it will either be a device ID or a variable ID.
                    if source_id in indigo.devices.keys():

                        # Get the selected device state value
                        val = indigo.devices[source_id].states[values_dict[source]]
                        if not isinstance(val, (int, float, bool)):
                            error_msg_dict[source] = u"The selected device state can not be charted due to its value."

                    else:
                        val = indigo.variables[source_id].value
                        try:
                            float(val)
                        except ValueError:
                            if not val.lower() in ['true', 'false']:
                                error_msg_dict[source] = u"The selected variable value can not be charted due to " \
                                                         u"its value."
                                values_dict['settingsGroup'] = str(n)

        # ==========================  Stock Horizontal Bar  ===========================
        if type_id == 'barStockHorizontalChartingDevice':

            # Must select at least one source (bar 1)
            if values_dict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                values_dict['settingsGroup'] = "1"

            try:
                # Bar width must be greater than 0. Will also trap strings.
                if not float(values_dict['barWidth']) >= 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['barWidth'] = u"You must enter a bar width greater than 0."
                values_dict['settingsGroup'] = "ch"

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and locations must be the same length."
                    error_msg_dict['customTicksY'] = u"Custom tick labels and locations must be the same length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):

                    for tick in custom_ticks:
                        # Ensure all custom tick locations are within bounds.
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

            # Test the selected values to ensure that they can be charted (int, float, bool)
            for source in ['bar1Value', 'bar2Value', 'bar3Value', 'bar4Value', 'bar5Value']:

                # Pull the number out of the source key
                n = re.search('[0-9]', source)

                # Get the id of the bar source
                if values_dict['bar{0}Source'.format(n.group(0))] != "None":
                    source_id = int(values_dict['bar{0}Source'.format(n.group(0))])

                    # By definition it will either be a device ID or a variable ID.
                    if source_id in indigo.devices.keys():

                        # Get the selected device state value
                        val = indigo.devices[source_id].states[values_dict[source]]
                        if not isinstance(val, (int, float, bool)):
                            error_msg_dict[source] = u"The selected device state can not be charted due to its value."
                            values_dict['settingsGroup'] = str(n)

                    else:
                        val = indigo.variables[source_id].value
                        try:
                            float(val)
                        except ValueError:
                            if not val.lower() in ['true', 'false']:
                                error_msg_dict[source] = u"The selected variable value can not be charted due to " \
                                                         u"its value."
                                values_dict['settingsGroup'] = str(n)

        # ===============================  Radial Bar  ================================
        if type_id == 'radialBarChartingDevice':

            # Must select at least one source (bar 1)
            if values_dict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."

            # See if the scale value will float.
            if values_dict['scale'].startswith('%%'):
                try:
                    float(self.substitute(values_dict['scale']))
                except ValueError:
                    error_msg_dict['scale'] = u"The substitution field is not valid."

        # =========================== Battery Health Chart ============================
        if type_id == 'batteryHealthDevice':

            for prop in ('cautionLevel', 'warningLevel'):
                try:
                    # Bar width must be greater than 0. Will also trap strings.
                    if not 0 <= float(values_dict[prop]) <= 100:
                        raise ValueError
                except ValueError:
                    error_msg_dict[prop] = u"Alert levels must between 0 and 100 (integer)."
                    values_dict['settingsGroup'] = "dsp"

        # ============================== Calendar Chart ===============================
        # There are currently no unique validation steps needed for calendar devices
        if type_id == 'calendarChartingDevice':
            pass

        # ================================ CSV Engine =================================
        if type_id == 'csvEngine':

            # ========================== Number of Observations ===========================
            try:
                # Must be 1 or greater
                if int(values_dict['numLinesToKeep']) < 1:
                    raise ValueError
            except ValueError:
                error_msg_dict['numLinesToKeep'] = u"The observation value must be a whole number integer greater " \
                                                   u"than zero."

            # ================================= Duration ==================================
            try:
                # Must be zero or greater
                if float(values_dict['numLinesToKeepTime']) < 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['numLinesToKeepTime'] = u"The duration value must be an integer or float greater " \
                                                       u"than zero."

            # ============================= Refresh Interval ==============================
            try:
                # Must be zero or greater
                if int(values_dict['refreshInterval']) < 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['refreshInterval'] = u"The refresh interval must be a whole number integer and " \
                                                    u"greater than zero."

            # =============================== Data Sources ================================
            try:
                sources = ast.literal_eval(values_dict['columnDict'])

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

        # ================================ Line Chart =================================
        if type_id == 'lineChartingDevice':

            # There must be at least 1 source selected
            if values_dict['line1Source'] == 'None':
                error_msg_dict['line1Source'] = u"You must select at least one data source."
                values_dict['settingsGroup'] = "1"

            # Iterate for each line group (1-6).
            for area in range(1, 9, 1):

                # Line adjustment values
                for char in values_dict['line{i}adjuster'.format(i=area)]:
                    if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                        error_msg_dict['line{i}adjuster'.format(i=area)] = u"Valid operators are +, -, *, /"
                        values_dict['settingsGroup'] = str(area)

                # Fill is illegal for the steps line type
                if values_dict['line{i}Style'.format(i=area)] == 'steps' and values_dict['line{i}Fill'.format(i=area)]:
                    error_msg_dict['line{i}Fill'.format(i=area)] = u"Fill is not supported for the Steps line type."
                    values_dict['settingsGroup'] = str(area)

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and custom tick locations must be the " \
                                                          u"same length."
                    error_msg_dict['customTicksY'] = u"Custom tick labels and custom tick locations must be the same " \
                                                     u"length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):

                    for tick in custom_ticks:
                        # Ensure all custom tick locations are within bounds.
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

        # ============================== Multiline Text ===============================
        if type_id == 'multiLineText':

            for prop in ('thing', 'thingState'):
                # A data source must be selected
                if not values_dict[prop] or values_dict[prop] == 'None':
                    error_msg_dict[prop] = u"You must select a data source."
                    values_dict['settingsGroup'] = "src"

            try:
                if int(values_dict['numberOfCharacters']) < 1:
                    raise ValueError
            except ValueError:
                error_msg_dict['numberOfCharacters'] = u"The number of characters must be a positive number greater " \
                                                       u"than zero (integer)."
                values_dict['settingsGroup'] = "dsp"

            # Figure width and height.
            for prop in ('figureWidth', 'figureHeight'):
                try:
                    if int(values_dict[prop]) < 1:
                        raise ValueError
                except ValueError:
                    error_msg_dict[prop] = u"The figure width and height must be positive whole numbers greater " \
                                           u"than zero (pixels)."
                    values_dict['settingsGroup'] = "dsp"

            # Font size
            try:
                if float(values_dict['multilineFontSize']) < 0:
                    raise ValueError
            except ValueError:
                error_msg_dict['multilineFontSize'] = u"The font size must be a positive real number greater than zero."
                values_dict['settingsGroup'] = "dsp"

        # ================================ Polar Chart ================================
        if type_id == 'polarChartingDevice':

            if not values_dict['thetaValue']:
                error_msg_dict['thetaValue'] = u"You must select a direction source."
                values_dict['settingsGroup'] = "src"

            if not values_dict['radiiValue']:
                error_msg_dict['radiiValue'] = u"You must select a magnitude source."
                values_dict['settingsGroup'] = "src"

            # Number of observations
            try:
                if int(values_dict['numObs']) < 1:
                    error_msg_dict['numObs'] = u"You must specify at least 1 observation (must be a whole number " \
                                               u"integer)."
                    values_dict['settingsGroup'] = "dsp"
            except ValueError:
                error_msg_dict['numObs'] = u"You must specify at least 1 observation (must be a whole number " \
                                           u"integer)."
                values_dict['settingsGroup'] = "dsp"

        # =============================== Scatter Chart ===============================
        if type_id == 'scatterChartingDevice':

            if not values_dict['group1Source']:
                error_msg_dict['group1Source'] = u"You must select at least one data source."
                values_dict['settingsGroup'] = "1"

            # =============================== Custom Ticks ================================
            # Ensure all custom tick locations are numeric, within bounds and of the same length.
            if values_dict['customTicksY'].lower() not in ("", 'none'):
                custom_ticks = values_dict['customTicksY'].replace(' ', '')
                custom_ticks = custom_ticks.split(',')
                custom_tick_labels = values_dict['customTicksLabelY'].split(',')

                default_y_axis = (values_dict['yAxisMin'], values_dict['yAxisMax'])
                default_y_axis = [x.lower() == 'none' for x in default_y_axis]

                try:
                    custom_ticks = [float(_) for _ in custom_ticks]
                except ValueError:
                    error_msg_dict['customTicksY'] = u"All custom tick locations must be numeric values."
                    values_dict['settingsGroup'] = "y"

                # Ensure tick labels and values are the same length.
                if len(custom_tick_labels) != len(custom_ticks):
                    error_msg_dict['customTicksLabelY'] = u"Custom tick labels and custom tick locations must be the " \
                                                          u"same length."
                    error_msg_dict['customTicksY'] = u"Custom tick labels and custom tick locations must be the same " \
                                                     u"length."
                    values_dict['settingsGroup'] = "y"

                # Ensure all custom Y tick locations are within bounds. User has elected to
                # change at least one Y axis boundary (if both upper and lower bounds are set
                # to 'None', we move on).
                if not all(default_y_axis):

                    for tick in custom_ticks:
                        # Ensure all custom tick locations are within bounds.
                        if values_dict['yAxisMin'].lower() != 'none' and not tick >= float(values_dict['yAxisMin']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

                        if values_dict['yAxisMax'].lower() != 'none' and not tick <= float(values_dict['yAxisMax']):
                            error_msg_dict['customTicksY'] = u"All custom tick locations must be within the " \
                                                             u"boundaries of the Y axis."
                            values_dict['settingsGroup'] = "y"

        # =============================== Weather Chart ===============================
        if type_id == 'forecastChartingDevice':

            if not values_dict['forecastSourceDevice']:
                error_msg_dict['forecastSourceDevice'] = u"You must select a weather forecast source device."
                values_dict['settingsGroup'] = "ch"

        # ========================== Composite Weather Chart ==========================
        if type_id == 'compositeForecastDevice':

            if not values_dict['forecastSourceDevice']:
                error_msg_dict['forecastSourceDevice'] = u"You must select a weather forecast source device."
                values_dict['settingsGroup'] = "ch"

            for _ in ('pressure_min', 'pressure_max',
                      'temperature_min', 'temperature_max',
                      'humidity_min', 'humidity_max',
                      'precipitation_min', 'precipitation_max',
                      'wind_min', 'wind_max',):
                try:
                    float(values_dict[_])

                except ValueError:
                    if values_dict[_] in ("", "None"):
                        pass
                    else:
                        error_msg_dict[_] = u"The value must be empty, 'None', or a numeric value."
                        values_dict['settingsGroup'] = "y1"

            if len(values_dict['component_list']) < 2:
                error_msg_dict['component_list'] = u"You must select at least two plot elements."
                values_dict['settingsGroup'] = "fe"

        # ============================== All Chart Types ==============================
        # The following validation blocks are applied to all graphical chart device
        # types.

        # ========================== Chart Custom Dimensions ==========================
        # Check to see that custom chart dimensions conform to valid types
        for custom_dimension_prop in ('customSizeHeight', 'customSizeWidth', 'customSizePolar'):
            try:
                if custom_dimension_prop in values_dict.keys() and \
                        values_dict[custom_dimension_prop] != 'None' and \
                        float(values_dict[custom_dimension_prop]) < 75:
                    error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be greater than 75 pixels."
            except ValueError:
                error_msg_dict[custom_dimension_prop] = u"The chart dimension value must be a real number greater " \
                                                        u"than 75 pixels."

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
                    values_dict[limit_prop] = 'None'
                    error_msg_dict[limit_prop] = u"The axis limit must be a real number or None."

        # Y axis limits min must be less than max
        try:
            y_min = float(values_dict.get('yAxisMin', "None"))
        except ValueError:
            y_min = min

        try:
            y_max = float(values_dict.get('yAxisMax', "None"))
        except ValueError:
            y_max = max

        if isinstance(y_min, float) and isinstance(y_max, float):
            if not y_max > y_min:
                error_msg_dict['yAxisMin'] = u"Min must be less than max if both are specified."
                error_msg_dict['yAxisMax'] = u"Max must be greater than min if both are specified."

        if len(error_msg_dict) > 0:
            error_msg_dict['showAlertText'] = u"Configuration Errors\n\nThere are one or more settings that need to " \
                                              u"be corrected. Fields requiring attention will be highlighted."
            return False, values_dict, error_msg_dict

        self.logger.threaddebug(u"Preferences validated successfully.")
        return True, values_dict, error_msg_dict

    # =============================================================================
    def validateMenuConfigUi(self, values_dict=None, type_id="", dev_id=0):
        self.logger.info(u"v: {}".format(values_dict))
        self.logger.info(u"t: {}".format(type_id))
        self.logger.info(u"d: {}".format(dev_id))
        return True, values_dict

    # =============================================================================
    def __log_dicts(self, dev=None):
        """
        Write parameters dicts to log under verbose logging
        Simple method to write rcParm and kwarg dicts to debug log.
        -----
        :param dev:
        """

        self.logger.threaddebug(u"[{0:<19}] Props: {1}".format(dev.name, dict(dev.pluginProps)))

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
    def action_refresh_the_charts(self, plugin_action):
        """
        Called by an Indigo Action item.
        Allows the plugin to call the charts_refresh() method from an Indigo Action
        item. This action will refresh all charts.
        -----
        :param class 'indigo.PluginAction' plugin_action:
        """
        self.skipRefreshDateUpdate = True
        devices_to_refresh = [dev for dev in indigo.devices.itervalues('self') if
                              dev.enabled and dev.deviceTypeId != 'csvEngine']

        self.charts_refresh(dev_list=devices_to_refresh)
        self.logger.info(u"{0:{1}^80}".format(u' Redraw All Charts Action Complete ', '='))

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

        self.logger.threaddebug(u"Advanced settings menu final prefs: {vd}".format(vd=dict(values_dict)))
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
        self.logger.threaddebug(u"Advanced settings menu final prefs: {vd}".format(vd=dict(values_dict)))
        return

    # =============================================================================
    def audit_csv_health(self):
        """
        Creates any missing CSV files before beginning
        Iterate through all existing CSV Engine devices. It doesn't matter if the
        device is enabled or not, since we're only creating the file if it doesn't
        exist, and we're only going to add the header to the file.
        -----
        :return:
        """
        self.logger.debug(u"Auditing CSV health.")
        data_path = self.pluginPrefs['dataPath']

        for dev in indigo.devices.iter(filter='self'):
            if dev.deviceTypeId == 'csvEngine':
                column_dict = ast.literal_eval(dev.pluginProps['columnDict'])

                for thing in column_dict.items():
                    full_path = data_path + thing[1][0] + ".csv"

                    # ============================= Create (if needed) ============================
                    # If the appropriate CSV file doesn't exist, create it and write the header
                    # line.
                    if not os.path.isdir(data_path):
                        try:
                            os.makedirs(data_path)
                            self.logger.warning(u"Target data folder doesn't exist. Creating it.")

                        except IOError:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.critical(u"[{name}] Target data folder doesn't exist and the plugin is "
                                                 u"unable to create it. See plugin log for more "
                                                 u"information.".format(name=dev.name))

                        except OSError:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.critical(u"[{name}] The plugin is unable to access the data storage location. "
                                                 u"See plugin log for more information.".format(name=dev.name))

                    if not os.path.isfile(full_path):
                        self.logger.warning(u"CSV file doesn't exist. Creating a new one: {fp}".format(fp=full_path))
                        csv_file = open(full_path, 'w')
                        csv_file.write('{t},{h}\n'.format(t='Timestamp', h=thing[1][2].encode("utf-8")))
                        csv_file.close()

    # =============================================================================
    def audit_device_props(self):
        """
        Audit device properties to ensure they match the current config.
        The audit_device_props method performs two functions. It compares the current
        device config XML layout to the current dev.pluginProps, and (1) where the
        current config has fields that are missing from the device, they will be
        _added_ to the device (checkboxes will be coerced to boolean based on the
        defaultValue attribute if specified; if unspecified, the value will be set to
        False.) and (2) where the current pluginProps contains keys that are not in
        the config, they will be _removed_ from the device.
        The method will return True if it has run error free; False on exception.
        Note that this method should _not_ be called from deviceStartComm() as it will
        cause an infinite loop--the call to dev.replacePluginPropsOnServer() from this
        method automatically calls deviceStartComm(). It is recommended that the method
        be called from plugin's startup() method.
        -----
        :return:
        """
        # TODO: migrate this to DLFramework

        self.logger.debug(u"Updating device properties to match current plugin version.")

        try:
            # Iterate through the plugin's devices
            for dev in indigo.devices.iter(filter="self"):

                # =========================== Match Props to Config ===========================
                # For config props that are not in the device's current definition.

                device_xml = self.getDeviceConfigUiXml(dev.deviceTypeId, dev.id)
                fields     = []
                props      = dev.pluginProps
                tree       = eTree.fromstring(device_xml.encode('utf-8'))

                # Iterate through the Config UI fields
                for field in tree.iter('Field'):

                    attributes = field.attrib

                    # Ignore UI controls that the device doesn't need to function.
                    if attributes['type'].lower() not in ('button', 'label', 'separator'):

                        field_id      = attributes['id']    # attribute 'id' is required
                        field_type    = attributes['type']  # attribute 'type' is required
                        default_value = attributes.get('defaultValue', "")  # attribute 'defaultValue is not required

                        # Save a list of field IDs for later use.
                        fields.append(field_id)

                        # If the XML field is not in the device's current props dict
                        if field_id not in props.keys():

                            # Coerce checkbox default values to bool. Everything that comes in from the XML is a
                            # string; everything that's not converted will be sent as a string.
                            if field_type.lower() == 'checkbox':
                                if default_value.lower() == u'true':
                                    default_value = True
                                else:
                                    default_value = False  # will be False if no defaultValue specified.

                            props[field_id] = default_value
                            self.logger.debug(u"[{name}] missing prop [{id}] will be added. Value set to "
                                              u"[{val}]".format(name=dev.name, id=field_id, val=default_value))

                # =========================== Match Config to Props ===========================
                # For props that have been removed but are still in the device definition.

                for key in props.keys():
                    if key not in fields:

                        self.logger.debug(u"[{name}] prop obsolete prop [{k}] will be "
                                          u"removed".format(name=dev.name, k=key))
                        del props[key]

                # Now that we're done, let's save the updated dict back to the device.
                dev.replacePluginPropsOnServer(props)

            return True

        except Exception as sub_error:
            self.logger.warning(u"Audit device props error: {s}".format(s=sub_error))

            return False

    # =============================================================================
    def audit_dict_color(self, _dict_):
        """
        """
        # TODO: this method can be flattened

        pattern = r"[0-9A-Fa-f][0-9A-Fa-f] [0-9A-Fa-f][0-9A-Fa-f] [0-9A-Fa-f][0-9A-Fa-f]"
        # Colors are stored in pluginProps as "XX XX XX", and we need to convert them to "#XXXXXX".
        for k in _dict_.keys():
            if isinstance(_dict_[k], unicode):
                if re.search(pattern, _dict_[k]):
                    _dict_[k] = self.fix_rgb(color=_dict_[k])
                else:
                    pass

            # k_dict is a dict of dicts, so we need to go one level lower.
            elif isinstance(_dict_[k], dict):
                for k1 in _dict_[k]:
                    if isinstance(_dict_[k][k1], unicode):
                        if re.search(pattern, _dict_[k][k1]):
                            _dict_[k][k1] = self.fix_rgb(color=_dict_[k][k1])
                        else:
                            pass
                    if isinstance(_dict_[k][k1], dict):
                        for k11 in _dict_[k][k1].keys():
                            if re.search(pattern, str(_dict_[k][k1][k11])):
                                _dict_[k][k1][k11] = self.fix_rgb(color=_dict_[k][k1][k11])
                            else:
                                pass

        return _dict_

    # =============================================================================
    def audit_save_paths(self):
        """
        Audit plugin save locations to ensure validity
        The audit_save_paths() method will attempt to access the configured paths
        (CSV save location, chart save location) to ensure that they are accessible
        to the plugin. It will attempt to write to the paths and warn the user if
        unsuccessful.
        -----
        :return:
        """

        # ============================= Audit Save Paths ==============================
        # Test the current path settings to ensure that they are valid.
        path_list = (self.pluginPrefs['dataPath'], self.pluginPrefs['chartPath'])

        # If the target folders do not exist, create them.
        self.logger.debug(u"Auditing save paths.")
        for path_name in path_list:

            if not os.path.isdir(path_name):
                try:
                    self.logger.warning(u"Target folder doesn't exist. Creating path:{path}".format(path=path_name))
                    os.makedirs(path_name)

                except (IOError, OSError):
                    self.plugin_error_handler(sub_error=traceback.format_exc())
                    self.logger.critical(u"Target folder doesn't exist and the plugin is unable to create it. See "
                                         u"plugin log for more information.")

        # Test to ensure that each path is writeable.
        self.logger.debug(u"Auditing path IO.")
        for path_name in path_list:
            if os.access(path_name, os.W_OK):
                self.logger.debug(u"   Path OK: {path}".format(path=path_name))
            else:
                self.logger.critical(u"   Plugin doesn't have the proper rights to write to the path: "
                                     u"{path}".format(path=path_name))

        # ================ Compare Save Path to Current Indigo Version ================
        new_save_path = indigo.server.getInstallFolderPath() + u"/IndigoWebServer/images/controls/static/"
        current_save_path = self.pluginPrefs['chartPath']

        if new_save_path != current_save_path:
            if current_save_path.startswith('/Library/Application Support/Perceptive Automation/Indigo'):
                self.logger.critical(u"Charts are being saved to: {path})".format(path=current_save_path))
                self.logger.critical(u"You may want to change the save path to: {path}".format(path=new_save_path))

    @staticmethod
    # =============================================================================
    def audit_themes_file():
        """
        Check to make sure that the themes repository exists. If it doesn't, create it.
        :return:
        """
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        if not os.path.isfile(full_path):
            with open(full_path, 'w') as outfile:
                outfile.write(json.dumps({}, indent=4))

    # =============================================================================
    def chart_stock_bar(self, dev):
        # We can't access Indigo objects from the subprocess, so we need to get all
        # the information we need before calling the process.

        bars_data = []  # data for all bars (all data should be pickleable.

        for _ in range(1, 6, 1):
            bar_data = {}  # data for each bar
            try:
                annotate    = dev.ownerProps['bar{0}Annotate'.format(_)]
                color       = self.fix_rgb(dev.pluginProps['bar{0}Color'.format(_)])
                legend      = dev.ownerProps['bar{0}Legend'.format(_)]
                suppress    = dev.ownerProps['suppressBar{0}'.format(_)]
                thing_id    = int(dev.ownerProps['bar{0}Source'.format(_)])
                thing_state = dev.ownerProps['bar{0}Value'.format(_)]

                # Is it a device
                if thing_id in indigo.devices.keys():
                    d = indigo.devices[thing_id]
                    val = d.states[thing_state]
                    name = d.name
                    state = thing_state
                # or a variable?
                elif thing_id in indigo.variables.keys():
                    v = indigo.variables[thing_id]
                    val = v.value
                    name = v.name
                    state = "value"

                else:
                    raise ValueError

                bar_data['number'] = _
                bar_data['name'] = name
                bar_data['state'] = state
                bar_data['annotate_{0}'.format(_)] = annotate
                bar_data['color_{0}'.format(_)]    = color
                bar_data['legend_{0}'.format(_)]   = legend
                bar_data['suppress_{0}'.format(_)] = suppress
                bar_data['val_{0}'.format(_)]      = val
                bars_data.append(bar_data)

            except ValueError:
                # the bar[X]source field could be empty, so let's ignore it
                pass

        return bars_data

    # =============================================================================
    def charts_refresh(self, dev_list=None):
        """
        Refreshes all the plugin chart devices.
        Iterate through each chart device and refresh the image. Only enabled chart
        devices will be refreshed.
        -----
        :param list dev_list: list of devices to be refreshed.
        """

        def convert_to_native(obj):
            """
            Convert any indigo.Dict and indigo.List objects to native formats.

            credit: Jay Martin
                    https://forums.indigodomo.com/viewtopic.php?p=193744#p193744
            -----
            :param obj:
            :return:
            """
            if isinstance(obj, indigo.List):
                native_list = list()
                for _item_ in obj:
                    native_list.append(convert_to_native(_item_))
                return native_list
            elif isinstance(obj, indigo.Dict):
                native_dict = dict()
                for _key_, value in obj.items():
                    native_dict[_key_] = convert_to_native(value)
                return native_dict
            else:
                return obj

        if not self.pluginIsShuttingDown:

            k_dict       = {}  # A dict of kwarg dicts
            reply        = ""
            err          = ""
            path_to_file = ""
            payload      = {}

            # A dict of plugin preferences (we set defaults and override with pluginPrefs).
            p_dict  = dict(self.pluginPrefs)

            try:
                # ============================  p_dict Overrides  =============================
                p_dict['font_style']    = 'normal'
                p_dict['font_weight']   = 'normal'
                p_dict['tick_bottom']   = 'on'
                p_dict['tick_left']     = 'on'
                p_dict['tick_right']    = 'off'
                p_dict['tick_top']      = 'off'
                p_dict['legendColumns'] = self.pluginPrefs.get('legendColumns', 5)

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

                # ============================= Background color ==============================
                # backgroundColorOther is the transparent background config setting
                # Transparent Background = True
                # Filled Background      = False

                # Transparent is True, so we don't want filled.
                if self.pluginPrefs.get('backgroundColorOther', 'false'):
                    p_dict['transparent_charts'] = True
                # Transparent is False, so we want filled.
                else:
                    p_dict['transparent_charts'] = False

                # ============================== Plot Area color ==============================
                # facColorOther is the transparent plot config setting
                # Transparent Plot Area  = True
                # Filled Plot Area       = False

                # Transparent is True, so we don't want filled.
                if self.pluginPrefs.get('faceColorOther', 'false'):
                    p_dict['transparent_filled'] = False
                # Transparent is False, so we want filled.
                else:
                    p_dict['transparent_filled'] = True

                # ===========================  Device List is None  ===========================
                # Gather up a list of the devices that have exceeded their refresh times.
                if not dev_list:
                    dev_list = []

                    for dev in indigo.devices.itervalues('self'):
                        refresh_interval = int(dev.pluginProps['refreshInterval'])

                        if dev.deviceTypeId != 'csvEngine' and refresh_interval > 0 and dev.enabled:
                            diff = dt.datetime.now() - date_parse(dev.states['chartLastUpdated'])
                            refresh_needed = diff > dt.timedelta(seconds=refresh_interval)

                            if refresh_needed:
                                dev_list.append(dev)

                # =============================  Fix RGB Colors  ==============================
                # TODO: consolidate fix_rgb
                plt.rcParams['grid.color']  = self.fix_rgb(color=self.pluginPrefs.get('gridColor', '88 88 88'))
                plt.rcParams['xtick.color'] = self.fix_rgb(color=self.pluginPrefs.get('tickColor', '88 88 88'))
                plt.rcParams['ytick.color'] = self.fix_rgb(color=self.pluginPrefs.get('tickColor', '88 88 88'))

                # ============================  Update the Charts  ============================
                for dev in dev_list:
                    device_states = list()  # A list of state/value pairs used to feed updateStatesOnServer()
                    self.logger.debug(u"Updating chart: [{0}]".format(dev.name))
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
                    k_dict['k_battery']            = {'color': p_dict['fontColorAnnotation'],
                                                      'ha': 'right',
                                                      'size': plt.rcParams['xtick.labelsize'],
                                                      'textcoords': 'data',
                                                      'va': 'center',
                                                      'xycoords': 'data',
                                                      'zorder': 25
                                                      }
                    k_dict['k_annotation_battery'] = {'bbox': dict(boxstyle='round,pad=0.3',
                                                                   facecolor=p_dict['faceColor'],
                                                                   edgecolor=p_dict['spineColor'],
                                                                   alpha=0.75,
                                                                   linewidth=0.5
                                                                   ),
                                                      'color': p_dict['fontColorAnnotation'],
                                                      'ha': 'center',
                                                      'size': plt.rcParams['xtick.labelsize'],
                                                      'textcoords': 'data',
                                                      'va': 'center',
                                                      'xycoords': 'data',
                                                      'zorder': 25
                                                      }
                    k_dict['k_annotation']         = {'bbox': dict(boxstyle='round,pad=0.3',
                                                                   facecolor=p_dict['faceColor'],
                                                                   edgecolor=p_dict['spineColor'],
                                                                   alpha=0.75,
                                                                   linewidth=0.5
                                                                   ),
                                                      'color': p_dict['fontColorAnnotation'],
                                                      'size': plt.rcParams['xtick.labelsize'],
                                                      'horizontalalignment': 'center',
                                                      'textcoords': 'offset points',
                                                      'verticalalignment': 'center'
                                                      }
                    k_dict['k_bar']                = {'alpha': 1.0, 'zorder': 10}
                    k_dict['k_base_font']          = {'size': float(p_dict['mainFontSize']),
                                                      'weight': p_dict['font_weight']
                                                      }
                    k_dict['k_calendar']           = {'verticalalignment': 'top'}
                    k_dict['k_custom']             = {'alpha': 1.0, 'zorder': 3}
                    k_dict['k_fill']               = {'alpha': 0.7, 'zorder': 10}
                    k_dict['k_grid_fig']           = {'which': 'major',
                                                      'color': p_dict['gridColor'],
                                                      'zorder': 1
                                                      }
                    k_dict['k_line']               = {'alpha': 1.0}
                    k_dict['k_major_x']            = {'bottom': p_dict['tick_bottom'],
                                                      'reset': False,
                                                      'top': p_dict['tick_top'],
                                                      'which': 'major',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['xtick.color']
                                                      }
                    k_dict['k_major_y']            = {'left': p_dict['tick_left'],
                                                      'reset': False,
                                                      'right': p_dict['tick_right'],
                                                      'which': 'major',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['ytick.color']
                                                      }
                    k_dict['k_major_y2']           = {'left': p_dict['tick_left'],
                                                      'reset': False,
                                                      'right': p_dict['tick_right'],
                                                      'which': 'major',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['ytick.color']
                                                      }
                    k_dict['k_max']                = {'linestyle': 'dotted',
                                                      'marker': None,
                                                      'alpha': 1.0,
                                                      'zorder': 1}
                    k_dict['k_min']                = {'linestyle': 'dotted',
                                                      'marker': None,
                                                      'alpha': 1.0,
                                                      'zorder': 1
                                                      }
                    k_dict['k_minor_x']            = {'bottom': p_dict['tick_bottom'],
                                                      'reset': False,
                                                      'top': p_dict['tick_top'],
                                                      'which': 'minor',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['xtick.color']
                                                      }
                    k_dict['k_minor_y']            = {'left': p_dict['tick_left'],
                                                      'reset': False,
                                                      'right': p_dict['tick_right'],
                                                      'which': 'minor',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['ytick.color']
                                                      }
                    k_dict['k_minor_y2']           = {'left': p_dict['tick_left'],
                                                      'reset': False,
                                                      'right': p_dict['tick_right'],
                                                      'which': 'minor',
                                                      'labelcolor': p_dict['fontColor'],
                                                      'labelsize': float(p_dict['mainFontSize']),
                                                      'color': plt.rcParams['ytick.color']
                                                      }
                    k_dict['k_rgrids']             = {'angle': 67,
                                                      'color': p_dict['fontColor'],
                                                      'horizontalalignment': 'left',
                                                      'verticalalignment': 'center'
                                                      }
                    k_dict['k_title_font']         = {'color': p_dict['fontColor'],
                                                      'fontname': p_dict['fontMain'],
                                                      'fontsize': float(p_dict['mainFontSize']),
                                                      'fontstyle': p_dict['font_style'],
                                                      'weight': p_dict['font_weight'],
                                                      'visible': True
                                                      }
                    k_dict['k_x_axis_font']        = {'color': p_dict['fontColor'],
                                                      'fontname': p_dict['fontMain'],
                                                      'fontsize': float(p_dict['mainFontSize']),
                                                      'fontstyle': p_dict['font_style'],
                                                      'weight': p_dict['font_weight'],
                                                      'visible': True
                                                      }
                    k_dict['k_y_axis_font']        = {'color': p_dict['fontColor'],
                                                      'fontname': p_dict['fontMain'],
                                                      'fontsize': float(p_dict['mainFontSize']),
                                                      'fontstyle': p_dict['font_style'],
                                                      'weight': p_dict['font_weight'],
                                                      'visible': True
                                                      }
                    k_dict['k_y2_axis_font']       = {'color': p_dict['fontColor'],
                                                      'fontname': p_dict['fontMain'],
                                                      'fontsize': float(p_dict['mainFontSize']),
                                                      'fontstyle': p_dict['font_style'],
                                                      'weight': p_dict['font_weight'],
                                                      'visible': True
                                                      }

                    # If the user has selected transparent in the plugin menu, we account for that here when
                    # setting up the kwargs for savefig().
                    if p_dict['transparent_charts']:
                        k_dict['k_plot_fig'] = {'bbox_extra_artists': None,
                                                'bbox_inches': None,
                                                'format': None,
                                                'frameon': None,
                                                'orientation': None,
                                                'pad_inches': None,
                                                'papertype': None,
                                                'transparent': True
                                                }
                    else:
                        k_dict['k_plot_fig'] = {'bbox_extra_artists': None,
                                                'bbox_inches': None,
                                                'edgecolor': p_dict['backgroundColor'],
                                                'facecolor': p_dict['backgroundColor'],
                                                'format': None,
                                                'frameon': None,
                                                'orientation': None,
                                                'pad_inches': None,
                                                'papertype': None,
                                                'transparent': False
                                                }

                    # ========================== matplotlib.rc overrides ==========================
                    plt.rc('font', **k_dict['k_base_font'])

                    p_dict.update(dev.pluginProps)

                    for _ in ('bar_colors', 'customTicksLabelY', 'customTicksY', 'data_array', 'dates_to_plot',
                              'headers', 'wind_direction', 'wind_speed', 'x_obs1', 'x_obs2', 'x_obs3', 'x_obs4',
                              'x_obs5', 'x_obs6', 'x_obs7', 'x_obs8', 'y_obs1', 'y_obs1_max', 'y_obs1_min', 'y_obs2',
                              'y_obs2_max', 'y_obs2_min', 'y_obs3', 'y_obs3_max', 'y_obs3_min', 'y_obs4',
                              'y_obs4_max', 'y_obs4_min', 'y_obs5', 'y_obs5_max', 'y_obs5_min', 'y_obs6',
                              'y_obs6_max', 'y_obs6_min', 'y_obs7', 'y_obs7_max', 'y_obs7_min', 'y_obs8',
                              'y_obs8_max', 'y_obs8_min'
                              ):
                        p_dict[_] = []

                    p_dict['fileName']  = ''
                    p_dict['headers_1'] = ()  # Tuple
                    p_dict['headers_2'] = ()  # Tuple

                    try:
                        # TODO: can delete.  Moved to top of block
                        # device_states = list()  # A list of state/value pairs used to feed updateStatesOnServer()
                        p_dict.update(dev.pluginProps)  # update p_dict with any corresponding value in pluginProps

                        # ======================= Limit number of observations ========================
                        try:
                            p_dict['numObs'] = int(p_dict['numObs'])

                        except KeyError:
                            # Only some devices will have their own numObs.
                            pass

                        except ValueError as sub_error:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.warning(u"[{name}] The number of observations must be a positive "
                                                u"number: {s}. See plugin log for more "
                                                u"information.".format(name=dev.name, s=sub_error))

                        # ============================ Custom Square Size =============================
                        try:
                            if p_dict['customSizePolar'] == 'None':
                                pass

                            else:
                                p_dict['sqChartSize'] = float(p_dict['customSizePolar'])

                        except ValueError as sub_error:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.warning(u"[{name}] Custom size must be a positive number or None: "
                                                u"{s}".format(name=dev.name, s=sub_error))

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
                        for _ in range(1, 9, 1):

                            try:
                                best_fit_color = dev.pluginProps['line{i}BestFitColor'.format(i=_)]
                                p_dict['line{i}BestFitColor'.format(i=_)] = best_fit_color
                            except KeyError:
                                pass

                        # ============================== Phantom Labels ===============================
                        # Since users may or may not include axis labels and because we want to ensure
                        # that all plot areas present in the same way, we need to create 'phantom'
                        # labels that are plotted but not visible.  Setting the font color to 'None'
                        # will effectively hide them.
                        try:
                            if p_dict['customAxisLabelX'].isspace() or p_dict['customAxisLabelX'] == '':
                                p_dict['customAxisLabelX'] = 'null'
                                k_dict['k_x_axis_font']    = {'color': 'None',
                                                              'fontname': p_dict['fontMain'],
                                                              'fontsize': float(p_dict['mainFontSize']),
                                                              'fontstyle': p_dict['font_style'],
                                                              'weight': p_dict['font_weight'],
                                                              'visible': True
                                                              }
                        except KeyError:
                            # Not all devices will contain these keys
                            pass

                        try:
                            if p_dict['customAxisLabelY'].isspace() or p_dict['customAxisLabelY'] == '':
                                p_dict['customAxisLabelY'] = 'null'
                                k_dict['k_y_axis_font']    = {'color': 'None',
                                                              'fontname': p_dict['fontMain'],
                                                              'fontsize': float(p_dict['mainFontSize']),
                                                              'fontstyle': p_dict['font_style'],
                                                              'weight': p_dict['font_weight'],
                                                              'visible': True
                                                              }
                        except KeyError:
                            # Not all devices will contain these keys
                            pass

                        try:
                            # Not all devices that get to this point will support Y2.
                            if 'customAxisLabelY2' in p_dict.keys():
                                if p_dict['customAxisLabelY2'].isspace() or p_dict['customAxisLabelY2'] == '':
                                    p_dict['customAxisLabelY2'] = 'null'
                                    k_dict['k_y2_axis_font']    = {'color': 'None',
                                                                   'fontname': p_dict['fontMain'],
                                                                   'fontsize': float(p_dict['mainFontSize']),
                                                                   'fontstyle': p_dict['font_style'],
                                                                   'weight': p_dict['font_weight'],
                                                                   'visible': True
                                                                   }
                        except KeyError:
                            # Not all devices will contain these keys
                            pass

                        # ================================ Annotations ================================
                        # If the user wants annotations, we need to hide the line
                        # markers as we don't want to plot one on top of the other.
                        for line in range(1, 9, 1):
                            try:
                                if p_dict['line{i}Annotate'.format(i=line)] and \
                                        p_dict['line{i}Marker'.format(i=line)] != 'None':
                                    p_dict['line{i}Marker'.format(i=line)] = 'None'
                                    self.logger.warning(u"[{name}] Line {ln} marker is suppressed to display "
                                                        u"annotations. To see the marker, disable annotations for "
                                                        u"this line.".format(name=dev.name, ln=line)
                                                        )
                            except KeyError:
                                # Not all devices will contain these keys
                                pass

                        # =============================== Line Markers ================================
                        # Some line markers need to be adjusted due to their inherent value. For
                        # example, matplotlib uses '<', '>' and '.' as markers but storing these values
                        # will blow up the XML.  So we need to convert them. (See self.formatMarkers()
                        # method.)
                        p_dict = self.format_markers(p_dict=p_dict)

                        # Note that the logging of p_dict and k_dict are handled within the thread.
                        self.logger.threaddebug(u"{0:*^80}".format(u" Generating Chart: {name} ".format(name=dev.name)))
                        self.__log_dicts(dev)

                        plug_dict = dict(self.pluginPrefs)
                        dev_dict  = dict(dev.pluginProps)
                        dev_dict['name']  = dev.name
                        dev_dict['model'] = dev.model

                        # ==========================  Custom Line Segments  ===========================
                        # We support substitutions in custom line segments settings. These need to be
                        # converted in the main plugin thread because they can't be converted within
                        # the subprocess.
                        try:
                            if p_dict['enableCustomLineSegments'] and \
                                dev.deviceTypeId in ["areaChartingDevice",
                                                     "barChartingDevice",
                                                     "barStockChartingDevice",
                                                     "barStockHorizontalChartingDevice",
                                                     "lineChartingDevice",
                                                     "scatterChartingDevice",
                                                     "forecastChartingDevice"] and \
                                    p_dict['customLineSegments'] not in ("", "None"):

                                try:
                                    # constants_to_plot will be (val, rgb) or ((val, rgb), (val, rgb)), Since
                                    # we can't mutate a tuple, we listify it first
                                    constants_to_plot = ast.literal_eval(p_dict['customLineSegments'])
                                    substituted_constants = ()

                                    # If val start with '%%' perform a substitution on it
                                    try:
                                        for element in [list(item) for item in constants_to_plot]:
                                            if str(element[0]).startswith("%%"):
                                                element[0] = float(self.substitute(element[0]))
                                            substituted_constants += (tuple(element),)

                                    except TypeError:
                                        substituted_constants += constants_to_plot

                                    p_dict['customLineSegments'] = substituted_constants

                                except (ValueError, IndexError):
                                    self.logger.warning(u"Problem with custom line segments. Please ensure setting is"
                                                        u"in the proper format.")

                        # Not all devices support custom line segments
                        except KeyError:
                            pass
                        except SyntaxError:
                            self.logger.warning(u"[{name}] Custom Line Segments entry is invalid. Skipping.".format(name=dev.name))

                        # =================================================
                        # Convert these indigo.List(s) to Python lists.
                        for key in plug_dict.iterkeys():
                            if isinstance(plug_dict[key], indigo.List):
                                plug_dict[key] = list(plug_dict[key])

                        for key in dev_dict.iterkeys():
                            if isinstance(dev_dict[key], indigo.List):
                                dev_dict[key] = list(dev_dict[key])

                        for key in p_dict.iterkeys():
                            if isinstance(p_dict[key], indigo.List):
                                p_dict[key] = list(p_dict[key])

                        # =================================================

                        # ============================== rcParams Device ==============================
                        if dev.deviceTypeId == 'rcParamsDevice':
                            self.rcParamsDeviceUpdate(dev=dev)

                        # For the time being, we're running each device through its
                        # own process synchronously; parallel processing may come later.
                        #
                        # NOTE: elements passed to a subprocess have to be pickleable. Indigo device
                        # and plugin objets are not pickleable, so we create a proxy to send to the
                        # process. Therefore, devices can't be changed in the processes.

                        # Audit values in p_dict and k_dict to ensure they're in the proper format.
                        plug_dict = copy.deepcopy(self.audit_dict_color(_dict_=plug_dict))
                        plug_dict['old_prefs'] = None
                        dev_dict  = self.audit_dict_color(_dict_=dev_dict)
                        p_dict    = copy.deepcopy(self.audit_dict_color(_dict_=p_dict))
                        p_dict['old_prefs']    = None
                        k_dict    = self.audit_dict_color(_dict_=k_dict)

                        # Instantiate basic payload sent to the subprocess scripts. Additional
                        # key/value pairs may be added below before payload is sent.
                        raw_payload = {'prefs': plug_dict,
                                       'props': dev_dict,
                                       'p_dict': p_dict,
                                       'k_dict': k_dict,
                                       'data': None,
                                       }

                        # ================================ Area Charts ================================
                        if dev.deviceTypeId == "areaChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_area.py'

                        # ================================  Flow Bar  =================================
                        if dev.deviceTypeId == 'barChartingDevice':

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_bar_flow.py'

                        # ================================  Stock Bar  ================================
                        if dev.deviceTypeId == 'barStockChartingDevice':

                            raw_payload['data'] = self.chart_stock_bar(dev=dev)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_bar_stock.py'

                        # ==========================  Stock Horizontal Bar  ===========================
                        if dev.deviceTypeId == 'barStockHorizontalChartingDevice':

                            raw_payload['data'] = self.chart_stock_bar(dev=dev)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_bar_stock_horizontal.py'

                        # ============================  Stock Radial Bar  =============================
                        if dev.deviceTypeId == 'radialBarChartingDevice':

                            source_id = int(dev.pluginProps['bar1Source'])
                            source_value = dev.pluginProps['bar1Value']
                            scale = dev.pluginProps['scale']

                            # The data value to chart.
                            if source_id in indigo.devices:
                                raw_payload['data'] = float(indigo.devices[source_id].states[source_value])
                            else:
                                raw_payload['data'] = float(indigo.variables[source_id].value)

                            # Convert scale value if it's a substitution. The substitution value should be valid
                            # because we checked it in validation.
                            if scale.startswith('%%'):
                                raw_payload['scale'] = self.substitute(scale)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_bar_radial.py'

                        # =========================== Battery Health Chart ============================
                        if dev.deviceTypeId == 'batteryHealthDevice':

                            device_dict  = {}
                            exclude_list = [int(_) for _ in dev.pluginProps.get('excludedDevices', [])]

                            for batt_dev in indigo.devices.itervalues():
                                try:
                                    if batt_dev.batteryLevel is not None and batt_dev.id not in exclude_list:
                                        device_dict[batt_dev.name] = batt_dev.states['batteryLevel']

                                    # The following line is used for testing the battery health code; it isn't
                                    # needed in production.
                                    # device_dict = {'Device 1': '0', 'Device 2': '100', 'Device 3': '8',
                                    #                'Device 4': '4', 'Device 5': '92', 'Device 6': '72',
                                    #                'Device 7': '47', 'Device 8': '68', 'Device 9': '0',
                                    #                'Device 10': '47'
                                    #                }

                                except Exception as sub_error:
                                    self.plugin_error_handler(sub_error=traceback.format_exc())
                                    self.logger.error(u"[{name}] Error reading battery devices: "
                                                      u"{s}".format(name=batt_dev.name, s=sub_error))

                            if device_dict == {}:
                                device_dict['No Battery Devices'] = 0

                            dev_dict['excludedDevices'] = convert_to_native(dev_dict['excludedDevices'])
                            p_dict['excludedDevices']   = convert_to_native(p_dict['excludedDevices'])

                            # Payload sent to the subprocess script
                            raw_payload['data'] = device_dict

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_batteryhealth.py'

                        # ============================== Calendar Charts ==============================
                        if dev.deviceTypeId == "calendarChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_calendar.py'

                        # ================================ Line Charts ================================
                        if dev.deviceTypeId == "lineChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_line.py'

                        # ============================== Multiline Text ===============================
                        if dev.deviceTypeId == 'multiLineText':

                            try:
                                # Get the text to plot. We do this here so we don't need to send all the
                                # devices and variables to the method (the process does not have access to the
                                # Indigo server).
                                if int(p_dict['thing']) in indigo.devices:
                                    dev_id = int(p_dict['thing'])
                                    raw_payload['data'] = unicode(indigo.devices[dev_id].states[p_dict['thingState']])

                                elif int(p_dict['thing']) in indigo.variables:
                                    raw_payload['data'] = unicode(indigo.variables[int(p_dict['thing'])].value)

                                else:
                                    raw_payload['data'] = u"Unable to reconcile plot text. Confirm device settings."
                                    self.logger.info(u"Presently, the plugin only supports device state and variable "
                                                     u"values.")

                                # Convert any nested indigo.Dict and indigo.List objects to native formats.
                                # We wait until this point to convert and pickle it because some devices add
                                # additional device-specific data.
                                raw_payload = convert_to_native(raw_payload)

                                # Serialize the payload
                                payload = pickle.dumps(raw_payload)

                                # Run the plot
                                path_to_file = 'chart_multiline.py'

                            except OSError as err:
                                if "Argument list too long" in err:
                                    self.logger.critical(u"Text source too long.")

                        # =============================== Polar Charts ================================
                        if dev.deviceTypeId == "polarChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_polar.py'

                        # ============================== Scatter Charts ===============================
                        if dev.deviceTypeId == "scatterChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_scatter.py'

                        # ========================== Weather Forecast Charts ==========================
                        if dev.deviceTypeId == "forecastChartingDevice":

                            dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                            state_list = dict(indigo.devices[int(p_dict['forecastSourceDevice'])].states)
                            sun_rise_set = [str(indigo.server.calculateSunrise()), str(indigo.server.calculateSunset())]

                            raw_payload['dev_type']     = dev_type
                            raw_payload['state_list']   = state_list
                            raw_payload['sun_rise_set'] = sun_rise_set

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_weather_forecast.py'

                        # ========================== Weather Composite Charts =========================
                        if dev.deviceTypeId == "compositeForecastDevice":

                            dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                            state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states

                            raw_payload['dev_type']   = dev_type
                            raw_payload['state_list'] = dict(state_list)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats.
                            # We wait until this point to convert and pickle it because some devices add
                            # additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Serialize the payload
                            payload = pickle.dumps(raw_payload)

                            # Run the plot
                            path_to_file = 'chart_weather_composite.py'

                        # =============================  Process Result  ==============================
                        # Get the results and act on anything
                        try:
                            proc = subprocess.Popen(['python2.7', path_to_file, payload, ],
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    )
                            if proc:
                                reply, err = proc.communicate()

                        except (TypeError, ValueError):
                            self.logger.debug(u"Payload raised error: {0}".format(payload))

                        # Parse the output log
                        result = self.process_plotting_log(device=dev, replies=reply, errors=err)

                        # If we have manually asked for all charts to update, don't refresh the last
                        # update time so that the charts will update on their own at the next refresh
                        # cycle.
                        if 'chartLastUpdated' in dev.states and not self.skipRefreshDateUpdate:
                            device_states.append({'key': 'chartLastUpdated',
                                                  'value': u"{now}".format(now=dt.datetime.now())})

                        # All has gone well.
                        if not result and dev.deviceTypeId not in ('rcParamsDevice',):
                            device_states.append({'key': 'onOffState', 'value': True, 'uiValue': 'Error'})
                        elif dev.deviceTypeId:
                            refresh_interval = dev.pluginProps.get('refreshInterval', 900)
                            if int(refresh_interval) == 0 and dev.deviceTypeId not in ('rcParamsDevice',):
                                ui_value = 'Manual'
                            elif int(refresh_interval) > 0 and dev.deviceTypeId not in ('rcParamsDevice',):
                                ui_value = 'Updated'
                            else:
                                ui_value = " "

                            device_states.append({'key': 'onOffState', 'value': True, 'uiValue': ui_value})

                        dev.updateStatesOnServer(device_states)

                    except RuntimeError as sub_error:
                        self.plugin_error_handler(sub_error=traceback.format_exc())
                        self.logger.critical(u"[{name}] Critical Error: {s}. See plugin log for more "
                                             u"information.".format(name=dev.name, s=sub_error))
                        self.logger.critical(u"Skipping device.")
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

                # Ensure the flag is in the proper state for the next automatic refresh.
                self.skipRefreshDateUpdate = False

            except Exception as sub_error:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.critical(u"[{name}] Error: {s}. See plugin log for more "
                                     u"information.".format(name=dev.name, s=unicode(sub_error)))
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

    # =============================================================================
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
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(u"Exception when trying to kill all comms. Error: {s}. See plugin log for more "
                                  u"information.".format(s=sub_error))

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
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(u"Exception when trying to kill all comms. Error: {s}. See plugin log for more "
                                  u"information.".format(s=sub_error))

    # =============================================================================
    def csv_check_unique(self):
        """
        :return:
        """
        self.logger.debug(u"Checking CSV references.")
        titles = {}

        # Iterate through CSV Engine devices
        for dev in indigo.devices.iter(filter='self'):
            if dev.deviceTypeId == 'csvEngine':

                # Get the list of CSV file titles
                column_dict = ast.literal_eval(dev.pluginProps['columnDict'])

                # Build a dictionary where the file title is the key and the value is a list of
                # devices that point to that title for a source.
                for key in column_dict.keys():

                    title = column_dict[key][0]

                    if title not in titles.keys():
                        titles[title] = [dev.name]

                    else:
                        titles[title].append(dev.name)

        # Iterate through the dict of titles
        for title_name in titles.keys():
            if len(titles[title_name]) > 1:
                self.logger.warning(u"Audit CSV data files: CSV filename [{tname}] referenced by more than one CSV "
                                    u"Engine device: {tnum}".format(tname=title_name, tnum=titles[title_name]))

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
        self.logger.threaddebug(u"[{dn}] csv item add values_dict: {vd}".format(dn=dev.name, vd=dict(values_dict)))

        error_msg_dict = indigo.Dict()

        try:
            # Convert column_dict from a string to a literal dict
            column_dict = ast.literal_eval(values_dict['columnDict'])
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
                error_msg_dict['addSource'] = u"Please select a device or variable as a source for your CSV data " \
                                              u"element."
                error_msg_dict['showAlertText'] = u"ID Error.\n\nA source is required for each CSV data element."
                return values_dict, error_msg_dict

            if values_dict['addState'] == "":
                error_msg_dict['addState'] = u"Please select a value source for your CSV data element."
                error_msg_dict['showAlertText'] = u"Data Error.\n\nA data value is required for each CSV data element."
                return values_dict, error_msg_dict

            # Create a list of existing keys with the 'k' lopped off
            [lister.append(key.lstrip('k')) for key in sorted(column_dict.keys())]
            # Change each value to an integer for evaluation
            [num_lister.append(int(item)) for item in lister]
            # Generate the next key
            next_key = u'k{nk}'.format(nk=int(max(num_lister)) + 1)
            # Save the tuple of properties
            column_dict[next_key] = (values_dict['addValue'], values_dict['addSource'], values_dict['addState'])

            # Remove any empty entries as they're not going to do any good anyway.
            new_dict = {}

            for k, v in column_dict.iteritems():
                if v != (u"", u"", u"") and v != ('None', 'None', 'None'):
                    new_dict[k] = v
                else:
                    self.logger.info(u"Pruning CSV Engine.")

            # Convert column_dict back to a string and prepare it for storage.
            values_dict['columnDict'] = str(new_dict)

        except AttributeError, sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"[{name}] Error adding CSV item: {s}. See plugin log for more "
                              u"information.".format(name=dev.name, s=sub_error))

        # If the appropriate CSV file doesn't exist, create it and write the header line.
        file_name = values_dict['addValue']
        full_path = "{path}{fn}.csv".format(path=self.pluginPrefs['dataPath'], fn=file_name.encode("utf-8"))

        if not os.path.isfile(full_path):

            with open(full_path, 'w') as outfile:
                outfile.write(u"{t},{fn}\n".format(t='Timestamp', fn=file_name).encode("utf-8"))

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
        self.logger.threaddebug(u"[{name}] csv item delete "
                                u"values_dict: {vd}".format(name=dev.name, vd=dict(values_dict)))

        # Convert column_dict from a string to a literal dict.
        column_dict = ast.literal_eval(values_dict['columnDict'])

        try:
            values_dict["editKey"] = values_dict["csv_item_list"]
            del column_dict[values_dict['editKey']]

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"[{name}] Error deleting CSV item: {s}. See plugin log for more "
                              u"information.".format(name=dev.name, s=sub_error))

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
            # Returning an empty dict seems to work and may solve the 'None' issue
            values_dict['columnDict'] = values_dict.get('columnDict', '{}')
            # Convert column_dict from a string to a literal dict.
            column_dict = ast.literal_eval(values_dict['columnDict'])
            prop_list   = [(key, "{n}".format(n=value[0].encode("utf-8"))) for key, value in column_dict.items()]

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"[{name}] Error generating CSV item list: {s}. See plugin log for more "
                              u"information.".format(name=dev.name, s=sub_error))
            prop_list = []

        # Return a list sorted by the value and not the key. Case insensitive sort.
        result = sorted(prop_list, key=lambda tup: tup[1].lower())
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
        self.logger.threaddebug(u"[{name}] csv item update "
                                u"values_dict: {vd}".format(name=dev.name, vd=dict(values_dict)))

        error_msg_dict = indigo.Dict()
        # Convert column_dict from a string to a literal dict.
        column_dict  = ast.literal_eval(values_dict['columnDict'])

        try:
            key = values_dict['editKey']
            previous_key = values_dict['previousKey']
            if key != previous_key:
                if key in column_dict:
                    error_msg_dict['editKey'] = u"New key ({k}) already exists in the global properties, please " \
                                                u"use a different key value".format(k=key)
                    values_dict['editKey']   = previous_key
                else:
                    del column_dict[previous_key]
            else:
                column_dict[key]            = (values_dict['editValue'],
                                               values_dict['editSource'],
                                               values_dict['editState']
                                               )
                values_dict['csv_item_list'] = ""
                values_dict['editKey']       = ""
                values_dict['editSource']    = ""
                values_dict['editState']     = ""
                values_dict['editValue']     = ""

            if not len(error_msg_dict):
                values_dict['previousKey'] = key

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"[{name}] Error updating CSV item: {s}. See plugin log for more "
                              u"information.".format(name=dev.name, s=sub_error))

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
        self.logger.threaddebug(u"[{name}] csv item select "
                                u"values_dict: {vd}".format(name=dev.name, vd=dict(values_dict)))

        try:
            column_dict                    = ast.literal_eval(values_dict['columnDict'])
            values_dict['editKey']          = values_dict['csv_item_list']
            values_dict['editSource']       = column_dict[values_dict['csv_item_list']][1]
            values_dict['editState']        = column_dict[values_dict['csv_item_list']][2]
            values_dict['editValue']        = column_dict[values_dict['csv_item_list']][0]
            values_dict['isColumnSelected'] = True
            values_dict['previousKey']      = values_dict['csv_item_list']

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"[{name}] There was an error establishing a connection with the item you chose: {s}. "
                              u"See plugin log for more information.".format(name=dev.name, s=sub_error))
        return values_dict

    # =============================================================================
    def csv_refresh(self):
        """
        Refreshes data for all CSV custom devices
        The csv_refresh() method manages CSV files through CSV Engine custom devices.
        -----
        """
        if not self.pluginIsShuttingDown:
            for dev in indigo.devices.itervalues("self"):

                if dev.deviceTypeId == 'csvEngine' and dev.enabled:

                    refresh_interval = int(dev.pluginProps['refreshInterval'])

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
                        csv_dict = ast.literal_eval(csv_dict_str)

                        self.logger.threaddebug(u"[{name}] Refreshing CSV "
                                                u"Device: {csv}".format(name=dev.name, csv=dict(csv_dict)))
                        self.csv_refresh_process(dev=dev, csv_dict=csv_dict)

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

            target_lines = int(dev.pluginProps.get('numLinesToKeep', '300'))
            delta        = dev.pluginProps.get('numLinesToKeepTime', '72')
            cycle_time   = dt.datetime.now()
            column_names = []
            data = []

            # If delta isn't a valid float, set it to zero.
            try:
                delta = float(delta)
            except ValueError:
                delta = 0.0

            # Read through the dict and construct headers and data
            for k, v in sorted(csv_dict.items()):

                # Create a path variable that is based on the target folder and the CSV item name.
                full_path = u"{path}{var}.csv".format(path=self.pluginPrefs['dataPath'], var=v[0])
                backup    = full_path.replace(u'.csv', u' copy.csv')

                # ============================= Create (if needed) ============================
                # If the appropriate CSV file doesn't exist, create it and write the header
                # line.
                if not os.path.isdir(self.pluginPrefs['dataPath']):
                    try:
                        os.makedirs(self.pluginPrefs['dataPath'])
                        self.logger.warning(u"Target data folder doesn't exist. Creating it.")

                    except OSError:
                        self.logger.critical(u"[{name}] Target data folder either doesn't exist or the plugin is "
                                             u"unable to access/create it.".format(name=dev.name))

                if not os.path.isfile(full_path):
                    try:
                        self.logger.debug(u"CSV doesn't exist. Creating: {path}".format(path=full_path))
                        csv_file = open(full_path, 'w')
                        csv_file.write('{t},{n}\n'.format(t='Timestamp', n=v[0].encode("utf-8")))
                        csv_file.close()
                        self.sleep(1)

                    except IOError:
                        self.logger.critical(u"[{name}] The plugin is unable to access the data storage location. "
                                             u"See plugin log for more information.".format(name=dev.name))

                # =============================== Create Backup ===============================
                # Make a backup of the CSV file in case something goes wrong.
                try:
                    shutil.copyfile(full_path, backup)

                except IOError as sub_error:
                    self.logger.error(u"[{name}] Unable to backup CSV file: {s}.".format(name=dev.name, s=sub_error))

                except Exception as sub_error:
                    self.plugin_error_handler(sub_error=traceback.format_exc())
                    self.logger.error(u"[{name}] Unable to backup CSV file: {s}. See plugin log for more "
                                      u"information.".format(name=dev.name, s=sub_error))

                # ================================= Load Data =================================
                # Read CSV data into data frame
                try:
                    with open(full_path) as in_file:
                        raw_data = [row for row in csv.reader(in_file, delimiter=',')]

                    # Split the headers and the data
                    column_names = raw_data[:1]
                    data         = raw_data[1:]

                    # Coerce header 0 to be 'Timestamp'
                    if column_names[0][0] != u'Timestamp':
                        column_names[0][0] = u'Timestamp'

                except IOError as sub_error:
                    self.logger.error(u"[{name}] Unable to load CSV data: {s}.".format(name=dev.name, s=sub_error))

                # ============================== Limit for Time ===============================
                # Limit data by time
                if delta > 0:
                    cut_off = dt.datetime.now() - dt.timedelta(hours=delta)
                    time_data = [row for row in data if date_parse(row[0]) >= cut_off]

                    # If all records are older than the delta, return the original data (so
                    # there's something to chart) and send a warning to the log.
                    if len(time_data) == 0:
                        self.logger.debug(u"[{name} - {cn}] all CSV data are older than the time limit. "
                                          u"Returning original data.".format(name=dev.name,
                                                                             cn=column_names[0][1].decode('utf-8')
                                                                             )
                                          )
                    else:
                        data = time_data

                # ============================ Add New Observation ============================
                # Determine if the thing to be written is a device or variable.
                try:
                    state_to_write = u""

                    if not v[1]:
                        self.logger.warning(u"Found CSV Data element with missing source ID. Please check to "
                                            u"ensure all CSV sources are properly configured.")

                    elif int(v[1]) in indigo.devices:
                        state_to_write = u"{states}".format(states=indigo.devices[int(v[1])].states[v[2]])

                    elif int(v[1]) in indigo.variables:
                        state_to_write = u"{vars}".format(vars=indigo.variables[int(v[1])].value)

                    else:
                        self.logger.critical(u"The settings for CSV Engine data element '{elm}' are not valid: "
                                             u"[dev: {dev}, state/value: {val}]".format(elm=v[0], dev=v[1], val=v[2]))

                    # Give matplotlib something it can chew on if the value to be saved is 'None'
                    if state_to_write in ('None', None, u""):
                        state_to_write = 'NaN'

                    # Add the newest observation to the end of the data list.
                    now = dt.datetime.strftime(cycle_time, '%Y-%m-%d %H:%M:%S.%f')
                    data.append([now, state_to_write])

                except ValueError as sub_error:
                    self.plugin_error_handler(sub_error=traceback.format_exc())
                    self.logger.error(u"[{name}] Invalid Indigo ID: {s}. See plugin log for more "
                                      u"information.".format(name=dev.name, s=sub_error))

                except Exception as sub_error:
                    self.plugin_error_handler(sub_error=traceback.format_exc())
                    self.logger.error(u"[{name}] Invalid CSV definition: {s}".format(name=dev.name, s=sub_error))

                # ============================= Limit for Length ==============================
                # The data frame (with the newest observation included) may now be too long.
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
                    self.plugin_error_handler(sub_error=traceback.format_exc())
                    self.logger.error(u"[{name}] Unable to delete backup file. {s}".format(name=dev.name, s=sub_error))

            dev.updateStatesOnServer([{'key': 'csvLastUpdated', 'value': u"{now}".format(now=dt.datetime.now())},
                                      {'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])

            self.logger.info(u"[{name}] CSV data updated successfully.".format(name=dev.name))
            dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

        except UnboundLocalError:
            self.logger.critical(u"[{name}] Unable to reach storage location. Check connections and "
                                 u"permissions.".format(name=dev.name))

        except ValueError as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.critical(u"[{name}] Error: {s}".format(name=dev.name, s=sub_error))

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.critical(u"[{name}] Error: {s}".format(name=dev.name, s=sub_error))

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
            csv_dict = ast.literal_eval(csv_dict_str)

            self.csv_refresh_process(dev=dev, csv_dict=csv_dict)

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
            temp_dict     = ast.literal_eval(dev.pluginProps['columnDict'])
            payload           = {target_source: temp_dict[target_source]}

            self.csv_refresh_process(dev=dev, csv_dict=payload)

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

        # Devices
        if values_dict.get('addSourceFilter', 'A') == "D":
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{name}".format(name=dev.name))) for dev in indigo.devices.iter()]

        # Variables
        elif values_dict.get('addSourceFilter', 'A') == "V":
            [list_.append(t) for t in [(u"-3", u"%%separator%%"),
                                       (u"-4", u"%%disabled:Variables%%"),
                                       (u"-5", u"%%separator%%")
                                       ]
             ]
            [list_.append((var.id, u"{name}".format(name=var.name))) for var in indigo.variables.iter()]

        # Devices and variables
        else:
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{name}".format(name=dev.name))) for dev in indigo.devices.iter()]

            [list_.append(t) for t in [(u"-3", u"%%separator%%"),
                                       (u"-4", u"%%disabled:Variables%%"),
                                       (u"-5", u"%%separator%%")
                                       ]
             ]
            [list_.append((var.id, u"{name}".format(name=var.name))) for var in indigo.variables.iter()]

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

        # Devices
        if values_dict.get('editSourceFilter', 'A') == "D":
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{name}".format(name=dev.name))) for dev in indigo.devices.iter()]

        # Variables
        elif values_dict.get('editSourceFilter', 'A') == "V":
            [list_.append(t) for t in [(u"-3", u"%%separator%%"),
                                       (u"-4", u"%%disabled:Variables%%"),
                                       (u"-5", u"%%separator%%")
                                       ]
             ]
            [list_.append((var.id, u"{name}".format(name=var.name))) for var in indigo.variables.iter()]

        # Devices and variables
        else:
            [list_.append(t) for t in [(u"-1", u"%%disabled:Devices%%"), (u"-2", u"%%separator%%")]]
            [list_.append((dev.id, u"{name}".format(name=dev.name))) for dev in indigo.devices.iter()]

            [list_.append(t) for t in [(u"-3", u"%%separator%%"),
                                       (u"-4", u"%%disabled:Variables%%"),
                                       (u"-5", u"%%separator%%")
                                       ]
             ]
            [list_.append((var.id, u"{name}".format(name=var.name))) for var in indigo.variables.iter()]

        return list_

    # =============================================================================
    def get_csv_device_list(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of CSV Engine devices set to manual refresh
        The get_csv_device_list() method returns a list of CSV Engine devices with a
        manual refresh interval.
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param target_id:
        :return:
        """

        # Return a list of tuples that contains only CSV devices set to manual refresh
        # (refreshInterval = 0) for config menu.
        return [(dev.id, dev.name) for dev in indigo.devices.iter("self") if
                dev.deviceTypeId == "csvEngine" and dev.pluginProps['refreshInterval'] == "0"]

    # =============================================================================
    def get_csv_source_list(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of CSV sources from CSV Engine devices set to manual refresh
        The get_csv_source_list() method returns a list of CSV sources for the target
        CSV Engine device.
        :param unicode fltr:
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
            dev_dict      = ast.literal_eval(dev.pluginProps['columnDict'])

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
    def fix_rgb(self, color):

        return r"#{c}".format(c=color.replace(' ', '').replace('#', ''))

    # =============================================================================
    def format_markers(self, p_dict):
        """
        Format matplotlib markers
        The Devices.xml file cannot contain '<' or '>' as a value, as this conflicts
        with the construction of the XML code. Matplotlib needs these values for
        select built-in marker styles, so we need to change them to what MPL is
        expecting.
        -----
        :param p_dict:
        """

        markers     = ('area1Marker', 'area2Marker', 'area3Marker', 'area4Marker', 'area5Marker', 'area6Marker',
                       'area7Marker', 'area8Marker', 'line1Marker', 'line2Marker', 'line3Marker', 'line4Marker',
                       'line5Marker', 'line6Marker', 'line7Marker', 'line8Marker', 'group1Marker', 'group2Marker',
                       'group3Marker', 'group4Marker')
        marker_dict = {"PIX": ",", "TL": "<", "TR": ">"}

        for marker in markers:
            try:
                if p_dict[marker] in marker_dict.keys():
                    p_dict[marker] = marker_dict[p_dict[marker]]

            except KeyError:
                pass

        return p_dict

    # =============================================================================
    def generatorDeviceStates(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Returns device states list or variable 'value'.

        Returns a list of device states or 'value' for a variable, based on ID
        transmitted in the filter attribute. The generatorDeviceStates() method
        returns a list of device states each list includes only states for the
        selected device. If a variable id is provided, the list returns one
        element. The lists are generated in the DLFramework module.

        Returns:
          [('dev state name', 'dev state name'), ('dev state name', 'dev state name')]
        or
          [('value', 'value')]
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """
        return self.Fogbert.generatorStateOrValue(values_dict[fltr])

    # =============================================================================
    def generatorDeviceList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of Indigo variables.
        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::
            [(dev.id, dev.name), (dev.id, dev.name)].
        The list is generated within the DLFramework module.
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.deviceList()

    # =============================================================================
    def latestDevVarList(self, fltr="", values_dict=None, type_id="", target_id=0):
        return self.dev_var_list

    # =============================================================================
    def generatorDeviceAndVariableList(self, fltr="", values_dict=None, type_id="", target_id=0):
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
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.deviceAndVariableList()

    # =============================================================================
    def generatorVariableList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of Indigo variables.
        Provides a list of Indigo variables for various dropdown menus. The method is
        agnostic as to whether the variable is enabled or disabled. The method returns
        a list of tuples in the form::
            [(var.id, var.name), (var.id, var.name)].
        The list is generated within the DLFramework module.
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        return self.Fogbert.variableList()

    # =============================================================================
    def getAxisList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Returns a list of axis formats.
        Returns a list of Python date formatting strings for use in plotting date
        labels.  The list does not include all Python format specifiers.
        -----
        :param str fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        now = dt.datetime.now()

        axis_list_menu = [("None", "None"),
                          ("-1", "%%separator%%"),
                          ("%I:%M", dt.datetime.strftime(now, "%I:%M") + ' (12 hour clock)'),
                          ("%H:%M", dt.datetime.strftime(now, "%H:%M") + ' (24 hour clock)'),
                          ("%l:%M %p", dt.datetime.strftime(now, "%l:%M %p").strip() + ' (full time)'),
                          ("%a", dt.datetime.strftime(now, "%a") + ' (short day)'),
                          ("%A", dt.datetime.strftime(now, "%A") + ' (long day)*'),
                          ("%b", dt.datetime.strftime(now, "%b") + ' (short month)'),
                          ("%B", dt.datetime.strftime(now, "%B") + ' (long month)'),
                          ("%d", dt.datetime.strftime(now, "%d") + ' (date)'),
                          ("%Y", dt.datetime.strftime(now, "%Y") + ' (year)'),
                          ("%b %d", dt.datetime.strftime(now, "%b %d") + ' (month date)'),
                          ("%d %b", dt.datetime.strftime(now, "%d %b") + ' (date month)'),
                          ("%y %b", dt.datetime.strftime(now, "%b %y") + ' (month year)'),
                          ("%y %b", dt.datetime.strftime(now, "%y %b") + ' (year month)'),
                          ("%b %d %Y", dt.datetime.strftime(now, "%b %d %Y") + ' (full date)'),
                          ("%Y %b %d", dt.datetime.strftime(now, "%Y %b %d") + ' (full date)')]

        return axis_list_menu

    # =============================================================================
    def getBatteryDeviceList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Create a list of battery-powered devices
        Creates a list of tuples that contains the device ID and device name of all
        Indigo devices that report a batterLevel device property that is not None.
        If no devices meet the criteria, a single tuple is returned as a place-
        holder.
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        batt_list = [(dev.id, dev.name) for dev in indigo.devices.iter() if dev.batteryLevel is not None]

        if len(batt_list) == 0:
            batt_list = [(-1, 'No battery devices detected.'), ]

        return batt_list

# =============================================================================
    def getFileList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Get list of CSV files for various dropdown menus.
        Generates a list of CSV source files that are located in the folder specified
        within the plugin configuration dialog. If the method is unable to find any CSV
        files, an empty list is returned.
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        file_name_list_menu = []
        default_path = '{path}/com.fogbert.indigoplugin.matplotlib/'.format(path=indigo.server.getLogsFolderPath())
        source_path = self.pluginPrefs.get('dataPath', default_path)

        try:
            import glob
            import os

            for file_name in glob.glob(u"{path}{fn}".format(path=source_path, fn='*.csv')):
                final_filename = os.path.basename(file_name)
                file_name_list_menu.append((final_filename, final_filename[:-4]))

            # Sort the file list
            file_name_list_menu = sorted(file_name_list_menu, key=lambda s: s[0].lower())  # Case insensitive sort

            # Add 'None' as an option, and show it first in list
            file_name_list_menu = file_name_list_menu + [(u"-5", u"%%separator%%"), (u"None", u"None")]

        except IOError as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"Error generating file list: {s}. See plugin log for more "
                              u"information.".format(s=sub_error))

        # return sorted(file_name_list_menu, key=lambda s: s[0].lower())  # Case insensitive sort
        return file_name_list_menu

    # =============================================================================
    def getFontList(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Provide a list of font names for various dropdown menus.
        Note that these are the fonts that Matplotlib can see, not necessarily all of
        the fonts installed on the system. If matplotlib can't find any fonts, then a
        default list of fonts that matplotlib supports natively are provided.
        -----
        :param unicode fltr:
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
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"Error building font list.  Returning generic list. {s}. See plugin log for more "
                              u"information.".format(s=sub_error))

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
    def getForecastSource(self, fltr="", values_dict=None, type_id="", target_id=0):
        """
        Return a list of WUnderground devices for forecast chart devices
        Generates and returns a list of potential forecast devices for the forecast
        devices type. Presently, the plugin only works with WUnderground devices, but
        the intention is to expand the list of compatible devices going forward.
        -----
        :param unicode fltr:
        :param class 'indigo.Dict' values_dict:
        :param unicode type_id:
        :param int target_id:
        """

        forecast_source_menu = []

        # We accept both WUnderground (legacy) and Fantastic Weather devices. We have to
        # construct these one at a time. Note the typo in the bundle identifier is correct.
        try:
            for dev in indigo.devices.itervalues("com.fogbert.indigoplugin.fantasticwWeather"):
                if dev.deviceTypeId in ('Daily', 'Hourly'):
                    forecast_source_menu.append((dev.id, dev.name))

            for dev in indigo.devices.itervalues("com.fogbert.indigoplugin.wunderground"):
                if dev.deviceTypeId in ('wundergroundTenDay', 'wundergroundHourly'):
                    forecast_source_menu.append((dev.id, dev.name))

        except Exception as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.error(u"Error getting list of forecast devices: {s}. See plugin log for more "
                              u"information.".format(s=sub_error))

        self.logger.threaddebug(u"Forecast device list generated successfully: {fsm}".format(fsm=forecast_source_menu))
        self.logger.threaddebug(u"forecast_source_menu: {fsm}".format(fsm=forecast_source_menu))

        return sorted(forecast_source_menu, key=lambda s: s[1].lower())

    # =============================================================================
    def plotActionApi(self, plugin_action, dev=None, caller_waiting_for_result=False):
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
        self.logger.info(u"Scripting payload: {pyld}".format(pyld=dict(plugin_action.props)))

        # TODO: take a look at broadcast messages and whether this is something else that can be made to
        #       work in this neighborhood.
        # TODO: this worked well up until where the "real" device would get its data.
        #       Need to make the API shim device work with existing get data steps.
        # # Instantiate an instance of an ApiDevice for data from the API call.
        # my_device = ApiDevice()
        #
        # # =============================  Unpack Payload  ==============================
        # # Take payload data from action and parse it into API device attributes.
        # my_device.apiXvalues   = plugin_action.props['x_values']
        # my_device.apiYvalues   = plugin_action.props['y_values']
        # my_device.apiKwargs    = plugin_action.props['kwargs']
        # my_device.path_name    = plugin_action.props['path']
        # my_device.apiFileName  = plugin_action.props['filename']
        # my_device.deviceTypeId = plugin_action.props['deviceTypeId']
        #
        # # ======================  Obtain All Plugin Preferences  ======================
        # # Take plugin prefs and parse them into API device attributes.
        # my_device.globalProps = self.pluginPrefs
        #
        # # ==================  Obtain All Properties for Device Type  ==================
        # # Take device type properties and parse them into API device attributes.
        #
        # # Get the config XML for the chart device type
        # props = self.devicesTypeDict[my_device.deviceTypeId]["ConfigUIRawXml"]
        # root  = eTree.ElementTree(eTree.fromstring(props))
        #
        # # Extract all field ids and defaultValues from XML
        # for type_tag in root.findall('Field'):
        #     field_id        = type_tag.get('id')
        #     default_value   = type_tag.get('defaultValue')
        #     if field_id not in my_device.globalProps.keys():
        #         my_device.globalProps[field_id] = default_value
        #
        # # Call for chart to be produced.
        # self.charts_refresh(dev_list=[my_device])

        dpi          = int(self.pluginPrefs.get('chartResolution', 100))
        height       = float(self.pluginPrefs.get('rectChartHeight', 250))
        width        = float(self.pluginPrefs.get('rectChartWidth', 600))
        face_color   = self.pluginPrefs.get('faceColor', '#000000')
        bk_color     = self.pluginPrefs.get('backgroundColor', '#000000')

        # =============================  Unpack Payload  ==============================
        x_values = plugin_action.props['x_values']
        y_values = plugin_action.props['y_values']
        kwargs = plugin_action.props['kwargs']
        path_name = plugin_action.props['path']
        file_name = plugin_action.props['filename']

        try:
            fig = plt.figure(1, figsize=(width / dpi, height / dpi))
            ax = fig.add_subplot(111)
            ax.patch.set_facecolor(face_color)
            ax.plot(x_values, y_values, **kwargs)
            plt.savefig(u"{path}{fn}".format(path=path_name, fn=file_name),
                        facecolor=bk_color,
                        dpi=dpi)
            plt.clf()
            plt.close('all')

        except Exception as sub_error:
            if caller_waiting_for_result:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(u"[{name}] Error: {fn}. See plugin log for more "
                                  u"information.".format(name=dev.name, fn=sub_error))
                return {'success': False, 'message': u"{s}".format(s=sub_error)}

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
            if dev.pluginProps.get('isChart', False):
                chart_devices += 1
            elif dev.deviceTypeId == 'csvEngine':
                csv_engines += 1

        self.logger.info(u"")
        self.logger.info(u"{0:{1}^135}".format(" Matplotlib Environment ", "="))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib version:", plt.matplotlib.__version__))
        self.logger.info(u"{0:<31} {1}".format("Numpy version:", np.__version__))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib RC Path:", plt.matplotlib.matplotlib_fname()))
        log_path = indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin log location:", log_path))
        self.logger.info(u"{0:<31} {1}".format("Number of Chart Devices:", chart_devices))
        self.logger.info(u"{0:<31} {1}".format("Number of CSV Engine Devices:", csv_engines))
        # rcParams is a dict containing all of the initial matplotlibrc settings
        self.logger.threaddebug(u"{0:<31} {1}".format("Matplotlib base rcParams:", dict(rcParams)))
        self.logger.threaddebug(u"{0:<31} {1}".format('Initial Plugin Prefs:', dict(self.pluginPrefs)))
        self.logger.info(u"{0:{1}^135}".format("", "="))

    # =============================================================================
    def plugin_error_handler(self, sub_error):
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
            self.logger.critical(u"!!! {ln}".format(ln=line))

        self.logger.critical(u"!" * 80)

    # =============================================================================
    def process_plotting_log(self, device, replies, errors):
        """
        Process output of multiprocessing queue messages
        The processLogQueue() method accepts a multiprocessing queue that contains log
        messages. The method parses those messages across the various self.logger.
        calls.
        -----
        :param indigo.Device device:
        :param str replies:
        :param unicode errors:
        """

        # ======================= Process Output Queue ========================
        try:
            replies = pickle.loads(replies)
            success = True

            for msg in replies['Threaddebug']:
                self.logger.threaddebug(msg)
            for msg in replies['Debug']:
                self.logger.debug(msg)
            for msg in replies['Info']:
                self.logger.info(msg)
            for msg in replies['Warning']:
                self.logger.warning(msg)
            for msg in replies['Critical']:
                self.logger.critical(msg)
                success = False

            if not success:
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
                self.logger.critical(u"[{name}] error producing chart. See logs for more "
                                     u"information.".format(name=device.name))
            else:
                device.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                self.logger.info(u"[{name}] chart refreshed.".format(name=device.name))

            return success

        except EOFError:
            pass

        # Process any special output.
        if len(errors) > 0:
            if "FutureWarning: " in errors:
                self.logger.threaddebug(errors)

            elif "'numpy.float64' object cannot be interpreted as an index" in errors:
                self.logger.critical(u"[{n}] Unfortunately, your version of Matplotlib doesn't support "
                                     u"Polar chart plotting. Disabling device.".format(n=device.name))
                indigo.device.enable(device, False)

            else:
                self.logger.critical(errors)
                device.updateStateImageOnServer(indigo.kStateImageSel.Error)

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
        self.charts_refresh(dev_list=[dev])
        self.logger.info(u"{0:{1}^80}".format(u' Redraw a Chart Action Complete ', '='))

    # =============================================================================
    def refresh_the_charts_now(self, values_dict, menu_id):
        """
        Refresh all enabled charts
        Refresh all enabled charts based on some user action (like an Indigo menu
        call).
        -----
        :return:
        """
        self.skipRefreshDateUpdate = True

        # Skip charts set to manual updates
        if values_dict['allCharts'] == 'auto':
            devices_to_refresh = [dev for dev in indigo.devices.itervalues('self') if
                                  dev.enabled and dev.deviceTypeId != 'csvEngine' and
                                  int(dev.ownerProps.get('refreshInterval', "0")) > 0]
            self.logger.info(u"Redraw Charts Now: Skipping manual charts.")

        # Refresh all charts regardless
        else:
            devices_to_refresh = [dev for dev in indigo.devices.itervalues('self') if
                                  dev.enabled and dev.deviceTypeId != 'csvEngine']
            self.logger.info(u"Redraw Charts Now: Redrawing all charts.")

        # Put the request in the queue
        self.refresh_queue.put(devices_to_refresh)
        return True, values_dict

    # =============================================================================
    def refresh_the_charts_queue(self):
        """Create and manage the queue for chart updates"""

        def work_the_refresh_queue():
            while not self.refresh_queue.empty():
                queue_dev = self.refresh_queue.get()
                self.charts_refresh(queue_dev)

        t = threading.Thread(target=work_the_refresh_queue(), args=())
        t.daemon = True
        t.start()

    # =============================================================================
    def save_snapshot(self, action=None):
        """Save a snapshot of select plugin information to disk for later debugging."""
        home = os.path.expanduser("~")
        with open(home + "/matplotlib_snapshot.txt", 'w') as outfile:
            outfile.write(u"{0:50} - {1}\n".format("pluginPrefs", dict(self.pluginPrefs)))
            outfile.write(u"{0:50} - {1}\n".format("rcParams", rcParams))

            for dev in indigo.devices.iter(filter="self"):
                outfile.write(u"{0:50} - {1}\n".format(dev.name, dict(dev.ownerProps)))

        indigo.server.log(u'Snapshot written to user home directory.')  # Write to log regardless of plugin debug level.

    def themeNameGenerator(self, fltr="", values_dict=None, type_id="", target_id=0):
        """Generate a list of theme names from the json file for UI controls"""
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        with open(full_path, 'r') as f:
            infile = json.load(f)

        self.logger.debug(u"themeNameGenerator: infile.keys() = {}".format(infile.keys()))
        return [(key, key) for key in sorted(infile.keys())]

    def themeManagerCloseUi(self, values_dict=None, menu_item_id="", foo=None):
        """Apply theme settings when user closes Theme Manager dialog"""
        # Don't need to trap user cancel since this callback won't be called
        # if user cancels. There is no way to trap the cancel.

        # ==========================  Apply Theme Settings  ===========================
        for key in ['backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther', 'fontColor',
                    'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle', 'legendFontSize',
                    'lineWeight', 'mainFontSize', 'spineColor', 'tickColor', 'tickFontSize', 'tickSize']:
            self.pluginPrefs[key] = values_dict[key]

        return True

    # =============================================================================
    def themeApplyAction(self, plugin_action):
        """Process the Indigo Apply Theme action item"""
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        selected_theme = plugin_action.props['targetTheme']

        # ==============================  Get the Theme  ==============================
        with open(full_path, 'r') as f:
            infile = json.load(f)

        # ======================  Confirm Theme is Still Valid  =======================
        if selected_theme not in infile.keys():
            self.logger.warning(u"Cannot change theme. Selected theme no longer valid.")
            return

        # =============================  Apply the Theme  =============================
        for key in infile[selected_theme]:
            self.pluginPrefs[key] = infile[selected_theme][key]

        self.logger.info(u"[{}] theme applied.".format(selected_theme))

    # =============================================================================
    def themeApply(self, values_dict, menu_item_id):
        """Process the Theme Manager Apply Theme action"""
        error_msg_dict = indigo.Dict()
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        selected_theme = values_dict['allThemes']

        # ===============================  Validation  ================================
        if len(selected_theme) == 0:
            error_msg_dict['allThemes'] = u"You must select a theme to apply."
            error_msg_dict['showAlertText'] = u"You must select a theme to apply."
            return values_dict, error_msg_dict

        if len(selected_theme) > 1:
            error_msg_dict['allThemes'] = u"You can only select one theme to apply."
            error_msg_dict['showAlertText'] = u"You can only select one theme to apply."
            return values_dict, error_msg_dict

        # ==========================  Apply Selected Theme  ===========================
        # Get existing themes
        with open(full_path, 'r') as f:
            infile = json.load(f)

        for key in infile[selected_theme[0]]:
            values_dict[key] = infile[selected_theme[0]][key]
            self.pluginPrefs[key] = infile[selected_theme[0]][key]

        # ======================  Reset Theme Manager Controls  =======================
        values_dict['allThemes'] = ""
        values_dict['menu'] = 'select'
        return values_dict

    # =============================================================================
    def themeExecuteActionButton(self, values_dict, menu_item_id):
        """Process the Theme Manager Execute Action button press"""
        error_msg_dict = indigo.Dict()
        result = None

        # ===============================  Validation  ================================
        if values_dict['menu'] == 'select':
            error_msg_dict['menu'] = u"You must select an action to execute."
            error_msg_dict['showAlertText'] = u"You must select an action to execute."
            return values_dict, error_msg_dict

        # ==================  Execute Selected Theme Manager Action  ==================
        if values_dict['menu'] == 'apply':
            result = self.themeApply(values_dict, menu_item_id)
        elif values_dict['menu'] == 'delete':
            result = self.themeDelete(values_dict, menu_item_id)
        elif values_dict['menu'] == 'rename':
            result = self.themeRename(values_dict, menu_item_id)
        elif values_dict['menu'] == 'save':
            values_dict['allThemes'] = "select"
            result = self.themeSave(values_dict, menu_item_id)

        return result

    # =============================================================================
    def themeRename(self, values_dict, menu_item_id):
        """Process the Theme Manager Rename Theme action"""
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        old_name = values_dict['allThemes']
        new_name = values_dict['newThemeName']
        error_msg_dict = indigo.Dict()

        # ===============================  Validation  ================================
        if len(old_name) == 0:
            error_msg_dict['allThemes'] = u"You must select a theme to rename."
            error_msg_dict['showAlertText'] = u"You must select a theme to rename."
            return values_dict, error_msg_dict

        if len(old_name) > 1:
            error_msg_dict['allThemes'] = u"You must select only one theme to rename."
            error_msg_dict['showAlertText'] = u"You must select only one theme to rename."
            return values_dict, error_msg_dict

        if len(old_name) == 1 and len(new_name) == 0:
            error_msg_dict['newThemeName'] = u"You must enter a new theme name."
            error_msg_dict['showAlertText'] = u"You must enter a new theme name."
            return values_dict, error_msg_dict

        # Get existing themes
        with open(full_path, 'r') as f:
            infile = json.load(f)

        infile[new_name] = infile[old_name[0]]
        del infile[old_name[0]]

        # Write theme dict to file.
        with open(full_path, 'w') as f:
            json.dump(infile, f, indent=4, sort_keys=True)

        values_dict['menu'] = 'select'
        return values_dict

    # =============================================================================
    def themeSave(self, values_dict, menu_item_id):
        """Process the Theme Manager Save Theme action"""
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        new_theme_name = values_dict['newTheme']
        error_msg_dict = indigo.Dict()

        # ===========================  Get existing Themes  ===========================
        with open(full_path, 'r') as f:
            infile = json.load(f)

        # ===============================  Validation  ================================
        # Save name blank
        if values_dict['newTheme'] == "":
            error_msg_dict['newTheme'] = u"You must specify a theme name."
            error_msg_dict['showAlertText'] = u"You must specify a theme name."
            return values_dict, error_msg_dict

        # Save name already used
        if values_dict['newTheme'] in infile.keys():
            error_msg_dict['newTheme'] = u"You must specify a unique name."
            error_msg_dict['showAlertText'] = u"You must specify a unique name."
            return values_dict, error_msg_dict

        infile[new_theme_name] = {}

        # Populate the theme dict
        for key in self.pluginPrefs:
            if key in ['backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther', 'fontColor',
                       'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle', 'legendFontSize',
                       'lineWeight', 'mainFontSize', 'spineColor', 'tickColor', 'tickFontSize', 'tickSize']:
                # infile[new_theme_name][key] = self.pluginPrefs[key]
                infile[new_theme_name][key] = values_dict[key]

        # Write theme dict to file.
        with open(full_path, 'w') as f:
            json.dump(infile, f, indent=4, sort_keys=True)

        # Reset field
        values_dict['newTheme'] = ""
        values_dict['menu'] = 'select'
        return values_dict

    # =============================================================================
    def themeDelete(self, values_dict, menu_item_id):
        """Process the Theme Manager Delete Theme action"""
        full_path = indigo.server.getInstallFolderPath() + "/Preferences/Plugins/matplotlib plugin themes.json"
        del_theme_name = [name for name in values_dict['allThemes']]
        error_msg_dict = indigo.Dict()

        # ===============================  Validation  ================================
        if len(del_theme_name) == 0:
            error_msg_dict['allThemes'] = u"You must select at least one theme to delete."
            error_msg_dict['showAlertText'] = u"You must select at least one theme to delete."
            return values_dict, error_msg_dict

        # Get existing themes
        with open(full_path, 'r') as f:
            infile = json.load(f)

        for name in del_theme_name:
            del infile[name]

        # Write theme dict to file.
        with open(full_path, 'w') as f:
            json.dump(infile, f, indent=4, sort_keys=True)

        values_dict['menu'] = 'select'
        return values_dict

    # =============================================================================


class MakeChart(object):

    def __init__(self):
        self.final_data = []

        base = indigo.server.getInstallFolderPath()
        path = base + "/Logs/com.fogbert.indigoplugin.matplotlib/"
        logging.basicConfig(filename='{path}process.log'.format(path=path), level=logging.INFO)

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
    def eval_(self, mode):
        operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow,
                     ast.BitXor: op.xor, ast.USub: op.neg}

        if isinstance(mode, ast.Num):  # <number>
            return mode.n
        elif isinstance(mode, ast.BinOp):  # <left> <operator> <right>
            return operators[type(mode.op)](self.eval_(mode.left), self.eval_(mode.right))
        elif isinstance(mode, ast.UnaryOp):  # <operator> <operand> e.g., -1
            return operators[type(mode.op)](self.eval_(mode.operand))
        else:
            raise TypeError(mode)


class ApiDevice(object):

    def __init__(self):
        self.configured = True
        self.deviceTypeId = ''  # areaChartingDevice, lineChartingDevice, etc.
        self.enabled = True
        self.errorState = False
        self.globalProps = indigo.Dict()
        self.id = -1
        self.lastChanged = ""
        self.lastSuccessfulComm = ""
        self.model = "API Device"
        self.name = 'Matplotlib Plugin API Device'
        self.pluginId = "com.fogbert.indigoplugin.matplotlib"
        self.pluginProps = self.globalProps

        self.states = indigo.Dict()
        self.states['chartLastUpdated'] = ""
        self.states['onOffState'] = ""

        # Attributes to hold payload data
        self.apiXvalues  = []
        self.apiYvalues  = []
        self.apiKwargs   = {}
        self.apiPathName = ""
        self.apiFileName = ""

    @staticmethod
    def __doc__(self):
        return "A Matplotlib Plugin API shim device. Used to pass scripting payload to the " \
               "plugin by simulating a built-in device type. See Plugin Wiki for more information."

    def __str__(self):
        """ Meant to mimic a standard Indigo device doc as much as possible"""
        output = ""
        for key in self.__dict__.keys():
            value = self.__dict__[key]
            output += u"\n{0} : {1}".format(key, value)
        return output

    # def __del__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __delattr__(self, item):
    #     """[built-in method]"""
    #     del self.__dict__[item]
    #
    # def __dir__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __format__(self, format_spec):
    #     """[built-in method]"""
    #     pass
    #
    # def __getattribute__(self, item):
    #     """[built-in method]"""
    #     pass
    #
    # def __hash__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __module__(self):
    #     """[Indigo custom attr?]"""
    #     pass
    #
    # def __new__(cls, *args, **kwargs):
    #     """[built-in method]"""
    #     pass
    #
    # def __reduce__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __reduce_ex__(self, protocol):
    #     """[built-in method]"""
    #     pass
    #
    # def __repr__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __setattr__(self, key, value):
    #     """[built-in method]"""
    #     pass
    #
    # def __sizeof__(self):
    #     """[built-in method]"""
    #     pass
    #
    # def __subclasshook__(self):
    #     pass
    #
    # def __weakref__(self):
    #     pass
    # =============================================================================

    # =============================  Custom Methods  ==============================
    def updateStateOnServer(self, item):
        indigo.server.log(u"updateStateOnServer: {0}".format(item))

    def updateStatesOnServer(self, item):
        # Update object attributes based on item payload. Item is a list of dicts
        # {'key': k, 'value': v, 'uiValue': uiv}
        for thing in item:
            self.states[thing['key']] = thing['value']

    def updateStateImageOnServer(self, item):
        indigo.server.log(u"updateStateImageOnServer: {0}".format(item))
    # =============================================================================
