import subprocess

from app.config import cfg


def call_maya(sentences):
    if not cfg.mayaVersion.value:
        return
    mayapy = f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"'
    command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(name='python'); {';'.join(sentences)}; standalone.uninitialize()\""
    return subprocess.check_output(command).strip().decode()
