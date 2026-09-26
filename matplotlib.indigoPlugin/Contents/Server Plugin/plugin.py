# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
matplotlib plugin
author: DaveL17

The matplotlib plugin is used to produce various types of charts and graphics for use on Indigo control pages. The key
benefits of the plugin are its ability to make global changes to all generated charts (i.e., fonts, colors) and its
relative simplicity. It contains direct support for some automated charts (for example, it can create Fantastic Weather
plugin forecast charts if linked to the proper Fantastic Weather devices).
"""

# =================================== Notes ===================================
# We run each plot update in its own process to isolate resources and prevent any potential memory accumulation over
# long-running sessions.

# ================================== IMPORTS ==================================
# Built-in modules
import ast
import copy
import json
import logging
import os
import subprocess
import threading
import traceback
from typing import Any, Tuple, Union
import datetime as dt
from queue import Queue
import numpy as np
from dateutil.parser import parse as date_parse

import matplotlib
# Note: this statement must be run before any other matplotlib imports are done.
matplotlib.use('AGG')
from matplotlib import pyplot as plt          # noqa
from matplotlib import rcParams               # noqa

try:
    import indigo  # noqa
except ImportError:
    ...

# My modules
import DLFramework.DLFramework as Dave                     # noqa
import audits                                               # noqa
import color_utils                                          # noqa
import csv_handling                                         # noqa
import maintenance                                         # noqa
import theme_handling                                       # noqa
import ui_lists                                             # noqa
import validate                                            # noqa
from constants import DEBUG_LABELS  # noqa
from plugin_defaults import kDefaultPluginPrefs            # noqa

# =================================== HEADER ==================================
__author__    = Dave.__author__
__copyright__ = Dave.__copyright__
__license__   = Dave.__license__
__build__     = Dave.__build__
__title__     = "Matplotlib Plugin for Indigo"
__version__   = "2025.2.6"


# =============================================================================
class Plugin(indigo.PluginBase):
    """The main Indigo plugin class for the Matplotlib plugin.

    Manages chart devices, CSV engine devices, plugin preferences, and all Indigo-framework callbacks.
    Provides chart rendering by dispatching subprocess scripts and handling their output.
    """

    def __init__(self, plugin_id: str = "", plugin_display_name: str = "", plugin_version: str = "", plugin_prefs: indigo.Dict = None):  # noqa
        """Initialize the Plugin instance and set up logging and framework objects.

        Args:
            plugin_id (str): The Indigo plugin bundle identifier.
            plugin_display_name (str): The human-readable plugin name.
            plugin_version (str): The plugin version string.
            plugin_prefs (indigo.Dict): The persisted plugin preferences dictionary.
        """
        super().__init__(plugin_id, plugin_display_name, plugin_version, plugin_prefs)

        # ============================ Instance Attributes =============================
        self.pluginIsInitializing: bool  = True   # Flag signaling that __init__ is in process
        self.pluginIsShuttingDown: bool  = False  # Flag signaling that the plugin is shutting down.
        self.skipRefreshDateUpdate: bool = False  # Flag that we have called for a manual chart refresh
        # List of devices and variables (updated in getDeviceConfigUiValues)
        self.dev_var_list: list          = []
        self.refresh_queue: Queue        = Queue()
        self.debug_level: int            = int(plugin_prefs.get('showDebugLevel', "30"))

        # ========================== Initialize DLFramework ===========================
        self.Fogbert  = Dave.Fogbert(self)           # Plugin functional framework
        self.maintain = maintenance.Maintain(self)  # Maintenance of plugin props and device prefs

        # ============================= Initialize Logger =============================
        self.plugin_file_handler.setFormatter(logging.Formatter(Dave.LOG_FORMAT, datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug_level = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debug_level)

        # Set private log handler based on plugin preference
        if self.pluginPrefs.get('verboseLogging', False):
            self.plugin_file_handler.setLevel(5)
            self.logger.warning("Verbose logging is on. It is best to leave this turned off unless directed.")
        else:
            self.plugin_file_handler.setLevel(10)

        self.pluginIsInitializing = False

    def log_plugin_environment(self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> None:
        """
        Log pluginEnvironment information when plugin is first started
        """
        self.Fogbert.pluginEnvironment()
        self.pluginEnvironmentLogger()

    # =============================================================================
    def __del__(self) -> None:
        """Destroy the Plugin instance and call the parent class destructor."""
        indigo.PluginBase.__del__(self)

    # =============================================================================
    # ============================== Indigo Methods ===============================
    # =============================================================================
    def closed_device_config_ui(self, values_dict: indigo.Dict = None, user_cancelled: bool = False, type_id: str = "", dev_id: int = 0) -> bool:  # noqa
        """Handle cleanup when a device configuration dialog is closed.

        Logs the final values_dict if the user confirmed, or a cancellation message if the user
        canceled. If the device is fully configured and is a chart device type, queues a chart
        refresh.

        Args:
            values_dict (indigo.Dict): The configuration values from the dialog.
            user_cancelled (bool): True if the user canceled the dialog without saving.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            bool: Always True.
        """
        dev = indigo.devices[dev_id]

        if not user_cancelled:
            self.logger.threaddebug("[%s] Final device values_dict: %s", dev.name, values_dict)
            self.logger.threaddebug("Configuration complete.")
        else:
            self.logger.threaddebug("User cancelled.")

        if dev.configured and dev.deviceTypeId not in ("rcParamsDevice", "csvEngine"):
            self.refresh_queue.put([dev])

        return True

    # =============================================================================
    def closed_prefs_config_ui(self, values_dict: indigo.Dict = None, user_cancelled: bool = False) -> dict:  # noqa
        """
        Standard Indigo method called when plugin preferences dialog is closed.

        :param indigo.Dict values_dict:
        :param bool user_cancelled:
        :return:
        """
        if not user_cancelled:
            # Ensure that self.pluginPrefs includes any recent changes.
            for k in values_dict:
                self.pluginPrefs[k] = values_dict[k]

            # Debug Logging
            self.debug_level = int(values_dict.get('showDebugLevel', "30"))
            self.indigo_log_handler.setLevel(self.debug_level)
            indigo.server.log(f"Logging Level: {DEBUG_LABELS[self.debug_level]} ({self.debug_level})")

            # Plugin-specific actions
            if values_dict['verboseLogging']:
                self.plugin_file_handler.setLevel(5)
                self.logger.warning("Verbose logging is on. It is best not to leave this turned on for very long.")
            else:
                self.plugin_file_handler.setLevel(self.debug_level)
                self.logger.info("Verbose logging is off.  It is best to leave this turned off unless directed.")

            self.logger.debug("Plugin prefs saved.")

        else:
            self.logger.debug("Plugin prefs cancelled.")

        return values_dict

    # =============================================================================
    def device_start_comm(self, dev: indigo.Device = None) -> None:  # noqa
        """Start communication with a chart device.

        Resets the plugin shutdown flag, cleans device properties to match the current plugin
        version, and updates the device state list and state image.

        Args:
            dev (indigo.Device): The Indigo device instance being started.
        """
        self.logger.debug("[%s] Starting chart device.", dev.name)
        # If we're coming here from a sleep state, we need to ensure that the plugin shutdown global is in its proper
        # state.
        self.pluginIsShuttingDown = False
        self.maintain.clean_props(dev)
        dev.stateListOrDisplayStateIdChanged()
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    @staticmethod
    def device_stop_comm(dev: indigo.Device = None) -> None:  # noqa
        """Stop communication with a chart device and update its state to show disabled.

        Args:
            dev (indigo.Device): The Indigo device instance being stopped.
        """
        dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    # =============================================================================
    def getActionConfigUiValues(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> dict:
        """Return pre-populated values for an action configuration dialog.

        For the 'themeApplyAction' type, returns values_dict unchanged. For all other action
        types, returns the full pluginPrefs dict if values_dict is empty, otherwise returns
        the existing values_dict.

        Args:
            values_dict (indigo.Dict): The current dialog values.
            type_id (str): The action type identifier string.
            dev_id (int): The Indigo device ID associated with the action.

        Returns:
            dict: The resolved values dictionary to populate the action dialog.
        """
        # ===========================  Apply Theme Action  ============================
        if type_id == "themeApplyAction":
            return values_dict

        # ==================================  Else  ===================================
        if len(values_dict) == 0:
            result = self.pluginPrefs
        else:
            result = values_dict

        return result

    # =============================================================================
    def getDeviceConfigUiValues(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> indigo.Dict:  # noqa
        """Return pre-populated values for a device configuration dialog.

        Handles special initialization for CSV Engine devices (resetting workflow fields) and
        ensures the dialog opens on the 'Chart Controls' settings group. For new (unconfigured)
        devices, sets per-type default values for colors, sources, and style preferences.

        Args:
            values_dict (indigo.Dict): The current device configuration values.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            indigo.Dict: The populated values dictionary, or a (True, values_dict) tuple on error.
        """
        dev = indigo.devices[int(dev_id)]
        self.dev_var_list = self.generatorDeviceAndVariableList()

        self.logger.threaddebug("[%s] Getting device config props: %s", dev.name, values_dict)

        try:

            # ===========================  CSV Engine Defaults  ===========================
            # Put certain props in a state that we expect when the config dialog is first opened. These settings are
            # regardless of whether the device has been initially configured or not.
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
            # Ensure that every time a device config dialog is opened, it reverts to the 'Chart Controls' settings
            # group.
            if 'settingsGroup' in values_dict:
                values_dict['settingsGroup'] = "ch"

            # ========================== Set Config UI Defaults ===========================
            # For new devices, force certain defaults in case they don't carry from Devices.xml. This seems to be
            # especially important for menu items built with callbacks and colorpicker controls that don't accept
            # defaultValue (Indigo version 7.5 adds support for colorpicker defaultValue).
            if not dev.configured:
                values_dict['refreshInterval'] = '900'

                # ============================ Line Charting Device ===========================
                if type_id == "areaChartingDevice":

                    for _ in range(1, 9, 1):
                        values_dict[f'area{_}Color']       = 'FF FF FF'
                        values_dict[f'area{_}Marker']      = 'None'
                        values_dict[f'area{_}MarkerColor'] = 'FF FF FF'
                        values_dict[f'area{_}Source']      = 'None'
                        values_dict[f'area{_}Style']       = '-'
                        values_dict[f'line{_}Color']       = 'FF FF FF'
                        values_dict[f'line{_}Style']       = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ================================  Flow Bar  =================================
                if type_id == "barChartingDevice":

                    for _ in range(1, 5, 1):
                        values_dict[f'bar{_}Color']  = 'FF FF FF'
                        values_dict[f'bar{_}Source'] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ================================  Stock Bar  ================================
                if type_id == "barStockChartingDevice":

                    for _ in range(1, 6, 1):
                        values_dict[f'bar{_}Color']  = 'FF FF FF'
                        values_dict[f'bar{_}Source'] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisLabelFormat']    = 'None'

                # ================================  Stock Bar H ===============================
                if type_id == "barStockHorizontalChartingDevice":

                    for _ in range(1, 6, 1):
                        values_dict[f'bar{_}Color']  = 'FF FF FF'
                        values_dict[f'bar{_}Source'] = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisLabelFormat']    = 'None'

                # ================================  Radial Bar ================================
                if type_id == "radialBarChartingDevice":

                    values_dict['bar_1']      = '00 FF 00'
                    values_dict['bar_2']      = '33 33 33'
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
                        values_dict[f'line{_}BestFit']      = False
                        values_dict[f'line{_}BestFitColor'] = 'FF 00 00'
                        values_dict[f'line{_}Color']        = 'FF FF FF'
                        values_dict[f'line{_}Marker']       = 'None'
                        values_dict[f'line{_}MarkerColor']  = 'FF FF FF'
                        values_dict[f'line{_}Source']       = 'None'
                        values_dict[f'line{_}Style']        = '-'

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
                        values_dict[f'line{_}BestFit']      = False
                        values_dict[f'line{_}BestFitColor'] = 'FF 00 00'
                        values_dict[f'group{_}Color']       = 'FF FF FF'
                        values_dict[f'group{_}Marker']      = '.'
                        values_dict[f'group{_}MarkerColor'] = 'FF FF FF'
                        values_dict[f'group{_}Source']      = 'None'

                    values_dict['customLineStyle']     = '-'
                    values_dict['customTickFontSize']  = 8
                    values_dict['customTitleFontSize'] = 10
                    values_dict['xAxisBins']           = 'daily'
                    values_dict['xAxisLabelFormat']    = '%A'

                # ========================== Weather Forecast Device ==========================
                if type_id == "forecastChartingDevice":

                    for _ in range(1, 3, 1):
                        values_dict[f'line{_}Marker']      = 'None'
                        values_dict[f'line{_}MarkerColor'] = 'FF FF FF'
                        values_dict[f'line{_}Style']       = '-'

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
                    self.logger.threaddebug("Enabling advanced feature: Custom Line Segments.")
                else:
                    values_dict['enableCustomLineSegmentsSetting'] = False

            return values_dict

        except KeyError as sub_error:
            self.plugin_error_handler(sub_error=traceback.format_exc())
            self.logger.warning("[%s] Error: %s. See plugin log for more information.", dev.name, sub_error)

        return True, values_dict

    # =============================================================================
    def getDeviceStateList(self, dev: indigo.Device = None) -> list:  # noqa
        """Return the list of device states for the given device.

        For rcParams devices, dynamically adds one string state for each matplotlib rcParams key
        (with '.' replaced by '_'). Also appends an 'onOffState' string state.

        Args:
            dev (indigo.Device): The Indigo device instance.

        Returns:
            list: The list of device state dictionaries for the device.
        """
        state_list = indigo.PluginBase.getDeviceStateList(self, dev)

        if dev.deviceTypeId == 'rcParamsDevice':
            for key in rcParams:
                key = key.replace('.', '_')  # Indigo state keys can not have '.' in them.
                if key.startswith("_"):
                    key = key[1:]
                dynamic_state = self.getDeviceStateDictForStringType(key, key, key)
                state_list.append(dynamic_state)
            state_list.append(self.getDeviceStateDictForStringType('onOffState', 'onOffState', 'onOffState'))

        return state_list

    # =============================================================================
    def getMenuActionConfigUiValues(self, menu_id: str = "") -> Tuple[indigo.Dict, indigo.Dict]:
        """Return pre-populated settings and an empty error dict for menu action dialogs.

        For the advanced settings menu, reads the relevant preference keys from pluginPrefs. For
        the Theme Manager menu, also reads the current theme-related preference values.

        Args:
            menu_id (str): The menu action identifier string.

        Returns:
            tuple: A two-element tuple of (settings indigo.Dict, error_msg_dict indigo.Dict).
        """
        settings       = indigo.Dict()
        error_msg_dict = indigo.Dict()

        self.logger.threaddebug("Getting menu action config prefs: %s", dict(settings))

        # =========================  Advanced Settings Menu  ==========================
        if menu_id not in ["refreshChartsNow", "themeManager"]:
            settings['enableCustomLineSegments']  = self.pluginPrefs.get('enableCustomLineSegments', False)
            settings['forceOriginLines'] = self.pluginPrefs.get('forceOriginLines', False)
            settings['promoteCustomLineSegments'] = self.pluginPrefs.get('promoteCustomLineSegments', False)
            settings['snappyConfigMenus'] = self.pluginPrefs.get('snappyConfigMenus', False)

        # ===========================  Theme Manager Menu  ============================
        # Open dialog with existing settings populated.
        if menu_id == "themeManager":
            for key in ['backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther',
                        'fontColor', 'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle',
                        'legendFontSize', 'lineWeight', 'mainFontSize', 'spineColor', 'tickColor',
                        'tickFontSize', 'tickSize'
                        ]:

                settings[key] = self.pluginPrefs.get(key, None)

        return settings, error_msg_dict

    # =============================================================================
    def getPrefsConfigUiValues(self) -> indigo.Dict:  # noqa
        """Return plugin preferences pre-populated with defaults for the preferences dialog.

        Reads the current pluginPrefs and fills in defaults for any missing color, font, and
        display preference keys. This is primarily needed the first time the plugin is configured.

        Returns:
            indigo.Dict: The plugin preferences dictionary with all required keys populated.
        """
        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        self.logger.threaddebug("Getting plugin Prefs: %s", dict(plugin_prefs))

        # Establish a set of defaults for select plugin settings. Only those settings that are populated dynamically
        # need to be set here (the others can be set directly by the XML.)
        defaults_dict = {
            'backgroundColor': '00 00 00',
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
        for key, value in defaults_dict.items():
            plugin_prefs[key] = plugin_prefs.get(key, value)

        return plugin_prefs

    # =============================================================================
    def runConcurrentThread(self) -> None:  # noqa
        """Run the plugin's main background loop.

        Checks the chart refresh queue, refreshes CSV engine data, and refreshes chart devices on
        each iteration. Sleeps 10 seconds between cycles. Runs until the plugin is shut down.
        """
        self.sleep(0.5)

        while True:
            if not self.pluginIsShuttingDown:
                self.refresh_the_charts_queue()  # check to see if anything is in the queue.
                self.csv_refresh()  # iterate plugin devices to see if any need updating.
                self.charts_refresh()  # refresh plugin devices that need updating.
                self.sleep(10)

    # =============================================================================
    @staticmethod
    def sendDevicePing(dev_id: int = 0, suppress_logging: bool = False) -> dict:  # noqa
        """Respond to a device ping request.

        Matplotlib plugin devices do not support the ping function. Logs an informational message
        and returns a Failure result.

        Args:
            dev_id (int): The Indigo device ID to ping.
            suppress_logging (bool): Whether to suppress logging output.

        Returns:
            dict: A result dictionary with key 'result' set to 'Failure'.
        """
        indigo.server.log("Matplotlib Plugin devices do not support the ping function.")
        return {'result': 'Failure'}

    # =============================================================================
    def startup(self) -> None:
        """Perform plugin startup tasks.

        Audits the Indigo server version compatibility, checks CSV filename uniqueness, audits CSV
        file health, audits device properties, audits chart and data save paths, and audits the
        themes file.
        """
        # =========================== Check Indigo Version ============================
        self.Fogbert.audit_server_version(min_ver=2022)

        # =========================== Check CSV Uniqueness ============================
        self.csv_check_unique()

        # ============================== Audit CSV Files ==============================
        self.audit_csv_health()

        # ============================ Audit Device Props =============================
        audits.audit_device_props(get_device_config_ui_xml=self.getDeviceConfigUiXml)

        # ============================= Audit Save Paths ==============================
        audits.audit_save_paths(prefs=self.pluginPrefs, vers_str_to_tuple=self.versStrToTuple)

        # ============================ Audit Theme Paths ==============================
        audits.audit_themes_file()

        # =========================== Audit Stylesheets ===========================
        audits.audit_stylesheets()

    # =============================================================================
    def shutdown(self) -> None:
        """Perform plugin shutdown tasks.

        Sets the pluginIsShuttingDown flag to True to halt the concurrent thread loop.
        """
        self.logger.threaddebug("Shutdown called.")
        self.pluginIsShuttingDown = True

    # =============================================================================
    def validatePrefsConfigUi(self, values_dict: indigo.Dict = None) -> Tuple[bool, indigo.Dict]:  # noqa
        """Validate the plugin preferences configuration dialog before saving.

        Validates data paths, chart colors, chart dimensions, chart resolution, and line weight.
        Logs any changed preference values. Sets the dpiWarningFlag to True on success.

        Args:
            values_dict (indigo.Dict): The preference values submitted from the dialog.

        Returns:
            tuple: (True, values_dict) on success, or (False, values_dict, error_msg_dict)
                if validation fails.
        """
        error_msg_dict = indigo.Dict()

        self.debug_level = int(values_dict.get('showDebugLevel', 30))
        self.indigo_log_handler.setLevel(self.debug_level)
        self.logger.threaddebug("Validating plugin configuration parameters.")

        # ================================ Data Paths =================================
        error_msg_dict = validate.data_paths(values_dict, error_msg_dict)

        # =============================== Chart Colors ================================
        validate.chart_colors(values_dict)

        # ============================= Chart Dimensions ==============================
        values_dict, error_msg_dict = validate.chart_dimensions(values_dict, error_msg_dict)

        # ============================= Chart Resolution ==============================
        values_dict, error_msg_dict = validate.chart_resolution(values_dict, error_msg_dict)

        # ================================ Line Weight ================================
        values_dict, error_msg_dict = validate.line_weight(values_dict, error_msg_dict)

        # ============================== There are errors ==============================
        if len(error_msg_dict) > 0:
            error_msg_dict['showAlertText'] = (
                "Configuration Errors\n\nThere are one or more settings that need to be corrected. Fields requiring "
                "attention will be highlighted."
            )
            return False, values_dict, error_msg_dict

        # ============================ There are no errors =============================
        else:
            # ============================== Log All Changes ==============================
            # Log any changes to the plugin preferences.
            changed_keys   = ()
            config_changed = False

            for key in values_dict:
                try:
                    if values_dict[key] != self.pluginPrefs[key]:
                        config_changed = True
                        changed_keys += ((f"{key}", f"Old: {self.pluginPrefs[key]}", f"New: {values_dict[key]}"),)

                # Missing keys will be config dialog format props like labels and separators
                except KeyError:
                    ...

            if config_changed:
                self.logger.threaddebug("values_dict changed: %s", changed_keys)

            values_dict['dpiWarningFlag'] = True
            self.logger.threaddebug("Preferences validated successfully.")
            return True, values_dict

    # =============================================================================
    def validateDeviceConfigUi(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> Tuple[bool, indigo.Dict, indigo.Dict]:  # noqa
        """Validate a device configuration dialog before saving.

        Applies device-type-specific validation (required sources, numeric values, axis limits,
        custom tick counts, etc.) and general validation across all chart types (custom dimensions,
        axis limit format and ordering).

        Args:
            values_dict (indigo.Dict): The device configuration values submitted from the dialog.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            tuple: (True, values_dict, error_msg_dict) on success, or
                (False, values_dict, error_msg_dict) if validation fails.
        """
        error_msg_dict = indigo.Dict()
        self.logger.threaddebug("Validating device configuration parameters.")

        # ================================ Area Chart =================================
        if type_id == 'areaChartingDevice':
            values_dict, error_msg_dict = validate.area_chart(values_dict, error_msg_dict)

        # ================================  Flow Bar  =================================
        if type_id == 'barChartingDevice':
            values_dict, error_msg_dict = validate.bar_flow_chart(values_dict, error_msg_dict)

        # ================================  Stock Bar  ================================
        if type_id == 'barStockChartingDevice':
            values_dict, error_msg_dict = validate.bar_stock_chart(values_dict, error_msg_dict)

        # ==========================  Stock Horizontal Bar  ===========================
        if type_id == 'barStockHorizontalChartingDevice':
            values_dict, error_msg_dict = validate.bar_stock_horizontal_chart(values_dict, error_msg_dict)

        # ===============================  Radial Bar  ================================
        if type_id == 'radialBarChartingDevice':

            # Must select at least one source (bar 1)
            if values_dict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = "You must select at least one data source."

            # See if the scale value will float.
            if values_dict['scale'].startswith('%%'):
                try:
                    float(self.substitute(values_dict['scale']))
                except ValueError:
                    error_msg_dict['scale'] = "The substitution field is not valid."

        # =========================== Battery Health Chart ============================
        if type_id == 'batteryHealthDevice':
            values_dict, error_msg_dict = validate.battery_health_chart(values_dict, error_msg_dict)

        # ============================== Calendar Chart ===============================
        # There are currently no unique validation steps needed for calendar devices
        if type_id == 'calendarChartingDevice':
            ...

        # ================================ CSV Engine =================================
        if type_id == 'csvEngine':
            values_dict, error_msg_dict = validate.csv_engine(values_dict, error_msg_dict)

        # ================================ Line Chart =================================
        if type_id == 'lineChartingDevice':
            values_dict, error_msg_dict = validate.line_chart(values_dict, error_msg_dict)

        # ============================== Multiline Text ===============================
        if type_id == 'multiLineText':
            values_dict, error_msg_dict = validate.multiline_text(values_dict, error_msg_dict)

        # ================================ Polar Chart ================================
        if type_id == 'polarChartingDevice':
            values_dict, error_msg_dict = validate.polar_chart(values_dict, error_msg_dict)

        # =============================== Scatter Chart ===============================
        if type_id == 'scatterChartingDevice':
            values_dict, error_msg_dict = validate.scatter_chart(values_dict, error_msg_dict)

        # =============================== Weather Chart ===============================
        if type_id == 'forecastChartingDevice':
            values_dict, error_msg_dict = validate.weather_forecast_chart(values_dict, error_msg_dict)

        # ========================== Composite Weather Chart ==========================
        if type_id == 'compositeForecastDevice':
            values_dict, error_msg_dict = validate.composite_weather_chart(values_dict, error_msg_dict)

        # ============================== All Chart Types ==============================
        # The following validation blocks are applied to all graphical chart device types.
        values_dict, error_msg_dict = validate.chart_custom_dimensions(values_dict, error_msg_dict)
        values_dict, error_msg_dict = validate.axis_limits(values_dict, error_msg_dict)

        if len(error_msg_dict) > 0:
            error_msg_dict['showAlertText'] = (
                "Configuration Errors\n\nThere are one or more settings that need to be corrected. Fields requiring "
                "attention will be highlighted."
            )
            return False, values_dict, error_msg_dict

        self.logger.threaddebug("Preferences validated successfully.")
        return True, values_dict, error_msg_dict

    # =============================================================================
    def validateMenuConfigUi(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> Tuple[bool, indigo.Dict]:  # noqa
        """Validate menu configuration dialog values and log the submitted payload.

        Args:
            values_dict (indigo.Dict): The menu configuration values submitted from the dialog.
            type_id (str): The menu type identifier string.
            dev_id (int): The Indigo device ID (if applicable).

        Returns:
            tuple: A two-element tuple of (True, values_dict).
        """
        self.logger.info("v: %s", values_dict)
        self.logger.info("t: %s", type_id)
        self.logger.info("d: %s", dev_id)
        return True, values_dict

    # =============================================================================
    def __log_dicts(self, dev: indigo.Device = None) -> None:
        """Write device plugin properties to the threaddebug log.

        A simple helper to log the device's pluginProps dict under verbose logging for
        troubleshooting chart rendering issues.

        Args:
            dev (indigo.Device): The Indigo device whose props will be logged.
        """
        self.logger.threaddebug("[%-19s] Props: %s", dev.name, dict(dev.pluginProps))

    # =============================================================================
    @staticmethod
    def dummyCallback(values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> None:  # noqa
        """Serve as a no-op callback to force configuration dialog refreshes.

        Provides a callback target for configuration dialog controls that use dynamicReload=True.
        Calling this method triggers Indigo to reload dynamic controls in the dialog.

        Args:
            values_dict (indigo.Dict): The current dialog values.
            type_id (str): The type identifier string.
            target_id (int): The target device or variable ID.
        """

    # =============================================================================
    def action_refresh_the_charts(self, plugin_action: Any) -> None:  # noqa
        """Refresh all enabled chart devices in response to an Indigo Action item.

        Sets the skipRefreshDateUpdate flag and calls charts_refresh() with all enabled non-CSV
        chart devices. Logs a completion banner when finished.

        Args:
            plugin_action: The Indigo plugin action instance (passed by Indigo).
        """
        self.skipRefreshDateUpdate = True
        devices_to_refresh = [dev for dev in indigo.devices.iter('self') if
                              dev.enabled and dev.deviceTypeId != 'csvEngine']

        self.charts_refresh(dev_list=devices_to_refresh)
        self.logger.info(f"{' Redraw All Charts Action Complete ':=^80}")

    # =============================================================================
    def advancedSettingsExecuted(self, values_dict: indigo.Dict = None, menu_id: int = 0) -> bool:  # noqa
        """Save advanced settings menu selections to pluginPrefs for permanent storage.

        Persists the custom line segments, promote custom line segments, snappy config menus, and
        force origin lines preferences from the advanced settings menu dialog. Note that values_dict
        here covers only menu values, not all plugin prefs.

        Args:
            values_dict (indigo.Dict): The advanced settings dialog values.
            menu_id (int): The menu identifier (passed by Indigo, not used directly).

        Returns:
            bool: Always True.
        """
        self.pluginPrefs['enableCustomLineSegments']  = values_dict['enableCustomLineSegments']
        self.pluginPrefs['promoteCustomLineSegments'] = values_dict['promoteCustomLineSegments']
        self.pluginPrefs['snappyConfigMenus']         = values_dict['snappyConfigMenus']
        self.pluginPrefs['forceOriginLines']          = values_dict['forceOriginLines']

        self.logger.threaddebug("Advanced settings menu final prefs: %s", dict(values_dict))
        return True

    # =============================================================================
    def advancedSettingsMenu(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> None:  # noqa
        """Log the current advanced settings menu selections at threaddebug level.

        Called when actions are taken within the Advanced Settings Menu item from the plugin menu.

        Args:
            values_dict (indigo.Dict): The advanced settings dialog values.
            type_id (str): The menu type identifier string.
            dev_id (int): The Indigo device ID (if applicable).
        """
        self.logger.threaddebug("Advanced settings menu final prefs: %s", dict(values_dict))

    # =============================================================================
    def audit_csv_health(self) -> None:
        """Create any missing CSV data files before the plugin begins normal operation.

        Iterates through all CSV Engine devices (enabled or disabled) and creates any missing CSV
        files in the configured data path. New files are initialized with a header row. Also
        creates the data directory if it does not yet exist.
        """
        csv_handling.audit_csv_health(prefs=self.pluginPrefs)

    # =============================================================================
    @staticmethod
    def chart_stock_bar(dev: indigo.Device = None) -> list:
        """Collect stock bar chart data from Indigo devices and variables.

        Iterates through up to five bar data sources configured on the device. Reads each value
        from the appropriate Indigo device state or variable, and assembles a list of per-bar
        data dicts ready to be serialized and passed to the chart subprocess.

        Args:
            dev (indigo.Device): The Indigo chart device instance.

        Returns:
            list: A list of dicts, each containing the bar number, name, state, color, legend,
                annotation flag, suppress flag, and value for one bar series.
"""
        # We can't access Indigo objects from the subprocess, so we need to get all the information we need before
        # calling the process.

        bars_data = []  # data for all bars (all data should be serializable).

        for _ in range(1, 6, 1):
            bar_data = {}  # data for each bar
            try:
                annotate    = dev.ownerProps[f'bar{_}Annotate']
                color       = color_utils.fix_rgb(dev.pluginProps[f'bar{_}Color'])
                legend      = dev.ownerProps[f'bar{_}Legend']
                suppress    = dev.ownerProps[f'suppressBar{_}']
                thing_id    = int(dev.ownerProps[f'bar{_}Source'])
                thing_state = dev.ownerProps[f'bar{_}Value']

                # Is it a device
                if thing_id in indigo.devices:
                    d = indigo.devices[thing_id]
                    val = d.states[thing_state]
                    name = d.name
                    state = thing_state
                # or a variable?
                elif thing_id in indigo.variables:
                    v = indigo.variables[thing_id]
                    val = v.value
                    name = v.name
                    state = "value"

                else:
                    raise ValueError

                bar_data['number']        = _
                bar_data['name']          = name
                bar_data['state']         = state
                bar_data[f'annotate_{_}'] = annotate
                bar_data[f'color_{_}']    = color
                bar_data[f'legend_{_}']   = legend
                bar_data[f'suppress_{_}'] = suppress
                bar_data[f'val_{_}']      = val
                bars_data.append(bar_data)

            except ValueError:
                # the bar[X]source field could be empty, so let's ignore it
                ...

        return bars_data

    # =============================================================================
    def charts_refresh(self, dev_list: list = None) -> None:
        """Refresh all plugin chart devices, rendering updated images via subprocesses.

        Iterates through the provided device list (or builds one from devices that have exceeded
        their refresh interval), assembles the per-device payload, audits color values, and
        dispatches a subprocess for each chart type. Processes the subprocess reply log when
        finished.

        Args:
            dev_list (list): A list of indigo.Device instances to refresh. If None, the method
                determines which devices need refreshing based on their refresh intervals.
        """
        def convert_to_native(obj: Union[indigo.Dict, indigo.List]) -> Any:
            """Convert any indigo.Dict and indigo.List objects to native Python formats.

            Recursively converts indigo.List to Python list and indigo.Dict to Python dict.
            Credit: Jay Martin
                    https://forums.indigodomo.com/viewtopic.php?p=193744#p193744

            Args:
                obj (indigo.Dict | indigo.List): The Indigo collection object to convert.

            Returns:
                list | dict | object: The converted native Python object.
            """
            if isinstance(obj, indigo.List):
                native_list = []
                for _item_ in obj:
                    native_list.append(convert_to_native(_item_))
                return native_list
            elif isinstance(obj, indigo.Dict):
                native_dict = {}
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

            # A dict of plugin preferences (we set defaults and override with pluginPrefs).
            p_dict: dict[str, Any]  = dict(self.pluginPrefs)

            try:
                # ============================  p_dict Overrides  =============================
                p_dict['legendColumns'] = self.pluginPrefs.get('legendColumns', 5)

                # ============================ rcParams overrides =============================
                plt.rcParams['font.size']        = float(p_dict['mainFontSize'])
                plt.rcParams['font.style']       = 'normal'
                plt.rcParams['font.weight']      = 'normal'
                plt.rcParams['grid.linestyle']   = self.pluginPrefs.get('gridStyle', ':')
                plt.rcParams['lines.linewidth']  = float(self.pluginPrefs.get('lineWeight', '1'))
                plt.rcParams['savefig.dpi']      = int(self.pluginPrefs.get('chartResolution', '100'))
                plt.rcParams['xtick.bottom']     = 'True'
                plt.rcParams['xtick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))
                plt.rcParams['xtick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
                plt.rcParams['xtick.minor.size'] = plt.rcParams['xtick.major.size'] / 2
                plt.rcParams['xtick.top']        = 'False'
                plt.rcParams['ytick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))
                plt.rcParams['ytick.left']       = 'True'
                plt.rcParams['ytick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
                plt.rcParams['ytick.minor.size'] = plt.rcParams['ytick.major.size'] / 2
                plt.rcParams['ytick.right']      = 'False'

                # Color values need a couple of adjustments.
                plt.rcParams['grid.color']  = color_utils.fix_rgb(color=self.pluginPrefs.get('gridColor', '88 88 88'))
                plt.rcParams['xtick.color'] = color_utils.fix_rgb(color=self.pluginPrefs.get('tickColor', '88 88 88'))
                plt.rcParams['ytick.color'] = color_utils.fix_rgb(color=self.pluginPrefs.get('tickColor', '88 88 88'))
                plt.rcParams['xtick.labelcolor'] = color_utils.fix_rgb(color=p_dict.get('fontColor', '88 88 88'))
                plt.rcParams['ytick.labelcolor'] = color_utils.fix_rgb(color=p_dict.get('fontColor', '88 88 88'))

                # ============================= Background color ==============================
                # backgroundColorOther is the transparent background config setting
                # Transparent Background = True
                # Filled Background      = False

                # Transparent is True, so we don't want filled.
                if self.pluginPrefs.get('backgroundColorOther', False):
                    p_dict['transparent_charts'] = True
                # Transparent is False, so we want filled.
                else:
                    p_dict['transparent_charts'] = False

                # ============================== Plot Area color ==============================
                # facColorOther is the transparent plot config setting
                # Transparent Plot Area  = True
                # Filled Plot Area       = False

                # Transparent is True, so we don't want filled.
                if self.pluginPrefs.get('faceColorOther', False):
                    p_dict['transparent_filled'] = False
                # Transparent is False, so we want filled.
                else:
                    p_dict['transparent_filled'] = True

                # ===========================  Device List is None  ===========================
                # Gather up a list of the devices that have exceeded their refresh times.
                if not dev_list:
                    dev_list = []

                    for dev in indigo.devices.iter('self'):
                        refresh_interval = int(dev.pluginProps['refreshInterval'])

                        if dev.deviceTypeId != 'csvEngine' and refresh_interval > 0 and dev.enabled:
                            diff = dt.datetime.now() - date_parse(dev.states['chartLastUpdated'])
                            refresh_needed = diff > dt.timedelta(seconds=refresh_interval)

                            if refresh_needed:
                                dev_list.append(dev)

                # ============================  Update the Charts  ============================
                for dev in dev_list:
                    # A list of state/value pairs used to feed updateStatesOnServer()
                    device_states = []
                    self.logger.debug("Updating chart: [%s]", dev.name)
                    dev.updateStatesOnServer(
                        [{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                    # ============================= Custom Font Sizes =============================
                    # Custom font sizes for retina/non-retina adjustments.
                    try:
                        if dev.pluginProps['customSizeFont']:
                            p_dict['mainFontSize'] = int(dev.pluginProps['customTitleFontSize'])
                            plt.rcParams['xtick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                            plt.rcParams['ytick.labelsize'] = int(dev.pluginProps['customTickFontSize'])

                    except KeyError:
                        # Not all devices may support this feature.
                        ...

                    # ================================== kwargs ===================================
                    k_dict['k_battery'] = {
                        'color': p_dict['fontColorAnnotation'],
                        'ha': 'right',
                        'textcoords': 'data',
                        'va': 'center',
                        'xycoords': 'data',
                        'zorder': 25
                    }
                    k_dict['k_annotation_battery'] = {
                        'bbox': {'alpha': 0.75,
                                 'boxstyle': 'round,pad=0.3',
                                 'edgecolor': p_dict['spineColor'],
                                 'facecolor': p_dict['faceColor'],
                                 'linewidth': 0.5,
                                 },
                        'color': p_dict['fontColorAnnotation'],
                        'ha': 'center',
                        'textcoords': 'data',
                        'va': 'center',
                        'xycoords': 'data',
                        'zorder': 25
                        }
                    k_dict['k_annotation'] = {
                        'bbox':
                            {'alpha': 0.75,
                             'boxstyle': 'round,pad=0.3',
                             'facecolor': p_dict['faceColor'],
                             'edgecolor': p_dict['spineColor'],
                             'linewidth': 0.5
                             },
                        'color': p_dict['fontColorAnnotation'],
                        'ha': 'center',
                        'textcoords': 'offset points',
                        'va': 'center'
                    }
                    k_dict['k_bar']       = {'alpha': 1.0, 'zorder': 10}
                    k_dict['k_base_font'] = {'size': float(p_dict['mainFontSize'])}
                    k_dict['k_calendar']  = {'va': 'top'}
                    k_dict['k_custom']    = {'alpha': 1.0, 'zorder': 3}
                    k_dict['k_fill']      = {'alpha': 0.7, 'zorder': 10}
                    k_dict['k_grid_fig']  = {'which': 'major', 'zorder': 1}
                    k_dict['k_line']      = {'alpha': 1.0}
                    k_dict['k_major_x']   = {'reset': False, 'which': 'major'}
                    k_dict['k_major_y']   = {'reset': False, 'which': 'major'}
                    k_dict['k_major_y2']  = {'reset': False, 'which': 'major'}
                    k_dict['k_max'] = {
                        'linestyle': 'dotted',
                        'marker': None,
                        'alpha': 1.0,
                        'zorder': 1
                    }
                    k_dict['k_min'] = {
                        'linestyle': 'dotted',
                        'marker': None,
                        'alpha': 1.0,
                        'zorder': 1
                    }
                    k_dict['k_minor_x'] = {
                        'reset': False,
                        'which': 'minor',
                    }
                    k_dict['k_minor_y'] = {
                        'reset': False,
                        'which': 'minor',
                    }
                    k_dict['k_minor_y2'] = {
                        'reset': False,
                        'which': 'minor',
                    }
                    k_dict['k_rgrids'] = {
                        'angle': 67,
                        'ha': 'left',
                        'va': 'center'
                    }
                    k_dict['k_title_font'] = {
                        'color': p_dict['fontColor'],
                        'fontname': p_dict['fontMain'],
                        'visible': True
                    }
                    k_dict['k_x_axis_font'] = {
                        'color': p_dict['fontColor'],
                        'fontname': p_dict['fontMain'],
                        'visible': True
                    }
                    k_dict['k_y_axis_font'] = {
                        'color': p_dict['fontColor'],
                        'fontname': p_dict['fontMain'],
                        'visible': True
                    }
                    k_dict['k_y2_axis_font'] = {
                        'color': p_dict['fontColor'],
                        'fontname': p_dict['fontMain'],
                        'visible': True
                    }

                    # If the user has selected transparent in the plugin menu, we account for that here when setting up
                    # the kwargs for savefig().
                    if p_dict['transparent_charts']:
                        k_dict['k_plot_fig'] = {
                            'bbox_extra_artists': None,
                            'bbox_inches': None,
                            'format': None,
                            # 'frameon': None,
                            'orientation': None,
                            'pad_inches': None,
                            # 'papertype': None,
                            'transparent': True
                        }
                    else:
                        k_dict['k_plot_fig'] = {
                            'bbox_extra_artists': None,
                            'bbox_inches': None,
                            'edgecolor': p_dict['backgroundColor'],
                            'facecolor': p_dict['backgroundColor'],
                            'format': None,
                            # 'frameon': None,
                            'orientation': None,
                            'pad_inches': None,
                            # 'papertype': None,
                            'transparent': False
                        }

                    # ========================== matplotlib.rc overrides ==========================
                    plt.rc('font', **k_dict['k_base_font'])

                    for _ in (
                        'bar_colors', 'customTicksLabelY', 'customTicksY', 'data_array', 'dates_to_plot', 'headers',
                        'wind_direction', 'wind_speed', 'x_obs1', 'x_obs2', 'x_obs3', 'x_obs4', 'x_obs5', 'x_obs6',
                        'x_obs7', 'x_obs8', 'y_obs1', 'y_obs1_max', 'y_obs1_min', 'y_obs2', 'y_obs2_max', 'y_obs2_min',
                        'y_obs3', 'y_obs3_max', 'y_obs3_min', 'y_obs4', 'y_obs4_max', 'y_obs4_min', 'y_obs5',
                        'y_obs5_max', 'y_obs5_min', 'y_obs6', 'y_obs6_max', 'y_obs6_min', 'y_obs7', 'y_obs7_max',
                        'y_obs7_min', 'y_obs8', 'y_obs8_max', 'y_obs8_min'
                    ):
                        p_dict[_] = []

                    p_dict['fileName']  = ''
                    p_dict['headers_1'] = ()  # Tuple
                    p_dict['headers_2'] = ()  # Tuple

                    try:
                        p_dict.update(dev.pluginProps)

                        # ===================== Limit number of observations =======================
                        try:
                            p_dict['numObs'] = int(p_dict['numObs'])

                        except KeyError:
                            # Only some devices will have their own numObs.
                            ...

                        except ValueError as sub_error:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.warning(
                                "[%s] The number of observations must be a positive number: %s. See plugin log for "
                                "more information.", dev.name, sub_error
                            )

                        # =========================== Custom Square Size ===========================
                        try:
                            if p_dict['customSizePolar'] == 'None':
                                ...

                            else:
                                p_dict['sqChartSize'] = float(p_dict['customSizePolar'])

                        except ValueError as sub_error:
                            self.plugin_error_handler(sub_error=traceback.format_exc())
                            self.logger.warning(
                                "[%s] Custom size must be a positive number or None: %s", dev.name, sub_error
                            )

                        except KeyError:
                            ...

                        # ============================ Extra Wide Chart ============================
                        try:
                            if p_dict.get('rectWide', False):
                                p_dict['chart_height'] = float(p_dict['rectChartWideHeight'])
                                p_dict['chart_width']  = float(p_dict['rectChartWideWidth'])

                            else:
                                p_dict['chart_height'] = float(p_dict['rectChartHeight'])
                                p_dict['chart_width']  = float(p_dict['rectChartWidth'])

                        except KeyError:
                            # Not all devices will have these keys
                            ...

                        # =============================== Custom Size ==============================
                        # If the user has specified a custom size, let's override with their custom setting.
                        if p_dict.get('customSizeChart', False):
                            try:
                                if p_dict['customSizeHeight'] != 'None':
                                    p_dict['chart_height'] = float(p_dict['customSizeHeight'])

                                if p_dict['customSizeWidth'] != 'None':
                                    p_dict['chart_width'] = float(p_dict['customSizeWidth'])

                            except KeyError:
                                # Not all devices will have these keys
                                ...

                        # ============================= Best Fit Lines =============================
                        # Set the defaults for best fit lines in p_dict.
                        for _ in range(1, 9, 1):
                            try:
                                best_fit_color = dev.pluginProps[f'line{_}BestFitColor']
                                p_dict[f'line{_}BestFitColor'] = best_fit_color
                            except KeyError:
                                ...

                        # ============================= Phantom Labels =============================
                        # Since users may or may not include axis labels and because we want to ensure that all plot
                        # areas present in the same way, we need to create 'phantom' labels that are plotted but not
                        # visible.  Setting the font color to 'None' will effectively hide them.
                        try:
                            if p_dict['customAxisLabelX'].isspace() or p_dict['customAxisLabelX'] == '':
                                p_dict['customAxisLabelX'] = 'null'
                                k_dict['k_x_axis_font'] = {
                                    'color': 'None',
                                    'fontname': p_dict['fontMain'],
                                    'visible': True
                                }
                        except KeyError:
                            # Not all devices will contain these keys
                            ...

                        try:
                            if p_dict['customAxisLabelY'].isspace() or p_dict['customAxisLabelY'] == '':
                                p_dict['customAxisLabelY'] = 'null'
                                k_dict['k_y_axis_font'] = {
                                    'color': 'None',
                                    'fontname': p_dict['fontMain'],
                                    'visible': True
                                }
                        except KeyError:
                            # Not all devices will contain these keys
                            ...

                        try:
                            # Not all devices that get to this point will support Y2.
                            if 'customAxisLabelY2' in p_dict:
                                if p_dict['customAxisLabelY2'].isspace() or p_dict['customAxisLabelY2'] == '':
                                    p_dict['customAxisLabelY2'] = 'null'
                                    k_dict['k_y2_axis_font'] = {
                                        'color': 'None',
                                        'fontname': p_dict['fontMain'],
                                        'fontsize': float(p_dict['mainFontSize']),
                                        # 'fontstyle': p_dict['font_style'],
                                        # 'weight': p_dict['font_weight'],
                                        'visible': True
                                    }
                        except KeyError:
                            # Not all devices will contain these keys
                            ...

                        # =============================== Annotations ==============================
                        # If the user wants annotations, we need to hide the line markers as we don't want to plot one
                        # on top of the other.
                        for line in range(1, 9, 1):
                            try:
                                if p_dict[f'line{line}Annotate'] and p_dict[f'line{line}Marker'] != 'None':
                                    p_dict[f'line{line}Marker'] = 'None'
                                    self.logger.warning(
                                        "[%s] Line %s marker is suppressed to display  annotations. To "
                                        "see the marker, disable annotations for this line.", dev.name, line
                                    )
                            # Not all devices will contain these keys
                            except KeyError:
                                ...

                        # ============================== Line Markers ==============================
                        # Some line markers need to be adjusted due to their inherent value. For example, matplotlib
                        # uses '<', '>' and '.' as markers but storing these values will blow up the XML.  So we need
                        # to convert them. (See color_utils.format_markers().)
                        p_dict = color_utils.format_markers(p_dict=p_dict)

                        # Note that the logging of p_dict and k_dict are handled within the thread.
                        self.logger.threaddebug(f"{f' Generating Chart: {dev.name} ':*^80}")
                        self.__log_dicts(dev)

                        plug_dict         = dict(self.pluginPrefs)
                        dev_dict          = dict(dev.pluginProps)
                        dev_dict['name']  = dev.name
                        dev_dict['model'] = dev.model
                        dev_dict['id']    = dev.id

                        # =========================  Custom Line Segments  =========================
                        # We support substitutions in custom line segments settings. These need to be converted in the
                        # main plugin thread because they can't be converted within the subprocess.
                        _ = [
                            "areaChartingDevice",
                            "barChartingDevice",
                            "barStockChartingDevice",
                            "barStockHorizontalChartingDevice",
                            "lineChartingDevice",
                            "scatterChartingDevice",
                            "forecastChartingDevice"
                        ]
                        try:
                            if (p_dict['enableCustomLineSegments'] and
                               dev.deviceTypeId in _ and
                               p_dict['customLineSegments'] not in ("", "None")):

                                try:
                                    # constants_to_plot will be (val, rgb) or ((val, rgb), (val, rgb)), Since we can't
                                    # mutate a tuple, we listify it first.
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
                                    self.logger.warning(
                                        "Problem with custom line segments. Please ensure setting is in the proper "
                                        "format."
                                    )

                        # Not all devices support custom line segments
                        except KeyError:
                            ...
                        except SyntaxError:
                            self.logger.warning("[%s] Custom Line Segments entry is invalid. Skipping.", dev.name)

                        # =================================================
                        # Convert these indigo.List(s) to Python lists.
                        for key in plug_dict:
                            if isinstance(plug_dict[key], indigo.List):
                                plug_dict[key] = list(plug_dict[key])

                        for key in dev_dict:
                            if isinstance(dev_dict[key], indigo.List):
                                dev_dict[key] = list(dev_dict[key])

                        for key in p_dict:
                            if isinstance(p_dict[key], indigo.List):
                                p_dict[key] = list(p_dict[key])

                        # ============================= rcParams Device ============================
                        if dev.deviceTypeId == 'rcParamsDevice':
                            self.rc_params_device_update(dev=dev)

                        # For the time being, we're running each device through its own process synchronously; parallel
                        # processing may come later.
                        #
                        # NOTE: elements passed to a subprocess have to be serializable. Indigo device and plugin
                        # objects are not serializable, so we create a proxy to send to the process. Therefore, devices
                        # can't be changed in the processes.

                        # Audit values in p_dict and k_dict to ensure they're in the proper format.
                        plug_dict = copy.deepcopy(audits.audit_dict_color(_dict_=plug_dict))
                        plug_dict['old_prefs'] = None
                        dev_dict  = audits.audit_dict_color(_dict_=dev_dict)
                        p_dict    = copy.deepcopy(audits.audit_dict_color(_dict_=p_dict))
                        p_dict['old_prefs'] = None
                        k_dict    = audits.audit_dict_color(_dict_=k_dict)

                        # Instantiate basic payload sent to the subprocess scripts. Additional key/value pairs may be
                        # added below before payload is sent.
                        raw_payload = {
                            'prefs': plug_dict,
                            'props': dev_dict,
                            'p_dict': p_dict,
                            'k_dict': k_dict,
                            'data': None,
                        }

                        # =============================== Area Charts ==============================
                        if dev.deviceTypeId == "areaChartingDevice":

                            # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait until
                            # this point to convert it because some devices add additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Run the plot
                            path_to_file = 'Charts/chart_area.py'

                        # ===============================  Flow Bar  ===============================
                        if dev.deviceTypeId == 'barChartingDevice':

                            # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait until
                            # this point to convert it because some devices add additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Run the plot
                            path_to_file = 'Charts/chart_bar_flow.py'

                        # ===============================  Stock Bar  ==============================
                        if dev.deviceTypeId == 'barStockChartingDevice':

                            raw_payload['data'] = self.chart_stock_bar(dev=dev)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait until
                            # this point to convert it because some devices add additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Run the plot
                            path_to_file = 'Charts/chart_bar_stock.py'

                        # =========================  Stock Horizontal Bar  =========================
                        if dev.deviceTypeId == 'barStockHorizontalChartingDevice':

                            raw_payload['data'] = self.chart_stock_bar(dev=dev)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait until
                            # this point to convert it because some devices add additional device-specific data.
                            raw_payload = convert_to_native(raw_payload)

                            # Run the plot
                            path_to_file = 'Charts/chart_bar_stock_horizontal.py'

                        # ===========================  Stock Radial Bar  ===========================
                        if dev.deviceTypeId == 'radialBarChartingDevice':
                            source_id = int(dev.pluginProps['bar1Source'])
                            source_value = dev.pluginProps['bar1Value']
                            scale = dev.pluginProps['scale']

                            # The data value to chart.
                            if source_id in indigo.devices:
                                try:
                                    val = indigo.devices[source_id].states[source_value]
                                    raw_payload['data'] = float(val)
                                except ValueError:
                                    self.logger.warning(
                                        f"Could not convert device {source_id} value to a float [{val}]"
                                    )
                            else:
                                try:
                                    val = indigo.variables[source_id].value
                                    raw_payload['data'] = float(val)
                                except ValueError:
                                    self.logger.warning(
                                        f"Could not convert variable {source_id} value to a float [{val}]"
                                    )

                            # Convert scale value if it's a substitution. The substitution value should be valid
                            # because we checked it in validation.
                            if scale.startswith('%%'):
                                raw_payload['scale'] = self.substitute(scale)

                            # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait
                            # until this point to convert it because some devices add additional device-specific
                            # data.
                            raw_payload = convert_to_native(raw_payload)

                            # Run the plot
                            path_to_file = 'Charts/chart_bar_radial.py'

                        # ========================== Battery Health Chart ==========================
                        if dev.deviceTypeId == 'batteryHealthDevice':

                            device_dict  = {}
                            exclude_list = [int(_) for _ in dev.pluginProps.get('excludedDevices', [])]

                            for batt_dev in indigo.devices.iter():
                                try:
                                    if batt_dev.batteryLevel \
                                            is not None \
                                            and batt_dev.id not in exclude_list:
                                        device_dict[batt_dev.name] = batt_dev.states['batteryLevel']

                                    # The following line is used for testing the battery health code; it isn't needed
                                    # in production.
                                    # self.logger.warning("Using dummy battery data for testing.")
                                    # device_dict = {
                                    #     'Device A': 0, 'Device B': 100, 'Device C': 8,
                                    #     'Device D': 4, 'Device E': 92, 'Device F': 72,
                                    #     'Device G': 47, 'Device H': 68, 'Device I': 0,
                                    #     'Device J': 47
                                    # }

                                except Exception as sub_error:
                                    self.plugin_error_handler(sub_error=traceback.format_exc())
                                    self.logger.error(
                                        "[%s] Error reading battery devices: %s", batt_dev.name, sub_error
                                    )

                            if not device_dict:
                                device_dict['No Battery Devices'] = 0

                            dev_dict['excludedDevices'] = convert_to_native(dev_dict['excludedDevices'])
                            p_dict['excludedDevices']   = convert_to_native(p_dict['excludedDevices'])

                            # Payload sent to the subprocess script
                            raw_payload['data'] = device_dict
                            path_to_file = 'Charts/chart_batteryhealth.py'

                        # ============================= Calendar Charts ============================
                        if dev.deviceTypeId == "calendarChartingDevice":

                            path_to_file = 'Charts/chart_calendar.py'

                        # =============================== Line Charts ==============================
                        if dev.deviceTypeId == "lineChartingDevice":

                            path_to_file = 'Charts/chart_line.py'

                        # ============================= Multiline Text =============================
                        if dev.deviceTypeId == 'multiLineText':
                            try:
                                plt.rcParams['text.color'] = p_dict['textColor']
                                plt.rcParams['patch.facecolor'] = p_dict['faceColor']

                                # Get the text to plot. We do this here, so we don't need to send all the devices and
                                # variables to the method (the process doesn't have access to the Indigo server).
                                if int(p_dict['thing']) in indigo.devices:
                                    dev_id = int(p_dict['thing'])
                                    raw_payload['data'] = f"{indigo.devices[dev_id].states[p_dict['thingState']]}"

                                elif int(p_dict['thing']) in indigo.variables:
                                    raw_payload['data'] = f"{indigo.variables[int(p_dict['thing'])].value}"

                                else:
                                    raw_payload['data'] = "Unable to reconcile plot text. Confirm device settings."
                                    self.logger.info("The plugin only supports device state and variable values.")

                                path_to_file = 'Charts/chart_multiline.py'

                            except OSError as err:
                                if "Argument list too long" in str(err):
                                    self.logger.critical("Text source too long.")

                        # ============================== Polar Charts ==============================
                        if dev.deviceTypeId == "polarChartingDevice":

                            path_to_file = 'Charts/chart_polar.py'

                        # ============================= Scatter Charts =============================
                        if dev.deviceTypeId == "scatterChartingDevice":

                            # Run the plot
                            path_to_file = 'Charts/chart_scatter.py'

                        # ========================= Weather Forecast Charts ========================
                        if dev.deviceTypeId == "forecastChartingDevice":

                            dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                            state_list = dict(indigo.devices[int(p_dict['forecastSourceDevice'])].states)
                            sun_rise_set = [str(indigo.server.calculateSunrise()), str(indigo.server.calculateSunset())]

                            raw_payload['dev_type']     = dev_type
                            raw_payload['state_list']   = state_list
                            raw_payload['sun_rise_set'] = sun_rise_set
                            path_to_file = 'Charts/chart_weather_forecast.py'

                        # ========================= Weather Composite Charts =======================
                        if dev.deviceTypeId == "compositeForecastDevice":

                            dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                            state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states

                            raw_payload['dev_type']   = dev_type
                            raw_payload['state_list'] = dict(state_list)
                            path_to_file = 'Charts/chart_weather_composite.py'

                        # Convert any nested indigo.Dict and indigo.List objects to native formats. We wait until this
                        # point to convert it because some devices add additional device-specific data.
                        raw_payload = convert_to_native(raw_payload)

                        # Serialize the payload
                        payload = json.dumps(raw_payload, indent=4, separators=(',', ': '))

                        # =========================  Process Style Sheet  ==========================
                        # Save rcParams as a style sheet for use in subprocess calls. We use a separate style sheet for
                        # each device because each device can have different styles.

                        # If the "Stylesheets" folder isn't present, create one.
                        if not os.path.exists("Stylesheets/"):
                            os.mkdir("Stylesheets/")

                        with open(
                                f"Stylesheets/{dev.id}_stylesheet", 'w', encoding="utf-8"
                        ) as outfile:
                            for k, v in rcParams.items():
                                # matplotlib stylesheets require lists to NOT have `[` or `]`, and values separated by
                                # commas. Empty string for empty list.
                                if isinstance(v, list):
                                    if len(v) > 0:
                                        v = ', '.join(str(_) for _ in v)
                                    else:
                                        v = ""
                                # '#' starts a comment in matplotlib stylesheet ('.mplstyle') file syntax, so a
                                # '#RRGGBB' color value would be silently dropped to matplotlib's default if left
                                # in place. matplotlib.rcParams itself always normalizes hex colors to include the
                                # '#' internally (see fix_rgb()), so this strip is required here regardless of how
                                # the value was originally set.
                                if isinstance(v, str) and v.startswith('#'):
                                    v = v[1:]
                                outfile.write(f"{k}: {v}\n")

                        # ============================  Process Result  ============================
                        self.logger.debug("[%s] Sending to chart refresh process.", dev.name)
                        # It's important to use the full path to the Python version to ensure that we get the version
                        # we want.
                        try:
                            plugin_dir  = os.getcwd()
                            environment = os.environ.copy()
                            environment['PYTHONPATH'] = plugin_dir
                            with subprocess.Popen(
                                    ['/usr/local/bin/python3', path_to_file, payload, ],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=environment,
                            ) as proc:

                                # Get the results and act on anything that's returned.
                                if proc:
                                    reply, err = proc.communicate()

                        except (TypeError, ValueError):
                            self.logger.exception("")
                            self.logger.debug("Payload raised error: %s", payload)

                        # Parse the output log
                        result = self.process_plotting_log(dev=dev, replies=reply, errors=err)
                        # If we have manually asked for all charts to update, don't refresh the last update time so
                        # that the charts will update on their own at the next refresh cycle.
                        if 'chartLastUpdated' in dev.states and not self.skipRefreshDateUpdate:
                            device_states.append({'key': 'chartLastUpdated', 'value': f"{dt.datetime.now()}"})

                        # All has gone well.
                        if not result and dev.deviceTypeId not in ('rcParamsDevice',):
                            device_states.append({'key': 'onOffState', 'value': True, 'uiValue': "Error"})
                        elif dev.deviceTypeId:
                            refresh_interval = dev.pluginProps.get('refreshInterval', 900)
                            if int(refresh_interval) == 0 \
                                    and dev.deviceTypeId not in ('rcParamsDevice',):
                                ui_value = 'Manual'
                            elif int(refresh_interval) > 0 \
                                    and dev.deviceTypeId not in ('rcParamsDevice',):
                                ui_value = 'Updated'
                            else:
                                ui_value = " "

                            device_states.append({'key': 'onOffState', 'value': True, 'uiValue': ui_value})

                        dev.updateStatesOnServer(device_states)

                    except RuntimeError as sub_error:
                        self.plugin_error_handler(sub_error=traceback.format_exc())
                        self.logger.critical(
                            "[%s] Critical Error: %s. See plugin log for more information.", dev.name, sub_error
                        )
                        self.logger.critical("Skipping device.")
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)

                # Ensure the flag is in the proper state for the next automatic refresh.
                self.skipRefreshDateUpdate = False

            except Exception as sub_error:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.critical("Error: %s. See plugin log for more information.", sub_error)

    # =============================================================================
    def commsKillAll(self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> None:  # noqa
        """
        Deactivate communication with all plugin devices

        commsKillAll() sets the enabled status of all plugin devices to false.
        """
        self.logger.info("Stopping communication with all plugin devices.")

        for dev in indigo.devices.iter("self"):
            try:
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                indigo.device.enable(dev, value=False)
            except Exception as sub_error:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(
                    "Exception when trying to kill all comms. Error: %s. See plugin log for more information.", sub_error
                )

    # =============================================================================
    def commsUnkillAll(self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> None:  # noqa
        """
        Establish communication for all disabled plugin devices

        commsUnkillAll() sets the enabled status of all plugin devices to true.
        """
        self.logger.info("Starting communication with all plugin devices.")

        for dev in indigo.devices.iter("self"):
            try:
                indigo.device.enable(dev, value=True)
            except Exception as sub_error:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(
                    "Exception when trying to kill all comms. Error: %s. See plugin log for more information.", sub_error
                )

    # =============================================================================
    @staticmethod
    def csv_check_unique() -> None:
        """Check CSV Engine devices for duplicate CSV filename references.

        Iterates through all CSV Engine devices and builds a mapping of CSV filenames to the
        devices that reference them. Logs a warning for any filename referenced by more than one
        CSV Engine device, as duplicate references can cause data integrity issues.
        """
        csv_handling.csv_check_unique()

    # =============================================================================
    def csv_item_add(self, values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> Tuple[indigo.Dict, indigo.Dict]:  # noqa
        """Add a new CSV data source item to the CSV Engine device configuration.

        Called when the user clicks the 'Add Item' button in the CSV Engine config dialog.
        Validates that all required fields are populated, generates the next key, saves the new
        item to the columnDict, creates the CSV file if it does not exist, and resets the add
        form fields.

        Args:
            values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            tuple: A two-element tuple of (values_dict, error_msg_dict).
        """
        return csv_handling.csv_item_add(values_dict=values_dict, dev_id=dev_id, prefs=self.pluginPrefs)

    # =============================================================================
    @staticmethod
    def csv_item_delete(values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> dict:  # noqa
        """Delete the selected CSV data source item from the CSV Engine configuration.

        Called when the user clicks the 'Delete Item' button in the CSV Engine config dialog.
        Removes the selected item from the columnDict and resets all edit form fields.

        Args:
            values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            dict: The updated values_dict with the item removed and edit fields cleared.
        """
        return csv_handling.csv_item_delete(values_dict=values_dict, dev_id=dev_id)

    # =============================================================================
    @staticmethod
    def csv_item_list(filter: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Generate the sorted list of CSV item key/name pairs for the CSV Engine config dialog.

        Reads the columnDict from values_dict and returns a case-insensitive sorted list of
        (key, item_name) tuples for display in the CSV Engine item list control. Called when the
        dialog opens and whenever changes are made.

        Args:
            filter (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
            type_id (str): The device type identifier string.
            target_id (int): The Indigo device ID.

        Returns:
            list: A sorted list of (key, item_name) tuples.
        """
        return csv_handling.csv_item_list(values_dict=values_dict, target_id=target_id)

    # =============================================================================
    @staticmethod
    def csv_item_update(values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> Tuple[indigo.Dict, indigo.Dict]:  # noqa
        """Update a CSV data source item in the CSV Engine device configuration.

        Called when the user clicks the 'Update Item' button in the CSV Engine config dialog.
        Validates the new key for uniqueness, updates the selected item in columnDict, and resets
        the edit form fields on success.

        Args:
            values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            tuple: A two-element tuple of (values_dict, error_msg_dict).
        """
        return csv_handling.csv_item_update(values_dict=values_dict, dev_id=dev_id)

    # =============================================================================
    @staticmethod
    def csv_item_select(values_dict: indigo.Dict = None, type_id: str = "", dev_id: int = 0) -> dict:  # noqa
        """Populate CSV Engine edit controls when the user selects an item from the item list.

        Called when the user selects an item from the CSV Engine Item List dropdown. Reads the
        selected item's properties from columnDict and populates the edit key, source, state, and
        value controls, and sets the isColumnSelected flag.

        Args:
            values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
            type_id (str): The device type identifier string.
            dev_id (int): The Indigo device ID.

        Returns:
            dict: The updated values_dict with edit controls populated.
        """
        return csv_handling.csv_item_select(values_dict=values_dict, dev_id=dev_id)

    # =============================================================================
    def csv_refresh(self) -> None:
        """
        Refreshes data for all CSV custom devices

        The csv_refresh() method manages CSV files through CSV Engine custom devices.
        """
        csv_handling.csv_refresh(
            is_shutting_down=self.pluginIsShuttingDown, log_dicts=self.__log_dicts, prefs=self.pluginPrefs,
            sleep_fn=self.sleep
        )

    # =============================================================================
    def csv_refresh_process(self, dev: indigo.Device = None, csv_dict: dict = None) -> None:
        """Process a CSV data refresh for a CSV Engine device.

        For each CSV source in csv_dict:
        - creates the CSV file if missing,
        - backs it up,
        - loads existing data,
        - applies time and length limits,
        - appends the newest observation from the linked Indigo device or variable, and
        - writes the updated data back to disk.

        Updates the device's csvLastUpdated state and state image on completion.

        Args:
            dev (indigo.Device): The Indigo CSV Engine device instance.
            csv_dict (dict): A dict mapping keys to (item_name, source_id, source_state) tuples.
        """
        csv_handling.csv_refresh_process(dev=dev, csv_dict=csv_dict, prefs=self.pluginPrefs, sleep_fn=self.sleep)

    # =============================================================================
    def csv_refresh_device_action(self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> None:  # noqa
        """Manually refresh all CSV sources for a single CSV Engine device via an Action item.

        Updates all CSV sources associated with the selected CSV Engine device. Only CSV Engine
        devices set to a manual refresh interval are presented in the action configuration.

        Args:
            plugin_action (indigo.ActionGroup): The Indigo action group containing the target
                device selection.
            dev (indigo.Device): The Indigo device associated with the action (passed by Indigo).
            caller_waiting_for_result (bool): Whether the caller is waiting for a return value.
        """
        csv_handling.csv_refresh_device_action(
            plugin_action=plugin_action, prefs=self.pluginPrefs, sleep_fn=self.sleep
        )

    # =============================================================================
    def csv_refresh_source_action(
            self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False  # noqa
    ) -> None:
        """Manually refresh a single CSV source for a CSV Engine device via an Action item.

        Allows the user to update one specific CSV source from a CSV Engine device. The action
        configuration presents the available CSV sources for the selected CSV Engine device. Only
        CSV Engine devices set to a manual refresh interval are presented.

        Args:
            plugin_action (indigo.ActionGroup): The Indigo action group containing the target
                device and source selections.
            dev (indigo.Device): The Indigo device associated with the action (passed by Indigo).
            caller_waiting_for_result (bool): Whether the caller is waiting for a return value.
        """
        csv_handling.csv_refresh_source_action(
            plugin_action=plugin_action, prefs=self.pluginPrefs, sleep_fn=self.sleep
        )

    # =============================================================================
    @staticmethod
    def csv_source(type_id: str = "", values_dict: indigo.Dict = None, dev_id: int = 0, target_id: int = 0) -> list:  # noqa
        """Construct the list of available devices and variables for the CSV Engine add-item control.

        Builds a list of (id, name) tuples for devices, variables, or both depending on the
        addSourceFilter preference. Category labels and separators are included for visual clarity.

        Args:
            type_id (str): The device type identifier string (passed by Indigo).
            values_dict (indigo.Dict): The current dialog values, including 'addSourceFilter'.
            dev_id (int): The Indigo device ID (passed by Indigo).
            target_id (int): The target device or variable ID (passed by Indigo).

        Returns:
            list: A list of (id, name) tuples suitable for an Indigo dropdown control.
        """
        return csv_handling.csv_source(values_dict=values_dict)

    # =============================================================================
    @staticmethod
    def csv_source_edit(type_id: str = "", values_dict: indigo.Dict = None, dev_id: int = 0, target_id: int = 0) -> list:  # noqa
        """Construct the list of available devices and variables for the CSV Engine edit-item control.

        Builds a list of (id, name) tuples for devices, variables, or both depending on the
        editSourceFilter preference. Category labels and separators are included for visual clarity.

        Args:
            type_id (str): The device type identifier string (passed by Indigo).
            values_dict (indigo.Dict): The current dialog values, including 'editSourceFilter'.
            dev_id (int): The Indigo device ID (passed by Indigo).
            target_id (int): The target device or variable ID (passed by Indigo).

        Returns:
            list: A list of (id, name) tuples suitable for an Indigo dropdown control.
        """
        return csv_handling.csv_source_edit(values_dict=values_dict)

    # =============================================================================
    @staticmethod
    def get_csv_device_list(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of CSV Engine devices configured for manual refresh.

        Filters plugin devices to return only CSV Engine devices whose refreshInterval is set to
        zero (manual update only).

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (device_id, device_name) tuples for CSV Engine manual-refresh devices.
        """
        return csv_handling.get_csv_device_list()

    # =============================================================================
    @staticmethod
    def get_csv_source_list(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return the list of CSV data sources for the selected CSV Engine device.

        Once the user selects a target CSV Engine device (from get_csv_device_list()), this method
        populates the CSV source dropdown with the available data sources for that device.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values, containing 'targetDevice'.
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (key, item_name) tuples for the CSV sources, or an empty list on error.
        """
        return csv_handling.get_csv_source_list(values_dict=values_dict)

    # =============================================================================
    @staticmethod
    def device_state_value_list_add(type_id: str = "", values_dict: indigo.Dict = None, dev_id: int = 0, target_id: int = 0) -> list:  # noqa
        """Return the list of device states or variable value for the CSV Engine add-item control.

        Once the user selects a device or variable in the CSV Engine add-item dialog, populates
        the state/value dropdown. Returns the device's states (excluding UI states) for devices, or
        [('value', 'value')] for variables. Returns a placeholder if no source is selected or the
        filter does not match the source type.

        Args:
            type_id (str): The device type identifier string (passed by Indigo).
            values_dict (indigo.Dict): The current dialog values, containing 'addSource' and
                'addSourceFilter'.
            dev_id (int): The Indigo device ID (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of state/value identifier strings or placeholder tuples.
        """
        return ui_lists.device_state_value_list_add(values_dict=values_dict)

    # =============================================================================
    @staticmethod
    def device_state_value_list_edit(type_id: str = "", values_dict: indigo.Dict = None, dev_id: int = 0, target_id: int = 0) -> list:  # noqa
        """Return the list of device states or variable value for the CSV Engine edit-item control.

        Once the user selects a device or variable in the CSV Engine edit-item dialog, populates
        the state/value dropdown. Returns the device's states (excluding UI states) for devices, or
        [('value', 'value')] for variables. Returns a placeholder if no source is selected or the
        filter does not match the source type.

        Args:
            type_id (str): The device type identifier string (passed by Indigo).
            values_dict (indigo.Dict): The current dialog values, containing 'editSource' and
                'editSourceFilter'.
            dev_id (int): The Indigo device ID (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of state/value identifier strings or placeholder tuples.
        """
        return ui_lists.device_state_value_list_edit(values_dict=values_dict)

    # =============================================================================
    def generatorDeviceStates(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return device states or a variable value list for a dropdown control.

        Returns a list of device states for the selected device, or [('value', 'value')] if a
        variable is selected. The device or variable ID is transmitted via the fltr attribute.
        Generated by DLFramework.

        Example return values:
            [('dev state name', 'dev state name'), ...]
            [('value', 'value')]

        Args:
            fltr (str): The key in values_dict that holds the selected device or variable ID.
            values_dict (indigo.Dict): The current dialog values.
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of state name tuples or the variable value tuple.
        """
        return self.Fogbert.generatorStateOrValue(values_dict[fltr])

    # =============================================================================
    def generatorDeviceList(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of all Indigo devices for dropdown menus.

        Returns (device_id, device_name) tuples for all devices, regardless of enabled status.
        Generated by DLFramework.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (device_id, device_name) tuples.
        """
        return self.Fogbert.deviceList()

    # =============================================================================
    @staticmethod
    def generatorPrecisionList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of numeric display precision options for dropdown menus.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (value, label) tuples for 0–3 decimal place precision options.
        """
        return ui_lists.generatorPrecisionList()

    # =============================================================================
    @staticmethod
    def generatorLineStyleDefaultNoneList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of matplotlib line style options with 'None' as the default.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (value, label) tuples for matplotlib line styles.
        """
        return ui_lists.generatorLineStyleDefaultNoneList()

    # =============================================================================
    @staticmethod
    def generatorLineStyleDefaultSolidList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of matplotlib line style options with 'Solid' as the default.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (value, label) tuples for matplotlib line styles.
        """
        return ui_lists.generatorLineStyleDefaultSolidList()

    # =============================================================================
    @staticmethod
    def generatorMarkerList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of matplotlib marker style options for dropdown menus.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (value, label) tuples for matplotlib marker styles.
        """
        return ui_lists.generatorMarkerList()

# =============================================================================
    def latestDevVarList(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return the cached list of devices and variables built in getDeviceConfigUiValues.

        Returns the dev_var_list populated when the device config dialog was opened, avoiding
        redundant Indigo server calls during dialog interaction.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: The cached list of (id, name) tuples for devices and variables.
        """
        return self.dev_var_list

    # =============================================================================
    def generatorDeviceAndVariableList(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a combined list of all Indigo devices and variables for dropdown menus.

        All devices are listed first and then all variables, regardless of enabled status.
        Generated by DLFramework.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (id, name) tuples for all devices followed by all variables.
        """
        return self.Fogbert.deviceAndVariableList()

    # =============================================================================
    def generatorVariableList(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of all Indigo variables for dropdown menus.

        Returns (variable_id, variable_name) tuples for all variables, regardless of enabled
        status. Generated by DLFramework.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (variable_id, variable_name) tuples.
        """
        return self.Fogbert.variableList()

    # =============================================================================
    @staticmethod
    def get_axis_list(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of common Python date format strings for X-axis label dropdown menus.

        Generates live examples using the current date and time to show the user how each format
        will appear. Does not include all possible Python strftime specifiers.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (format_string, example_label) tuples.
        """
        return ui_lists.get_axis_list()

    # =============================================================================
    @staticmethod
    def get_battery_device_list(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of all Indigo devices that report a battery level.

        Filters all Indigo devices to those with a non-None batteryLevel property. If no
        battery-powered devices are found, returns a single placeholder tuple.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (device_id, device_name) tuples for battery-powered devices.
        """
        return ui_lists.get_battery_device_list()

    # =============================================================================
    def getFileList(self, fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a sorted list of CSV files from the configured data path for dropdown menus.

        Scans the dataPath folder for '*.csv' files and returns a sorted list of (filename,
        display_name) tuples. Appends a separator and a 'None' option at the end of the list.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A sorted list of (filename, display_name) tuples plus a 'None' entry.
        """
        return ui_lists.getFileList(prefs=self.pluginPrefs)

    # =============================================================================
    @staticmethod
    def getFontList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a sorted list of font names visible to matplotlib for dropdown menus.

        These are the fonts that matplotlib can discover, not necessarily all fonts installed on the
        system. Falls back to the FONT_MENU constant list if matplotlib cannot find any fonts.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A sorted list of font name strings.
        """
        return ui_lists.getFontList()

    # =============================================================================
    @staticmethod
    def getRefreshList(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a list of chart devices for the 'Redraw Charts Now...' menu dropdown.

        Builds a menu list starting with 'All Charts' and 'Skip Manual Charts' options, then
        appends each enabled plugin chart device.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A list of (id, label) tuples for the refresh menu.
        """
        return ui_lists.getRefreshList()

    # =============================================================================
    @staticmethod
    def getForecastSource(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a sorted list of compatible weather forecast source devices.

        Iterates over Fantastic Weather and WUnderground plugin devices and returns those with
        supported forecast device type IDs. Intended to be expanded to support additional weather
        plugins in the future.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The device type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A case-insensitive sorted list of (device_id, device_name) tuples.
        """
        return ui_lists.getForecastSource()

    # =============================================================================
    def plotActionApi(self, plugin_action: indigo.ActionGroup = None, dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> dict | None:  # noqa
        """Handle simple chart generation API calls from Indigo Action items.

        Provides a scripting API entry point for generating a basic matplotlib line chart from
        an Action item payload. All payload elements are required; kwargs may be an empty dict.

        Expected payload structure::

            {
                'x_values': [1, 2, 3],
                'y_values': [2, 4, 6],
                'kwargs': {
                    'linestyle': 'dashed',
                    'color': 'b',
                    'marker': 's',
                    'markerfacecolor': 'b'
                },
                'path': '/full/path/name/',
                'filename': 'chart_filename.png'
            }

        Args:
            plugin_action (indigo.ActionGroup): The Indigo action group containing the chart
                payload in its props dict.
            dev (indigo.Device): The Indigo device associated with the action (passed by Indigo).
            caller_waiting_for_result (bool): If True, returns a result dict; otherwise returns
                None.

        Returns:
            dict | None: {'success': True, 'message': 'Success'} on success,
                {'success': False, 'message': error} on failure, or None if
                caller_waiting_for_result is False.
        """
        self.logger.info("Scripting payload: %s", dict(plugin_action.props))

        dpi          = int(self.pluginPrefs.get('chartResolution', 100))
        height       = float(self.pluginPrefs.get('rectChartHeight', 250))
        width        = float(self.pluginPrefs.get('rectChartWidth', 600))
        face_color   = self.pluginPrefs.get('faceColor', '#000000')
        bk_color     = self.pluginPrefs.get('backgroundColor', '#000000')

        # =============================  Unpack Payload  ==============================
        x_values  = plugin_action.props['x_values']
        y_values  = plugin_action.props['y_values']
        kwargs    = plugin_action.props['kwargs']
        path_name = plugin_action.props['path']
        file_name = plugin_action.props['filename']

        try:
            fig = plt.figure(1, figsize=(width / dpi, height / dpi))
            ax = fig.add_subplot(111)
            ax.patch.set_facecolor(face_color)
            ax.plot(x_values, y_values, **kwargs)
            plt.savefig(f"{path_name}{file_name}", facecolor=bk_color, dpi=dpi)
            plt.clf()
            plt.close('all')

        except Exception as sub_error:
            if caller_waiting_for_result:
                self.plugin_error_handler(sub_error=traceback.format_exc())
                self.logger.error(
                    "[%s] Error: %s. See plugin log for more information.", dev.name, sub_error
                )
                return {'success': False, 'message': sub_error}

        if caller_waiting_for_result:
            # Note! returns from actions that were called by calls to indigo.executeAction() can't be Bools,
            # indigo.Dict -- and likely other types. Strings and the following dict will work.
            return {'success': True, 'message': "Success"}

        return None

    # =============================================================================
    def pluginEnvironmentLogger(self) -> None:  # noqa
        """
        Log information about the plugin resource environment.

        Write select information about the environment that the plugin is running in. This method is only called once,
        when the plugin is first loaded (or reloaded).
        """
        chart_devices = 0
        csv_engines = 0
        log_path = indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')
        matplotlib_environment = ""
        matplotlib_version = plt.matplotlib.__version__
        rc_path = plt.matplotlib.matplotlib_fname()
        spacer = " " * 35

        # ========================== Get Plugin Device Load ===========================
        for dev in indigo.devices.iter('self'):
            if dev.pluginProps.get('isChart', False):
                chart_devices += 1
            elif dev.deviceTypeId == 'csvEngine':
                csv_engines += 1

        matplotlib_environment += f"{' Matplotlib Environment ':{'='}^135}\n"
        matplotlib_environment += f"{spacer}{'Matplotlib version:':<31} {matplotlib_version}\n"
        matplotlib_environment += f"{spacer}{'Numpy version:':<31} {np.__version__}\n"
        matplotlib_environment += f"{spacer}{'Matplotlib RC Path:':<31} {rc_path}\n"
        matplotlib_environment += f"{spacer}{'Matplotlib Plugin log location:':<31} {log_path}\n"
        matplotlib_environment += f"{spacer}{'Number of Chart Devices:':<31} {chart_devices}\n"
        matplotlib_environment += f"{spacer}{'Number of CSV Engine Devices:':<31} {csv_engines}\n"
        # rcParams is a dict containing all the initial _matplotlibrc settings
        matplotlib_environment += f"{spacer}{'='*135}"
        self.logger.info(matplotlib_environment)

        self.logger.threaddebug("Matplotlib base rcParams:       %s", dict(rcParams))
        self.logger.threaddebug("Initial Plugin Prefs:           %s", dict(self.pluginPrefs))

    # =============================================================================
    def plugin_error_handler(self, sub_error: str = "") -> None:
        """Log a formatted traceback message to the plugin log file.

        Formats and logs traceback messages to the plugin log only (not the Indigo Events log).
        Use this method to handle exceptions by passing traceback.format_exc() as the argument.

        Args:
            sub_error (str): The string-formatted traceback message to log.
        """
        sub_error = sub_error.splitlines()
        self.logger.critical(f"{' TRACEBACK ':!^80}")

        for line in sub_error:
            self.logger.critical("!!! %s", line)

        self.logger.critical("!" * 80)

    # =============================================================================
    def process_plotting_log(self, dev: indigo.Device = None, replies: bytes = b"", errors: str = "") -> bool | None:
        """Process and dispatch log messages returned from a chart subprocess.

        Parses the JSON log reply from a subprocess and routes each log-level list to the
        corresponding self.logger.* call. Updates the device state image based on whether any
        critical messages were received. Also handles select special stderr output patterns.

        Args:
            dev (indigo.Device): The Indigo device that triggered the chart subprocess.
            replies (bytes): The raw stdout bytes from the chart subprocess, expected to be JSON.
            errors (str): The stderr output from the chart subprocess.

        Returns:
            bool | None: True if the chart rendered without critical errors, False if a critical
                error occurred, or None if the reply could not be parsed.
        """
        # ======================= Process Output Queue ========================
        try:
            try:
                replies = json.loads(replies)
            except json.decoder.JSONDecodeError:
                return None
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
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorTripped)
                self.logger.critical("[%s] error producing chart. See logs for more information.", dev.name)
            else:
                dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                self.logger.info("[%s] chart refreshed.", dev.name)

            return success

        except EOFError:
            ...

        # Process any special output.
        if len(errors) > 0:
            if "FutureWarning: " in errors:
                self.logger.threaddebug(errors)

            elif "'numpy.float64' object cannot be interpreted as an index" in errors:
                self.logger.critical(
                    "[%s] Unfortunately, your version of Matplotlib doesn't support Polar chart plotting. "
                    "Disabling device.", dev.name
                )
                indigo.device.enable(dev, False)

            else:
                self.logger.critical(errors)
                dev.updateStateImageOnServer(indigo.kStateImageSel.Error)

        return None

    # =============================================================================
    @staticmethod
    def rc_params_device_update(dev: indigo.Device = None) -> None:  # noqa
        """Push all current matplotlib rcParams values to the rcParams device states.

        Updates each state on the rcParamsDevice with the corresponding current matplotlib
        rcParams value. State names were already created by getDeviceStateList(). This ensures
        future rcParams additions are automatically picked up.

        Args:
            dev (indigo.Device): The Indigo rcParams device instance to update.
        """
        state_list = []
        for key, value in rcParams.items():
            key = key.replace('.', '_')
            if key.startswith('_'):
                key = key[1:]
            state_list.append({'key': key, 'value': str(value)})

        state_list.append({'key': 'onOffState', 'value': True, 'uiValue': 'Updated'})
        dev.updateStatesOnServer(state_list)

    # =============================================================================
    def refreshAChartAction(self, plugin_action: indigo.ActionGroup = None) -> bool:  # noqa
        """Refresh a single chart device in response to an Indigo Action item call.

        Reads the target device from the action's deviceId and calls charts_refresh() for that
        device only. Logs a completion banner when finished.

        Args:
            plugin_action (indigo.ActionGroup): The Indigo action group specifying the target
                device to refresh.

        Returns:
            bool: Always False.
        """
        # Indigo will trap if device is disabled.
        dev = indigo.devices[plugin_action.deviceId]
        self.charts_refresh(dev_list=[dev])
        self.logger.info(f"{' Redraw a Chart Action Complete ':{'='}^80}")
        return False

    # =============================================================================
    def refresh_the_charts_now(self, plugin_action: indigo.ActionGroup = None, values_dict: indigo.Dict = None, menu_id: str = "", dev: indigo.Device = None, caller_waiting_for_result: bool = False) -> tuple:  # noqa
        """Trigger a chart refresh from the 'Redraw Charts Now...' plugin menu item or action.

        Validates that a refresh target is selected and adds the appropriate device list to the
        refresh queue. Supports 'all charts', 'skip manual charts', or a single selected chart.

        Args:
            plugin_action (indigo.ActionGroup): The action group object when called as an action.
            values_dict (indigo.Dict): The menu dialog values containing the 'allCharts' selection.
            menu_id (str): The menu identifier string (passed by Indigo).
            dev (indigo.Device): The Indigo device associated with the action (passed by Indigo).
            caller_waiting_for_result (bool): Whether the caller is waiting for a return value.

        Returns:
            tuple: (True, values_dict) on success, or (False, values_dict, error_msg_dict) if
                no target is selected.
        """
        if isinstance(plugin_action, indigo.ActionGroup):
            values_dict = plugin_action.props
        elif isinstance(plugin_action, indigo.Dict):
            values_dict = plugin_action
        elif plugin_action is not None:
            values_dict = plugin_action.props
        self.skipRefreshDateUpdate = True
        error_msg_dict = indigo.Dict()

        if not values_dict['allCharts']:
            error_msg_dict['allCharts'] = "Required"
            return False, values_dict, error_msg_dict

        # Skip charts set to manual updates
        if values_dict['allCharts'] == 'auto':
            devices_to_refresh = [
                dev for dev in indigo.devices.iter('self') if
                dev.enabled and dev.deviceTypeId != 'csvEngine' and
                int(dev.ownerProps.get('refreshInterval', "0")) > 0
            ]
            self.logger.info("Redraw Charts Now: Skipping manual charts.")

        # Refresh all charts regardless
        elif values_dict['allCharts'] == 'all':
            devices_to_refresh = [
                dev for dev in indigo.devices.iter('self') if
                dev.enabled and dev.deviceTypeId not in ['csvEngine', 'rcParamsDevice']
            ]
            self.logger.info("Redraw Charts Now: Redrawing all charts.")

        # Refresh selected chart device
        else:
            devices_to_refresh = [indigo.devices[int(values_dict['allCharts'])]]

        # Put the request in the queue
        self.refresh_queue.put(devices_to_refresh)
        return True, values_dict

    # =============================================================================
    def refresh_the_charts_queue(self) -> None:
        """Drain the chart refresh queue by processing all pending refresh requests.

        Spawns a daemon thread that calls charts_refresh() for each device list in the queue
        until the queue is empty.
        """
        def work_the_refresh_queue() -> None:
            while not self.refresh_queue.empty():
                queue_dev = self.refresh_queue.get()
                self.charts_refresh(queue_dev)

        t = threading.Thread(target=work_the_refresh_queue)
        t.daemon = True
        t.start()

    # =============================================================================
    def save_snapshot(self, action: indigo.ActionGroup = None) -> None:  # noqa
        """Save a diagnostic snapshot of plugin state to a file in the user's home directory.

        Writes the current pluginPrefs, matplotlib rcParams, and all plugin device props to
        ~/matplotlib_snapshot.txt for later debugging. Logs a confirmation message regardless of
        the current plugin debug level.

        Args:
            action (indigo.ActionGroup): The Indigo action group (passed by Indigo, not used).
        """
        home = os.path.expanduser("~")
        with open(home + "/matplotlib_snapshot.txt", 'w', encoding='utf-8') as outfile:
            outfile.write(f"{'pluginPrefs':50} - {dict(self.pluginPrefs)}\n")
            outfile.write(f"{'rcParams':50} - {rcParams}\n")

            for dev in indigo.devices.iter(filter="self"):
                outfile.write(f"{dev.name:50} - {dict(dev.ownerProps)}\n")

        # Write to log regardless of plugin debug level.
        indigo.server.log('Snapshot written to user home directory.')

    # =============================================================================
    @staticmethod
    def themeNameGenerator(fltr: str = "", values_dict: indigo.Dict = None, type_id: str = "", target_id: int = 0) -> list:  # noqa
        """Return a sorted list of theme names from the themes JSON file for UI dropdown controls.

        Reads the themes JSON file from the Indigo Preferences folder and returns a sorted list of
        (name, name) tuples for use in dialog dropdown controls.

        Args:
            fltr (str): Filter string passed by Indigo (not used directly).
            values_dict (indigo.Dict): The current dialog values (passed by Indigo).
            type_id (str): The type identifier string (passed by Indigo).
            target_id (int): The target device ID (passed by Indigo).

        Returns:
            list: A sorted list of (theme_name, theme_name) tuples.
        """
        return theme_handling.themeNameGenerator()

    # =============================================================================
    def themeManagerCloseUi(self, values_dict: indigo.Dict = None, menu_item_id: str = "") -> bool:  # noqa
        """Apply theme settings to pluginPrefs when the Theme Manager dialog is closed.

        Validates the color and line weight values, then copies the theme-related preference keys
        from the dialog values into pluginPrefs for persistence. User cancellation cannot be
        trapped for this dialog type.

        Args:
            values_dict (indigo.Dict): The Theme Manager dialog values.
            menu_item_id (str): The menu item identifier string (passed by Indigo).

        Returns:
            bool: Always True.
        """
        return theme_handling.themeManagerCloseUi(
            values_dict=values_dict, menu_item_id=menu_item_id, prefs=self.pluginPrefs
        )

    # =============================================================================
    def themeApplyAction(self, plugin_action: indigo.ActionGroup = None) -> None:  # noqa
        """Apply the selected theme to pluginPrefs via an Indigo Action item.

        Reads the selected theme name from the action props, retrieves the theme from the themes
        JSON file, and updates each theme key in pluginPrefs. Logs a warning if the theme is no
        longer valid.

        Args:
            plugin_action (indigo.ActionGroup): The Indigo action group containing the
                'targetTheme' selection.
        """
        theme_handling.themeApplyAction(plugin_action=plugin_action, prefs=self.pluginPrefs)

    # =============================================================================
    def themeApply(self, values_dict: indigo.Dict = None, menu_item_id: str = ""):  # noqa
        """Apply the selected theme from the Theme Manager dialog to pluginPrefs.

        Validates that exactly one theme is selected, loads the theme from the JSON file, validates
        its color and line weight values (the JSON file is user-editable and not otherwise
        constrained by the UI), and applies the result to both the dialog and pluginPrefs. Resets
        the allThemes control.

        Args:
            values_dict (indigo.Dict): The Theme Manager dialog values containing 'allThemes'.
            menu_item_id (str): The menu item identifier string (passed by Indigo).

        Returns:
            indigo.Dict | tuple: The updated values_dict on success, or a (values_dict,
                error_msg_dict) tuple if validation fails.
        """
        return theme_handling.themeApply(values_dict=values_dict, prefs=self.pluginPrefs)

    # =============================================================================
    def themeExecuteActionButton(self, values_dict: indigo.Dict = None, menu_item_id: str = 0) -> dict|tuple:  # noqa
        """Process the Theme Manager Execute Action button press.

        Validates the selected action and dispatches to the appropriate theme management method
        (apply, delete, rename, or save).

        Args:
            values_dict (indigo.Dict): Form values from the config UI dialog.
            menu_item_id (str): The menu item identifier (unused).

        Returns:
            dict | tuple: Updated values_dict, or a tuple of (values_dict, error_msg_dict) on
                validation failure.
        """
        return theme_handling.themeExecuteActionButton(values_dict=values_dict, prefs=self.pluginPrefs)
