import platform
import os
import locale

from qfluentwidgets import (
    QConfig,
    qconfig,
    ConfigItem,
    BoolValidator,
    RangeValidator,
    OptionsConfigItem,
    OptionsValidator,
    ConfigSerializer,
)


class MayaVersionSerializer(ConfigSerializer):
    def serialize(self, version):
        return version

    def deserialize(self, value):
        return int(value) if value else None


class Config(QConfig):
    mayaVersion = OptionsConfigItem(
        "Convert",
        "MayaVersion",
        None,
        OptionsValidator([None, 2018, 2019, 2020, 2022, 2023, 2024, 2025, 2026]),
    )

    checkUpdateAtStartUp = ConfigItem(
        "Update", "CheckUpdateAtStartUp", True, BoolValidator()
    )

    useNightlyVersion = ConfigItem(
        "Update", "UseNightlyVersion", False, BoolValidator()
    )

    proxyServerAddress = ConfigItem("Proxy", "ServerAddress", "")
    proxyServerPort = ConfigItem("Proxy", "ServerPort", 9000, RangeValidator(0, 9999))
    proxyServerHost = ConfigItem("Proxy", "ServerPort", False, BoolValidator())

    convertModernOn = ConfigItem("Convert", "ModernOptionOn", False, BoolValidator())
    convertNativeOn = ConfigItem("Convert", "NativeOptionOn", False, BoolValidator())
    convertDoubleOn = ConfigItem("Convert", "DoubleOptionOn", False, BoolValidator())
    convertForceOn = ConfigItem("Convert", "ForceOptionOn", True, BoolValidator())
    convertProfileOn = ConfigItem("Convert", "ProfileOptionOn", False, BoolValidator())
    convertGpuOn = ConfigItem("Convert", "GpuOptionOn", True, BoolValidator())


def get_config_dir():
    if platform.system() == "Windows":
        return os.path.join(os.environ["APPDATA"], "Nemo")
    else:
        return os.path.join(os.path.expanduser("~"), ".config", "Nemo")


def get_config_file():
    config_dir = get_config_dir()
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    return os.path.join(config_dir, "config.json")


def get_api_domain():
    """
    Get the appropriate API domain based on system language.
    Returns 'nemopuppet.cn' for China Mainland users (zh_CN), 'nemopuppet.com' otherwise.
    """
    try:
        lang, encoding = locale.getdefaultlocale()
        if lang == 'zh_CN':
            return "nemopuppet.cn"
    except:
        pass

    return "nemopuppet.com"


cfg = Config()
qconfig.load(get_config_file(), cfg)
