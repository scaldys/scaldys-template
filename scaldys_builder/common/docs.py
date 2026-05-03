import logging
from scaldys_builder.common.base import BaseBuildEnvironment
from scaldys_builder.common.utils import safe_empty_dir

logger = logging.getLogger(__name__)


class DocumentationBuilder:
    """
    Handles Sphinx documentation generation.

    This builder automates the creation of user guides and developer
    documentation (API docs) using Sphinx.
    """

    def __init__(self, env: BaseBuildEnvironment) -> None:
        """
        Initialize the documentation builder.

        Parameters
        ----------
        env : BaseBuildEnvironment
            The build environment configuration.
        """
        self.env = env

    def build_developer_guide(self) -> None:
        """
        Generate developer documentation using sphinx-apidoc and sphinx-build.

        Notes
        -----
        This process first runs `sphinx-apidoc` to generate RST files from
        the source code, then builds HTML and Single-Page HTML outputs.
        """
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

    def build_user_guide(self) -> None:
        """
        Generate user documentation using sphinx-build.

        Notes
        -----
        Builds both standard HTML and Single-Page HTML outputs from the
        `docs/manual` directory.
        """
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

    def build(self) -> None:
        """
        Orchestrate the documentation build process.

        Assumes required tools are available (verified by pre-flight checks).
        Skips a guide silently only if its source directory does not exist.
        """
        if self.env.user_guide_dir_path.exists():
            self.build_user_guide()
        else:
            logger.warning("User guide not found.")

        if self.env.developer_guide_dir_path.exists():
            self.build_developer_guide()
