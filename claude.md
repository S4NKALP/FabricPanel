# Claude Configuration for Tsumiki

## What this repo is

Tsumiki is a modular status bar / panel for Hyprland written using [Fabric](https://github.com/Fabric-Development/fabric) (Python GTK4 widget framework). Main code is Python, with UI widgets under `modules/`, `widgets/`, `shared/`, `services/`, and helpers in `utils/`. Styles live in `styles/`. Docs and site assets live in `docs/`

## Project Structure

- **modules/** — Core UI modules (dock, overview, notification, settings, etc.)
- **services/** — Background services (battery, weather, network, brightness, etc.)
- **widgets/** — Individual widget implementations
- **shared/** — Reusable UI components and mixins
- **styles/** — SCSS stylesheets and theming
- **utils/** — Utility functions, config management, helpers
- **docs/** — Astro-based documentation site
- **tests/** — Test suite
- **assets/** — Static assets (icons, images, i18n, emoji, etc.)

## Key Files

- `main.py` — Entry point
- `pyproject.toml` — Python project metadata
- `config.toml` / `theme.toml` — Configuration examples
- `tsumiki.schema.json` — Configuration schema
- `Justfile` — Task recipes

## Editing rules

- Prefer small, focused changes.
- Do not revert user changes unless explicitly asked.
- Keep style consistent with nearby code.
- Prefer refactors that reduce duplication and nested branching.
- When changing popup, dock, notification, OSD, or settings UI code, check for shared helpers first.
- Use ASCII unless existing file clearly uses Unicode.

## Useful commands

- Start app: `./init.sh -start`
- Setup deps: `./init.sh -setup`
- Install from bootstrap: `./install.sh`
- Generate docs: `python doc_gen.py`
- Freeze deps: `pip freeze > requirements.txt`
- Generate stubs: `fabric-cli gs Glace-0.1 GtkLayerShell-0.1 Playerctl-2.0 NM-1.0`

## Practical notes

- `pyproject.toml` targets Python 3.12 style checks.
- Ruff is enabled; keep imports clean and avoid obvious lint noise.
- Popup-related logic is centralized in `shared/popup.py`.
- Lazy widget loading happens in `modules/bar.py`.
- Settings UI is large and repetitive; prefer generic builders over copy-paste.

## Working with This Codebase

### Before Starting

- Read `README.md` for setup instructions
- Check `CONTRIBUTING.md` for guidelines
- Review `doc.md` for architecture notes
- Run `init.sh` to set up environment

### Running Tasks

Use `Justfile` recipes:
```bash
just --list  # Show available tasks
```

### Testing

Tests are in `tests/` directory:
```bash
python -m pytest tests/
```

### Documentation

Docs are in `docs/` (Astro + pnpm). Build with:
```bash
cd docs && pnpm install && pnpm build
```

## Communication Preferences

- **Be concise** — Respect token budgets; prioritize clarity over elaboration
- **Focus on facts** — Ground answers in code inspection, not assumptions
- **Concrete examples** — Show code snippets rather than descriptions
- **Progressive disclosure** — Start simple, add detail only if needed
- **Challenge assumptions** — Point out issues in plans or designs plainly

## When Reviewing Code

Check against:
1. **Does it follow project conventions?** (structure, naming, patterns)
2. **Does it integrate cleanly?** (minimal coupling, proper separation)
3. **Is it maintainable?** (readable, documented, testable)
4. **Config schema alignment** — Does it respect `tsumiki.schema.json`?

## Tools & Workflows

- Use `pylance` for Python analysis
- Use branch/commit tools for git workflows
- Use `review` skill for PR reviews
- Use `diagnose` skill for bug investigations
- Use `tdd` skill for feature development

## Common Tasks

| Task | Approach |
|------|----------|
| Add new widget | Copy template from `widgets/`, implement in module |
| Add new service | Create in `services/`, register in main |
| Add config option | Update schema, add to `utils/config.py`, update docs |
| Style changes | Edit relevant SCSS, test theme variants |
| Fix UI bug | Check widget state, animator, signal handling |

## Special Notes

- Configuration is hot-reloadable via `utils/config_watcher.py`
- Themes are generated dynamically (see `services/matugen.py`)
- DBus is used for system integration (`utils/dbus_helper.py`)
- Internationalization via JSON files in `assets/i18n/`

## When fixing bugs

- Validate the touched file with existing error checks if available.
- If a change affects shared state, check call sites before editing.
- If a refactor touches UI lifecycle code, watch for stale handlers, duplicate timers, and destroy/cleanup paths.

## Questions to Ask Before Starting

- Is this a feature, bugfix, or refactor?
- Does it affect the public config schema?
- Does it require new tests?
- Is documentation needed (README, docs site, or schema)?


## gi.repository type stubs

`gi.repository` imports lack type checking by default. Stubs are generated via `gengir`. The Fabric wiki has more detail: https://fabric-development.github.io/fabric-wiki/installing-stubs.html
