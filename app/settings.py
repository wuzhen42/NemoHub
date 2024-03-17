import datetime

import tzlocal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QSpacerItem, QSizePolicy
from qfluentwidgets import (
    ComboBoxSettingCard,
    SwitchSettingCard,
    HyperlinkCard,
    PrimaryPushSettingCard,
)
from qfluentwidgets import FluentIcon as FIF

from app.utils import call_maya
from app.config import cfg


class SettingsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)

        self.setObjectName("Settings")
        self.setup()
        if cfg.checkUpdateAtStartUp.value:
            self.updateVersion()

    def updateVersion(self):
        try:
            version, ts = call_maya(
                [
                    "import NemoMaya",
                    "print(NemoMaya.get_version())",
                    "print(NemoMaya.get_timestamp())",
                ]
            ).splitlines()[-2:]
            ts = datetime.datetime.strptime(ts, "%Y%m%d%H%M")
            ts = datetime.datetime(
                ts.year,
                ts.month,
                ts.day,
                ts.hour,
                ts.minute,
                tzinfo=datetime.timezone.utc,
            )
            ts = ts.astimezone(tzlocal.get_localzone())
            self.aboutCard.setContent(
                f"Version: {version} Date:{ts.strftime('%Y-%m-%d %I:%M')}"
            )
        except Exception as e:
            print(e)

    def setup(self):
        self.layout = QVBoxLayout(self)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        self.optionMaya = ComboBoxSettingCard(
            cfg.mayaVersion,
            FIF.ROBOT,
            "Maya",
            texts=["", "2018", "2019", "2020", "2022", "2023", "2024"],
        )
        self.layout.addWidget(self.optionMaya)

        self.switchAutoUpdate = SwitchSettingCard(
            FIF.UPDATE,
            self.tr("Check for updates when the application starts"),
            self.tr("The new version will be more sufficient and have more features"),
            configItem=cfg.checkUpdateAtStartUp,
        )
        self.layout.addWidget(self.switchAutoUpdate)

        self.helpCard = HyperlinkCard(
            "https://docs.nemopuppet.com",
            self.tr("Document"),
            FIF.HELP,
            self.tr("Help"),
            self.tr("Discover new features and learn useful tips about Nemo"),
        )
        self.layout.addWidget(self.helpCard)

        self.feedbackCard = HyperlinkCard(
            "https://www.nemopuppet.com/download",
            self.tr("Feedback"),
            FIF.FEEDBACK,
            self.tr("Provide feedback"),
            self.tr("Help us improve Nemo by providing feedback"),
        )
        self.layout.addWidget(self.feedbackCard)

        self.aboutCard = PrimaryPushSettingCard(
            self.tr("Check Update"),
            FIF.INFO,
            self.tr("About"),
            self.tr("Version: ") + " Unknown",
        )
        self.aboutCard.clicked.connect(self.updateVersion)
        self.layout.addWidget(self.aboutCard)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)
