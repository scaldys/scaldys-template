.. _settings_guide:

********
Settings
********

``AppSettings`` provides a simple, validated, persistent settings store backed
by a standard INI file.  This page explains how it works and how to extend it.

.. contents:: On this page
   :local:
   :depth: 2


Design
======

The settings stack has two layers:

* **``_SettingsModel``** — a Pydantic ``BaseModel`` that validates raw strings
  from the INI file and provides type-safe access.  ``extra="ignore"`` means
  unknown keys in the file are silently discarded (forward compatibility when
  reading a file written by a newer version of the app).

* **``AppSettings``** — owns the INI file path, reads/writes the file via
  ``configparser``, and exposes a clean property API.

The INI file is stored at::

    <AppDataDir>/<package_name>_settings.ini

On a Windows installation this resolves to something like::

    C:\Users\<user>\AppData\Local\Scaldys\Scaldys-Template\scaldys_template_settings.ini


Lifecycle
=========

On construction ``AppSettings.__init__()`` calls ``_initialize()``, which:

1. Creates the settings directory if it does not exist.
2. Writes the settings file with defaults if it does not exist.
3. Reads the file into ``configparser`` and passes the ``DEFAULT`` section as
   a ``dict`` to ``_SettingsModel(**raw)``.
4. If Pydantic raises a ``ValidationError`` (e.g., the file was edited by hand
   and contains an invalid log level), logs a warning and falls back to all
   defaults.  The corrupt file is left on disk so the user can inspect it.


Interaction with ``--log``
==========================

The app callback in ``cli.py`` resolves the effective log level:

.. code-block:: python

    if log_level is None:
        log_level = AppSettings().log_level
    setup_logging(log_level, verbose)

The CLI flag (``--log``) always takes priority over the persisted value.  If
neither is set, ``setup_logging()`` defaults to ``"info"``.

The ``settings set log-level`` command persists the user's preferred default::

    scaldys settings set log-level debug

After this, every subsequent run behaves as if ``--log debug`` was passed,
without the user having to type it.


Adding a new setting
====================

Follow these four steps:

1. **Add the field to ``_SettingsModel``**:

   .. code-block:: python

       class _SettingsModel(BaseModel):
           log_level: _LogLevel = ""
           theme: Literal["light", "dark", ""] = ""   # new field

2. **Add a property to ``AppSettings``**:

   .. code-block:: python

       @property
       def theme(self) -> str | None:
           value = self._model.theme
           return value if value else None

       @theme.setter
       def theme(self, value: str | None) -> None:
           self._model = _SettingsModel(
               log_level=cast(_LogLevel, self._model.log_level),
               theme=cast(..., value or ""),
           )

3. **Include it in ``save()``**:

   .. code-block:: python

       config["DEFAULT"] = {
           "log_level": self._model.log_level,
           "theme": self._model.theme,         # new key
       }

4. **Expose it in ``cmd_settings.py``**:

   Add a sub-command (or extend ``settings set``) so users can change the
   value via the CLI.


File format
===========

The INI file uses ``configparser``'s DEFAULT section.  A typical file after a
``settings set log-level debug`` call looks like::

    [DEFAULT]
    log_level = debug

Empty string values (the "not configured" sentinel) are written as blank::

    [DEFAULT]
    log_level =

``configparser`` reads blank values as empty strings, which the Pydantic
``Literal["off", "debug", ..., ""]`` validator accepts, and the property
getter converts to ``None`` so callers can use a simple ``if`` check.
