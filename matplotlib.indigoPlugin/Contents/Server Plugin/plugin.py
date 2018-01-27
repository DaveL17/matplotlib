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
# TODO: NEW -- Standard chart types with pre-populated data that link to types of Indigo devices (like energy or battery health.)

# TODO: Consider hiding Y1 tick labels if Y2 is a mirror of Y1.
# TODO: consider ways to make variable CSV data file lengths or user settings to vary the number of observations shown (could be date range or number of obs).
# TODO: Look at fill with steps line style via the plugin API.
# TODO: Independent Y2 axis.
# TODO: Finer grained control over the legend.
# TODO: Variable refresh rates for each device so it can update on its own (including CSV engine).

# TODO: look at use of kv_list to ensure that all devices are updated properly
# TODO: trap condition where there are too many observations to plot ( i.e., too many x axis values)

# TODO: Linear transformations with multiplier and offset (e.g. <datum> * X + Y). Offset would be especially helpful for plotting multiple boolean values. Multiplier is nice for unit
#       conversion or just getting two plotlines in the same neighborhood if actual value is less important than trend or correlation.

# TODO: Be more agnostic about date formatting.  Look at dateutil.parser
# TODO: Better trap for CSV data that doesn't have a properly formatted date column.
# TODO: What happens when the style sheet is set to read only and a new version of the plugin is installed?

# TODO: Scatter charts: don't need GroupXColor? Seems to use only GroupXMarkerColor. Consider deleting GroupXColor?
# TODO: Scatter charts: Y axis tick locations instructions are not right.

# ================================== IMPORTS ==================================

# Built-in modules
from ast import literal_eval
from csv import reader
import datetime as dt
import logging
import multiprocessing
import numpy as np
import traceback
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
__version__   = "0.5.03"

# =============================================================================

kDefaultPluginPrefs = {
    u'annotationColorOther': "#FFFFFF",
    u'backgroundColor': "#000000",
    u'backgroundColorOther': "#000000",
    u'chartPath': "/Library/Application Support/Perceptive Automation/Indigo 7/IndigoWebServer/images/controls/static/",
    u'chartResolution': 100,
    u'dataPath': "{0}/com.fogbert.indigoplugin.matplotlib/".format(indigo.server.getLogsFolderPath()),
    u'enableCustomLineSegments': False,
    u'faceColor': "#000000",
    u'faceColorOther': "#000000",
    u'fontColor': "#FFFFFF",
    u'fontColorAnnotation': "#FFFFFF",
    u'fontColorOther': "#FFFFFF",
    u'fontMain': "Arial",
    u'forceOriginLines': False,
    u'gridColor': "#888888",
    u'gridColorOther': "#888888",
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
    u'spineColor': "#888888",
    u'spineColorOther': "#888888",
    u'sqChartSize': 250,
    u'tickColor': "#888888",
    u'tickColorOther': "#888888",
    u'tickFontSize': 8,
    u'tickSize': 4
}


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        updater_url = "https://davel17.github.io/matplotlib/matplotlib_version.html"
        self.updater = indigoPluginUpdateChecker.updateChecker(self, updater_url)

        self.plugin_file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug      = True
        self.debugLevel = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debugLevel)
        self.verboseLogging = self.pluginPrefs.get('verboseLogging', False)
        self.sleep_interval = self.pluginPrefs.get('refreshInterval', 900)

        # ====================== Initialize DLFramework =======================

        self.Fogbert = Dave.Fogbert(self)

        # Log pluginEnvironment information when plugin is first started
        self.Fogbert.pluginEnvironment()

        # Convert old debugLevel scale (low, medium, high) to new scale (1, 2, 3).
        if not int(self.pluginPrefs.get('showDebugLevel')):
            self.pluginPrefs['showDebugLevel'] = self.Fogbert.convertDebugLevel(self.debugLevel)

        # =====================================================================

        self.logger.info(u"")
        self.logger.info(u"{0:=^130}".format(" Matplotlib Environment "))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib version:", plt.matplotlib.__version__))
        self.logger.info(u"{0:<31} {1}".format("Numpy version:", np.__version__))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin version:", self.pluginVersion))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib RC Path:", plt.matplotlib.matplotlib_fname()))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin log location:", indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')))
        self.logger.debug(u"{0:<31} {1}".format("Matplotlib base rcParams:", dict(rcParams)))  # rcParams is a dict containing all of the initial matplotlibrc settings
        self.logger.info(u"{0:=^130}".format(""))

        self.final_data = []

        # Initially, the plugin was constructed with a standard set of colors that could be overwritten by electing to set a custom color value.
        # With the inclusion of the color picker control, this is no longer needed.  So we try to set the color field to the custom value.
        # This block is for plugin color preferences.
        if '#custom' in self.pluginPrefs.values():
            for pref in self.pluginPrefs:
                if 'color' in pref.lower():
                    if self.pluginPrefs[pref] in['#custom', 'custom']:
                        indigo.server.log(u"Resetting plugin preferences for custom colors to new color picker.")
                        if self.pluginPrefs[u'{0}Other'.format(pref)]:
                            self.pluginPrefs[pref] = self.pluginPrefs[u'{0}Other'.format(pref)]
                        else:
                            self.pluginPrefs[pref] = 'FF FF FF'

        # try:
        #     pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)
        # except:
        #     pass

    def __del__(self):
        indigo.PluginBase.__del__(self)

# Indigo Methods ==============================================================

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        """This routine will be called whenever the user has closed the device
        config dialog either by save or cancel. Note that a device can't be
        updated from here because valuesDict has yet to be saved."""
        self.logger.debug(u"{0:*^40}".format(' Closed Device Configuration Dialog '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"userCancelled = {0}  typeId = {1}  devId = {2}".format(userCancelled, typeId, devId))

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        """ User closes config menu. The validatePrefsConfigUI() method will
        also be called."""
        self.sleep_interval = valuesDict['refreshInterval']

        # If the user selects Save, let's redraw the charts so that they reflect the new settings.
        if not userCancelled:
            self.logger.info(u"{0:=^80}".format(' Configuration Saved '))

    def deviceStartComm(self, dev):
        """ Start communication with plugin devices."""
        self.logger.debug(u"Starting device: {0}".format(dev.name))
        dev.stateListOrDisplayStateIdChanged()
        dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Enabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    def deviceStopComm(self, dev):
        """ Stop communication with plugin devices."""
        self.logger.debug(u"Stopping device: {0}".format(dev.name))
        dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])
        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)

    def getDeviceConfigUiValues(self, valuesDict, typeId, devId):
        """The getDeviceConfigUiValues() method is called when a device config
        is opened."""

        self.logger.debug(u"{0:*^40}".format(' Plugin Settings Menu '))
        if self.verboseLogging:
            self.logger.threaddebug(u"pluginProps = {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {0}".format(typeId, devId))

        dev = indigo.devices[int(devId)]
        indigo.server.log(str(dev.configured))

        try:

            # Make sure that the data entry fields of the CVS Engine device are in the proper state when the dialog is opened.
            if typeId == "csvEngine":
                valuesDict['addItemFieldsCompleted'] = False
                valuesDict['addKey']                 = ""
                valuesDict['addSource']              = ""
                valuesDict['addState']               = ""
                valuesDict['addValue']               = ""
                valuesDict['columnList']             = ""
                valuesDict['editKey']                = ""
                valuesDict['editSource']             = ""
                valuesDict['editState']              = ""
                valuesDict['editValue']              = ""
                valuesDict['isColumnSelected']       = False
                valuesDict['previousKey']            = ""
                self.logger.debug(u"Analyzing CSV Engine device settings.")
                return valuesDict

            # For new devices, force certain defaults that don't carry from devices.xml. This seems to be especially important for
            # menu items built with callbacks and colorpicker controls that don't appear to accept defaultValue.
            if not dev.configured:
                if typeId == "barChartingDevice":
                    valuesDict['bar1Color']           = 'FF FF FF'
                    valuesDict['bar1Source']          = 'None'
                    valuesDict['bar2Color']           = 'FF FF FF'
                    valuesDict['bar2Source']          = 'None'
                    valuesDict['bar3Color']           = 'FF FF FF'
                    valuesDict['bar3Source']          = 'None'
                    valuesDict['bar4Color']           = 'FF FF FF'
                    valuesDict['bar4Source']          = 'None'
                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                if typeId == "calendarChartingDevice":
                    valuesDict['fontSize'] = 16

                if typeId == "lineChartingDevice":
                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['line1Color']          = 'FF FF FF'
                    valuesDict['line1Marker']         = 'None'
                    valuesDict['line1MarkerColor']    = 'FF FF FF'
                    valuesDict['line1Source']         = 'None'
                    valuesDict['line1Style']          = '-'
                    valuesDict['line2Color']          = 'FF FF FF'
                    valuesDict['line2Marker']         = 'None'
                    valuesDict['line2MarkerColor']    = 'FF FF FF'
                    valuesDict['line2Source']         = 'None'
                    valuesDict['line2Style']          = '-'
                    valuesDict['line3Color']          = 'FF FF FF'
                    valuesDict['line3Marker']         = 'None'
                    valuesDict['line3MarkerColor']    = 'FF FF FF'
                    valuesDict['line3Source']         = 'None'
                    valuesDict['line3Style']          = '-'
                    valuesDict['line4Color']          = 'FF FF FF'
                    valuesDict['line4Marker']         = 'None'
                    valuesDict['line4MarkerColor']    = 'FF FF FF'
                    valuesDict['line4Source']         = 'None'
                    valuesDict['line4Style']          = '-'
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                if typeId == "multiLineText":
                    valuesDict['textColor']  = "FF 00 FF"
                    valuesDict['thing']      = 'None'
                    valuesDict['thingState'] = 'None'

                if typeId == "polarChartingDevice":
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['currentWindColor']    = 'FF 33 33'
                    valuesDict['maxWindColor']        = '33 33 FF'
                    valuesDict['radiiValue']          = 'None'
                    valuesDict['thetaValue']          = 'None'

                if typeId == "scatterChartingDevice":
                    valuesDict['customLineStyle']     = '-'
                    valuesDict['customTickFontSize']  = 8
                    valuesDict['customTitleFontSize'] = 10
                    valuesDict['group1Color']         = 'FF FF FF'
                    valuesDict['group1Marker']        = '.'
                    valuesDict['group1MarkerColor']   = 'FF FF FF'
                    valuesDict['group1Source']        = 'None'
                    valuesDict['group2Color']         = 'FF FF FF'
                    valuesDict['group2Marker']        = '.'
                    valuesDict['group2MarkerColor']   = 'FF FF FF'
                    valuesDict['group2Source']        = 'None'
                    valuesDict['group3Color']         = 'FF FF FF'
                    valuesDict['group3Marker']        = '.'
                    valuesDict['group3MarkerColor']   = 'FF FF FF'
                    valuesDict['group3Source']        = 'None'
                    valuesDict['group4Color']         = 'FF FF FF'
                    valuesDict['group4Marker']        = '.'
                    valuesDict['group4MarkerColor']   = 'FF FF FF'
                    valuesDict['group4Source']        = 'None'
                    valuesDict['xAxisBins']           = 'daily'
                    valuesDict['xAxisLabelFormat']    = '%A'

                if typeId == "forecastChartingDevice":
                    valuesDict['customLineStyle']      = '-'
                    valuesDict['customTickFontSize']   = 8
                    valuesDict['customTitleFontSize']  = 10
                    valuesDict['forecastSourceDevice'] = 'None'
                    valuesDict['line1Color']           = 'FF 33 33'
                    valuesDict['line1Marker']          = 'None'
                    valuesDict['line1MarkerColor']     = 'FF FF FF'
                    valuesDict['line1Style']           = '-'
                    valuesDict['line2Color']           = '00 00 FF'
                    valuesDict['line2Marker']          = 'None'
                    valuesDict['line2MarkerColor']     = 'FF FF FF'
                    valuesDict['line2Style']           = '-'
                    valuesDict['line3Color']           = '99 CC FF'
                    valuesDict['line3MarkerColor']     = 'FF FF FF'
                    valuesDict['xAxisBins']            = 'daily'
                    valuesDict['xAxisLabelFormat']     = '%A'

            if self.pluginPrefs.get('enableCustomLineSegments', False):
                valuesDict['enableCustomLineSegmentsSetting'] = True
                self.logger.debug(u"Enabling advanced feature: Custom Line Segments.")
            else:
                valuesDict['enableCustomLineSegmentsSetting'] = False

            # If enabled, reset all device config dialogs to a minimized state (all sub-groups minimized upon open.)
            if self.pluginPrefs.get('snappyConfigMenus', False):
                self.logger.debug(u"Enabling advanced feature: Snappy Config Menus.")
                valuesDict['barLabel1']   = False
                valuesDict['barLabel2']   = False
                valuesDict['barLabel3']   = False
                valuesDict['barLabel4']   = False
                valuesDict['lineLabel1']  = False
                valuesDict['lineLabel2']  = False
                valuesDict['lineLabel3']  = False
                valuesDict['lineLabel4']  = False
                valuesDict['groupLabel1'] = False
                valuesDict['groupLabel2'] = False
                valuesDict['groupLabel3'] = False
                valuesDict['groupLabel4'] = False
                valuesDict['xAxisLabel']  = False
                valuesDict['y2AxisLabel'] = False
                valuesDict['yAxisLabel']  = False

            return valuesDict

        except KeyError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.debug(u"!!!!! KeyError preparing device config values: {0} !!!!!".format(sub_error))

        return True

    def getMenuActionConfigUiValues(self, menuId):
        """The getMenuActionConfigUiValues() method loads the settings
        for the advanced settings menu dialog. Populates them, and
        sends them to the dialog as it's loaded."""
        self.logger.debug(u"{0:*^80}".format(' Advanced Settings Menu '))
        self.logger.debug(u"menuId = {0}".format(menuId))

        settings     = indigo.Dict()
        error_msg_dict = indigo.Dict()
        settings['enableCustomLineSegments'] = self.pluginPrefs.get('enableCustomLineSegments', False)
        settings['promoteCustomLineSegments'] = self.pluginPrefs.get('promoteCustomLineSegments', False)
        settings['snappyConfigMenus'] = self.pluginPrefs.get('snappyConfigMenus', False)
        settings['forceOriginLines'] = self.pluginPrefs.get('forceOriginLines', False)
        self.logger.debug(u"Advanced settings menu initial prefs: {0}".format(dict(settings)))

        return settings, error_msg_dict

    def getPrefsConfigUiValues(self):
        """getPrefsConfigUiValues(self) is called when the plugin config dialog
        is called."""
        self.logger.debug(u"{0:=^80}".format(' Get Prefs Config UI Values '))

        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        self.logger.threaddebug(u"Initial plugin_prefs: {0}".format(dict(plugin_prefs)))

        # Establish a set of defaults for select plugin settings. Only those settings that are populated dynamically need to be set here (the others can be set directly by the XML.)
        defaults_dict = {'annotationColorOther': 'FF FF FF',
                         'backgroundColor': '00 00 00',
                         'backgroundColorOther': '00 00 00',
                         'faceColor': '00 00 00',
                         'faceColorOther': '00 00 00',
                         'fontColor': 'FF FF FF',
                         'fontColorAnnotation': 'FF FF FF',
                         'fontColorOther': 'FF FF FF',
                         'fontMain': 'Arial',
                         'gridColor': '88 88 88',
                         'gridStyle': ':',
                         'legendFontSize': '6',
                         'mainFontSize': '10',
                         'spineColor': '88 88 88',
                         'spineColorOther': '88 88 88',
                         'tickColor': '88 88 88',
                         'tickColorOther': '88 88 88',
                         'tickFontSize': '8'}

        # Try to assign the value from plugin_prefs. If it doesn't work, add the key, value pair based on the defaults_dict above.
        # This should only be necessary the first time the plugin is configured.
        for key, value in defaults_dict.items():
            plugin_prefs[key] = plugin_prefs.get(key, value)

        self.logger.threaddebug(u"Updated initial plugin_prefs: {0}".format(dict(plugin_prefs)))
        return plugin_prefs

    def runConcurrentThread(self):
        """"""
        self.logger.info(u"{0:=^80}".format(' Initializing Main Thread '))
        self.sleep(0.5)

        try:
            while True:
                self.updater.checkVersionPoll()

                try:
                    self.sleep_interval = int(self.pluginPrefs.get('refreshInterval', '900'))
                except ValueError:
                    self.sleep_interval = 0

                # If sleep interval is zero, the user must update all charts manually
                if self.sleep_interval != 0:
                    self.refreshTheCSV()
                    self.refreshTheCharts()
                    self.logger.info(u"{0:=^80}".format(' Cycle Complete '))
                    self.sleep(self.sleep_interval)
                    self.logger.info(u"{0:=^80}".format(' Cycling Main Thread '))
                else:
                    # Check once per minute to break out if user changes
                    # preference and plugin doesn't refresh on its own
                    self.sleep(60)

        except self.StopThread():
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.debug(u"self.stopThread() called.")

    def startup(self):
        """ Plugin startup routines."""

        # Initially, the plugin was constructed with a standard set of colors that could be overwritten by electing to set a custom color value.
        # With the inclusion of the color picker control, this is no longer needed.  So we try to set the color field to the custom value.
        # This block is for device color preferences. They should be updated whether or not the device is enabled in the Indigo UI.
        for dev in indigo.devices.itervalues("self"):
            props = dev.pluginProps

            if '#custom' in props.values() or 'custom' in props.values():
                for prop in props:
                    if 'color' in prop.lower():
                        if props[prop] in ['#custom', 'custom']:
                            indigo.server.log(u"Resetting device preferences for custom colors to new color picker.")
                            if props[u'{0}Other'.format(prop)]:
                                props[prop] = props[u'{0}Other'.format(prop)]
                            else:
                                props[prop] = 'FF FF FF'
            dev.replacePluginPropsOnServer(props)


        self.updater.checkVersionPoll()
        self.logger.debug(u"{0}{1}".format("Log Level = ", self.debugLevel))

    def shutdown(self):
        """ Plugin shutdown routines."""
        self.logger.debug(u"{0:*^40}".format(' Shut Down '))

    def validatePrefsConfigUi(self, valuesDict):
        """ Validate select plugin config menu settings."""
        self.debugLevel = int(valuesDict['showDebugLevel'])
        self.indigo_log_handler.setLevel(self.debugLevel)
        self.logger.info(u"Debug level set to: {0}".format(self.debugLevel))

        error_msg_dict = indigo.Dict()

        # Data and chart paths.
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

        # Chart resolution.  Note that chart resolution includes a warning feature that will pass the value after the warning is cleared.
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

        # Chart dimension properties.
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

        # Line weight.
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
        return True, valuesDict

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        """ Validate select device config menu settings."""
        self.logger.debug(u"{0:*^40}".format(' Validate Device Config UI '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        error_msg_dict = indigo.Dict()

        # Bar Chart Device
        if typeId == 'barChartingDevice':
            if valuesDict['bar1Source'] == 'None':
                error_msg_dict['bar1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

        # Line Chart Device
        if typeId == 'lineChartingDevice':
            if valuesDict['line1Source'] == 'None':
                error_msg_dict['line1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

        # Polar Chart Device
        if typeId == 'polarChartingDevice':
            if not valuesDict['thetaValue']:
                error_msg_dict['thetaValue'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Direction Source Error.\n\nYou must select a direction source for charting."
                return False, valuesDict, error_msg_dict

            if not valuesDict['radiiValue']:
                error_msg_dict['radiiValue'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Magnitude Source Error.\n\nYou must select a magnitude source for charting."
                return False, valuesDict, error_msg_dict

        # Scatter Chart Device
        if typeId == 'scatterChartingDevice':
            if not valuesDict['group1Source']:
                error_msg_dict['group1Source'] = u"You must select at least one data source."
                error_msg_dict['showAlertText'] = u"Data Source Error.\n\nYou must select at least one source for charting."
                return False, valuesDict, error_msg_dict

        # Multiline Text
        if typeId == 'multiLineText':
            if not valuesDict['thing']:
                error_msg_dict['thing'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Source Error.\n\nYou must select a text source for charting."
                return False, valuesDict, error_msg_dict

            if not valuesDict['thingState']:
                error_msg_dict['thingState'] = u"You must select a data source."
                error_msg_dict['showAlertText'] = u"Text to Chart Error.\n\nYou must select a text source for charting."
                return False, valuesDict, error_msg_dict

        # Weather Chart Device
        if typeId == 'forecastChartingDevice':
            if not valuesDict['forecastSourceDevice']:
                error_msg_dict['forecastSourceDevice'] = u"You must select a weather forecast source device."
                error_msg_dict['showAlertText'] = u"Forecast Device Source Error.\n\nYou must select a weather forecast source device for charting."
                return False, valuesDict, error_msg_dict

        # Chart Custom Dimensions
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

        return True, valuesDict

# Plugin methods ==============================================================

    def advancedSettingsExecuted(self, valuesDict, menuId):
        """The advancedSettingsExecuted() method is a place where advanced
        settings will be controlled. This method takes the returned values
        and sends them to the pluginPrefs for permanent storage."""
        # Note that valuesDict here is for the menu, not all plugin prefs.
        # self.logger.threaddebug(u"menuId = {0}".format(menuId))

        self.pluginPrefs['enableCustomLineSegments']  = valuesDict['enableCustomLineSegments']
        self.pluginPrefs['promoteCustomLineSegments'] = valuesDict['promoteCustomLineSegments']
        self.pluginPrefs['snappyConfigMenus']         = valuesDict['snappyConfigMenus']
        self.pluginPrefs['forceOriginLines']          = valuesDict['forceOriginLines']

        self.logger.debug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        return True

    def advancedSettingsMenu(self, valuesDict, typeId="", devId=None):
        """The advancedSettingsMenu() method is called when actions are taken
        within the Advanced Settings Menu item from the plugin menu."""
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        self.logger.debug(u"Enable custom line segments: {0}".format(valuesDict['enableCustomLineSegments']))
        self.logger.debug(u"Enable snappy config menus: {0}".format(valuesDict['snappyConfigMenus']))
        self.logger.debug(u"Enable force origin lines: {0}".format(valuesDict['forceOriginLines']))
        self.logger.threaddebug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        return

    def checkVersionNow(self):
        """ The checkVersionNow() method will call the Indigo Plugin Update
        Checker based on a user request. """

        self.updater.checkVersionNow()

    def addColumn(self, valuesDict, typeId="", devId=None):
        """The addColumn() method is called when the user clicks on the "Add
        Column" button in the CSV Engine config dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Add Column List Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

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
            self.logger.warning(u"Error adding column. {0}".format(sub_error))

        # Wipe the field values clean for the next element to be added.
        for key in ['addValue', 'addSource', 'addState']:
            valuesDict[key] = u""

        return valuesDict, error_msg_dict

    def columnList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """The columnList() method generates the list of Column Key : Column
        Value pairs that will be presented in the CVS Engine device config
        dialog. It's called at open and routinely as changes are made in the
        dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Column List Generated '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))

        try:
            # valuesDict['columnDict'] = valuesDict.get('columnDict', '{"k0": ("None", "None", "None")}')  # Just in case the user has deleted all CSV Engine elements
            valuesDict['columnDict'] = valuesDict.get('columnDict', '{}')  # Returning an empty dict seems to work and may solve the 'None' issue
            column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.
            prop_list   = [(key, "{0}".format(value[0].encode("utf-8"))) for key, value in column_dict.items()]
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error generating column list. {0}".format(sub_error))
            prop_list = []
        return sorted(prop_list, key=lambda tup: tup[1])  # Return a list sorted by the value and not the key.

    def deleteColumn(self, valuesDict, typeId="", devId=None):
        """The deleteColumn() method is called when the user clicks on the
        "Delete Column" button in the CSV Engine config dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Delete Column List Item '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            valuesDict["editKey"] = valuesDict["columnList"]
            del column_dict[valuesDict['editKey']]
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error deleting column. {0}".format(sub_error))

        valuesDict['columnList']  = ""
        valuesDict['editKey']     = ""
        valuesDict['editSource']  = ""
        valuesDict['editState']   = ""
        valuesDict['editValue']   = ""
        valuesDict['previousKey'] = ""
        valuesDict['columnDict']  = str(column_dict)  # Convert column_dict back to a string for storage.

        return valuesDict

    def selectColumn(self, valuesDict, typeId="", devId=None):
        """The selectColumn() method is called when the user actually selects
        something within the Column List dropdown menu."""
        self.logger.debug(u"{0:*^40}".format(' Select Column '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        try:
            column_dict                    = literal_eval(valuesDict['columnDict'])
            valuesDict['editKey']          = valuesDict['columnList']
            valuesDict['editSource']       = column_dict[valuesDict['columnList']][1]
            valuesDict['editState']        = column_dict[valuesDict['columnList']][2]
            valuesDict['editValue']        = column_dict[valuesDict['columnList']][0]
            valuesDict['isColumnSelected'] = True
            valuesDict['previousKey']      = valuesDict['columnList']
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"There was an error establishing a connection with the item you chose. {0}".format(sub_error))
        return valuesDict

    def updateColumn(self, valuesDict, typeId="", devId=None):
        """The updateColumn() method is called when the user clicks on the
        "Update Column" button in the CSV Engine config dialog."""
        self.logger.debug(u"{0:*^40}".format(' Update Column '))
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

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
                column_dict[key]         = (valuesDict['editValue'], valuesDict['editSource'], valuesDict['editState'])
                valuesDict['columnList'] = ""
                valuesDict['editKey']    = ""
                valuesDict['editSource'] = ""
                valuesDict['editState']  = ""
                valuesDict['editValue']  = ""

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

    def csvSource(self, typeId, valuesDict, devId, targetId):
        """"""
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}  targetId = {2}".format(typeId, devId, targetId))

        list_of = []

        [list_of.append((dev.id, u"(D) {0}".format(dev.name))) for dev in indigo.devices.iter()]
        [list_of.append((var.id, u"(V) {0}".format(var.name))) for var in indigo.variables.iter()]

        return list_of

    def csvSourceIdUpdated(self, typeId, valuesDict, devId):
        """"""
        pass

    def deviceStateValueList(self, typeId, valuesDict, devId, targetId):
        """"""
        if self.verboseLogging:
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
            self.logger.threaddebug(u"typeId = {0}  devId = {1}  targetId = {2}".format(typeId, devId, targetId))

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

    def getDeviceStateList(self, dev):
        """ getDeviceStateList is called automatically by
        dev.stateListOrDisplayStateIdChanged().
        """
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

    def killAllComms(self):
        """ killAllComms() sets the enabled status of all plugin devices to
        false. """

        for dev in indigo.devices.itervalues("self"):
            try:
                indigo.device.enable(dev, value=False)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Exception when trying to kill all comms. Error: {0}".format(sub_error))

    def unkillAllComms(self):
        """ unkillAllComms() sets the enabled status of all plugin devices to
        true. """

        for dev in indigo.devices.itervalues("self"):
            try:
                indigo.device.enable(dev, value=True)
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Exception when trying to kill all comms. Error: {0}".format(sub_error))

    def rcParamsDeviceUpdate(self, dev):
        """ Push the rcParams settings to the rcParams Device. The state names
        have already been created by getDeviceStateList() which will ensure that
        future rcParams will be picked up if they're ever added to the file."""
        state_list = []
        for key, value in rcParams.iteritems():
            key = key.replace('.', '_')
            state_list.append({'key': key, 'value': str(value)})
            dev.updateStatesOnServer(state_list)

        dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}])

    def refreshTheCSV(self):
        """ The refreshTheCSV() method manages CSV files through CSV Engine
        custom devices. """
        self.logger.debug(u"{0:*^40}".format(' Refresh the CSV '))

        for dev in indigo.devices.itervalues("self"):
            if dev.deviceTypeId == 'csvEngine' and dev.enabled:
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                import os
                csv_dict_str  = dev.pluginProps['columnDict']   # {key: (Column Name, Source ID, Source State)}
                csv_dict      = literal_eval(csv_dict_str)  # Convert column_dict from a string to a literal dict.

                # Read through the dict and construct headers and data
                for k, v in sorted(csv_dict.items()):

                    # Create a path variable that is based on the target folder and the CSV column name.
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
                        # if state_to_write == 'None':
                        #     state_to_write = 'NaN'
                        # if not state_to_write:
                        #     state_to_write = 'NaN'

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

    def refreshTheCharts(self, chart_id=None):
        """
        Refreshes all the charts.
        The keyValueList is a new Indigo API hook which allows the plugin to
        update all custom device states in one go.
        keyValueList = [{'key': 'someKey1', 'value': True},
                        {'key': 'someKey2', 'value': 456},
                        {'key': 'someKey3', 'value': 789.123, 'uiValue': "789.12 lbs", 'decimalPlaces': 2}
                        ]
        dev.updateStatesOnServer(keyValueList)
        """
        self.verboseLogging = self.pluginPrefs.get('verboseLogging', False)
        return_queue = multiprocessing.Queue()

        # A specific chart id may be passed to the method. In that case, refresh only that chart. Otherwise, chart_id is None and we refresh all of the charts.
        dev_list = []
        if not chart_id:
            for dev in indigo.devices.itervalues('self'):
                dev_list.append(dev)
        else:
            dev_list.append(indigo.devices[int(chart_id)])

        k_dict  = {}  # A dict of kwarg dicts
        p_dict  = dict(self.pluginPrefs)  # A dict of plugin preferences (we set defaults and override with pluginPrefs).

        p_dict['font_style']  = 'normal'
        p_dict['font_weight'] = 'normal'
        p_dict['tick_bottom'] = 'on'
        p_dict['tick_left']   = 'on'
        p_dict['tick_right']  = 'off'
        p_dict['tick_top']    = 'off'

        if self.verboseLogging:
            self.logger.threaddebug(u"{0:<19}{1}".format("Starting rcParams: ", dict(plt.rcParams)))
            self.logger.threaddebug(u"{0:<19}{1}".format("Starting p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

        # rcParams overrides
        plt.rcParams['grid.linestyle']   = self.pluginPrefs.get('gridStyle', ':')
        plt.rcParams['lines.linewidth']  = float(self.pluginPrefs.get('lineWeight', '1'))
        plt.rcParams['savefig.dpi']      = int(self.pluginPrefs.get('chartResolution', '100'))
        plt.rcParams['xtick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
        plt.rcParams['ytick.major.size'] = int(self.pluginPrefs.get('tickSize', '8'))
        plt.rcParams['xtick.minor.size'] = plt.rcParams['xtick.major.size'] / 2
        plt.rcParams['ytick.minor.size'] = plt.rcParams['ytick.major.size'] / 2
        plt.rcParams['xtick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))
        plt.rcParams['ytick.labelsize']  = int(self.pluginPrefs.get('tickFontSize', '8'))

        plt.rcParams['grid.color'] = r"#{0}".format(self.pluginPrefs.get('gridColor', '88 88 88').replace(' ', '').replace('#', ''))
        plt.rcParams['xtick.color'] = r"#{0}".format(self.pluginPrefs.get('tickColor', '88 88 88').replace(' ', '').replace('#', ''))
        plt.rcParams['ytick.color'] = r"#{0}".format(self.pluginPrefs.get('tickColor', '88 88 88').replace(' ', '').replace('#', ''))

        p_dict['fontColor'] = r"#{0}".format(self.pluginPrefs.get('fontColor', 'FF FF FF').replace(' ', '').replace('#', ''))
        p_dict['fontColorAnnotation'] = r"#{0}".format(self.pluginPrefs.get('fontColorAnnotation', 'FF FF FF').replace(' ', '').replace('#', ''))
        p_dict['gridColor'] = r"#{0}".format(self.pluginPrefs.get('gridColor', '88 88 88').replace(' ', '').replace('#', ''))
        p_dict['spineColor'] = r"#{0}".format(self.pluginPrefs.get('spineColor', '88 88 88').replace(' ', '').replace('#', ''))

        # Background color?
        if not self.pluginPrefs.get('backgroundColorOther', 'false'):
            p_dict['transparent_charts'] = False
            p_dict['backgroundColor'] = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
        elif self.pluginPrefs.get('backgroundColorOther', 'false') == 'false':
            p_dict['transparent_charts'] = False
            p_dict['backgroundColor'] = r"#{0}".format(self.pluginPrefs.get('backgroundColor', 'FF FF FF').replace(' ', '').replace('#', ''))
        else:
            p_dict['transparent_charts'] = True
            p_dict['backgroundColor'] = '#000000'

        # Plot Area color?
        if not self.pluginPrefs.get('faceColorOther', 'false'):
            p_dict['transparent_filled'] = True
            p_dict['faceColor'] = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
        elif self.pluginPrefs.get('faceColorOther', 'false') == 'false':
            p_dict['transparent_filled'] = True
            p_dict['faceColor'] = r"#{0}".format(self.pluginPrefs.get('faceColor', 'false').replace(' ', '').replace('#', ''))
        else:
            p_dict['transparent_filled'] = False
            p_dict['faceColor'] = '00 00 00'

        if self.verboseLogging:
            self.logger.threaddebug(u"{0:<19}{1}".format("Updated rcParams:  ", dict(plt.rcParams)))
            self.logger.threaddebug(u"{0:<19}{1}".format("Updated p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

        for dev in dev_list:

            if dev.deviceTypeId != 'csvEngine' and dev.enabled:
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

            # Custom font sizes for retina/non-retina adjustments.
            try:
                if dev.pluginProps['customSizeFont']:
                    p_dict['mainFontSize'] = int(dev.pluginProps['customTitleFontSize'])
                    plt.rcParams['xtick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                    plt.rcParams['ytick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
            except KeyError:
                # Not all devices may support this feature.
                pass

            # kwargs
            # Note: PyCharm wants attribute values to be strings. This is not always what Matplotlib wants (i.e., bbox alpha and linewidth should be floats.)
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

            # matplotlib.rc overrides.
            plt.rc('font', **k_dict['k_base_font'])

            p_dict.update(dev.pluginProps)

            p_dict['bar_colors']        = []
            p_dict['customTicksLabelY'] = []
            p_dict['customTicksY']      = []
            p_dict['data_array']        = []
            p_dict['dates_to_plot']     = []
            p_dict['fileName']          = ''
            p_dict['headers']           = []
            p_dict['headers_1']         = ()  # Tuple
            p_dict['headers_2']         = ()  # Tuple
            p_dict['wind_direction']    = []
            p_dict['wind_speed']        = []
            p_dict['x_obs1']            = []
            p_dict['x_obs2']            = []
            p_dict['x_obs3']            = []
            p_dict['x_obs4']            = []
            p_dict['y_obs1']            = []
            p_dict['y_obs1_max']        = []
            p_dict['y_obs1_min']        = []
            p_dict['y_obs2']            = []
            p_dict['y_obs2_max']        = []
            p_dict['y_obs2_min']        = []
            p_dict['y_obs3']            = []
            p_dict['y_obs3_max']        = []
            p_dict['y_obs3_min']        = []
            p_dict['y_obs4']            = []
            p_dict['y_obs4_max']        = []
            p_dict['y_obs4_min']        = []

            if dev.enabled and dev.model != "CSV Engine":

                try:
                    kv_list = []  # A list of state/value pairs used to feed updateStatesOnServer()
                    kv_list.append({'key': 'onOffState', 'value': True, 'uiValue': 'Updated'})
                    p_dict.update(dev.pluginProps)

                    # Limit number of observations
                    try:
                        p_dict['numObs'] = int(p_dict['numObs'])
                    except KeyError:
                        # Only some devices will have their own numObs.
                        pass
                    except ValueError:
                        self.pluginErrorHandler(traceback.format_exc())
                        self.logger.warning(u"The number of observations must be a positive number.")

                    # Custom Square Size
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

                    # Extra Wide Chart
                    try:
                        if p_dict['rectWide']:
                            p_dict['chart_height'] = float(p_dict['rectChartWideHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWideWidth'])
                        else:
                            p_dict['chart_height'] = float(p_dict['rectChartHeight'])
                            p_dict['chart_width']  = float(p_dict['rectChartWidth'])
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                    # If the user has specified a custom size, let's override with their custom setting.
                    try:
                        if p_dict['customSizeHeight'] != 'None':
                            p_dict['chart_height'] = float(p_dict['customSizeHeight'])
                        if p_dict['customSizeWidth'] != 'None':
                            p_dict['chart_width'] = float(p_dict['customSizeWidth'])
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                    # Since users may or may not include axis labels and because we want to ensure that all plot areas present in the same way, we need to create 'phantom' labels that
                    # are plotted but not visible.  Setting the font color to 'None' will effectively hide them.
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

                    # If the user wants annotations, we need to hide the line markers as we don't want to plot one on top of the other.
                    for line in range(1, 5, 1):
                        try:
                            if p_dict['line{0}Annotate'.format(line)] and p_dict['line{0}Marker'.format(line)] != 'None':
                                p_dict['line{0}Marker'.format(line)] = 'None'
                                self.logger.warning(u"{0}: Line {1} marker is suppressed to display annotations. "
                                                    u"To see the marker, disable annotations for this line.".format(dev.name, line))
                        except KeyError:
                            self.pluginErrorHandler(traceback.format_exc())

                    # Some line markers need to be adjusted due to their inherent value.  For example, matplotlib uses '<', '>' and '.' as markers but storing these values will blow up
                    # the XML.  So we need to convert them. (See self.fixTheMarkers() method.)
                    try:
                        if p_dict['line1Marker'] != 'None' or p_dict['line2Marker'] != 'None' or p_dict['line3Marker'] != 'None:' or p_dict['line4Marker'] != 'None:':
                            p_dict['line1Marker'], p_dict['line2Marker'], p_dict['line3Marker'], p_dict['line4Marker'] = self.fixTheMarkers(p_dict['line1Marker'],
                                                                                                                                            p_dict['line2Marker'],
                                                                                                                                            p_dict['line3Marker'],
                                                                                                                                            p_dict['line4Marker'])
                    except KeyError:
                        pass

                    try:
                        if p_dict['group1Marker'] != 'None' or p_dict['group2Marker'] != 'None' or p_dict['group3Marker'] != 'None:' or p_dict['group4Marker'] != 'None:':
                            p_dict['group1Marker'], p_dict['group2Marker'], p_dict['group3Marker'], p_dict['group4Marker'] = self.fixTheMarkers(p_dict['group1Marker'],
                                                                                                                                                p_dict['group2Marker'],
                                                                                                                                                p_dict['group3Marker'],
                                                                                                                                                p_dict['group4Marker'])
                    except KeyError:
                        pass

                    self.logger.debug(u"")
                    self.logger.debug(u"{0:*^80}".format(u" Generating Chart: {0} ".format(dev.name)))

                    # ======= rcParams Device ======
                    if dev.deviceTypeId == 'rcParamsDevice':
                        self.rcParamsDeviceUpdate(dev)

                    # For the time being, we're running each device through its own process synchronously; parallel processing may come later.

                    # ======= Bar Charts ======
                    if dev.deviceTypeId == 'barChartingDevice':

                        if __name__ == '__main__':
                            p_bar = multiprocessing.Process(name='p_bar', target=self.chartSimpleBar, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_bar.start()
                            p_bar.join()  # We're want individual processes; parallel processing may come later.

                    # ======= Calendar Charts ======
                    if dev.deviceTypeId == "calendarChartingDevice":

                        if __name__ == '__main__':
                            p_calendar = multiprocessing.Process(name='p_calendar', target=self.chartSimpleCalendar, args=(dev, p_dict, k_dict, return_queue,))
                            p_calendar.start()
                            p_calendar.join()

                    # ======= Line Charts ======
                    if dev.deviceTypeId == "lineChartingDevice":

                        if __name__ == '__main__':
                            p_line = multiprocessing.Process(name='p_line', target=self.chartSimpleLine, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_line.start()
                            p_line.join()

                    # ======= Multiline Text ======
                    if dev.deviceTypeId == 'multiLineText':

                        # Get the text to plot. We do this here so we don't need to send all the devices and variables to the method (the process does not have access to the Indigo
                        # server).
                        if int(p_dict['thing']) in indigo.devices:
                            text_to_plot = unicode(indigo.devices[int(p_dict['thing'])].states[p_dict['thingState']])
                            self.logger.debug(u"Data retrieved successfully: {0}".format(text_to_plot))
                        elif int(p_dict['thing']) in indigo.variables:
                            text_to_plot = unicode(indigo.variables[int(p_dict['thing'])].value)
                            self.logger.debug(u"Data retrieved successfully: {0}".format(text_to_plot))
                        else:
                            text_to_plot = u"Unable to reconcile plot text. Confirm device settings."
                            self.logger.info(u"Presently, the plugin only supports device state and variable values.")

                        if __name__ == '__main__':
                            p_multiline = multiprocessing.Process(name='p_multiline', target=self.chartMultilineText, args=(dev, p_dict, k_dict, text_to_plot, return_queue,))
                            p_multiline.start()
                            p_multiline.join()

                    # ======= Polar Charts ======
                    if dev.deviceTypeId == "polarChartingDevice":

                        if __name__ == '__main__':
                            p_polar = multiprocessing.Process(name='p_polar', target=self.chartPolar, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_polar.start()
                            p_polar.join()

                    # ======= Scatter Charts ======
                    if dev.deviceTypeId == "scatterChartingDevice":

                        if __name__ == '__main__':
                            p_scatter = multiprocessing.Process(name='p_scatter', target=self.chartSimpleScatter, args=(dev, p_dict, k_dict, kv_list, return_queue,))
                            p_scatter.start()
                            p_scatter.join()

                    # ======= Weather Forecast Charts ======
                    if dev.deviceTypeId == "forecastChartingDevice":

                        dev_type = indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId
                        state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states
                        if __name__ == '__main__':
                            p_weather = multiprocessing.Process(name='p_weather', target=self.chartWeatherForecast,
                                                                args=(dev, dev_type, p_dict, k_dict, kv_list, state_list, return_queue,))
                            p_weather.start()
                            p_weather.join()

                    # ======= Process the output queue ======
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
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOff)
                    else:
                        self.logger.info(u"[{0}] {1}".format(dev.name, result['Message']))
                        dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)

                    dev.updateStateImageOnServer(indigo.kStateImageSel.SensorOn)
                    kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})
                    dev.updateStatesOnServer(kv_list)

                except RuntimeError as sub_error:
                    self.logger.critical(u"[{0}] Critical Error: {1}".format(dev.name, sub_error))
                    self.logger.critical(u"Skipping device.")

            else:
                if dev.model != "CSV Engine":
                    self.logger.info(u"Disabled: {0}: {1} [{2}] - Skipping plot sequence.".format(dev.model, dev.name, dev.id))

    def refreshTheChartsMenuAction(self):
        """ Called by an Indigo Menu selection. """
        self.logger.info(u"{0:=^80}".format(' Refresh the Charts Menu Action '))
        self.refreshTheCharts()
        self.logger.info(u"{0:=^80}".format(' Cycle complete. '))

    def refreshAChartAction(self, pluginAction):
        """ Call for a chart refresh and pass the id of the device
        called from the action. """
        self.logger.info(u"{0:=^80}".format(' Refresh Single Chart Action '))
        self.refreshTheCharts(pluginAction.deviceId)

    def refreshTheChartsAction(self, action):
        """ Called by an Indigo Action item. """
        self.logger.info(u"{0:=^80}".format(' Refresh All Charts Action '))
        if self.verboseLogging:
            self.logger.threaddebug(u"  valuesDict: {0}".format(action))

        self.refreshTheCharts()
        self.logger.info(u"{0:=^80}".format(' Cycle complete. '))

    def plotActionTest(self, pluginAction, dev, callerWaitingForResult):
        """
        A container for simple API calls to the matplotlib plugin.  Receives
        payload = {'x_values': [1, 2, 3],
                   'y_values': [2, 4, 6],
                   'kwargs': {'linestyle': 'dashed',
                              'color': 'b',
                              'marker': 's',
                              'markerfacecolor': 'b'},
                   'path': '/full/path/name/',
                   'filename': 'chart_filename.png'}
        All payload elements are required, although kwargs can be an empty
        dict if no kwargs desired.
        If caller is waiting for a result (recommended), returns a dict.
        :param pluginAction:
        :param dev:
        :param callerWaitingForResult:
        :return:
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

    def chartMakeFigure(self, width, height, p_dict):
        """"""
        fig = plt.figure(1, figsize=(float(width) / plt.rcParams['savefig.dpi'], float(height) / plt.rcParams['savefig.dpi']))
        ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
        ax.margins(0.04, 0.05)
        [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]
        return ax

    def chartFormatAxisX(self, ax, k_dict, p_dict):
        """"""
        ax.tick_params(axis='x', **k_dict['k_major_x'])
        ax.tick_params(axis='x', **k_dict['k_minor_x'])
        ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))
        self.setAxisScaleX(p_dict['xAxisBins'])  # Set the scale for the X axis. We assume a date.

        return ax

    def chartFormatAxisY(self, ax, k_dict, p_dict):
        """"""
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

        except Exception:
            pass

        return ax

    def chartFormatGrid(self, p_dict, k_dict):
        """"""
        # Show X and Axis Grids?
        if self.verboseLogging:
            self.logger.threaddebug(u"Display grids [X/Y]: {0} / {1}".format(p_dict['showxAxisGrid'], p_dict['showyAxisGrid']))
        if p_dict['showxAxisGrid']:
            plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])
        if p_dict['showyAxisGrid']:
            plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

    def chartSimpleBar(self, dev, p_dict, k_dict, kv_list, return_queue):
        """"""
        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Debug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            num_obs = p_dict['numObs']
            p_dict['bar1Color'] = r"#{0}".format(p_dict['bar1Color'].replace(' ', '').replace('#', ''))
            p_dict['bar2Color'] = r"#{0}".format(p_dict['bar2Color'].replace(' ', '').replace('#', ''))
            p_dict['bar3Color'] = r"#{0}".format(p_dict['bar3Color'].replace(' ', '').replace('#', ''))
            p_dict['bar4Color'] = r"#{0}".format(p_dict['bar4Color'].replace(' ', '').replace('#', ''))

            ax = self.chartMakeFigure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.chartFormatAxisX(ax, k_dict, p_dict)
            self.chartFormatAxisY(ax, k_dict, p_dict)

            for bar in range(1, 5, 1):

                # If the bar color is the same as the background color, alert the user.
                if p_dict['bar{0}Color'.format(bar)] == p_dict['backgroundColor']:
                    log['Info'].append(u"[{0}] Bar {0} color is the same as the background color (so you may not be able to see it).".format(dev.name, bar))
                # Plot the bars
                if p_dict['bar{0}Source'.format(bar)] not in ["", "None"]:

                    # Get the data and grab the header.
                    data_column = self.getTheData(u'{0}{1}'.format(self.pluginPrefs['dataPath'].encode("utf-8"), p_dict['bar{0}Source'.format(bar)]))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(bar)].append(element[0])
                        p_dict['y_obs{0}'.format(bar)].append(float(element[1]))

                    # Convert the date strings for charting.
                    list_of_dates = [dt.datetime.strptime(obs, '%Y-%m-%d %H:%M:%S.%f') for obs in p_dict['x_obs{0}'.format(bar)]]
                    dates_to_plot = mdate.date2num(list_of_dates)

                    # Plot the bar.
                    # Note: hatching is not supported in the PNG backend.
                    ax.bar(dates_to_plot[len(dates_to_plot) - num_obs:], p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:], align='center',
                           width=float(p_dict['barWidth']), color=p_dict['bar{0}Color'.format(bar)], edgecolor=p_dict['bar{0}Color'.format(bar)], **k_dict['k_bar'])
                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:]]

                    # If annotations desired, plot those too.
                    if p_dict['bar{0}Annotate'.format(bar)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(bar)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            # Setting the limits before the plot turns off autoscaling, which causes the limit that's not set to behave weirdly at times. This block is meant to overcome that weirdness
            # for something more desirable.
            log['Debug'].append(u"Y Max: {0}  Y Min: {1}  Y Diff: {2}".format(max(p_dict['data_array']),
                                                                              min(p_dict['data_array']),
                                                                              max(p_dict['data_array']) - min(p_dict['data_array'])))

            try:
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

            except ValueError as sub_error:
                return_queue.put({'Error': True, 'Log': log,
                                  'Message': u"Warning: trouble with {0} Y Min or Y Max. Set values to a real number or None. {1}".format(dev.name, sub_error), 'Name': dev.name})
            except Exception as sub_error:
                return_queue.put({'Error': True, 'Log': log, 'Message': u"Warning: trouble with {0} Y Min or Y Max. {1}".format(dev.name, sub_error), 'Name': dev.name})

            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])  # Chart title

            # X Axis Label - If the user chooses to display a legend, we don't want an axis label because they will fight with each other for space.
            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                log['Warning'].append(u"[{0}] X axis label is suppressed to make room for the chart legend.".format(dev.name))

            # Y Axis Label
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Legend Properties. Legend should be plotted before any other lines are plotted (like averages or custom line segments).
            if self.verboseLogging:
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

            # Plot the min/max lines if needed.  Note that these need to be plotted after the legend is established, otherwise some of the characteristics of the min/max lines will
            # take over the legend props.
            for bar in range(1, 5, 1):
                if p_dict['plotBar{0}Min'.format(bar)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:]), color=p_dict['bar{0}Color'.format(bar)], **k_dict['k_min'])
                if p_dict['plotBar{0}Max'.format(bar)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:]), color=p_dict['bar{0}Color'.format(bar)], **k_dict['k_max'])
                if self.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plotCustomLineSegments(ax, k_dict, p_dict)
            self.chartFormatGrid(p_dict, k_dict)

            # Custom Y ticks
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])
            try:
                marks  = [float(_) for _ in p_dict['customTicksY'].split(",")]
                if p_dict['customTicksLabelY'] == "":
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksY'].split(",")]
                else:
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksLabelY'].split(",")]
                plt.yticks(marks, labels)
            except:
                pass

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15, right=0.92)

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except IndexError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] IndexError ({1})".format(dev.name, sub_error)})
        except UnicodeEncodeError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] UnicodeEncodeError ({1})".format(dev.name, sub_error)})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Error plotting chart ({1})".format(dev.name, sub_error)})

    def chartSimpleCalendar(self, dev, p_dict, k_dict, return_queue):
        """"""

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}
        try:
            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Debug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            import calendar
            today = dt.datetime.today()
            calendar.setfirstweekday(int(dev.pluginProps['firstDayOfWeek']))
            cal = calendar.month(today.year, today.month)

            ax = self.chartMakeFigure(350, 250, p_dict)

            ax.text(0, 1, cal, transform=ax.transAxes, color=p_dict['fontColor'], fontname='Andale Mono', fontsize=dev.pluginProps['fontSize'], backgroundcolor=p_dict['faceColor'],
                    bbox=dict(pad=3), **k_dict['k_calendar'])
            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            ax.axis('off')  # uncomment this line to hide the box

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except UnicodeEncodeError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': sub_error, 'Name': dev.name})

    def chartSimpleLine(self, dev, p_dict, k_dict, kv_list, return_queue):
        """"""
        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Debug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            p_dict['line1Color'] = r"#{0}".format(p_dict['line1Color'].replace(' ', '').replace('#', ''))
            p_dict['line2Color'] = r"#{0}".format(p_dict['line2Color'].replace(' ', '').replace('#', ''))
            p_dict['line3Color'] = r"#{0}".format(p_dict['line3Color'].replace(' ', '').replace('#', ''))
            p_dict['line4Color'] = r"#{0}".format(p_dict['line4Color'].replace(' ', '').replace('#', ''))
            p_dict['line1MarkerColor'] = r"#{0}".format(p_dict['line1MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['line2MarkerColor'] = r"#{0}".format(p_dict['line2MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['line3MarkerColor'] = r"#{0}".format(p_dict['line3MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['line4MarkerColor'] = r"#{0}".format(p_dict['line4MarkerColor'].replace(' ', '').replace('#', ''))

            ax = self.chartMakeFigure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.chartFormatAxisX(ax, k_dict, p_dict)
            self.chartFormatAxisY(ax, k_dict, p_dict)

            for line in range(1, 5, 1):

                # If line color is the same as the background color, alert the user.
                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Warning'].append(u"[{0}] Line {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, line))

                # Plot the lines
                if p_dict['line{0}Source'.format(line)] not in ["", "None"]:

                    data_column = self.getTheData('{0}{1}'.format(self.pluginPrefs['dataPath'].encode("utf-8"), p_dict['line{0}Source'.format(line)].encode("utf-8")))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(line)].append(element[0])
                        p_dict['y_obs{0}'.format(line)].append(float(element[1]))

                    # Convert the date strings for charting.
                    list_of_dates = [dt.datetime.strptime(obs, '%Y-%m-%d %H:%M:%S.%f') for obs in p_dict['x_obs{0}'.format(line)]]
                    dates_to_plot = mdate.date2num(list_of_dates)

                    ax.plot_date(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                                 marker=p_dict['line{0}Marker'.format(line)], markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=10, **k_dict['k_line'])
                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Fill'.format(line)]:
                        ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            if self.verboseLogging:
                log['Debug'].append(u"Y Max: {0}  Y Min: {1}  Y Diff: {2}".format(max(p_dict['data_array']),
                                                                                  min(p_dict['data_array']),
                                                                                  max(p_dict['data_array']) - min(p_dict['data_array'])))

            try:
                # Min and Max are not 'None'.
                if p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] != 'None':
                    y_axis_min = float(p_dict['yAxisMin'])
                    y_axis_max = float(p_dict['yAxisMax'])

                # Max is 'None'.
                elif p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] == 'None':
                    y_axis_min = float(p_dict['yAxisMin'])
                    y_axis_max = max(p_dict['data_array'])

                # Min is 'None'.
                elif p_dict['yAxisMin'] == 'None' and p_dict['yAxisMax'] != 'None':
                    y_axis_min = min(p_dict['data_array'])
                    y_axis_max = float(p_dict['yAxisMax'])

                # Both min and max are not 'None'.
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

            except ValueError as sub_error:
                return_queue.put({'Error': True, 'Log': log,
                                  'Message': u"[{0}] Y Min or Y Max error. Set values to a real number or None. {1}".format(dev.name, sub_error), 'Name': dev.name})
            except Exception as sub_error:
                return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Y Min or Y Max error. {1}".format(dev.name, sub_error), 'Name': dev.name})

            # Transparent Chart Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Legend
            if self.verboseLogging:
                log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

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
                legend = ax.legend(final_headers, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # For lines 1-4, plot min and max as warranted.
            for line in range(1, 5, 1):
                if p_dict['plotLine{0}Min'.format(line)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_min'])
                if p_dict['plotLine{0}Max'.format(line)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_max'])
                if self.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plotCustomLineSegments(ax, k_dict, p_dict)
            self.chartFormatGrid(p_dict, k_dict)

            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                log['Debug'].append(u"[{0}] X axis label is suppressed to make room for the chart legend.".format(dev.name))

            # Custom Y ticks
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])
            try:
                marks  = [float(_) for _ in p_dict['customTicksY'].split(",")]
                if p_dict['customTicksLabelY'] == "":
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksY'].split(",")]
                else:
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksLabelY'].split(",")]
                plt.yticks(marks, labels)
            except Exception:
                pass

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15, right=0.92)

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except IndexError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] IndexError ({1})".format(dev.name, sub_error), 'Name': dev.name})
        except UnicodeEncodeError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] UnicodeEncodeError ({1})".format(dev.name, sub_error), 'Name': dev.name})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Error plotting chart ({1})".format(dev.name, sub_error), 'Name': dev.name})

    def chartMultilineText(self, dev, p_dict, k_dict, text_to_plot, return_queue):
        """"""

        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}
        try:

            import textwrap

            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Debug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            p_dict['textColor'] = r"#{0}".format(p_dict['textColor'].replace(' ', '').replace('#', ''))

            # If the value to be plotted is empty, use the default text from the device configuration.
            if len(text_to_plot) <= 1:
                text_to_plot = unicode(p_dict['defaultText'])
            else:
                # The cleanUpString method tries to remove some potential ugliness from the text to be plotted. It's optional--defaulted to on. No need to call this if the default text
                # is used.
                if p_dict['cleanTheText']:
                    text_to_plot = self.cleanUpString(text_to_plot)

            # Wrap the text and prepare it for plotting.
            text_to_plot = textwrap.fill(text_to_plot, int(p_dict['numberOfCharacters']), replace_whitespace=p_dict['cleanTheText'])

            ax = self.chartMakeFigure(p_dict['figureWidth'], p_dict['figureHeight'], p_dict)

            ax.text(0.01, 0.95, text_to_plot, transform=ax.transAxes, color=p_dict['textColor'], fontname=p_dict['fontMain'], fontsize=p_dict['multilineFontSize'],
                    verticalalignment='top')

            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)

            if not p_dict['textAreaBorder']:
                [s.set_visible(False) for s in ax.spines.values()]

            # Transparent Charts Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Chart title
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            plt.tight_layout(pad=1)
            plt.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05)

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except (KeyError, IndexError, ValueError, UnicodeEncodeError) as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

    def chartPolar(self, dev, p_dict, k_dict, kv_list, return_queue):
        # Note that the polar chart device can be used for other things, but it is coded like a wind rose which makes it easier to understand what's happening. Note that it would be
        # possible to convert wind direction names (north-northeast) to an ordinal degree value, however, it would be very difficult to contend with all of the possible international
        # Unicode values that could be passed to the device.  Better to make it the responsibility of the user to convert their data to degrees.
        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            if self.verboseLogging:
                log['Threaddebug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Threaddebug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            self.final_data    = []
            num_obs = p_dict['numObs']
            p_dict['currentWindColor'] = r"#{0}".format(p_dict['currentWindColor'].replace(' ', '').replace('#', ''))
            p_dict['maxWindColor'] = r"#{0}".format(p_dict['maxWindColor'].replace(' ', '').replace('#', ''))

            # Grab the column headings for the labels, then delete the row from self.final_data.
            theta_path = '{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['thetaValue'])  # The name of the theta file.
            radii_path = '{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['radiiValue'])  # The name of the radii file.

            if theta_path != 'None' and radii_path != 'None':

                try:
                    # Get the data.
                    self.final_data.append(self.getTheData(theta_path))
                    self.final_data.append(self.getTheData(radii_path))

                    # Pull out the header information out of the data.
                    del self.final_data[0][0]
                    del self.final_data[1][0]

                    # Create lists of data to plot (string -> float).
                    [p_dict['wind_direction'].append(float(item[1])) for item in self.final_data[0]]
                    [p_dict['wind_speed'].append(float(item[1])) for item in self.final_data[1]]

                    p_dict['wind_direction'] = p_dict['wind_direction'][len(p_dict['wind_direction']) - num_obs: len(p_dict['wind_direction'])]
                    p_dict['wind_speed'] = p_dict['wind_speed'][len(p_dict['wind_speed']) - num_obs: len(p_dict['wind_speed'])]

                except (IndexError, UnicodeEncodeError) as sub_error:
                    return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Error plotting chart ({1})".format(dev.name, sub_error), 'Name': dev.name})

                # Create the array of grey scale for the intermediate lines and set the last one red. (MPL will accept string values '0' - '1' as grey scale, so we create a number of
                # greys based on 1.0 / number of observations.)
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

                if len(wind) < num_obs:
                    return_queue.put({'Error': True,
                                      'Log': log,
                                      'Message': u"[{0}] Error plotting chart (CSV file contains insufficient number of observations.)".format(dev.name), 'Name': dev.name})

                # Customizations.
                size = float(p_dict['sqChartSize']) / int(plt.rcParams['savefig.dpi'])
                plt.figure(figsize=(size, size))
                ax = plt.subplot(111, polar=True)                                 # Create subplot
                plt.grid(color=plt.rcParams['grid.color'])                        # Color the grid
                ax.set_theta_zero_location('N')                                   # Set zero to North
                ax.set_theta_direction(-1)                                        # Reverse the rotation
                ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])  # Customize the xtick labels
                ax.spines['polar'].set_visible(False)                             # Show or hide the plot spine
                ax.set_axis_bgcolor(p_dict['faceColor'])                          # Color the background of the plot area.

                # Create the plot. Note: zorder of the plot must be >2.01 for the plot to be above the grid (the grid defaults to z=2.)
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

                if p_dict['xHideLabels']:
                    ax.axes.xaxis.set_ticklabels([])
                if p_dict['yHideLabels']:
                    ax.axes.yaxis.set_ticklabels([])

                # Plot circles for current obs and max wind. Note that we reduce the value of the circle plot so that it appears when transparent charts are enabled (otherwise the
                # circle is obscured. The transform can be done one of two ways: access the private attribute "ax.transData._b", or "ax.transProjectionAffine + ax.transAxes".
                fig = plt.gcf()
                max_wind_circle = plt.Circle((0, 0), (max(p_dict['wind_speed']) * 0.99),
                                             transform=ax.transProjectionAffine + ax.transAxes,
                                             fill=False,
                                             edgecolor=p_dict['maxWindColor'],
                                             linewidth=2, alpha=1, zorder=9)
                fig.gca().add_artist(max_wind_circle)

                last_wind_circle = plt.Circle((0, 0), (p_dict['wind_speed'][num_obs - 1] * 0.99), transform=ax.transProjectionAffine + ax.transAxes, fill=False,
                                              edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=10)
                fig.gca().add_artist(last_wind_circle)

                # If latest obs is a speed of zero, plot something that we can at least see.
                if p_dict['wind_speed'][num_obs - 1] == 0:
                    zero_wind_circle = plt.Circle((0, 0), 0.15, transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['currentWindColor'],
                                                  edgecolor=p_dict['currentWindColor'], linewidth=2, alpha=1, zorder=12)
                    fig.gca().add_artist(zero_wind_circle)

                # Transparent Chart Fill
                if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                    ylim = ax.get_ylim()
                    patch = plt.Circle((0, 0), ylim[1], transform=ax.transProjectionAffine + ax.transAxes, fill=True, facecolor=p_dict['faceColor'], linewidth=1, alpha=1, zorder=1)
                    fig.gca().add_artist(patch)

                # Legend Properties
                if self.verboseLogging:
                    log['Debug'].append(u"Display legend: {0}".format(p_dict['showLegend']))

                if p_dict['showLegend']:
                    legend = ax.legend(([u"Current", u"Maximum"]), loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                    legend.legendHandles[0].set_color(p_dict['currentWindColor'])
                    legend.legendHandles[1].set_color(p_dict['maxWindColor'])
                    [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                    frame = legend.get_frame()
                    frame.set_alpha(0)

                if self.verboseLogging:
                    log['Debug'].append(u"Display grids[X / Y]: always on")

                # Chart title
                plt.title(p_dict['chartTitle'], position=(0, 1.0), **k_dict['k_title_font'])

                if p_dict['fileName'] != '':
                    plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

                plt.clf()
                plt.close('all')

                return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

                kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except ValueError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})
        except KeyError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

    def chartSimpleScatter(self, dev, p_dict, k_dict, kv_list, return_queue):
        """"""
        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            if self.verboseLogging:
                log['Threaddebug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Threaddebug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            p_dict['group1Color'] = r"#{0}".format(p_dict['group1Color'].replace(' ', '').replace('#', ''))
            p_dict['group2Color'] = r"#{0}".format(p_dict['group2Color'].replace(' ', '').replace('#', ''))
            p_dict['group3Color'] = r"#{0}".format(p_dict['group3Color'].replace(' ', '').replace('#', ''))
            p_dict['group4Color'] = r"#{0}".format(p_dict['group4Color'].replace(' ', '').replace('#', ''))
            p_dict['group1MarkerColor'] = r"#{0}".format(p_dict['group1MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['group2MarkerColor'] = r"#{0}".format(p_dict['group2MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['group3MarkerColor'] = r"#{0}".format(p_dict['group3MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['group4MarkerColor'] = r"#{0}".format(p_dict['group4MarkerColor'].replace(' ', '').replace('#', ''))

            ax = self.chartMakeFigure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.chartFormatAxisX(ax, k_dict, p_dict)
            self.chartFormatAxisY(ax, k_dict, p_dict)

            for line in range(1, 5, 1):

                # If dot color is the same as the background color, alert the user.
                if p_dict['group{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Debug'].append(u"[{0}] Group {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, line))

                # Plot the points
                if p_dict['group{0}Source'.format(line)] not in ["", "None"]:

                    data_column = self.getTheData('{0}{1}'.format(self.pluginPrefs['dataPath'].encode("utf-8"), p_dict['group{0}Source'.format(line)].encode("utf-8")))
                    p_dict['headers'].append(data_column[0][1])
                    del data_column[0]

                    # Pull the observations into distinct lists for charting.
                    for element in data_column:
                        p_dict['x_obs{0}'.format(line)].append(element[0])
                        p_dict['y_obs{0}'.format(line)].append(float(element[1]))

                    # Convert the date strings for charting.
                    list_of_dates = [dt.datetime.strptime(obs, '%Y-%m-%d %H:%M:%S.%f') for obs in p_dict['x_obs{0}'.format(line)]]
                    dates_to_plot = mdate.date2num(list_of_dates)

                    # Note that using 'c' to set the color instead of 'color' makes a difference for some reason.
                    ax.scatter(dates_to_plot, p_dict['y_obs{0}'.format(line)], c=p_dict['group{0}Color'.format(line)], marker=p_dict['group{0}Marker'.format(line)],
                               edgecolor=p_dict['group{0}MarkerColor'.format(line)], zorder=10, **k_dict['k_line'])
                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

            if self.verboseLogging:
                log['Debug'].append(u"Y Max: {0}  Y Min: {1}  Y Diff: {2}".format(max(p_dict['data_array']),
                                                                                  min(p_dict['data_array']),
                                                                                  max(p_dict['data_array']) - min(p_dict['data_array'])))

            try:
                # Min and Max are not 'None'.
                if p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] != 'None':
                    y_axis_min = float(p_dict['yAxisMin'])
                    y_axis_max = float(p_dict['yAxisMax'])

                # Max is 'None'.
                elif p_dict['yAxisMin'] != 'None' and p_dict['yAxisMax'] == 'None':
                    y_axis_min = float(p_dict['yAxisMin'])
                    y_axis_max = max(p_dict['data_array'])

                # Min is 'None'.
                elif p_dict['yAxisMin'] == 'None' and p_dict['yAxisMax'] != 'None':
                    y_axis_min = min(p_dict['data_array'])
                    y_axis_max = float(p_dict['yAxisMax'])

                # Both min and max are not 'None'.
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

            except ValueError as sub_error:
                return_queue.put({'Error': True, 'Log': log,
                                  'Message': u"[{0}] Y Min or Y Max error. Set values to a real number or None. {1}".format(dev.name, sub_error), 'Name': dev.name})
            except Exception as sub_error:
                return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Y Min or Y Max error. {1}".format(dev.name, sub_error), 'Name': dev.name})

            # Legend
            if self.verboseLogging:
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
                                                        markerfacecolor=p_dict['group{0}Color'.format(counter)])))
                    counter += 1

                legend = ax.legend(legend_styles, final_headers, loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, numpoints=1, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # For lines 1-4, plot min and max as warranted.
            for group in range(1, 5, 1):
                if p_dict['plotGroup{0}Min'.format(group)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(group)]), color=p_dict['group{0}Color'.format(line)], **k_dict['k_min'])
                if p_dict['plotGroup{0}Max'.format(group)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(group)]), color=p_dict['group{0}Color'.format(line)], **k_dict['k_max'])
                if self.pluginPrefs.get('forceOriginLines', True):
                    ax.axhline(y=0, color=p_dict['spineColor'])

            self.plotCustomLineSegments(ax, k_dict, p_dict)
            self.chartFormatGrid(p_dict, k_dict)

            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                log['Warning'].append(u"[{0}] X axis label is suppressed to make room for the chart legend.".format(dev.name))

            # Custom Y ticks
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])
            try:
                marks  = [float(_) for _ in p_dict['customTicksY'].split(",")]
                if p_dict['customTicksLabelY'] == "":
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksY'].split(",")]
                else:
                    labels = [u"{0}".format(_.strip()) for _ in p_dict['customTicksLabelY'].split(",")]
                plt.yticks(marks, labels)
            except:
                pass
            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15, right=0.92)

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            plt.clf()
            plt.close('all')

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except IndexError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] IndexError ({1})".format(dev.name, sub_error), 'Name': dev.name})
        except UnicodeEncodeError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] UnicodeEncodeError ({1})".format(dev.name, sub_error), 'Name': dev.name})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Error plotting chart ({1})".format(dev.name, sub_error), 'Name': dev.name})

    def chartWeatherForecast(self, dev, dev_type, p_dict, k_dict, kv_list, state_list, return_queue):
        """"""
        log = {'Threaddebug': [], 'Debug': [], 'Info': [], 'Warning': [], 'Critical': []}

        try:
            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))
                log['Debug'].append(u"{0:<19}{1}".format("k_dict: ", [(k, v) for (k, v) in sorted(k_dict.items())]))

            p_dict['line1Color'] = r"#{0}".format(p_dict['line1Color'].replace(' ', '').replace('#', ''))
            p_dict['line2Color'] = r"#{0}".format(p_dict['line2Color'].replace(' ', '').replace('#', ''))
            p_dict['line3Color'] = r"#{0}".format(p_dict['line3Color'].replace(' ', '').replace('#', ''))
            p_dict['line1MarkerColor'] = r"#{0}".format(p_dict['line1MarkerColor'].replace(' ', '').replace('#', ''))
            p_dict['line2MarkerColor'] = r"#{0}".format(p_dict['line2MarkerColor'].replace(' ', '').replace('#', ''))

            dates_to_plot = p_dict['dates_to_plot']

            for line in range(1, 4, 1):

                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    log['Debug'].append(u"[{0}] A line color is the same as the background color (so you will not be able to see it).".format(dev.name))

            if self.verboseLogging:
                log['Debug'].append(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            # Prepare the data for charting.
            if dev_type == 'wundergroundHourly':
                pass
                for counter in range(1, 25, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    p_dict['x_obs1'].append(state_list['h{0}_timeLong'.format(counter)])
                    p_dict['y_obs1'].append(state_list['h{0}_temp'.format(counter)])
                    p_dict['y_obs3'].append(state_list['h{0}_precip'.format(counter)])

                    # Convert the date strings for charting.
                    list_of_dates = [dt.datetime.strptime(obs, '%Y-%m-%d %H:%M') for obs in p_dict['x_obs1']]
                    dates_to_plot = mdate.date2num(list_of_dates)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1'] = ('Temperature',)  # Note that the trailing comma is required to ensure that Matplotlib interprets the legend as a tuple.
                    p_dict['headers_2'] = ('Precipitation',)

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
                    list_of_dates = [dt.datetime.strptime(obs, '%Y-%m-%d') for obs in p_dict['x_obs1']]
                    dates_to_plot = mdate.date2num(list_of_dates)

                    # Note that bar plots behave strangely if all the y obs are zero.  We need to adjust slightly if that's the case.
                    if set(p_dict['y_obs3']) == {0.0}:
                        p_dict['y_obs3'][0] = 1.0

                    p_dict['headers_1'] = ('High Temperature', 'Low Temperature',)
                    p_dict['headers_2'] = ('Precipitation',)

            else:
                log['Warning'].append(u"This device type only supports WUnderground plugin forecast devices.")

            ax1 = self.chartMakeFigure(p_dict['chart_width'], p_dict['chart_height'], p_dict)

            self.chartFormatAxisX(ax1, k_dict, p_dict)
            self.chartFormatAxisY(ax1, k_dict, p_dict)

            # Plot the chance of precipitation bars.  The width of the bars is a percentage of a day, so we need to account for instances where the unit of time could be hours to months
            # or years.
            if p_dict['y_obs3']:
                if len(dates_to_plot) <= 15:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=((1.0 / len(dates_to_plot)) * 5), alpha=0.25, zorder=3)
                else:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=(1.0 / (len(dates_to_plot) * 1.75)), alpha=0.25, zorder=3)

                if p_dict['line3Annotate']:
                    for xy in zip(dates_to_plot, p_dict['y_obs3']):
                        ax1.annotate('%.0f' % xy[1], xy=(xy[0], 5), xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            try:
                # Y2 Min/Max
                if p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] != 'None':
                    y2_axis_min = float(p_dict['y2AxisMin'])
                    y2_axis_max = float(p_dict['y2AxisMax'])

                elif p_dict['y2AxisMin'] != 'None' and p_dict['y2AxisMax'] == 'None':
                    y2_axis_min = float(p_dict['y2AxisMin'])
                    y2_axis_max = max(p_dict['y_obs3'])

                elif p_dict['y2AxisMin'] == 'None' and p_dict['y2AxisMax'] != 'None':
                    # y2_axis_min = min(p_dict['y_obs3'])
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

            except ValueError as sub_error:
                return_queue.put({'Error': True, 'Message': str(sub_error), 'Name': dev.name})
            except Exception as sub_error:
                return_queue.put({'Error': True, 'Message': str(sub_error), 'Name': dev.name})

            # X Axis Label
            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                log['Debug'].append(u"[{0}] X axis label suppressed to make room for the chart legend.".format(dev.name))

            # Y1 Axis Label
            plt.ylabel(p_dict['customAxisLabelY'], labelpad=20, **k_dict['k_y_axis_font'])

            # Legend Properties (note that we need a separate instance of this code for each subplot. This one controls the precipitation subplot.)
            if self.verboseLogging:
                log['Debug'].append(u"Display legend 1: {0}".format(p_dict['showLegend']))

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_2']]
                legend = ax1.legend(headers, loc='upper right', bbox_to_anchor=(1.0, -0.1), ncol=1, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            self.chartFormatGrid(p_dict, k_dict)

            # Transparent Charts Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax1.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax1.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Create a second plot area and plot the temperatures.
            ax2 = ax1.twinx()
            ax2.margins(0.04, 0.05)  # This need to remain or the margins get screwy (they don't carry over from ax1).

            for line in range(1, 3, 1):
                if p_dict['y_obs{0}'.format(line)]:
                    ax2.plot(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                             marker=p_dict['line{0}Marker'.format(line)], markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=(10 - line), **k_dict['k_line'])
                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax2.annotate('%.0f' % xy[1], xy=xy, xytext=(0, 0), zorder=(11 - line), **k_dict['k_annotation'])

            self.chartFormatAxisX(ax2, k_dict, p_dict)
            self.chartFormatAxisY(ax2, k_dict, p_dict)

            self.plotCustomLineSegments(ax2, k_dict, p_dict)

            plt.autoscale(enable=True, axis='x', tight=None)

            # Note that we plot the bar plot so that it will be under the line plot, but we still want the temperature scale on the left and the percentages on the right.
            ax1.yaxis.tick_right()
            ax2.yaxis.tick_left()

            if self.verboseLogging:
                log['Debug'].append(u"Y1 Max: {0}  Y1 Min: {1}  Y1 Diff: {2}".format(max(p_dict['data_array']),
                                                                                     min(p_dict['data_array']),
                                                                                     max(p_dict['data_array']) - min(p_dict['data_array'])))

            # Y1 Axis Min/Max
            try:
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

            except ValueError:
                return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Y Min or Y Max error. Set values to a real number or None.".format(dev.name), 'Name': dev.name})
            except Exception as sub_error:
                return_queue.put({'Error': True, 'Log': log, 'Message': u"[{0}] Y Min or Y Max error. {1}".format(dev.name, sub_error), 'Name': dev.name})

            # Chart title
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # Y2 Axis Label
            plt.ylabel(p_dict['customAxisLabelY2'], labelpad=20, **k_dict['k_y2_axis_font'])

            # Legend Properties (note that we need a separate instance of this code for each subplot. This one controls the temperatures subplot.)
            if self.verboseLogging:
                log['Debug'].append(u"Display legend 2: {0}".format(p_dict['showLegend']))

            if p_dict['showLegend']:
                headers = [_.decode('utf-8') for _ in p_dict['headers_1']]
                legend = ax2.legend(headers, loc='upper left', bbox_to_anchor=(0.0, -0.1), ncol=2, prop={'size': float(p_dict['legendFontSize'])})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)  # Note: frame alpha should be an int and not '0'.

            self.chartFormatGrid(p_dict, k_dict)

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15)

            if p_dict['fileName'] != '':
                plt.savefig(u'{0}{1}'.format(p_dict['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

            return_queue.put({'Error': False, 'Log': log, 'Message': 'updated successfully.', 'Name': dev.name})

        except ValueError as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})
        except Exception as sub_error:
            return_queue.put({'Error': True, 'Log': log, 'Message': str(sub_error), 'Name': dev.name})

    def cleanUpString(self, val):
        """The cleanUpString(self, val) method is used to scrub multiline text
        elements in order to try to make them more presentable. The need is
        easily seen by looking at the rough text that is provided by the U.S.
        National Weather Service, for example."""
        if self.verboseLogging:
            self.logger.debug(u"{0:*^40}".format(" Clean Up String "))
            self.logger.debug(u"Length of initial string: {0}".format(len(val)))

        # List of (elements, replacements)
        clean_list = [(' am ', ' AM '), (' pm ', ' PM '), ('*', ' '), ('\u000A', ' '), ('...', ' '), ('/ ', '/'), (' /', '/'), ('/', ' / ')]

        # Take the old, and replace it with the new.
        for (old, new) in clean_list:
            val = val.replace(old, new)

        return ' '.join(val.split())  # Eliminate spans of whitespace.

    def convertTheData(self, final_data):
        """Matplotlib can't plot values like 'Open' and 'Closed', so we convert
        them for plotting. We do this on the fly and we do not change the
        underlying data in any way."""

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
                     '-99': 'NaN'}

        for value in final_data:
            if value[1].lower() in converter.keys():
                value[1] = converter[value[1].lower()]

        return final_data

    def _dummyCallback(self, valuesDict=None, typeId="", targetId=0):
        """The purpose of the _dummyCallback method is to provide something
        for configuration dialogs to call in order to force a refresh of any
        dynamic controls (dynamicReload=True)."""
        pass

    def deviceStateGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        """The deviceStateGenerator() method returns a list of device states
        and variables. Each device list includes only states for the selected
        device.
        """

        try:
            id = valuesDict['thing']
            return self.Fogbert.generatorStateOrValue(id)
        except KeyError:
            return [("Select a Source Above", "Select a Source Above")]

    def fixTheMarkers(self, line1_marker, line2_marker, line3_marker, line4_marker):
        """ The devices.xml file cannot contain '<' or '>' as a value, as this
        conflicts with the construction of the XML code.  Matplotlib needs
        these values for select built-in marker styles, so we need to change
        them to what MPL is expecting."""
        if self.verboseLogging:
            self.logger.threaddebug(u"Fixing the markers.")

        marker_dict = {"PIX": ",", "TL": "<", "TR": ">"}

        for k, v in marker_dict.iteritems():
            if line1_marker == k:
                line1_marker = marker_dict[k]
            if line2_marker == k:
                line2_marker = marker_dict[k]
            if line3_marker == k:
                line3_marker = marker_dict[k]
            if line4_marker == k:
                line4_marker = marker_dict[k]

        return line1_marker, line2_marker, line3_marker, line4_marker

    def getAxisList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of possible axis formats."""
        self.logger.debug(u"{0:*^40}".format(' Get Axis List '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        axis_list_menu = [
            ("%I:%M", "01:00"),
            ("%l:%M %p", "1:00 pm"),
            ("%H:%M", "13:00"),
            ("%a", "Sun"),
            ("%A", "Sunday"),
            ("%b", "Jan"),
            ("%B", "January"),
            ("%y", "16"),
            ("%Y", "2016")]

        # self.logger.threaddebug(u"axis_list_menu: {0}".format(axis_list_menu))
        return axis_list_menu

    def getBinList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of bins for the X axis."""
        self.logger.debug(u"{0:*^40}".format(' Get Bin List '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        bin_list_menu = [
            ("quarter-hourly", "Every 15 Minutes"),
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

    def getChartList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of all plugin charts."""
        self.logger.debug(u"{0:*^40}".format(' Get Chart List '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        chart_list_menu = []

        for dev in indigo.devices.itervalues('self'):
            if dev.model not in ["CSV Engine", "Matplotlib Parameters Device"]:
                chart_list_menu.append((dev.id, dev.name))

        return chart_list_menu

    def getFontList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Generates and returns a list of fonts.  Note that these are the
        fonts that Matplotlib can see, not necessarily all of the fonts
        installed on the system."""
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        font_menu = []

        try:
            from os import path

            for font in mfont.findSystemFonts(fontpaths=None, fontext='ttf'):
                font_name = path.splitext(path.basename(font))[0]
                if font_name not in font_menu:
                    font_menu.append(font_name)

            self.logger.threaddebug(u"Font list: {0}".format(font_menu))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error building font list.  Returning generic list. {0}".format(sub_error))

            font_menu = [
                'Arial',
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
        """Returns a list of allowable font sizes."""
        if self.verboseLogging:
            self.logger.threaddebug(u"Constructing font size list.")

        return [(str(_), str(_)) for _ in np.arange(6, 21)]

    def getForecastSource(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Generates and returns a list of potential forecast devices for the
        forecast devices type. Presently, the plugin only works with
        WUnderground devices, but the intention is to expand the list of
        compatible devices going forward."""
        self.logger.debug(u"{0:*^40}".format(' Get Forecast Source '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

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
        """Returns a list of line styles."""
        if self.verboseLogging:
            self.logger.threaddebug(u"Constructing line list.")

        return [
            ("None", "None"),
            ("--", "Dashed"),
            (":", "Dotted"),
            ("-.", "Dot Dash"),
            ("-", "Solid"),
            ("steps", "Steps"),
            ("steps-mid", "Steps Mid"),
            ("steps-post", "Steps Post")
        ]

    def getListOfFiles(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Get list of CSV files."""
        self.logger.debug(u"{0:*^40}".format(' Get List of Files '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        file_name_list_menu = []
        source_path = self.pluginPrefs.get('dataPath', '{0}/com.fogbert.indigoplugin.matplotlib/'.format(indigo.server.getLogsFolderPath()))

        try:
            import glob
            import os

            for file_name in glob.glob(u"{0}{1}".format(source_path, '*.csv')):
                final_filename = os.path.basename(file_name)
                file_name_list_menu.append((final_filename, final_filename[:-4]))
            file_name_list_menu.append('None')
            self.logger.threaddebug(u"File list generated successfully: {0}".format(file_name_list_menu))

        except IOError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"Error generating file list: {0}".format(sub_error))

        self.logger.threaddebug(u"File name list menu: {0}".format(file_name_list_menu))
        return file_name_list_menu

    def getMarkerList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of marker styles."""
        self.logger.debug(u"{0:*^40}".format(' Get Marker List '))
        if self.verboseLogging:
            self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
            self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        return [
            ("None", "None"),
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
            ("x", "X")
        ]

    def getTheData(self, data_source):
        """ Get the data. """

        final_data = []
        try:
            data_file  = open(data_source, "r")
            csv_data   = reader(data_file, delimiter=',')
            [final_data.append(item) for item in csv_data]
            data_file.close()
            final_data = self.convertTheData(final_data)
            self.logger.debug(u"Data retrieved successfully: {0}".format(data_source.decode("utf-8")))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error downloading CSV data. Skipping: {0}".format(sub_error))

        if self.verboseLogging:
            self.logger.threaddebug(u"{0:<19}{1}".format("Final data: ", final_data))

        return final_data

    def listGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        """This method returns a dictionary of the form
        ((dev.id, dev.name), (var.id, var.name)). It prepends (D) or (V) to
        make it easier to distinguish between the two.
        """
        return self.Fogbert.deviceAndVariableList()

    def plotCustomLineSegments(self, ax, k_dict, p_dict):
        """"""
        # Plot the custom lines if needed.  Note that these need to be plotted after the legend is established, otherwise some of the characteristics of the min/max
        # lines will take over the legend props.
        self.logger.debug(u"Custom line segments ({0}): {1}".format(p_dict['enableCustomLineSegments'], p_dict['customLineSegments']))

        if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ["", "None"]:
            try:
                constants_to_plot = literal_eval(p_dict['customLineSegments'])
                for element in constants_to_plot:
                    if type(element) == tuple:
                        cls = ax.axhline(y=element[0], color=element[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        # If we want to promote custom line segments, we need to add them to the list that's used to calculate the Y axis limits.
                        if self.pluginPrefs.get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(element[0])
                    else:
                        cls = ax.axhline(y=constants_to_plot[0], color=constants_to_plot[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        if self.pluginPrefs.get('promoteCustomLineSegments', False):
                            p_dict['data_array'].append(constants_to_plot[0])

                return cls

            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"There is a problem with the custom segments settings. {0}".format(sub_error))

    def pluginErrorHandler(self, sub_error):
        """Centralized handling of traceback messages formatted for pretty
        display in the plugin log file. If sent here, they will not be
        displayed in the Indigo Events log. Use the following syntax to
        send exceptions here:
        self.pluginErrorHandler(traceback.format_exc())"""
        sub_error = sub_error.splitlines()
        self.logger.threaddebug(u"{0:!^80}".format(" TRACEBACK "))
        for line in sub_error:
            self.logger.threaddebug(u"!!! {0}".format(line))
        self.logger.threaddebug(u"!" * 80)
        # self.logger.warning(u"Error: {0}".format(sub_error[3]))

    def setAxisScaleX(self, x_axis_bins):
        """The setAxisScaleX() method sets the bins for the X axis. Presently,
        we assume a date-based axis."""
        if self.verboseLogging:
            self.logger.threaddebug(u"Constructing the bins for the X axis.")

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
