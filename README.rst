****************
Scaldys Template
****************

.. image:: https://img.shields.io/github/license/scaldys/scaldys-template
   :alt: License
   :target: https://github.com/scaldys/scaldys-template/blob/main/LICENSE

A modern Python project template with best practices.

This template provides a solid foundation for Python projects with integrated testing, documentation,
and quality assurance tools. While primarily created for personal use, it's available for anyone to use or
fork on GitHub: https://github.com/scaldys/scaldys-template


Features
========

* Modern Python development with Python 3.12+
* Command-line interface (CLI) built with Typer for intuitive and feature-rich applications
* Fast dependency management with ``uv``
* Comprehensive testing with ``pytest`` and coverage reporting
* Code quality verification with ``ruff`` (linting & formatting) and ``pyright`` (type checking)
* Documentation with reStructuredText and ``sphinx`` using ReadTheDocs theme
* GitHub Actions workflows for CI/CD and PyPI publishing


Getting Started
===============

Prerequisites
-------------

* Python 3.12 or later
* Git

Setup
-----

1. **Get the template:**

   .. code-block:: bash

      # Option 1: Download as ZIP
      # Download from https://github.com/scaldys/scaldys-template/archive/refs/heads/main.zip

      # Option 2: Clone with Git
      git clone https://github.com/scaldys/scaldys-template.git your-project-name
      cd your-project-name
      rm -rf .git
      git init

2. **Customize the template:**

   * Replace all occurrences of ``scaldys`` (case-sensitive) with your project name
   * Update file and directory names containing "scaldys"
   * Modify package metadata in ``pyproject.toml``

3. **Set up your repository:**

   * Create a new repository on GitHub/GitLab
   * Follow their instructions to push your local repository
   * Set up required GitHub environments for trusted publishing


Development Workflow
====================

Installation
------------

``uv`` will automatically install development dependencies when running a command, for instance run the tests.

.. code-block:: bash

   uv run pytest ./tests

While the environment is synced automatically, it may also be explicitly synced using ``uv sync``:

.. code-block:: bash

   uv sync

For comprehensive documentation on using ``uv``, visit the official documentation: https://docs.astral.sh/uv/guides/ .


Execute the Application
-----------------------

Execute the application with the following command:

.. code-block:: bash

   uv run ./src/scaldys.py

or from within the source directory :

.. code-block:: bash

   # using uv
   uv run scaldys.py

   # using Python directly
   python scaldys.py


Building the Application
------------------------

You can build distribution packages for your application to share or deploy it.
The build process creates both source distributions (sdist) and binary wheel distributions.

Basic Build
~~~~~~~~~~~

To build the application using ``uv``:

.. code-block:: bash

   # Build source distribution and wheel
   uv build

This creates distribution files in the ``dist/`` directory:
- ``scaldys-x.y.z.tar.gz`` (source distribution)
- ``scaldys-x.y.z-py3-none-any.whl`` (wheel distribution)


Build Options
~~~~~~~~~~~~~

For more control over the build process:

.. code-block:: bash

   # Build only the wheel
   uv build --wheel

   # Build only the source distribution
   uv build --sdist

   # Clean previous builds first
   rm -rf dist/ build/
   uv build

   # Include development extras in the build
   uv build --config-setting="--extras=dev"


Verify the Build
~~~~~~~~~~~~~~~~

You can verify your build artifacts before distribution:

.. code-block:: bash

   # List contents of the wheel
   python -m zipfile -l dist/scaldys-*.whl

   # Install from the local wheel to test
   pip install --force-reinstall dist/scaldys-*.whl

   # Run a smoke test after installation
   scaldys --version


Build for Different Environments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For specific target environments:

.. code-block:: bash

   # For a specific Python version
   uv build --python-tag py312

   # For specific platforms (when using C extensions)
   uv build --config-setting="--plat-name=manylinux2014_x86_64"


Automated Builds
~~~~~~~~~~~~~~~~

The project includes GitHub Actions workflows that automatically build packages when you create a new release.
See the workflow file at ``.github/workflows/release.yml`` for details.


Code Quality Verification
-------------------------

The project includes automated code quality checks that run when you push changes to GitHub.
These checks are defined in ``.github/workflows/release.yml`` and include:

* Building the project with ``uv build``
* (Optional) Smoke tests for the wheel and source distribution packages

You can also run quality checks locally before committing:

.. code-block:: bash

   # Sync dependencies with lock file
   uv sync

   # Run tests
   uv run pytest

   # Run tests
   uv run pytest

   # Check test coverage
   uv run coverage run -m pytest

   # Lint and check formatting
   uv run ruff check ./src

   # Format code
   uv run ruff format ./src

   # Check types
   uv run pyright ./src

   # Build documentation
   uv run sphinx-build docs docs/_build


Publishing to PyPI
------------------

This template supports trusted publishing to PyPI using GitHub Actions:

1. Read the Packaging Python Projects guide: https://packaging.python.org/en/latest/tutorials/packaging-projects/
2. For trusted publishing details, see uv's trusted publishing examples: https://github.com/astral-sh/trusted-publishing-examples
3. For testing purposes, use TestPyPI: modify the ``run`` step in ``.github/workflows/release.yml`` to use TestPyPI
4. Configure trusted publishing:

   * Log in to PyPI (https://pypi.org/) or TestPyPI (https://test.pypi.org/)
   * Go to "Your projects" → "Publishing" → "Trusted Publisher Management"
   * Click "Add a new pending publisher" and configure:
     * Project name: Your package name
     * Owner: Your GitHub username
     * Repository: Your repository name
     * Workflow name: ``release.yml``
     * Environment name: ``release`` (configure this in your GitHub repository settings)


License
=======

This project template is distributed under the MIT license. See the LICENSE file for details.
