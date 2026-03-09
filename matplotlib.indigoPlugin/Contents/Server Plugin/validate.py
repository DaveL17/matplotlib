# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Validation code that's repeated for multiple object instances

TODO: move other validation code here.
"""
import re
import logging
from typing import Tuple

import indigo  # noqa

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the validate module (no-op placeholder)."""

# ==============================================================================
# ============================= Plugin Validation ==============================
# ==============================================================================


# =============================== Chart Colors ================================+
def chart_colors(values_dict: indigo.Dict) -> None:
    """Inspect color controls and reset any invalid hex values to their defaults.

    Checks each tracked color preference against a valid hexadecimal pattern (A-F, 0-9). If a value fails
    validation, it is replaced with the corresponding default color and a warning is logged.

    Args:
        values_dict (indigo.Dict): The plugin preferences dictionary containing color fields to validate.
    """
    # TODO: check to see whether this dict is up to date.
    # TODO: update 2024-10-23 - this may need to be refactored because color controls have been moved to the theme
    #       manager.
    color_dict = {
        'fontColorAnnotation': "FF FF FF", 'fontColor': "FF FF FF", 'backgroundColor': "00 00 00",
        'faceColor': "00 00 00", 'gridColor': "88 88 88", 'spineColor': "88 88 88", 'tickColor': "88 88 88",
    }

    for item in color_dict:
        if re.search(r"^[0-9A-Fa-f]+$", values_dict[item].replace(" ", "")) is None:
            values_dict[item] = color_dict[item]
            my_logger.warning("Invalid color code found in plugin preferences [%s], resetting to default." % item)

    my_logger.debug("Plugin config: chart colors validated.")


# ============================= Chart Dimensions ==============================
def chart_dimensions(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate plugin chart dimension preferences.

    Checks that each chart dimension property is a real number greater than 75 pixels. Removes surrounding whitespace
    from the values before checking. Populates error_msg_dict with an appropriate message for each failing field.

    Args:
        values_dict (indigo.Dict): The plugin preferences dictionary containing chart dimension fields.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    for dimension_prop in (
            'rectChartHeight',
            'rectChartWidth',
            'rectChartWideHeight',
            'rectChartWideWidth',
            'sqChartSize'
    ):

        # Remove any spaces
        try:
            values_dict[dimension_prop] = values_dict[dimension_prop].replace(" ", "")
        except AttributeError:
            ...

        try:
            if float(values_dict[dimension_prop]) < 75:
                error_msg_dict[dimension_prop] = "The dimension value must be greater than 75 pixels."
        except ValueError:
            error_msg_dict[dimension_prop] = "The dimension value must be a real number."

    my_logger.debug("Plugin config: Chart dimensions validated.")
    return values_dict, error_msg_dict


# ============================= Chart Resolution ==============================
# Note that chart resolution includes a warning feature that will pass the value after the warning is cleared.
def chart_resolution(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate the chart resolution (DPI) preference.

    Ensures the chartResolution field is not null or blank. If the DPI warning flag is set and the value is below 80,
    clears the flag and reports a warning. Includes a warning feature that passes the value after the warning is
    cleared.

    Args:
        values_dict (indigo.Dict): The plugin preferences dictionary containing the chartResolution field.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    try:
        # If value is null, a null string, or all whitespace.
        if not values_dict['chartResolution'] or \
                values_dict['chartResolution'] == "" or \
                str(values_dict['chartResolution']).isspace():
            values_dict['chartResolution'] = "100"
            my_logger.warning("No resolution value entered. Resetting resolution to 100 DPI.")

        # If warning flag and the value is potentially too small.
        elif values_dict['dpiWarningFlag'] and 0 < int(values_dict['chartResolution']) < 80:
            values_dict['dpiWarningFlag'] = False
            error_msg_dict['dpiWarningFlag'] = "A value of 80 or more is recommended for best results."

    except ValueError:
        error_msg_dict['chartResolution'] = "The chart resolution value must be greater than 0."

    my_logger.debug("Plugin config: Chart resolution validated.")
    return values_dict, error_msg_dict


# ================================ Data Paths ==================================
def data_paths(values_dict: indigo.Dict, error_dict: indigo.Dict) -> dict:
    """Ensure chart and data path values end with a forward slash.

    Validates that the chartPath and dataPath fields end with a '/' character. Sets an error message for any path
    that does not conform.

    Args:
        values_dict (indigo.Dict): The plugin preferences dictionary containing path fields.
        error_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        dict: The error_dict after validation, possibly containing path-related errors.
    """
    for path_prop in ('chartPath', 'dataPath'):
        try:
            if not values_dict[path_prop].endswith('/'):
                error_dict[path_prop] = "The path must end with a forward slash '/'."

        except AttributeError:
            error_dict[path_prop] = "The path must end with a forward slash '/'."

    my_logger.debug("Plugin config: Data paths validated.")
    return error_dict


# ================================ Line Weight =================================
# Line weight is a hidden prop in PluginConfig.xml and may no longer be needed.  fixme
def line_weight(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate the global line weight preference.

    Ensures the lineWeight field is a real number greater than zero. This is a hidden prop in PluginConfig.xml and
    may no longer be needed.

    Args:
        values_dict (indigo.Dict): The plugin preferences dictionary containing the lineWeight field.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    try:
        if float(values_dict['lineWeight']) <= 0:
            error_msg_dict['lineWeight'] = "The line weight value must be greater than zero."
    except ValueError:
        error_msg_dict['lineWeight'] = "The line weight value must be a real number."

    return values_dict, error_msg_dict


# ==============================================================================
# ============================= Device Validation ==============================
# ==============================================================================

# =============================== Custom Ticks =================================
def custom_ticks(values_dict: indigo.Dict, error_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate custom Y-axis tick locations and labels.

    Ensures all custom tick location values are numeric, that tick locations and labels contain the same number of
    items, and that all tick locations fall within the configured Y-axis bounds (if bounds are set).

    Args:
        values_dict (indigo.Dict): The device configuration dictionary containing customTicksY,
            customTicksLabelY, yAxisMin, and yAxisMax fields.
        error_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_dict) after validation.
    """

    my_ticks = values_dict['customTicksY'].split(',')  # Make a list from a string.
    my_tick_labels = values_dict['customTicksLabelY'].split(',')  # Make a list from a string.
    y_min = values_dict['yAxisMin']  # Custom Y min.
    y_max = values_dict['yAxisMax']  # Custom Y max.

    if not my_ticks == [''] or not my_tick_labels == ['']:
        # Ensure custom tick locations are numeric.
        try:
            my_ticks = [float(_) for _ in my_ticks]
        except ValueError:
            error_dict['customTicksY'] = "Custom tick locations must be numeric values."
            values_dict['settingsGroup'] = "y"

        # Ensure custom tick locations and labels have the same number of items.
        if len(my_ticks) != len(my_tick_labels):
            error_dict['customTicksY'] = "Tick labels and tick locations must have the same number of items."
            error_dict['customTicksLabelY'] = "Tick labels and tick locations must have the same number of items."
            values_dict['settingsGroup'] = "y"

        # Ensure all custom Y tick locations are within bounds. User has elected to change at least one Y axis
        # boundary (if both upper and lower bounds are set to 'None', we move on).
        if y_min not in ('', 'None', 'none'):
            for tick in my_ticks:
                if not tick >= float(values_dict['yAxisMin']):
                    error_dict['customTicksY'] = (
                        "All custom tick locations must be within the boundaries of the Y axis."
                    )
                    values_dict['settingsGroup'] = "y"

        if y_max not in ('', 'None', 'none'):
            for tick in my_ticks:
                if not tick <= float(values_dict['yAxisMax']):
                    error_dict['customTicksY'] = (
                        "All custom tick locations must be within the boundaries of the Y axis."
                    )
                    values_dict['settingsGroup'] = "y"

    my_logger.debug("Custom ticks validated.")
    return values_dict, error_dict
