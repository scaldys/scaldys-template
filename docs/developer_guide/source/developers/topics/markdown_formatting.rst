.. _markdown_formatting_guide:

*****************************
Markdown Formatting and Hooks
*****************************

This page explains the role of ``.prettierrc``, ``.pre-commit-config.yaml``,
and how the two work together with the GitHub Actions CI pipeline to enforce
consistent Markdown formatting across the project.

.. contents:: On this page
   :local:
   :depth: 2


Why Prettier for Markdown?
==========================

Python tooling (ruff, pyright) handles Python source files, but leaves
Markdown untouched.  Markdown files in this project — ``README.md``,
``licenses/*.md``, and documentation pages — benefit from the same kind of
automated, deterministic formatting:

* **Consistent line wrapping** — long paragraphs are reflowed to a fixed print
  width, making diffs easier to read and review.
* **Uniform blank lines and spacing** — heading separators, list indentation,
  and fenced code blocks are normalised automatically.
* **No manual style debates** — the formatter decides; contributors follow.

`Prettier <https://prettier.io/>`_ is the de-facto standard formatter for
Markdown.  It is managed here through the ``pre-commit`` framework so that
Node.js does **not** need to be installed by contributors — pre-commit
downloads and isolates Prettier automatically.


``.prettierrc``
===============

.. code-block:: json

    {
      "printWidth": 80,
      "proseWrap": "always",
      "endOfLine": "auto"
    }

``printWidth: 80``
    Paragraphs are reflowed so that no line exceeds 80 characters.

``proseWrap: "always"``
    Prettier actively wraps prose to ``printWidth``.  Without this option
    Prettier would leave existing long lines untouched.

``endOfLine: "auto"``
    Prettier preserves whatever line endings are already in the file rather
    than enforcing LF.  This prevents a conflict with Git's ``core.autocrlf``
    setting on Windows: without ``"auto"``, Prettier would rewrite CRLF files
    to LF, Git would convert them back to CRLF, and every commit would
    trigger a spurious "files were modified by this hook" failure.


``.pre-commit-config.yaml``
===========================

.. code-block:: yaml

    repos:
      - repo: https://github.com/rbubley/mirrors-prettier
        rev: v3.8.3
        hooks:
          - id: prettier
            types_or: [markdown]

**Why** ``rbubley/mirrors-prettier`` **instead of the official mirror?**
The official ``pre-commit/mirrors-prettier`` repository is archived and its
last release is an alpha.  ``rbubley/mirrors-prettier`` is the actively
maintained community fork that tracks Prettier stable releases.

**How it works**
    The first time the hook runs, pre-commit downloads the pinned Prettier
    version into its own isolated cache (``~/.cache/pre-commit/``).
    No global ``npm install`` or Node.js setup is required.

**``types_or: [markdown]``**
    Restricts the hook to Markdown files only.  Python, RST, TOML, and all
    other file types are left to their respective tools (ruff, sphinx-build,
    etc.).

To install the git hook after cloning::

    uv run pre-commit install

To run Prettier manually on all Markdown files at any time::

    uv run pre-commit run prettier --all-files


Integration with GitHub Actions CI
===================================

The ``ci.yml`` workflow runs the same Prettier check on every push and pull
request::

    - name: Prettier format
      run: uv run pre-commit run prettier --all-files

Using ``uv run pre-commit`` in CI (rather than ``npx prettier`` directly)
guarantees that CI and local development use the **exact same tool, version,
and configuration**.  Specifically:

* The Prettier version is pinned in ``.pre-commit-config.yaml`` (``rev:
  v3.8.3``) and is identical in both environments.
* The ``.prettierrc`` options (``printWidth``, ``proseWrap``, ``endOfLine``)
  are respected in both environments.
* No Node.js or npm setup step is needed in the workflow.

If CI reports formatting failures, fix them locally and commit::

    uv run pre-commit run prettier --all-files
    git add -p
    git commit
