.. _overview:

********
Overview
********

``scaldys-template`` is a Python project scaffold aimed at developers starting
a new CLI application.  Rather than an empty repository or a minimal
"hello world", it ships a *working* application with the plumbing already in
place, letting you add domain logic without first solving the surrounding
infrastructure.

.. contents:: On this page
   :local:
   :depth: 2


What the template provides
==========================

The template is organised around six concerns that every serious CLI
application needs to address:

**1. Lifecycle management** (``src/scaldys/__main__.py``)
    A numbered startup sequence — freeze support, pre-init logging, crash hook,
    signal handlers, asyncio policy, environment validation — that runs *before*
    the CLI argument parser touches ``sys.argv``.  The ordering is intentional
    and documented in the module docstring.

**2. Structured, async logging** (``src/scaldys/common/logging.py``)
    JSON Lines log files written through a ``QueueHandler`` so disk I/O never
    blocks the main thread.  ``--log`` and ``--verbose`` flags control the log
    level and whether log output appears on the console.

**3. Cross-platform path resolution** (``src/scaldys/common/app_location.py``)
    A single ``AppLocation`` class that returns the correct ``AppDataDir`` and
    ``LogDir`` on Windows, macOS, and Linux, and switches automatically between
    a source-tree layout and an installed / frozen executable layout.

**4. Persisted settings** (``src/scaldys/cli/settings.py``)
    An INI file backed by Pydantic validation.  ``AppSettings`` reads, writes,
    and validates the settings file on construction; the CLI callback uses it
    to resolve the default log level when ``--log`` is not passed explicitly.

**5. Async processing pipeline** (``src/scaldys/core/async_processor.py``)
    A fully documented template for batched, concurrent async work callable
    from a synchronous Typer command.  Demonstrates per-item timeouts,
    ``return_exceptions=True`` gather, progress callbacks, cooperative shutdown
    via ``_shutdown_event``, and a clean ``asyncio.run()`` wrapper.

**6. Database scaffold** (``src/scaldys/core/database.py``)
    Context-manager connection lifecycle, parameterised query stubs,
    ``@contextmanager`` transaction helper, and a thread-safe semaphore-based
    connection pool — all swappable with a real driver without changing the
    public interface.


Relationship to scaldys-builder
================================

``scaldys-builder`` consumes ``scaldys-template`` projects.  The template
ships with:

* A ``builder.toml`` wiring the Windows build pipeline.
* ``packaging/windows/`` scripts for Inno Setup.
* Sphinx documentation trees (``docs/manual/``, ``docs/developer_guide/``).
* GitHub Actions workflows for CI, PyPI publishing, and releases.

The ``pyproject.toml`` ``[tool.uv.sources]`` section points ``scaldys-builder``
at a local editable checkout during development so the two projects stay in
sync without a PyPI publish cycle.


Who this guide is for
=====================

This developer guide is written for contributors who:

* Maintain the template itself (add features, fix bugs, update dependencies).
* Extend the template with new scaffold patterns for adoption by downstream projects.
* Need to understand a design decision before changing it.

If you are building an application *on top of* the template and want to know
what the template gives you out of the box, read the project's README first,
then return here when you need to go deeper.
