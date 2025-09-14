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
            f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"'
        )
        command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(); {';'.join(sentences)}; standalone.uninitialize()\""
    else:
        mayapy = f"/usr/autodesk/maya{cfg.mayaVersion.value}/bin/mayapy"
        command = [
            mayapy,
            "-c",
            f"from maya import standalone; standalone.initialize(); {';'.join(sentences)}; standalone.uninitialize()",
        ]
    return subprocess.check_output(command).strip().decode()


def get_license_path():
    return os.path.join(app.config.get_config_dir(), "NemoSeat.lic")


def get_proxies():
    if qconfig.get(cfg.proxyServerHost):
        URL = (
            f"{qconfig.get(cfg.proxyServerAddress)}:{qconfig.get(cfg.proxyServerPort)}"
        )
        result = urlparse(URL)
        if result.scheme and result.netloc:
            return {"http": URL, "https": URL}
    return dict()
