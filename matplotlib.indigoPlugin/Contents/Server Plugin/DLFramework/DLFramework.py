# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
DLFramework is a framework to consolidate methods used throughout all Indigo plugins with the
com.fogbert.indigoPlugin.xxxx bundle identifier.
"""

import ast
import logging
import operator as op
import os
import platform
import sys
import webbrowser

try:
    import indigo  # noqa
except ImportError:
    pass

# =================================== HEADER ==================================
__author__ = "DaveL17"
__build__ = "Unused"
__copyright__ = "Copyright 2017-2022 DaveL17"
__license__ = "MIT"
__title__ = "DLFramework"
__version__ = "0.1.04"

# supported operators for eval expressions
OPERATORS = {
    ast.Add: op.add,
    ast.Sub: op.sub,
    ast.Mult: op.mul,
    ast.Div: op.truediv,
    ast.Pow: op.pow,
    ast.BitXor: op.xor,
    ast.USub: op.neg,
    ast.LShift: None,
    ast.RShift: None,
    ast.Invert: None,
}


# =============================================================================
class Fogbert:
    """
    Title Placeholder

    Body placeholder
    """
    # =============================================================================
    def __init__(self, plugin):
        """
        Title Placeholder

        Body placeholder

        :param plugin:
        :return:
        """
        self.plugin = plugin
        self.plugin.debugLog("Initializing DLFramework...")
        self.pluginPrefs = plugin.pluginPrefs

        log_format = '%(asctime)s.%(msecs)03d\t%(levelname)-10s\t%(name)s.%(funcName)-28s %(msg)s'
        self.plugin.plugin_file_handler.setFormatter(
            logging.Formatter(fmt=log_format, datefmt='%Y-%m-%d %H:%M:%S')
        )

    # =============================================================================
    def pluginEnvironment(self):  # noqa
        """
        The pluginEnvironment method prints selected information about the pluginEnvironment that
        the plugin is running in. It pulls some of this information from the calling plugin and
        some from the server pluginEnvironment. It uses the legacy "indigo.server.log" method to
        write to the log.

        :return:
        """
        self.plugin.debugLog("DLFramework pluginEnvironment method called.")

        indigo.server.log(f"{' Initializing New Plugin Session ':{'='}^135}")
        indigo.server.log(f"{'Plugin name:':<31} {self.plugin.pluginDisplayName}")
        indigo.server.log(f"{'Plugin version:':<31} {self.plugin.pluginVersion}")
        indigo.server.log(f"{'Plugin ID:':<31} {self.plugin.pluginId}")
        indigo.server.log(f"{'Indigo version:':<31} {indigo.server.version}")
        sys_version = sys.version.replace('\n', '')
        indigo.server.log(f"{'Python version:':<31} {sys_version}")
        indigo.server.log(f"{'Mac OS Version:':<31} {platform.mac_ver()[0]}")
        indigo.server.log(f"{'Process ID:':<31} {os.getpid()}")
        indigo.server.log("=" * 135)

    # =============================================================================
    def pluginEnvironmentLogger(self):  # noqa
        """
        The pluginEnvironmentLogger method prints selected information about the pluginEnvironment
        that the plugin is running in. It pulls some of this information from the calling plugin
        and some from the server pluginEnvironment. This method differs from the pluginEnvironment
        method in that it leverages Indigo's logging hooks using the Python Logger framework.

        :return:
        """
        self.plugin.logger.debug("DLFramework pluginEnvironment method called.")

        self.plugin.logger.info("")
        self.plugin.logger.info(f"{' Initializing New Plugin Session ':=^135}")
        self.plugin.logger.info(f"{'Plugin name:':<31} {self.plugin.pluginDisplayName}")
        self.plugin.logger.info(f"{'Plugin version:':<31} {self.plugin.pluginVersion}")
        self.plugin.logger.info(f"{'Plugin ID:':<31} {self.plugin.pluginId}")
        self.plugin.logger.info(f"{'Indigo version:':<31} {indigo.server.version}")
        sys_version = sys.version.replace('\n', '')  # backslashes are not allowed in f strings
        self.plugin.logger.info(f"{'Python version:':<31} {sys_version}")
        self.plugin.logger.info(f"{'Mac OS Version:':<31} {platform.mac_ver()[0]}")
        self.plugin.logger.info(f"{'Process ID:':<31} {os.getpid()}")
        self.plugin.logger.info("=" * 135)

    # =============================================================================
    def pluginErrorHandler(self, sub_error):  # noqa
        """
        Centralized handling of traceback messages

        Centralized handling of traceback messages formatted for pretty display in the plugin log
        file. If sent here, they will not be displayed in the Indigo Events log. Use the following
        syntax to send exceptions here::

            self.pluginErrorHandler(traceback.format_exc())

        
        :param traceback object sub_error:
        :return:
        """

        sub_error = sub_error.splitlines()
        self.plugin.logger.critical(f"{' TRACEBACK ':!^80}")

        for line in sub_error:
            self.plugin.logger.critical(f"!!! {line}")

        self.plugin.logger.critical("!" * 80)

    # =============================================================================
    def convertDebugLevel(self, debug_val):  # noqa
        """
        The convertDebugLevel method is used to standardize the various implementations of debug
        level settings across plugins. Its main purpose is to convert an old string-based setting
        to account for older plugin versions. Over time, this method will become obsolete and
        should be deprecated.

        :param str debug_val:
        :return:
        """
        self.plugin.debugLog("DLFramework convertDebugLevel method called.")

        # If the debug value is High/Medium/Low, it is the old style. Covert it to 3/2/1
        if debug_val in ["High", "Medium", "Low"]:
            if debug_val == "High":
                debug_val = 3
            elif debug_val == "Medium":
                debug_val = 2
            else:
                debug_val = 1

        return debug_val

    # =============================================================================
    @staticmethod
    def deviceList(dev_filter=None):  # noqa
        """
        Returns a list of tuples containing Indigo devices for use in config dialogs (etc.)

        :param str dev_filter:
        :return: [(ID, "Name"), (ID, "Name")]
        """
        devices_list = [('None', 'None')]
        _ = [devices_list.append((dev.id, dev.name)) for dev in indigo.devices.iter(dev_filter)]
        return devices_list

    # =============================================================================
    @staticmethod
    def deviceListEnabled(dev_filter=None):  # noqa
        """
        Returns a list of tuples containing Indigo devices for use in config dialogs (etc.) Returns
        enabled devices only.

        :param str dev_filter:
        :return: [(ID, "Name"), (ID, "Name")]
        """
        devices_list = [('None', 'None')]
        _ = [devices_list.append((dev.id, dev.name))
             for dev in indigo.devices.iter(dev_filter)
             if dev.enabled
             ]
        return devices_list

    # =============================================================================
    @staticmethod
    def variableList():  # noqa
        """
        Returns a list of tuples containing Indigo variables for use in config dialogs (etc.)

        :return: [(ID, "Name"), (ID, "Name")]
        """
        variable_list = [('None', 'None')]
        _ = [variable_list.append((var.id, var.name)) for var in indigo.variables]
        return variable_list

    # =============================================================================
    @staticmethod
    def deviceAndVariableList():  # noqa
        """
        Returns a list of tuples containing Indigo devices and variables for use in config dialogs
        (etc.)

        :return: [(ID, "(D) Name"), (ID, "(V) Name")]
        """
        devices_and_variables_list = []
        _ = [devices_and_variables_list.append((dev.id, f"(D) {dev.name}"))
             for dev in indigo.devices
             ]
        _ = [devices_and_variables_list.append((var.id, f"(V) {var.name}"))
             for var in indigo.variables
             ]
        devices_and_variables_list.append(('-1', '%%separator%%'),)
        devices_and_variables_list.append(('None', 'None'),)
        return devices_and_variables_list

    # =============================================================================
    @staticmethod
    def launchWebPage(launch_url):  # noqa
        """
        The launchWebPage method is used to direct a call to the registered default browser and
        open the page referenced by the parameter 'URL'.

        :param str launch_url:
        :return:
        """
        webbrowser.open(url=launch_url)

    # =============================================================================
    @staticmethod
    def generatorStateOrValue(dev_id):  # noqa
        """
        The generator_state_or_value() method returns a list to populate the relevant device
        states or variable value to populate a menu control.

        :param int dev_id:
        :return:
        """
        value = None

        try:
            id_number = int(dev_id)

            # if id_number in indigo.devices.keys():
            if id_number in indigo.devices:
                state_list = [
                    (state, state) for state in indigo.devices[id_number].states
                    if not state.endswith('.ui')
                ]
                if ('onOffState', 'onOffState') in state_list:
                    state_list.remove(('onOffState', 'onOffState'))
                value = state_list

            # elif id_number in indigo.variables.keys():
            elif id_number in indigo.variables:
                value = [('value', 'Value')]

            return value

        except (KeyError, ValueError):
            return [(0, 'Pick a Device or Variable')]

    # =============================================================================
    def audit_server_version(self, min_ver):
        """
        Audit Indigo Version

        Compare current Indigo version to the minimum version required to successfully run the
        plugin.

        
        :param int min_ver:
        :return:
        """

        ver = self.plugin.versStrToTuple(indigo.server.version)
        if ver[0] < min_ver:
            self.plugin.stopPlugin(
                f"This plugin requires Indigo version {min_ver} or above.", isError=True
            )

        self.plugin.logger.debug("Indigo server version OK.")

    # =============================================================================
    def audit_os_version(self, min_ver):
        """
        Audit Operating System Version

        Compare current OS version to the minimum version required to successfully run the plugin.
        Thanks to FlyingDiver for improved audit code.

        :param float min_ver:
        :return:
        """
        # minimum allowable version. i.e., (10, 13)
        min_ver = tuple(map(int, (str(min_ver).split("."))))
        mac_os = platform.mac_ver()[0]
        current_ver = tuple(map(int, (str(mac_os).split("."))))  # current version. i.e., (11, 4)

        if current_ver < min_ver:
            self.plugin.stopPlugin(
                f"The plugin requires macOS version {min_ver} or above.", isError=True
            )
        else:
            self.plugin.logger.debug("macOS version OK.")


# =============================================================================
class Formatter:
    """
    The Formatter class contains methods to provide unique custom data formats as needed.
    """

    # =============================================================================
    def __init__(self, plugin):
        """
        Title Placeholder

        :param plugin:
        :return:
        """
        self.plugin = plugin
        self.pluginPrefs = plugin.pluginPrefs

    # =============================================================================
    def dateFormat(self):  # noqa
        """
        The dateFormat method takes the user configuration preference for date and time display and
        converts them to a valid datetime() format specifier.

        :return:
        """

        date_formatter = {
            'DD-MM-YYYY': '%d-%m-%Y',
            'MM-DD-YYYY': '%m-%d-%Y',
            'YYYY-MM-DD': '%Y-%m-%d'
        }
        return date_formatter[self.pluginPrefs['uiDateFormat']]

    # =============================================================================
    def timeFormat(self):  # noqa
        """
        The timeFormat method takes the user configuration preference for date and time display and
        converts them to a valid datetime() format specifier.

        :return:
        """

        time_formatter = {'military': '%H:%M', 'standard': '%I:%M', 'standard_am_pm': '%I:%M %p'}
        return time_formatter[self.pluginPrefs['uiTimeFormat']]


# =============================================================================
class evalExpr:  # noqa
    """
    The evalExpr method evaluates mathematical expressions that are passed as strings and returns a
    numerical result.

    This code is licensed under an MIT-compatible license.
    credit: jfs @ https://stackoverflow.com/a/9558001/2827397
    """

    # =============================================================================
    def __init__(self, plugin):
        """
        Title Placeholder

        Body placeholder
        
        :param plugin:
        :return:
        """
        self.plugin = plugin
        self.pluginPrefs = plugin.pluginPrefs

    # =============================================================================
    def eval_expr(self, expr):
        """
        Title Placeholder

        Body placeholder
        
        :param str expr:
        :return:
        """
        return self.__eval(ast.parse(expr, mode='eval').body)

    # =============================================================================
    def __eval(self, node):
        """
        Title Placeholder

        Body placeholder
        
        :param node:
        :return:
        """

        # See https://stackoverflow.com/q/71353183/2827397 (and the accompanying answer) for an
        # explanation of the code inspection warnings thrown by this method.
        try:
            if isinstance(node, ast.Num):  # <number>
                value = node.n
            elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
                value = OPERATORS[type(node.op)](self.__eval(node.left), self.__eval(node.right))
            elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
                value = OPERATORS[type(node.op)](self.__eval(node.operand))
            else:
                raise TypeError(node)

            return value
        except (TypeError, KeyError):
            self.plugin.logger.critical("That expression is not allowed.")


class DummyClass:

    def Dave(self, at1="foo", at2=0):
        """
        This docstring is loosely formatted to `PEP 287` with a nod towards PyCharm reStructured
        Text rendering.

        :param str at1: This is a string attribute.
        :param int at2: This is an integer attribute.
        :return: True | False
        """
        x = at1 + "x"
        y = at2 + 1
        return True
