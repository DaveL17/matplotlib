#### v2023.0.1
- Changes to prepare for Indigo `v2023.2`.
- Code enhancements.

#### v2022.1.7
- Fixes bug where `Matplotlib Paramters Device` incorrectly labelled in error state.
- Fixes bug `PluginAction' object has no attribute 'PROPS'`.
- Fixes bug where Refresh CSV Device Action returned an error when no such devices exist.

#### v2022.1.6
- Fixed bug where custom Y axis tick marks and locations were sometimes not plotted properly.
- Fixed bug where `rcParamsDevice` devices were not skipped when user elects to redraw all charts from the plugin menu.
- Adds module filename to chart error tracebacks to make it easier to find the error.
- Adds new module `validate` and moves validation code to that module.
- Code refinements.
- Minor UI refinements.
 
#### v2022.1.5
- Charts
  - Annotation value precision controls added to Area, Bar Flow Vertical, Bar Stock Horizontal, Bar Stock Vertical, 
    Line, Weather Forecast devices.
  - Fixed bug in annotation display for weather forecast devices.
- Theme Manager
  - Changes behavior of Save Theme action to allow updates to existing themes without having to create a new theme.
  - Fixed bug in Theme Manager Rename action.
- Custom Line Segments
  - Deprecates `step`, `steps-mid`, and `steps-post` line styles which are no longer supported by Matplotlib.
  - Fixed bug that caused custom line segments to not be plotted.
- Code refinements.
- Minor UI refinements.

#### v2022.1.4
- Converts `feature_requests.txt` to `_feature_requests.md`.
- Adds foundation for API `3.1`.
- Fixes bug where `'list' object has not attribute 'lower'`.
- Fixes bug where `'list' object has not attribute 'strip'`.
- Fixes bug where Weather Composite Chart Precipitation Bar resulted in an empty chart.
- Fixes bug where some settings for Forecast Weather Composite devices would revert to their default settings when the 
  configuration dialog is opened.

#### v2022.1.3
- Adds control to rotate X-axis labels (charts: area, bar (horizontal stock), bar (vertical flow), bar (vertical stock),
  line, scatter, weather forecast, weather forecast composite)
- Fixes bug where user executes `Redraw Charts Now...` Menu Item without first selecting an option.
- Adds `_to_do_list.md` and changes changelog to markdown.
- Moves plugin environment logging to plugin menu item (log only on request).

#### v2022.1.2
- Adds option to refresh individual chart to `Redraw Charts Now...` Menu Item.

#### v2022.1.1
- Removes extra space between title and plot figure.

#### v2022.0.2
- Removes dummy testing data for battery charts.

#### v2022.0.1
- Updates plugin for Indigo 2022.1 and Python 3.
- Polar charts are back!
- Standardizes Indigo method implementation.
- Deprecates `step`, `steps-mid`, and `steps-post` line styles which are no longer supported by matplotlib. Step charts
  will return in the future as a separate chart type.
- Fixes bug where Stylesheets folder is not present.
- Adds additional logic for instances where data are None values (or otherwise unavailable).
- Streamlines Devices.xml (~800 lines moved to dynamic list callbacks).

#### v0.9.52
- Fixes bug in file save location testing.
- Fixes bug that caused multiline text title to move to the left.
- Changes alert that file save locations do not match current Indigo version from error level to warning.

#### v0.9.51
- Addresses queue `module not found` import error.

#### v0.9.50
- Updates image save path logic for Indigo 2021.

#### v0.9.49
- Implements Constants.py
- Code refinements.

#### v0.9.48
- Refines save path audit to allow for more than just static images folder.

#### v0.9.47
- New Device Type: Radial Bar Chart

#### v0.9.46
- Deprecates snappy config menus as they are no longer needed with the new UI changes.
- Refinements

#### v0.9.45
- Refinements

#### v0.9.44
- New Feature: Theme Manager
- Reorders display settings in Theme Manager (categories).
- Hides display settings in plugin config.

#### v0.9.43
- Factors out chart themes for a different implementation.

#### v0.9.42
- Sorts yAxisPrecision KeyError for stock horizontal charts.
- Fixes bug in A axis tick formatting for quarter- and half-hour increments.

#### v0.9.41
- Sorts x-axis label color bug for stock bar charts.

#### v0.9.40
- Refinements to PluginConfig.xml
- Refinements to MenuItems.xml
- Refinements to Devices.xml
- Refinements to Actions.xml
- Fixes 'xAxisBins' KeyError in chart_bar_stock.py
- Devices now refresh "instantly" after saving configuration.

#### v0.9.39
- sync

#### v0.9.38
- Increases visual space between legends and plots.
- When device config validation fails, try to automatically force dialog to settings group with the error.

#### v0.9.37
- New Device Type: Horizontal Stock Bar Chart
- New Feature: Menu Item [Redraw Charts Now] now give option to skip manual update charts.
- Significant refinements to how settings are displayed in chart configuration dialogs.
- Changes default bar width for all charts to 0.8.
- Moves chart config dialog warning text to template.
- Reduces `runconcurrentThread()` sleep from 15 to 1.

#### v0.9.36
- Improves color collision auditing so only those chart elements where a source is defined will be checked (doesn't
  audit non-configured elements.)
- Changes UI status for manual chart devices so that, after a chart update, the status is returned to 'manual'.
- Fixes bug where non-chart devices could throw an error on first refresh after plugin loaded.
- Fixes bug in how Composite Forecast device implemented transparency.

#### v0.9.35
- Improves handling of chart annotation values for Stock Bar Charts.

#### v0.9.34
- Fixes stock bar annotations when bars plotted with values of zero.
- Traps stock bar error when data starts with zero, but Display Zero Bars unchecked.
- Changes default setting for Stock Bar Display Zero Bars to True.

#### v0.9.33
- Fixes stock bar validation error where device would fail validation when less than 100 percent of bars populated.
- Fixes stock bar annotations when bars plotted with values of zero.

#### v0.9.32
- Fixes bug where new action data didn't pickle properly.

#### v0.9.31
- New Feature: Change Chart Colors action.
- Moves successful charting messages from chart files to plugin.py for error trapping/status reporting.
- Fixes bug in format X axis for non-date-based charts.
- More robust log handling, UI reporting, error messages.
- Cleaner debug logging.
- Streamlines code in charts_refresh().

#### v0.9.30
- Traps bug in format X axis (key error).
- Traps "OSError: [Errno 7] Argument list too long" for multiline text devices.
- Modifies device validation to expand control groups to ensure that any flagged setting will be immediately visible
  (expands closed group if error in group).
- Modifies Stock Bar device validation to ensure that selected sources can be charted (int, float, bool) since they
  are not based on external CSV.
- Standardizes Indigo method implementation.

#### v0.9.29
- Adds maintenance of anomalies filter to convert from bool to int for already established devices.

#### v0.9.28
- New Device Type: Stock Bar Chart -- which displays stock data (as opposed to flow data).
- New trap for SyntaxError for custom line segments.
- Adds validation for Y axis min/max to ensure that min < max when both are specified.
- Adds "chart_type" field to all device types for identification through values_dict payload.
- Fixes bug in color repair for bbox dicts in k_dict (goes another level deep).

#### v0.9.27
- Improves logging.
- Fixed bug where scatter charts were always plotted with a transparent background.
- Fixed bug where composite weather charts weren't displaying the proper background.

#### v0.9.26
- Fixed bug in color audit.
- Fixed bug in custom line segments.

#### v0.9.25
- Feature: Scatter charts now support adjustment factor
- Bug fixes

#### v0.9.24
- Feature: Custom line segments now supports variable and device substitutions.

#### v0.9.23
- Fixes bug in line color settings for Composite Weather devices when initially created.
- Code refinements.
- Faster sorting in maintenance.clean_prefs
- Removes legacy custom color pre-processing.
- Refines color management (conversion of (XX XX XX to #XXXXXX).

#### v0.9.22
- New Feature: hide anomalies in data for line, scatter charts (not currently available for other chart types).
- New Feature: highlight today's date on calendar charts.
- Minor improvements to plugin API.
- Bug fixes
- Code refinements

#### v0.9.21
- Adds device custom font settings to maintenance.py.
- Code refinements.

#### v0.9.20
- Fixes setting of tick font styles across chart types.

#### v0.9.19
- Fixes bug in setting tick label size for forecast charts.
- Fixes bug in setting tick label size for composite weather charts.
- Code refinements.

#### v0.9.18
- Refactors battery health chart to address several rendering bugs.

#### v0.9.17
- Fixes font size bug in formatting of title and X axis tick labels for polar charts.
- Fixes bug in coloring of polar chart grid and tick labels.

#### v0.9.16
- Fixes Invalid IHDR data error for multiline charts (size / DPI less than one).
- Fixes font size bug in formatting of title and X axis tick labels.

#### v0.9.15
- Fixes plug_dict bug in scatter chart.
- Fixes Dict error in weather composite chart.
- Fixes color bug in battery health chart.

#### v0.9.14
- Fixes bug in line chart title.
- Fixes bug in line chart adjustment factor.
- Fixes bug in line chart custom line segments.
- Traps MAXTICKS error more cleanly.
- More logging refinements.

#### v0.9.13
- Refines logging across processes.

#### v0.9.12
- Code refinement and bug fixes as a result of subprocess.Popen refactoring.

#### v0.9.11
- Converts weather composite charting code from multiprocessing to subprocess.Popen.

#### v0.9.10
- Converts weather forecast charting code from multiprocessing to subprocess.Popen.

#### v0.9.09
- Converts scatter charting code from multiprocessing to subprocess.Popen.

#### v0.9.08
- Converts area charting code from multiprocessing to subprocess.Popen.

#### v0.9.07
- Converts area charting code from multiprocessing to subprocess.Popen.

#### v0.9.06
- Converts polar charting code from multiprocessing to subprocess.Popen.

#### v0.9.05
- Converts battery health charting code from multiprocessing to subprocess.Popen.

#### v0.9.04
- Converts multiline charting code from multiprocessing to subprocess.Popen.

#### v0.9.03
- Converts line charting code from multiprocessing to subprocess.Popen.
- Code refinements.

#### v0.9.02
- Converts calendar charting code from multiprocessing to subprocess.Popen.

#### v0.9.01
- Converts all usages of Indigo objects used in multiprocessing processes to standard pickleable objects.

#### v0.8.39
- Fixes plugin configuration validation bug for new installs.

#### v0.8.38
- Pre-release of all changes to this point. Includes final zero bar error fix.

#### v0.8.37
- Adds feature to force leading and trailing bars with zero values to be plotted (to overcome matplotlib bug).

#### v0.8.36
- Additional bar chart error trapping.

#### v0.8.35
- Code refinements.

#### v0.8.34
- Better integration of DLFramework.

#### v0.8.33
- Improvements to device configuration validation.
- Deprecates matplotlib_version.html.

#### v0.8.32
- Fixes initialization error.

#### v0.8.31
- Fixes broken link to repo.

#### v0.8.30
- Fixes bug where y-axis min not formatted properly when set automatically.
- Improves error handling in csv_refresh_process.
- Code refinements.

#### v0.8.29
- Removes all references to legacy version checking.

#### v0.8.28
- Provides additional validation to ensure that required plugin configuration fields are non-empty.
- Bug fixes.

#### v0.8.27
- Fixes bug in Area, Bar, Line, and Scatter Chart devices where ticking the "Suppress [item]" checkbox did not silence
  the warnings that the [item] color is the same as the plot area color.

#### v0.8.26
- Version sync

#### v0.8.25
- Improves Calendar Chart devices which no longer require monospace fonts. A few additional settings added including a
  format specifier for how days are reflected (i.e., 'M', 'Mon', 'Monday').

#### v0.8.24
- Adds precipitation bar chart option for composite forecast devices.
- Adds min/max settings for composite weather device elements.
- Changes device type name for composite forecast devices.
- Reorders plot elements list for composite forecast device.
- Enables validation for composite forecast device.
- Code refinements.

#### v0.8.23
- Adds Composite Weather Device type.
- Fixes bug in selection menu for date format (DD MMM) which was improperly defined.

#### v0.8.22
- Adds lines to Area Chart device.

#### v0.8.21
- Adds markers to Area Chart device. Note that the marker will be placed at the cumulative value of the data point and
  not its absolute value.

#### v0.8.20
- Adds plot min and max to Area Chart device. Note that the min/max lines reflect the cumulative value of the data
  point and not its absolute value.

#### v0.8.19
- Adds annotations to Area Chart device. Note that annotation reflects the cumulative value of the data point and not
  its absolute value.

#### v0.8.18
- Adds Area Chart device type. Note that v0.8.18 does not support some features for Area Chart devices that other
  device types support (min, max, annotations and markers.)

#### v0.8.17
- Fixes bug in setting of hourly bins for charts that support the option.
- Adds a 2-hour option to the X Axis bins setting.

#### v0.8.16
- Audits save paths to ensure they exist and are writeable at startup.

#### v0.8.15
- Adds feature to limit the number of days of data to display to bar, line, and scatter charts.
- Fixes bug in setting of Y1 axis limits where max or min of data are negative.

#### v0.8.14
- Removes development logging.

#### v0.8.13
- Fixes bug in line chart legend layout where colors didn't match chart.

#### v0.8.12
- Converts all static menu callbacks to hard-coded XML list items to make selection of default option more seamless
  and converts them to XML templates for consistency and lightness.
- Indicates default menu item options with a star (*); only applies to static menu lists (not dynamic lists).

#### v0.8.11
- Adds lines 7 and 8 to Line Charting device.

#### v0.8.10
- Adds test at plugin startup which will review each device's properties and bring it up to date with the latest base
  configuration. Any changes are written to the plugin log.

#### v0.8.09
- Adds test at plugin startup which will review CSV Engine device sources and issue a warning when more than one CSV
  device is writing to the same CSV file.

#### v0.8.08
- Adds device/variable filter to Multiline Text devices.

#### v0.8.07
- Fixes bug where the legend colors didn't match plot for select column number settings for Scatter Charts.
- Fixes bug where the Display Legend? control did not appear for scatter charts.

#### v0.8.06
- Improves and expands options for X axis bins.
- Adds section text and tooltips to show/hide controls for bar, line, scatter, and weather devices (other device types
  don't have show/hide controls.)

#### v0.8.05
- At plugin startup, iterate through all CSV Engine devices, audit CSV files, and create any missing ones.

#### v0.8.04
- Traps OSError when plugin cannot connect to the CSV storage location.
- Refactors battery charting code.

#### v0.8.03
- Highlights battery devices with dead batteries (level of 0) by coloring the label using the warning color setting.

#### v0.8.02
- Adds control to vary the number of legend columns for bar, line and scatter charts.
- UI Refinements

#### v0.8.01
- Plugin should shut down more gracefully.
- Code refinements.

#### v0.7.57
- Moves 'None' options in drop-down lists to bottom of list (per Indigo standard.)

#### v0.7.56
- Adds check to ensure that the plugin is compatible with Indigo version.

#### v0.7.55
- Re-fixes float error in the duration value for CSV refreshes.

#### v0.7.54
- Fixes float error in the duration value for CSV refreshes.
- Moves dev prop maintenance routine to device_start_comm.

#### v0.7.53
- Adds tests to alert the user that they're saving charts to the wrong location (when the Indigo version is updated.)
- Fixes bug where battery level being displayed regardless of setting.

#### v0.7.52
- Better handles long device names in Battery Health chart.
- Plots title relative to figure instead of to plot.
- Fixes KeyError bug in pluginEnvironmentLogger 'isChart'.

#### v0.7.51
- Adds control to hide device names on battery health charts.
- Improves plotting of battery level values on battery health charts.
- Code refinements.

#### v0.7.50
- Consolidates chart plot logging into single method.
- Help bubble refinements.
- Code refinements.

#### v0.7.49
- Standardizes plotting of X axis label across all devices.
- Standardizes plotting of chart title across all devices.
- Standardizes save image code across all devices.
- Refines <SupportURL> behavior across all plugin elements.

#### v0.7.48
- Adds support for charting 'Armed' and 'Disarmed' values.

#### v0.7.47
- Improves handling of CSV data updates when duration is set to zero (no limit.)

#### v0.7.46
- Fixes empty text instances for custom Y tick labels (where locations are defined but labels are not.)

#### v0.7.45
- Adds feature to Battery Health Device to plot a background box for battery level values.
- Improves validation for chart axis limits (Y Min, Y Max, Y2 Min, Y2 Max).
- Improves code for plotting Y1 and Y2 axis limits (Y Min, Y Max, Y2 Min, Y2 Max).
- Code refinements.

#### v0.7.44
- Updates config dialog text for Battery Health Chart -- excluded devices (language referred to legacy control.)
- Adds requirement that the custom Y tick labels field and custom Y tick values field be the same length.
- Fixes bug for Battery Health Chart to remove "No Battery Devices" dummy device when actual devices present.

#### v0.7.43
- Adds default entries for legend labels (will only be displayed if Display Legend option is enabled.)

#### v0.7.42
- Refines configuration dialog control labels.
- Deletes unneeded Fill control from Bar Devices (bar 4).

#### v0.7.41
- Fixes bug in format_axis_y_ticks where error was thrown under certain conditions (including 'None', '', and ' '.)
- Improved error logging.

#### v0.7.40
- Fixed bug in line charting for 'TypeError: list indices must be integers, not str'

#### v0.7.39
- No longer allows creation of CSV device without establishing at least one data source.
- Fixes bug in validation of plugin configuration settings for change logging.
- Improves docstrings.

#### v0.7.38
- Adds process garbage collection to runConcurrentThread().

#### v0.7.37
- Chart update processes are no longer blocking.
- Puts CSV refreshing back in the main thread.

#### v0.7.36
- Moves CSV refreshing to its own process.

#### v0.7.35
- Fixes bug in custom line segments where only the first custom line is plotted.

#### v0.7.34
- Fixes bug in duration setting for CSV devices.

#### v0.7.33
- Further improves maintenance of legacy props in all chart devices.
- Moves maintenance tasks to separate module.

#### v0.7.32
- Further improves maintenance of legacy props in all chart devices.
- Set all device UI icons to off state when comm killed through plugin menu action.
- Fixed bug in snappy config menus which created unneeded device props.

#### v0.7.31
- Fixed bug in bar chart config dialog where X axis grid setting not hiding properly.

#### v0.7.30
- Improves logging of plugin prefs when changes made using configuration dialog.
- Fixes placement of line 6 suppression option in line chart device configuration dialog.

#### v0.7.29
- Improves resiliency to CSV files that contain 1 or fewer observations.
- Changes the default timestamp from the epoch to current time (retains the epoch as the default device last refresh).
- Adds trap for RuntimeError when trying to save chart image to address the 'too many ticks' error.
- Adds trap for TypeError when trying to generate a best fit line segment to address the 'int' object is not iterable
  error.
- Adds number of chart devices and CSV engine devices to plugin environment logging.

#### v0.7.28
- Improved conversion of legacy line fill properties to bool type.

#### v0.7.27
- Reorders plugin device model list when editing device.
- Improves error logging.
- Cleans up XML attributes.

#### v0.7.26
- Revises chart device names for consistency.
- Fixes bug in battery chart device "KeyError: 'customSizeChart'. "

#### v0.7.25
- Adds choice to bar, line and scatter charts to suppress the plotting of individual data elements. The data and all
  settings are retained.

#### v0.7.24
- Synchronize self.pluginPrefs in closed_prefs_config_ui().

#### v0.7.23
- Adds choice to set bar width to make it simpler for first time device creation. If the value is set to zero, the
  plugin will attempt to set an attractive bar width automatically. Zero is now the new default for new bar chart
  devices.
- Changes menu items from "En/Disable All Devices" to "En/Disable All Plugin Devices".
- Changes default font for Calendar Devices to 12 pt (to better fit the default image size for non-retina screens.)
- Changes behavior of custom size chart checkbox so that now, custom size values will only be honored when the custom
  size checkbox is checked.
- Improves validation of plugin device configuration settings.
- Improves setting of Y1 limits and better handles condition where limits set improperly when all observations are the
  same value.
- Updates CSV device validation for duration (data to keep).
- Updates behavior so that if all CSV data are older than the time limit, the plugin will return the original data and
  warn the user.
- Refines grid settings for Polar Chart Devices
- Fixes bug in Line Chart devices where customizations (like best fit or fill) would result in an 'argument dimensions
  are incompatible' error.
- Fixes bug in default line color settings for Weather Forecast devices.
- Fixes bug in new CSV data source names that contain extended Unicode characters.
- Fixes bug in new and existing Polar Chart data source names that contain extended Unicode characters.
- Fixes bug where data header name was converted to 'NaN' while data quality repairs were made.
- Fixes bug where line chart best fit property incorrectly stored as a string. Will convert legacy devices in this
  state to boolean.
- Changes Python lists to tuples where possible to improve speed.
- Updates kDefaultPluginPrefs
- Code refinements.

#### v0.7.22
- Removes dependence on pandas library.
- Code refinements.

#### v0.7.21
- Removes default location from plugin preferences for data and chart save locations.

#### v0.7.20
- Improves resiliency in dealing with malformed CSV files.
- Adds new date formats for chart axes:
    Jan 16       [M D]
    Jan 16 2019  [M D Y]
    16 Jan       [D M]
    2019 Jan 16  [Y M D]
- [Line Devices] Hides the best fit color control until the "Plot Best Fit" checkbox is selected.
- Fixes bug in date/time format specifiers.
- Improves CSV item processing performance.
- Fixes bug in manual refresh Action.
- *Attempts* to work around pandas bug in rare csv write bug where the string '-01-01 00:00:00' is added to observation
  data.
- Refines plugin logging.
- Improves under-hood maintenance to ensure that the plugin and its devices are up-to-date for the installed version
  (plugin preference, device properties, etc.)
- Code refinements.

#### v0.7.19
- CSV Engine / Edit Data Item / Data Source control now returns a case-insensitive sorted list.
- Fixes bug in naming of CSV Engine data items that contain Unicode characters.
- Ups the default duration limit to no limit (where it should have been in the first place.)

#### v0.7.18
- Ups the duration limit default to 7200 hours.

#### v0.7.17
- Refines behavior of filters in CSV Engine configuration dialog.

#### v0.7.16
- Moves 'None' option on chart Data Source menu to bottom of list (to follow Indigo UI design.)
- Refines behavior of filters in CSV Engine configuration dialog.

#### v0.7.15
- Adds filter to CSV Engine Edit Data Item controls.

#### v0.7.14
- In data source menus for chart devices, moves the option 'None' to the top of the menu list.
- Fixes bug in management of CSV files when at the limit of requested observations.
- Fixes bug where device comm not honored for chart devices when called by single chart refresh action.

#### v0.7.13
- Adds filter to CSV Engine Add Device controls to allow source menu to be filtered to show all sources, just devices,
  or just variables.

#### v0.7.12
- Consolidates csv_refresh_process() under pandas.

#### v0.7.11
- Adds CSV Engine device limit based on time (in hours).
- Includes pandas library in base installation (#### v0.19.1).

#### v0.7.10
- Improves device configuration dialogs (battery health, line).
- Removes plugin update checking.
- Fixes bug where manual update charts were updating every 15 seconds.
- Code refinements.

#### v0.7.09
- Settings for manual CSV refresh actions now retained when CSV Engine device source names changed.

#### v0.7.08
- Adds Action item to update CSV device set to manual update only
- Adds Action item to update CSV device set to manual update only for single CSV data source.

#### v0.7.07
- Fixes bug for rare circumstance where chart device's 'csvLastUpdated' state did not save in expected timestamp format.

#### v0.7.06
- Fixes datetime bug in new CSV Engine devices (csvLastUpdated).

#### v0.7.05
- Adds support for Fantastic Weather forecast devices.
- Fixes bug in Refresh Charts menu item.
- Fixes bug in Refresh Charts action item.

#### v0.7.04
- Moves refresh interval to charts. Users can now establish individual refresh rates for each chart separately.
- Adds weekly option to refresh interval.
- Better sorting of CSV sources within device configuration dialogs.
- Significantly reduces debug logging.
- Code refinements.

#### v0.7.03
- Fixes bug in setting of marker style for lines 5 and 6.
- Fixes bug in setting of marker color for all lines.
- Fixes bug in sorting of data source names for device configuration.
- Code refinements.

#### v0.7.02
- Moves charting code into separate class.

#### v0.7.01
- Adjusts chart output logging for consistency between enabled and disabled devices.
- Fixes bug where legacy devices not updated for missing line5Annotate and line6Annotate props.

#### v0.6.06
- Adds two more lines to the line charting device.
- Fixes bug where best fit line affected legend entries.

#### v0.6.05
- Fixes bug in Scatter Chart devices to plot points when marker is set to None. (This is a bug in matplotlib, plugin
  overrides the behavior).
- Fixes bug in naming of PluginConfig.xml (which caused problems on systems set up as case-sensitive).

#### v0.6.04
- New Feature: optional 'best fit line' for line and scatter charts.
- Polar charts will now plot when CSV records are fewer than the desired number of observations.
- Significantly reduces the amount of information written to the log unless verbose logging is enabled.

#### v0.6.03
- Improves placement of legend for 10 day and 24-hour forecast devices.
- Base CSV file now created at the time new item added to CSV engine.

#### v0.6.02
- Adds feature to battery health chart to select devices to exclude from the list of devices charted.
- Fixes bug in grid setting for battery health chart.

#### v0.6.01
- New Battery Health Device: plots the battery level of all Indigo devices that report a battery level value.
- Adds new daylight indicator to 24-hour forecast device. The default is to display daylight on the chart; the setting
  can be disabled from the device configuration dialog.
- Adds delay between updates of CSV data and processing of charts to ensure data writing steps have completed.
- Improves polar device handling of condition where the number of csv observations is less than the number wanted by
  the device.
- Improves error handling for situations where a fatal error might cause a device to hang during refresh.

#### v0.5.07
- Improves handling of nonsense values (-99 values).
- Suppresses non-chart device types from displaying in Update Chart Actions.
- Adds separators and labels to dropdown menus for context and visual clarity.
- Improves code commenting and adds Sphinx compatibility to docstrings.
- Code consolidation.

#### v0.5.06
- Refactors code for better method naming convention.

#### v0.5.05
- Adds line chart device validation to disallow fill with steps line style.
- Updates plugin update checker to use curl to overcome outdated security of Apple's Python install.

#### v0.5.04
- Adds data adjustment factor to line devices.
- Removes obsolete references to pre-colorpicker color settings.
- Adds logic to convert legacy colors set as hex to raw. (FF FF FF instead of #FFFFFF)
- Adds format setting for X axis label format to be None. (No X axis label will appear.)
- Plugin is now more agnostic about the date format for CSV files. (Should now work with any date/time value that is
  acceptable to the dateutil parser.)

#### v0.5.03
- Adds internal converter to allow more binary values to be plotted. The following values plot as True (1): 'locked',
  'on', 'open', 'up', 'true', '1'. The plugin will now also skip values of '-99' which are meaningless values set by
  the WUnderground plugin when rational data aren't provided by the service.
- Improves device config default settings for all charts.
- Improves device config validation for: Bar, Line, Multiline Text, Polar, Scatter, and Weather charts.
- Expands use of DLFramework.

#### v0.5.02
- Corrects Indigo API reference in info.plist from 2.0.0 to 2.0

#### v0.5.01
- Increments version number for release.

#### v0.4.16
- Code consolidation using DLFramework.
- Standardizes file framework.
- Adds note to documentation that the plugin requires Internet access to function.
- Adds README.md

#### v0.4.15
- Moves Redraw Single Chart action to the device actions submenu and renames it to 'Redraw Chart'.
- Moves Redraw All Charts action to the device actions submenu.

#### v0.4.14
- Standardizes plugin menu item styles. Menu items with an ellipsis (...) denote that a dialog box will open. Menu
  items without an ellipsis denote that the plugin will take immediate action.

#### v0.4.13
- Changes font list method to a list comprehension.

#### v0.4.12
- Converts all color settings to new Indigo Color Picker. This may cause users to need to re-enter color preferences
  in the plugin configuration (affecting all charts at once) and each device configuration (affecting devices
  individually.) This should only need to be done once, and will not be needed for new devices.
- Improves multiprocessing logging.

#### v0.4.11
- The following devices have been moved to a multiprocessing environment:
    . Bar Chart Devices
    . Line Chart Devices
    . Polar Chart Devices
    . Scatter Chart Devices
- Adds trap for Matplotlib runtime error when charts are refreshed.

#### v0.4.10
- The following devices have been moved to a multiprocessing environment:
    . Calendar Devices
    . Multiline Text Devices
    . Weather Forecast Devices
- Fixes error in debug logging where 'isError' attribute was used with API 2.0 logging.

#### v0.4.09
- Fixes bug where CSV data are updated once per minute when refresh interval
  set to manual only.
- Ensures that refresh interval is updated as soon as the setting is changed.

#### v0.4.08
- Adds a new Action Item to refresh individual charts. Useful when a single data point changes (i.e., device state or
  variable value).
- Makes the clean_string() method optional for multiline text charts.
- Removes the need to manually refresh the list of values to chart when selecting a data source for multiline text
  charts (removes the 'Refresh' button).
- Updates plugin to require Indigo API version 2.0 (as Indigo 7 is required in order to run the plugin).
- Testing new multiprocessing feature with multiline charts. Should not cause any observable differences in plugin
  operation.
- Plugin now only calls the Matplotlib AGG backend.
- Stylistic changes to Indigo Plugin Update Checker module.
- Improves code used to read and write select information from the plugin logs folder.
- Saving plugin configuration (or advanced settings configuration) will no longer regenerate all charts automatically.
  Feature wasn't working well on slower servers with a lot of charts.
- Further reduces the amount of information written to the debug log.

#### v0.4.04
- Fixes bug in CSV data element validation to eliminate null devices.

#### v0.4.03
- Adds steps-mid and steps-post to line styles.
- Adds plugin menu items to enable and disable communication for all charting devices (includes CSV Engine devices).
- Refactors CSV Engine configuration dialog to pre-populate dropdown menus so data no longer needs to be entered
  manually.
- Adds additional validation checks to CSV Engine device to avoid creation of null devices. Includes maintenance code
  to automatically eliminate null devices that have been previously created.
- Better handling of devices that produced a KeyError on 'customAxisLabelY2'.
- Reduces the amount of default debug logging, and introduces a configuration setting to allow for verbose logging.

#### v0.4.02
- Adds new device type for tracking rcParams.
- Adds optional border around multiline text plots.
- Adds additional option to Mirror Y axis labels to have labels display *only* on Y2.
- Logs warning when CSV Engine data element source ID is None type.
- Properly sets the state of the device indicator in the main Indigo UI (green if enabled, gray if disabled), and
  provides a small set of status messages as the plugin cycles.
- Fixes bug where certain devices with unicode characters in a path name would fail.
- Fixes bug where 'pixel', 'triangle left' and 'triangle right' marker styles would cause an error (scatter charts
  only).
- Minor UI refinements.
- Various code refinements.
- Various error reporting improvements.

#### v0.4.01
- Adds new Scatter chart type.
- Adds baseline API to allow scripters the ability to send data to create charts.
- Adds ability to modify legend labels with custom text (bar, line and scatter charts only).
- Adds ability to mirror Y axis value labels to Y2 (bar, line and scatter charts only).
- Adds ability to hide the X (surrounding) and Y (radial) labels for polar charts.
- Adds advanced settings menu item to force origin lines to be plotted when charts contain both positive and negative
  values.
- Fixes the min/max settings for precipitation values on weather charts.
- Reorganizes most chart device settings (alphabetically within each grouping) to make them easier to find.
- Renames the standard rectangular sizes to increase clarity (they were still too confusing). They are now Size 1 and
  Size 2. Size 1 is the default, Size 2 is the override and Custom Sizes override both Size 1 and Size 2.
- Reduces the minimum size for chart dimensions to 75 pixels.
- Additional fixes for international characters.
- Various code refinements.

#### v0.3.03
- Adds 4, 8, and 12 hour bins to the X axis.
- Substantial additions to the plugin manual.
- Renames "Extra Wide" controls to "Special Size" to better reflect that the settings not only control width and
  height, but can also be smaller or larger than the standard size.
- Fixes bug where certain data file names with unicode characters would cause an error.
- Moves support URL to GitHub.
- Various code refinements.

#### v0.3.02
- Fixes bug in CSV device that caused a crash when Unicode characters were contained in device names.

#### v0.3.01
- Move project to GitHub and increments version number.

#### v0.2.05
- Fixes bug where certain combinations of temperatures would cause below zero temperatures to be plotted outside the
  boundaries of the plot.
- Fixes (?) all instances where the plugin will save a CSV value of 'None' would be saved to the file (changes it to
  'NaN').
- Refines annotations to increase readability -- especially during annotation collisions.
- Refines plotting of 10-Day weather forecast devices to always place higher display priority on high temperature line.
- Simplifies code used to plot max, min and custom line segments (minor speed improvement). Affects bar and line charts.

#### v0.2.04
- Adds dropdown to CSV Engine to show available data sources (device states or variable value).
- Adds device-specific custom font sizes to support retina/non-retina displays.
- Tweaks weather forecast device to increase separation between low temperature line and precipitation bar annotations.
- Fixes bug in Matplotlib Action item.
- CSV Engine: changed "Source Title" to "Title",  changed "Source Device" to "ID", changed "Source State" to "Data" to
  be more descriptive of devices and variable data sources).

#### v0.2.03
- Added additional X Axis bins:
  . Every 15 minutes
  . Every 30 minutes
- Links "About Matplotlib" menu item to the new forum.
- Fixes bug when using variables for Multiline Text.
- Fixes bug in CSV Engine that would not allow the assignment of an 11th data element.

#### v0.2.02
- Implements Indigo Version Update Checker.
- Fixes a bug where the CSV engine spawned a None type data element which kept some installs from creating CSV data
  successfully.
- Attempts to fix a bug where the plugin would randomly restart during a sleep cycle.
- Fixes a bug where plugin would log inability to import pydevd.
- Fixes a bug where custom color values were not recognized as valid for some settings.

