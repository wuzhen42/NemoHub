import sys
import os

from PySide6.QtCore import QTranslator, QLocale, QLibraryInfo
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import (
    NavigationItemPosition,
    FluentWindow,
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


class ClientWindow(FluentWindow):
    def __init__(self, loginTuple):
        super().__init__()

        self.easyArea = EasyWidget(loginTuple, self)
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
        self.addSubInterface(self.easyArea, FIF.SEND, self.tr("Convert"))
        self.addSubInterface(self.assetsArea, FIF.BOOK_SHELF, self.tr("Tasks"))
        self.addSubInterface(self.licenseArea, FIF.VPN, self.tr("License"))

        self.addSubInterface(self.settingArea, FIF.SETTING, self.tr("Settings"), NavigationItemPosition.BOTTOM)

    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon(":/images/logo.png"))
        self.setWindowTitle(self.tr("Nemo Hub"))

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)


def load_translations(app):
    """Load translation files based on system locale"""
    # Get system locale using Qt's locale detection (more reliable for Qt apps)
    locale_name = QLocale.system().name()  # e.g., 'zh_CN', 'en_US'

    print(f"Detected locale: {locale_name}")

    app_translator = QTranslator(app)
    translations_dir = os.path.join(os.path.dirname(__file__), "translations")
    qm_file = os.path.join(translations_dir, f"nemohub_{locale_name}.qm")

    if os.path.exists(qm_file):
        if app_translator.load(qm_file):
            app.installTranslator(app_translator)
            print(f"✓ Loaded NemoHub translation: {locale_name}")
        else:
            print(f"✗ Failed to load translation file: {qm_file}")
    else:
        print(f"Translation file not found: {qm_file}, using default language(English)")

    # Also load Qt base translations for standard dialogs
    qt_translator = QTranslator(app)
    qt_translations_loaded = qt_translator.load(f"qt_{locale_name}", QLibraryInfo.path(QLibraryInfo.TranslationsPath))
    if qt_translations_loaded:
        app.installTranslator(qt_translator)
        print(f"✓ Loaded Qt base translations")

    return app_translator if os.path.exists(qm_file) else None


if __name__ == "__main__":
    app = QApplication(sys.argv)

    translator = load_translations(app)

    loginWindow = LoginWindow()
    loginWindow.show()

    def switchToMainWindow(username, password, auth):
        mainWindow = ClientWindow((username, password, auth))
        mainWindow.show()
        loginWindow.close()

    loginWindow.loginSuccess.connect(switchToMainWindow)

    app.exec()
    cfg.save()
