# Contributing to ha-myq-garage

## Commit and pull request conventions

This project uses [release-please](https://github.com/googleapis/release-please) for changelogs and version bumps. Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

- `feat:` — new feature (minor bump)
- `fix:` — bug fix (patch bump)
- `docs:`, `chore:`, `test:`, `refactor:` — non-releasing changes
- `feat!:` / `fix!:` — breaking change (major bump)

**Merge strategy:** use **squash-only** merges with a conventional PR title. Disable merge commits and rebase merges on `main`. One conventional commit per merged PR keeps the release-please changelog free of duplicate feature/merge entries.

## Release Please token

Configure a repository secret named `RELEASE_PLEASE_TOKEN` with a narrowly scoped GitHub App installation token (or fine-grained PAT) that can open and update pull requests. Release Please uses this instead of the default `GITHUB_TOKEN` so its release PR updates still trigger the Validate workflow.

Without `RELEASE_PLEASE_TOKEN`, the workflow falls back to `github.token`, which does not start new workflows from events it creates — release commits may then merge without an attached Validate run.

## Test dependencies

Test and tooling dependencies live in `requirements_test.txt` with loose version ranges. Set up a local environment with:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements_test.txt
.venv/bin/pre-commit install
```

CI installs the same way, so no lockfile regeneration step is needed.

Keep the Ruff revision in `.pre-commit-config.yaml` aligned with the `ruff` pin in `requirements_test.txt`.
