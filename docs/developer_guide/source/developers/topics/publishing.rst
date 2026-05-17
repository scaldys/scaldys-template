.. _publishing_guide:

*********
Publishing
*********

This guide covers everything needed to publish your project to PyPI using
GitHub Actions with OIDC Trusted Publishing — no API tokens or secrets to
manage.

.. important::
   **This is a template guide.**  Every occurrence of ``scaldys-template``
   (PyPI name, hyphenated) and ``scaldys_template`` (Python package name,
   underscored) below is a placeholder.  Replace them with your own project
   name before following these steps.  ``scaldys-template`` is already
   registered on PyPI and cannot be reused.

.. contents:: On this page
   :local:
   :depth: 2


Overview
========

Releases are triggered by pushing a version tag (e.g. ``v1.0.0``) to GitHub.
The ``release.yml`` workflow then builds the distributions with ``uv build``
and publishes them to PyPI via ``uv publish --trusted-publishing always``.

CI (``ci.yml``) runs on every push and pull request: it lints, type-checks,
and runs the test suite.  A release should only be triggered once CI is green.


Prerequisites
=============

- A `PyPI account <https://pypi.org/account/register/>`_ with 2FA enabled
  (now required by PyPI for publishing)
- The GitHub repository must exist and have GitHub Actions enabled


Step 1 — PyPI Trusted Publishing
=================================

Trusted Publishing lets PyPI verify the identity of a GitHub Actions workflow
using OIDC tokens.  No API token or secret is stored in the repository.

1. Log in to `pypi.org <https://pypi.org>`_ and go to **Your account →
   Publishing** (or visit
   ``https://pypi.org/manage/account/publishing/`` directly).
2. Under **Add a new pending publisher**, fill in:

   ==================== ================================================
   Field                Value
   ==================== ================================================
   PyPI project name    your project name (e.g. ``my-project``)
   Owner                your GitHub username or organisation
   Repository name      your GitHub repository name
   Workflow name        ``release.yml``
   Environment name     ``release``
   ==================== ================================================

3. Click **Add**.  PyPI will accept tokens from that exact workflow/environment
   combination and no other source.

.. note::
   Use ``testpypi`` (``test.pypi.org``) to do a dry run first.  Set up a
   separate pending publisher on Test PyPI with the same fields, and
   temporarily point the workflow at ``--index testpypi``.  See
   :ref:`testpypi_dry_run_template` below.


Step 2 — GitHub Environment
============================

The workflow declares ``environment: release``, which must exist in the
repository settings before the workflow can publish.

1. In the GitHub repository, go to **Settings → Environments → New
   environment**.
2. Name it ``release``.
3. Optionally add a **required reviewer** (deployment protection rule) so that
   a human must approve each publish job before it runs.
4. Save.

The ``id-token: write`` permission in the workflow is what allows GitHub to
mint the OIDC token that PyPI verifies.


Step 3 — Workflow Files
========================

The workflow files are located in the repository under ``.github/workflows/``.

ci.yml
------

Runs on every push and pull request::

    .github/workflows/ci.yml

Jobs:

- **code_quality** — ``ruff check``, ``ruff format --diff``, Prettier,
  ``pyright``
- **test** — ``pytest --cov`` across the matrix
- **build** — ``uv build`` (verifies the package can be built)

release.yml
-----------

Runs when a ``v*`` tag is pushed::

    .github/workflows/release.yml

.. code-block:: yaml

    on:
      push:
        tags:
          - v*

    jobs:
      pypi:
        name: Publish to PyPI
        runs-on: ubuntu-latest
        environment:
          name: release
        permissions:
          id-token: write
        steps:
          - uses: actions/checkout@v4
          - uses: astral-sh/setup-uv@v3
          - name: Build the project
            run: uv build --index-strategy unsafe-best-match
          - name: Publish
            run: uv publish --trusted-publishing always

.. note::
   The template ships with the ``tags:`` trigger commented out and
   ``on: push`` active.  Make sure to uncomment the tag trigger and remove the
   bare ``push`` trigger before the first release, otherwise every push to
   the repository will attempt a publish.


Step 4 — Version Bump
======================

Version is declared once in ``pyproject.toml``::

    [project]
    version = "1.0.0"

It is read at runtime via ``importlib.metadata`` in
``src/<your_package>/__about__.py``.

Before tagging a release:

1. Edit ``pyproject.toml`` and bump ``version``.
2. Update ``CHANGELOG`` with the release notes.
3. Commit both changes::

       git commit -am "Release v1.0.0"


Step 5 — Trigger a Release
============================

Push a version tag to kick off the ``release.yml`` workflow::

    git tag v1.0.0
    git push origin v1.0.0

GitHub Actions will:

1. Check out the repository at the tagged commit.
2. Run ``uv build``, producing ``dist/<your_package>-1.0.0-py3-none-any.whl``
   and ``dist/<your_package>-1.0.0.tar.gz``.
3. Authenticate to PyPI using an OIDC token (no secret needed).
4. Upload both distributions via ``uv publish``.

The package will appear on ``https://pypi.org/project/<your-project>/``
within a minute or two.


.. _testpypi_dry_run_template:

TestPyPI Dry Run
================

Before the first real release it is a good idea to verify the full pipeline
against `Test PyPI <https://test.pypi.org>`_.

1. Create an account on ``test.pypi.org`` and add a pending publisher there
   with the same fields as in :ref:`Step 1 <publishing_guide>` but pointing at
   ``test.pypi.org``.
2. Temporarily change the publish step in ``release.yml``::

       run: uv publish --index testpypi --trusted-publishing always

3. Push a pre-release tag::

       git tag v1.0.0rc1
       git push origin v1.0.0rc1

4. Confirm the package appears on ``https://test.pypi.org/project/<your-project>/``.
5. Revert the workflow change before the real release.
