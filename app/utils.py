import subprocess
import platform
import os


def call_maya(sentences):
    from app.config import cfg

    if not cfg.mayaVersion.value:
        return
    mayapy = f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"'
    command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(name='python'); {';'.join(sentences)}; standalone.uninitialize()\""
    return subprocess.check_output(command).strip().decode()


def get_config_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "Nemo")
    else:  # Linux/Unix
        return os.path.join(os.path.expanduser("~"), ".config", "Nemo")


def get_config_file():
    config_dir = get_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, "config.json")

def get_license_path():
    return os.path.join(get_config_dir(), "NemoSeat.lic")