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
* ``scaldys-project`` checked out at ``../scaldys-project``
  if you need to run the full Windows build pipeline.

Clone and install
-----------------

::

    git clone https://github.com/scaldys/scaldys-template.git
    cd scaldys-template
    uv sync --group dev

``uv sync`` creates ``.venv/``, installs the project in editable mode, and
installs all dev-group dependencies (pytest, ruff, pyright, Sphinx, mdformat, etc.).

The ``[tool.uv.sources]`` section in ``pyproject.toml`` points
``scaldys-project`` at the local checkout::

    [tool.uv.sources]
    scaldys-project = { path = "../scaldys-project", editable = true }

Any change to ``scaldys-project`` source is picked up immediately without
reinstalling.


Running the Application
=======================

From the source tree::

    uv run python src/scaldys_template.py --help
    uv run python -m scaldys_template --help

Or via the installed entry point (after ``uv sync``)::

    uv run scaldys-template --help
    uv run scaldys-template --verbose process --num-tasks 5


Running the Tests
=================

Run all tests::

    uv run pytest

Run only fast unit tests::

    uv run pytest -m unit

Run with coverage::

    uv run pytest --cov=src/scaldys_template --cov-report=term-missing

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
    uv lock --check

``ruff`` is configured in ``pyproject.toml`` with ``line-length = 100`` and
``target-version = "py313"``.  The ``uv lock --check`` command ensures the
lock file is in sync with ``pyproject.toml``.  The ``__init__.py`` files are
exempt from ``F403`` (wildcard imports) because re-exporting via ``*`` is
intentional there.

``pyright`` is configured to use the ``.venv`` virtual environment
(``venvPath = "."``; ``venv = ".venv"``).

Markdown files are formatted with `mdformat <https://mdformat.readthedocs.io/>`_.
To check formatting without modifying files::

    uv run mdformat --check README.md

To format Markdown files in place::

    uv run mdformat README.md

See :ref:`markdown_formatting_guide` for details.


Building the Documentation Locally
====================================

Developer guide (this document)::

    uv run sphinx-build -b html docs/developer_guide/source docs/developer_guide/build/html

User guide::

    uv run sphinx-build -b html docs/user_guide/source docs/user_guide/build/html

Or via the convenience wrappers::

    cd docs/developer_guide && make html
    cd docs/user_guide && make html

Or using ``scaldys-project``::

    uv run scaldys-project build docs


Versioning, Building, and Publishing
=====================================

Version is declared once in ``pyproject.toml`` under ``[project] version`` and
read at runtime via ``importlib.metadata`` in ``src/scaldys_template/__about__.py``.
Update ``pyproject.toml`` before tagging a release.

Build a wheel and source distribution::

    uv build

Releases are published to PyPI manually via ``scaldys-project publish``
to ensure only binary wheels with compiled extensions are uploaded.
GitHub Actions and GitLab CI/CD handle only the creation of the
GitHub/GitLab Release and auto-generating/extracting release notes.

For a full walkthrough covering PyPI setup, the GitHub ``release`` environment,
version bumping, tag pushing, and a TestPyPI dry run, see
:ref:`publishing_guide`.


CI/CD Workflows
===============

GitHub Actions and GitLab CI/CD workflows are included:

``ci.yml`` / ``.gitlab-ci.yml``
    Runs on every push and pull request (GitHub) or merge request (GitLab).
    Executes ruff, pyright, and ``pytest``.

``release.yml`` / ``.gitlab/ci/release.yml``
    Triggered by a version tag push (``v*``).  Creates a GitHub/GitLab
    Release with release notes. See :ref:`publishing_guide` for details.

To adapt the workflows to a renamed project, update the ``name`` field in
``pyproject.toml`` and the ``scaldys_template`` references in the workflow files.


Adapting the Template for a New Project
=========================================

The template is designed to be cloned and then renamed.  The minimum set of
changes to make it your own:

1. **Rename the package**: change ``scaldys_template`` to your package name in
   ``pyproject.toml`` (``[project] name``), ``src/scaldys_template/__about__.py``
   (``APP_NAME``, ``PACKAGE_NAME``, ``ORGANIZATION_NAME``), and rename the
   ``src/scaldys_template/`` directory.

2. **Update version**: set the initial ``version`` in ``pyproject.toml``.

3. **Replace stubs**: delete or replace the stub commands in
   ``src/<yourpackage>/cli/commands/`` and the stub implementations in
   ``src/<yourpackage>/core/`` with your actual application logic.

4. **Update documentation**: fill in the user guide under ``docs/user_guide/``
   and this developer guide under ``docs/developer_guide/``.

5. **Update CI workflows**: change the package name references in
   ``.github/workflows/`` and ``.gitlab/ci/`` and verify the release
   configuration.

6. **Configure scaldys-project.toml**: update the ``[cython]`` and ``[windows]``
   sections if you plan to use the scaldys-project Windows distribution
   pipeline.


Reporting Issues
================

Please report bugs and feature requests on the GitHub issue tracker:

https://github.com/scaldys/scaldys-template/issues
