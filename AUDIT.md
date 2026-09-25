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

### 3. `plugin.py` is very large (3,240 lines, down from 4,463 at time of audit)
Progress: `plugin.py` has shrunk by ~27% since the audit, via several extractions
(each also noted where relevant above): device-validation logic moved to
`validate.py`, axis-formatting logic consolidated in `chart_tools.py`, dead code
removed (`MakeChart`/`ApiDevice`, ~162 lines — confirmed unused/superseded, not
just movable), CSV Engine handling (15 methods, ~780 lines) moved to
`csv_handling.py`, and Theme Manager handling (8 methods, ~320 lines) moved to a
new `theme_handling.py`. In both extractions, module-level functions take explicit
`logger`/`prefs` params; `Plugin` methods Indigo calls by exact name (`csv_item_add`,
`themeManagerCloseUi`, etc. — referenced directly from `Actions.xml`/`Devices.xml`/
`MenuItems.xml`) remain as thin delegating wrappers, since those names can't be
renamed. Three theme methods (`theme_rename`, `theme_save`, `theme_delete`) weren't
referenced anywhere except internally, so they were deleted from `plugin.py`
entirely rather than left as unused wrappers. Verified with `py_compile`, the full
`pytest` suite (55 passed, including confirming the three live-Indigo CSV/theme
integration tests passed against a real server rather than being skipped), and —
since 7 of the 8 theme methods have no test coverage at all — standalone smoke
tests covering every `theme_handling.py` function and validation branch directly.
- **Fix:** still the single largest file in the codebase and still worth further
  reduction, but no longer the extreme outlier it was at audit time.
