.. _logging_guide:

*******
Logging
*******

The logging system is designed to be both observable (JSON Lines files that
survive a crash) and unobtrusive (no console noise in normal operation).  This
page explains every part of it.

.. contents:: On this page
   :local:
   :depth: 2


Handler chain
=============

The full handler chain after ``setup_logging()`` is called:

.. code-block:: text

    scaldys_template (package logger)
    │
    ├── queue_handler  ──▶  QueueListener ──▶  file_json
    │                                           (RotatingFileHandler, JSON Lines)
    │
    ├── stdout         ──▶  StreamHandler → sys.stdout
    │                       level: DEBUG (filtered to ≤INFO by NonErrorFilter)
    │
    └── stderr         ──▶  StreamHandler → sys.stderr
                            level: ERROR

    root logger
    └── stderr         ──▶  StreamHandler → sys.stderr
                            level: WARNING

The ``scaldys_template`` logger has ``propagate=False`` so its records do not also
reach the root logger's stderr handler.  This prevents duplicate ERROR output.


JSON Lines file
===============

Log records are written to ``<LogDir>/<package_name>.log.jsonl`` by a
``RotatingFileHandler`` with ``maxBytes=10000`` and ``backupCount=3``.  A
typical record looks like:

.. code-block:: json

    {
      "level": "INFO",
      "message": "Starting async processing pipeline",
      "timestamp": "2025-04-01T14:32:01.123456+00:00",
      "logger": "scaldys_template",
      "module": "async_processor",
      "function": "process_items",
      "line": 257,
      "thread_name": "MainThread",
      "num_items": 100,
      "timeout_per_item": 5.0
    }

The ``num_items`` and ``timeout_per_item`` fields come from the ``extra={}``
dict passed to the logger call — ``JsonFormatter`` automatically includes all
non-built-in ``LogRecord`` attributes in the output.


QueueHandler / QueueListener
=============================

Python 3.12 added ``QueueHandler.listener``, which allows the listener to be
started and stopped through the handler.  The template uses this to:

1. Configure the listener via ``dictConfig`` (no manual instantiation).
2. Retrieve it by name (``logging.getHandlerByName("queue_handler")``) after
   configuration is complete.
3. Start it and register ``atexit`` to stop it cleanly:

.. code-block:: python

    queue_handler = logging.getHandlerByName("queue_handler")
    assert isinstance(queue_handler, QueueHandler)
    queue_listener = queue_handler.listener
    queue_listener.start()
    atexit.register(queue_listener.stop)

This ensures that all log records enqueued before the process exits are flushed
to disk.  If the process is killed with SIGKILL (not interceptable), records
still in the queue will be lost — this is a fundamental limitation of async
logging.


Verbosity control
=================

The ``--verbose`` flag and ``--log`` option interact as follows:

.. list-table::
   :header-rows: 1
   :widths: 20 20 60

   * - ``--log``
     - ``--verbose``
     - Behaviour
   * - (not set)
     - False
     - File: INFO. Console: CRITICAL only (silent in practice).
   * - ``debug``
     - False
     - File: DEBUG. Console: CRITICAL only.
   * - ``debug``
     - True
     - File: DEBUG. Console: DEBUG and INFO to stdout; ERROR+ to stderr.
   * - ``off``
     - False
     - File logging disabled (level set above CRITICAL). Console: silent.
   * - ``off``
     - True
     - File logging disabled. Console: INFO (verbose overrides ``off``).

The ``--log`` flag is resolved in the app callback with a fallback to the
persisted ``AppSettings.log_level``, so a previously saved default applies
even when the user does not pass ``--log`` on the command line.


Pre-init fallback
=================

Before ``setup_logging()`` is called (i.e., before the Typer callback runs),
``__main__.py`` installs a minimal ``basicConfig`` fallback:

.. code-block:: python

    logging.basicConfig(
        level=logging.CRITICAL,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

This ensures that any exception raised during the startup sequence (crash hook,
signal handlers, environment validation) produces visible output on stderr
rather than disappearing silently.  Once ``setup_logging()`` runs, the
``dictConfig`` call replaces this fallback with the full configuration
(``disable_existing_loggers=False`` preserves loggers already acquired before
the call).


Extending the logging system
==============================

**Adding a new handler** (e.g., a remote log aggregator):

1. Add a handler entry under ``"handlers"`` in the ``dictConfig`` dict in
   ``_configure_logging()``.
2. Add the handler name to the ``"handlers"`` list of the ``scaldys_template`` logger
   (or the ``queue_handler`` handlers list if you want async delivery).

**Adding a new formatter**:

Define a class that subclasses ``logging.Formatter`` and override ``format()``.
Register it in the ``"formatters"`` section of ``dictConfig`` using the
``"()"`` factory key.

**Changing the log file location**:

``setup_logging()`` calls ``AppLocation.get_directory(AppLocation.LogDir)``
to resolve the path.  Changing ``AppLocation.LogDir`` resolution affects all
file-based logging.

**Adding structured context to all log records**:

Use a ``logging.Filter`` that injects fields into the ``LogRecord``:

.. code-block:: python

    class AppContextFilter(logging.Filter):
        def filter(self, record):
            record.app_version = VERSION
            return True

Register it as a filter on the ``scaldys_template`` logger or on the ``file_json``
handler.
