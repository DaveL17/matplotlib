### Feature Requests

---
#### 2019-01-04  Autolog
I would like to be able to specify a different scale on the Y2 axis - Is this possible, if not can I request another 
feature addition?

My use case is mapping thermostat values; multiple Temperatures and Heat Setpoints. I use the range -5 deg C to 
35 deg C for the Y1 axis. I would like to map the thermostat valve opening value on the Y2 scale from 0% (fully 
closed) to 100% (fully open). I would then be able to easily correlate the valve opening against the temperature.

---
### COMPLETED

---

#### 2019-06-10  jltnol [COMPLETE]
Create charts where the plotted data can be stock values (instead of flow). For
example, a bar chart where each bar is a distinct variable or device state
value.

#### 2019-02-12  RogueProeliator [COMPLETE]
Include a facility to import/export constructed chart devices and have some option to dump the Properties to JSON or 
XML.  Then create a generic import that can read those in... that way you don't have to maintain any particular 
import/export -- it just exports/imports all plugin props it finds on the device and/or XML file during import.

DaveL17 - Device import/export utility added with `v0.8.25`.

#### 2019-05-02  Londonmark  [COMPLETE]
Would it be possible to pull the precipintensity field from Fantastic Weather so we could straightforwardly show the 
amount of precipitation expected hour by hour / day by day?

DaveL17 - Composite Weather Device added with `v0.8.23`.

#### 2019-05-20  norcoscia  [COMPLETE]
Support area charts.

DaveL17 - Area Charts added with `v0.8.18`.

#### 2019-05-01  norcoscia  [COMPLETE]
Add a check for bad paths.

DaveL17 - Check to ensure that the path is valid and reachable (writeable) by the plugin.  Added in 0.8.16.

#### 2019-01-21  Autolog  [COMPLETE]
Another useful feature to add to the mix, especially if you are going to roll-your-own rather than using pandas, would 
be to be able to specify a period on the CSV file. My TRV plugin is creating CSV files for the measurements over the 
last say 24 hours. At times I would like to view the last 3 hours in more detail. The only reasonable way to do this 
at the moment is to create 2 sets of CSV file. If you could specify a period in the chart then that would save having 
to do this. My processing adds an entry to the CSV file for the start of the period (based on the last one dropped 
off) so that graph lines are always generated from the graph origin.

DaveL17 - note that this is a limit on a chart by chart basis and not on the data file. This feature became available 
in `v0.8.15`.

#### 2019-04-05  Sam  [COMPLETE]
In the Line Chart 'device', would it be possible to have 8 lines?

DaveL17 - Implemented with version `0.8.11`.

#### 2019-02-12  Autolog  [COMPLETE]
it would be useful to set the whole bar to red if the battery is zero - so it stands out.

DaveL17 - setting the full bar for zero level devices was a bit of a Pandora's box, so instead the device label will 
be colored with the warning color if highlight dead batteries setting is ticked. `v0.8.03`

#### 2019-02-10  Busta999  [COMPLETE]
Legend extended so it can run all the way across the bottom of the graph - at the moment it wraps to a second line 
even though it is only using the middle half of the graph - if all 6 lines are used and text is too long it wraps 
rather than - see below.

DaveL17 - added in `v0.8.02`. Includes a refactoring of the legend labels so that they wrap by row instead of by column.

#### 2019-02-12  Mat  [PARTIALLY COMPLETE]
Consider automatically updating the chart save path to the latest version of Indigo.

DaveL17 - If a user has saved an image as a static image, it would likely be fine; but if they've saved the image as 
a refreshing image URL, those would likely break. Solution is to send a message to the log that the save location 
looks like it doesn't match the Indigo version (there is some introspection of the save path, so that this only 
happens if the original path is in the Indigo folder tree).  `v0.7.53`

#### 2019-02-12  Autolog  [COMPLETE]
It would be useful to able to specify the text colour when selecting Show Battery Level. At the moment if you select 
a light green colour for the Healthy colour then the white text gets lost.

DaveL17 - annotations feature added to Battery Health devices in `v0.7.45`.

#### 2019-01-21  Autolog  [COMPLETE]
I had incorrectly assumed that if the checkbox for a line wasn't ticked that the line was disabled - it isn't. You 
have to select None for the data source. The main disadvantage of this approach is that you can't temporarily disable a
line without remembering the data item you were trying to graph.

DaveL17 - this feature was added to bar, line and scatter charts in `v0.7.24`.

#### 2018-12-18  Autolog  [COMPLETE]
A minor usability feature request: When you select an item (ID: field), it lists all devices and variables and then 
list is displayed at the bottom of the variable list. This means (in my case) there is an awful lot of scrolling
to do before getting to the devices. It would be useful to be able to select from a device list or variable list.

DaveL17 - this feature was added with build `v0.7.13`.

#### 2018-12-18  Autolog  [COMPLETE]
In the CSV Engine you can specify the number of Observations that you wish to keep in your CSV file.

It would also be useful to able to specify a user specified data retention period (e.g. 24 hours) so that older 
entries get dropped off. This would then make it easy to display graphs for the last 24 hours for example.

DaveL17 - this feature was added with build `v0.7.11`.
