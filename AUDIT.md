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

### 5. Known `TODO`/`FIXME` markers still open
Markers found in shipped code, listed for visibility (none newly discovered, but
worth surfacing together):
- `chart_tools.py:517` — axis methods need balancing.
- `plugin.py:696` — possible DLFramework generalization.
- `plugin.py:1101`, `plugin.py:1109` — commented-out alternate save paths, unclear
  if still needed.
- ~~`plugin.py:2903` (`fix_rgb`) — migration note: once complete, the leading `#`
  handling here and a corresponding truncation elsewhere can be removed.~~
  **Resolved after a deep dive:** the premise was wrong, not incomplete. Verified
  directly against matplotlib: `mcolors.to_rgba('FF0000')` raises (Artist color
  kwargs require the `#`), while a `#`-prefixed color written into a `.mplstyle`
  file is silently dropped to the default (`#` starts a comment in that file
  format). `fix_rgb()`'s hash-adding and the Stylesheets writer's hash-stripping
  are a matched pair serving two matplotlib subsystems with opposite `#`
  conventions, not redundant leftovers — doing what the FIXME suggested would
  have broken chart rendering. Replaced the FIXME with comments at both sites
  explaining why each step is required.

## Things checked and found clean
- No hardcoded secrets/API keys/passwords in tracked `.py` files; `tests/.env`
  (which does hold real credentials) is correctly gitignored and not tracked.
- No bare `except:` clauses in `Server Plugin/*.py` or `Charts/*.py`.
- `.gitignore` correctly excludes `.DS_Store`, `__pycache__/`, `.venv/`, `.idea/`,
  `.env`, `.pytest_cache/`; verified none of these are actually tracked.
- `tests/shared` submodule points at the correct upstream
  (`IndigoDomotics/TestingBase`, branch `main`) and is checked out clean.
- `matplotlib.wiki/` is a separate, independent repo as documented in `CLAUDE.md`,
  currently clean (no uncommitted changes), pointed at the correct
  `DaveL17/matplotlib.wiki.git` remote — no cross-repo contamination found.
- Version strings agree between `plugin.py` (`__version__ = "2025.2.5"`) and
  `Info.plist` (`PluginVersion` = `2025.2.5`).
- `LICENSE` is a real MIT file (not a symlink — matches the fix in commit
  `bfb926b`).
- No `requirements.txt`/`Pipfile`/`pyproject.toml`: confirmed intentional, not an
  oversight. Matplotlib, Numpy, and Python are supplied by the Indigo-installed
  Python environment rather than a plugin-managed venv; pinning or vendoring
  alternate versions could conflict with Indigo's bundled versions. Documented in
  `matplotlib.wiki/requirements.md`.
- `pytest tests/` shows **10 failed, 45 passed**; all 10 failures are
  `tests/test_plugin.py::TestPluginActions` live-integration tests that call a real
  Indigo Web Server API and fail with HTTP 400 when no server is reachable — an
  environment precondition, not a code defect. Now documented in `CLAUDE.md`'s
  Testing section.
