.. _app_location_guide:

************
App Location
************

``AppLocation`` is the single point of truth for all filesystem paths used by
the application.  It resolves correctly whether the application is running from
the source tree, installed as a package, or frozen into a standalone executable
by PyInstaller.

.. contents:: On this page
   :local:
   :depth: 2


Directory types
===============

``AppLocation.get_directory(dir_type)`` accepts one of three integer constants:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Constant
     - Resolved path
   * - ``AppLocation.AppDir``
     - The directory containing the application's Python package (or the
       directory containing the frozen executable).
   * - ``AppLocation.AppDataDir``
     - The OS-appropriate user data directory (settings, exported data, …).
       See :ref:`os_paths` below.
   * - ``AppLocation.LogDir``
     - ``AppDataDir / "logs"``.  Created on demand by ``setup_logging()``.


Resolution logic
================

The resolution has three modes, checked in order:

1. **Frozen** (``sys.frozen`` is set — PyInstaller executable):
   ``app_path = Path(sys.argv[0]).parent``

2. **Source tree** (``is_running_from_source(app_path)`` is True):
   Both ``"src"`` and the package name appear as components of ``app_path``.
   ``AppDataDir`` is resolved to ``<repo_root>/app_data/`` so development runs
   are self-contained.

3. **Installed package** (neither of the above):
   ``get_os_app_data_path()`` is called to return the OS-specific user
   directory.

.. code-block:: python

    app_path = FROZEN_APP_PATH if is_frozen() else APP_PATH
    if is_running_from_source(app_path):
        app_data_path = app_path.parent.parent.joinpath("app_data")
    else:
        app_data_path = get_os_app_data_path()


.. _os_paths:

OS-specific data paths
======================

When running as an installed package, ``AppDataDir`` is:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Platform
     - Path
   * - Windows
     - ``%LOCALAPPDATA%\<ORGANIZATION_NAME>\<APP_NAME>\``
       (``LOCALAPPDATA`` is read from the environment; raises ``RuntimeError``
       if not set)
   * - macOS
     - ``platformdirs.AppDirs(APP_NAME).user_data_dir``
   * - Linux / other
     - ``$HOME/.<APP_NAME>``
       (``HOME`` is read from the environment; raises ``RuntimeError`` if not
       set)

``APP_NAME``, ``ORGANIZATION_NAME``, and ``PACKAGE_NAME`` are defined in
``src/scaldys_template/__about__.py`` and should be the first things you change when
adapting the template.


Testing with AppLocation
========================

Integration tests that exercise filesystem code must not write to the real
user data directory.  The top-level ``tests/conftest.py`` patches
``AppLocation.get_directory`` to redirect all calls to a pytest ``tmp_path``
fixture:

.. code-block:: python

    @pytest.fixture(autouse=True)
    def tmp_app_location(tmp_path, monkeypatch):
        def fake_get_directory(dir_type=AppLocation.AppDir):
            if dir_type == AppLocation.AppDir:
                return tmp_path / "app"
            elif dir_type == AppLocation.AppDataDir:
                return tmp_path / "app_data"
            elif dir_type == AppLocation.LogDir:
                return tmp_path / "app_data" / "logs"
        monkeypatch.setattr(AppLocation, "get_directory", staticmethod(fake_get_directory))

This fixture is ``autouse=True`` at the top level, so every test — including
integration tests — gets an isolated filesystem.

When writing new tests that need specific directory behaviour, you can override
this fixture locally with a more targeted ``monkeypatch`` call.


Adding a new directory type
============================

To add a new directory constant (e.g., ``CacheDir``):

1. Add the constant to ``AppLocation``:

   .. code-block:: python

       CacheDir = 4

2. Add a branch to ``get_directory()``:

   .. code-block:: python

       elif dir_type == AppLocation.CacheDir:
           path = app_data_path.joinpath("cache")

3. Update the test ``conftest.py`` to return a suitable ``tmp_path``
   sub-directory for the new type.

4. Ensure the directory is created on demand wherever it is first used (follow
   the pattern in ``setup_logging()`` and ``AppSettings._initialize()``).
