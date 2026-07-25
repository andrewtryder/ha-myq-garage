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

- `requirements_test.txt` — short, unpinned input list
- `requirements_test.lock.txt` — committed lockfile used by required PR CI (current Home Assistant patch)
- `requirements_test.minimum.txt` — overlay pins for the declared minimum Home Assistant version in `hacs.json`
- `requirements_test.minimum.lock.txt` — committed lockfile used by the minimum-version PR CI job

After changing `requirements_test.txt`, regenerate the current lockfile for Linux CI:

```bash
uv pip compile requirements_test.txt -o requirements_test.lock.txt \
  --python-version 3.14.2 --python-platform linux --generate-hashes
```

After changing `requirements_test.minimum.txt` (or whenever the declared minimum Home Assistant version changes), regenerate the minimum lockfile:

```bash
uv pip compile requirements_test.minimum.txt -o requirements_test.minimum.lock.txt \
  --python-version 3.14.2 --python-platform linux --generate-hashes
```

Keep `homeassistant` and `pytest-homeassistant-custom-component` in `requirements_test.minimum.txt` paired: each `pytest-homeassistant-custom-component` release pins exactly one Home Assistant version.

Required PR CI installs with:

- `pip install --require-hashes -r requirements_test.lock.txt` (current)
- `pip install --require-hashes -r requirements_test.minimum.lock.txt` (declared minimum)

Keep the Ruff revision in `.pre-commit-config.yaml` aligned with the locked `ruff` version.

## Test-only dependency vulnerability exceptions

Some transitive packages pinned by Home Assistant (notably `Pillow` and `PyJWT`) may appear in Dependabot alerts even though this integration ships with an empty `manifest.json` `requirements` list. Those packages are installed only for CI/tests and are not distributed to HACS users.

When dismissing such alerts as `tolerable_risk`:

1. Note that the package is test-only and exact-pinned by the locked Home Assistant version.
2. Include an explicit review condition: **recheck whenever `homeassistant==` in `requirements_test.lock.txt` or `requirements_test.minimum.lock.txt` changes**.
3. Re-evaluate the same advisories as part of every Home Assistant / lockfile refresh.
