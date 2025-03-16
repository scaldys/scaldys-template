***********
``scaldys``
***********

Scaldys' template for Python projects.

This template is mainly for my own usage, but feel free to try it out or fork it
(https://github.com/scaldys/scaldys-template).


Tools
=====

* Python 3.12 or above
* Documentation written in reStructuredText and built with `Sphinx` using the ReadTheDocs template
* Package management with `uv`
* Tests run with `pytest`


Quickstart
==========

  - Download the code of this project as a Zip-file from GitHub.
  - Uncompress the files, and rename the directory with the name of your new project.
  - Open your project folder using your preferred IDE, and replace the project name in all files (see below).
  - Create a new repository on GitHub, GitLab, or any provider of your choice.
    Upon completion of the repository creation, instructions are shown to initialize a local working directory,
    configure the remote's URL, and commit and push your files to the repository.


What to replace on project setup
--------------------------------

* `scaldys` case-sensitive

  * strings in all files
  * filenames
  * folder names


Publish your project on PyPI
----------------------------

 - `Packaging Python Projects <https://packaging.python.org/en/latest/tutorials/packaging-projects/>`
 - Refer to `trusted publishing examples <https://github.com/astral-sh/trusted-publishing-examples>` for
   a full, self-contained example for trusted publishing with `uv`.
 - If you're just creating a package for learning purposes, you're better off using TestPyPi,
   a separate instance of the Python Package Index that allows you to try distribution tools and processes
   without affecting the real index. Update the `run` step in file `.github/workflows/release.yml`
 - Logging to your account on `PyPI <https://pypi.org/>` or `TestPyPI <https://test.pypi.org/>`, or create
   an account if you don't already have one.
 - Navigate to `Your projects`, then `Publishing`. This will bring you to the `Trusted Publisher Management` page.
 - `Add a new pending publisher` for GitHub. Fill out the project name, owner and repository name associated
   to your project. The workflow name is `release.yml` (same file name as `.github/workflows/release.yml`).
   The `environment name` shall be configured under the repository's settings on GitHub. It is strongly encouraged
   to set up a dedicated publishing environment.


