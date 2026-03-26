"""
Unit tests for chart_*.py chart generation scripts.

Each chart script is invoked as a subprocess (mirroring how the Indigo plugin calls them),
receiving a minimal but complete payload via sys.argv[1].  No running Indigo instance is required.

Structure
---------
- _run_chart()          module-level helper: runs a chart script and returns (process, log)
- _base_payload()       module-level helper: builds the keys common to all chart payloads
- _make_*_payload()     per-chart helpers: call _base_payload() and add chart-specific keys
- _ChartTestBase        abstract base: holds the 3 standard tests (file created, no critical
                        errors, valid PNG); not collected by pytest (underscore prefix)
- TestChart*            one subclass per chart script; sets SCRIPT/OUTPUT_FILENAME and builds
                        its payload in setUpClass; may add chart-specific tests
"""
# Built-in Modules
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Tuple

SERVER_PLUGIN_PATH = Path(__file__).parent.parent / "matplotlib.indigoPlugin" / "Contents" / "Server Plugin"
_STYLESHEET_ID     = "1331356132"  # Known stylesheet present in Stylesheets/
_CSV_FILENAME      = "test_data.csv"

_CSV_CONTENT = (
    "timestamp,Test Series 1\n"
    "2025-01-01 00:00:00,10.0\n"
    "2025-01-02 00:00:00,20.0\n"
    "2025-01-03 00:00:00,15.0\n"
    "2025-01-04 00:00:00,25.0\n"
    "2025-01-05 00:00:00,18.0\n"
)

# =============================================================================
# Shared runner
# =============================================================================

def _run_chart(script: str, payload: dict) -> Tuple[subprocess.CompletedProcess, dict]:
    """Run a chart script as a subprocess and parse its JSON log output.

    Args:
        script (str): Filename of the chart script (e.g. 'chart_area.py').
        payload (dict): The payload to pass as sys.argv[1].

    Returns:
        Tuple[subprocess.CompletedProcess, dict]: The completed process and the parsed LOG dict.
    """
    result = subprocess.run(
        [sys.executable, script, json.dumps(payload)],
        cwd=str(SERVER_PLUGIN_PATH),
        capture_output=True,
        text=True,
    )
    log: dict = json.loads(result.stdout) if result.stdout.strip() else {}
    return (result, log)


# =============================================================================
# Payload builders
# =============================================================================

def _base_payload(csv_dir: str, output_dir: str, output_filename: str) -> dict:
    """Build the keys shared by all chart payloads.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.
        output_filename (str): Name of the output file (e.g. 'test_chart_area.png').

    Returns:
        dict: A base payload dict.  Chart-specific keys should be merged in by callers.
    """
    csv_dir_slash    = csv_dir.rstrip("/") + "/"
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':                 csv_dir_slash,
        'verboseLogging':           False,
        'forceOriginLines':         False,
        'enableCustomLineSegments': False,
    }

    props: dict = {
        'name':                 'Test Chart',
        'id':                   _STYLESHEET_ID,
        'chart_type':           '',       # overridden per chart
        'isChart':              True,
        'limitDataRangeLength': '0',
        'limitDataRange':       'new',
    }

    p_dict: dict = {
        'chart_width':              500.0,
        'chart_height':             300.0,
        'chartPath':                output_dir_slash,
        'fileName':                 output_filename,
        'faceColor':                '#191919',
        'spineColor':               '#585858',
        'fontColor':                '#E6E6E6',
        'backgroundColor':          '#191919',
        'fontMain':                 'sans-serif',
        'tickFontSize':             '8',
        'showLegend':               False,
        'legendColumns':            3,
        'legendFontSize':           8.0,
        'transparent_charts':       False,
        'transparent_filled':       False,
        'chartTitle':               '',
        'customAxisLabelX':         '',
        'customAxisLabelY':         '',
        'xAxisLabelFormat':         '%m-%d',
        'xAxisBins':                '10',
        'xAxisRotate':              False,
        'yAxisMin':                 'None',
        'yAxisMax':                 'None',
        'yAxisPrecision':           '0',
        'yMirrorValues':            False,
        'yMirrorValuesAlsoY1':      False,
        'yAxisRotate':              False,
        'customSizeFont':           False,
        'customTickFontSize':       '8',
        'showxAxisGrid':            False,
        'showyAxisGrid':            False,
        'customTicksY':             [],
        'customTicksLabelY':        [],
        'enableCustomLineSegments': False,
        'customLineSegments':       [],
        'customLineStyle':          ':',
        'verboseLogging':           False,
        'data_array':               [],
        'headers':                  [],
    }

    k_dict = {
        'k_line':        {'alpha': 1.0},
        'k_bar':         {'alpha': 1.0, 'zorder': 10},
        'k_annotation':  {
            'bbox': {
                'alpha':     0.75,
                'boxstyle':  'round,pad=0.3',
                'facecolor': '#191919',
                'edgecolor': '#585858',
                'linewidth': 0.5,
            },
            'color':      '#E6E6E6',
            'ha':         'center',
            'textcoords': 'offset points',
            'va':         'center',
        },
        'k_plot_fig':    {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
        'k_min':         {'linestyle': 'dotted', 'marker': None, 'alpha': 1.0, 'zorder': 1},
        'k_max':         {'linestyle': 'dotted', 'marker': None, 'alpha': 1.0, 'zorder': 1},
        'k_custom':      {'alpha': 1.0, 'zorder': 3},
        'k_grid_fig':    {'which': 'major', 'zorder': 1},
        'k_title_font':  {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_x_axis_font': {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_y_axis_font': {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_major_x':     {'reset': False, 'which': 'major'},
        'k_minor_x':     {'reset': False, 'which': 'minor'},
        'k_major_y':     {'reset': False, 'which': 'major'},
        'k_minor_y':     {'reset': False, 'which': 'minor'},
    }

    return {'prefs': prefs, 'props': props, 'p_dict': p_dict, 'k_dict': k_dict}


def _make_area_payload(csv_dir: str, output_dir: str) -> dict:
    """Build the full payload for chart_area.py.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_area.py.
    """
    payload = _base_payload(csv_dir, output_dir, 'test_chart_area.png')
    payload['props']['chart_type'] = 'area'
    payload['props']['name']       = 'Test Area Chart'

    for n in range(1, 9):
        payload['props'][f'area{n}adjuster']            = ''
        payload['props'][f'area{n}AnnotationPrecision'] = '0'
        payload['props'][f'line{n}BestFit']             = False

    for n in range(1, 9):
        payload['p_dict'][f'area{n}Source']      = _CSV_FILENAME if n == 1 else ''
        payload['p_dict'][f'area{n}Color']       = '#FF6600'
        payload['p_dict'][f'area{n}Annotate']    = False
        payload['p_dict'][f'area{n}Legend']      = ''
        payload['p_dict'][f'area{n}Marker']      = 'None'
        payload['p_dict'][f'area{n}MarkerColor'] = '#FF6600'
        payload['p_dict'][f'line{n}Style']       = 'None'
        payload['p_dict'][f'line{n}Color']       = '#FF6600'
        payload['p_dict'][f'plotArea{n}Min']     = False
        payload['p_dict'][f'plotArea{n}Max']     = False
        payload['p_dict'][f'suppressArea{n}']    = False
        payload['p_dict'][f'x_obs{n}']           = []
        payload['p_dict'][f'y_obs{n}']           = []

    return payload


def _make_bar_flow_payload(csv_dir: str, output_dir: str) -> dict:
    """Build the full payload for chart_bar_flow.py.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_bar_flow.py.
    """
    payload = _base_payload(csv_dir, output_dir, 'test_chart_bar_flow.png')
    payload['props']['chart_type'] = 'bar (flow)'
    payload['props']['name']       = 'Test Bar Flow Chart'

    for n in range(1, 5):
        payload['props'][f'bar{n}AnnotationPrecision'] = '0'

    payload['props']['limitDataRangeLength'] = '0'
    payload['props']['limitDataRange']       = 'new'

    payload['p_dict']['numObs']      = 0
    payload['p_dict']['barWidth']    = '0.8'
    payload['p_dict']['showZeroBars'] = False

    for n in range(1, 5):
        payload['p_dict'][f'bar{n}Source']    = _CSV_FILENAME if n == 1 else ''
        payload['p_dict'][f'bar{n}Color']     = '#FF6600'
        payload['p_dict'][f'bar{n}Annotate']  = False
        payload['p_dict'][f'bar{n}Legend']    = ''
        payload['p_dict'][f'plotBar{n}Min']   = False
        payload['p_dict'][f'plotBar{n}Max']   = False
        payload['p_dict'][f'suppressBar{n}']  = False
        payload['p_dict'][f'x_obs{n}']        = []
        payload['p_dict'][f'y_obs{n}']        = []

    return payload


def _make_bar_radial_payload(output_dir: str) -> dict:
    """Build the full payload for chart_bar_radial.py.

    This chart does not use CSV data.  It plots a single float value supplied
    directly in payload['data'] against a configurable scale.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_bar_radial.py.
    """
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':                 output_dir_slash,
        'verboseLogging':           False,
        'forceOriginLines':         False,
        'enableCustomLineSegments': False,
    }

    props = {
        'name':       'Test Radial Bar Chart',
        'id':         _STYLESHEET_ID,
        'chart_type': 'radial bar',
        'isChart':    True,
    }

    p_dict = {
        'chartPath':        output_dir_slash,
        'fileName':         'test_chart_bar_radial.png',
        'faceColor':        '#191919',
        'spineColor':       '#585858',
        'fontColor':        '#E6E6E6',
        'bar_1':            '#FF6600',
        'bar_2':            '#333333',
        'gridColor':        '#585858',
        'fontMain':         'sans-serif',
        'mainFontSize':     12,
        'precision':        1,
        'sqChartSize':      3,
        'startAngle':       90,
        'scale':            100.0,
        'customSizeFont':   False,
        'customTickFontSize': '8',
    }

    k_dict = {
        'k_plot_fig': {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
    }

    return {
        'prefs':  prefs,
        'props':  props,
        'p_dict': p_dict,
        'k_dict': k_dict,
        'data':   75.0,
        'scale':  100.0,
    }


def _make_bar_stock_payload(output_dir: str) -> dict:
    """Build the full payload for chart_bar_stock.py.

    This chart uses stock (time-agnostic) data supplied directly in payload['data']
    as a list of bar descriptor dicts rather than CSV files.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_bar_stock.py.
    """
    payload = _base_payload(output_dir, output_dir, 'test_chart_bar_stock.png')
    payload['props']['chart_type'] = 'bar (stock)'
    payload['props']['name']       = 'Test Bar Stock Chart'

    for n in range(1, 5):
        payload['props'][f'bar{n}AnnotationPrecision'] = '0'

    payload['p_dict']['barWidth']     = '0.8'
    payload['p_dict']['showZeroBars'] = False

    for n in range(1, 5):
        payload['p_dict'][f'bar{n}Annotate']  = False
        payload['p_dict'][f'bar{n}Legend']    = f'Bar {n}'
        payload['p_dict'][f'suppressBar{n}']  = False

    payload['data'] = [
        {'number': n, f'color_{n}': '#FF6600', f'val_{n}': str(10.0 * n),
         f'legend_{n}': f'Bar {n}', f'annotate_{n}': False}
        for n in range(1, 3)
    ]

    return payload


def _make_bar_stock_horizontal_payload(output_dir: str) -> dict:
    """Build the full payload for chart_bar_stock_horizontal.py.

    Identical structure to the vertical stock bar payload; the script renders
    bars horizontally via ax.barh() but consumes the same payload shape.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_bar_stock_horizontal.py.
    """
    payload = _make_bar_stock_payload(output_dir)
    payload['p_dict']['fileName']  = 'test_chart_bar_stock_horizontal.png'
    payload['props']['chart_type'] = 'bar (stock horizontal)'
    payload['props']['name']       = 'Test Bar Stock Horizontal Chart'
    payload['p_dict']['xAxisMin']  = 'None'
    payload['p_dict']['xAxisMax']  = 'None'
    return payload


def _make_batteryhealth_payload(output_dir: str) -> dict:
    """Build the full payload for chart_batteryhealth.py.

    This chart uses a dict of {device_name: battery_level} supplied in
    payload['data'] rather than CSV files.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_batteryhealth.py.
    """
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':                 output_dir_slash,
        'verboseLogging':           False,
        'forceOriginLines':         False,
        'enableCustomLineSegments': False,
        'showxAxisGrid':            False,
        'gridColor':                '#585858',
        'gridStyle':                ':',
        'fontColor':                '#E6E6E6',
        'tickFontSize':             '8',
        'fontMain':                 'sans-serif',
    }

    props = {
        'name':       'Test Battery Health Chart',
        'id':         _STYLESHEET_ID,
        'chart_type': 'batteryhealth',
        'isChart':    True,
    }

    p_dict = {
        'chart_width':               500.0,
        'chart_height':              300.0,
        'chartPath':                 output_dir_slash,
        'fileName':                  'test_chart_batteryhealth.png',
        'faceColor':                 '#191919',
        'spineColor':                '#585858',
        'fontColor':                 '#E6E6E6',
        'backgroundColor':           '#191919',
        'fontMain':                  'sans-serif',
        'chartTitle':                '',
        'customAxisLabelX':          '',
        'customAxisLabelY':          '',
        'xAxisLabelFormat':          '%m-%d',
        'xAxisBins':                 '10',
        'xAxisRotate':               False,
        'customSizeFont':            False,
        'customTickFontSize':        '8',
        'verboseLogging':            False,
        'cautionColor':              '#FFAA00',
        'cautionLevel':              50,
        'healthyColor':              '#00AA00',
        'warningColor':              '#FF0000',
        'warningLevel':              20,
        'showBatteryLevelBackground': False,
        'showBatteryLevel':          True,
        'showDeadBattery':           False,
        'showDeviceName':            True,
        'transparent_charts':        False,
        'transparent_filled':        False,
        'data_array':                [],
    }

    k_dict = {
        'k_bar':             {'alpha': 1.0, 'zorder': 10},
        'k_battery':         {
            'color':     '#E6E6E6',
            'ha':        'right',
            'textcoords': 'data',
            'va':        'center',
            'xycoords':  'data',
            'zorder':    25,
        },
        'k_annotation_battery': {
            'bbox': {
                'alpha':     0.75,
                'boxstyle':  'round,pad=0.3',
                'facecolor': '#191919',
                'edgecolor': '#585858',
                'linewidth': 0.5,
            },
            'color':      '#E6E6E6',
            'ha':         'center',
            'textcoords': 'data',
            'va':         'center',
            'xycoords':   'data',
            'zorder':     25,
        },
        'k_title_font':  {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_x_axis_font': {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_plot_fig':    {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
    }

    return {
        'prefs':  prefs,
        'props':  props,
        'p_dict': p_dict,
        'k_dict': k_dict,
        'data':   {'Alpha Device': 85, 'Beta Device': 42, 'Gamma Device': 15},
    }


def _make_calendar_payload(output_dir: str) -> dict:
    """Build the full payload for chart_calendar.py.

    This chart generates a calendar for the current month from the system clock;
    no external data source is required.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_calendar.py.
    """
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':       output_dir_slash,
        'verboseLogging': False,
    }

    props = {
        'name':               'Test Calendar Chart',
        'id':                 _STYLESHEET_ID,
        'chart_type':         'calendar',
        'isChart':            True,
        'firstDayOfWeek':     6,
        'dayOfWeekFormat':    'mid',
        'dayOfWeekAlignment': 'right',
        'customSizeHeight':   '200',
        'customSizeWidth':    '500',
        'fontSize':           10,
        'calendarGrid':       True,
    }

    p_dict = {
        'chartPath':      output_dir_slash,
        'fileName':       'test_chart_calendar.png',
        'faceColor':      '#191919',
        'spineColor':     '#585858',
        'fontColor':      '#E6E6E6',
        'fontMain':       'sans-serif',
        'todayHighlight': '#555555',
    }

    k_dict = {
        'k_plot_fig': {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
    }

    return {'prefs': prefs, 'props': props, 'p_dict': p_dict, 'k_dict': k_dict}


def _make_line_payload(csv_dir: str, output_dir: str) -> dict:
    """Build the full payload for chart_line.py.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_line.py.
    """
    payload = _base_payload(csv_dir, output_dir, 'test_chart_line.png')
    payload['props']['chart_type'] = 'line'
    payload['props']['name']       = 'Test Line Chart'

    payload['props']['limitDataRangeLength'] = '0'
    payload['props']['limitDataRange']       = 'new'
    payload['props']['filterAnomalies']      = '0'
    for n in range(1, 9):
        payload['props'][f'line{n}adjuster']            = ''
        payload['props'][f'line{n}BestFit']             = False
        payload['props'][f'line{n}AnnotationPrecision'] = '0'

    payload['k_dict']['k_fill'] = {'alpha': 0.7, 'zorder': 10}

    for n in range(1, 9):
        payload['p_dict'][f'line{n}Source']      = _CSV_FILENAME if n == 1 else ''
        payload['p_dict'][f'line{n}Color']       = '#FF6600'
        payload['p_dict'][f'line{n}Style']       = '-'
        payload['p_dict'][f'line{n}Marker']      = 'None'
        payload['p_dict'][f'line{n}MarkerColor'] = '#FF6600'
        payload['p_dict'][f'line{n}Fill']        = False
        payload['p_dict'][f'line{n}Annotate']    = False
        payload['p_dict'][f'line{n}Legend']      = ''
        payload['p_dict'][f'plotLine{n}Min']     = False
        payload['p_dict'][f'plotLine{n}Max']     = False
        payload['p_dict'][f'suppressLine{n}']    = False
        payload['p_dict'][f'x_obs{n}']           = []
        payload['p_dict'][f'y_obs{n}']           = []

    return payload


def _make_multiline_payload(output_dir: str) -> dict:
    """Build the full payload for chart_multiline.py.

    This chart renders a block of text as an image; payload['data'] is the
    string to display rather than numeric time-series data.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_multiline.py.
    """
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':       output_dir_slash,
        'verboseLogging': False,
    }

    props = {
        'name':         'Test Multiline Chart',
        'id':           _STYLESHEET_ID,
        'chart_type':   'multiline',
        'isChart':      True,
        'figureWidth':  '500',
        'figureHeight': '200',
    }

    p_dict = {
        'chartPath':          output_dir_slash,
        'fileName':           'test_chart_multiline.png',
        'faceColor':          '#191919',
        'fontMain':           'sans-serif',
        'chartTitle':         '',
        'cleanTheText':       True,
        'defaultText':        'No data available.',
        'numberOfCharacters': 60,
        'textAreaBorder':     False,
        'transparent_charts': False,
        'transparent_filled': False,
        'figureWidth':        500.0,
        'figureHeight':       200.0,
    }

    k_dict = {
        'k_title_font': {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_plot_fig':   {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
    }

    return {
        'prefs':  prefs,
        'props':  props,
        'p_dict': p_dict,
        'k_dict': k_dict,
        'data':   'Partly cloudy with a high near 72. South wind around 10 mph.',
    }


def _make_polar_payload(csv_dir: str, output_dir: str) -> dict:
    """Build the full payload for chart_polar.py.

    This chart reads two CSV files: one for wind direction (theta, degrees) and
    one for wind speed (radii).  The existing test CSV is reused for both.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_polar.py.
    """
    csv_dir_slash    = csv_dir.rstrip("/") + "/"
    output_dir_slash = output_dir.rstrip("/") + "/"

    prefs = {
        'dataPath':       csv_dir_slash,
        'verboseLogging': False,
        'gridColor':      '#585858',
        'fontColor':      '#E6E6E6',
        'tickFontSize':   '8',
        'fontMain':       'sans-serif',
    }

    props = {
        'name':       'Test Polar Chart',
        'id':         _STYLESHEET_ID,
        'chart_type': 'polar',
        'isChart':    True,
    }

    p_dict = {
        'chartPath':          output_dir_slash,
        'fileName':           'test_chart_polar.png',
        'faceColor':          '#191919',
        'spineColor':         '#585858',
        'fontColor':          '#E6E6E6',
        'fontMain':           'sans-serif',
        'thetaValue':         _CSV_FILENAME,
        'radiiValue':         _CSV_FILENAME,
        'wind_direction':     [],
        'wind_speed':         [],
        'bar_colors':         [],
        'numObs':             5,
        'currentWindColor':   '#FF6600',
        'maxWindColor':       '#FF0000',
        'sqChartSize':        300,
        'xHideLabels':        False,
        'yHideLabels':        False,
        'transparent_charts': False,
        'transparent_filled': False,
        'showLegend':         False,
        'legendFontSize':     8.0,
        'customSizeFont':     False,
        'customTickFontSize': '8',
        'tickFontSize':       '8',
        'chartTitle':         '',
    }

    k_dict = {
        'k_rgrids':     {'angle': 67, 'ha': 'left', 'va': 'center'},
        'k_title_font': {'color': '#E6E6E6', 'fontname': 'sans-serif', 'visible': True},
        'k_plot_fig':   {'facecolor': '#191919', 'edgecolor': '#191919', 'transparent': False},
    }

    return {'prefs': prefs, 'props': props, 'p_dict': p_dict, 'k_dict': k_dict}


def _make_scatter_payload(csv_dir: str, output_dir: str) -> dict:
    """Build the full payload for chart_scatter.py.

    Args:
        csv_dir (str): Directory containing the test CSV file.
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_scatter.py.
    """
    payload = _base_payload(csv_dir, output_dir, 'test_chart_scatter.png')
    payload['props']['chart_type'] = 'scatter'
    payload['props']['name']       = 'Test Scatter Chart'

    payload['props']['limitDataRangeLength'] = '0'
    payload['props']['limitDataRange']       = 'new'
    payload['props']['filterAnomalies']      = '0'
    for n in range(1, 5):
        payload['props'][f'group{n}adjuster']            = ''
        payload['props'][f'line{n}BestFit']              = False

    for n in range(1, 5):
        payload['p_dict'][f'group{n}Source']      = _CSV_FILENAME if n == 1 else ''
        payload['p_dict'][f'group{n}Color']       = '#FF6600'
        payload['p_dict'][f'group{n}Marker']      = 'o'
        payload['p_dict'][f'group{n}MarkerColor'] = '#FF6600'
        payload['p_dict'][f'group{n}Legend']      = ''
        payload['p_dict'][f'plotGroup{n}Min']     = False
        payload['p_dict'][f'plotGroup{n}Max']     = False
        payload['p_dict'][f'suppressGroup{n}']    = False
        payload['p_dict'][f'x_obs{n}']            = []
        payload['p_dict'][f'y_obs{n}']            = []

    return payload


def _daily_state_list() -> dict:
    """Return a minimal state_list dict covering 8 forecast days.

    Returns:
        dict: State-list dict with keys d01 through d08 for all weather fields
            consumed by both chart_weather_composite.py and chart_weather_forecast.py.
    """
    state: dict = {}
    for i in range(1, 9):
        tag = f'd0{i}'
        state[f'{tag}_date']            = f'2025-01-{i:02d}'
        state[f'{tag}_temperatureHigh'] = float(60 + i)
        state[f'{tag}_temperatureLow']  = float(40 + i)
        state[f'{tag}_humidity']        = float(55 + i)
        state[f'{tag}_pressure']        = float(1010 + i)
        state[f'{tag}_windSpeed']       = float(5 + i)
        state[f'{tag}_windBearing']     = float(180 + i)
        state[f'{tag}_precipTotal']     = float(i) * 0.05
        state[f'{tag}_precipChance']    = float(i) * 5.0
        state[f'{tag}_pop']             = float(i) * 5.0
    return state


def _make_weather_composite_payload(output_dir: str) -> dict:
    """Build the full payload for chart_weather_composite.py.

    Uses 'Daily' device type with a 2-subplot layout (high temperature +
    humidity) to exercise the composite rendering path without requiring
    a live Indigo weather device.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_weather_composite.py.
    """
    payload = _base_payload(output_dir, output_dir, 'test_chart_weather_composite.png')
    payload['props']['chart_type'] = 'composite forecast'
    payload['props']['name']       = 'Test Weather Composite Chart'

    payload['props']['component_list']    = ['show_high_temperature', 'show_humidity']
    payload['props']['height']            = '300'
    payload['props']['width']             = '500'
    payload['props']['xAxisLabelFormat']  = '%m-%d'
    payload['props']['customSizeFont']    = False
    payload['props']['customTickFontSize'] = '8'

    payload['p_dict']['lineColor']         = '#FF6600'
    payload['p_dict']['lineMarkerColor']   = '#FF6600'
    payload['p_dict']['temperature_min']   = 'None'
    payload['p_dict']['temperature_max']   = 'None'
    payload['p_dict']['humidity_min']      = 'None'
    payload['p_dict']['humidity_max']      = 'None'
    payload['p_dict']['pressure_min']      = 'None'
    payload['p_dict']['pressure_max']      = 'None'
    payload['p_dict']['precipitation_min'] = 'None'
    payload['p_dict']['precipitation_max'] = 'None'
    payload['p_dict']['wind_min']          = 'None'
    payload['p_dict']['wind_max']          = 'None'
    payload['p_dict']['transparent_filled'] = False

    payload['prefs']['fontMain']     = 'sans-serif'
    payload['prefs']['tickFontSize'] = '8'

    payload['state_list'] = _daily_state_list()
    payload['dev_type']   = 'Daily'

    return payload


def _make_weather_forecast_payload(output_dir: str) -> dict:
    """Build the full payload for chart_weather_forecast.py.

    Uses 'Daily' device type (8-day forecast) to exercise the dual-axis
    temperature + precipitation rendering path.

    Args:
        output_dir (str): Directory where the output PNG will be written.

    Returns:
        dict: A complete payload for chart_weather_forecast.py.
    """
    payload = _base_payload(output_dir, output_dir, 'test_chart_weather_forecast.png')
    payload['props']['chart_type'] = 'weather forecast'
    payload['props']['name']       = 'Test Weather Forecast Chart'

    payload['props']['showDaytime']             = False
    payload['props']['xAxisLabelFormat']        = '%m-%d'
    payload['props']['line1AnnotationPrecision'] = '0'
    payload['props']['line2AnnotationPrecision'] = '0'
    payload['props']['line3AnnotationPrecision'] = '0'

    for n in range(1, 4):
        payload['p_dict'][f'line{n}Color']       = '#FF6600'
        payload['p_dict'][f'line{n}Style']       = '-'
        payload['p_dict'][f'line{n}Marker']      = 'None'
        payload['p_dict'][f'line{n}MarkerColor'] = '#FF6600'
        payload['p_dict'][f'line{n}Annotate']    = False

    payload['p_dict']['dates_to_plot'] = []
    payload['p_dict']['x_obs1']        = []
    payload['p_dict']['x_obs2']        = []
    payload['p_dict']['x_obs3']        = []
    payload['p_dict']['y_obs1']        = []
    payload['p_dict']['y_obs2']        = []
    payload['p_dict']['y_obs3']        = []
    payload['p_dict']['headers_1']     = ()
    payload['p_dict']['headers_2']     = ()
    payload['p_dict']['yAxisMin']      = 'None'
    payload['p_dict']['yAxisMax']      = 'None'
    payload['p_dict']['y2AxisMin']     = 'None'
    payload['p_dict']['y2AxisMax']     = 'None'
    payload['p_dict']['customAxisLabelY2'] = ''
    payload['p_dict']['daytimeColor']  = '#FFFF99'

    payload['prefs']['fontMain']     = 'sans-serif'
    payload['prefs']['tickFontSize'] = '8'

    payload['state_list']   = _daily_state_list()
    payload['dev_type']     = 'Daily'
    payload['sun_rise_set'] = []

    return payload


# =============================================================================
# Base test class
# =============================================================================

class _ChartTestMixin:
    """Mixin providing shared infrastructure and standard tests for all chart script test classes.

    Not a unittest.TestCase subclass — so neither pytest nor PyCharm's unittest runner will
    collect it directly.  Concrete test classes inherit from both this mixin and unittest.TestCase.

    Subclasses must set SCRIPT and OUTPUT_FILENAME as class attributes and build
    cls._payload in their own setUpClass (calling super().setUpClass() first).
    """
    SCRIPT:          str = ''
    OUTPUT_FILENAME: str = ''

    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_dir    = tempfile.TemporaryDirectory()
        tmp              = cls._temp_dir.name
        csv_path         = Path(tmp) / _CSV_FILENAME
        csv_path.write_text(_CSV_CONTENT, encoding='utf-8')
        cls._output_file = Path(tmp) / cls.OUTPUT_FILENAME
        cls._payload: dict = {}  # populated by subclass setUpClass

    @classmethod
    def tearDownClass(cls) -> None:
        cls._temp_dir.cleanup()

    # ------------------------------------------------------------------
    # Standard tests (inherited by all subclasses)
    # ------------------------------------------------------------------

    def test_output_file_created(self) -> None:
        """Chart script should write an image to chartPath/fileName."""
        _run_chart(self.SCRIPT, self._payload)
        self.assertTrue(self._output_file.exists(), f"Expected output file not found: {self._output_file}")

    def test_no_critical_errors(self) -> None:
        """Chart script should complete without any critical-level log entries."""
        _, log = _run_chart(self.SCRIPT, self._payload)
        self.assertEqual(log.get('Critical', []), [], f"Critical errors logged: {log.get('Critical')}")

    def test_valid_png_header(self) -> None:
        """The output file should be a valid PNG (correct magic bytes)."""
        _run_chart(self.SCRIPT, self._payload)
        with open(self._output_file, 'rb') as fh:
            header = fh.read(4)
        self.assertEqual(header, b'\x89PNG', "Output file does not have a valid PNG header.")


# =============================================================================
# Per-chart test classes
# =============================================================================

class TestChartArea(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_area.py."""
    SCRIPT          = 'chart_area.py'
    OUTPUT_FILENAME = 'test_chart_area.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_area_payload(cls._temp_dir.name, cls._temp_dir.name)

    def test_suppressed_area_no_critical_errors(self) -> None:
        """Suppressing an area with no data source should produce no critical errors."""
        payload = copy.deepcopy(self._payload)
        payload['p_dict']['suppressArea2'] = True
        _, log = _run_chart(self.SCRIPT, payload)
        self.assertEqual(log.get('Critical', []), [], f"Critical errors logged: {log.get('Critical')}")


class TestChartBarFlow(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_bar_flow.py."""
    SCRIPT          = 'chart_bar_flow.py'
    OUTPUT_FILENAME = 'test_chart_bar_flow.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_bar_flow_payload(cls._temp_dir.name, cls._temp_dir.name)

    def test_suppressed_bar_no_critical_errors(self) -> None:
        """Suppressing a bar with no data source should produce no critical errors."""
        payload = copy.deepcopy(self._payload)
        payload['p_dict']['suppressBar2'] = True
        _, log = _run_chart(self.SCRIPT, payload)
        self.assertEqual(log.get('Critical', []), [], f"Critical errors logged: {log.get('Critical')}")


class TestChartBarRadial(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_bar_radial.py.

    This chart takes a single float value via payload['data'] rather than CSV
    time-series data, so no CSV file is written during setup.
    """
    SCRIPT          = 'chart_bar_radial.py'
    OUTPUT_FILENAME = 'test_chart_bar_radial.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_bar_radial_payload(cls._temp_dir.name)


class TestChartBarStock(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_bar_stock.py."""
    SCRIPT          = 'chart_bar_stock.py'
    OUTPUT_FILENAME = 'test_chart_bar_stock.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_bar_stock_payload(cls._temp_dir.name)


class TestChartBarStockHorizontal(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_bar_stock_horizontal.py."""
    SCRIPT          = 'chart_bar_stock_horizontal.py'
    OUTPUT_FILENAME = 'test_chart_bar_stock_horizontal.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_bar_stock_horizontal_payload(cls._temp_dir.name)


class TestChartBatteryHealth(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_batteryhealth.py."""
    SCRIPT          = 'chart_batteryhealth.py'
    OUTPUT_FILENAME = 'test_chart_batteryhealth.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_batteryhealth_payload(cls._temp_dir.name)


class TestChartCalendar(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_calendar.py."""
    SCRIPT          = 'chart_calendar.py'
    OUTPUT_FILENAME = 'test_chart_calendar.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_calendar_payload(cls._temp_dir.name)


class TestChartLine(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_line.py."""
    SCRIPT          = 'chart_line.py'
    OUTPUT_FILENAME = 'test_chart_line.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_line_payload(cls._temp_dir.name, cls._temp_dir.name)


class TestChartMultiline(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_multiline.py."""
    SCRIPT          = 'chart_multiline.py'
    OUTPUT_FILENAME = 'test_chart_multiline.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_multiline_payload(cls._temp_dir.name)


class TestChartPolar(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_polar.py."""
    SCRIPT          = 'chart_polar.py'
    OUTPUT_FILENAME = 'test_chart_polar.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_polar_payload(cls._temp_dir.name, cls._temp_dir.name)


class TestChartScatter(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_scatter.py."""
    SCRIPT          = 'chart_scatter.py'
    OUTPUT_FILENAME = 'test_chart_scatter.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_scatter_payload(cls._temp_dir.name, cls._temp_dir.name)


class TestChartWeatherComposite(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_weather_composite.py."""
    SCRIPT          = 'chart_weather_composite.py'
    OUTPUT_FILENAME = 'test_chart_weather_composite.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_weather_composite_payload(cls._temp_dir.name)


class TestChartWeatherForecast(_ChartTestMixin, unittest.TestCase):
    """Tests for chart_weather_forecast.py."""
    SCRIPT          = 'chart_weather_forecast.py'
    OUTPUT_FILENAME = 'test_chart_weather_forecast.png'

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls._payload = _make_weather_forecast_payload(cls._temp_dir.name)


if __name__ == '__main__':
    unittest.main()
