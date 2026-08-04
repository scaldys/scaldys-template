# -*- coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# tksvg needs to be on the disk because it uses os.chdir(os.path.dirname(__file__))
# to load its Tcl extension and pkgIndex.tcl.
# collect_all ensures that the package is collected as data (on disk) 
# rather than being bundled in the PYZ archive.
datas, binaries, hiddenimports = collect_all('tksvg')
