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


cfg = Config()
qconfig.load("config/config.json", cfg)
