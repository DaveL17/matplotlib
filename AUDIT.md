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

### 3. `plugin.py` is very large (4,145 lines, down from 4,463 at time of audit)
By comparison `chart_tools.py` is 1,138 lines and `validate.py` is now 808 lines
(up from 233, after absorbing `validateDeviceConfigUi`'s validation logic per
finding #5). This matches the project's own `_to_do_list.md` refinement item —
"Move more code out of plugin.py" — so it's a known, tracked issue, not a new
discovery, but it's still the single largest maintainability risk in the codebase
(hard to navigate, hard to test in isolation, one accidental global changes many
chart types).
- **Fix:** no action needed immediately beyond what's already tracked; the
  validation-logic extraction (#5) trimmed ~320 lines. Further reductions would need
  to move other self-contained subsystems (e.g. CSV handling, theme handling) out
  the same way.
