# Project Audit — Matplotlib Indigo Plugin

Date: 2026-09-24
Scope: `matplotlib.indigoPlugin/` (plugin repo), root-level scripts/docs, and the
`tests/` harness. `matplotlib.wiki/` was checked only for repo hygiene, not content.

## Summary

The plugin is functional and reasonably well documented (Google-style docstrings,
type hints are present on most new/refactored code), and the wiki + changelog are
actively maintained. The issues below are mostly hygiene/cleanup items rather than
functional defects — nothing found here blocks day-to-day use.

## Findings

### 3. `plugin.py` is very large (3,472 lines, down from 4,463 at time of audit)
Progress: `plugin.py` has shrunk by ~22% since the audit, via several extractions
(each also noted where relevant above): device-validation logic moved to
`validate.py`, axis-formatting logic consolidated in `chart_tools.py`, dead code
removed (`MakeChart`/`ApiDevice`, ~162 lines — confirmed unused/superseded, not
just movable), and CSV Engine handling (15 methods, ~780 lines) moved to a new
`csv_handling.py` (module-level functions; the `Plugin` methods that Indigo calls
by name — `csv_item_add`, `get_csv_device_list`, etc. — remain as thin delegating
wrappers, since those names are referenced directly from `Actions.xml`/`Devices.xml`
and can't be renamed). Verified with `py_compile`, the full `pytest` suite (55
passed), and specifically confirming the two live-Indigo CSV integration tests
(`test_refresh_csv_device_action`, `test_refresh_csv_source_action`) passed against
a real server, not just skipped.
- **Fix:** still the single largest file in the codebase and still worth further
  reduction (theme handling, ~320 lines, is the next similarly-shaped candidate),
  but no longer the extreme outlier it was at audit time.
