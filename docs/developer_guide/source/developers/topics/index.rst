.. _topics:

***************
In-Depth Guides
***************

These guides go beyond the architecture overview to explain each subsystem in
detail.  Use them when you need to understand exactly what a component does,
tune its behaviour, extend it, or troubleshoot an issue.

.. toctree::
   :maxdepth: 2

   project_layout
   markdown_formatting
   logging
   app_location
   settings
   async_processing
   customisation


Guide summaries
===============

:ref:`project_layout`
    The directory structure of the template, what each file is for, and where
    build output is written.

:ref:`markdown_formatting_guide`
    Why ``.prettierrc`` and ``.pre-commit-config.yaml`` exist, how Prettier is
    managed without Node.js, and how the same check runs in GitHub Actions CI.

:ref:`logging_guide`
    How the JSON Lines structured logging system works: the handler chain,
    the QueueHandler / QueueListener pair, the JsonFormatter, verbosity
    control, and how to extend it.

:ref:`app_location_guide`
    How ``AppLocation`` resolves data and log directories across Windows,
    macOS, Linux, source-tree runs, and PyInstaller frozen executables.

:ref:`settings_guide`
    The INI + Pydantic settings stack: file location, validation, adding new
    settings, and the interaction with the ``--log`` CLI flag.

:ref:`async_processing_guide`
    The async pipeline template in depth: batching, per-item timeouts,
    ``return_exceptions`` gather, cooperative shutdown, and the sync wrapper
    boundary.

:ref:`customisation_guide`
    Step-by-step guide to renaming the package, replacing stubs, adding
    commands, and wiring up the Windows distribution pipeline.
