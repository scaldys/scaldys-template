# -*- coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# ttkbootstrap contains localized strings and theme data.
# collect_all ensures that the package is collected as data (on disk)
# which is generally safer for Tkinter-based libraries that might
# need to access their resources via filesystem paths.
datas, binaries, hiddenimports = collect_all('ttkbootstrap')
