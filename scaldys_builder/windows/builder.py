import logging
import os
from pathlib import Path
from typing import Optional, Any, Union, Iterable
from scaldys_builder.common.base import BaseBuildEnvironment, BaseBuilder
from scaldys_builder.common.docs import DocumentationBuilder
from scaldys_builder.common.utils import (
    safe_empty_dir,
    safe_copy,
    safe_copytree,
    safe_unlink,
    safe_rename,
    safe_rmtree,
)

logger = logging.getLogger(__name__)


class WindowsBuildEnvironment(BaseBuildEnvironment):
    """
    Windows-specific build environment.

    Discovers tools like Inno Setup and PyInstaller, and manages paths
    specific to the Windows build process.
    """

    def __init__(self, project_path: Path, verbose: bool = False) -> None:
        """
        Initialize the Windows build environment.

        Parameters
        ----------
        project_path : Path
            The root directory of the project.
        verbose : bool, default False
            If True, enables verbose output.
        """
        super().__init__(project_path, verbose)

        self.program_files_dir_path = Path(os.getenv("PROGRAMFILES") or "C:\\Program Files")
        self.program_files_x86_dir_path = Path(
            os.getenv("PROGRAMFILES(x86)") or "C:\\Program Files (x86)"
        )

        # Discovery of executables
        self.pyinstaller_exe_path = self._find_tool("pyinstaller.exe", self.python_dir_path)
        self.innosetup_exe_path = self._find_tool(
            "ISCC.exe", self.program_files_x86_dir_path.joinpath("Inno Setup 6")
        )

        # Set up a variety of paths that are used throughout the build process.
        self.script_dir_path = self.project_path.joinpath("scaldys_builder", "windows")
        self.win32_icon_file_path = self.script_dir_path.joinpath(
            f"{self.project_package_name}.ico"
        ).resolve()

        self.src_compiled_dir_path = self.build_dir_path.joinpath("compiled")
        self.examples_dir_path = self.project_path.joinpath("examples")
        self.dist_exe_dir_path = self.dist_dir_path.joinpath("pyinstaller")
        self.dist_setup_dir_path = self.dist_dir_path.joinpath("setup")

    def pre_flight_checks(
        self,
        require_sphinx: bool = False,
        require_pyinstaller: bool = False,
        require_innosetup: bool = False,
    ) -> None:
        """
        Verify that all required tools are available before starting.

        Parameters
        ----------
        require_sphinx : bool, default False
            Whether Sphinx is required.
        require_pyinstaller : bool, default False
            Whether PyInstaller is required.
        require_innosetup : bool, default False
            Whether Inno Setup is required.

        Raises
        ------
        RuntimeError
            If any required tool is missing.
        """
        logger.info("[bold blue]Running pre-flight checks...[/bold blue]")

        missing = []
        if require_sphinx and not self.sphinx_exe_path.exists():
            missing.append(f"Sphinx (sphinx-build.exe) at {self.sphinx_exe_path}")
        if require_pyinstaller and not self.pyinstaller_exe_path.exists():
            missing.append(f"PyInstaller (pyinstaller.exe) at {self.pyinstaller_exe_path}")
        if require_innosetup and not self.innosetup_exe_path.exists():
            missing.append(f"Inno Setup (ISCC.exe) at {self.innosetup_exe_path}")

        if missing:
            logger.error("[bold red]Missing required tools:[/bold red]")
            for item in missing:
                logger.error(f"  - {item}")
            raise RuntimeError("Pre-flight checks failed.")


class Compiler:
    """Handles Cython compilation and PyInstaller bundling on Windows."""

    def __init__(self, env: WindowsBuildEnvironment) -> None:
        """
        Initialize the compiler.

        Parameters
        ----------
        env : WindowsBuildEnvironment
            The Windows build environment.
        """
        self.env = env

    def run_cython(self) -> None:
        """
        Compile Python modules using Cython with a clean staging area.

        Raises
        ------
        RuntimeError
            If the Cython build command fails.
        """
        logger.info("[bold]Running Cython...[/bold]")
        src_path = self.env.src_dir_path
        compiled_path = self.env.src_compiled_dir_path

        # 1. Clean and prepare staging directory
        safe_empty_dir(compiled_path)

        # 2. Run Cython compilation directly from src to compiled
        # We use build_ext --build-lib to place ONLY .pyd files in the staging area.
        cmd = [
            str(self.env.python_exe_path),
            "-P",
            "compile.py",
            "build_ext",
            "--build-lib",
            str(compiled_path),
            "--compiler=msvc",
        ]
        self.env.run_command(cmd, "Error running Cython build", cwd=self.env.project_path)

        # 3. Identify which modules were compiled to .pyd
        # This allows us to avoid copying their .py source files.
        compiled_py_files = set()
        for pyd in compiled_path.rglob("*.pyd"):
            rel_pyd = pyd.relative_to(compiled_path)
            # Extract module name (handles Windows .cp313-win_amd64.pyd suffixes)
            name = rel_pyd.name.split(".")[0]
            py_rel_path = rel_pyd.with_name(f"{name}.py")
            compiled_py_files.add(str(py_rel_path))

        # 4. Copy remaining source files from src to compiled
        # We ignore junk, temp build files, and the .py files of compiled modules.
        def ignore_logic(directory: Union[str, Path], contents: list[str]) -> Iterable[str]:
            ignored = []
            dir_path = Path(directory)
            try:
                rel_dir = dir_path.relative_to(src_path)
            except ValueError:
                return []

            for name in contents:
                full_rel_path = rel_dir.joinpath(name)
                # Ignore common junk and build artifacts
                if name == "__pycache__" or name.endswith(
                    (".pyc", ".pyo", ".c", ".html", ".obj", ".lib", ".exp")
                ):
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

    def run_pyinstaller(self) -> None:
        """
        Run PyInstaller to build an executable.

        Raises
        ------
        RuntimeError
            If the PyInstaller command fails.
        """
        logger.info("[bold]Running PyInstaller...[/bold]")

        entry_point = self.env.src_compiled_dir_path.joinpath(
            f"{self.env.project_package_name}", "__main__.py"
        )
        hooks_dir = self.env.src_compiled_dir_path.joinpath("extra_hooks")

        # Ensure we have a hook file named correctly for PyInstaller to pick it up.
        # We use a generic name in the source to make it reusable across projects.
        if hooks_dir.exists():
            generic_hook = hooks_dir / "hook_package.py"
            if generic_hook.exists():
                target_hook = hooks_dir / f"hook-{self.env.project_package_name}.py"
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
            "--collect-submodules",
            self.env.project_package_name,
            "--noupx",
        ]

        if hooks_dir.exists():
            cmd.extend(["--additional-hooks-dir", str(hooks_dir)])

        if self.env.win32_icon_file_path.exists():
            cmd.extend(["--icon", str(self.env.win32_icon_file_path)])

        cmd.append(str(entry_point))

        self.env.run_command(cmd, "Error running PyInstaller", cwd=self.env.project_path)

        # Post-build: Rename the application directory to 'bin' for a cleaner distribution structure.
        pkg_dir = self.env.dist_exe_dir_path.joinpath(self.env.exe_name)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        if pkg_dir.exists():
            safe_rmtree(bin_dir)
            safe_rename(pkg_dir, bin_dir)

    def build(self) -> None:
        """
        Execute the compilation and bundling pipeline.
        """
        self.run_cython()
        self.run_pyinstaller()


class Packager:
    """Handles distribution preparation and Inno Setup installer creation."""

    def __init__(self, env: WindowsBuildEnvironment) -> None:
        """
        Initialize the packager.

        Parameters
        ----------
        env : WindowsBuildEnvironment
            The Windows build environment.
        """
        self.env = env

    def prepare_examples(self) -> None:
        """
        Copy examples to distribution.

        Notes
        -----
        Expects `examples` directory to exist in the project root.
        """
        if self.env.examples_dir_path.is_dir():
            logger.info("[bold]Copying example files...[/bold]")
            target = self.env.dist_exe_dir_path.joinpath("examples")
            safe_empty_dir(target)
            safe_copytree(self.env.examples_dir_path, target, dirs_exist_ok=True)

    def prepare_windows_files(self) -> None:
        """
        Copy Windows helpers and docs.

        Includes batch scripts, PowerShell scripts, and help files.
        """
        logger.info("[bold]Copying extra files for Windows...[/bold]")
        self.env.dist_exe_dir_path.joinpath("logs").mkdir(parents=True, exist_ok=True)
        bin_dir = self.env.dist_exe_dir_path.joinpath("bin")
        bin_dir.mkdir(parents=True, exist_ok=True)

        for script in [
            f"{self.env.project_package_name}_commandline.bat",
            f"{self.env.project_package_name}_powershell.ps1",
        ]:
            script_path = self.env.script_dir_path.joinpath(script)
            if script_path.exists():
                safe_copy(script_path, bin_dir.joinpath(script))

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

    def run_innosetup(self) -> None:
        """
        Create the installer using Inno Setup.

        Notes
        -----
        Requires `ISCC.exe` to be available.

        Raises
        ------
        RuntimeError
            If the Inno Setup command fails.
        """
        if not self.env.innosetup_exe_path.exists():
            logger.warning("Inno Setup not found. Skipping installer.")
            return

        logger.info("[bold]Running Inno Setup...[/bold]")
        iss_file = self.env.script_dir_path.joinpath(f"{self.env.project_package_name}.iss")
        if not iss_file.exists():
            logger.warning(f"Inno Setup script not found: {iss_file}")
            return

        self.env.dist_setup_dir_path.mkdir(parents=True, exist_ok=True)
        cmd = [
            str(self.env.innosetup_exe_path),
            f"/DMyAppVersion={self.env.version}",
            f"/DSourceDir={self.env.dist_exe_dir_path}",
            f"/O{self.env.dist_setup_dir_path}",
            "/Q",
            str(iss_file),
        ]
        self.env.run_command(cmd, "Error running Inno Setup", cwd=self.env.project_path)

    def build(self) -> None:
        """
        Orchestrate the final packaging process.

        Includes preparing examples, copying Windows-specific files, and
        running Inno Setup.
        """
        self.prepare_examples()
        self.prepare_windows_files()
        self.run_innosetup()


class WindowsBuilder(BaseBuilder):
    """
    Orchestrates the Windows build pipeline.

    This class brings together documentation generation, Cython
    compilation, PyInstaller bundling, and installer creation.
    """

    def __init__(self, project_path: Path, verbose: bool = False) -> None:
        """
        Initialize the Windows builder pipeline.

        Parameters
        ----------
        project_path : Path
            The root directory of the project.
        verbose : bool, default False
            If True, enables verbose output.
        """
        self.env = WindowsBuildEnvironment(project_path, verbose)
        super().__init__(self.env)
        self.doc_builder = DocumentationBuilder(self.env)
        self.compiler = Compiler(self.env)
        self.packager = Packager(self.env)

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

    def clean(self) -> None:
        """
        Clean out files generated by previous builds.

        Specially handles OneDrive environments to avoid sync conflicts.
        """
        target_dirs = [self.env.build_dir_path, self.env.dist_dir_path]

        # Show OneDrive warning only if we are in OneDrive AND at least one directory exists to clean
        if self._is_in_onedrive() and any(p.exists() for p in target_dirs):
            logger.info(
                "[yellow]OneDrive detected: active synchronization may cause the cleaning process to take several minutes. "
                "If it becomes excessively slow, you can manually delete the 'build' and 'dist' directories via File Explorer.[/yellow]"
            )

        super().clean()

    def build_docs(self) -> None:
        """Generate all documentation using the documentation builder."""
        self.doc_builder.build()

    def build_exe(self) -> None:
        """Generate the standalone executable using the compiler."""
        self.compiler.build()

    def build_installer(self) -> None:
        """Generate the setup installer using the packager."""
        self.packager.build()

    def main(self, console: Optional[Any] = None) -> None:
        """
        Run the complete end-to-end Windows build workflow.

        Parameters
        ----------
        console : Console, optional
            A rich console instance for synchronized output.
        """
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

        if console is None:
            from rich.console import Console

            console = Console()

        steps = [
            (
                "Pre-flight checks",
                lambda: self.env.pre_flight_checks(
                    require_sphinx=self.env.docs_dir_path.joinpath("manual").exists(),
                    require_pyinstaller=True,
                    require_innosetup=True,
                ),
            ),
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
            total_task = progress.add_task(
                f"[green]Building {self.env.project_package_name}...", total=len(steps)
            )
            for description, step_func in steps:
                progress.update(total_task, description=f"[cyan]{description}...")
                step_func()
                progress.advance(total_task)
        logger.info("Windows build completed successfully!")
