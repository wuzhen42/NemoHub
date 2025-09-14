import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout
from qfluentwidgets import (
    NavigationItemPosition,
    FluentWindow,
    SubtitleLabel,
    setFont,
    InfoBadge,
    InfoBadgePosition,
)
from qfluentwidgets import FluentIcon as FIF

from app.login import LoginWindow
from app.easy import EasyWidget
from app.assets import AssetsWidget
from app.settings import SettingsWidget
from app.license import LicenseWidget
from app.config import cfg


class Widget(QFrame):
    def __init__(self, text: str, parent=None):
        super().__init__(parent=parent)
        self.label = SubtitleLabel(text, self)
        self.hBoxLayout = QHBoxLayout(self)

        setFont(self.label, 24)
        self.label.setAlignment(Qt.AlignCenter)
        self.hBoxLayout.addWidget(self.label, 1, Qt.AlignCenter)
        self.setObjectName(text.replace(" ", "-"))


class ClientWindow(FluentWindow):
    def __init__(self, loginTuple):
        super().__init__()

        # create sub interface
        self.easyArea = EasyWidget(loginTuple, self)
        # self.batchArea = Widget("Multiple in batch", self)
        self.assetsArea = AssetsWidget(self)
        self.settingArea = SettingsWidget(loginTuple, self)
        self.licenseArea = LicenseWidget(loginTuple, self)

        self.initNavigation()
        self.initWindow()
        self.taskBadge = None

        self.assetsArea.activeTasksChanged.connect(self.onActiveTasksBage)

    def onActiveTasksBage(self, count):
        if not self.taskBadge:
            item = self.navigationInterface.widget(self.assetsArea.objectName())
            self.taskBadge = InfoBadge.attension(
                text=count,
                parent=item.parent(),
                target=item,
                position=InfoBadgePosition.NAVIGATION_ITEM,
            )
            return

        if count == 0:
            self.taskBadge.hide()
        else:
            self.taskBadge.show()
            self.taskBadge.setText(str(count))

    def initNavigation(self):
        self.addSubInterface(self.easyArea, FIF.SEND, "Easy")
        # self.addSubInterface(self.batchArea, FIF.CALORIES, "Batch")
        self.addSubInterface(self.assetsArea, FIF.BOOK_SHELF, "Tasks")

        self.addSubInterface(self.licenseArea, FIF.VPN, "License", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingArea, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon(":/images/logo.png"))
        self.setWindowTitle("Nemo Hub")

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    loginWindow = LoginWindow()
    loginWindow.show()

    def switchToMainWindow(username, password, auth):
        mainWindow = ClientWindow((username, password, auth))
        mainWindow.show()
        loginWindow.close()

    loginWindow.loginSuccess.connect(switchToMainWindow)
    # mainWindow = ClientWindow((None, None))
    # mainWindow.show()

    app.exec()
    cfg.save()
