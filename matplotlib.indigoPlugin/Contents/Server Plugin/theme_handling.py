# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Theme Manager support.

Covers the Theme Manager menu dialog's callbacks (name list, close, execute action) and the
apply/rename/save/delete operations on the plugin themes JSON file stored in the Indigo
Preferences folder.
"""
import json
import logging

import indigo  # noqa

import validate

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the theme_handling module (no-op placeholder)."""


# =============================================================================
def _themes_file_path() -> str:
    """Return the full path to the plugin themes JSON file.

    Returns:
        str: The full path to 'matplotlib plugin themes.json' in the Indigo Preferences folder.
    """
    return f"{indigo.server.getInstallFolderPath()}/Preferences/Plugins/matplotlib plugin themes.json"


# =============================================================================
def themeNameGenerator() -> list:
    """Return a sorted list of theme names from the themes JSON file for UI dropdown controls.

    Reads the themes JSON file from the Indigo Preferences folder and returns a sorted list of
    (name, name) tuples for use in dialog dropdown controls.

    Returns:
        list: A sorted list of (theme_name, theme_name) tuples.
    """
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    my_logger.debug("themeNameGenerator: list(infile) = %s", list(infile))
    return [(key, key) for key in sorted(infile)]


# =============================================================================
def themeManagerCloseUi(values_dict: indigo.Dict, menu_item_id: str, prefs: indigo.Dict) -> bool:
    """Apply theme settings to pluginPrefs when the Theme Manager dialog is closed.

    Validates the color and line weight values, then copies the theme-related preference keys
    from the dialog values into pluginPrefs for persistence. User cancellation cannot be trapped
    for this dialog type.

    Args:
        values_dict (indigo.Dict): The Theme Manager dialog values.
        menu_item_id (str): The menu item identifier string (passed by Indigo).
        prefs (indigo.Dict): The plugin preferences dictionary to update.

    Returns:
        bool: Always True.
    """
    # Don't need to trap user cancel since this callback won't be called if user cancels. There is no way to trap
    # the cancel.
    my_logger.debug("%s", values_dict)
    my_logger.debug("%s", menu_item_id)

    # ==========================  Validate Theme Values  ===========================
    values_dict = validate.theme_prefs(values_dict)

    # ==========================  Apply Theme Settings  ===========================
    for key in [
        'backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther', 'fontColor',
        'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle', 'legendFontSize',
        'lineWeight', 'mainFontSize', 'spineColor', 'tickColor', 'tickFontSize', 'tickSize'
    ]:
        prefs[key] = values_dict[key]

    return True


# =============================================================================
def themeApplyAction(plugin_action: indigo.ActionGroup, prefs: indigo.Dict) -> None:
    """Apply the selected theme to pluginPrefs via an Indigo Action item.

    Reads the selected theme name from the action props, retrieves the theme from the themes JSON
    file, and updates each theme key in pluginPrefs. Logs a warning if the theme is no longer
    valid.

    Args:
        plugin_action (indigo.ActionGroup): The Indigo action group containing the 'targetTheme'
            selection.
        prefs (indigo.Dict): The plugin preferences dictionary to update.
    """
    selected_theme = plugin_action.props['targetTheme']

    # ==============================  Get the Theme  ==============================
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    # ======================  Confirm Theme is Still Valid  =======================
    if selected_theme not in infile:
        my_logger.warning("Cannot change theme. Selected theme no longer valid.")
        return

    # =============================  Apply the Theme  =============================
    for key in infile[selected_theme]:
        prefs[key] = infile[selected_theme][key]

    my_logger.info("[%s] theme applied.", selected_theme)


# =============================================================================
def themeApply(values_dict: indigo.Dict, prefs: indigo.Dict):
    """Apply the selected theme from the Theme Manager dialog to pluginPrefs.

    Validates that exactly one theme is selected, loads the theme from the JSON file, validates
    its color and line weight values (the JSON file is user-editable and not otherwise constrained
    by the UI), and applies the result to both the dialog and pluginPrefs. Resets the allThemes
    control.

    Args:
        values_dict (indigo.Dict): The Theme Manager dialog values containing 'allThemes'.
        prefs (indigo.Dict): The plugin preferences dictionary to update.

    Returns:
        indigo.Dict | tuple: The updated values_dict on success, or a (values_dict,
            error_msg_dict) tuple if validation fails.
    """
    error_msg_dict = indigo.Dict()
    selected_theme = values_dict['allThemes']

    # ===============================  Validation  ================================
    if not len(selected_theme) == 1:
        error_msg_dict['allThemes'] = "You must select a theme to apply."

    if len(error_msg_dict) > 0:
        return values_dict, error_msg_dict

    # ==========================  Apply Selected Theme  ===========================
    # Get existing themes
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    theme_values = validate.theme_prefs(infile[selected_theme[0]])

    for key in theme_values:
        values_dict[key] = theme_values[key]
        prefs[key] = theme_values[key]

    # ======================  Reset Theme Manager Controls  =======================
    values_dict['allThemes'] = ""
    values_dict['menu'] = 'select'
    return values_dict


# =============================================================================
def themeExecuteActionButton(values_dict: indigo.Dict, prefs: indigo.Dict) -> dict | tuple:
    """Process the Theme Manager Execute Action button press.

    Validates the selected action and dispatches to the appropriate theme management function
    (apply, delete, rename, or save).

    Args:
        values_dict (indigo.Dict): Form values from the config UI dialog.
        prefs (indigo.Dict): The plugin preferences dictionary, passed through to themeApply()
            and theme_save().

    Returns:
        dict | tuple: Updated values_dict, or a tuple of (values_dict, error_msg_dict) on
            validation failure.
    """
    error_msg_dict = indigo.Dict()
    result = None

    # ===============================  Validation  ================================
    if values_dict['menu'] == 'select':
        error_msg_dict['menu'] = "You must select an action to execute."
        return values_dict, error_msg_dict

    # ==================  Execute Selected Theme Manager Action  ==================
    if values_dict['menu'] == 'apply':
        result = themeApply(values_dict, prefs)
    elif values_dict['menu'] == 'delete':
        result = theme_delete(values_dict)
    elif values_dict['menu'] == 'rename':
        result = theme_rename(values_dict)
    elif values_dict['menu'] == 'save':
        result = theme_save(values_dict, prefs)
        values_dict['allThemes'] = "select"

    return result


# =============================================================================
def theme_rename(values_dict: indigo.Dict):
    """Process the Theme Manager Rename Theme action.

    Validates that exactly one theme is selected and a new name is provided, then renames the
    theme in the plugin themes JSON file.

    Args:
        values_dict (indigo.Dict): Form values from the config UI dialog.

    Returns:
        indigo.Dict | tuple: Updated values_dict, or a tuple of (values_dict, error_msg_dict) on
            validation failure.
    """
    old_name       = values_dict['allThemes']
    new_name       = values_dict['newThemeName']
    error_msg_dict = indigo.Dict()

    # ===============================  Validation  ================================
    if len(old_name) != 1:
        error_msg_dict['allThemes'] = "You must select one (and only one) theme to rename."

    if len(old_name) == 1 and len(new_name) == 0:
        error_msg_dict['newThemeName'] = "You must enter a new theme name."

    if len(error_msg_dict) > 0:
        error_msg_dict['showAlertText'] = (
            "Configuration Errors\n\nThere are one or more settings that need to be corrected. Fields requiring "
            "attention will be highlighted."
        )
        return values_dict, error_msg_dict

    # Get existing themes
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    infile[new_name] = infile[old_name[0]]
    del infile[old_name[0]]

    # Write theme dict to file.
    with open(_themes_file_path(), 'w', encoding='utf-8') as f:
        json.dump(infile, f, indent=4, sort_keys=True)

    values_dict['menu'] = 'select'
    values_dict['newThemeName'] = ""
    return values_dict


# =============================================================================
def theme_save(values_dict: indigo.Dict, prefs: indigo.Dict):
    """Process the Theme Manager Save Theme action.

    Validates that a theme name is provided, then saves the current plugin preferences as a named
    theme to the plugin themes JSON file.

    Args:
        values_dict (indigo.Dict): Form values from the config UI dialog.
        prefs (indigo.Dict): The plugin preferences dictionary; only its keys are used, to select
            which theme-related fields to save from values_dict.

    Returns:
        indigo.Dict | tuple: Updated values_dict, or a tuple of (values_dict, error_msg_dict) on
            validation failure.
    """
    my_logger.debug("theme_save")
    new_theme_name = values_dict['newTheme']
    error_msg_dict = indigo.Dict()

    # ===========================  Get existing Themes  ===========================
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    # ===============================  Validation  ================================
    # Save name blank
    if values_dict['newTheme'] == "":
        error_msg_dict['newTheme'] = "You must specify a theme name."

    # Save name already used
    # if values_dict['newTheme'] in infile:
    #     error_msg_dict['newTheme'] = "You must specify a unique name."

    if len(error_msg_dict) > 0:
        error_msg_dict['showAlertText'] = (
            "Configuration Errors\n\nThere are one or more settings that need to be corrected.  Fields requiring "
            "attention will be highlighted."
        )
        return values_dict, error_msg_dict

    infile[new_theme_name] = {}

    # Populate the theme dict
    for key in prefs:
        if key in [
            'backgroundColor', 'backgroundColorOther', 'faceColor', 'faceColorOther', 'fontColor',
            'fontColorAnnotation', 'fontMain', 'gridColor', 'gridStyle', 'legendFontSize', 'lineWeight',
            'mainFontSize', 'spineColor', 'tickColor', 'tickFontSize', 'tickSize'
        ]:
            # infile[new_theme_name][key] = prefs[key]
            infile[new_theme_name][key] = values_dict[key]

    # Write theme dict to file.
    with open(_themes_file_path(), 'w', encoding='utf-8') as f:
        json.dump(infile, f, indent=4, sort_keys=True)

    # Reset field
    values_dict['newTheme'] = ""
    values_dict['menu'] = 'select'
    return values_dict


# =============================================================================
def theme_delete(values_dict: indigo.Dict):
    """Process the Theme Manager Delete Theme action.

    Validates that at least one theme is selected, then removes the selected theme(s) from the
    plugin themes JSON file.

    Args:
        values_dict (indigo.Dict): Form values from the config UI dialog.

    Returns:
        indigo.Dict | tuple: Updated values_dict, or a tuple of (values_dict, error_msg_dict) on
            validation failure.
    """
    del_theme_name = list(values_dict['allThemes'])
    error_msg_dict = indigo.Dict()

    # ===============================  Validation  ================================
    if len(del_theme_name) == 0:
        error_msg_dict['allThemes'] = "You must select at least one theme to delete."
        error_msg_dict['showAlertText'] = "You must select at least one theme to delete."
        return values_dict, error_msg_dict

    # Get existing themes
    with open(_themes_file_path(), 'r', encoding='utf-8') as f:
        infile = json.load(f)

    for name in del_theme_name:
        del infile[name]

    # Write theme dict to file.
    with open(_themes_file_path(), 'w', encoding='utf-8') as f:
        json.dump(infile, f, indent=4, sort_keys=True)

    values_dict['menu'] = 'select'
    return values_dict
