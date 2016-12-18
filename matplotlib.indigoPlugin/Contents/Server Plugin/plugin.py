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
# TODO: NEW -- Create a new device to create a horizontal bar chart (i.e., like device battery levels.)
# TODO: NEW -- Create a new device to create dot plots (i.e., like Z-Wave Node Matrix)
# TODO: NEW -- Create a new device to plot with Y2. This is more complicated than it sounds.  Separate device type?
# TODO: NEW -- Provide hooks that can be used by other plugin authors.
# TODO: NEW -- Standard chart types with pre-populated data that link to types of Indigo devices (like energy)
# TODO: Manual
# TODO: Look into color palettes (grey scale, roygbiv, tableau 10, color blind 10, etc.)
# TODO: Make changes to sleeptime take effect instantly.
# TODO: See what other plugin devices the weather device will support.
# TODO: Consider making autolayout an option. [ rcParams.update({'figure.autolayout': True}) ]
# TODO: Automatically remove CSV items if their tuple is ('', '', '')
# TODO: Consider removing bar min markers -- will bar min always be zero?

# Feature requests:
# TODO: Option to override legend names
# TODO: Option to specify X and Y axis intervals
# TODO: When the source title is changed in the CSV engine, refactor the CSV file, too.
# TODO: When the source is deleted, offer to delete the CSV file too.
# TODO: Add half-hourly X Axis intervals are done. Need to reign in the labels a bit.


from ast import literal_eval
from csv import reader
import datetime as dt
import gc
import indigoPluginUpdateChecker
import logging
from matplotlib import rcParams
try:
    import matplotlib.pyplot as plt
except ValueError:
    indigo.server.log(u"There was an error importing necessary Matplotlib components. Please reboot your server and try to re-enable the plugin.", isError=True)
import matplotlib.patches as patches
import matplotlib.dates as mdate
import matplotlib.ticker as mtick
import matplotlib.font_manager as mfont
import numpy as np
import traceback

try:
    import indigo
except ImportError as error:
    pass

try:
    import pydevd  # To support remote debugging
except ImportError as error:
    pass

__author__    = "DaveL17"
__build__     = ""
__copyright__ = "Copyright 2016 DaveL17"
__license__   = ""
__title__     = "Matplotlib Plugin for Indigo Home Control"
__version__   = "0.2.05"


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        indigo.PluginBase.__init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs)

        self.updater = indigoPluginUpdateChecker.updateChecker(self, "https://dl.dropboxusercontent.com/u/2796881/matplotlib_version.html")
        # pydevd.settrace('localhost', port=5678, stdoutToServer=True, stderrToServer=True, suspend=False)  # To enable remote PyCharm Debugging, uncomment this line.

        self.plugin_file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S'))
        self.debug      = True
        self.debugLevel = int(self.pluginPrefs.get('showDebugLevel', '30'))
        self.indigo_log_handler.setLevel(self.debugLevel)

        self.final_data = []

    def __del__(self):
        indigo.PluginBase.__del__(self)

    def startup(self):
        """ Plugin startup routines."""
        self.logger.info(u"")
        self.logger.info(u"{:=^80}".format(' Initializing New Plugin Session '))
        self.logger.info(u"{0:<31} {1}".format("Indigo version:", indigo.server.version))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib version:", plt.matplotlib.__version__))
        self.logger.info(u"{0:<31} {1}".format("Numpy version:", np.__version__))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin version:", self.pluginVersion))
        self.logger.threaddebug(u"{0:<31} {1}".format("Matplotlib base rcParams:", dict(rcParams)))  # rcParams is a dict containing all of the initial matplotlibrc settings
        self.logger.info(u"{0:<31} {1}".format("Matplotlib RC Path:", plt.matplotlib.matplotlib_fname()))
        self.logger.info(u"{0:<31} {1}".format("Matplotlib Plugin log location:", indigo.server.getLogsFolderPath(pluginId='com.fogbert.indigoplugin.matplotlib')))
        self.logger.debug(u"{0:<31} {1}".format("Log Level = ", self.debugLevel))
        self.updater.checkVersionPoll()

    def deviceStartComm(self, dev):
        """ Start communication with plugin devices."""
        self.logger.debug(u"Starting device: {0}".format(dev.name))
        dev.stateListOrDisplayStateIdChanged()

    def shutdown(self):
        """ Plugin shutdown routines."""
        self.logger.debug(u"{0:*^40}".format(' Shut Down '))

    def deviceStopComm(self, dev):
        """ Stop communication with plugin devices."""
        self.logger.debug(u"Stopping device: {0}".format(dev.name))

    def getPrefsConfigUiValues(self):
        """getPrefsConfigUiValues(self) is called when the plugin config dialog
        is called."""
        self.logger.debug(u"{0:*^40}".format(' Get Prefs Config UI Values '))

        # Pull in the initial pluginPrefs. If the plugin is being set up for the first time, this dict will be empty.
        # Subsequent calls will pass the established dict.
        plugin_prefs = self.pluginPrefs
        self.logger.threaddebug(u"Initial plugin_prefs: {0}".format(dict(plugin_prefs)))

        # Establish a set of defaults for select plugin settings. Only those settings that are populated dynamically need
        # to be set here (the others can be set directly by the XML.)
        defaults_dict = {'annotationColorOther': '#FFFFFF',
                         'backgroundColor': '#000000',
                         'backgroundColorOther': '#000000',
                         'enableCustomColors': False,
                         'faceColor': '#000000',
                         'faceColorOther': '#000000',
                         'fontColor': '#FFFFFF',
                         'fontColorAnnotation': '#FFFFFF',
                         'fontColorOther': '#FFFFFF',
                         'fontMain': 'Arial',
                         'gridColor': '#888888',
                         'gridStyle': ':',
                         'mainFontSize': '10',
                         'spineColor': '#888888',
                         'spineColorOther': '#888888',
                         'tickColor': '#888888',
                         'tickColorOther': '#888888',
                         'tickFontSize': '8'}

        # Try to assign the value from plugin_prefs. If it doesn't work, add the key, value pair based on the defaults_dict above.
        # This should only be necessary the first time the plugin is configured.
        for key, value in defaults_dict.items():
            plugin_prefs[key] = plugin_prefs.get(key, value)

        self.logger.threaddebug(u"Updated initial plugin_prefs: {0}".format(dict(plugin_prefs)))
        return plugin_prefs

    def validatePrefsConfigUi(self, valuesDict):
        """ Validate select plugin config menu settings."""
        self.debugLevel = int(valuesDict['showDebugLevel'])
        self.indigo_log_handler.setLevel(self.debugLevel)
        self.logger.threaddebug(u"Config UI validator valuesDict: {0}".format(dict(valuesDict)))

        err_msg_dict = indigo.Dict()

        # Data and chart paths.
        for path_prop in ['chartPath', 'dataPath']:
            try:
                if not valuesDict[path_prop].endswith('/'):
                    err_msg_dict[path_prop]       = u"The path must end with a forward slash '/'."
                    err_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                    return False, valuesDict, err_msg_dict
            except AttributeError:
                self.pluginErrorHandler(traceback.format_exc())
                err_msg_dict[path_prop]       = u"The  path must end with a forward slash '/'."
                err_msg_dict['showAlertText'] = u"Path Error.\n\nYou have entered a path that does not end with a forward slash '/'."
                return False, valuesDict, err_msg_dict

        # Chart resolution.  Note that chart resolution includes a warning feature that will pass the value after the warning is cleared.
        try:
            # If value is null, a null string, or all whitespace.
            if not valuesDict['chartResolution'] or valuesDict['chartResolution'] == "" or valuesDict['chartResolution'].isspace():
                valuesDict['chartResolution'] = "100"
                self.logger.warning(u"No resolution value entered. Resetting resolution to 100 DPI.")
            # If warning flag and the value is potentially too small.
            elif valuesDict['dpiWarningFlag'] and 0 < int(valuesDict['chartResolution']) < 80:
                err_msg_dict['chartResolution'] = u"It is recommended that you enter a value of 80 or more for best results."
                err_msg_dict['showAlertText']   = u"Chart Resolution Warning.\n\nIt is recommended that you enter a value of 80 or more for best results."
                valuesDict['dpiWarningFlag']    = False
                return False, valuesDict, err_msg_dict

            # If no warning flag and the value is good.
            elif not valuesDict['dpiWarningFlag'] or int(valuesDict['chartResolution']) >= 80:
                pass
            else:
                err_msg_dict['chartResolution'] = u"The chart resolution value must be greater than 0."
                err_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nYou have entered a chart resolution value that is less than 0."
                return False, valuesDict, err_msg_dict
        except ValueError:
            self.pluginErrorHandler(traceback.format_exc())
            err_msg_dict['chartResolution'] = u"The chart resolution value must be an integer."
            err_msg_dict['showAlertText']   = u"Chart Resolution Error.\n\nYou have entered a chart resolution value that is not an integer."
            return False, valuesDict, err_msg_dict

        # Chart dimension properties.
        for dimension_prop in ['rectChartHeight', 'rectChartWidth', 'rectChartWideHeight', 'rectChartWideWidth', 'sqChartSize']:
            try:
                if float(valuesDict[dimension_prop]) < 100:
                    err_msg_dict[dimension_prop]  = u"The dimension value must be greater than 100 pixels."
                    err_msg_dict['showAlertText'] = u"Dimension Error.\n\nYou have entered a dimension value that is less than 100 pixels."
                    return False, valuesDict, err_msg_dict
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                err_msg_dict[dimension_prop]  = u"The dimension value must be a real number."
                err_msg_dict['showAlertText'] = u"Dimension Error.\n\nYou have entered a dimension value that is not a real number."
                return False, valuesDict, err_msg_dict

        # Line weight.
        try:
            if float(valuesDict['lineWeight']) <= 0:
                err_msg_dict['lineWeight']    = u"The line weight value must be greater than 0."
                err_msg_dict['showAlertText'] = u"Line Weight Error.\n\nYou have entered a line weight value that is less than 0."
                return False, valuesDict, err_msg_dict
        except ValueError:
            self.pluginErrorHandler(traceback.format_exc())
            err_msg_dict['lineWeight']    = u"The line weight value must be a real number."
            err_msg_dict['showAlertText'] = u"Line Weight Error.\n\nYou have entered a line weight value that is not a real number."
            return False, valuesDict, err_msg_dict

        valuesDict['dpiWarningFlag'] = True
        return True, valuesDict

    def closedPrefsConfigUi(self, valuesDict, userCancelled):
        """ User closes config menu. The validatePrefsConfigUI() method will
        also be called."""
        self.logger.threaddebug(u"Final valuesDict: {0}".format(dict(valuesDict)))

        # If the user selects Save, let's redraw the charts so that they reflect the new settings.
        # TODO: Is it worthwhile to only do this updating if something has changed?
        if not userCancelled:
            self.logger.info(u"{:=^80}".format(' Configuration saved. Regenerating Charts '))
            self.refreshTheCharts()
            self.logger.info(u"{:=^80}".format(' Regeneration complete. '))

    def getDeviceConfigUiValues(self, pluginProps, typeId, devId):
        """The getDeviceConfigUiValues() method is called when a device config
        is opened."""
        self.logger.debug(u"{0:*^40}".format(' Plugin Settings Menu '))
        self.logger.threaddebug(u"pluginProps = {0}".format(dict(pluginProps)))
        self.logger.threaddebug(u"typeId = {0}  devId = {0}".format(typeId, devId))

        try:

            # Make sure that the data entry fields of the CVS Engine device are in the proper state when the dialog is opened.
            if typeId == "csvEngine":
                pluginProps['addItemFieldsCompleted'] = False
                pluginProps['addKey']                 = ""
                pluginProps['addSource']              = ""
                pluginProps['addState']               = ""
                pluginProps['addValue']               = ""
                pluginProps['columnList']             = ""
                pluginProps['editKey']                = ""
                pluginProps['editSource']             = ""
                pluginProps['editState']              = ""
                pluginProps['editValue']              = ""
                pluginProps['isColumnSelected']       = False
                pluginProps['previousKey']            = ""
                self.logger.debug(u"Analyzing CSV Engine device settings.")
                return pluginProps

            else:
                # Establish a set of defaults for select device settings. Only those settings that are populated dynamically need
                # to be set here (the others can be set directly by the XML.)
                defaults_dict = {'bar1Color': '#FFFFFF',
                                 'bar1ColorOther': '#FFFFFF',
                                 'bar1Source': 'None',
                                 'bar2Color': '#FFFFFF',
                                 'bar2ColorOther': '#FFFFFF',
                                 'bar2Source': 'None',
                                 'bar3Color': '#FFFFFF',
                                 'bar3ColorOther': '#FFFFFF',
                                 'bar3Source': 'None',
                                 'bar4Color': '#FFFFFF',
                                 'bar4ColorOther': '#FFFFFF',
                                 'bar4Source': 'None',
                                 'customLineStyle': '-',
                                 'line1Color': '#FFFFFF',
                                 'line1ColorOther': '#FFFFFF',
                                 'line1Marker': 'None',
                                 'line1MarkerColor': '#FFFFFF',
                                 'line1MarkerColorOther': '#FFFFFF',
                                 'line1Source': 'None',
                                 'line1Style': 'None',
                                 'line2Color': '#FFFFFF',
                                 'line2ColorOther': '#FFFFFF',
                                 'line2Marker': 'None',
                                 'line2MarkerColor': '#FFFFFF',
                                 'line2MarkerColorOther': '#FFFFFF',
                                 'line2Source': 'None',
                                 'line2Style': 'None',
                                 'line3Color': '#FFFFFF',
                                 'line3ColorOther': '#FFFFFF',
                                 'line3Marker': 'None',
                                 'line3MarkerColor': '#FFFFFF',
                                 'line3MarkerColorOther': '#FFFFFF',
                                 'line3Source': 'None',
                                 'line3Style': 'None',
                                 'line4Color': '#FFFFFF',
                                 'line4ColorOther': '#FFFFFF',
                                 'line4Marker': 'None',
                                 'line4MarkerColor': '#FFFFFF',
                                 'line4MarkerColorOther': '#FFFFFF',
                                 'line4Source': 'None',
                                 'line4Style': 'None',
                                 'xAxisBins': 'daily',
                                 'xAxisLabelFormat': '%A',
                                 }

                # Try to assign the value from pluginProps. If it doesn't work, add the key, value pair based on the defaults_dict above.
                # This should only be necessary the first time the device is configured.
                self.logger.debug(u"Applying updated defaults as needed.")
                for key, value in defaults_dict.items():
                    pluginProps[key] = pluginProps.get(key, value)

            if self.pluginPrefs.get('enableCustomLineSegments', False):
                pluginProps['enableCustomLineSegmentsSetting'] = True
                self.logger.debug(u"Enabling advanced feature: Custom Line Segments.")
            else:
                pluginProps['enableCustomLineSegmentsSetting'] = False

            # If enabled, reset all device config dialogs to a minimized state (all sub-groups minimized upon open.)
            if self.pluginPrefs['snappyConfigMenus']:
                self.logger.debug(u"Enabling advanced feature: Snappy Config Menus.")
                pluginProps['xAxisLabel']  = False
                pluginProps['yAxisLabel']  = False
                pluginProps['y2AxisLabel'] = False
                pluginProps['barLabel1']   = False
                pluginProps['barLabel2']   = False
                pluginProps['barLabel3']   = False
                pluginProps['barLabel4']   = False
                pluginProps['lineLabel1']  = False
                pluginProps['lineLabel2']  = False
                pluginProps['lineLabel3']  = False
                pluginProps['lineLabel4']  = False

            return pluginProps

        except KeyError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.debug(u"!!!!! KeyError preparing device config values: {0} !!!!!".format(sub_error))

        return True

    def validateDeviceConfigUi(self, valuesDict, typeId, devId):
        """ Validate select device config menu settings."""
        self.logger.debug(u"{0:*^40}".format(' Validate Device Config UI '))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        err_msg_dict = indigo.Dict()

        # Chart Custom Dimensions.
        for custom_dimension_prop in ['customSizeHeight', 'customSizeWidth', 'customSizePolar']:
            try:
                if custom_dimension_prop in valuesDict.keys() and valuesDict[custom_dimension_prop] != 'None' and float(valuesDict[custom_dimension_prop]) < 100:
                    err_msg_dict[custom_dimension_prop] = u"The chart dimension value must be greater than 100 pixels."
                    err_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is less than 100 pixels."
                    return False, valuesDict, err_msg_dict
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                err_msg_dict[custom_dimension_prop] = u"The chart dimension value must be a real number."
                err_msg_dict['showAlertText']       = u"Chart Dimension Error.\n\nYou have entered a chart dimension value that is not a real number."
                valuesDict[custom_dimension_prop] = 'None'
                return False, valuesDict, err_msg_dict

        # Check to see that each axis limit matches one of the accepted formats.
        for limit_prop in ['yAxisMax', 'yAxisMin', 'y2AxisMax', 'y2AxisMin']:
            try:
                if limit_prop in valuesDict.keys() and valuesDict[limit_prop] not in ['None', '0']:
                    float(valuesDict[limit_prop])
            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                err_msg_dict[limit_prop]      = u"An axis limit must be a real number or None."
                err_msg_dict['showAlertText'] = u"Axis limit Error.\n\nA valid axis limit must be in the form of a real number or None."
                valuesDict[limit_prop] = 'None'
                return False, valuesDict, err_msg_dict

        return True, valuesDict

    def closedDeviceConfigUi(self, valuesDict, userCancelled, typeId, devId):
        """This routine will be called whenever the user has closed the device
        config dialog either by save or cancel. Note that a device can't be
        updated from here because valuesDict has yet to be saved."""
        self.logger.debug(u"{0:*^40}".format(' Closed Device Configuration Dialog '))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"userCancelled = {0}  typeId = {1}  devId = {2}".format(userCancelled, typeId, devId))

    def getMenuActionConfigUiValues(self, menuId):
        """The getMenuActionConfigUiValues() method loads the settings
        for the advanced settings menu dialog. Populates them, and
        sends them to the dialog as it's loaded."""
        self.logger.debug(u"{0:*^80}".format(' Advanced Settings Menu '))
        self.logger.debug(u"menuId = {0}".format(menuId))

        settings     = indigo.Dict()
        err_msg_dict = indigo.Dict()
        settings['enableCustomColors'] = self.pluginPrefs['enableCustomColors']
        settings['enableCustomLineSegments'] = self.pluginPrefs['enableCustomLineSegments']
        settings['promoteCustomLineSegments'] = self.pluginPrefs['promoteCustomLineSegments']
        settings['snappyConfigMenus'] = self.pluginPrefs['snappyConfigMenus']
        self.logger.debug(u"Advanced settings menu initial prefs: {0}".format(dict(settings)))

        return settings, err_msg_dict

    def advancedSettingsExecuted(self, valuesDict, menuId):
        """The advancedSettingsExecuted() method is a place where advanced
        settings will be controlled. This method takes the returned values
        and sends them to the pluginPrefs for permanent storage."""
        # Note that valuesDict here is for the menu, not all plugin prefs.
        self.logger.threaddebug(u"menuId = {0}".format(menuId))

        self.pluginPrefs['enableCustomColors']        = valuesDict['enableCustomColors']
        self.pluginPrefs['enableCustomLineSegments']  = valuesDict['enableCustomLineSegments']
        self.pluginPrefs['promoteCustomLineSegments'] = valuesDict['promoteCustomLineSegments']
        self.pluginPrefs['snappyConfigMenus']         = valuesDict['snappyConfigMenus']

        self.logger.debug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        self.logger.info(u"{:=^80}".format(' Advanced settings saved. Regenerating Charts. '))
        self.refreshTheCharts()
        self.logger.info(u"{:=^80}".format(' CycleRegeneration complete. '))
        return True

    def advancedSettingsMenu(self, valuesDict, typeId="", devId=None):
        """The advancedSettingsMenu() method is called when actions are taken
        within the Advanced Settings Menu item from the plugin menu."""
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        self.logger.info(u"Use of custom colors: {0}".format(valuesDict['enableCustomColors']))
        self.logger.info(u"Plot success messages: {0}".format(valuesDict['enableCustomLineSegments']))
        self.logger.info(u"Plot success messages: {0}".format(valuesDict['snappyConfigMenus']))
        self.logger.threaddebug(u"Advanced settings menu final prefs: {0}".format(dict(valuesDict)))
        return

    def addColumn(self, valuesDict, typeId="", devId=None):
        """The addColumn() method is called when the user clicks on the "Add
        Column" button in the CSV Engine config dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Add Column List Item '))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        err_msg_dict = indigo.Dict()

        try:
            column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict
            lister = [0]
            num_lister = []

            [lister.append(key.lstrip('k')) for key in sorted(column_dict.keys())]  # Create a list of existing keys with the 'k' lopped off
            [num_lister.append(int(item)) for item in lister]  # Change each value to an integer for evaluation
            next_key = u'k{0}'.format(int(max(num_lister)) + 1)  # Generate the next key
            column_dict[next_key] = (valuesDict['addValue'], valuesDict['addSource'], valuesDict['addState'])  # Save the tuple of properties
            valuesDict['columnDict'] = str(column_dict)  # Convert column_dict back to a string and prepare it for storage.

        except Exception, sub_error:
            self.logger.warning(u"Error adding column. {0}".format(sub_error))

        # Wipe the field values clean for the next element to be added.
        valuesDict['addValue'] = ""
        valuesDict['addSource'] = ""
        valuesDict['addState'] = ""

        return valuesDict, err_msg_dict

    def columnList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """The columnList() method generates the list of Column Key : Column
        Value pairs that will be presented in the CVS Engine device config
        dialog. It's called at open and routinely as changes are made in the
        dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Column List Generated '))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))

        try:
            # valuesDict['columnDict'] = valuesDict.get('columnDict', '{"k0": ("None", "None", "None")}')  # Just in case the user has deleted all CSV Engine elements
            valuesDict['columnDict'] = valuesDict.get('columnDict', '{}')  # Returning an empty dict seems to work and may solve the 'None' issue
            column_dict = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.
            prop_list   = [(key, "{0}".format(value[0])) for key, value in column_dict.items()]
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error generating column list. {0}".format(sub_error))
            prop_list = []
        return sorted(prop_list, key=lambda tup: tup[1])  # Return a list sorted by the value and not the key.

    def checkVersionNow(self):
        """ The checkVersionNow() method will call the Indigo Plugin Update
        Checker based on a user request. """

        self.updater.checkVersionNow()

    def deleteColumn(self, valuesDict, typeId="", devId=None):
        """The deleteColumn() method is called when the user clicks on the
        "Delete Column" button in the CSV Engine config dialog."""
        self.logger.debug(u"{0:*^40}".format(' CSV Device Delete Column List Item '))
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

    def csvSourceIdUpdated(self, typeId, valuesDict, devId):
        pass

    def deviceStateValueList(self, typeId, valuesDict, devId, targetId):

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

    def selectColumn(self, valuesDict, typeId="", devId=None):
        """The selectColumn() method is called when the user actually selects
        something within the Column List dropdown menu."""
        self.logger.debug(u"{0:*^40}".format(' Select Column '))
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
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"typeId = {0}  devId = {1}".format(typeId, devId))

        err_msg_dict = indigo.Dict()
        column_dict  = literal_eval(valuesDict['columnDict'])  # Convert column_dict from a string to a literal dict.

        try:
            key = valuesDict['editKey']
            previous_key = valuesDict['previousKey']
            if key != previous_key:
                if key in column_dict:
                    err_msg_dict['editKey'] = u"New key ({0}) already exists in the global properties, please use a different key value".format(key)
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

            if not len(err_msg_dict):
                valuesDict['previousKey'] = key

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Something went wrong: {0}".format(sub_error))

        valuesDict['columnDict'] = str(column_dict)  # Convert column_dict back to a string for storage.

        return valuesDict, err_msg_dict

    def refreshTheCSV(self):
        """The refreshTheCSV() method manages CSV files through CSV Engine
        custom devices."""
        self.logger.debug(u"{0:*^40}".format(' Refresh the CSV '))

        for dev in indigo.devices.itervalues("self"):

            if dev.deviceTypeId == 'csvEngine' and dev.enabled:

                import os
                csv_dict_str  = dev.pluginProps['columnDict']   # {key: (Column Name, Source ID, Source State)}
                csv_dict      = literal_eval(csv_dict_str)  # Convert column_dict from a string to a literal dict.

                # Read through the dict and construct headers and data
                for k, v in sorted(csv_dict.items()):

                    # Create a path variable that is based on the target folder and the CSV column name.
                    full_path = "{0}{1}.csv".format(self.pluginPrefs['dataPath'], v[0])

                    # If the appropriate CSV file doesn't exist, create it and write the header line.
                    if not os.path.isfile(full_path):
                        csv_file = open(full_path, 'w')
                        csv_file.write('{0},{1}\n'.format('Timestamp', v[0]))
                        csv_file.close()

                    # Determine the length of the CSV file and truncate if needed.
                    backup = "{0}{1} copy.csv".format(self.pluginPrefs['dataPath'], v[0])
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

                    # Write the file (retaining the header line and the last target_lines.
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
                        if int(v[1]) in indigo.devices:
                            state_to_write = u"{0}".format(indigo.devices[int(v[1])].states[v[2]])
                        elif int(v[1]) in indigo.variables:
                            state_to_write = u"{0}".format(indigo.variables[int(v[1])].value)
                        else:
                            state_to_write = u""
                            self.logger.critical(u"The settings for CSV Engine data element '{0}' are not valid: [dev: {1}, state/value: {2}]".format(v[0], v[1], v[2]))

                        # Give matplotlib something it can chew on if the value to be saved is 'None'
                        if state_to_write == 'None':
                            state_to_write = 'NaN'
                        if not state_to_write:
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
                                          {'key': 'onOffState', 'value': True, 'uiValue': 'Enabled'}])

                self.logger.info(u"CSV data updated successfully.")

            else:
                dev.updateStatesOnServer([{'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'}])

    def refreshTheCharts(self):
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

        k_dict  = {}  # A dict of kwarg dicts
        p_dict  = dict(self.pluginPrefs)  # A dict of plugin preferences (we set defaults and override with pluginPrefs).

        p_dict['font_style']  = 'normal'
        p_dict['font_weight'] = 'normal'
        p_dict['tick_bottom'] = 'on'
        p_dict['tick_left']   = 'on'
        p_dict['tick_right']  = 'off'
        p_dict['tick_top']    = 'off'

        # A dict of plugin prefs (copy that we modify on the fly. We don't want to modify the original.) We add dev props to it later.
        # p_dict  = dict(self.pluginPrefs)

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

        if self.pluginPrefs.get('gridColor', '#888888') == 'custom':
            plt.rcParams['grid.color'] = self.pluginPrefs.get('gridColorOther', '#888888')
        else:
            plt.rcParams['grid.color'] = self.pluginPrefs.get('gridColor', '#888888')

        if self.pluginPrefs.get('tickColor', '#888888') == 'custom':
            plt.rcParams['xtick.color'] = self.pluginPrefs.get('tickColorOther', '#888888')
            plt.rcParams['ytick.color'] = self.pluginPrefs.get('tickColorOther', '#888888')
        else:
            plt.rcParams['xtick.color'] = self.pluginPrefs.get('tickColor', '#888888')
            plt.rcParams['ytick.color'] = self.pluginPrefs.get('tickColor', '#888888')

        if self.pluginPrefs.get('fontColor', '#888888') == 'custom':
            p_dict['fontColor'] = self.pluginPrefs.get('fontColorOther', '#888888')
        else:
            p_dict['fontColor'] = self.pluginPrefs.get('fontColor', '#888888')

        if self.pluginPrefs.get('fontColorAnnotation', '#FFFFFF') == 'custom':
            p_dict['fontColorAnnotation'] = self.pluginPrefs.get('annotationColorOther', '#FFFFFF')
        else:
            p_dict['fontColorAnnotation'] = self.pluginPrefs.get('fontColorAnnotation', '#FFFFFF')

        if self.pluginPrefs.get('spineColor', '#888888') == 'custom':
            p_dict['spineColor'] = self.pluginPrefs.get('spineColorOther', '#888888')
        else:
            p_dict['spineColor'] = self.pluginPrefs.get('spineColor', '#888888')

        # Background color?
        if self.pluginPrefs.get('backgroundColor', '#000000') == 'custom':
            p_dict['backgroundColor'] = self.pluginPrefs.get('backgroundColorOther', '#000000')
            p_dict['transparent_charts'] = False
        elif self.pluginPrefs.get('backgroundColor', '#000000') == 'transparent':
            p_dict['backgroundColor'] = '#000000'
            p_dict['transparent_charts'] = True
        else:
            p_dict['transparent_charts'] = False

        # Plot Area color?
        if self.pluginPrefs.get('faceColor', '#000000') == 'custom':
            p_dict['faceColor'] = self.pluginPrefs.get('faceColorOther', '#000000')
            p_dict['transparent_filled'] = True
        elif self.pluginPrefs.get('faceColor', '#000000') == "transparent":
            if not p_dict['transparent_charts']:
                self.logger.warning(u"Global: No plot areas will appear as transparent because a background color has been specified.")
            p_dict['faceColor'] = '#000000'
            p_dict['transparent_filled'] = False
        else:
            p_dict['transparent_filled'] = True

        self.logger.threaddebug(u"{0:<19}{1}".format("Updated rcParams:  ", dict(plt.rcParams)))
        self.logger.threaddebug(u"{0:<19}{1}".format("Updated p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

        for dev in indigo.devices.itervalues("self"):

            # kwargs
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

            p_dict['bar_colors']     = []
            p_dict['data_array']     = []
            p_dict['dates_to_plot']  = []
            p_dict['headers']        = []
            p_dict['headers_1']      = ()  # Tuple
            p_dict['headers_2']      = ()  # Tuple
            p_dict['wind_direction'] = []
            p_dict['wind_speed']     = []
            p_dict['x_obs1']         = []
            p_dict['x_obs2']         = []
            p_dict['x_obs3']         = []
            p_dict['x_obs4']         = []
            p_dict['y_obs1']         = []
            p_dict['y_obs1_max']     = []
            p_dict['y_obs1_min']     = []
            p_dict['y_obs2']         = []
            p_dict['y_obs2_max']     = []
            p_dict['y_obs2_min']     = []
            p_dict['y_obs3']         = []
            p_dict['y_obs3_max']     = []
            p_dict['y_obs3_min']     = []
            p_dict['y_obs4']         = []
            p_dict['y_obs4_max']     = []
            p_dict['y_obs4_min']     = []

            if dev.enabled and dev.model != "CSV Engine":

                kv_list = []  # A list of state/value pairs used to feed updateStatesOnServer()
                kv_list.append({'key': 'onOffState', 'value': True, 'uiValue': 'Enabled'})
                p_dict.update(dev.pluginProps)

                # Custom font sizes for retina/non-retina adjustments.
                try:
                    if dev.pluginProps['customSizeFont']:
                        p_dict['mainFontSize'] = int(dev.pluginProps['customTitleFontSize'])
                        plt.rcParams['xtick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                        plt.rcParams['ytick.labelsize'] = int(dev.pluginProps['customTickFontSize'])
                except KeyError:
                    # Not all devices may support this feature.
                    pass

                # Limit number of observations
                try:
                    p_dict['numObs'] = int(p_dict['numObs'])
                except KeyError:
                    # Only some devices will have their own numObs.
                    pass
                except ValueError:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.warning(u"{0}: Custom size must be a positive number or None.")

                # Custom Square Size
                try:
                    if p_dict['customSizePolar'] != 'None':
                        p_dict['sqChartSize'] = float(p_dict['customSizePolar'])
                except KeyError:
                    pass
                except ValueError:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.warning(u"{0}: Custom size must be a positive number or None.")

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

                # Since users may or may not include axis labels and because we want to ensure that all plot areas present in the same way, we need to create 'phantom'
                # labels that are plotted but not visible.  Setting the font color to 'None' will effectively hide them.
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
                    if p_dict['customAxisLabelY2'].isspace() or p_dict['customAxisLabelY2'] == '':
                        p_dict['customAxisLabelY2'] = 'null'
                        k_dict['k_y2_axis_font']    = {'color': 'None', 'fontname': p_dict['fontMain'], 'fontsize': float(p_dict['mainFontSize']), 'fontstyle': p_dict['font_style'],
                                                       'weight': p_dict['font_weight'], 'visible': True}
                except KeyError:
                    self.pluginErrorHandler(traceback.format_exc())

                # If the user wants annotations, we need to hide the line markers as we don't want to plot one on top of the other.
                for line in range(1, 5, 1):
                    try:
                        if p_dict['line{0}Annotate'.format(line)] and p_dict['line{0}Marker'.format(line)] != 'None':
                            p_dict['line{0}Marker'.format(line)] = 'None'
                            self.logger.warning(u"{0}: Line {1} marker is suppressed to display annotations. "
                                                u"To see the marker, disable annotations for this line.".format(dev.name, line))
                    except KeyError:
                        self.pluginErrorHandler(traceback.format_exc())

                # Some line markers need to be adjusted due to their inherent value.  For example, matplotlib uses '<', '>' and '.' as markers but storing these values will
                # blow up the XML.  So we need to convert them. (See self.fixTheMarkers() method.)
                try:
                    if p_dict['line1Marker'] != 'None' or p_dict['line2Marker'] != 'None' or p_dict['line3Marker'] != 'None:' or p_dict['line4Marker'] != 'None:':
                        p_dict['line1Marker'], p_dict['line2Marker'], p_dict['line3Marker'], p_dict['line4Marker'] = self.fixTheMarkers(p_dict['line1Marker'],
                                                                                                                                        p_dict['line2Marker'],
                                                                                                                                        p_dict['line3Marker'],
                                                                                                                                        p_dict['line4Marker'])
                except KeyError:
                    self.pluginErrorHandler(traceback.format_exc())

                self.logger.debug(u"")
                self.logger.debug(u"{0:*^80}".format(u" Generating Chart: {0} ".format(dev.name)))

                # ======= Bar Charts ======
                if dev.deviceTypeId == 'barChartingDevice':
                    self.chartSimpleBar(dev, p_dict, k_dict, kv_list)

                # ======= Battery Status Charts ======
                if dev.deviceTypeId == "simpleBatteryChartingDevice":
                    self.chartSimpleBattery(dev, p_dict, k_dict, kv_list)

                # ======= Calendar Charts ======
                if dev.deviceTypeId == "calendarChartingDevice":
                    self.chartSimpleCalendar(dev, p_dict, k_dict)

                # ======= Line Charts ======
                if dev.deviceTypeId == "lineChartingDevice":
                    self.chartSimpleLine(dev, p_dict, k_dict, kv_list)

                # ======= Multiline Text ======
                if dev.deviceTypeId == 'multiLineText':
                    self.chartMultilineText(dev, p_dict, k_dict, kv_list)

                # ======= Polar Charts ======
                if dev.deviceTypeId == "polarChartingDevice":
                    self.chartPolar(dev, p_dict, k_dict, kv_list)

                # ======= Weather Forecast Charts ======
                if dev.deviceTypeId == "forecastChartingDevice":
                    self.chartWeatherForecast(dev, p_dict, k_dict, kv_list)

                # ======= Z-Wave Node Matrix Charts ======
                if dev.deviceTypeId == "simpleNodeMatrixChartingDevice":
                    self.chartSimpleNodeMatrix(dev, p_dict, k_dict, kv_list)

                try:
                    self.logger.threaddebug(u"Output chart: {0:<19}{1}".format(self.pluginPrefs['chartPath'], p_dict['fileName']))
                    self.logger.threaddebug(u"Output kwargs: {0:<19}".format(dict(**k_dict['k_plot_fig'])))
                    plt.savefig(u"{0}{1}".format(self.pluginPrefs['chartPath'], p_dict['fileName']), **k_dict['k_plot_fig'])

                    self.logger.info(u"{0} chart created successfully.".format(dev.name))

                except ValueError as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.critical(u"ValueError: {0}".format(sub_error))

                plt.clf()  # In theory, this is redundate of close('all') below
                plt.close('all')  # Changed plt.close() to plt.close('all') to see if it fixes the race/leak

            else:
                kv_list = []  # A list of state/value pairs used to feed updateStatesOnServer()
                if dev.model != "CSV Engine":
                    self.logger.info(u"Disabled: {0}: {1} [{2}] - Skipping plot sequence.".format(dev.model, dev.name, dev.id))
                    kv_list.append({'key': 'onOffState', 'value': False, 'uiValue': 'Disabled'})

            dev.updateStatesOnServer(kv_list)

    def refreshTheChartsMenuAction(self):
        """ Called by an Indigo Menu selection. """
        self.logger.debug(u"{0:*^40}".format(' User Call For Refresh '))
        self.refreshTheCharts()
        self.logger.info(u"{:=^80}".format(' Cycle complete. '))

    def refreshTheChartsAction(self, action):
        """ Called by an Indigo Action item. """

        # indigo.server.log(str(indigo.devices[action.deviceId].address))  # to pull something from the specified device
        # indigo.server.log(str(indigo.devices[action.deviceId].pluginProps['bar1Color']))  # to pull a prop from the specified device

        self.logger.debug(u"{0:*^40}".format(' Refresh Charts Action '))
        self.logger.threaddebug(u"  valuesDict: {0}".format(action))
        self.refreshTheCharts()
        self.logger.info(u"{:=^80}".format(' Cycle complete. '))

    def refreshTheChartsActionTest(self, action):
        """ Called by an Indigo Action item. """

        # indigo.server.log(u"action.props['foo'] = {0}".format(action.props))
        # indigo.server.log(u"action.props['foo'] = {0}".format(action.props['foo']))
        self.plotActionTest(action.props)

        self.logger.debug(u"{0:*^40}".format(' Refresh Charts Action '))
        self.logger.threaddebug(u"action dict: {0}".format(action))

    def plotActionTest(self, payload):
        """"""

        plt.plot(payload['x_values'], payload['y_values'])
        plt.savefig(u"{0}{1}".format(payload['path'], payload['filename']))
        plt.close('all')

    def chartSimpleBar(self, dev, p_dict, k_dict, kv_list):
        """"""

        try:

            dates_to_plot = p_dict['dates_to_plot']
            num_obs = p_dict['numObs']

            self.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            fig = plt.figure(1, figsize=(p_dict['chart_width'] / plt.rcParams['savefig.dpi'], p_dict['chart_height'] / plt.rcParams['savefig.dpi']))
            ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
            ax.margins(0.04, 0.05)

            # Spine properties
            [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

            # X Axis properties
            ax.tick_params(axis='x', **k_dict['k_major_x'])
            ax.tick_params(axis='x', **k_dict['k_minor_x'])
            ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))

            # Y Axis properties
            ax.tick_params(axis='y', **k_dict['k_major_y'])
            ax.tick_params(axis='y', **k_dict['k_minor_y'])
            ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision']))))

            for bar in range(1, 5, 1):

                # If the bar color is set to custom, set it to the custom value.
                if p_dict['bar{0}Color'.format(bar)] == 'custom':
                    p_dict['bar{0}Color'.format(bar)] = p_dict['bar{0}ColorOther']

                # If the bar color is the same as the background color, alert the user.
                if p_dict['bar{0}Color'.format(bar)] == p_dict['backgroundColor']:
                    self.logger.warning(u"{0}: Bar {0} color is the same as the background color (so you may not be able to see it).".format(dev.name, bar))

                # Plot the bars
                if p_dict['bar{0}Source'.format(bar)] not in ["", "None"]:

                    # Get the data and grab the header.
                    data_column = self.getTheData('{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['bar{0}Source'.format(bar)]))
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

            self.plotCustomLineSegments(ax, dates_to_plot, k_dict, p_dict)

            # Setting the limits before the plot turns off autoscaling, which causes the limit that's not set to behave weirdly at times.
            # This block is meant to overcome that weirdness for something more desirable.
            self.logger.threaddebug(u"Y Max: {0}  Y Min: {1}  Y Diff: {2}".format(max(p_dict['data_array']),
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
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. Set values to a real number or None. {1}".format(dev.name, sub_error))
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. {1}".format(dev.name, sub_error))

            # Set the scale for the X axis. We assume a date.
            self.setAxisScaleX(p_dict['xAxisBins'])

            # Plot the min/max lines if needed.  Note that these need to be plotted after the legend is established, otherwise some of the characteristics of the min/max
            # lines will take over the legend props.
            for bar in range(1, 5, 1):
                if p_dict['plotBar{0}Min'.format(bar)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:]), color=p_dict['bar{0}Color'.format(bar)], **k_dict['k_min'])
                if p_dict['plotBar{0}Max'.format(bar)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(bar)][len(p_dict['y_obs{0}'.format(bar)]) - num_obs:]), color=p_dict['bar{0}Color'.format(bar)], **k_dict['k_max'])

            # Chart title
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # X Axis Label - If the user chooses to display a legend, we don't want an axis label because they will fight with each other for space.
            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                self.logger.warning(u"{0}: X axis label is suppressed to make room for the chart legend.".format(dev.name))

            # Y Axis Label
            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

            # Add a patch so that we can have transparent charts but a filled plot area.
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Legend Properties
            self.logger.debug(u"Display legend: {0}".format(p_dict['showLegend']))
            if p_dict['showLegend']:
                legend = ax.legend(p_dict['headers'], loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, prop={'size': 6})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # Show X and Axis Grids?
            self.logger.debug(u"Display grids [X/Y]: {0} / {1}".format(p_dict['showxAxisGrid'], p_dict['showyAxisGrid']))
            if p_dict['showxAxisGrid']:
                plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])
            if p_dict['showyAxisGrid']:
                plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15, right=0.92)

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except IndexError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check the structure of the CSV file ({1})".format(dev.name, sub_error))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check path to CSV file ({1})".format(dev.name, sub_error))

    def chartSimpleBattery(self, dev, p_dict, k_dict, kv_list):
        """"""
        pass

    def chartSimpleCalendar(self, dev, p_dict, k_dict):
        """"""

        try:
            import calendar
            today = dt.datetime.today()
            calendar.setfirstweekday(int(dev.pluginProps['firstDayOfWeek']))
            cal = calendar.month(today.year, today.month)

            # fig = plt.figure(1, figsize=(p_dict['chart_width'] / plt.rcParams['savefig.dpi'], p_dict['chart_height'] / plt.rcParams['savefig.dpi']))
            fig = plt.figure(1, figsize=(3.5, 2.5))
            ax = fig.add_subplot(111)

            ax.text(0, 1, cal, transform=ax.transAxes, color=p_dict['fontColor'], fontname='Andale Mono', fontsize=dev.pluginProps['fontSize'], backgroundcolor=p_dict['faceColor'],
                    bbox=dict(pad=3), **k_dict['k_calendar'])
            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)
            ax.axis('off')  # uncomment this line to hide the box

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check path to CSV file ({1})".format(dev.name, sub_error))

    def chartSimpleLine(self, dev, p_dict, k_dict, kv_list):
        """"""

        try:

            dates_to_plot = p_dict['dates_to_plot']

            self.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            fig = plt.figure(1, figsize=(p_dict['chart_width'] / plt.rcParams['savefig.dpi'], p_dict['chart_height'] / plt.rcParams['savefig.dpi']))
            ax = fig.add_subplot(111, axisbg=p_dict['faceColor'])
            ax.margins(0.04, 0.05)

            [ax.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

            ax.tick_params(axis='x', **k_dict['k_major_x'])
            ax.tick_params(axis='x', **k_dict['k_minor_x'])
            ax.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))

            ax.tick_params(axis='y', **k_dict['k_major_y'])
            ax.tick_params(axis='y', **k_dict['k_minor_y'])
            ax.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision']))))

            for line in range(1, 5, 1):

                # If line color is custom, set it equal to the custom color value.
                if p_dict['line{0}Color'.format(line)] == 'custom':
                    p_dict['line{0}Color'.format(line)] = p_dict['line{0}ColorOther'.format(line)]

                # If line marker color is custom, set it equal to the custom color value.
                if p_dict['line{0}MarkerColor'.format(line)] == 'custom':
                    p_dict['line{0}MarkerColor'.format(line)] = p_dict['line{0}MarkerColorOther'.format(line)]

                # If line color is the same as the background color, alert the user.
                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    self.logger.warning(u"{0}: Line {1} color is the same as the background color (so you may not be able to see it).".format(dev.name, line))

                # Plot the lines
                if p_dict['line{0}Source'.format(line)] not in ["", "None"]:

                    data_column = self.getTheData('{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['line{0}Source'.format(line)]))
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

                    # num_obs = len(p_dict['y_obs{0}'.format(line)])  # TODO: what is the story with num_obs? Let's comment it out and see if anything breaks.

                    if p_dict['line{0}Fill'.format(line)]:
                        ax.fill_between(dates_to_plot, 0, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], **k_dict['k_fill'])

                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax.annotate(u"{0}".format(xy[1]), xy=xy, xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            self.plotCustomLineSegments(ax, dates_to_plot, k_dict, p_dict)

            self.logger.threaddebug(u"Y Max: {0}  Y Min: {1}  Y Diff: {2}".format(max(p_dict['data_array']),
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
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. Set values to a real number or None. {1}".format(dev.name, sub_error))
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. {1}".format(dev.name, sub_error))

            # Set the scale for the X axis. We assume a date.
            self.setAxisScaleX(p_dict['xAxisBins'])

            # For lines 1-4, plot min and max as warranted.
            for line in range(1, 5, 1):
                if p_dict['plotLine{0}Min'.format(line)]:
                    ax.axhline(y=min(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_min'])
                if p_dict['plotLine{0}Max'.format(line)]:
                    ax.axhline(y=max(p_dict['y_obs{0}'.format(line)]), color=p_dict['line{0}Color'.format(line)], **k_dict['k_max'])

            # Transparent Chart Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Legend
            self.logger.debug(u"Display legend: {0}".format(p_dict['showLegend']))
            if p_dict['showLegend']:
                legend = ax.legend(p_dict['headers'], loc='upper center', bbox_to_anchor=(0.5, -0.1), ncol=4, prop={'size': 6})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # Grids
            self.logger.debug(u"Display grids [X/Y]: {0} / {1}".format(p_dict['showxAxisGrid'], p_dict['showyAxisGrid']))
            if p_dict['showxAxisGrid']:
                plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])
            if p_dict['showyAxisGrid']:
                plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], **k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                self.logger.warning(u"{0}: X axis label is suppressed to make room for the chart legend.".format(dev.name))

            plt.ylabel(p_dict['customAxisLabelY'], **k_dict['k_y_axis_font'])

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15, right=0.92)

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except IndexError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check the structure of the CSV file ({1})".format(dev.name, sub_error))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check path to CSV file ({1})".format(dev.name, sub_error))

    def chartMultilineText(self, dev, p_dict, k_dict, kv_list):
        """"""

        try:

            import textwrap

            if p_dict['textColor'] == 'custom':
                p_dict['textColor'] = p_dict['textColorOther']

            self.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            text_to_plot = u""
            try:
                if int(p_dict['thing']) in indigo.devices:
                    text_to_plot = unicode(indigo.devices[int(p_dict['thing'])].states[p_dict['thingState']])
                elif int(p_dict['thing']) in indigo.variables:
                    text_to_plot = unicode(indigo.variables[int(p_dict['thing'])].value)
                else:
                    text_to_plot = u"Unable to reconcile plot text. Confirm device settings."
                    self.logger.info(u"Presently, the plugin only supports device state and variable values.")

                # The cleanUpString method tries to remove some potential ugliness from the text to be plotted.
                text_to_plot = self.cleanUpString(text_to_plot)

            except ValueError:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Multiline text device {0} not fully configured. Please check the settings.".format(dev.name))

            if len(text_to_plot) <= 1:
                text_to_plot = p_dict['defaultText']
            text_to_plot = textwrap.fill(text_to_plot, int(p_dict['numberOfCharacters']))

            fig = plt.figure(figsize=(float(p_dict['figureWidth']) / plt.rcParams['savefig.dpi'], float(p_dict['figureHeight']) / plt.rcParams['savefig.dpi']))
            ax = fig.add_subplot(111)

            ax.set_axis_bgcolor(p_dict['faceColor'])
            ax.text(0.01, 0.95, text_to_plot, transform=ax.transAxes, color=p_dict['textColor'], fontname=p_dict['fontMain'], fontsize=p_dict['multilineFontSize'],
                    verticalalignment='top')

            ax.axes.get_xaxis().set_visible(False)
            ax.axes.get_yaxis().set_visible(False)

            # Transparent Charts Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Chart title
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            plt.tight_layout(pad=1)
            plt.subplots_adjust(left=0.02, right=0.98, top=0.9, bottom=0.05)

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except (KeyError, IndexError, ValueError) as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check the structure of the CSV file ({1})".format(dev.name, sub_error))
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.critical(u"{0}: Check path to CSV file ({1})".format(dev.name, sub_error))

    def chartSimpleNodeMatrix(self, dev, p_dict, k_dict, kv_list):
        """"""
        pass

    def chartPolar(self, dev, p_dict, k_dict, kv_list):
        # Note that the polar chart device can be used for other things, but it is coded like a wind rose which makes it easier to understand what's happening.
        # Note that it would be possible to convert wind direction names (north-northeast) to an ordinal degree value, however, it would be very difficult to
        # contend with all of the possible international Unicode values that could be passed to the device.  Better to make it the responsibility of the user
        # to convert their data to degrees.

        try:
            self.final_data    = []
            num_obs = p_dict['numObs']

            if p_dict['currentWindColor'] == 'custom':
                p_dict['currentWindColor'] = p_dict['currentWindColorOther']

            if p_dict['maxWindColor'] == 'custom':
                p_dict['maxWindColor'] = p_dict['maxWindColorOther']

            self.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            # Grab the column headings for the labels, then delete the row from self.final_data.
            theta_path = '{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['thetaValue'])  # The name of the theta file.
            radii_path = '{0}{1}'.format(self.pluginPrefs['dataPath'], p_dict['radiiValue'])  # The name of the radii file.

            if theta_path != 'None' and radii_path != 'None':

                try:
                    # Get the data.
                    self.final_data.append(self.getTheData(theta_path))
                    self.final_data.append(self.getTheData(radii_path))

                    # Pull out the header information out of the data.
                    # p_dict['headers'] = (self.final_data[0][0][1], self.final_data[1][0][1])
                    del self.final_data[0][0]
                    del self.final_data[1][0]

                    # Create lists of data to plot (string -> float).
                    [p_dict['wind_direction'].append(float(item[1])) for item in self.final_data[0]]
                    [p_dict['wind_speed'].append(float(item[1])) for item in self.final_data[1]]

                    p_dict['wind_direction'] = p_dict['wind_direction'][len(p_dict['wind_direction']) - num_obs: len(p_dict['wind_direction'])]
                    p_dict['wind_speed'] = p_dict['wind_speed'][len(p_dict['wind_speed']) - num_obs: len(p_dict['wind_speed'])]

                except IndexError as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.critical(u"{0}: Check the structure of the CSV file ({1})".format(dev.name, sub_error))
                except Exception as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.critical(u"{0}: Check path to CSV file ({1})".format(dev.name, sub_error))

                # Create the array of grey scale for the intermediate lines and set the last one red. (MPL will accept string values '0' - '1' as grey scale, so we create
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

                # polar(theta, r, color)
                wind = zip(p_dict['wind_direction'], p_dict['wind_speed'], p_dict['bar_colors'])

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
                    plt.text(0.5, 0.5, u"Holy crap!", color='#FFFFFF', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes,
                             bbox=dict(facecolor='red', alpha=0.5))

                # Plot circles for current obs and max wind. Note that we reduce the value of the circle plot so that it appears when transparent charts are enabled (otherwise
                # the circle is obscured. The transform can be done one of two ways: access the private attribute "ax.transData._b", or "ax.transProjectionAffine + ax.transAxes".
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
                self.logger.debug(u"Display legend: {0}".format(p_dict['showLegend']))
                if p_dict['showLegend']:
                    legend = ax.legend(([u"Current", u"Maximum"]), loc='upper center', bbox_to_anchor=(0.5, -0.05), ncol=2, prop={'size': 6})
                    legend.legendHandles[0].set_color(p_dict['currentWindColor'])
                    legend.legendHandles[1].set_color(p_dict['maxWindColor'])
                    [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                    frame = legend.get_frame()
                    frame.set_alpha(0)

                self.logger.debug(u"Display grids[X / Y]: always on")

                # Chart title
                plt.title(p_dict['chartTitle'], position=(0, 1.0), **k_dict['k_title_font'])

                kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except ValueError:
            self.pluginErrorHandler(traceback.format_exc())
        except KeyError:
            self.pluginErrorHandler(traceback.format_exc())

    def chartWeatherForecast(self, dev, p_dict, k_dict, kv_list):
        """"""

        try:
            dates_to_plot = p_dict['dates_to_plot']

            for line in range(1, 4, 1):

                if p_dict['line{0}Color'.format(line)] == 'custom':
                    p_dict['line{0}Color'.format(line)] = p_dict['line{0}ColorOther'.format(line)]

                if p_dict['line{0}Color'.format(line)] == p_dict['backgroundColor']:
                    self.logger.warning(u"{0}: High temperature color is the same as the background color (so you may not be able to see it).".format(dev.name))

                if line < 3:
                    if p_dict['line{0}MarkerColor'.format(line)] == 'custom':
                        p_dict['line{0}MarkerColor'.format(line)] = p_dict['line{0}MarkerColorOther'.format(line)]

            self.logger.threaddebug(u"{0:<19}{1}".format("p_dict: ", [(k, v) for (k, v) in sorted(p_dict.items())]))

            # Prepare the data for charting.
            if indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId == 'wundergroundHourly':

                for counter in range(1, 25, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states
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

                self.logger.debug(u"Data retrieved successfully: {0} [{1}]".format(dev.name, dev.id))
                self.logger.debug(u"{0:<19}{1}".format("Final data:", zip(p_dict['x_obs1'], p_dict['y_obs1'], p_dict['y_obs2'], p_dict['y_obs3'])))

            elif indigo.devices[int(p_dict['forecastSourceDevice'])].deviceTypeId == 'wundergroundTenDay':

                for counter in range(1, 11, 1):
                    if counter < 10:
                        counter = '0{0}'.format(counter)
                    state_list = indigo.devices[int(p_dict['forecastSourceDevice'])].states
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

                self.logger.debug(u"Data retrieved successfully: {0} [{1}]".format(dev.name, dev.id))
                self.logger.debug(u"{0:<19}{1}".format("Final data:", zip(p_dict['x_obs1'], p_dict['y_obs1'], p_dict['y_obs2'], p_dict['y_obs3'])))

            else:
                self.logger.warning(u"This device type only supports WUnderground plugin forecast devices.")

            fig = plt.figure(1, figsize=(p_dict['chart_width'] / plt.rcParams['savefig.dpi'], p_dict['chart_height'] / plt.rcParams['savefig.dpi']))
            ax1 = fig.add_subplot(111, axisbg=p_dict['faceColor'])
            ax1.margins(0.04, 0.05)

            # Spine properties
            [ax1.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

            # X1 Axis properties
            ax1.tick_params(axis='x', **k_dict['k_major_x'])
            ax1.tick_params(axis='x', **k_dict['k_minor_x'])
            ax1.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))

            # Y1 Axis properties
            ax1.tick_params(axis='y', **k_dict['k_major_y'])
            ax1.tick_params(axis='y', **k_dict['k_minor_y'])
            ax1.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision']))))

            # Plot the chance of precipitation bars.  The width of the bars is a percentage of a day, so we need to account for instances where the unit of time could be
            # hours to months or years.
            if p_dict['y_obs3']:
                if len(dates_to_plot) <= 15:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=((1.0 / len(dates_to_plot)) * 5), alpha=0.25, zorder=3)
                else:
                    ax1.bar(dates_to_plot, p_dict['y_obs3'], align='center', color=p_dict['line3Color'], width=(1.0 / (len(dates_to_plot) * 1.75)), alpha=0.25, zorder=3)

                if p_dict['line3Annotate']:
                    for xy in zip(dates_to_plot, p_dict['y_obs3']):
                        ax1.annotate('%.0f' % xy[1], xy=(xy[0], 5), xytext=(0, 0), zorder=10, **k_dict['k_annotation'])

            plt.ylim(0, 100)

            # X Axis Label
            if not p_dict['showLegend']:
                plt.xlabel(p_dict['customAxisLabelX'], k_dict['k_x_axis_font'])
            if p_dict['showLegend'] and p_dict['customAxisLabelX'].strip(' ') not in ['', 'null']:
                self.logger.warning(u"{0}: X axis label [{1}] is suppressed to make room for the chart legend.".format(dev.name, p_dict['customAxisLabelX']))

            # Y1 Axis Label
            plt.ylabel(p_dict['customAxisLabelY'], labelpad=20, **k_dict['k_y_axis_font'])

            # Legend Properties (note that we need a separate instance of this code for each subplot. This one controls the precipitation subplot.)
            self.logger.debug(u"Display legend 1: {0}".format(p_dict['showLegend']))
            if p_dict['showLegend']:
                legend = ax1.legend(p_dict['headers_2'], loc='upper right', bbox_to_anchor=(1.0, -0.1), ncol=1, prop={'size': 6})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)

            # Show Axis Grids?
            self.logger.debug(u"Display grids 1 [X/Y]: {0} / {1}".format(p_dict['showxAxisGrid'], p_dict['showyAxisGrid']))
            if p_dict['showxAxisGrid']:
                plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])
            if p_dict['showy2AxisGrid']:
                plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

            # Transparent Charts Fill
            if p_dict['transparent_charts'] and p_dict['transparent_filled']:
                ax1.add_patch(patches.Rectangle((0, 0), 1, 1, transform=ax1.transAxes, facecolor=p_dict['faceColor'], zorder=1))

            # Create a second plot area and plot the temperatures.
            ax2 = ax1.twinx()
            ax2.margins(0.04, 0.05)
            [ax2.spines[spine].set_color(p_dict['spineColor']) for spine in ('top', 'bottom', 'left', 'right')]

            for line in range(1, 3, 1):
                if p_dict['y_obs{0}'.format(line)]:
                    ax2.plot(dates_to_plot, p_dict['y_obs{0}'.format(line)], color=p_dict['line{0}Color'.format(line)], linestyle=p_dict['line{0}Style'.format(line)],
                             marker=p_dict['line{0}Marker'.format(line)], markerfacecolor=p_dict['line{0}MarkerColor'.format(line)], zorder=(10 - line), **k_dict['k_line'])
                    [p_dict['data_array'].append(node) for node in p_dict['y_obs{0}'.format(line)]]

                    if p_dict['line{0}Annotate'.format(line)]:
                        for xy in zip(dates_to_plot, p_dict['y_obs{0}'.format(line)]):
                            ax2.annotate('%.0f' % xy[1], xy=xy, xytext=(0, 0), zorder=(11 - line), **k_dict['k_annotation'])

            self.plotCustomLineSegments(ax2, dates_to_plot, k_dict, p_dict)

            # y1, y2 = ax2.get_ylim()
            # plt.ylim((y1 * .9), y2)

            # X2 Axis properties
            ax2.tick_params(axis='x', **k_dict['k_major_x'])
            ax2.tick_params(axis='x', **k_dict['k_minor_x'])
            ax2.xaxis.set_major_formatter(mdate.DateFormatter(p_dict['xAxisLabelFormat']))

            # Y1 Axis properties
            [label.set_fontproperties(p_dict['fontMain']) for label in ax2.get_yticklabels()]
            ax2.tick_params(axis='y', **k_dict['k_major_y2'])
            ax2.tick_params(axis='y', **k_dict['k_minor_y2'])
            ax2.yaxis.set_major_formatter(mtick.FormatStrFormatter(u"%.{0}f".format(int(p_dict['yAxisPrecision']))))

            plt.autoscale(enable=True, axis='x', tight=None)

            # Note that we plot the bar plot so that it will be under the line plot, but we still want the temperature scale on the left and the percentages on the right.
            ax1.yaxis.tick_right()
            ax2.yaxis.tick_left()

            self.logger.threaddebug(u"Y1 Max: {0}  Y1 Min: {1}  Y1 Diff: {2}".format(max(p_dict['data_array']),
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
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. Set values to a real number or None.".format(dev.name))
            except Exception as sub_error:
                self.pluginErrorHandler(traceback.format_exc())
                self.logger.warning(u"Warning: trouble with {0} Y Min or Y Max. {1}".format(dev.name, sub_error))

            # Set the scale for the X axis. We assume a date.
            self.setAxisScaleX(p_dict['xAxisBins'])

            # Chart title
            plt.title(p_dict['chartTitle'], position=(0.5, 1.0), **k_dict['k_title_font'])

            # Y2 Axis Label
            plt.ylabel(p_dict['customAxisLabelY2'], labelpad=20, **k_dict['k_y2_axis_font'])

            # Legend Properties (note that we need a separate instance of this code for each subplot. This one controls the temperatures subplot.)
            self.logger.debug(u"Display legend 2: {0}".format(p_dict['showLegend']))
            if p_dict['showLegend']:
                legend = ax2.legend(p_dict['headers_1'], loc='upper left', bbox_to_anchor=(0.0, -0.1), ncol=2, prop={'size': 6})
                [text.set_color(p_dict['fontColor']) for text in legend.get_texts()]
                frame = legend.get_frame()
                frame.set_alpha(0)  # Note: frame alpha should be an int and not '0'.

            # Grids
            self.logger.debug(u"Display grids 2 [X/Y]: {0} / {1}".format(p_dict['showxAxisGrid'], p_dict['showyAxisGrid']))
            if p_dict['showxAxisGrid']:
                plt.gca().xaxis.grid(True, **k_dict['k_grid_fig'])
            if p_dict['showyAxisGrid']:
                plt.gca().yaxis.grid(True, **k_dict['k_grid_fig'])

            plt.tight_layout(pad=1)
            plt.subplots_adjust(top=0.9, bottom=0.15)

            kv_list.append({'key': 'chartLastUpdated', 'value': u"{0}".format(dt.datetime.now())})

        except ValueError as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Something went wrong: {0}".format(sub_error))
        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Something went wrong: {0}".format(sub_error))

    def cleanUpString(self, val):
        """The cleanUpString(self, val) method is used to scrub multiline text
        elements in order to try to make them more presentable. The need is
        easily seen by looking at the rough text that is provided by the U.S.
        National Weather Service, for example."""
        self.logger.debug(u"{0:*^40}".format(" Clean Up String "))
        self.logger.debug(u"Length of initial string: {0}".format(len(val)))

        # List of (elements, replacements)
        clean_list = [(' am ', ' AM '), (' pm ', ' PM '), ('*', ' '), ('\u000A', ' '), ('...', ' '), ('/ ', '/'), (' /', '/'), ('/', ' / ')]

        # Take the old, and replace it with the new.
        for (old, new) in clean_list:
            val = val.replace(old, new)

        val = ' '.join(val.split())  # Eliminate spans of whitespace.

        self.logger.debug(u"Length of final string: {0}".format(len(val)))
        return val

    def deviceStateGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        """The deviceStateGenerator() method produces a list of device states
        and variables. Each device list includes only states for the selected
        device.
        """
        self.logger.debug(u"{0:*^40}".format(' Device State Generator '))
        self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))
        state_list = []

        # If there are no devices created yet.
        if not valuesDict:
            return state_list

        if valuesDict and "thing" in valuesDict:
            # If an item has been selected.
            if valuesDict['thing'] not in ["", "None"]:
                device_string = int(valuesDict['thing'])
                try:
                    # If it's a device, grab the selected state.
                    for devID in indigo.devices.iterkeys():
                        if device_string == devID:
                            # If there's no device specified, the state is NoneType.
                            for state in indigo.devices[device_string].states:
                                # if ".ui" in state or "All" in state or "zone" in state:
                                if any(item in state for item in (".ui", "All", "zone")):
                                    pass
                                else:
                                    state_list.append(state)

                    # If it's not a device, it's a variable. Grab it's value.
                    for varID in indigo.variables.iterkeys():
                        if device_string == varID:
                            var = indigo.variables[device_string].name
                            state_list.append(var + u" value")

                # If it's somehow not a device or a variable, skip it.
                except Exception as sub_error:
                    self.pluginErrorHandler(traceback.format_exc())
                    self.logger.info(u"Element not of device type or variable type. Skipping. {0}".format(sub_error))

                # Append the list with a "None" choice.
                state_list.append("None")
                return state_list

            # If an item has not been selected, return and empty list.
            else:
                return state_list

    def fixTheMarkers(self, line1_marker, line2_marker, line3_marker, line4_marker):
        """ The devices.xml file cannot contain '<' or '>' as a value, as this
        conflicts with the construction of the XML code.  Matplotlib needs
        these values for select built-in marker styles, so we need to change
        them to what MPL is expecting."""
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

        self.logger.threaddebug(u"axis_list_menu: {0}".format(axis_list_menu))
        return axis_list_menu

    def getBinList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of bins for the X axis."""
        self.logger.debug(u"{0:*^40}".format(' Get Bin List '))
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        bin_list_menu = [
            ("quarter-hourly", "Every 15 Minutes"),
            ("half-hourly", "Every 30 Minutes"),
            ("hourly", "Every Hour"),
            ("daily", "Every Day"),
            ("weekly", "Every Week"),
            ("monthly", "Every Month"),
            ("yearly", "Every Year")]

        self.logger.threaddebug(u"bin_list_menu: {0}".format(bin_list_menu))
        return bin_list_menu

    def getBackgroundColorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of available colors. There are two color lists. This
        list is for things that support transparency (e.g., background and plot
        area."""
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        background_color_list_menu = [
            ("#000000", "Black"),
            ("#111111", "Grey(9)"),
            ("#222222", "Grey(8)"),
            ("#333333", "Grey(7)"),
            ("#444444", "Grey(6)"),
            ("#555555", "Grey(5)"),
            ("#666666", "Grey(4)"),
            ("#777777", "Grey(3)"),
            ("#888888", "Grey(2)"),
            ("#999999", "Grey(1)"),
            ("#FFFFFF", "White"),
            ("#FF0000", "Red"),
            ("#FFA500", "Orange"),
            ("#FFFF00", "Yellow"),
            ("#008000", "Green"),
            ("#0000FF", "Blue"),
            ("#4B0082", "Indigo"),
            ("#EE82EE", "Violet"),
            ("transparent", "Transparent")]

        try:
            if self.pluginPrefs['enableCustomColors']:
                background_color_list_menu.append(("custom", "Custom"))
        except KeyError:
            self.pluginErrorHandler(traceback.format_exc())

        return background_color_list_menu

    def getColorList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Returns a list of available colors. There are two color lists. This
        list is for things that don't support transparency (e.g., fonts, lines,
        etc.)"""
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        color_list_menu = [
            ("#000000", "Black"),
            ("#111111", "Grey(9)"),
            ("#222222", "Grey(8)"),
            ("#333333", "Grey(7)"),
            ("#444444", "Grey(6)"),
            ("#555555", "Grey(5)"),
            ("#666666", "Grey(4)"),
            ("#777777", "Grey(3)"),
            ("#888888", "Grey(2)"),
            ("#999999", "Grey(1)"),
            ("#FFFFFF", "White"),
            ("#FF0000", "Red"),
            ("#FFA500", "Orange"),
            ("#FFFF00", "Yellow"),
            ("#008000", "Green"),
            ("#0000FF", "Blue"),
            ("#4B0082", "Indigo"),
            ("#EE82EE", "Violet")]

        try:
            if self.pluginPrefs['enableCustomColors']:
                color_list_menu.append(("custom", "Custom"))
        except KeyError:
            self.pluginErrorHandler(traceback.format_exc())

        return color_list_menu

    def getFontList(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Generates and returns a list of fonts.  Note that these are the
        fonts that Matplotlib can see, not necessarily all of the fonts
        installed on the system."""
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
        """Returns a list of possible font sizes."""
        self.logger.threaddebug(u"Constructing font size list.")
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        font_size_menu = [
            ("6", "6"),
            ("7", "7"),
            ("8", "8"),
            ("9", "9"),
            ("10", "10"),
            ("11", "11"),
            ("12", "12"),
            ("13", "13"),
            ("14", "14"),
            ("15", "15"),
            ("16", "16"),
            ("17", "17"),
            ("18", "18"),
            ("19", "19"),
            ("20", "20")]

        return font_size_menu

    def getForecastSource(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Generates and returns a list of potential forecast devices for the
        forecast devices type. Presently, the plugin only works with
        WUnderground devices, but the intention is to expand the list of
        compatible devices going forward."""
        self.logger.debug(u"{0:*^40}".format(' Get Forecast Source '))
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
        self.logger.threaddebug(u"Constructing line list.")
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        line_list_menu = [
            ("None", "None"),
            ("--", "Dashed"),
            (":", "Dotted"),
            ("-.", "Dot Dash"),
            ("-", "Solid"),
            ("steps", "Steps")]

        return line_list_menu

    def getListOfFiles(self, filter="", valuesDict=None, typeId="", targetId=0):
        """Get list of CSV files."""
        self.logger.debug(u"{0:*^40}".format(' Get List of Files '))
        self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        file_name_list_menu = []
        source_path = self.pluginPrefs.get('dataPath', '/Library/Application Support/Perceptive Automation/Indigo 7/Logs/com.fogbert.indigoplugin.matplotlib/')

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
        self.logger.threaddebug(u"filter = {0}  typeId = {1}  targetId = {2}".format(filter, typeId, targetId))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))

        marker_list_menu = [
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
            ("x", "X")]

        self.logger.threaddebug(u"marker_list_menu: {0}".format(marker_list_menu))
        return marker_list_menu

    def getTheData(self, data_source):
        """ Get the data. """

        final_data = []
        try:
            data_file  = open(data_source, "r")
            csv_data   = reader(data_file, delimiter=',')
            [final_data.append(item) for item in csv_data]
            data_file.close()
            self.logger.debug(u"Data retrieved successfully: {0}".format(data_source))

        except Exception as sub_error:
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.warning(u"Error downloading CSV data. Skipping: {0}".format(sub_error))

        self.logger.debug(u"{0:<19}{1}".format("Final data: ", final_data))
        return final_data

    def listGenerator(self, filter="", valuesDict=None, typeId="", targetId=0):
        """This method collects IDs and names for all Indigo devices and
        variables. It creates a dictionary of the form
        ((dev.id, dev.name), (var.id, var.name)). It prepends (D) or (V) to
        make it easier to distinguish between the two.
        """
        self.logger.debug(u"{0:*^40}".format(' List Generator '))
        self.logger.threaddebug(u"valuesDict: {0}".format(dict(valuesDict)))
        self.logger.threaddebug(u"filter = {0} typeId = {1}  devId = {2}".format(filter, typeId, targetId))

        dev_list = [(dev.id, u"(D) {0}".format(dev.name)) for dev in indigo.devices]
        var_list = [(var.id, u"(V) {0}".format(var.name)) for var in indigo.variables]

        device_variable_list_menu = dev_list + var_list
        device_variable_list_menu.append((u"None", u"None"))

        self.logger.debug(u"List generator data generated successfully.\nDevice List:\n{0}\nVariable List:\n{1}".format(dev_list, var_list))
        return device_variable_list_menu

    def plotCustomLineSegments(self, ax, dates_to_plot, k_dict, p_dict):  #  TODO: Can we remove dates_to_plot now since we don't need it?  Don't forget to remove it from the call, too.
        """"""
        # Plot the custom lines if needed.  Note that these need to be plotted after the legend is established, otherwise some of the characteristics of the min/max
        # lines will take over the legend props.
        self.logger.debug(u"Custom line segments ({0}): {1}".format(p_dict['enableCustomLineSegments'], p_dict['customLineSegments']))

        if p_dict['enableCustomLineSegments'] and p_dict['customLineSegments'] not in ["", "None"]:
            try:
                # num_obs = len(dates_to_plot)  # TODO: what is the story with num_obs? Let's comment it out and see if anything breaks.
                constants_to_plot = literal_eval(p_dict['customLineSegments'])
                for element in constants_to_plot:
                    if type(element) == tuple:
                        cls = ax.axhline(y=element[0], color=element[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        # If we want to promote custom line segments, we need to add them to the list that's used to calculate the Y axis limits.
                        if self.pluginPrefs['promoteCustomLineSegments']:
                            p_dict['data_array'].append(element[0])
                    else:
                        cls = ax.axhline(y=constants_to_plot[0], color=constants_to_plot[1], linestyle=p_dict['customLineStyle'], marker='', **k_dict['k_custom'])

                        if self.pluginPrefs['promoteCustomLineSegments']:
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

    def runConcurrentThread(self):
        """"""
        self.logger.info(u"{:=^80}".format(' Initializing Concurrent Thread '))
        self.sleep(0.5)

        try:
            while True:
                self.updater.checkVersionPoll()
                self.refreshTheCSV()
                self.refreshTheCharts()
                self.logger.info(u"{:=^80}".format(' Cycle complete. '))

                # Trying ensure that garbage is collected before sleeping.
                gc.collect()
                self.sleep(int(self.pluginPrefs.get('refreshInterval', '900')))
                self.logger.info(u"{:=^80}".format(' Cycling Concurrent Thread '))

        except self.StopThread():
            self.pluginErrorHandler(traceback.format_exc())
            self.logger.debug(u"self.stopThread() called.")