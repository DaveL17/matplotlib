# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Plugin startup/maintenance audits.

Covers device property reconciliation against the current XML config, recursive color-string
normalization, save-path validation, the themes JSON file's existence, and orphaned stylesheet
pruning. Most of these run once at plugin startup(); audit_dict_color() also runs per chart
refresh from charts_refresh().
"""
import glob
import json
import logging
import os
import re
import traceback
import xml.etree.ElementTree as eTree
from typing import Any, Callable

import indigo  # noqa

import color_utils
import log_utils

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the audits module (no-op placeholder)."""


# =============================================================================
def audit_device_props(get_device_config_ui_xml: Callable) -> bool:
    """Audit device properties to ensure they match the current plugin configuration.

    Compares the current device config XML layout to each device's pluginProps. Fields present in
    the XML but missing from the device are added (checkboxes coerced to bool based on
    defaultValue, or False if unspecified). Keys present in pluginProps but absent from the XML
    are removed. Should not be called from device_start_comm() to avoid an infinite loop. Should
    be called from the plugin's startup() method instead.

    Args:
        get_device_config_ui_xml (Callable): A callable matching
            indigo.PluginBase.getDeviceConfigUiXml(type_id, dev_id).

    Returns:
        bool: True if the audit completed without errors, False on exception.
    """
    my_logger.debug("Updating device properties to match current plugin version.")

    try:
        # Iterate through the plugin's devices
        for dev in indigo.devices.iter(filter="self"):

            # =========================== Match Props to Config ===========================
            # For config props that are not in the device's current definition.

            device_xml = get_device_config_ui_xml(dev.deviceTypeId, dev.id)
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
                    # attribute 'defaultValue is not required
                    default_value = attributes.get('defaultValue', "")

                    # Save a list of field IDs for later use.
                    fields.append(field_id)

                    # If the XML field is not in the device's current props dict
                    if field_id not in props:

                        # Coerce checkbox default values to bool. Everything that comes in from the XML is a
                        # string; everything that's not converted will be sent as a string.
                        if field_type.lower() == 'checkbox':
                            if default_value.lower() == 'true':
                                default_value = True
                            else:
                                # will be False if no defaultValue specified.
                                default_value = False

                        props[field_id] = default_value
                        my_logger.debug(
                            "[%s] missing prop [%s] will be added. Value set [%s]", dev.name, field_id, default_value
                        )

            # =========================== Match Config to Props ===========================
            # For props that have been removed but are still in the device definition.

            for key in list(props):
                if key not in fields:

                    my_logger.debug("[%s] prop obsolete prop [%s] will be removed", dev.name, key)
                    del props[key]

            # Now that we're done, let's save the updated dict back to the device.
            dev.replacePluginPropsOnServer(props)

        return True

    except Exception as sub_error:
        my_logger.warning("Audit device props error: %s", sub_error)

        return False


# =============================================================================
def audit_dict_color(_dict_: dict) -> dict:
    """Convert all color strings in a dict (and nested dicts) to '#RRGGBB' format.

    Recursively traverses the given dictionary and replaces any string values that match the
    'XX XX XX' color pattern with the normalized '#XXXXXX' format required by matplotlib.

    Args:
        _dict_ (dict): The dictionary to process for color string normalization.

    Returns:
        dict: A new dictionary with all matching color strings converted.
    """
    pattern = r"[0-9A-Fa-f]{2} [0-9A-Fa-f]{2} [0-9A-Fa-f]{2}"

    def process_value(value: Any) -> Any:
        if isinstance(value, str):
            return color_utils.fix_rgb(color=value) if re.search(pattern, value) else value
        elif isinstance(value, dict):
            return {k: process_value(v) for k, v in value.items()}
        return value

    return {k: process_value(v) for k, v in _dict_.items()}


# =============================================================================
def audit_save_paths(prefs: indigo.Dict, vers_str_to_tuple: Callable) -> None:
    """Audit and validate the plugin's CSV and chart save path configurations.

    Attempts to access the configured paths for CSV and chart file storage. Creates missing
    directories and checks write permissions, logging warnings for any inaccessible paths. Also
    compares the current save path against the expected path for the installed Indigo version and
    warns if they differ.

    Args:
        prefs (indigo.Dict): The plugin preferences dictionary, containing 'dataPath' and
            'chartPath'.
        vers_str_to_tuple (Callable): A callable matching indigo.PluginBase.versStrToTuple(str).
    """
    # ============================= Audit Save Paths ==============================
    # Test the current path settings to ensure that they are valid.
    path_list = (prefs['dataPath'], prefs['chartPath'])

    # If the target folders do not exist, create them.
    my_logger.debug("Auditing save paths.")
    for path_name in path_list:

        if not os.path.isdir(path_name):
            try:
                my_logger.warning("Target folder doesn't exist. Creating path:%s", path_name)
                os.makedirs(path_name)

            except (IOError, OSError):
                log_utils.log_traceback(traceback.format_exc())
                my_logger.critical(
                    "Target folder doesn't exist and the plugin is unable to create it. See plugin log for more "
                    "information."
                )

    # Test to ensure that each path is writeable.
    my_logger.debug("Auditing path IO.")
    for path_name in path_list:
        if os.access(path_name, os.W_OK):
            my_logger.debug("   Path OK: %s", path_name)
        else:
            my_logger.critical("   Plugin doesn't have the proper rights to write to the path: %s", path_name)

    # ================ Compare Save Path to Current Indigo Version ================
    indigo_ver = vers_str_to_tuple(indigo.server.version)[0]
    current_save_path = prefs['chartPath']

    if current_save_path.startswith('/Library/Application Support/Perceptive Automation/Indigo'):

        if indigo_ver <= 7:
            new_save_path = f"{indigo.server.getInstallFolderPath()}/IndigoWebServer/images/controls/"

            if new_save_path != current_save_path:
                my_logger.warning("Charts are being saved to: %s)", current_save_path)
                my_logger.warning("You may want to change the save path to: %s", new_save_path)

        elif indigo_ver == 2021:
            new_save_path = f"{indigo.server.getInstallFolderPath()}/Web Assets/images/controls/static/"

            if new_save_path != current_save_path:
                my_logger.warning("Charts are being saved to: %s)", current_save_path)
                my_logger.warning("You may want to change the save path to: %s", new_save_path)


# =============================================================================
def audit_themes_file() -> None:
    """Create the themes JSON repository file if it does not already exist.

    Checks for the presence of the plugin themes JSON file in the Indigo Preferences folder and
    creates an empty JSON object file if the file is not found.
    """
    full_path = (indigo.server.getInstallFolderPath() +
                 "/Preferences/Plugins/matplotlib plugin themes.json")
    if not os.path.isfile(full_path):
        with open(full_path, 'w', encoding='utf-8') as outfile:
            outfile.write(json.dumps({}, indent=4))


# =============================================================================
def audit_stylesheets() -> None:
    """Prune stylesheet files that no longer correspond to a plugin device.

    Compares stylesheet filenames against existing plugin device IDs and removes any orphaned
    files. Logs each pruned file at the WARNING level. Called once at plugin startup.
    """
    if not os.path.exists("Stylesheets/"):
        return

    valid_ids = {dev.id for dev in indigo.devices.iter(filter='self')}

    for filepath in glob.glob("Stylesheets/*_stylesheet"):
        basename = os.path.basename(filepath)
        stem     = basename[: -len("_stylesheet")]
        if not stem.isdigit():
            continue
        if int(stem) not in valid_ids:
            my_logger.warning("Pruning orphaned stylesheet: %s", basename)
            os.remove(filepath)
