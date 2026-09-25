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

### 3. `plugin.py` is very large (2,797 lines, down from 4,463 at time of audit)
Progress: `plugin.py` has shrunk by ~37% since the audit, via several extractions
(each also noted where relevant above): device-validation logic moved to
`validate.py`; axis-formatting logic consolidated in `chart_tools.py`; dead code
removed (`MakeChart`/`ApiDevice`, ~162 lines — confirmed unused/superseded, not
just movable); CSV Engine handling (15 methods, ~780 lines) moved to
`csv_handling.py`; Theme Manager handling (8 methods, ~320 lines) moved to
`theme_handling.py`; 12 config-dialog list-generator methods (~400 lines) moved to
a new `ui_lists.py`; 5 startup/maintenance audit methods (~195 lines) moved to a
new `audits.py`; and `fix_rgb`/`format_markers` (~50 lines) moved to a new
`color_utils.py` — deliberately *not* `chart_tools.py`, since that module parses
`sys.argv[1]` as a chart payload at import time (safe only for the chart_*.py
subprocess scripts it's meant for; importing it from `plugin.py`'s own process
risked a crash against the plugin process's unrelated argv).

In every extraction, module-level functions take explicit `logger`/`prefs`/etc.
params (or a passed-in callable for genuine `indigo.PluginBase` framework methods
like `self.sleep`/`self.getDeviceConfigUiXml`, which aren't defined anywhere in
this codebase). `Plugin` methods Indigo calls by exact name (`csv_item_add`,
`themeManagerCloseUi`, `getFileList`, etc. — referenced directly from
`Actions.xml`/`Devices.xml`/`MenuItems.xml`/`PluginConfig.xml`) remain as thin
delegating wrappers, since those names can't be renamed. Methods not referenced
anywhere except internally (`theme_rename`, `theme_save`, `theme_delete`, all 5
audit methods, `fix_rgb`, `format_markers`) were deleted from `plugin.py` entirely
and their callers updated to call the new modules directly, rather than left as
unused wrappers.

Found and fixed one real, pre-existing bug while verifying the audit-methods move:
`audit_device_props()` iterated over `props` (a dict) while deleting keys from it
in the same loop (`for key in props: ... del props[key]`) — a mutate-during-iterate
bug that raises `RuntimeError` against a plain dict whenever there's an obsolete
prop to remove, silently defeating that half of the audit. Fixed by iterating
`list(props)` instead; caught by a standalone smoke test, not the existing suite.

Verified with `py_compile` throughout; the full `pytest` suite (55 passed
consistently); confirming the relevant live-Indigo integration tests
(CSV, theme-apply, and all three chart-refresh actions — the latter exercising
`color_utils`/`audits` through the real `charts_refresh()` path) passed against a
real server rather than being skipped; and — since most of these ~35 moved methods
have no test coverage at all — standalone smoke tests covering every function in
`theme_handling.py`, `ui_lists.py`, and `audits.py` directly against a mocked
`indigo` module.
- **Fix:** still the largest file in the codebase, but the remaining bulk
  (`charts_refresh()` alone is ~800 lines) is the core chart-orchestration engine,
  not a contained subsystem — it calls `self.substitute` (genuine Indigo
  variable-substitution framework coupling) plus a dozen+ sibling methods, so
  extracting it would thread that coupling through a new module for no real
  reduction in complexity. Deliberately left in place rather than extracted.
