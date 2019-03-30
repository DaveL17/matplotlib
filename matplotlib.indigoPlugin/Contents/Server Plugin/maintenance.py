#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
maintenance is a container for code that makes specific to consolidate methods used throughout all
Indigo plugins with the com.fogbert.indigoPlugin.xxxx bundle identifier.
"""

import indigo
import logging
import re

__author__ = "DaveL17"
__build__ = "Unused"
__copyright__ = "Copyright 2017-2019 DaveL17"
__license__ = "MIT"
__title__ = "maintenance"
__version__ = "0.1.01"


class Maintain(object):

    def __init__(self, plugin):
        self.plugin = plugin
        self.pluginPrefs = plugin.pluginPrefs

        self.plugin.plugin_file_handler.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s', datefmt='%Y-%m-%d %H:%M:%S'))

        self.plugin.logger.threaddebug(u"Initializing maintenance framework.")

    def clean_prefs(self, dev_name, prefs):
        """
        Remove legacy keys from plugin and device prefs

        -----

        :param unicode dev_name:
        :param dict prefs:
        :return:
        """

        list_of_removed_keys = []
        list_of_keys_to_remove = (
            'annotationColorOther',
            'bar_colors',
            'barLabel1',
            'barLabel2',
            'barLabel3',
            'barLabel4',
            'chart_height',
            'chart_width',
            'chartTitle',
            'csv_item_add',
            'customAxisLabelX',
            'customAxisLabelY',
            'customAxisLabelY2',
            'customLineStyle',
            'customSizeHeight',
            'customSizeWidth',
            'data_array',
            'dates_to_plot',
            'defaultColor',
            'deviceControlsLabel',
            'deviceControlsSeparator',
            'dynamicDeviceList',
            'emailLabel',
            'enableCustomColors',
            'enableCustomLineSegmentsSetting',
            'fileName',
            'font_style',
            'font_weight',
            'fontColorOther',
            'foo',
            'forecastSourceDevice',
            'gridColorOther',
            'line1adjuster',
            'line1Annotate',
            'line1BestFit',
            'line1BestFitColor',
            'line1Color',
            'line1ColorOther',
            'line1Fill',
            'line1Marker',
            'line1MarkerColor',
            'line1MarkerColorOther',
            'line1Max',
            'line1Min',
            'line1Source',
            'line1Style',
            'line2adjuster',
            'line2Annotate',
            'line2BestFit',
            'line2BestFitColor',
            'line2Color',
            'line2ColorOther',
            'line2Fill',
            'line2Marker',
            'line2MarkerColor',
            'line2MarkerColorOther',
            'line2Max',
            'line2Min',
            'line2Source',
            'line2Style',
            'line3adjuster',
            'line3Annotate',
            'line3BestFit',
            'line3BestFitColor',
            'line3Color',
            'line3ColorOther',
            'line3Fill',
            'line3Marker',
            'line3MarkerColor',
            'line3MarkerColorOther',
            'line3Max',
            'line3Min',
            'line3Source',
            'line3Style',
            'line4adjuster',
            'line4Annotate',
            'line4BestFit',
            'line4BestFitColor',
            'line4Color',
            'line4ColorOther',
            'line4Fill',
            'line4Marker',
            'line4MarkerColor',
            'line4MarkerColorOther',
            'line4Max',
            'line4Min',
            'line4Source',
            'line4Style',
            'line5adjuster',
            'line5Annotate',
            'line5BestFit',
            'line5BestFitColor',
            'line5Color',
            'line5Fill',
            'line5Marker',
            'line5MarkerColor',
            'line5Max',
            'line5Min',
            'line5Source',
            'line6adjuster',
            'line6Annotate',
            'line6BestFit',
            'line6BestFitColor',
            'line6Color',
            'line6Fill',
            'line6Marker',
            'line6MarkerColor',
            'line6Source',
            'lineLabel1',
            'lineLabel2',
            'lineLabel3',
            'lineLabel4',
            'notificationsHeaderSpace',
            'notificationsLabel',
            'offColor',
            'onColor',
            'plotLine1Max',
            'plotLine1Min',
            'plotLine2Max',
            'plotLine2Min',
            'plotLine3Max',
            'plotLine3Min',
            'plotLine4Max',
            'plotLine4Min',
            'plotLine5Max',
            'plotLine5Min',
            'plotLine6Max',
            'plotLine6Min',
            'saveSettingsLabel',
            'saveSettingsSeparator',
            'showLegend',
            'showNotificationSettings',
            'showxAxisGrid',
            'showy2AxisGrid',
            'showyAxisGrid',
            'spineColorOther',
            'test',
            'tickColorOther',
            'updaterEmail',
            'updaterEmailsEnabled',
            'updaterLastCheck',
            'updaterLastVersionEmailed',
            'wind_direction',
            'wind_speed',
            'x_obs1',
            'x_obs2',
            'x_obs3',
            'x_obs4',
            'xAxisBins',
            'xAxisLabel',
            'xAxisLabelFormat',
            'y_obs1_max',
            'y_obs1_min',
            'y_obs1',
            'y_obs2_max',
            'y_obs2_min',
            'y_obs2',
            'y_obs3_max',
            'y_obs3_min',
            'y_obs3',
            'y_obs4_max',
            'y_obs4_min',
            'y_obs4',
            'y2AxisLabel',
            'y2AxisMax',
            'y2AxisMin',
            'y2AxisPrecision',
            'yAxisLabel',
            'yAxisMax',
            'yAxisMin',
            'yAxisPrecision'
        )

        # Iterate the keys to delete and delete them if they exist
        for key in list_of_keys_to_remove:
            if key in prefs.keys():
                list_of_removed_keys.append(key)
                del prefs[key]

        # Log list of removed keys
        if list_of_removed_keys:
            self.plugin.logger.debug(u"[{0}] Performing maintenance - removing unneeded keys: {1}".format(dev_name, list_of_removed_keys))

        return prefs

    def clean_props(self):
        """
        Remove legacy keys from plugin prefs

        -----

        :return:
        """

        for dev in indigo.devices.itervalues("self"):

            props = dev.pluginProps

            # ================================ All Devices ================================
            # Set whether it's a chart device or not
            is_chart_dict = {'barChartingDevice': True,
                             'batteryHealthDevice': True,
                             'calendarChartingDevice': True,
                             'csvEngine': False,
                             'forecastChartingDevice': True,
                             'lineChartingDevice': True,
                             'multiLineText': True,
                             'polarChartingDevice': True,
                             'rcParamsDevice': False,
                             'scatterChartingDevice': True}

            props['isChart'] = is_chart_dict[dev.deviceTypeId]

            # ========================== Battery Health Devices ===========================
            if dev.deviceTypeId in ('batteryHealthDevice',):

                # Some legacy devices had the battery level prop established as a string.
                if props['showBatteryLevel'] in ('true', 'True'):
                    props['showBatteryLevel'] = True
                else:
                    props['showBatteryLevel'] = False

                # Some legacy devices had the battery level box prop established as a string.
                if props['showBatteryLevelBackground'] in ('true', 'True'):
                    props['showBatteryLevelBackground'] = True
                else:
                    props['showBatteryLevelBackground'] = False

            # =============================== Chart Devices ===============================
            if dev.deviceTypeId not in ('csvEngine', 'rcParamsDevice'):

                # ============================= Fix Custom Colors =============================
                # Update legacy color values from hex to raw (#FFFFFF --> FF FF FF)
                for prop in props:
                    if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', unicode(props[prop])):
                        self.plugin.logger.debug(u"[{0}] Refactoring color property: ({1})".format(dev.name, prop))
                        props[prop] = u'{0} {1} {2}'.format(prop[0:3], prop[3:5], prop[5:7]).replace('#', '')

                # ======================== Reset Legacy Color Settings ========================
                # Initially, the plugin was constructed with a standard set of colors that
                # could be overwritten by electing to set a custom color value. With the
                # inclusion of the color picker control, this was no longer needed. So we try
                # to set the color field to the custom value. This block is for device color
                # preferences. They should be updated whether or not the device is enabled in
                # the Indigo UI.
                if '#custom' in props.values() or 'custom' in props.values():
                    for prop in props:
                        if 'color' in prop.lower():
                            if props[prop] in ('#custom', 'custom'):

                                self.plugin.logger.debug(u"Resetting legacy device preferences for custom colors to new color picker.")

                                if props[u'{0}Other'.format(prop)]:
                                    props[prop] = props[u'{0}Other'.format(prop)]

                                else:
                                    props[prop] = 'FF FF FF'

                # ================================= Fix Props =================================
                # Some early devices were created with the device prop as the wrong type. Let's
                # go ahead and fix those.

                # =============================== Fix Bar Props ===============================
                if dev.deviceTypeId == 'barChartingDevice':

                    for _ in range(1, 5, 1):

                        for item in ('bar{0}Annotate'.format(_),
                                     'barLabel{0}'.format(_),
                                     'plotBar{0}Max'.format(_),
                                     'plotBar{0}Min'.format(_),
                                     'suppressBar{0}'.format(_),
                                     ):

                            if item in dev.ownerProps.keys():
                                if not isinstance(props[item], bool):
                                    if props[item] in ('False', 'false', ''):
                                        props[item] = False
                                    elif props[item] in ('True', 'true'):
                                        props[item] = True

                    for prop in props.keys():
                        if prop.startswith(('line', 'group', 'suppressLine', 'suppressGroup', 'plotLine')):
                            del props[prop]

                # ============================ Fix Calendar Props =============================
                elif dev.deviceTypeId == 'calendarChartingDevice':

                    for prop in props.keys():
                        if prop.startswith(('bar', 'group', 'line', 'plotLine', 'suppressBar', 'suppressGroup', 'suppressLine')):
                            del props[prop]

                # ============================== Fix Line Props ===============================
                elif dev.deviceTypeId == 'lineChartingDevice':

                    for _ in range(1, 7, 1):

                        for item in ('line{0}Annotate'.format(_),
                                     'line{0}BestFit'.format(_),
                                     'line{0}Fill'.format(_),
                                     'lineLabel{0}'.format(_),
                                     'plotLine{0}Max'.format(_),
                                     'plotLine{0}Min'.format(_),
                                     'suppressLine{0}'.format(_),
                                     ):

                            if item in dev.ownerProps.keys():
                                if not isinstance(props[item], bool):
                                    if props[item] in ('False', 'false', ''):
                                        props[item] = False
                                    elif props[item] in ('True', 'true'):
                                        props[item] = True

                    for prop in props.keys():
                        if prop.startswith(('bar', 'group', 'suppressBar', 'suppressGroup')):
                            del props[prop]

                # ========================= Fix Multiline Text Props ==========================
                elif dev.deviceTypeId == 'multiLineText':

                    for item in ('textAreaBorder',
                                 'cleanTheText',
                                 ):

                        if item in dev.ownerProps.keys():
                            if not isinstance(props[item], bool):
                                if props[item] in ('False', 'false', ''):
                                    props[item] = False
                                elif props[item] in ('True', 'true'):
                                    props[item] = True

                    for prop in props.keys():
                        if prop.startswith(('bar', 'enableCustomLineSegmentsSetting', 'group', 'line', 'plotLine', 'suppressBar', 'suppressGroup', 'suppressLine')):
                            del props[prop]

                # ============================== Fix Polar Props ==============================
                elif dev.deviceTypeId == 'polarChartingDevice':

                    for prop in props.keys():
                        if prop.startswith(('bar', 'enableCustomLineSegmentsSetting', 'group', 'line', 'plotLine', 'suppressBar', 'suppressGroup', 'suppressLine')):
                            del props[prop]

                # ============================= Fix Scatter Props =============================
                elif dev.deviceTypeId == 'scatterChartingDevice':

                    for _ in range(1, 4, 1):

                        for item in ('line{0}BestFit'.format(_),
                                     'groupLabel{0}'.format(_),
                                     'line{0}Fill'.format(_),
                                     'line{0}BestFit'.format(_),
                                     'plotGroup{0}Min'.format(_),
                                     'plotGroup{0}Max'.format(_),
                                     'suppressGroup{0}'.format(_),
                                     ):

                            if item in dev.ownerProps.keys():
                                if not isinstance(props[item], bool):
                                    if props[item] in ('False', 'false', ''):
                                        props[item] = False
                                    elif props[item] in ('True', 'true'):
                                        props[item] = True
                            else:
                                props[item] = False

                    for prop in props.keys():
                        if prop.startswith(('bar', 'plotLine', 'suppressBar', 'suppressLine')):
                            del props[prop]

                # ============================ Fix Forecast Props =============================
                elif dev.deviceTypeId == 'forecastChartingDevice':

                    for _ in range(1, 4, 1):

                        for item in (
                                     'lineLabel{0}'.format(_),
                                     'line{0}Annotate'.format(_),
                                     ):

                            if 'item' in dev.ownerProps.keys():
                                if not isinstance(props[item], bool):
                                    if props[item] in ('False', 'false', ''):
                                        props[item] = False
                                    elif props[item] in ('True', 'true'):
                                        props[item] = True

                    for prop in props.keys():
                        if prop.startswith(('bar', 'group',
                                            'line4', 'line5', 'line6',
                                            'line1adjuster', 'line2adjuster', 'line3adjuster',
                                            'lineLabel4', 'lineLabel5', 'lineLabel6',
                                            'line1BestFit', 'line2BestFit', 'line3BestFit',
                                            'line1BestFitColor', 'line2BestFitColor', 'line3BestFitColor',
                                            'plotLine4', 'plotLine5', 'plotLine6',
                                            'plotLine1Max', 'plotLine2Max', 'plotLine3Max',
                                            'plotLine1Min', 'plotLine2Min', 'plotLine3Min',
                                            'suppressBar', 'suppressGroup',
                                            'suppressLine4', 'suppressLine5', 'suppressLine6')):
                            del props[prop]

                # =============== Establish Refresh Interval for Legacy Devices ===============
                # Establish refresh interval for legacy devices. If the prop isn't present, we
                # set it equal to the user's current global refresh rate.
                if 'refreshInterval' not in props.keys():
                    self.plugin.logger.debug(u"Adding refresh interval to legacy device. Set to 900 seconds.")
                    props['refreshInterval'] = self.pluginPrefs.get('refreshInterval', 900)

            # ============================= Non-chart Devices =============================
            elif dev.deviceTypeId in ('csvEngine', 'rcParamsDevice'):

                # Remove legacy cruft from csv engine and rcParams device props
                props = self.clean_prefs(dev.name, props)

            # ============================= Update the Server =============================
            dev.replacePluginPropsOnServer(props)

            self.plugin.logger.debug(u"[{0}] prefs cleaned.".format(dev.name))

    # def clean_dev_props(self, dev):
    #
    #     import xml.etree.ElementTree as ET
    #
    #     current_prefs = []
    #     dead_prefs = []
    #
    #     # Get the device's current Devices.xml config
    #     config_prefs = self.plugin.devicesTypeDict[dev.deviceTypeId]["ConfigUIRawXml"]
    #     config_prefs = ET.ElementTree(ET.fromstring(config_prefs))
    #
    #     # Iterate the XML to get the field IDs
    #     for pref in config_prefs.findall('Field'):
    #         dev_id = unicode(pref.get('id'))
    #         current_prefs.append(dev_id)
    #
    #     self.plugin.logger.info(u"Current config prefs: {0}".format(sorted(current_prefs)))
    #
    #     # Get the device's current config. There may be prefs here that are not
    #     # in Devices.xml but are still valid (they may have been added dynamically).
    #     dev_prefs = dev.pluginProps
    #     self.plugin.logger.info(u"Current device prefs: {0}".format(sorted(dict(dev_prefs).keys())))
    #
    #     # prefs in the device that aren't in the config
    #     for pref in dev_prefs:
    #         if pref not in current_prefs:
    #             dead_prefs.append(pref)
    #
    #     self.plugin.logger.info(u"Device prefs not in current config: {0}".format(sorted(dead_prefs)))
