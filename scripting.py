# noqa pylint: disable=too-many-lines, line-too-long, invalid-name, unused-argument, redefined-builtin, broad-except, fixme

"""
The scripting module is used as a plugin API for creating simple charts on demand.

"""
try:
    import indigo
except ImportError:
    pass


matplotlibPlugin = indigo.server.getPlugin("com.fogbert.indigoplugin.matplotlib")
payload = {'x_values': [1, 2, 3],
           'y_values': [2, 4, 7],
           'kwargs': {'linestyle': 'dashed',
                      'color': 'b',
                      'marker': 'd',
                      'markerfacecolor': 'r'},
           'path': '/Library/Application Support/Perceptive Automation/Indigo 7.x/'
                   'IndigoWebServer/images/controls/static/',
           'filename': 'chart_filename.png'
           }
try:
    result = matplotlibPlugin.executeAction('refreshTheChartsAPI',
                                            deviceId=0,
                                            waitUntilDone=True,
                                            props=payload
                                            )
    if result is not None:
        indigo.server.log(result['message'])
except Exception as err:
    indigo.server.log(f"Exception occurred: {err}")
