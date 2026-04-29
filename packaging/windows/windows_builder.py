import logging
import os
import shutil
import stat
import sys
import tempfile
import time
import uuid
from pathlib import Path
from subprocess import PIPE, run, CalledProcessError
from typing import Optional

import typer
from rich.console import Console
from rich.markup import escape
from rich.logging import RichHandler
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from scaldys.__about__ import PACKAGE_NAME, VERSION, APP_NAME

# Configure logging
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False, markup=True)],
)
logger = logging.getLogger(__name__)


def get_safe_temp_dir(path: Path) -> Path:
    """Find a temporary directory on the same drive as the path to allow atomic rename."""
    system_temp = Path(tempfile.gettempdir())
    try:
        # Use case-insensitive comparison for drive letters (e.g., 'C:' == 'c:')
        if system_temp.drive.lower() == path.drive.lower():
            return system_temp
    except Exception:
        pass
    return path.parent


def safe_rmtree(path: Path):
    """Safely remove a directory tree, handling read-only files and locks on Windows."""
    if not path.exists():
        return

    was_renamed = False
    # Try to rename the directory first to move it away from any active locks/syncing.
    # Moving it to the system TEMP folder (if on the same drive) is even better as
    # OneDrive won't be watching that location.
    if path.is_dir():
        temp_base = get_safe_temp_dir(path)
        for i in range(5):
            try:
                temp_path = temp_base / f"{path.name}.{uuid.uuid4().hex}.del"
                path.rename(temp_path)
                path = temp_path
                was_renamed = True
                break
            except (PermissionError, OSError):
                # If moving to system TEMP failed, try renaming in-place as a fallback
                if temp_base != path.parent:
                    try:
                        temp_path = path.parent / f"{path.name}.{uuid.uuid4().hex}.del"
                        path.rename(temp_path)
                        path = temp_path
                        was_renamed = True
                        break
                    except (PermissionError, OSError):
                        pass

                if i == 4:
                    # If rename fails after retries, we'll still try to delete the original path
                    logger.debug(f"Failed to rename {path} for deletion, proceeding with original path.")
                    break
                time.sleep(0.1 * (2**i))

    def handle_error(func, path_item, exc):
        """Error handler for shutil.rmtree that retries with backoff."""
        for i in range(10):  # More retries for OneDrive
            try:
                if not os.access(path_item, os.W_OK):
                    try:
                        os.chmod(path_item, stat.S_IWRITE)
                    except OSError:
                        pass
                func(path_item)
                return
            except (PermissionError, OSError):
                if i == 9:
                    raise
                time.sleep(0.1 * (2**i))

    try:
        # Using onexc for Python 3.12+, falling back to onerror for older versions
        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=handle_error)
        else:
            shutil.rmtree(path, onerror=handle_error)
    except Exception as e:
        # Final fallback: use Windows shell 'rd' command which can sometimes succeed where Python fails
        try:
            run(["cmd", "/c", "rd", "/s", "/q", str(path)], check=True, capture_output=True)
        except Exception:
            if was_renamed:
                # If we successfully renamed it, the original path is clear, so we don't need to crash.
                logger.warning(
                    f"Note: Could not fully delete renamed garbage directory {path}: {e}. "
                    "The original path was cleared, so the build will proceed."
                )
            else:
                # If it wasn't renamed and deletion failed, it's a hard error.
                logger.error(f"Failed to remove directory {path}: {e}")
                raise


def safe_unlink(path: Path):
    """Safely unlink a file, handling read-only files and locks on Windows."""
    if not path.exists():
        return
    for i in range(10):  # More retries for OneDrive
        try:
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWRITE)
            path.unlink()
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.warning(f"Failed to remove {path} after retries: {e}")
            else:
                time.sleep(0.1 * (2**i))


def safe_empty_dir(path: Path):
    """Safely empty a directory without deleting the directory itself."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return

    if not path.is_dir():
        safe_unlink(path)
        path.mkdir(parents=True, exist_ok=True)
        return

    logger.debug(f"Emptying directory: {path}")

    # Efficient approach: move the entire directory aside and create a new empty one.
    # This is much faster than iterating over thousands of files, especially on OneDrive,
    # because it performs a single rename operation instead of many deletions.
    temp_base = get_safe_temp_dir(path)
    temp_path = temp_base / f"{path.name}.{uuid.uuid4().hex}.del"

    try:
        path.rename(temp_path)
        path.mkdir(parents=True, exist_ok=True)
        # Now delete the moved contents in the background (functionally)
        # by calling safe_rmtree on the temporary path.
        safe_rmtree(temp_path)
    except (PermissionError, OSError) as e:
        # Fallback to item-by-item if we can't rename the root (e.g. if it's the CWD)
        logger.debug(f"Could not rename root {path} for cleaning: {e}. Falling back to item-by-item.")
        for item in path.iterdir():
            try:
                if item.is_dir():
                    safe_rmtree(item)
                else:
                    safe_unlink(item)
            except Exception as ex:
                logger.warning(f"Could not remove {item} while emptying {path}: {ex}")


def safe_copy(src: Path, dst: Path):
    """Safely copy a file with retries for Windows/OneDrive."""
    for i in range(10):
        try:
            shutil.copy(src, dst)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to copy {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))


def safe_copytree(src: Path, dst: Path, **kwargs):
    """Safely copy a directory tree with retries for Windows/OneDrive."""
    for i in range(10):
        try:
            shutil.copytree(src, dst, **kwargs)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to copy tree {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))


def safe_rename(src: Path, dst: Path):
    """Safely rename a file or directory with retries for Windows/OneDrive."""
    for i in range(10):
        try:
            os.rename(src, dst)
            return
        except (PermissionError, OSError) as e:
            if i == 9:
                logger.error(f"Failed to rename {src} to {dst}: {e}")
                raise
            time.sleep(0.1 * (2**i))


class BuildEnvironment:
    """Handle path discovery, tool location, and command execution."""

    def __init__(self, verbose: bool = False):
        if verbose:
            logger.setLevel(logging.DEBUG)

        self.verbose = verbose
        # Resolve key system and project paths.
        self.script_dir_path = Path(__file__).resolve().parent
        self.project_path = self.script_dir_path.parent.parent.resolve()
        self.project_package_name = PACKAGE_NAME
        self.version = VERSION

        self.python_exe_path = Path(sys.executable)
        self.python_dir_path = self.python_exe_path.parent

        self.program_files_dir_path = Path(os.getenv("PROGRAMFILES") or "C:\\Program Files")
        self.program_files_x86_dir_path = Path(
            os.getenv("PROGRAMFILES(x86)") or "C:\\Program Files (x86)"
        )
        self.exe_name = self.project_package_name

        # Discovery of executables
        self.sphinx_exe_path = self._find_tool("sphinx-build.exe", self.python_dir_path)
        self.sphinx_apidoc_exe_path = self._find_tool("sphinx-apidoc.exe", self.python_dir_path)
        self.pyinstaller_exe_path = self._find_tool("pyinstaller.exe", self.python_dir_path)
        self.innosetup_exe_path = self._find_tool(
            "ISCC.exe", self.program_files_x86_dir_path.joinpath("Inno Setup 6")
        )

        # Set up a variety of paths that are used throughout the build process.
        self.build_dir_path = self.project_path.joinpath("build")
        self.docs_dir_path = self.project_path.joinpath("docs")
        self.src_dir_path = self.project_path.joinpath("src")
        self.src_compiled_dir_path = self.build_dir_path.joinpath("compiled")
        self.examples_dir_path = self.project_path.joinpath("examples")
        self.win32_icon_file_path = self.script_dir_path.joinpath(
            f"{self.project_package_name}.ico"
        ).resolve()

        self.user_guide_dir_path = self.docs_dir_path.joinpath("manual")
        self.user_guide_build_dir_path = self.build_dir_path.joinpath("manual")
        self.developer_guide_dir_path = self.docs_dir_path.joinpath("developer_guide")
        self.developer_guide_build_dir_path = self.build_dir_path.joinpath("developer_guide")
        self.dist_dir_path = self.project_path.joinpath("dist")
        self.dist_bin_dir_path = self.project_path.joinpath("dist_bin")
        self.dist_exe_dir_path = self.project_path.joinpath("dist_exe")
        self.dist_setup_dir_path = self.project_path.joinpath("dist_setup")

    def _find_tool(self, name: str, fallback_path: Path) -> Path:
        """Find a tool in PATH or in a fallback location."""
        tool_path = shutil.which(name)
        if tool_path:
            return Path(tool_path)
        return fallback_path.joinpath(name)

    def run_command(self, cmd: list[str], err_msg: str, cwd: Optional[Path] = None):
        """Run command in subprocess and raise on unexpected exit status."""
        try:
            proc = run(
                cmd,
                stdout=PIPE,
                stderr=PIPE,
                text=True,
                cwd=str(cwd) if cwd is not None else None,
                check=True,
            )
            return proc.stdout or "", proc.stderr or ""
        except CalledProcessError as e:
            logger.error("[bold red]%s[/bold red]", escape(err_msg))
            if e.stdout:
                logger.error("STDOUT:\n%s", escape(e.stdout))
            if e.stderr:
                logger.error("STDERR:\n%s", escape(e.stderr))
            raise RuntimeError(err_msg) from e

    def pre_flight_checks(
        self,
        require_sphinx: bool = False,
        require_pyinstaller: bool = False,
        require_innosetup: bool = False,
    ):
        """Check if required tools are available."""
        logger.info("[bold blue]Running pre-flight checks...[/bold blue]")

        missing = []
        if require_pyinstaller and not self.pyinstaller_exe_path.exists():
            missing.append(f"PyInstaller (expected at: {self.pyinstaller_exe_path})")

        if require_sphinx and not self.sphinx_exe_path.exists():
            missing.append(f"Sphinx (expected at: {self.sphinx_exe_path})")

        if require_innosetup and not self.innosetup_exe_path.exists():
            missing.append(f"Inno Setup (expected at: {self.innosetup_exe_path})")

        if missing:
            logger.error("[bold red]Missing required tools:[/bold red]")
            for item in missing:
                logger.error(f"  - {item}")
            raise RuntimeError("Pre-flight checks failed.")

        if not require_innosetup and not self.innosetup_exe_path.exists():
            logger.warning("Inno Setup (ISCC.exe) not found at %s.", self.innosetup_exe_path)


class DocumentationBuilder:
    """Handles Sphinx documentation generation."""

    def __init__(self, env: BuildEnvironment):
        self.env = env

    def build_developer_guide(self):
        """Generate and build developer documentation with Sphinx."""
        logger.info("[bold]Running Sphinx to generate developer documentation...[/bold]")
        source_dir = str(self.env.src_dir_path)
        output_dir = str(self.env.developer_guide_dir_path.joinpath("source"))

        logger.info("  Running sphinx-apidoc...")
        self.env.run_command(
            [str(self.env.sphinx_apidoc_exe_path), "-f", "-o", output_dir, source_dir],
            "Error running sphinx - sphinx-apidoc",
        )

        safe_empty_dir(self.env.developer_guide_build_dir_path)

        logger.info("  Building html documentation...")
        html_out = str(self.env.developer_guide_build_dir_path.joinpath("html"))
        self.env.run_command(
            [str(self.env.sphinx_exe_path), "-b", "html", output_dir, html_out],
            "Error running Sphinx - make html (developer guide)",
        )

        logger.info("  Building single file html documentation...")
        single_out = str(self.env.developer_guide_build_dir_path.joinpath("singlehtml"))
        self.env.run_command(
            [str(self.env.sphinx_exe_path), "-b", "singlehtml", output_dir, single_out],
            "Error running Sphinx - make singlehtml (developer guide)",
        )

    def build_user_guide(self):
        """Build user guide HTML and single-file HTML outputs."""
        logger.info("[bold]Running Sphinx to generate user documentation...[/bold]")
        safe_empty_dir(self.env.user_guide_build_dir_path)

        source_dir = str(self.env.user_guide_dir_path.joinpath("source"))
        html_out = str(self.env.user_guide_build_dir_path.joinpath("html"))
        logger.info("  Building html documentation (user guide)...")
        self.env.run_command(
            [str(self.env.sphinx_exe_path), "-b", "html", source_dir, html_out],
            "Error running Sphinx - make html (user guide)",
            cwd=self.env.user_guide_dir_path,
        )

        single_out = str(self.env.user_guide_build_dir_path.joinpath("singlehtml"))
        logger.info("  Building single html documentation (user guide)...")
        self.env.run_command(
            [str(self.env.sphinx_exe_path), "-b", "singlehtml", source_dir, single_out],
            "Error running Sphinx - make singlehtml (user guide)",
            cwd=self.env.user_guide_dir_path,
        )

    def build(self):
        """Orchestrate documentation generation."""
        if self.env.sphinx_exe_path.exists():
            if self.env.user_guide_dir_path.exists():
                self.build_user_guide()
            else:
                logger.warning("User guide not found.")
        else:
            logger.warning("Sphinx not found. Documentation skipped.")


class Compiler:
    """Handles Cython compilation and PyInstaller bundling."""

    def __init__(self, env: BuildEnvironment):
        self.env = env

    def run_cython(self):
        """Compile Python modules using Cython with a clean staging area."""
        logger.info("[bold]Running Cython...[/bold]")
        src_path = self.env.src_dir_path
        compiled_path = self.env.src_compiled_dir_path

        # 1. Clean and prepare staging directory
        safe_empty_dir(compiled_path)

        # 2. Run Cython compilation directly from src to compiled
        # We use build_ext --build-lib to place ONLY .pyd files in the staging area.
        cmd = [
            str(self.env.python_exe_path),
            "compile.py",
            "build_ext",
            "--build-lib", str(compiled_path),
            "--compiler=msvc",
        ]
        self.env.run_command(cmd, "Error running Cython build", cwd=self.env.project_path)

        # 3. Identify which modules were compiled to .pyd
        # This allows us to avoid copying their .py source files.
        compiled_py_files = set()
        for pyd in compiled_path.rglob("*.pyd"):
            rel_pyd = pyd.relative_to(compiled_path)
            # Extract module name (handles Windows .cp313-win_amd64.pyd suffixes)
            name = rel_pyd.name.split('.')[0]
            py_rel_path = rel_pyd.with_name(f"{name}.py")
            compiled_py_files.add(str(py_rel_path))

        # 4. Copy remaining source files from src to compiled
        # We ignore junk, temp build files, and the .py files of compiled modules.
        def ignore_logic(directory, contents):
            ignored = []
            dir_path = Path(directory)
            try:
                rel_dir = dir_path.relative_to(src_path)
            except ValueError:
                return []

            for name in contents:
                full_rel_path = rel_dir.joinpath(name)
                # Ignore common junk and build artifacts
                if name == "__pycache__" or name.endswith((".pyc", ".pyo", ".c", ".html", ".obj", ".lib", ".exp")):
                    ignored.append(name)
                # Ignore .py files that are already present as .pyd
                elif str(full_rel_path) in compiled_py_files:
                    ignored.append(name)
            return ignored

        logger.info("  Collecting remaining source files to staging area...")
        safe_copytree(src_path, compiled_path, ignore=ignore_logic, dirs_exist_ok=True)

        # 5. Clean up lingering .c files in src (generated by Cython)
        logger.info("  Cleaning up lingering .c files in src...")
        for c_file in src_path.rglob("*.c"):
            safe_unlink(c_file)

    def run_pyinstaller(self):
        """Run PyInstaller to build an executable."""
        logger.info("[bold]Running PyInstaller...[/bold]")

        entry_point = self.env.src_compiled_dir_path.joinpath(f"{PACKAGE_NAME}", "__main__.py")
        hooks_dir = self.env.src_compiled_dir_path.joinpath("extra_hooks")

        # Ensure we have a hook file named correctly for PyInstaller to pick it up.
        # We use a generic name in the source to make it reusable across projects.
        if hooks_dir.exists():
            generic_hook = hooks_dir / "hook_package.py"
            if generic_hook.exists():
                target_hook = hooks_dir / f"hook-{PACKAGE_NAME}.py"
                safe_rename(generic_hook, target_hook)

        cmd = [
            str(self.env.pyinstaller_exe_path),
            "--noconfirm",
            "--clean",
            "--onedir",
            "--console",
            "--name",
            self.env.exe_name,
            "--paths",
            str(self.env.src_compiled_dir_path),
            "--distpath",
            str(self.env.dist_exe_dir_path),
            "--workpath",
            str(self.env.build_dir_path.joinpath("pyinstaller")),
            "--specpath",
            str(self.env.build_dir_path),
            "--collect-submodules", PACKAGE_NAME,
            "--noupx",
        ]

        if hooks_dir.exists():
            cmd.extend(["--additional-hooks-dir", str(hooks_dir)])

        if self.env.win32_icon_file_path.exists():
            cmd.extend(["--icon", str(self.env.win32_icon_file_path)])

        cmd.append(str(entry_point))

        self.env.run_command(cmd, "Error running PyInstaller", cwd=self.env.project_path)

        pkg_dir = self.env.dist_exe_dir_path.joinpath(self.env.exe_name)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        if pkg_dir.exists():
            safe_rmtree(bin_dir)
            safe_rename(pkg_dir, bin_dir)

    def build(self):
        """Orchestrate executable build."""
        self.run_cython()
        self.run_pyinstaller()


class Packager:
    """Handles distribution preparation and Inno Setup installer creation."""

    def __init__(self, env: BuildEnvironment):
        self.env = env

    def prepare_examples(self):
        """Copy examples to distribution."""
        if self.env.examples_dir_path.is_dir():
            logger.info("[bold]Copying example files...[/bold]")
            dist_examples = self.env.dist_exe_dir_path.joinpath("examples")
            safe_empty_dir(dist_examples)
            safe_copytree(self.env.examples_dir_path, dist_examples, dirs_exist_ok=True)

    def prepare_windows_files(self):
        """Copy Windows helpers and docs."""
        logger.info("[bold]Copying extra files for Windows...[/bold]")
        self.env.dist_exe_dir_path.joinpath("logs").mkdir(parents=True, exist_ok=True)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        bin_dir.mkdir(parents=True, exist_ok=True)

        for script in [f"{PACKAGE_NAME}_commandline.bat", f"{PACKAGE_NAME}_powershell.ps1"]:
            safe_copy(self.env.script_dir_path.joinpath(script), bin_dir.joinpath(script))

        help_src = self.env.user_guide_build_dir_path.joinpath("html")
        if help_src.is_dir():
            dist_doc = self.env.dist_exe_dir_path.joinpath("documentation", "help files")
            safe_empty_dir(dist_doc)
            safe_copytree(help_src, dist_doc, dirs_exist_ok=True)
            for f in ["_sources", "objects.inv", ".buildinfo"]:
                p = dist_doc.joinpath(f)
                if p.is_dir():
                    safe_rmtree(p)
                elif p.exists():
                    safe_unlink(p)

    def run_innosetup(self):
        """Create the installer using Inno Setup."""
        if not self.env.innosetup_exe_path.exists():
            logger.warning("Inno Setup not found. Skipping installer.")
            return

        logger.info("[bold]Running Inno Setup...[/bold]")
        self.env.dist_setup_dir_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.env.innosetup_exe_path),
            f"/DMyAppVersion={self.env.version}",
            f"/DSourceDir={self.env.dist_exe_dir_path}",
            f"/O{self.env.dist_setup_dir_path}",
            "/q",
            str(self.env.script_dir_path.joinpath(f"{PACKAGE_NAME}.iss")),
        ]
        self.env.run_command(cmd, "Error running Inno Setup", cwd=self.env.project_path)

    def build(self):
        """Orchestrate final packaging."""
        self.prepare_examples()
        self.prepare_windows_files()
        self.run_innosetup()


class WindowsBuilder:
    """Orchestrates the Windows build pipeline."""

    def __init__(self, verbose: bool = False):
        self.env = BuildEnvironment(verbose=verbose)
        self.doc_builder = DocumentationBuilder(self.env)
        self.compiler = Compiler(self.env)
        self.packager = Packager(self.env)

    def pre_flight_checks(self, **kwargs):
        """Delegate pre-flight checks to the environment."""
        self.env.pre_flight_checks(**kwargs)

    def build_docs(self):
        """Generate documentation."""
        self.doc_builder.build()

    def build_exe(self):
        """Generate executable."""
        self.compiler.build()

    def build_installer(self):
        """Generate installer."""
        self.packager.build()

    def _is_in_onedrive(self) -> bool:
        """Check if the project is located within a OneDrive-synchronized folder."""
        project_path = self.env.project_path.resolve()
        # Iterate through environment variables to find OneDrive roots
        for key, value in os.environ.items():
            if "onedrive" in key.lower() and value:
                try:
                    onedrive_root = Path(value).resolve()
                    # Check if project path is a subpath of this OneDrive root
                    if project_path.is_relative_to(onedrive_root):
                        return True
                except (ValueError, TypeError, OSError):
                    continue
        return False

    def clean(self):
        """Clean build directories."""
        target_dirs = [
            self.env.build_dir_path,
            self.env.dist_dir_path,
            self.env.dist_bin_dir_path,
            self.env.dist_exe_dir_path,
            self.env.dist_setup_dir_path,
        ]

        # Show OneDrive warning only if we are in OneDrive AND at least one directory exists to clean
        if self._is_in_onedrive() and any(p.exists() for p in target_dirs):
            logger.info(
                "[yellow]OneDrive detected: active synchronization may cause the cleaning process to take several minutes. "
                "If it becomes excessively slow, you can manually delete the 'build' and 'dist*' directories via File Explorer.[/yellow]"
            )

        logger.info("[bold]Cleaning build directories...[/bold]")
        for path in target_dirs:
            safe_empty_dir(path)

        # Clean up lingering .c files in src
        src_path = self.env.project_path.joinpath("src")
        for c_file in src_path.rglob("*.c"):
            safe_unlink(c_file)

    def main(self):
        """Run the end-to-end Windows build workflow."""
        steps = [
            ("Pre-flight checks", lambda: self.pre_flight_checks(
                require_sphinx=self.env.user_guide_dir_path.exists(),
                require_pyinstaller=True,
            )),
            ("Cleaning build directories", self.clean),
            ("Building documentation", self.build_docs),
            ("Building executable", self.build_exe),
            ("Building installer", self.build_installer),
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            total_task = progress.add_task(f"[green]Building {APP_NAME}...", total=len(steps))
            for description, step_func in steps:
                progress.update(total_task, description=f"[cyan]{description}...")
                step_func()
                progress.advance(total_task)

        logger.info("[bold green]Done. Windows build completed successfully![/bold green]")


app = typer.Typer(help=f"{APP_NAME} Windows Build Tool", no_args_is_help=True)
build_app = typer.Typer(help="Build subcommands", no_args_is_help=True)
windows_app = typer.Typer(help="Windows specific build subcommands", no_args_is_help=True)

app.add_typer(build_app, name="build")
build_app.add_typer(windows_app, name="windows")


@windows_app.command("docs")
def windows_docs(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Build Windows documentation."""
    builder = WindowsBuilder(verbose=verbose)
    builder.pre_flight_checks(require_sphinx=True)
    builder.build_docs()


@windows_app.command("exe")
def windows_exe(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Build Windows executables (Cython + PyInstaller)."""
    builder = WindowsBuilder(verbose=verbose)
    builder.pre_flight_checks(require_pyinstaller=True)
    builder.build_exe()


@windows_app.command("installer")
def windows_installer(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Build Windows setup installer."""
    builder = WindowsBuilder(verbose=verbose)
    builder.pre_flight_checks(require_innosetup=True)
    builder.build_installer()


@windows_app.command("all")
def windows_all(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Run the end-to-end Windows build workflow."""
    builder = WindowsBuilder(verbose=verbose)
    builder.main()


@windows_app.command("clean")
def windows_clean(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output."),
):
    """Clean out files generated by previous build."""
    builder = WindowsBuilder(verbose=verbose)
    builder.clean()


if __name__ == "__main__":
    app()
