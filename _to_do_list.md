### TODO 
- x

#### NEW
- Combination device (line/bar to replicate weather devices).
- "Error" chart with min/max/avg
- Floating bar chart
- Generic weather forecast charts to support any weather services and drop support for WU and FW.
- Standard chart types with pre-populated data that link to types of Indigo devices.
- Chart with axes (scales) 3 and 4.  
  [See example](https://matplotlib.org/3.1.1/gallery/ticks_and_spines/multiple_yaxis_with_spines.html)
- Create new STEP chart type as step is no longer a supported line style. 
  [See example](https://matplotlib.org/3.5.1/api/_as_gen/matplotlib.axes.Axes.step.html?highlight=steps%20post)
#### Refinements
- Try to address annotation collisions.
- Allow scripting control or a tool to repopulate color controls so that you can change all bars/lines/scatter etc. in 
  one go.
- Consider adding a leading zero obs when date range limited data is less than the specified date range (so the chart 
  always shows the specified date range.)
- When the number of bars to be plotted is less than the number of bars requested (because there isn't enough data), 
  the bars plot funny.
- Improve reaction when data location is unavailable. Maybe get it out of csv_refresh_process and don't even cycle the 
  plugin when the location is gone.
- Change chart features based on underlying data. (i.e., stock bar chart)
- Move more code out of plugin.py
- Move multiline text font color to theme color
- Move multiline text font size to theme size
- Make sure any existing processes have been closed with communicate(), before starting a new one.  (Too many open 
  files error.)
- Audit style sheet files -- if dev id no longer exists, delete the style sheet.
