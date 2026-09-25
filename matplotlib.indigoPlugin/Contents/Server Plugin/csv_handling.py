# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
CSV Engine device support.

Covers CSV file health/uniqueness audits, the per-device CSV data refresh pipeline, and the
CSV Engine device configuration dialog's add/edit/delete/list callbacks.
"""
import ast
import csv
import datetime as dt
import logging
import os
import shutil
import traceback
from typing import Callable, Tuple

import indigo  # noqa
from dateutil.parser import parse as date_parse

import log_utils

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the csv_handling module (no-op placeholder)."""


# =============================================================================
def audit_csv_health(prefs: indigo.Dict) -> None:
    """Create any missing CSV data files before the plugin begins normal operation.

    Iterates through all CSV Engine devices (enabled or disabled) and creates any missing CSV
    files in the configured data path. New files are initialized with a header row. Also creates
    the data directory if it does not yet exist.

    Args:
        prefs (indigo.Dict): The plugin preferences dictionary, containing 'dataPath'.
    """
    my_logger.debug("Auditing CSV health.")
    data_path = prefs['dataPath']

    for dev in indigo.devices.iter(filter='self'):
        if dev.deviceTypeId == 'csvEngine':
            column_dict = ast.literal_eval(dev.pluginProps['columnDict'])

            for thing in column_dict:
                full_path = data_path + column_dict[thing][0] + ".csv"

                # ============================= Create (if needed) ============================
                # If the appropriate CSV file doesn't exist, create it and write the header line.
                if not os.path.isdir(data_path):
                    try:
                        os.makedirs(data_path)
                        my_logger.warning("Target data folder doesn't exist. Creating it.")

                    except OSError:
                        log_utils.log_traceback(traceback.format_exc())
                        my_logger.critical(
                            "[%s] The plugin is unable to access the data storage location. See plugin log for "
                            "more information.", dev.name
                        )

                if not os.path.isfile(full_path):
                    my_logger.warning("CSV file doesn't exist. Creating a new one: %s", full_path)
                    with open(full_path, 'w', encoding='utf-8') as csv_file:
                        csv_file.write(f"Timestamp,{column_dict[thing][2]}\n")
                        csv_file.close()


# =============================================================================
def csv_check_unique() -> None:
    """Check CSV Engine devices for duplicate CSV filename references.

    Iterates through all CSV Engine devices and builds a mapping of CSV filenames to the devices
    that reference them. Logs a warning for any filename referenced by more than one CSV Engine
    device, as duplicate references can cause data integrity issues.
    """
    my_logger.debug("Checking CSV references.")
    titles = {}

    # Iterate through CSV Engine devices
    for dev in indigo.devices.iter(filter='self'):
        if dev.deviceTypeId == 'csvEngine':

            # Get the list of CSV file titles
            column_dict = ast.literal_eval(dev.pluginProps['columnDict'])

            # Build a dictionary where the file title is the key and the value is a list of devices that point to
            # that title for a source.
            for key in column_dict:
                title = column_dict[key][0]

                if title not in titles:
                    titles[title] = [dev.name]

                else:
                    titles[title].append(dev.name)

    # Iterate through the dict of titles
    for title_name in titles:
        if len(titles[title_name]) > 1:
            my_logger.warning(
                "Audit CSV data files: CSV filename [%s] referenced by more than one CSV Engine device: "
                "%s", title_name, titles[title_name]
            )


# =============================================================================
def csv_item_add(values_dict: indigo.Dict, dev_id: int, prefs: indigo.Dict) -> Tuple[indigo.Dict, indigo.Dict]:
    """Add a new CSV data source item to the CSV Engine device configuration.

    Called when the user clicks the 'Add Item' button in the CSV Engine config dialog. Validates
    that all required fields are populated, generates the next key, saves the new item to the
    columnDict, creates the CSV file if it does not exist, and resets the add form fields.

    Args:
        values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
        dev_id (int): The Indigo device ID.
        prefs (indigo.Dict): The plugin preferences dictionary, containing 'dataPath'.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict).
    """
    dev = indigo.devices[int(dev_id)]
    my_logger.threaddebug("[%s] csv item add values_dict: %s", dev.name, dict(values_dict))

    error_msg_dict = indigo.Dict()

    try:
        # Convert column_dict from a string to a literal dict
        column_dict = ast.literal_eval(values_dict['columnDict'])
        lister = [0]
        num_lister = []

        # ================================ Validation =================================
        # Add data item validation.  Will not add until all three conditions are met.
        if values_dict['addValue'] == "":
            error_msg_dict['addValue'] = "Please enter a title value for the CSV data element."

        if values_dict['addSource'] == "":
            error_msg_dict['addSource'] = "Please select a device or variable for the CSV data element."

        if values_dict['addState'] == "":
            error_msg_dict['addState'] = "Please select a value source for the CSV data element."

        # Create a list of existing keys with the 'k' lopped off
        _ = [lister.append(key.lstrip('k')) for key in sorted(column_dict)]

        # Change each value to an integer for evaluation
        _ = [num_lister.append(int(item)) for item in lister]

        # Generate the next key
        next_key = f'k{int(max(num_lister)) + 1}'

        # Save the tuple of properties
        column_dict[next_key] = values_dict['addValue'], values_dict['addSource'], values_dict['addState']

        # Remove any empty entries as they're not going to do any good anyway.
        new_dict = {}

        for key, value in column_dict.items():
            if value not in [("", "", ""), ('None', 'None', 'None')]:
                new_dict[key] = value
            else:
                my_logger.info("Pruning CSV Engine.")

        # Convert column_dict back to a string and prepare it for storage.
        values_dict['columnDict'] = str(new_dict)

    except AttributeError as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "[%s] Error adding CSV item: %s. See plugin log for more information.", dev.name, sub_error
        )

    # If the appropriate CSV file doesn't exist, create it and write the header line.
    file_name = values_dict['addValue']
    full_path = f"{prefs['dataPath']}{file_name}.csv"

    if not os.path.isfile(full_path):

        with open(full_path, 'w', encoding='utf-8') as outfile:
            outfile.write(f"{'Timestamp'},{file_name}\n")

    # Wipe the field values clean for the next element to be added.
    for key in ('addSourceFilter', 'editSourceFilter'):
        values_dict[key] = "A"

    for key in ('addValue', 'addSource', 'addState'):
        values_dict[key] = ""

    return values_dict, error_msg_dict


# =============================================================================
def csv_item_delete(values_dict: indigo.Dict, dev_id: int) -> dict:
    """Delete the selected CSV data source item from the CSV Engine configuration.

    Called when the user clicks the 'Delete Item' button in the CSV Engine config dialog. Removes
    the selected item from the columnDict and resets all edit form fields.

    Args:
        values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
        dev_id (int): The Indigo device ID.

    Returns:
        dict: The updated values_dict with the item removed and edit fields cleared.
    """
    dev = indigo.devices[int(dev_id)]
    my_logger.threaddebug("[%s] csv item delete values_dict: %s", dev.name, dict(values_dict))

    # Convert column_dict from a string to a literal dict.
    column_dict = ast.literal_eval(values_dict['columnDict'])

    try:
        values_dict["editKey"] = values_dict["csv_item_list"]
        del column_dict[values_dict['editKey']]

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "[%s] Error deleting CSV item: %s. See plugin log for more information.", dev.name, sub_error
        )

    values_dict['csv_item_list'] = ""
    values_dict['editKey']       = ""
    values_dict['editSource']    = ""
    values_dict['editState']     = ""
    values_dict['editValue']     = ""
    values_dict['previousKey']   = ""

    # Convert column_dict back to a string for storage.
    values_dict['columnDict']  = str(column_dict)

    return values_dict


# =============================================================================
def csv_item_list(values_dict: indigo.Dict, target_id: int) -> list:
    """Generate the sorted list of CSV item key/name pairs for the CSV Engine config dialog.

    Reads the columnDict from values_dict and returns a case-insensitive sorted list of
    (key, item_name) tuples for display in the CSV Engine item list control. Called when the
    dialog opens and whenever changes are made.

    Args:
        values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
        target_id (int): The Indigo device ID.

    Returns:
        list: A sorted list of (key, item_name) tuples.
    """
    dev = indigo.devices[int(target_id)]

    try:
        # Returning an empty dict seems to work and may solve the 'None' issue
        values_dict['columnDict'] = values_dict.get('columnDict', '{}')
        # Convert column_dict from a string to a literal dict.
        column_dict = ast.literal_eval(values_dict['columnDict'])
        prop_list   = [(key, value[0]) for key, value in column_dict.items()]

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "[%s] Error generating CSV item list: %s. See plugin log for more information.", dev.name, sub_error
        )
        prop_list = []

    # Return a list sorted by the value and not the key. Case-insensitive sort.
    result = sorted(prop_list, key=lambda tup: tup[1].lower())
    return result


# =============================================================================
def csv_item_update(values_dict: indigo.Dict, dev_id: int) -> Tuple[indigo.Dict, indigo.Dict]:
    """Update a CSV data source item in the CSV Engine device configuration.

    Called when the user clicks the 'Update Item' button in the CSV Engine config dialog.
    Validates the new key for uniqueness, updates the selected item in columnDict, and resets the
    edit form fields on success.

    Args:
        values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
        dev_id (int): The Indigo device ID.

    Returns:
        tuple: A two-element tuple of (values_dict, error_msg_dict).
    """
    dev = indigo.devices[dev_id]
    my_logger.threaddebug("[%s] csv item update values_dict: %s", dev.name, dict(values_dict))

    error_msg_dict = indigo.Dict()
    # Convert column_dict from a string to a literal dict.
    column_dict  = ast.literal_eval(values_dict['columnDict'])

    try:
        key = values_dict['editKey']
        previous_key = values_dict['previousKey']
        if key != previous_key:
            if key in column_dict:
                error_msg_dict['editKey'] = (
                    f"New key ({key}) already exists in the global properties, please use a different key value"
                )
                values_dict['editKey']   = previous_key
            else:
                del column_dict[previous_key]
                column_dict[key] = (
                    values_dict['editValue'],
                    values_dict['editSource'],
                    values_dict['editState']
                )
        else:
            column_dict[key] = (
                values_dict['editValue'],
                values_dict['editSource'],
                values_dict['editState']
            )
            values_dict['csv_item_list'] = ""
            values_dict['editKey']       = ""
            values_dict['editSource']    = ""
            values_dict['editState']     = ""
            values_dict['editValue']     = ""

        if len(error_msg_dict) == 0:
            values_dict['previousKey'] = key

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "[%s] Error updating CSV item: %s. See plugin log for more information.", dev.name, sub_error
        )

    # Remove any empty entries as they're not going to do any good anyway.
    new_dict = {}

    for key, value in column_dict.items():
        if value != ('', '', ''):
            new_dict[key] = value
    column_dict = new_dict

    # Convert column_dict back to a string for storage.
    values_dict['columnDict'] = f"{column_dict}"

    return values_dict, error_msg_dict


# =============================================================================
def csv_item_select(values_dict: indigo.Dict, dev_id: int) -> dict:
    """Populate CSV Engine edit controls when the user selects an item from the item list.

    Called when the user selects an item from the CSV Engine Item List dropdown. Reads the
    selected item's properties from columnDict and populates the edit key, source, state, and
    value controls, and sets the isColumnSelected flag.

    Args:
        values_dict (indigo.Dict): The current CSV Engine configuration dialog values.
        dev_id (int): The Indigo device ID.

    Returns:
        dict: The updated values_dict with edit controls populated.
    """
    dev = indigo.devices[int(dev_id)]
    my_logger.threaddebug("[%s] csv item select values_dict: %s", dev.name, dict(values_dict))

    try:
        column_dict                     = ast.literal_eval(values_dict['columnDict'])
        values_dict['editKey']          = values_dict['csv_item_list']
        values_dict['editSource']       = column_dict[values_dict['csv_item_list']][1]
        values_dict['editState']        = column_dict[values_dict['csv_item_list']][2]
        values_dict['editValue']        = column_dict[values_dict['csv_item_list']][0]
        values_dict['isColumnSelected'] = True
        values_dict['previousKey']      = values_dict['csv_item_list']

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.error(
            "[%s] There was an error establishing a connection with the item you  chose: %s. See plugin log for "
            "more information.", dev.name, sub_error
        )
    return values_dict


# =============================================================================
def csv_refresh(is_shutting_down: bool, log_dicts: Callable, prefs: indigo.Dict, sleep_fn: Callable) -> None:
    """Refresh data for all CSV custom devices whose refresh interval has elapsed.

    Manages CSV files through CSV Engine custom devices.

    Args:
        is_shutting_down (bool): The plugin's pluginIsShuttingDown flag; refresh is skipped if True.
        log_dicts (Callable): A callable (dev) -> None that logs the device's pluginProps dict
            under verbose logging, mirroring Plugin.__log_dicts().
        prefs (indigo.Dict): The plugin preferences dictionary, passed through to
            csv_refresh_process().
        sleep_fn (Callable): A callable matching indigo.PluginBase.sleep(), passed through to
            csv_refresh_process().
    """
    if not is_shutting_down:
        for dev in indigo.devices.iter("self"):
            if dev.deviceTypeId == 'csvEngine' and dev.enabled:
                refresh_interval = int(dev.pluginProps['refreshInterval'])

                try:
                    last_updated = date_parse(dev.states['csvLastUpdated'])
                except ValueError:
                    last_updated = date_parse('1970-01-01 00:00')

                diff = dt.datetime.now() - last_updated
                refresh_needed = diff > dt.timedelta(seconds=refresh_interval)

                if refresh_needed and refresh_interval != 0:
                    log_dicts(dev)
                    dev.updateStatesOnServer([{'key': 'onOffState', 'value': True, 'uiValue': 'Processing'}])

                    # {key: (Item Name, Source ID, Source State)}
                    csv_dict_str = dev.pluginProps['columnDict']

                    # Convert column_dict from a string to a literal dict.
                    csv_dict = ast.literal_eval(csv_dict_str)

                    my_logger.threaddebug("[%s] Refreshing CSV  Device: %s", dev.name, dict(csv_dict))
                    csv_refresh_process(dev=dev, csv_dict=csv_dict, prefs=prefs, sleep_fn=sleep_fn)


# =============================================================================
def csv_refresh_process(dev: indigo.Device, csv_dict: dict, prefs: indigo.Dict, sleep_fn: Callable) -> None:
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
        prefs (indigo.Dict): The plugin preferences dictionary, containing 'dataPath'.
        sleep_fn (Callable): A callable matching indigo.PluginBase.sleep(), used after creating a
            new CSV file to yield the plugin thread.
    """
    try:

        target_lines = int(dev.pluginProps.get('numLinesToKeep', '300'))
        delta        = dev.pluginProps.get('numLinesToKeepTime', '72')
        cycle_time   = dt.datetime.now()
        column_names = []
        data         = []

        # If delta isn't a valid float, set it to zero.
        try:
            delta = float(delta)
        except ValueError:
            delta = 0.0

        # Read through the dict and construct headers and data
        for value in sorted(csv_dict.values()):

            # Create a path variable that is based on the target folder and the CSV item name.
            full_path = f"{prefs['dataPath']}{value[0]}.csv"
            backup    = full_path.replace('.csv', ' copy.csv')

            # ============================= Create (if needed) ============================
            # If the appropriate CSV file doesn't exist, create it and write the header line.
            if not os.path.isdir(prefs['dataPath']):
                try:
                    os.makedirs(prefs['dataPath'])
                    my_logger.warning("Target data folder doesn't exist. Creating it.")

                except OSError:
                    my_logger.critical(
                        "[%s] Target data folder either doesn't exist or the plugin is unable to "
                        "access/create it.", dev.name
                    )

            if not os.path.isfile(full_path):
                try:
                    my_logger.debug("CSV doesn't exist. Creating: %s", full_path)
                    with open(full_path, 'w', encoding="utf-8") as csv_file:
                        csv_file.write(f"{'Timestamp'},{value[0]}\n")
                        csv_file.close()

                    sleep_fn(1)

                except IOError:
                    my_logger.critical(
                        "[%s] The plugin is unable to access the data storage location. See plugin log "
                        "for more information.", dev.name
                    )

            # =============================== Create Backup ===============================
            # Make a backup of the CSV file in case something goes wrong.
            try:
                shutil.copyfile(full_path, backup)
            except IOError as sub_error:
                my_logger.error("[%s] Unable to backup CSV file: %s.", dev.name, sub_error)
            except Exception as sub_error:
                log_utils.log_traceback(traceback.format_exc())
                my_logger.error(
                    "[%s] Unable to backup CSV file: %s. See plugin log for more information.", dev.name, sub_error
                )

            # ================================= Load Data =================================
            # Read CSV data into data frame
            try:
                with open(full_path, encoding='utf-8') as in_file:
                    raw_data = list(csv.reader(in_file, delimiter=','))

                # Split the headers and the data
                column_names = raw_data[:1]
                data         = raw_data[1:]

                # Coerce header 0 to be 'Timestamp'
                if column_names[0][0] != 'Timestamp':
                    column_names[0][0] = 'Timestamp'

            except IOError as sub_error:
                my_logger.error("[%s] Unable to load CSV data: %s.", dev.name, sub_error)

            # ============================== Limit for Time ===============================
            # Limit data by time
            if delta > 0:
                cut_off = dt.datetime.now() - dt.timedelta(hours=delta)
                time_data = [row for row in data if date_parse(row[0]) >= cut_off]

                # If all records are older than the delta, return the original data (so there's something to chart)
                # and send a warning to the log.
                if len(time_data) == 0:
                    my_logger.debug(
                        "[%s - %s] all CSV data are older than the time limit. Returning original data.", dev.name, column_names[0][1]
                    )
                else:
                    data = time_data

            # ============================ Add New Observation ============================
            # Determine if the thing to be written is a device or variable.
            try:
                state_to_write = ""

                if not value[1]:
                    my_logger.warning(
                        "Found CSV Data element with missing source ID. Please check to ensure all CSV sources are "
                        "properly configured."
                    )

                elif int(value[1]) in indigo.devices:
                    state_to_write = f"{indigo.devices[int(value[1])].states[value[2]]}"

                elif int(value[1]) in indigo.variables:
                    state_to_write = f"{indigo.variables[int(value[1])].value}"

                else:
                    my_logger.critical(
                        "The settings for CSV Engine data element '%s' are not valid: [dev: %s, state/value: %s]", value[0], value[1], value[2]
                    )

                # Give matplotlib something it can chew on if the value to be saved is 'None'
                if state_to_write in ('None', None, ""):
                    state_to_write = 'NaN'

                # Add the newest observation to the end of the data list.
                now = dt.datetime.strftime(cycle_time, '%Y-%m-%d %H:%M:%S.%f')
                data.append([now, state_to_write])

            except ValueError as sub_error:
                log_utils.log_traceback(traceback.format_exc())
                my_logger.error(
                    "[%s] Invalid Indigo ID: %s. See plugin log for more information.", dev.name, sub_error
                )
            except Exception as sub_error:
                log_utils.log_traceback(traceback.format_exc())
                my_logger.error("[%s] Invalid CSV definition: %s", dev.name, sub_error)

            # ============================= Limit for Length ==============================
            # The data frame (with the newest observation included) may now be too long. If it is, we trim it for
            # length.
            if 0 <= target_lines < len(data):
                data = data[len(data) - target_lines:]

            # ================================ Write Data =================================
            # Write CSV data to file

            with open(full_path, 'w', encoding='utf-8') as out_file:
                writer = csv.writer(out_file, delimiter=',')
                writer.writerows(column_names)
                writer.writerows(data)

            # =============================== Delete Backup ===============================
            # If all has gone well, delete the backup.
            try:
                os.remove(backup)
            except Exception as sub_error:
                log_utils.log_traceback(traceback.format_exc())
                my_logger.error("[%s] Unable to delete backup file. %s", dev.name, sub_error)

        dev.updateStatesOnServer(
            [{'key': 'csvLastUpdated', 'value': f"{dt.datetime.now()}"},
             {'key': 'onOffState', 'value': True, 'uiValue': 'Updated'}]
        )

        my_logger.info("[%s] CSV data updated successfully.", dev.name)
        dev.updateStateImageOnServer(indigo.kStateImageSel.WindowSensorClosed)

    except UnboundLocalError:
        my_logger.critical("[%s] Unable to reach storage location. Check connections and permissions.", dev.name)
    except ValueError as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.critical("[%s] Error: %s", dev.name, sub_error)

    except Exception as sub_error:
        log_utils.log_traceback(traceback.format_exc())
        my_logger.critical("[%s] Error: %s", dev.name, sub_error)


# =============================================================================
def csv_refresh_device_action(plugin_action: indigo.ActionGroup, prefs: indigo.Dict, sleep_fn: Callable) -> None:
    """Manually refresh all CSV sources for a single CSV Engine device via an Action item.

    Updates all CSV sources associated with the selected CSV Engine device. Only CSV Engine
    devices set to a manual refresh interval are presented in the action configuration.

    Args:
        plugin_action (indigo.ActionGroup): The Indigo action group containing the target device
            selection.
        prefs (indigo.Dict): The plugin preferences dictionary, passed through to
            csv_refresh_process().
        sleep_fn (Callable): A callable matching indigo.PluginBase.sleep(), passed through to
            csv_refresh_process().
    """
    dev = indigo.devices[int(plugin_action.props['targetDevice'])]

    if dev.enabled:

        # {key: (Item Name, Source ID, Source State)}
        csv_dict_str = dev.pluginProps['columnDict']

        # Convert column_dict from a string to a literal dict.
        csv_dict = ast.literal_eval(csv_dict_str)

        csv_refresh_process(dev=dev, csv_dict=csv_dict, prefs=prefs, sleep_fn=sleep_fn)

    else:
        my_logger.warning('CSV data not updated. Reason: target device disabled.')


# =============================================================================
def csv_refresh_source_action(plugin_action: indigo.ActionGroup, prefs: indigo.Dict, sleep_fn: Callable) -> None:
    """Manually refresh a single CSV source for a CSV Engine device via an Action item.

    Allows the user to update one specific CSV source from a CSV Engine device. The action
    configuration presents the available CSV sources for the selected CSV Engine device. Only CSV
    Engine devices set to a manual refresh interval are presented.

    Args:
        plugin_action (indigo.ActionGroup): The Indigo action group containing the target device
            and source selections.
        prefs (indigo.Dict): The plugin preferences dictionary, passed through to
            csv_refresh_process().
        sleep_fn (Callable): A callable matching indigo.PluginBase.sleep(), passed through to
            csv_refresh_process().
    """
    indigo.server.log(f"{plugin_action}")
    dev_id = int(plugin_action.props['targetDevice'])
    dev    = indigo.devices[dev_id]

    if dev.enabled:
        target_source = plugin_action.props['targetSource']
        temp_dict     = ast.literal_eval(dev.pluginProps['columnDict'])
        payload       = {target_source: temp_dict[target_source]}

        csv_refresh_process(dev=dev, csv_dict=payload, prefs=prefs, sleep_fn=sleep_fn)

    else:
        my_logger.warning('CSV data not updated. Reason: target device disabled.')


# =============================================================================
def csv_source(values_dict: indigo.Dict) -> list:
    """Construct the list of available devices and variables for the CSV Engine add-item control.

    Builds a list of (id, name) tuples for devices, variables, or both depending on the
    addSourceFilter preference. Category labels and separators are included for visual clarity.

    Args:
        values_dict (indigo.Dict): The current dialog values, including 'addSourceFilter'.

    Returns:
        list: A list of (id, name) tuples suitable for an Indigo dropdown control.
    """
    list_ = []

    # Devices
    if values_dict.get('addSourceFilter', 'A') == "D":
        list_.extend([("-1", "%%disabled:Devices%%"), ("-2", "%%separator%%")])
        list_.extend((dev.id, dev.name) for dev in indigo.devices.iter())

    # Variables
    elif values_dict.get('addSourceFilter', 'A') == "V":
        list_.extend([("-3", "%%separator%%"), ("-4", "%%disabled:Variables%%"), ("-5", "%%separator%%")])
        list_.extend((var.id, var.name) for var in indigo.variables.iter())

    # Devices and variables
    else:
        list_.extend([("-1", "%%disabled:Devices%%"), ("-2", "%%separator%%")])
        list_.extend((dev.id, dev.name) for dev in indigo.devices.iter())
        list_.extend([("-3", "%%separator%%"), ("-4", "%%disabled:Variables%%"), ("-5", "%%separator%%")])
        list_.extend((var.id, var.name) for var in indigo.variables.iter())

    return list_


# =============================================================================
def csv_source_edit(values_dict: indigo.Dict) -> list:
    """Construct the list of available devices and variables for the CSV Engine edit-item control.

    Builds a list of (id, name) tuples for devices, variables, or both depending on the
    editSourceFilter preference. Category labels and separators are included for visual clarity.

    Args:
        values_dict (indigo.Dict): The current dialog values, including 'editSourceFilter'.

    Returns:
        list: A list of (id, name) tuples suitable for an Indigo dropdown control.
    """
    list_ = []

    # Devices
    if values_dict.get('editSourceFilter', 'A') == "D":
        _ = [list_.append(t) for t in [("-1", "%%disabled:Devices%%"),
                                       ("-2", "%%separator%%")]
             ]
        _ = [list_.append((dev.id, dev.name)) for dev in indigo.devices.iter()]

    # Variables
    elif values_dict.get('editSourceFilter', 'A') == "V":
        _ = [list_.append(t) for t in [("-3", "%%separator%%"),
                                       ("-4", "%%disabled:Variables%%"),
                                       ("-5", "%%separator%%")
                                       ]
             ]
        _ = [list_.append((var.id, var.name)) for var in indigo.variables.iter()]

    # Devices and variables
    else:
        _ = [list_.append(t) for t in [("-1", "%%disabled:Devices%%"),
                                       ("-2", "%%separator%%")]
             ]
        _ = [list_.append((dev.id, dev.name)) for dev in indigo.devices.iter()]

        _ = [list_.append(t) for t in [("-3", "%%separator%%"),
                                       ("-4", "%%disabled:Variables%%"),
                                       ("-5", "%%separator%%")
                                       ]
             ]
        _ = [list_.append((var.id, var.name)) for var in indigo.variables.iter()]

    return list_


# =============================================================================
def get_csv_device_list() -> list:
    """Return a list of CSV Engine devices configured for manual refresh.

    Filters plugin devices to return only CSV Engine devices whose refreshInterval is set to zero
    (manual update only).

    Returns:
        list: A list of (device_id, device_name) tuples for CSV Engine manual-refresh devices.
    """
    # Return a list of tuples that contains only CSV devices set to manual refresh
    # (refreshInterval = 0) for config menu.
    return [(dev.id, dev.name) for dev in indigo.devices.iter("self") if
            dev.deviceTypeId == "csvEngine" and dev.pluginProps['refreshInterval'] == "0"]


# =============================================================================
def get_csv_source_list(values_dict: indigo.Dict) -> list:
    """Return the list of CSV data sources for the selected CSV Engine device.

    Once the user selects a target CSV Engine device (from get_csv_device_list()), this method
    populates the CSV source dropdown with the available data sources for that device.

    Args:
        values_dict (indigo.Dict): The current dialog values, containing 'targetDevice'.

    Returns:
        list: A list of (key, item_name) tuples for the CSV sources, or an empty list on error.
    """
    try:
        if not values_dict:
            result = []

        # Once user selects a device ( see get_csv_device_list() ), populate the dropdown menu.
        else:
            target_device = int(values_dict.get('targetDevice', 0))
            dev           = indigo.devices[target_device]
            dev_dict      = ast.literal_eval(dev.pluginProps['columnDict'])
            result        = [(k, dev_dict[k][0]) for k in dev_dict]

        return result

    except KeyError:
        return []
