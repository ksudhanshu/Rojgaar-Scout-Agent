# P0-01 · Create the repo skeleton

| Phase | Effort | Depends on | Status |
|---|---|---|---|
| 0 · Setup & spikes | 0.5 day | — | todo |

## Why
Everything else lands in this repo, so its layout encodes the core design rule: the tool is public, your data is private. A clean `src/` package from day one means `uvx rojgaar-scout` works later without a restructure.

## What to do
- [ ] Create the GitHub repo `Rojgaar-Scout-Agent` with an MIT `LICENSE`.
- [ ] `pyproject.toml` (Python ≥ 3.11, managed with `uv`), package name `rojgaar-scout`, console script `rojgaar = rojgaar.cli:main`.
- [ ] `src/rojgaar/__init__.py`, `src/rojgaar/cli.py` with a `--version` command.
- [ ] `AGENTS.md` stub (canonical instructions for Codex and Muse) and a one-line `CLAUDE.md` containing `@AGENTS.md`.
- [ ] `README.md` with the one-paragraph pitch, "never submits" promise and US-only scope.
- [ ] Empty folders with `.gitkeep`: `schemas/`, `config/`, `.agents/skills/`, `docs/decisions/`, `tests/fixtures/`, `eval/`.
- [ ] `.gitignore` that excludes any `RojgaarScout/` data folder, `.env`, `*.db`.

## Done when
- `uv run rojgaar --version` prints a version.
- `git status` on a fresh clone shows no personal data paths.

## Notes
Repo layout target is in the build plan, section "Repo layout and file formats".
