import subprocess
import platform
import os
from urllib.parse import urlparse

import app.config
from app.config import cfg

from qfluentwidgets import qconfig


def call_maya(sentences):

    if not cfg.mayaVersion.value:
        return
    if platform.system() == "Windows":
        mayapy = (
            f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"' if not cfg.mayapyPath.value else cfg.mayapyPath.value
        )
        command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(); {';'.join(sentences)}; standalone.uninitialize()\""
    else:
        mayapy = f"/usr/autodesk/maya{cfg.mayaVersion.value}/bin/mayapy" if not cfg.mayapyPath.value else cfg.mayapyPath.value
        command = [
            mayapy,
            "-c",
            f"from maya import standalone; standalone.initialize(); {';'.join(sentences)}; standalone.uninitialize()",
        ]
    env = os.environ.copy()
    if cfg.nemoModulePath.value:
        env["MAYA_MODULE_PATH"] = os.path.dirname(cfg.nemoModulePath.value) + os.pathsep + env.get("MAYA_MODULE_PATH", "")
    return subprocess.check_output(command, env=env).strip().decode()


def get_license_path():
    return os.path.join(app.config.get_config_dir(), "NemoSeat.lic")


def get_proxies():
    if not qconfig.get(cfg.proxyIsHost) and qconfig.get(cfg.proxyServerAddress):
        URL = (
            f"{qconfig.get(cfg.proxyServerAddress)}:{qconfig.get(cfg.proxyServerPort)}"
        )
        result = urlparse(URL)
        if not result.scheme or not result.netloc:
            print(f"Proxy {URL} invalid! Please check the proxy host or clear your proxy settings.")
        return {"http": URL, "https": URL}
    return dict()
