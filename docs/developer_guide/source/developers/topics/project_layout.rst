.. _project_layout:

**************
Project Layout
**************

This page describes every directory and file in the template and explains
what it is for.

.. contents:: On this page
   :local:
   :depth: 2


Repository root
===============

.. code-block:: text

    scaldys-template/
    ├── .claude/                # Claude Code local settings
    ├── .github/workflows/      # CI/CD GitHub Actions workflows
    ├── .junie/                 # Junie AI assistant memory (not tracked in output)
    ├── docs/
    │   ├── developer_guide/    # This documentation (Sphinx)
    │   └── user_guide/         # User-facing documentation (Sphinx)
    ├── examples/               # Usage examples (Markdown)
    ├── licenses/               # Third-party dependency licence files
    ├── packaging/windows/      # Inno Setup scripts for the Windows installer
    ├── src/                    # All Python source code
    ├── tests/                  # Pytest test suite
    ├── .gitignore
    ├── .prettierrc             # Prettier config for Markdown formatting
    ├── .python-version         # Python version constraint (>=3.13,<3.14)
    ├── builder.toml            # scaldys-builder pipeline configuration
    ├── package.json            # Node.js dependency for prettier
    ├── pyproject.toml          # Project metadata, dependencies, tool config
    └── README.md               # Project overview and quick-start


Source tree (``src/``)
======================

.. code-block:: text

    src/
    ├── scaldys_template.py          # Convenience alias: `python src/scaldys_template.py`
    └── scaldys_template/
        ├── __about__.py        # APP_NAME, PACKAGE_NAME, ORGANIZATION_NAME, VERSION
        ├── __init__.py         # Re-exports: from scaldys_template.cli import *; from scaldys_template.common import *
        ├── __main__.py         # Application lifecycle entry point
        ├── py.typed            # PEP 561 marker — package ships inline types
        ├── cli/
        │   ├── __init__.py
        │   ├── cli.py          # Typer app, HeaderGroup, app callback (setup_logging)
        │   ├── settings.py     # AppSettings — INI persistence + Pydantic validation
        │   └── commands/
        │       ├── __init__.py
        │       ├── arg_types.py        # Shared Annotated type aliases
        │       ├── cmd_export.py       # export command
        │       ├── cmd_process.py      # process command (async pipeline demo)
        │       └── cmd_settings.py     # settings sub-app
        ├── common/
        │   ├── __init__.py
        │   ├── app_location.py # AppLocation, is_frozen(), get_os_app_data_path()
        │   └── logging.py      # setup_logging(), JsonFormatter, NonErrorFilter
        └── core/
            ├── __init__.py
            ├── async_processor.py  # process_items() — async pipeline template
            ├── database.py         # DatabaseConnection, ConnectionPool, transaction()
            └── export.py           # export_data() — data serialisation stub

``src/scaldys_template.py`` is a one-liner (``from scaldys_template.cli.cli import app``) that
makes ``python src/scaldys_template.py`` work without installing the package.  It is
not part of the installed distribution.


Test tree (``tests/``)
======================

.. code-block:: text

    tests/
    ├── conftest.py             # Top-level fixtures: tmp_app_location patch
    ├── unit/
    │   ├── conftest.py         # reset_scaldys_template_logger fixture
    │   ├── common/             # Tests for common/
    │   ├── cli/                # Tests for cli/
    │   └── core/               # Tests for core/
    └── integration/            # Full-CLI tests via typer.testing.CliRunner

The top-level ``conftest.py`` patches ``AppLocation`` to redirect all
filesystem operations into a pytest ``tmp_path`` directory, so tests never
touch the developer's real user data directory.  See
:ref:`architecture` for details.


Documentation tree (``docs/``)
================================

Both documentation trees follow the same Sphinx layout:

.. code-block:: text

    docs/<tree>/
    ├── Makefile / make.bat     # Convenience wrappers for sphinx-build
    └── source/
        ├── conf.py             # Sphinx configuration
        ├── index.rst           # Master file / table of contents
        ├── authors.rst
        ├── changelog.rst
        ├── license.rst
        ├── help.rst
        ├── <section>/          # Section-specific pages
        │   └── topics/         # In-depth guide pages
        ├── _static/            # Static assets (CSS, images)
        └── _templates/         # Jinja2 template overrides

Build output is written to ``docs/<tree>/build/html/`` (excluded from git by
``.gitignore``).


Build output locations
======================

When ``scaldys-builder`` runs the Windows distribution pipeline, it writes:

.. code-block:: text

    build/
    ├── compiled/       # Staged source tree (Cython pre-compilation)
    └── <docs-name>/    # Sphinx HTML output per documentation unit

    dist/
        scaldys_template-x.y.z-cp313-cp313-win_amd64.whl   # Binary distribution wheel

    artifacts/
    ├── portable/       # Staged distribution tree (pyinstaller/pyruntime modes)
    ├── installer/      # Windows installer (pyinstaller/pyruntime modes)
    └── documentation/  # Standalone documentation copy (if public_doc_dirs is set)

All build directories are excluded from git and cleaned by
``scaldys-builder build clean``.


Configuration files
===================

``pyproject.toml``
    Single source of truth for:

    * Project metadata (name, version, authors, description, classifiers).
    * Runtime dependencies.
    * Dev dependencies (``[dependency-groups] dev``).
    * Tool configuration: ``[tool.ruff]``, ``[tool.pyright]``,
      ``[tool.pytest.ini_options]``, ``[tool.uv.sources]``.
    * Build system (setuptools).
    * Entry point: ``scaldys-template = "scaldys_template.__main__:main"``.

``builder.toml``
    Configuration for the ``scaldys-builder`` pipeline:

    * ``[cython]`` — list of modules to compile and the source root.
    * ``[windows]`` — path to the Inno Setup script directory.

``.python-version``
    Pins the Python version for ``uv``; currently ``>=3.13,<3.14``.

``.prettierrc``
    Prettier configuration for Markdown: ``printWidth: 80``,
    ``proseWrap: "always"``.
