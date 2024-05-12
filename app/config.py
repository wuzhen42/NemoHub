from qfluentwidgets import (
    QConfig,
    qconfig,
    ConfigItem,
    BoolValidator,
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
        OptionsValidator([None, 2018, 2019, 2020, 2022, 2023, 2024]),
    )

    checkUpdateAtStartUp = ConfigItem(
        "Update", "CheckUpdateAtStartUp", True, BoolValidator()
    )

    useNightlyVersion = ConfigItem(
        "Update", "UseNightlyVersion", False, BoolValidator()
    )

    convertModernOn = ConfigItem("Convert", "ModernOptionOn", False, BoolValidator())
    convertNativeOn = ConfigItem("Convert", "NativeOptionOn", False, BoolValidator())
    convertDoubleOn = ConfigItem("Convert", "DoubleOptionOn", False, BoolValidator())
    convertForceOn = ConfigItem("Convert", "ForceOptionOn", True, BoolValidator())
    convertProfileOn = ConfigItem("Convert", "ProfileOptionOn", False, BoolValidator())
    convertGpuOn = ConfigItem("Convert", "GpuOptionOn", True, BoolValidator())


cfg = Config()
qconfig.load("config/config.json", cfg)
