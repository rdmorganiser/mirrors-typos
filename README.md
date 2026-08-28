# mirrors-typos

Pre-commit mirror of `crate-ci/typos`.

This repository provides immutable release tags for using `typos` with
pre-commit.

## Background

The upstream `typos` repository uses multiple Git tagging conventions,
including the mutable `v1` tag, semantic release tags, and tags belonging to
subpackages.

This can lead to undesirable results with `pre-commit autoupdate`, which may
select a mutable or unrelated upstream tag instead of a specific `typos`
release.

This mirror exposes stable `typos` package releases using immutable tags such
as:

* `v1.49.0`
* `v1.50.0`
* `v1.50.1`

## Hook behavior

The `typos` hook intentionally behaves like the hook provided by
`adhtruong/mirrors-typos`.

Its defaults are:

```yaml
entry: typos
language: python
types: [text]
args:
  - --write-changes
  - --force-exclude
```

This means that `typos` automatically applies unambiguous spelling
corrections.

Repository-specific exclusions and additional configuration should remain in
the consuming repository's `.pre-commit-config.yaml`.

## Usage

Add the mirror to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/rdmorganiser/mirrors-typos
    rev: v1.49.0
    hooks:
      - id: typos
```

No additional `args` are necessary to get the default autofix behavior.

For repositories which freeze pre-commit revisions to commit SHAs, such as
RDMO, update with:

```console
pre-commit autoupdate --freeze
```

This allows pre-commit to discover the latest semantic release tag from this
mirror and then store the corresponding immutable commit SHA in the consuming
repository.

## Architecture

The mirror keeps the release namespace under RDMO control while the `typos`
executable remains a platform-specific PyPI dependency:

```text
PyPI release metadata
        |
        v
scripts/update_mirror.py
        |
        +--> pyproject.toml and .version
        |
        v
commit and vX.Y.Z tag
        |
        v
GitHub Actions atomic push
        |
        v
immutable mirror tag
        |
        v
pre-commit autoupdate --freeze in consuming repositories
```

The updater only reads PyPI metadata; it does not install or execute newly
published `typos` packages. The GitHub Actions workflow creates and pushes
the mirror commits and tags.

## Updating the mirror

The mirror is maintained automatically by the `Update mirror` GitHub Actions
workflow.

The workflow reads the available releases of the `typos` Python package from
PyPI.

For every new stable `X.Y.Z` release after the version recorded in `.version`,
the workflow:

1. updates the pinned `typos` dependency in `pyproject.toml`;
2. updates `.version`;
3. creates a commit named `Mirror: <version>`;
4. creates an immutable `v<version>` Git tag.

For example, updating from `1.49.0` to `1.50.0` creates:

```text
Mirror: 1.50.0
```

and the corresponding tag:

```text
v1.50.0
```

If several versions have been published since the previous workflow run, a
separate commit and tag is created for each version.

The workflow can also be started manually from GitHub Actions.

## What is mirrored?

This repository mirrors the pre-commit integration and release tags.

It does **not** contain or vendor the `typos` executable itself.

Each mirror release instead pins the corresponding `typos` Python package.
For example, tag `v1.49.0` contains:

```toml
dependencies = [
    "typos==1.49.0",
]
```

When pre-commit installs the hook environment, that dependency installs the
appropriate `typos` package for the user's platform.

The mirror therefore provides control over the pre-commit repository and its
immutable release revisions while retaining the same installation mechanism
as `adhtruong/mirrors-typos`.

## Initial setup

The first release tag must be created when the repository is bootstrapped.

For an initial `.version` of:

```text
1.49.0
```

the initial repository commit should also be tagged:

```console
git tag v1.49.0
git push origin main
git push origin v1.49.0
```

After that, the update workflow maintains subsequent releases automatically.

## RDMO migration

In the next RDMO release, replace the upstream repository in
`.pre-commit-config.yaml`:

```diff
- repo: https://github.com/crate-ci/typos
+ repo: https://github.com/rdmorganiser/mirrors-typos
```

Keep RDMO's existing hook exclusions. Then run:

```console
pre-commit autoupdate --freeze
```

This resolves the mirror's latest semantic tag and stores its immutable commit
SHA as the configured revision.

## Upstream projects

This mirror is based on the `typos` project from `crate-ci` and follows the
approach used by `adhtruong/mirrors-typos`.

The mirror infrastructure is maintained by the rdmorganiser community project.
