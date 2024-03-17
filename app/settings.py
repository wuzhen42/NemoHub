import sys
import os
import subprocess
import datetime
import tempfile
import threading
import shutil
import zipfile

import tzlocal
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QApplication,
)
from qfluentwidgets import (
    ComboBoxSettingCard,
    SwitchSettingCard,
    HyperlinkCard,
    PrimaryPushSettingCard,
    MessageDialog,
)
from qfluentwidgets import FluentIcon as FIF
import requests
from packaging import version

from app.utils import call_maya
from app.config import cfg


class SettingsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.currentHub = version.Version("0.0.2")
        self.latestHub = None
        self.currentNemo = None

        self.setObjectName("Settings")
        self.setup()
        if cfg.checkUpdateAtStartUp.value:
            self.checkHubVersion()
            self.checkNemoVersion()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onCheckUpdate)
        self.timer.start(1000)

    def onCheckUpdate(self):
        if self.latestHub and self.latestHub > self.currentHub:
            title = "New version of NemoHub dectected"
            content = f"Current version of NemoHub is {self.currentHub}. The latest version is {self.latestHub}, Do you want to update?"
            parent = self.parent().parent().parent()
            w = MessageDialog(title, content, parent)
            if w.exec():
                response = requests.get(
                    "https://api.github.com/repos/wuzhen42/NemoHub/releases/latest"
                ).json()
                asset = response["assets"][0]
                url = asset["browser_download_url"]
                recv = requests.get(url, stream=True)
                tmpdir = tempfile.mkdtemp()
                output_path = "{}/{}".format(tmpdir, asset["name"])
                with open(output_path, "wb") as f:
                    shutil.copyfileobj(recv.raw, f)
                with zipfile.ZipFile(output_path, allowZip64=True) as archive:
                    archive.extractall(tmpdir)
                os.remove(output_path)

                target_dir = os.path.realpath(os.path.dirname(sys.argv[0]))
                QApplication.quit()
                subprocess.Popen(
                    f"timeout 3 > NUL && .\\update {tmpdir} {target_dir}",
                    cwd=tmpdir,
                    shell=True,
                    start_new_session=True,
                )
                sys.exit(0)
            else:
                self.latestHub = None

    def checkNemoVersion(self):
        def run(widget, card):
            result = call_maya(
                [
                    "import NemoMaya",
                    "print(NemoMaya.get_version())",
                    "print(NemoMaya.get_timestamp())",
                ]
            )
            if not result:
                return
            version, ts = result.splitlines()[-2:]
            widget.currentNemo = (version, ts)

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
            card.setContent(f"Version: {version} Date:{ts.strftime('%Y-%m-%d %I:%M')}")

        threading.Thread(target=run, args=(self, self.nemoCard)).start()

    def checkHubVersion(self):
        def run(widget):
            response = requests.get(
                "https://api.github.com/repos/wuzhen42/NemoHub/releases/latest"
            ).json()
            widget.latestHub = version.parse(response["tag_name"])

        threading.Thread(target=run, args=(self,)).start()

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

        self.nemoCard = PrimaryPushSettingCard(
            self.tr("Check Update"),
            FIF.INFO,
            self.tr("Nemo"),
            self.tr("Version: ") + " Unknown",
        )
        self.nemoCard.clicked.connect(self.checkNemoVersion)
        self.layout.addWidget(self.nemoCard)

        self.hubCard = HyperlinkCard(
            "https://github.com/wuzhen42/NemoHub",
            self.tr("Contribute"),
            FIF.INFO,
            self.tr("Hub v") + str(self.currentHub),
            self.tr("Welcome to Contribute"),
        )
        self.layout.addWidget(self.hubCard)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)
