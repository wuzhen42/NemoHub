import os
from pathlib import Path
from shutil import copy
from distutils.sysconfig import get_python_lib


args = [
    "nuitka",
    "--standalone",
    # "--windows-disable-console",
    "--follow-import-to=app",
    "--plugin-enable=pyside6",
    "--include-qt-plugins=sensible,styles",
    "--msvc=latest",
    "--show-memory",
    "--show-progress",
    "--windows-icon-from-ico=resource/images/logo.ico",
    "--include-module=app",
    "--nofollow-import-to=pywin,pycryptodome",
    "--follow-import-to=win32gui,win32print,qfluentwidgets,app",
    "--output-dir=dist/NemoHub",
    "--company-name=\"GoMore Tech\"",
    "--product-name=NemoPuppet",
    "--file-description=\"visit nemopuppet.com\"",
    "--product-version=1.0.0",
    "--include-data-dir=translations=translations",
    "NemoHub.py",
]
os.system(" ".join(args))

# copy site-packages to dist folder
dist_folder = Path("dist/NemoHub/NemoHub.dist")
site_packages = Path(get_python_lib())

copy("update.bat", dist_folder)
