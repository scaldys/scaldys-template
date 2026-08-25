.. _publishing_guide:

**********
Publishing
**********

This guide explains how to publish a project derived from this template to
PyPI.  Because the template uses Cython-compiled extensions, the release
process is intentionally manual: the binary wheel is built locally with
``scaldys-project build all`` and uploaded with ``scaldys-project publish``.
GitHub Actions and GitLab CI/CD handle only CI quality gates, documentation deployment, and Release creation.

.. important::
   **This is a template guide.**  Every occurrence of ``scaldys-template``
   (PyPI name, hyphenated) and ``scaldys_template`` (Python package name,
   underscored) below is a placeholder.  Replace them with your own project
   name before following these steps.  ``scaldys-template`` is already
   registered on PyPI and cannot be reused.

.. contents:: On this page
   :local:
   :depth: 2


Why manual publishing?
======================

Projects derived from this template compile one or more Python modules with
Cython (configured via the ``[cython]`` section of ``scaldys-project.toml``).  The
compiled ``.pyd``/``.so`` extensions replace the original ``.py`` sources in
the distributed wheel, which is the mechanism that prevents casual inspection
of the implementation.

An automated CI workflow running ``uv build`` on a Linux runner would produce
a *pure-Python* source distribution — essentially a zip file with all ``.py``
sources intact.  Uploading that to PyPI defeats the purpose of compilation
entirely.

The alternative — building a binary wheel inside CI — would require
reproducing the full ``scaldys-project build`` pipeline (MSVC compiler,
Cython, PyInstaller, Sphinx) on a GitHub Actions runner.  This would add
significant CI complexity with no benefit: the correct binary wheel is already
produced locally as part of the normal development cycle.

Manual publishing is therefore the safe and straightforward choice:

- The binary wheel from ``scaldys-project build all`` is the only artifact
  uploaded to PyPI.
- No compiled source code is ever exposed.
- No OIDC configuration or CI secrets are required for PyPI.


Overview
========

Release workflow at a glance::

    scaldys-project build all           # 1. compile + package
    scaldys-project publish             # 2. upload binary wheel to PyPI
    git tag v1.0.0 && git push origin v1.0.0 # 3. trigger Release and Pages documentation deployment

CI (``ci.yml``) runs on every push and pull request: lint, format check, type
checking, and tests across platforms.  The build and publish steps are
deliberately absent — the binary wheel can only be produced by the local
pipeline.


Prerequisites
=============

- A `PyPI account <https://pypi.org/account/register/>`_ with 2FA enabled
  (now required by PyPI for publishing)
- A PyPI API token for your project (see Step 1)
- ``scaldys-project build all`` has been run and ``dist/`` contains a binary
  wheel


Step 1 — PyPI API Token
========================

``scaldys-project publish`` calls ``uv publish`` locally.  Authentication
uses a PyPI API token:

1. Log in to `pypi.org <https://pypi.org>`_ and go to **Account settings →
   API tokens → Add API token**.
2. For the first upload, use an account-scoped token (the project does not
   exist yet on PyPI, so a project-scoped token cannot be created).  Restrict
   it to the specific project on subsequent releases.
3. Copy the token — it is shown only once.

Pass the token to the publish command via an environment variable.

On Unix (bash/zsh)::

    UV_PUBLISH_TOKEN=pypi-... scaldys-project publish

On Windows (PowerShell)::

    $env:UV_PUBLISH_TOKEN = "pypi-..."; scaldys-project publish

For permanent configuration see the `uv authentication documentation
<https://docs.astral.sh/uv/guides/publish/#authentication>`_.

.. note::
   No OIDC Trusted Publishing setup is required.  The token is used locally
   only and is never stored in the repository or CI environment.


Step 2 — Build the Binary Wheel
================================

Run the full build from the project root::

    scaldys-project build all

This compiles the Cython extensions, assembles the binary wheel, builds
documentation, and produces the Windows installer.  The wheel is written to
``dist/``::

    dist/<your_package>-1.0.0-cp313-cp313-win_amd64.whl

The platform tag (``win_amd64``, not ``none-any``) confirms this is a binary
wheel with compiled extensions.


Step 3 — Publish to PyPI
=========================

From the project root::

    scaldys-project publish

The command validates the contents of ``dist/`` before uploading:

- Exits with an error if ``dist/`` is missing or contains no wheels.
- Refuses to publish a pure-Python wheel (platform tag ``none-any``) to
  prevent accidental source code exposure.
- Refuses to publish if multiple binary wheels are found — run
  ``scaldys-project build clean`` then ``scaldys-project build all`` to
  produce a clean build.
- Calls ``uv publish <wheel>`` on the validated binary wheel.

To publish to TestPyPI first (recommended for first-time setup)::

    scaldys-project publish --test


Step 4 — Version Bump and Tag
==============================

Version is declared once in ``pyproject.toml``::

    [project]
    version = "1.0.0"

Before a release:

1. Edit ``pyproject.toml`` and bump ``version``.
2. Update ``CHANGELOG`` with the release notes.
3. Commit::

       git commit -am "Release v1.0.0"

4. Run Steps 2 and 3 above to build and publish the wheel.
5. Push a version tag to trigger the GitHub/GitLab Release and Pages documentation deployment::

       git tag v1.0.0
       git push origin v1.0.0

The tag push creates a GitHub/GitLab Release with auto-generated notes from the
commit history (or extracted from ``RELEASES.md`` on GitLab), and deploys the
User Guide to GitHub Pages or GitLab Pages.  PyPI has already been updated in the
previous step.


Workflow files
==============

ci.yml / .gitlab-ci.yml
-----------------------

GitHub Actions (``ci.yml``) and GitLab CI/CD (``.gitlab-ci.yml``) run on every
push and pull request (GitHub) or merge request (GitLab)::

    .github/workflows/ci.yml
    .gitlab/ci/code_quality.yml
    .gitlab/ci/test.yml

Jobs:

- **code_quality** — ``ruff check``, ``ruff format --diff`` (on GitHub), mdformat,
  ``pyright``, and lock file check.
- **test** — ``pytest --cov`` on Ubuntu, macOS, and Windows (GitHub only).

No build or publish step is present in CI.  The binary wheel requires the local
``scaldys-project`` pipeline and cannot be reproduced in CI.

release.yml / .gitlab/ci/release.yml
------------------------------------

Runs when a ``v*`` tag is pushed::

    .github/workflows/release.yml
    .gitlab/ci/release.yml

.. code-block:: yaml

    # GitHub
    on:
      push:
        tags:
          - v*
    jobs:
      github_release:
        name: Create GitHub Release
        runs-on: ubuntu-latest
        permissions:
          contents: write
        steps:
          - uses: actions/checkout@v4
          - name: Create release
            env:
              GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
            run: |
              gh release create "${{ github.ref_name }}" \
                --title "${{ github.ref_name }}" \
                --generate-notes

.. code-block:: yaml

    # GitLab
    release:
      rules:
        - if: $CI_COMMIT_TAG =~ /^v/

These workflows create a GitHub/GitLab Release with release notes.
They do **not** build or publish to PyPI.

docs.yml / .gitlab/ci/pages.yml
-------------------------------

Runs when a ``v*`` tag is pushed or triggered manually (``workflow_dispatch`` on
GitHub Actions or ``web`` on GitLab CI/CD)::

    .github/workflows/docs.yml
    .gitlab/ci/pages.yml

Jobs:

- **deploy-docs** (GitHub Actions) — builds the User Guide (``docs/user_guide/source``)
  with Sphinx into ``build/user_guide/html``, packages the artifact, and deploys it to
  GitHub Pages.
- **pages** (GitLab CI/CD) — builds the User Guide into ``build/user_guide/html``,
  moves the output into the reserved ``public/`` directory, and automatically publishes it
  to GitLab Pages.


.. _testpypi_dry_run_template:

TestPyPI Dry Run
================

Before the first real release it is good practice to verify the full pipeline
against `Test PyPI <https://test.pypi.org>`_.

1. Create an account on ``test.pypi.org`` and generate an API token there.
2. Set ``UV_PUBLISH_TOKEN`` to the TestPyPI token.
3. Run::

       scaldys-project publish --test

4. Confirm the package appears on
   ``https://test.pypi.org/project/<your-project>/``.
5. Revert ``UV_PUBLISH_TOKEN`` to the real PyPI token before the actual
   release.
