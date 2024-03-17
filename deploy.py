import os
from pathlib import Path
from shutil import copy, copytree
from distutils.sysconfig import get_python_lib


# https://blog.csdn.net/qq_25262697/article/details/129302819
# https://www.cnblogs.com/happylee666/articles/16158458.html
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
    "--output-dir=dist/client",
    "client.py",
]
os.system(" ".join(args))

# copy site-packages to dist folder
dist_folder = Path("dist/client/client.dist")
site_packages = Path(get_python_lib())

copy("update.bat", dist_folder)

copied_libs = ["urllib3"]

for src in copied_libs:
    src = site_packages / src
    dist = dist_folder / src.name

    print(f"Coping site-packages `{src}` to `{dist}`")

    if src.is_file():
        copy(src, dist)
    else:
        copytree(src, dist)
