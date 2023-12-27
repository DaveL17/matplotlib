"""
Contains plugin default preferences.
"""

try:
    import indigo  # noqa
except ImportError:
    ...

INSTALL_PATH = indigo.server.getInstallFolderPath()

kDefaultPluginPrefs = {
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
