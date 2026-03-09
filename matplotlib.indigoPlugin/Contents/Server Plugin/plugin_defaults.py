"""
Contains plugin default preferences.

Defines the kDefaultPluginPrefs dictionary used to initialize plugin preferences when they are not already set by the
user. All keys correspond to fields defined in PluginConfig.xml.
"""

from typing import Any, Dict
import indigo  # noqa

INSTALL_PATH: str = indigo.server.getInstallFolderPath()

kDefaultPluginPrefs: Dict[str, Any] = {
    'backgroundColor': "00 00 00",
    'backgroundColorOther': False,
    'chartPath': f"{INSTALL_PATH}/IndigoWebServer/images/controls/",
    'chartResolution': 100,
    'dataPath': "{install_path}/Logs/com.fogbert.indigoplugin.matplotlib/",
    'dpiWarningFlag': False,
    'enableCustomLineSegments': False,
    'faceColor': "00 00 00",
    'faceColorOther': False,
    'fontColor': "FF FF FF",
    'fontColorAnnotation': "FF FF FF",
    'fontMain': "Arial",
    'forceOriginLines': False,
    'gridColor': "88 88 88",
    'gridStyle': ":",
    'legendFontSize': 6,
    'lineWeight': "1.0",
    'logEachChartCompleted': True,
    'mainFontSize': 10,
    'promoteCustomLineSegments': False,
    'rectChartHeight': 250,
    'rectChartWideHeight': 250,
    'rectChartWideWidth': 1000,
    'rectChartWidth': 600,
    'showDebugLevel': 30,  # comes from template_debugging.xml
    'spineColor': "88 88 88",
    'sqChartSize': 250,
    'tickColor': "88 88 88",
    'tickFontSize': 8,
    'tickSize': 4,
    'verboseLogging': False
}
