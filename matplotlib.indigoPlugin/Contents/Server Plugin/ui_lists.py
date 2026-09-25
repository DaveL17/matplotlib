# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Dropdown/list-generator callbacks for Indigo config UI dialogs.

Covers static option lists (precision, line style, marker, axis format), device/source-derived
lists (battery devices, forecast source devices, CSV files, system fonts, the redraw-charts menu),
and the CSV Engine add/edit-item state-or-value dropdowns.
"""
import glob
import logging
import os
import traceback
import datetime as dt

import indigo  # noqa
from matplotlib import font_manager as mfont

from constants import FONT_MENU
import log_utils

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the ui_lists module (no-op placeholder)."""


# =============================================================================
def device_state_value_list_add(values_dict: indigo.Dict) -> list:
    """Return the list of device states or variable value for the CSV Engine add-item control.

    Once the user selects a device or variable in the CSV Engine add-item dialog, populates the
    state/value dropdown. Returns the device's states (excluding UI states) for devices, or
    [('value', 'value')] for variables. Returns a placeholder if no source is selected or the
    filter does not match the source type.

    Args:
        values_dict (indigo.Dict): The current dialog values, containing 'addSource' and
            'addSourceFilter'.

    Returns:
        list: A list of state/value identifier strings or placeholder tuples.
    """
    result = None
    if values_dict['addSource'] != '':
        try:
            # User has selected an Indigo device element and then set the filter to Variables
            # only.
            if int(values_dict['addSource']) in indigo.devices \
                    and values_dict['addSourceFilter'] == "V":
                result = [('None', 'Please select a data source first')]

            # User has selected an Indigo device element and the filter is set to Devices only or Show All.
            elif int(values_dict['addSource']) in indigo.devices \
                    and values_dict['addSourceFilter'] != "V":
                dev = indigo.devices[int(values_dict['addSource'])]
                result = [x for x in dev.states if ".ui" not in x]

            elif int(values_dict['addSource']) in indigo.variables \
                    and values_dict['addSourceFilter'] != "D":
                result = [('value', 'value')]

            elif int(values_dict['addSource']) in indigo.variables \
                    and values_dict['addSourceFilter'] == "D":
                result = [('None', 'Please select a data source first')]

        except ValueError:
            result = [('None', 'Please select a data source first')]

    else:
        result = [('None', 'Please select a data source first')]

    return result


# =============================================================================
def device_state_value_list_edit(values_dict: indigo.Dict) -> list:
    """Return the list of device states or variable value for the CSV Engine edit-item control.

    Once the user selects a device or variable in the CSV Engine edit-item dialog, populates the
    state/value dropdown. Returns the device's states (excluding UI states) for devices, or
    [('value', 'value')] for variables. Returns a placeholder if no source is selected or the
    filter does not match the source type.

    Args:
        values_dict (indigo.Dict): The current dialog values, containing 'editSource' and
            'editSourceFilter'.

    Returns:
        list: A list of state/value identifier strings or placeholder tuples.
    """
    result = None
    if values_dict['editSource'] != '':
        try:
            # User has selected an Indigo device element and then set the filter to Variables only.
            if int(values_dict['editSource']) in indigo.devices \
                    and values_dict['editSourceFilter'] == "V":
                result = [('None', 'Please select a data source first')]

            # User has selected an Indigo device element and the filter is set to Devices only or Show All.
            elif int(values_dict['editSource']) in indigo.devices \
                    and values_dict['editSourceFilter'] != "V":
                dev = indigo.devices[int(values_dict['editSource'])]
                result = [x for x in dev.states if ".ui" not in x]

            elif int(values_dict['editSource']) in indigo.variables \
                    and values_dict['editSourceFilter'] != "D":
                result = [('value', 'value')]

            elif int(values_dict['editSource']) in indigo.variables \
                    and values_dict['editSourceFilter'] == "D":
                result = [('None', 'Please select a data source first')]

        except ValueError:
            result = [('None', 'Please select a data source first')]

    else:
        result = [('None', 'Please select a data source first')]

    return result


# =============================================================================
def generatorPrecisionList() -> list:
    """Return a list of numeric display precision options for dropdown menus.

    Returns:
        list: A list of (value, label) tuples for 0-3 decimal place precision options.
    """
    return [("0", "0 (#)*"),
            ("1", "1 (#.#)"),
            ("2", "2 (#.##)"),
            ("3", "3 (#.###)"),
            ]


# =============================================================================
def generatorLineStyleDefaultNoneList() -> list:
    """Return a list of matplotlib line style options with 'None' as the default.

    Returns:
        list: A list of (value, label) tuples for matplotlib line styles.
    """
    return [
        ("--", "Dashed"),
        (":", "Dotted"),
        ("-.", "Dot Dash"),
        ("-", "Solid"),
        ("-1", "%%separator%%"),
        ("None", "None*"),
    ]


# =============================================================================
def generatorLineStyleDefaultSolidList() -> list:
    """Return a list of matplotlib line style options with 'Solid' as the default.

    Returns:
        list: A list of (value, label) tuples for matplotlib line styles.
    """
    return [
        ("--", "Dashed"),
        (":", "Dotted"),
        ("-.", "Dot Dash"),
        ("-", "Solid*"),
        ("-1", "%%separator%%"),
        ("None", "None"),
    ]


# =============================================================================
def generatorMarkerList() -> list:
    """Return a list of matplotlib marker style options for dropdown menus.

    Returns:
        list: A list of (value, label) tuples for matplotlib marker styles.
    """
    return [
        ("o", "Circle"),
        ("D", "Diamond"),
        ("d", "Diamond(Thin)"),
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
        ("x", "X"),
        ("-1", "%%separator%%"),
        ("None", "None*")
    ]


# =============================================================================
def get_axis_list() -> list:
    """Return a list of common Python date format strings for X-axis label dropdown menus.

    Generates live examples using the current date and time to show the user how each format will
    appear. Does not include all possible Python strftime specifiers.

    Returns:
        list: A list of (format_string, example_label) tuples.
    """
    now = dt.datetime.now()

    return [
        ("None", "None"),
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
        ("%b %y", dt.datetime.strftime(now, "%b %y") + ' (month year)'),
        ("%y %b", dt.datetime.strftime(now, "%y %b") + ' (year month)'),
        ("%b %d %Y", dt.datetime.strftime(now, "%b %d %Y") + ' (full date)'),
        ("%Y %b %d", dt.datetime.strftime(now, "%Y %b %d") + ' (full date)')
    ]


# =============================================================================
def get_battery_device_list() -> list:
    """Return a list of all Indigo devices that report a battery level.

    Filters all Indigo devices to those with a non-None batteryLevel property. If no
    battery-powered devices are found, returns a single placeholder tuple.

    Returns:
        list: A list of (device_id, device_name) tuples for battery-powered devices.
    """
    batt_list = [(dev.id, dev.name) for dev in indigo.devices.iter() if dev.batteryLevel is not None]

    if len(batt_list) == 0:
        batt_list = [(-1, 'No battery devices detected.'), ]

    return batt_list


# =============================================================================
def getFileList(prefs: indigo.Dict) -> list:
    """Return a sorted list of CSV files from the configured data path for dropdown menus.

    Scans the dataPath folder for '*.csv' files and returns a sorted list of (filename,
    display_name) tuples. Appends a separator and a 'None' option at the end of the list.

    Args:
        prefs (indigo.Dict): The plugin preferences dictionary, containing 'dataPath'.

    Returns:
        list: A sorted list of (filename, display_name) tuples plus a 'None' entry.
    """
    file_name_list_menu = []
    default_path = f"{indigo.server.getLogsFolderPath()}/com.fogbert.indigoplugin.matplotlib/"
    source_path = prefs.get('dataPath', default_path)

    try:
        for file_name in glob.glob(f"{source_path}*.csv"):
            final_filename = os.path.basename(file_name)
            file_name_list_menu.append((final_filename, final_filename[:-4]))

        # Sort the file list (case-insensitive sort)
        file_name_list_menu = sorted(file_name_list_menu, key=lambda s: s[0].lower())

        # Add 'None' as an option, and show it first in list
        file_name_list_menu = file_name_list_menu + [("-5", "%%separator%%"), ("None", "None")]

    except IOError as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error("Error generating file list: %s. See plugin log for more information.", sub_error)

    return file_name_list_menu


# =============================================================================
def getFontList() -> list:
    """Return a sorted list of font names visible to matplotlib for dropdown menus.

    These are the fonts that matplotlib can discover, not necessarily all fonts installed on the
    system. Falls back to the FONT_MENU constant list if matplotlib cannot find any fonts.

    Returns:
        list: A sorted list of font name strings.
    """
    font_menu = []

    try:
        for font in mfont.findSystemFonts(fontpaths=None, fontext='ttf'):
            font_name = os.path.splitext(os.path.basename(font))[0]
            if font_name not in font_menu:
                font_menu.append(font_name)

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "Error building font list. Returning generic list. %s. See plugin log for more information.",
            sub_error
        )

        font_menu = FONT_MENU

    return sorted(font_menu)


# =============================================================================
def getRefreshList() -> list:
    """Return a list of chart devices for the 'Redraw Charts Now...' menu dropdown.

    Builds a menu list starting with 'All Charts' and 'Skip Manual Charts' options, then appends
    each enabled plugin chart device.

    Returns:
        list: A list of (id, label) tuples for the refresh menu.
    """
    menu = [('all', 'All Charts'), ('auto', 'Skip Manual Charts'), ('-1', '%%separator%%')]

    _ = [menu.append((dev.id, dev.name)) for dev in indigo.devices.iter(filter="self") if dev.pluginProps['isChart']]

    return menu


# =============================================================================
def getForecastSource() -> list:
    """Return a sorted list of compatible weather forecast source devices.

    Iterates over Fantastic Weather and WUnderground plugin devices and returns those with
    supported forecast device type IDs. Intended to be expanded to support additional weather
    plugins in the future.

    Returns:
        list: A case-insensitive sorted list of (device_id, device_name) tuples.
    """
    forecast_source_menu = []

    # We accept both WUnderground (legacy) and Fantastic Weather devices. We have to construct these one at a time.
    # Note the typo in the bundle identifier is correct.
    try:
        for dev in indigo.devices.iter("com.fogbert.indigoplugin.fantasticwWeather"):
            if dev.deviceTypeId in ('Daily', 'Hourly'):
                forecast_source_menu.append((dev.id, dev.name))

        for dev in indigo.devices.iter("com.fogbert.indigoplugin.wunderground"):
            if dev.deviceTypeId in ('wundergroundTenDay', 'wundergroundHourly'):
                forecast_source_menu.append((dev.id, dev.name))

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "Error getting list of forecast devices: %s. See plugin log for more information.", sub_error
        )

    my_logger.threaddebug(
        "Forecast device list generated successfully: %s", forecast_source_menu
    )
    my_logger.threaddebug("forecast_source_menu: %s", forecast_source_menu)

    return sorted(forecast_source_menu, key=lambda s: s[1].lower())
