# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Validation code that's repeated for multiple object instances
"""
import ast
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
            my_logger.warning("Invalid color code found in plugin preferences [%s], resetting to default.", item)

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


# ================================ Area Chart ==================================
def area_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate area charting device configuration.

    Ensures at least one data source is selected and that each area group's line adjustment field
    contains only valid numeric operator characters. Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # There must be at least 1 source selected
    if values_dict['area1Source'] == 'None':
        error_msg_dict['area1Source'] = "You must select at least one data source."
        values_dict['settingsGroup'] = "1"

    # Iterate for each area group (1-8).
    for area in range(1, 9, 1):
        # Line adjustment values
        for char in values_dict[f'area{area}adjuster']:
            if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                error_msg_dict[f'area{area}adjuster'] = "Valid operators are +, -, *, /"
                values_dict['settingsGroup'] = str(area)

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    my_logger.debug("Area chart validated.")
    return values_dict, error_msg_dict


# ================================  Flow Bar  =================================
def bar_flow_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate flow bar charting device configuration.

    Ensures at least one data source is selected and that the bar width is a real number greater
    than zero. Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # Must select at least one source (bar 1)
    if values_dict['bar1Source'] == 'None':
        error_msg_dict['bar1Source'] = "You must select at least one data source."
        values_dict['barLabel1'] = True
        values_dict['settingsGroup'] = "1"

    try:
        # Bar width must be greater than 0. Will also trap strings.
        if float(values_dict['barWidth']) <= 0:
            raise ValueError
    except ValueError:
        error_msg_dict['barWidth'] = "You must enter a bar width greater than 0."
        values_dict['settingsGroup'] = "ch"

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    my_logger.debug("Flow bar chart validated.")
    return values_dict, error_msg_dict


# ================================  Stock Bar  ================================
def bar_stock_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate stock bar charting device configuration.

    Ensures at least one data source is selected, that the bar width is a real number greater than
    zero, and that each selected bar source resolves to a chartable (int, float, bool) device state
    or variable value. Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # Must select at least one source (bar 1)
    if values_dict['bar1Source'] == 'None':
        error_msg_dict['bar1Source'] = "You must select at least one data source."
        values_dict['settingsGroup'] = "1"

    try:
        # Bar width must be greater than 0. Will also trap strings.
        if float(values_dict['barWidth']) <= 0:
            raise ValueError
    except ValueError:
        error_msg_dict['barWidth'] = "You must enter a bar width greater than 0."
        values_dict['settingsGroup'] = "ch"

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    # Test the selected values to ensure that they can be charted (int, float, bool)
    for source in ['bar1Value', 'bar2Value', 'bar3Value', 'bar4Value', 'bar5Value']:

        # Pull the number out of the source key
        n = re.search('[0-9]', source)

        # Get the id of the bar source
        if values_dict[f'bar{n.group(0)}Source'] != "None":
            source_id = int(values_dict[f'bar{n.group(0)}Source'])

            # By definition, it will either be a device ID or a variable ID.
            if source_id in indigo.devices:

                # Get the selected device state value
                val = indigo.devices[source_id].states[values_dict[source]]
                if not isinstance(val, (int, float, bool)):
                    error_msg_dict[source] = "The selected device state can not be charted due to its value."

            else:
                val = indigo.variables[source_id].value
                try:
                    float(val)
                except ValueError:
                    if val.lower() not in ['true', 'false']:
                        error_msg_dict[source] = "The selected variable can not be charted due to its value."
                        values_dict['settingsGroup'] = str(n.group(0))

    my_logger.debug("Stock bar chart validated.")
    return values_dict, error_msg_dict


# ==========================  Stock Horizontal Bar  ===========================
def bar_stock_horizontal_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate horizontal stock bar charting device configuration.

    Ensures at least one data source is selected, that the bar width is a real number greater than
    zero, and that each selected bar source resolves to a chartable (int, float, bool) device state
    or variable value. Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # Must select at least one source (bar 1)
    if values_dict['bar1Source'] == 'None':
        error_msg_dict['bar1Source'] = "You must select at least one data source."
        values_dict['settingsGroup'] = "1"

    try:
        # Bar width must be greater than 0. Will also trap strings.
        if float(values_dict['barWidth']) <= 0:
            raise ValueError
    except ValueError:
        error_msg_dict['barWidth'] = "You must enter a bar width greater than 0."
        values_dict['settingsGroup'] = "ch"

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    # Test the selected values to ensure that they can be charted (int, float, bool)
    for source in ['bar1Value', 'bar2Value', 'bar3Value', 'bar4Value', 'bar5Value']:

        # Pull the number out of the source key
        n = re.search('[0-9]', source)

        # Get the id of the bar source
        if values_dict[f'bar{n.group(0)}Source'] != "None":
            source_id = int(values_dict[f'bar{n.group(0)}Source'])

            # By definition, it will either be a device ID or a variable ID.
            if source_id in indigo.devices:

                # Get the selected device state value
                val = indigo.devices[source_id].states[values_dict[source]]
                if not isinstance(val, (int, float, bool)):
                    error_msg_dict[source] = "The selected device state can not be charted due to its value."
                    values_dict['settingsGroup'] = n.group(0)

            else:
                val = indigo.variables[source_id].value
                try:
                    float(val)
                except ValueError:
                    if val.lower() not in ['true', 'false']:
                        error_msg_dict[source] = "The selected variable can not be charted due to its value."
                        values_dict['settingsGroup'] = f"{n.group(0)}"

    my_logger.debug("Horizontal stock bar chart validated.")
    return values_dict, error_msg_dict


# =========================== Battery Health Chart ============================
def battery_health_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate battery health charting device configuration.

    Ensures the caution and warning alert levels are real numbers between 0 and 100.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    for prop in ('cautionLevel', 'warningLevel'):
        try:
            # Bar width must be greater than 0. Will also trap strings.
            if not 0 <= float(values_dict[prop]) <= 100:
                raise ValueError
        except ValueError:
            error_msg_dict[prop] = "Alert levels must between 0 and 100 (integer)."
            values_dict['settingsGroup'] = "dsp"

    my_logger.debug("Battery health chart validated.")
    return values_dict, error_msg_dict


# ================================ CSV Engine =================================
def csv_engine(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate CSV engine device configuration.

    Ensures the number of observations to keep, duration to keep, and refresh interval are valid
    numeric values, and that at least one CSV data source has been defined.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # ========================== Number of Observations ===========================
    try:
        # Must be 1 or greater
        if int(values_dict['numLinesToKeep']) < 1:
            raise ValueError
    except ValueError:
        error_msg_dict['numLinesToKeep'] = "The observation value must be a whole number greater than zero."

    # ================================= Duration ==================================
    try:
        # Must be zero or greater
        if float(values_dict['numLinesToKeepTime']) < 0:
            raise ValueError
    except ValueError:
        error_msg_dict['numLinesToKeepTime'] = "The duration value must be greater than zero."

    # ============================= Refresh Interval ==============================
    try:
        # Must be zero or greater
        if int(values_dict['refreshInterval']) < 0:
            raise ValueError
    except ValueError:
        error_msg_dict['refreshInterval'] = "The refresh interval must be a whole number greater than zero."

    # =============================== Data Sources ================================
    try:
        sources = ast.literal_eval(values_dict['columnDict'])

        # columnDict may contain a place-holder dict with one entry, so we test for that.
        if len(sources) < 2:
            # If columnDict has no keys, we know that won't work either.
            if len(sources) == 0:
                raise ValueError

            for key in sources:
                if sources[key] == ('None', 'None', 'None'):
                    raise ValueError

    except ValueError:
        error_msg_dict['addSource'] = "You must create at least one CSV data source."

    my_logger.debug("CSV engine validated.")
    return values_dict, error_msg_dict


# ================================ Line Chart =================================
def line_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate line charting device configuration.

    Ensures at least one data source is selected, that each line group's adjustment field contains
    only valid numeric operator characters, and that fill is not enabled for the steps line style.
    Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # There must be at least 1 source selected
    if values_dict['line1Source'] == 'None':
        error_msg_dict['line1Source'] = "You must select at least one data source."
        values_dict['settingsGroup'] = "1"

    # Iterate for each line group (1-6).
    for area in range(1, 7, 1):

        # Line adjustment values
        for char in values_dict[f'line{area}adjuster']:
            if char not in ' +-/*.0123456789':  # allowable numeric specifiers
                error_msg_dict[f'line{area}adjuster'] = "Valid operators are +, -, *, /"
                values_dict['settingsGroup'] = str(area)

        # Fill is illegal for the steps line type
        if values_dict[f'line{area}Style'] == 'steps' and values_dict[f'line{area}Fill']:
            error_msg_dict[f'line{area}Fill'] = ("Fill is not supported for the Steps "
                                                 "line type.")
            values_dict['settingsGroup'] = str(area)

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    my_logger.debug("Line chart validated.")
    return values_dict, error_msg_dict


# ============================== Multiline Text ===============================
def multiline_text(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate multiline text device configuration.

    Ensures a data source is selected, and that the number of characters, figure width/height, and
    font size are valid positive numeric values.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    for prop in ('thing', 'thingState'):
        # A data source must be selected
        if not values_dict[prop] or values_dict[prop] == 'None':
            error_msg_dict[prop] = "You must select a data source."
            values_dict['settingsGroup'] = "src"

    try:
        if int(values_dict['numberOfCharacters']) < 1:
            raise ValueError
    except ValueError:
        error_msg_dict['numberOfCharacters'] = "The number of characters must be greater than zero."
        values_dict['settingsGroup'] = "dsp"

    # Figure width and height.
    for prop in ('figureWidth', 'figureHeight'):
        try:
            if int(values_dict[prop]) < 1:
                raise ValueError
        except ValueError:
            error_msg_dict[prop] = (
                "The figure width and height must be positive whole numbers greater than zero (pixels)."
            )
            values_dict['settingsGroup'] = "dsp"

    # Font size
    try:
        if float(values_dict['multilineFontSize']) < 0:
            raise ValueError
    except ValueError:
        error_msg_dict['multilineFontSize'] = "The font size must be a positive real number greater than zero."
        values_dict['settingsGroup'] = "dsp"

    my_logger.debug("Multiline text validated.")
    return values_dict, error_msg_dict


# ================================ Polar Chart ================================
def polar_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate polar charting device configuration.

    Ensures a direction (theta) source and magnitude (radii) source are selected, and that the
    number of observations is a whole number of at least 1.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    if not values_dict['thetaValue']:
        error_msg_dict['thetaValue'] = "You must select a direction source."
        values_dict['settingsGroup'] = "src"

    if not values_dict['radiiValue']:
        error_msg_dict['radiiValue'] = "You must select a magnitude source."
        values_dict['settingsGroup'] = "src"

    # Number of observations
    try:
        if int(values_dict['numObs']) < 1:
            error_msg_dict['numObs'] = "You must specify at least 1 observation (must be a whole number)."
            values_dict['settingsGroup'] = "dsp"
    except ValueError:
        error_msg_dict['numObs'] = "You must specify at least 1 observation (must be a whole number integer)."
        values_dict['settingsGroup'] = "dsp"

    my_logger.debug("Polar chart validated.")
    return values_dict, error_msg_dict


# =============================== Scatter Chart ===============================
def scatter_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate scatter charting device configuration.

    Ensures at least one data source is selected. Also runs the shared custom tick validation.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    if not values_dict['group1Source']:
        error_msg_dict['group1Source'] = "You must select at least one data source."
        values_dict['settingsGroup'] = "1"

    values_dict, error_msg_dict = custom_ticks(values_dict, error_msg_dict)

    my_logger.debug("Scatter chart validated.")
    return values_dict, error_msg_dict


# =============================== Weather Chart ===============================
def weather_forecast_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate weather forecast charting device configuration.

    Ensures a weather forecast source device is selected.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    if not values_dict['forecastSourceDevice']:
        error_msg_dict['forecastSourceDevice'] = "You must select a weather forecast source device."
        values_dict['settingsGroup'] = "ch"

    my_logger.debug("Weather forecast chart validated.")
    return values_dict, error_msg_dict


# ========================== Composite Weather Chart ==========================
def composite_weather_chart(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate composite weather charting device configuration.

    Ensures a weather forecast source device is selected, that each plotted min/max bound is empty,
    'None', or a real number, and that at least two plot elements are selected.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    if not values_dict['forecastSourceDevice']:
        error_msg_dict['forecastSourceDevice'] = "You must select a weather forecast source device."
        values_dict['settingsGroup'] = "ch"

    for _ in (
        'pressure_min',
        'pressure_max',
        'temperature_min',
        'temperature_max',
        'humidity_min',
        'humidity_max',
        'precipitation_min',
        'precipitation_max',
        'wind_min',
        'wind_max'
    ):
        try:
            float(values_dict[_])

        except ValueError:
            if values_dict[_] in ("", "None"):
                ...
            else:
                error_msg_dict[_] = "The value must be empty, 'None', or a numeric value."
                values_dict['settingsGroup'] = "y1"

    if len(values_dict['component_list']) < 2:
        error_msg_dict['component_list'] = "You must select at least two plot elements."
        values_dict['settingsGroup'] = "fe"

    my_logger.debug("Composite weather chart validated.")
    return values_dict, error_msg_dict


# ========================== Chart Custom Dimensions ==========================
def chart_custom_dimensions(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate custom chart dimension fields shared across all graphical chart types.

    Checks that any of the customSizeHeight, customSizeWidth, and customSizePolar fields present in
    values_dict conform to a real number greater than 75 pixels.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    for custom_dimension_prop in ('customSizeHeight', 'customSizeWidth', 'customSizePolar'):
        try:
            if custom_dimension_prop in values_dict \
                    and values_dict[custom_dimension_prop] != 'None' \
                    and float(values_dict[custom_dimension_prop]) < 75:
                error_msg_dict[custom_dimension_prop] = "The chart dimension value must be greater than 75 pixels."
        except ValueError:
            error_msg_dict[custom_dimension_prop] = (
                "The chart dimension value must be a real number greater than 75 pixels."
            )

    my_logger.debug("Chart custom dimensions validated.")
    return values_dict, error_msg_dict


# ================================ Axis Limits ================================
def axis_limits(values_dict: indigo.Dict, error_msg_dict: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Validate Y axis limit fields shared across all graphical chart types.

    Checks that any of the yAxisMax, yAxisMin, y2AxisMax, and y2AxisMin fields present in
    values_dict are not empty and match an accepted format (a real number, or 'None'). Also ensures
    that the Y axis min is less than the Y axis max when both are specified.

    Args:
        values_dict (indigo.Dict): The device configuration values.
        error_msg_dict (indigo.Dict): The error message dictionary to populate with validation failures.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict) after validation.
    """
    # Check to see that each axis limit matches one of the accepted formats
    for limit_prop in ('yAxisMax', 'yAxisMin', 'y2AxisMax', 'y2AxisMin'):

        # We only do these if the device has these props.
        if limit_prop in values_dict:

            # Y-axis limits can not be empty.
            if values_dict[limit_prop] == '' or values_dict[limit_prop].isspace():
                my_logger.warning("Limits can not be empty. Setting empty limits to 'None.'")
                values_dict[limit_prop] = "None"

            # Y-axis limits must be a value that can float.
            try:
                if values_dict[limit_prop] not in ('None', '0'):
                    float(values_dict[limit_prop])
            except ValueError:
                values_dict[limit_prop] = 'None'
                error_msg_dict[limit_prop] = "The axis limit must be a real number or None."

    # Y-axis limits min must be less than max
    try:
        y_min = float(values_dict.get('yAxisMin', "None"))
    except ValueError:
        y_min = None

    try:
        y_max = float(values_dict.get('yAxisMax', "None"))
    except ValueError:
        y_max = None

    if isinstance(y_min, float) and isinstance(y_max, float):
        if not y_max > y_min:
            error_msg_dict['yAxisMin'] = "Min must be less than max if both are specified."
            error_msg_dict['yAxisMax'] = "Max must be greater than min if both are specified."

    my_logger.debug("Axis limits validated.")
    return values_dict, error_msg_dict
