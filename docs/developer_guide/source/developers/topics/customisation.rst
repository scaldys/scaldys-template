.. _customisation_guide:

*************
Customisation
*************

This guide walks through the steps needed to turn ``scaldys-template`` into
your own project.  It is aimed at developers who have just cloned the template
and need to rename it, add commands, and wire up the distribution pipeline.

.. contents:: On this page
   :local:
   :depth: 2


Step 1 — Rename the package
============================

All project-wide identifiers live in one place:
``src/scaldys/__about__.py``:

.. code-block:: python

    APP_NAME = "Scaldys"         # Human-readable name (shown in ASCII art, help text)
    PACKAGE_NAME = "scaldys"     # Python package name (import name, log file prefix)
    ORGANIZATION_NAME = "Scaldys" # Used in Windows app data path

Change these three strings first.  Everything else — log file name, settings
file name, Windows data path — derives from them at runtime.

Then rename the package directory::

    mv src/scaldys src/<yourpackage>

Update ``pyproject.toml``:

* ``[project] name`` — the distribution name (can differ from PACKAGE_NAME,
  but consistency is conventional).
* ``[project.scripts]`` — the CLI entry point name and module path.
* ``[tool.setuptools.packages.find] include`` — must match your new directory
  name.
* ``[tool.ruff] target-version`` — keep at ``py313`` unless you change the
  Python requirement.

Update any import paths throughout the source and tests:

.. code-block:: text

    # Find all occurrences of the old package name:
    grep -r "from scaldys" src/ tests/
    grep -r "import scaldys" src/ tests/


Step 2 — Set version and metadata
===================================

In ``pyproject.toml``:

.. code-block:: toml

    [project]
    name = "yourpackage"
    version = "0.1.0"
    description = "A short description of your project."
    authors = [{ name="Your Name", email="you@example.com" }]

Version is read at runtime via ``importlib.metadata`` in ``__about__.py``:

.. code-block:: python

    VERSION = version(PACKAGE_NAME)

Do not hard-code the version anywhere else.


Step 3 — Replace the stub commands
=====================================

The template ships three commands as starting points:

* ``export`` — reads a config file and exports data.
* ``process`` — demonstrates the async pipeline.
* ``settings`` — manages persisted settings.

To add your own command:

1. Create ``src/<yourpackage>/cli/commands/cmd_mycommand.py``:

   .. code-block:: python

       # -*- coding: utf-8 -*-
       # cython: language_level=3

       import typer
       from rich.console import Console
       from <yourpackage>.__about__ import PACKAGE_NAME
       import logging

       console = Console()
       logger = logging.getLogger(PACKAGE_NAME)

       __all__ = ["mycommand"]


       def mycommand(ctx: typer.Context) -> None:
           """A short description of what this command does."""
           logger.info("mycommand called")
           console.print("Hello from mycommand!")

2. Register it in ``cli.py``:

   .. code-block:: python

       import <yourpackage>.cli.commands.cmd_mycommand as cmd_mycommand
       ...
       app.command()(cmd_mycommand.mycommand)

3. To add shared arguments, extend ``commands/arg_types.py`` with a new
   ``Annotated`` type alias.

To remove a stub command, delete its module and remove the ``app.command()``
line from ``cli.py``.


Step 4 — Replace the core stubs
=================================

The ``core/`` directory contains three stub implementations:

``export.py``
    Demonstrates a simple synchronous operation.  Replace
    ``export_data()`` with your actual data export logic.

``async_processor.py``
    Replace ``_process_item()`` with your real async I/O operation.
    Keep the signature and the public ``process_items()`` interface.
    See :ref:`async_processing_guide` for details.

``database.py``
    Replace the stub bodies in ``DatabaseConnection.connect()``,
    ``disconnect()``, and ``execute()`` with your real driver calls
    (psycopg, asyncpg, sqlite3, SQLAlchemy, etc.).  The context-manager
    and transaction helper work without modification.

If you do not need a stub, delete its file and remove any import of it.


Step 5 — Update the documentation
====================================

Fill in the user guide at ``docs/user_guide/source/`` and this developer guide
at ``docs/developer_guide/source/``.  At minimum, update:

* ``docs/user_guide/source/index.rst`` — the one-liner description.
* ``docs/developer_guide/source/index.rst`` — the one-liner description.
* ``docs/*/source/authors.rst`` — your name and contact.
* ``docs/*/source/changelog.rst`` — initial version entry.

Both documentation trees use the ``sphinx_rtd_theme``.  To add pages, create
``.rst`` files and list them in the nearest ``.. toctree::`` directive.


Step 6 — Configure the Windows distribution pipeline
======================================================

If you plan to use ``scaldys-builder`` to produce a standalone Windows
executable and installer:

1. Update ``builder.toml``:

   .. code-block:: toml

       [cython]
       compiled_modules = [
           "<yourpackage>.__main__",
           "<yourpackage>.cli.cli",
           "<yourpackage>.cli.commands.cmd_mycommand",
           "<yourpackage>.core.mymodule",
       ]
       source_root = "src"

       [windows]
       script_dir = "packaging/windows"

2. Update ``packaging/windows/`` scripts to use your new package name and
   version placeholders.

3. Verify the build pipeline::

       uv run scaldys-builder check
       uv run scaldys-builder build all


Step 7 — Update CI/CD workflows
=================================

Edit ``.github/workflows/`` to use your package name:

* ``ci.yml`` — update the coverage path (``--cov=<yourpackage>``).
* ``python-publish.yml`` — verify the trusted publishing configuration
  matches your PyPI project name.
* ``release.yml`` — update any name references.


Step 8 — Clean up template artefacts
======================================

Remove or archive files that are specific to the template project:

* ``improvements.md`` — analysis of template improvements (not relevant to
  your project).
* ``ideas.md`` — template design notes.
* ``examples/example.md`` — replace with your own examples.

Update ``README.md`` to describe your project rather than the template.
