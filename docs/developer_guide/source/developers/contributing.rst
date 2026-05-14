.. _contributing:

************
Contributing
************

This guide covers setting up a development environment for working on
``scaldys-template`` itself: cloning, testing, linting, building
documentation, and publishing.

.. contents:: On this page
   :local:
   :depth: 2


Development Setup
=================

Prerequisites
-------------

* Python 3.13 (enforced by ``.python-version`` and ``pyproject.toml``).
* `uv <https://docs.astral.sh/uv/>`_ — used for all virtual-environment and
  dependency management.
* Node.js / npm — only needed to run ``prettier`` for Markdown formatting
  (optional, not required for Python development).
* ``scaldys-builder`` checked out at ``../scaldys-builder`` (sibling directory)
  if you need to run the full Windows build pipeline.

Clone and install
-----------------

::

    git clone https://github.com/scaldys/scaldys-template.git
    cd scaldys-template
    uv sync --group dev

``uv sync`` creates ``.venv/``, installs the project in editable mode, and
installs all dev-group dependencies (pytest, ruff, pyright, Sphinx, etc.).

The ``[tool.uv.sources]`` section in ``pyproject.toml`` points
``scaldys-builder`` at the sibling checkout::

    [tool.uv.sources]
    scaldys-builder = { path = "../scaldys-builder", editable = true }

Any change to ``scaldys-builder`` source is picked up immediately without
reinstalling.


Running the Application
=======================

From the source tree::

    uv run python src/scaldys.py --help
    uv run python -m scaldys --help

Or via the installed entry point (after ``uv sync``)::

    uv run scaldys --help
    uv run scaldys --verbose process --num-tasks 5


Running the Tests
=================

Run all tests::

    uv run pytest

Run only fast unit tests::

    uv run pytest -m unit

Run with coverage::

    uv run pytest --cov=scaldys --cov-report=term-missing

Run excluding slow tests::

    uv run pytest -m "not slow"

The test suite uses three pytest markers:

``unit``
    Fast, isolated tests with no filesystem or network I/O.

``integration``
    Tests that touch the filesystem or invoke the full CLI via
    ``typer.testing.CliRunner``.

``slow``
    Tests with simulated latency (e.g., async pipeline tests using real
    ``asyncio.sleep``).  These are excluded from fast CI runs but included
    in the full suite.


Linting and Type Checking
=========================

::

    uv run ruff check src tests
    uv run ruff format src tests
    uv run pyright

``ruff`` is configured in ``pyproject.toml`` with ``line-length = 100`` and
``target-version = "py313"``.  The ``__init__.py`` files are exempt from
``F403`` (wildcard imports) because re-exporting via ``*`` is intentional
there.

``pyright`` is configured to use the ``.venv`` virtual environment
(``venvPath = "."``; ``venv = ".venv"``).

To format Markdown files (requires Node.js)::

    npx prettier --write "**/*.md"


Pre-commit Hooks
================

The project ships a pre-commit configuration.  Install the hooks once::

    uv run pre-commit install

The hooks run ruff, pyright, and prettier automatically on every commit,
catching issues before they reach CI.


Building the Documentation Locally
====================================

Developer guide (this document)::

    uv run sphinx-build -b html docs/developer_guide/source docs/developer_guide/build/html

User guide::

    uv run sphinx-build -b html docs/user_guide/source docs/user_guide/build/html

Or via the convenience wrappers::

    cd docs/developer_guide && make html
    cd docs/user_guide && make html

Or using ``scaldys-builder``::

    uv run scaldys-builder build windows docs


Versioning, Building, and Publishing
=====================================

Version is declared once in ``pyproject.toml`` under ``[project] version`` and
read at runtime via ``importlib.metadata`` in ``src/scaldys/__about__.py``.
Update ``pyproject.toml`` before tagging a release.

Build a wheel and source distribution::

    uv build

Publish to PyPI (requires a configured API token or trusted publishing via
GitHub Actions)::

    uv publish

The ``python-publish.yml`` workflow in ``.github/workflows/`` publishes
automatically when a version tag (``v*``) is pushed.  To test against TestPyPI
first, uncomment the ``[[tool.uv.index]]`` block in ``pyproject.toml`` and
run::

    uv publish --index testpypi


CI/CD Workflows
================

Three GitHub Actions workflows are included:

``ci.yml``
    Runs on every push and pull request.  Executes ruff, pyright, and
    ``pytest``.

``python-publish.yml``
    Triggered by a version tag push (``v*``).  Builds the wheel and publishes
    to PyPI using OIDC trusted publishing (no stored secrets required).

``release.yml``
    Creates a GitHub Release and attaches the built wheel and source
    distribution as release assets.

To adapt the workflows to a renamed project, update the ``name`` field in
``pyproject.toml`` and the ``scaldys`` references in the workflow files.


Adapting the Template for a New Project
=========================================

The template is designed to be cloned and then renamed.  The minimum set of
changes to make it your own:

1. **Rename the package**: change ``scaldys`` to your package name in
   ``pyproject.toml`` (``[project] name``), ``src/scaldys/__about__.py``
   (``APP_NAME``, ``PACKAGE_NAME``, ``ORGANIZATION_NAME``), and rename the
   ``src/scaldys/`` directory.

2. **Update version**: set the initial ``version`` in ``pyproject.toml``.

3. **Replace stubs**: delete or replace the stub commands in
   ``src/<yourpackage>/cli/commands/`` and the stub implementations in
   ``src/<yourpackage>/core/`` with your actual application logic.

4. **Update documentation**: fill in the user guide under ``docs/user_guide/``
   and this developer guide under ``docs/developer_guide/``.

5. **Update CI workflows**: change the package name references in
   ``.github/workflows/`` and verify the PyPI publishing configuration.

6. **Configure builder.toml**: update the ``[cython]`` and ``[windows]``
   sections if you plan to use the scaldys-builder Windows distribution
   pipeline.


Reporting Issues
================

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-template/issues
