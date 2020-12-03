#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
maintenance is a container for code that makes specific to consolidate methods used throughout all
Indigo plugins with the com.fogbert.indigoPlugin.xxxx bundle identifier.
"""

try:
    import indigo
except ImportError:
    pass
import logging
import re

__author__ = "DaveL17"
__build__ = "Unused"
__copyright__ = "Copyright 2017-2019 DaveL17"
__license__ = "MIT"
__title__ = "maintenance"
__version__ = "0.1.02"


class Maintain(object):

    def __init__(self, plugin):
        self.plugin = plugin
        self.pluginPrefs = plugin.pluginPrefs

        fmt = '%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s'
        self.plugin.plugin_file_handler.setFormatter(logging.Formatter(fmt, datefmt='%Y-%m-%d %H:%M:%S'))

        self.plugin.logger.threaddebug(u"Initializing maintenance framework.")

    def clean_prefs(self, dev_name, prefs):
        """
        Remove legacy keys from non-chart device prefs

        -----

        :param unicode dev_name:
        :param dict prefs:
        :return:
        """

        list_of_removed_keys = []
        list_of_keys_to_remove = (
            'annotationColorOther',
            'area1adjuster',
            'area1Annotate',
            'area1Color',
            'area1ColorOther',
            'area1Fill',
            'area1Marker',
            'area1MarkerColor',
            'area1Max',
            'area1Min',
            'area1Source',
            'area1Style',
            'area2adjuster',
            'area2Annotate',
            'area2Color',
            'area2ColorOther',
            'area2Fill',
            'area2Marker',
            'area2MarkerColor',
            'area2Max',
            'area2Min',
            'area2Source',
            'area2Style',
            'area3adjuster',
            'area3Annotate',
            'area3Color',
            'area3ColorOther',
            'area3Fill',
            'area3Marker',
            'area3MarkerColor',
            'area3Max',
            'area3Min',
            'area3Source',
            'area3Style',
            'area4adjuster',
            'area4Annotate',
            'area4Color',
            'area4ColorOther',
            'area4Fill',
            'area4Marker',
            'area4MarkerColor',
            'area4Max',
            'area4Min',
            'area4Source',
            'area4Style',
            'area5adjuster',
            'area5Annotate',
            'area5Color',
            'area5Fill',
            'area5Marker',
            'area5MarkerColor',
            'area5Max',
            'area5Min',
            'area5Source',
            'area6adjuster',
            'area6Annotate',
            'area6Color',
            'area6Fill',
            'area6Marker',
            'area6MarkerColor',
            'area6Source',
            'area7adjuster',
            'area7Annotate',
            'area7Color',
            'area7Fill',
            'area7Marker',
            'area7MarkerColor',
            'area7Source',
            'area8adjuster',
            'area8Annotate',
            'area8Color',
            'area8Fill',
            'area8Marker',
            'area8MarkerColor',
            'area8Source',
            'areaLabel1',
            'areaLabel2',
            'areaLabel3',
            'areaLabel4',
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
            'line7adjuster',
            'line7Annotate',
            'line7BestFit',
            'line7BestFitColor',
            'line7Color',
            'line7Fill',
            'line7Marker',
            'line7MarkerColor',
            'line7Source',
            'line8adjuster',
            'line8Annotate',
            'line8BestFit',
            'line8BestFitColor',
            'line8Color',
            'line8Fill',
            'line8Marker',
            'line8MarkerColor',
            'line8Source',
            'lineLabel1',
            'lineLabel2',
            'lineLabel3',
            'lineLabel4',
            'notificationsHeaderSpace',
            'notificationsLabel',
            'offColor',
            'onColor',
            'plotArea1Max',
            'plotArea1Min',
            'plotArea2Max',
            'plotArea2Min',
            'plotArea3Max',
            'plotArea3Min',
            'plotArea4Max',
            'plotArea4Min',
            'plotArea5Max',
            'plotArea5Min',
            'plotArea6Max',
            'plotArea6Min',
            'plotArea7Max',
            'plotArea7Min',
            'plotArea8Max',
            'plotArea8Min',
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
            'plotLine7Max',
            'plotLine7Min',
            'plotLine8Max',
            'plotLine8Min',
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
            self.plugin.logger.debug(u"[{d}] Performing maintenance - removing unneeded keys: "
                                     u"{k}".format(d=dev_name, k=list_of_removed_keys))

        return prefs

    def clean_props(self, dev):
        """
        Remove legacy keys from device prefs

        # TODO: Note that at some point most, if not all, of this method can go away.
        -----

        :return:
        """

        props = dev.pluginProps

        def string_props_to_bool(bool_item):

            if not isinstance(props[bool_item], bool):
                if props[bool_item].strip() in ('False', 'false', ''):
                    props[bool_item] = False
                elif props[bool_item] in ('True', 'true'):
                    props[bool_item] = True

        # ================================ All Devices ================================
        # Set whether it's a chart device or not
        is_chart_dict = {'areaChartingDevice': True,
                         'barChartingDevice': True,
                         'batteryHealthDevice': True,
                         'calendarChartingDevice': True,
                         'csvEngine': False,
                         'compositeForecastDevice': True,
                         'forecastChartingDevice': True,
                         'lineChartingDevice': True,
                         'multiLineText': True,
                         'polarChartingDevice': True,
                         'rcParamsDevice': False,
                         'scatterChartingDevice': True}

        props['isChart'] = is_chart_dict[dev.deviceTypeId]

        # ============================= Non-chart Devices =============================
        if dev.deviceTypeId in ('csvEngine', 'rcParamsDevice'):

            # Remove legacy cruft from csv engine and rcParams device props
            props = self.clean_prefs(dev.name, props)

        # =============================== Chart Devices ===============================
        elif dev.deviceTypeId not in ('csvEngine', 'rcParamsDevice'):

            try:
                # Ensure that these values are not empty.
                if props['customTitleFontSize'] == "":
                    props['customTitleFontSize'] = '12'
                if props['customTickFontSize'] == "":
                    props['customTickFontSize'] = '8'
            except KeyError:
                pass

            # ============================= Fix Custom Colors =============================
            # For all chart device types
            # Update legacy color values from hex to raw (#FFFFFF --> FF FF FF)
            for prop in props:
                if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', unicode(props[prop])):
                    self.plugin.logger.debug(u"[{d}] Refactoring color property: ({p})".format(d=dev.name, p=prop))
                    props[prop] = u'{r} {g} {b}'.format(r=prop[0:3], g=prop[3:5], b=prop[5:7]).replace('#', '')

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

                            self.plugin.logger.debug(u"Resetting legacy device preferences for custom colors to new "
                                                     u"color picker.")

                            if props[u'{p}Other'.format(p=prop)]:
                                props[prop] = props[u'{0}Other'.format(prop)]

                            else:
                                props[prop] = 'FF FF FF'

            # ============================== Fix Area Props ===============================
            if dev.deviceTypeId == 'areaChartingDevice':

                for _ in range(1, 9, 1):

                    # Coerce these props to bool if needed.
                    for item in ('area{i}Annotate'.format(i=_),
                                 'line{i}BestFit'.format(i=_),
                                 'area{i}Fill'.format(i=_),
                                 'areaLabel{i}'.format(i=_),
                                 'plotArea{i}Max'.format(i=_),
                                 'plotArea{i}Min'.format(i=_),
                                 'suppressArea{i}'.format(i=_),
                                 ):

                        if item in dev.ownerProps.keys():
                            string_props_to_bool(bool_item=item)

            # =============================== Fix Bar Props ===============================
            if dev.deviceTypeId == 'barChartingDevice':

                for _ in range(1, 5, 1):

                    # Coerce these props to bool if needed.
                    for item in ('bar{i}Annotate'.format(i=_),
                                 'barLabel{i}'.format(i=_),
                                 'plotBar{i}Max'.format(i=_),
                                 'plotBar{i}Min'.format(i=_),
                                 'suppressBar{i}'.format(i=_),
                                 ):

                        if item in dev.ownerProps.keys():
                            if not isinstance(props[item], bool):
                                if props[item].strip() in ('False', 'false', ''):
                                    props[item] = False
                                else:
                                    props[item] = True

            # ========================= Fix Battery Health Props ==========================
            if dev.deviceTypeId == 'batteryHealthDevice':

                # Coerce these props to bool if needed.
                for item in ('showBatteryLevel', 'showBatteryLevelBackground'):
                    if not isinstance(props[item], bool):
                        if props[item].strip() in ('False', 'false', ''):
                            props[item] = False
                        else:
                            props[item] = True

            # ============================ Fix Calendar Props =============================
            if dev.deviceTypeId == 'calendarChartingDevice':

                pass

            # ============================== Fix Line Props ===============================
            if dev.deviceTypeId == 'lineChartingDevice':

                for _ in range(1, 9, 1):

                    # Coerce these props to bool if needed.
                    for item in ('line{i}Annotate'.format(i=_),
                                 'line{i}BestFit'.format(i=_),
                                 'line{i}Fill'.format(i=_),
                                 'lineLabel{i}'.format(i=_),
                                 'plotLine{i}Max'.format(i=_),
                                 'plotLine{i}Min'.format(i=_),
                                 'suppressLine{i}'.format(i=_),
                                 ):

                        if item in dev.ownerProps.keys():
                            string_props_to_bool(bool_item=item)

            # ========================= Fix Multiline Text Props ==========================
            if dev.deviceTypeId == 'multiLineText':

                # Coerce these props to bool if needed.
                for item in ('textAreaBorder',
                             'cleanTheText',
                             ):

                    if item in dev.ownerProps.keys():
                        if not isinstance(props[item], bool):
                            if props[item].strip() in ('False', 'false', ''):
                                props[item] = False
                            elif props[item] in ('True', 'true'):
                                props[item] = True

            # ============================== Fix Polar Props ==============================
            if dev.deviceTypeId == 'polarChartingDevice':

                pass

            # ============================= Fix Scatter Props =============================
            if dev.deviceTypeId == 'scatterChartingDevice':

                # Coerce these props to bool if needed.
                for _ in range(1, 4, 1):

                    for item in ('line{i}BestFit'.format(i=_),
                                 'groupLabel{i}'.format(i=_),
                                 'line{i}BestFit'.format(i=_),
                                 'plotGroup{i}Min'.format(i=_),
                                 'plotGroup{i}Max'.format(i=_),
                                 'suppressGroup{i}'.format(i=_),
                                 ):

                        if item in dev.ownerProps.keys():
                            string_props_to_bool(bool_item=item)
                        else:
                            props[item] = False

            # ============================ Fix Forecast Props =============================
            if dev.deviceTypeId == 'forecastChartingDevice':

                for _ in range(1, 4, 1):

                    # Coerce these props to bool if needed.
                    for item in (
                                 'lineLabel{i}'.format(i=_),
                                 'line{i}Annotate'.format(i=_),
                                 ):

                        if 'item' in dev.ownerProps.keys():
                            if not isinstance(props[item], bool):
                                if props[item].strip() in ('False', 'false', ''):
                                    props[item] = False
                                elif props[item] in ('True', 'true'):
                                    props[item] = True

            # =============== Establish Refresh Interval for Legacy Devices ===============
            # Establish refresh interval for legacy devices. If the prop isn't present, we
            # set it equal to the user's current global refresh rate.
            if 'refreshInterval' not in props.keys():
                self.plugin.logger.debug(u"Adding refresh interval to legacy device. Set to 900 seconds.")
                props['refreshInterval'] = self.pluginPrefs.get('refreshInterval', 900)

        # ============================= Update the Server =============================
        dev.replacePluginPropsOnServer(props)

        if self.plugin.pluginPrefs['verboseLogging']:
            self.plugin.logger.threaddebug(u"[{name}] prefs cleaned.".format(name=dev.name))
