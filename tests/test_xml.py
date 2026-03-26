import os
from .shared.classes import APIBase, ValidateXmlFile

SERVER_PLUGIN_DIR_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../matplotlib.indigoPlugin/Contents/Server Plugin"
    )
)

class TestDeviceXml(ValidateXmlFile, APIBase):
    server_plugin_dir_path = SERVER_PLUGIN_DIR_PATH
    file_name = "Devices.xml"

class TestActionsXml(ValidateXmlFile, APIBase):
    server_plugin_dir_path = SERVER_PLUGIN_DIR_PATH
    file_name = "Actions.xml"

# class TestEventsXml(ValidateXmlFile, APIBase):
#     server_plugin_dir_path = SERVER_PLUGIN_DIR_PATH
#     file_name = "Events.xml"

class TestMenuItemsXml(ValidateXmlFile, APIBase):
    server_plugin_dir_path = SERVER_PLUGIN_DIR_PATH
    file_name = "MenuItems.xml"

class TestPluginConfigXml(ValidateXmlFile, APIBase):
    server_plugin_dir_path = SERVER_PLUGIN_DIR_PATH
    file_name = "PluginConfig.xml"
