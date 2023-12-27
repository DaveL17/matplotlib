# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Validation code that's repeated for multiple object instances

TODO: move other validation code here.
"""
import re
import logging

try:
    import indigo  # noqa
except ImportError:
    pass

my_logger = logging.getLogger("Plugin")


def __init__():
    ...

# ==============================================================================
# ============================= Plugin Validation ==============================
# ==============================================================================


# =============================== Chart Colors ================================+
def chart_colors(values_dict: indigo.Dict):
    """
    Inspects various color controls and sets them to default when the value is not valid hex (A-F, 0-9).

    :param indigo.Dict values_dict:
    """
    # TODO: check to see whether this dict is up to date.
    color_dict = {
        'fontColorAnnotation': "FF FF FF", 'fontColor': "FF FF FF", 'backgroundColor': "00 00 00",
        'faceColor': "00 00 00", 'gridColor': "88 88 88", 'spineColor': "88 88 88", 'tickColor': "88 88 88",
    }

    for item in color_dict:
        if re.search(r"^[0-9A-Fa-f]+$", values_dict[item].replace(" ", "")) is None:
            values_dict[item] = color_dict[item]
            my_logger.warning(f"Invalid color code found in plugin preferences [{item}], resetting to default.")

    my_logger.debug("Plugin config: chart colors validated.")


# ============================= Chart Dimensions ==============================
def chart_dimensions(values_dict: indigo.Dict, error_msg_dict: indigo.Dict):
    """

    :param indigo.Dict values_dict:
    :param indigo.Dict error_msg_dict:
    :return:
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
def chart_resolution(values_dict: indigo.Dict, error_msg_dict: indigo.Dict):
    """

    :param values_dict:
    :param error_msg_dict:
    :return:
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
def data_paths(values_dict: indigo.Dict, error_dict: indigo.Dict):
    """
    Ensure the data path value is valid.

    :param indigo.Dict values_dict:
    :param indigo.Dict error_dict:
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
def line_weight(values_dict: indigo.Dict, error_msg_dict: indigo.Dict):
    """

    :param indigo.Dict values_dict:
    :param indigo.Dict error_msg_dict:
    :return:
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
def custom_ticks(values_dict: indigo.Dict, error_dict: indigo.Dict):
    """
    Ensure all custom tick locations are numeric, within bounds, and of the same length.

    :param indigo.Dict values_dict:
    :param indigo.Dict error_dict:
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
