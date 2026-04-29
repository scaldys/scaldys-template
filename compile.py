import os
from setuptools import setup, Extension, find_packages
from setuptools.dist import Distribution
from Cython.Build import cythonize
from Cython.Distutils import build_ext


class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""

    def has_ext_modules(foo):
        return True


# The modules that should be compiled via Cython
COMPILED_MODULES = [
    "scaldys.core.export",
]


def get_extension_modules(source_root):
    extensions = []
    for module in COMPILED_MODULES:
        source_file = os.path.join(source_root, *module.split(".")) + ".py"
        extensions.append(Extension(module, sources=[source_file]))
    return extensions


cmdclass = {"build_ext": build_ext}
distclass = BinaryDistribution

# Default to 'src' if not specified (e.g. when running manually for dev)
# But WindowsBuilder will pass --build-lib to specify output
source_root = "src"
packages = find_packages(source_root)
package_dir = {"": source_root}

setup(
    name="scaldys",
    cmdclass=cmdclass,
    ext_modules=cythonize(get_extension_modules(source_root), annotate=False, language_level="3"),
    package_dir=package_dir,
    packages=packages,
    distclass=distclass,
    entry_points={
        "console_scripts": [
            "scaldys=scaldys.cli.cli:main",
        ],
    },
)
