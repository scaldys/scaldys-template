.. _markdown_formatting_guide:

*****************************
Markdown Formatting and Tools
*****************************

This page explains how Markdown formatting works in ``scaldys-template``:
why ``mdformat`` is used directly via ``uv``, how target files are scoped
(``README.md``), and what happens at each stage — local commands and GitHub Actions CI.

.. contents:: On this page
   :local:
   :depth: 2


Why mdformat for Markdown?
==========================

Python tools such as Ruff and Pyright handle Python source files, but leave
Markdown untouched.  Markdown files in a project — such as ``README.md`` —
benefit from automated, deterministic formatting:

* **Pure-Python toolchain** — ``mdformat`` is written in Python and runs directly
  via ``uv run mdformat`` without requiring Node.js, npm, or wrapper frameworks
  like ``pre-commit``.
* **CommonMark compliance** — ``mdformat`` enforces standard CommonMark formatting,
  producing clean, predictable Markdown syntax across all platforms.
* **Consistent diffs** — list numbering, code block fences, indentation, and blank
  lines are formatted deterministically.
* **Unified developer experience** — Markdown checking and formatting work with
  the exact same CLI idioms as Ruff and Pyright.


Target File Scoping
===================

By default, Markdown formatting targets the root ``README.md``.

Excluded by default:

* **``RELEASES.md``** — preserved as-is so release notes remain untouched.
* **Other root markdown files and licenses** — license files (``licenses/*.md``)
  and internal notes remain untouched.
* **Sphinx documentation** — Sphinx documentation in ``docs/`` uses
  reStructuredText (``*.rst``) and is checked by ``sphinx-lint``.


Command Summary
===============

.. list-table::
   :header-rows: 1
   :widths: 35 25 15 25

   * - Command
     - Underlying action
     - Rewrites?
     - Exits non-zero on
   * - ``uv run mdformat --check README.md``
     - Markdown format check
     - No
     - Formatting differences
   * - ``uv run mdformat README.md``
     - Markdown format in-place
     - Yes
     - Execution error


Local Workflow
==============

The recommended developer workflow is:

1. Run ``uv run mdformat --check README.md`` to check formatting.
2. If formatting fails, run ``uv run mdformat README.md`` to fix target files in place.
3. Stage and commit the formatted files.


GitHub Actions CI
=================

In GitHub Actions (``.github/workflows/ci.yml``), Markdown formatting is verified
in the ``code_quality`` job step::

    - name: Markdown format check
      run: uv run mdformat --check README.md

Because ``mdformat`` runs with the ``--check`` flag, it will report any
unformatted files and fail the CI job without making modifications on the runner.
