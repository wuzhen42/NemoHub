import sys
import os
import subprocess
import datetime
import tempfile
import threading
import shutil
import zipfile

import tzlocal
from PySide6.QtCore import Qt, QTimer
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
    InfoBar,
    InfoBarPosition,
)
from qfluentwidgets import FluentIcon as FIF
import requests
from packaging import version

import app.utils as utils
from app.config import cfg
from app.proxy import ProxySettingsCard


class SettingsWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)
        self.loginTuple = loginTuple
        self.currentHub = version.Version("0.0.9")
        self.latestHub = None
        self.currentNemo = None
        self.stableNemo = None
        self.nightlyNemo = None
        self.expired = None

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
                    "https://api.github.com/repos/wuzhen42/NemoHub/releases/latest",
                    proxies=utils.get_proxies()
                ).json()
                asset = response["assets"][0]
                url = asset["browser_download_url"]
                recv = requests.get(url, stream=True, proxies=utils.get_proxies())
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

        if not self.currentNemo:
            return

        hasUpdate = False
        if cfg.useNightlyVersion.value:
            if self.nightlyNemo and self.nightlyNemo[1] > self.currentNemo[1]:
                hasUpdate = True
        elif self.stableNemo:
            if self.currentNemo[0] == "nightly":
                hasUpdate = True
            elif self.stableNemo[0] > version.parse(self.currentNemo[0]):
                hasUpdate = True

        if hasUpdate:
            title = "New version of NemoMaya dectected"
            if cfg.useNightlyVersion.value:
                currentDate = self.currentNemo[1].strftime("%Y-%m-%d")
                latestDate = self.nightlyNemo[1].strftime("%Y-%m-%d")
                if self.currentNemo[0] == "v0.0.0":
                    message = f"NemoMaya seems not installed on your machine yet.\nThe latest nightly version is released at {latestDate}."
                elif self.currentNemo[0] == "nightly":
                    message = f"Current version of NemoMaya is releasd at {currentDate}.\nThe latest nightly version is released at {latestDate}."
                else:
                    message = f"Current version of NemoMaya is {self.currentNemo[0]}.\nThe latest nightly version is released at {latestDate}."
            else:
                if self.currentNemo[0] == "v0.0.0":
                    message = f"NemoMaya seems not installed on your machine yet.\nThe latest stable version is {self.stableNemo[0]}."
                else:
                    message = f"Current version of NemoMaya is {self.currentNemo[0]}.\nThe latest stable version is {self.stableNemo[0]}."
            content = f"{message}\nDo you want to update now? It would take a while.\nNOTICE: all maya instances using Nemo should be closed before update."
            parent = self.parent().parent().parent()
            w = MessageDialog(title, content, parent)

            if w.exec():
                target_version = (
                    "nightly"
                    if cfg.useNightlyVersion.value
                    else str(self.stableNemo[0])
                )
                recv = requests.get(
                    f"https://www.nemopuppet.com/api/release/{target_version}/maya",
                    proxies=utils.get_proxies(),
                    stream=True,
                )
                tmpdir = tempfile.mkdtemp()
                output_path = f"{tmpdir}/NemoMaya_{target_version}.zip"
                with open(output_path, "wb") as f:
                    shutil.copyfileobj(recv.raw, f)
                with zipfile.ZipFile(output_path, allowZip64=True) as archive:
                    archive.extractall(tmpdir)
                os.remove(output_path)

                path_modules = "{}/Documents/maya/modules".format(
                    os.path.expanduser("~")
                )
                target_dir = "{}/Nemo".format(path_modules)
                if os.path.isdir(target_dir):
                    shutil.rmtree(target_dir)
                shutil.copytree("{}/Nemo".format(tmpdir), target_dir)
                shutil.copy("{}/nemo.mod".format(tmpdir), path_modules)
                InfoBar.success(
                    title="NemoMaya updated",
                    content=f"You can restart maya to try latest features now",
                    orient=Qt.Horizontal,
                    isClosable=True,
                    position=InfoBarPosition.TOP,
                    duration=-1,
                    parent=self,
                )
                self.currentNemo = None
                self.stableNemo = None
                self.nightlyNemo = None
                self.checkNemoVersion()
            else:
                self.currentNemo = None
        else:
            self.currentNemo = None

    def checkNemoVersion(self):
        def run(widget, card):
            if not cfg.mayaVersion.value:
                return
            try:
                result = utils.call_maya(
                    [
                        "import NemoMaya",
                        "print(NemoMaya.get_version())",
                        "print(NemoMaya.get_timestamp())",
                    ]
                )
                if not result:
                    return
            except subprocess.CalledProcessError:
                self.currentNemo = ("v0.0.0", datetime.date.min)
                return

            version, ts = result.splitlines()[-2:]
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
            widget.currentNemo = (version, ts.date())
            card.setContent(f"Version: {version} Date:{ts.strftime('%Y-%m-%d %I:%M')}")

        threading.Thread(target=run, args=(self, self.nemoCard)).start()

        def run(widget):
            response = requests.get("https://www.nemopuppet.com/api/releases", proxies=utils.get_proxies()).json()
            versions = []
            widget.nightlyNemo = ("None", datetime.date.min)
            for item in response:
                date = datetime.datetime.strptime(item["date"], "%Y/%m/%d").date()
                ver = item["version"]
                if ver == "nightly":
                    widget.nightlyNemo = (ver, date)
                else:
                    versions.append((version.parse(ver), date))
            widget.stableNemo = max(versions, key=lambda item: item[1])

        threading.Thread(target=run, args=(self,)).start()

    def checkHubVersion(self):
        def run(widget):
            response = requests.get(
                "https://api.github.com/repos/wuzhen42/NemoHub/releases/latest",
                proxies=utils.get_proxies()
            ).json()
            widget.latestHub = version.parse(response["tag_name"])

        threading.Thread(target=run, args=(self,)).start()

    def setup(self):
        self.layout = QVBoxLayout(self)

        self.optionMaya = ComboBoxSettingCard(
            cfg.mayaVersion,
            FIF.ROBOT,
            "Maya",
            texts=["", "2018", "2019", "2020", "2022", "2023", "2024", "2025", "2026"],
        )
        self.layout.addWidget(self.optionMaya)

        self.switchAutoUpdate = SwitchSettingCard(
            FIF.UPDATE,
            self.tr("Check for updates when the application starts"),
            self.tr("The new version will be more sufficient and have more features"),
            configItem=cfg.checkUpdateAtStartUp,
        )
        self.layout.addWidget(self.switchAutoUpdate)

        self.switchUseNightly = SwitchSettingCard(
            FIF.DEVELOPER_TOOLS,
            self.tr("Use nightly beta version"),
            self.tr(
                "The nightly version is always the latest, but may be unstable. Be sure only using it for test purpose"
            ),
            configItem=cfg.useNightlyVersion,
        )
        self.layout.addWidget(self.switchUseNightly)

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

        self.proxyCard = ProxySettingsCard(
            FIF.CLOUD,
            self.tr("Proxy"),
        )
        self.layout.addWidget(self.proxyCard)
