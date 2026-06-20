# Scaldys Template

![License](https://img.shields.io/github/license/scaldys/scaldys-template)

A modern Python project template with best practices.

This template provides a solid foundation for Python projects with integrated
testing, documentation, and quality assurance tools. While primarily created for
personal use, it's available for anyone to use or fork on GitHub:
https://github.com/scaldys/scaldys-template

## Features

- Modern Python development with Python 3.13+
- **Tkinter-based GUI** built with `ttkbootstrap` — includes a Signal Analyzer,
  real-time JSON Editor, and a widget showcase (**Windows only**)
- Command-line interface (CLI) built with Typer — global flags (`--log`,
  `--verbose`) resolved once before any subcommand runs
- Application lifecycle entry point (`__main__.py`) covering freeze support,
  crash hooks, signal handlers, asyncio policy, and environment validation
- Reference implementations in `core/` for async processing pipelines
  (`async_processor.py`) and database abstraction (`database.py`)
- Fast dependency management with `uv`
- Comprehensive testing with `pytest`, `pytest-asyncio`, `pytest-mock`, and
  coverage reporting — structured with unit / integration / slow markers
- Code quality verification with `ruff` (linting & formatting) and `pyright`
  (type checking)
- Documentation with reStructuredText and `sphinx` using ReadTheDocs theme
- Windows build infrastructure with `Cython`, `scaldys-project`, and — depending
  on the deployment mode — `PyInstaller`, `Inno Setup`, or wheel-only packaging
- GitHub Actions workflows for CI/CD and PyPI publishing

## Relationship with scaldys-project

This template is designed to work in tandem with
[scaldys-project](https://github.com/scaldys/scaldys-project), a specialized
toolset for managing Python project lifecycles, build pipelines, and
distribution.

`scaldys-template` serves as the **reference example** for all
`scaldys-project` compatible projects. It demonstrates the standard directory
structure, configuration patterns (via `scaldys-project.toml`), and integration
points—such as Cython compilation, Windows installer generation, and automated
documentation builds—that the ecosystem supports.

## Release Notes

For high-level highlights of each release, see [RELEASES.md](./RELEASES.md). For
a technical list of all changes, see the [CHANGELOG](./CHANGELOG).

## Project Structure

```
src/scaldys_template/
├── __main__.py             ← lifecycle entry point (freeze_support, crash hook,
│                             signal handlers, asyncio policy, env validation)
├── cli/
│   ├── cli.py              ← Typer app; owns the single setup_logging() call
│   ├── settings.py         ← AppSettings: persisted log level (INI + Pydantic)
│   └── commands/
│       ├── arg_types.py    ← shared Annotated type definitions
│       ├── cmd_export.py
│       ├── cmd_process.py  ← demonstrates async pipeline + DB connection
│       └── cmd_settings.py
├── common/
│   ├── app_location.py     ← OS-aware path resolution (Windows/macOS/Linux,
│   │                         source vs installed vs frozen)
│   └── logging.py          ← QueueHandler-based JSON logging setup
├── core/
│   ├── export.py
│   ├── async_processor.py  ← async pipeline pattern + sync wrapper
│   └── database.py         ← connection, transaction, pool scaffold
└── tk/
    ├── app.py              ← Main Application (Tkinter)
    └── ui/                 ← GUI frames (Analyzer, Editor, UI Examples)

tests/
├── conftest.py             ← isolated_app_location keystone fixture
├── unit/
│   ├── conftest.py         ← reset_scaldys_template_logger autouse fixture
│   ├── common/             ← mirrors src/scaldys_template/common/
│   ├── cli/                ← mirrors src/scaldys_template/cli/
│   ├── core/               ← mirrors src/scaldys_template/core/
│   └── tk/                 ← mirrors src/scaldys_template/tk/
└── integration/            ← full CLI invocations via CliRunner
```

## Getting Started

### Prerequisites

- Python 3.13 or later
- Git

### Setup

1. **Get the template:**

   ```bash
   # Option 1: Download as ZIP
   # Download from https://github.com/scaldys/scaldys-template/archive/refs/heads/main.zip

   # Option 2: Clone with Git
   git clone https://github.com/scaldys/scaldys-template.git your-project-name
   cd your-project-name
   rm -rf .git
   git init
   ```

2. **Customize the template:**
   - Replace all occurrences of `scaldys_template` / `Scaldys-Template`
     (case-sensitive) with your project name
   - Update file and directory names containing "scaldys_template"
   - Modify package metadata in `pyproject.toml`

3. **Set up your repository:**
   - Create a new repository on GitHub/GitLab
   - Follow their instructions to push your local repository
   - Set up required GitHub environments for trusted publishing

## Development Workflow

### Installation

`uv` will automatically install development dependencies when running a command,
for instance run the tests:

```bash
uv run pytest ./tests
```

While the environment is synced automatically, it may also be explicitly synced
using `uv sync`:

```bash
uv sync --group dev
```

For comprehensive documentation on using `uv`, visit the official documentation:
https://docs.astral.sh/uv/guides/

### Execute the Application

The CLI entry point is `scaldys_template.__main__:main`, which runs lifecycle
setup before handing off to the Typer app. Global options (`--log`, `--verbose`)
must appear **before** the subcommand name:

```bash
# Show help
uv run scaldys-template --help

# Show available commands
uv run scaldys-template --help

# Run the export command with debug logging
uv run scaldys-template --log debug export config.yml

# Run the process command with verbose output
uv run scaldys-template --verbose process --num-tasks 20

# Run via python -m (same lifecycle path)
uv run python -m scaldys_template --log info export config.yml

# Manage the persisted log level
uv run scaldys-template settings log warning
uv run scaldys-template settings          # show current level

# Launch the Tkinter GUI (Windows only)
uv run scaldys-template gui
```

You can also run directly from the source directory:

```bash
# using uv
uv run scaldys-template.py

# using Python directly
python src/scaldys_template.py
```

### Building the Application

You can build distribution packages for your application to share or deploy it.
The build process creates both source distributions (sdist) and binary wheel
distributions.

#### Basic Build

To build the application using `uv`:

```bash
# Build source distribution and wheel
uv build
```

This creates distribution files in the `dist/` directory:

- `scaldys_template-x.y.z.tar.gz` (source distribution)
- `scaldys_template-x.y.z-py3-none-any.whl` (wheel distribution)

#### Build Options

For more control over the build process:

```bash
# Build only the wheel
uv build --wheel

# Build only the source distribution
uv build --sdist

# Clean previous builds first
rm -rf dist/ build/
uv build

# Include development extras in the build
uv build --config-setting="--extras=dev"
```

#### Verify the Build

You can verify your build artifacts before distribution:

```bash
# List contents of the wheel
python -m zipfile -l dist/scaldys_template-*.whl

# Install from the local wheel to test
pip install --force-reinstall dist/scaldys_template-*.whl

# Run a smoke test after installation
scaldys-template --version
```

#### Build for Different Environments

For specific target environments:

```bash
# For a specific Python version
uv build --python-tag py313

# For specific platforms (when using C extensions)
uv build --config-setting="--plat-name=manylinux2014_x86_64"
```

#### Automated Builds

The project includes GitHub Actions workflows that automatically build packages
when you create a new release. See the workflow file at
`.github/workflows/release.yml` for details.

### Windows Packaging (scaldys-project)

This template includes a dedicated Windows build system managed by the
`scaldys-project` CLI command installed by `uv sync`.

**Deployment modes** — controlled by `deployment_mode` in
`scaldys-project.toml`:

| Mode                    | What it builds                                                    | When to use                           |
| ----------------------- | ----------------------------------------------------------------- | ------------------------------------- |
| `pyinstaller` (default) | PyInstaller exe + Inno Setup installer                            | Most applications                     |
| `pyruntime`             | Binary wheel + Inno Setup installer with a managed Python runtime | Apps that coexist with Quarto/Jupyter |
| `wheel_only`            | Binary wheel only, no installer                                   | Apps distributed via pip/uv           |

**Key features:**

- **Cython compilation:** Critical modules are compiled to `.pyd` extensions for
  performance and basic obfuscation.
- **Standalone executable:** (`pyinstaller` mode) Bundles the application into a
  self-contained directory via PyInstaller.
- **Managed Python runtime:** (`pyruntime` mode) Deploys a `uv`-managed virtual
  environment alongside the app, supporting online and offline installer
  variants.
- **Professional installer:** (`pyinstaller` / `pyruntime` modes) Creates a
  Windows setup `.exe` using Inno Setup with desktop shortcuts.
- **Binary wheel:** (all modes) Built from compiled sources and placed in
  `dist/` for users with their own environment.

**Build commands:**

```bash
# Full build: documentation + Windows distribution
scaldys-project build all

# Documentation only
scaldys-project build docs

# Windows distribution only (mode-dependent)
scaldys-project build windows

# Remove build/, dist/ and artifacts/
scaldys-project build clean

# Verify project compliance
scaldys-project check
```

**Prerequisites:**

- **Visual Studio Build Tools:** Required for Cython compilation (all modes).
- **PyInstaller:** Required for `pyinstaller` mode (`uv sync` installs it).
- **Inno Setup:** Required for `pyinstaller` and `pyruntime` modes (must be
  installed separately).

### Code Quality Verification

The project includes automated code quality checks that run when you push
changes to GitHub. These checks are defined in `.github/workflows/release.yml`
and include:

- Building the project with `uv build`
- (Optional) Smoke tests for the wheel and source distribution packages

You can also run quality checks locally before committing:

```bash
# Sync dependencies with lock file
uv sync --group dev

# Run the full test suite
uv run pytest

# Run only fast unit tests (no filesystem or CLI I/O)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Exclude slow tests (async pipeline tests with real latency)
uv run pytest -m "not slow"

# Run tests with coverage report
uv run pytest --cov=src/scaldys_template --cov-report=term-missing

# Lint and check formatting
uv run ruff check ./src

# Format code
uv run ruff format ./src

# Check types
uv run pyright ./src

# Build documentation
uv run sphinx-build docs/user_guide/source docs/_build
```

#### Test markers

| Marker        | What it covers                                                    | Typical run time          |
| ------------- | ----------------------------------------------------------------- | ------------------------- |
| `unit`        | Isolated tests — no real filesystem writes, CLI mocked            | < 1 s                     |
| `integration` | Full CLI invocations via `CliRunner`, real file I/O in `tmp_path` | ~10 s                     |
| `slow`        | Tests that run the real async pipeline with simulated latency     | included in `integration` |

### Publishing to PyPI

This template supports trusted publishing to PyPI using GitHub Actions:

1. Read the Packaging Python Projects guide:
   https://packaging.python.org/en/latest/tutorials/packaging-projects/
2. For trusted publishing details, see uv's trusted publishing examples:
   https://github.com/astral-sh/trusted-publishing-examples
3. For testing purposes, use TestPyPI: modify the `run` step in
   `.github/workflows/release.yml` to use TestPyPI
4. Configure trusted publishing:
   - Log in to PyPI (https://pypi.org/) or TestPyPI (https://test.pypi.org/)
   - Go to "Your projects" → "Publishing" → "Trusted Publisher Management"
   - Click "Add a new pending publisher" and configure:
     - Project name: Your package name
     - Owner: Your GitHub username
     - Repository: Your repository name
     - Workflow name: `release.yml`
     - Environment name: `release` (configure this in your GitHub repository
       settings)

## License

This project template is distributed under the MIT license. See the LICENSE file
for details.
