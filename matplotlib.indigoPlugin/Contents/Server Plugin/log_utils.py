# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
Small logging utility shared by plugin.py's extracted helper modules.

Deliberately separate from any single module: audits.py, csv_handling.py, and ui_lists.py all need
to log a formatted traceback the same way Plugin.plugin_error_handler() does, but none of them
should depend on the Plugin instance to do it.
"""
import logging

my_logger = logging.getLogger("Plugin")


def __init__() -> None:
    """Initialize the log_utils module (no-op placeholder)."""


# =============================================================================
def log_traceback(sub_error: str) -> None:
    """Log a formatted traceback message to the plugin log file.

    Mirrors Plugin.plugin_error_handler(). Use this to handle exceptions by passing
    traceback.format_exc() as the argument.

    Args:
        sub_error (str): The string-formatted traceback message to log.
    """
    sub_error = sub_error.splitlines()
    my_logger.critical(f"{' TRACEBACK ':!^80}")

    for line in sub_error:
        my_logger.critical("!!! %s", line)

    my_logger.critical("!" * 80)
