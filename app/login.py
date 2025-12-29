import webbrowser
import requests


from PySide6.QtCore import Qt, QSize, Signal, QSettings
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QSpacerItem, QSizePolicy, QLabel

from qframelesswindow import FramelessWindow
from qfluentwidgets import (
    setThemeColor,
    SplitTitleBar,
    InfoBar,
    InfoBarPosition,
    PushButton,
    PrimaryPushButton,
    HyperlinkButton,
    LineEdit,
    BodyLabel,
    CheckBox
)
from qfluentwidgets import FluentIcon as FIF

import resource_rc  # Import compiled Qt resources

from app.utils import get_proxies
from app.config import get_api_domain
from app.proxy import ProxyDialog


class LoginWindow(FramelessWindow):
    loginSuccess = Signal(str, str, requests.cookies.RequestsCookieJar)

    def __init__(self):
        super().__init__()

        self.settings = QSettings("NemoHub", "login")

        self.setupUi()
        setThemeColor("#28afe9")

        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()

        self.setWindowTitle(self.tr("Nemo Hub"))
        self.setWindowIcon(QIcon(":/images/logo.png"))

        inputFormWidth = 250
        self.resize(500 / 9 * 16 + inputFormWidth, 500)
        self.setMinimumSize(700, 500)

        self.load_settings()

        self.titleBar.titleLabel.setStyleSheet(
            """
            QLabel{
                background: transparent;
                font: 13px 'Segoe UI';
                padding: 0 4px;
                color: white
            }
        """
        )

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        self.buttonFindPassword.clicked.connect(
            lambda: webbrowser.open(
                f"https://www.{get_api_domain()}/login", new=0, autoraise=True
            )
        )
        self.buttonPoster.clicked.connect(
            lambda _: webbrowser.open(
                "https://www.youtube.com/@nemopuppet",
                new=0,
                autoraise=True,
            )
        )
        self.buttonLogin.clicked.connect(self.submit)
        self.buttonProxy.clicked.connect(self.showProxyDialog)

    def setupUi(self):
        """Create the UI programmatically"""
        centralWidget = QWidget(self)
        mainLayout = QHBoxLayout(centralWidget)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.setSpacing(0)

        # Left side: Poster button
        self.buttonPoster = QPushButton(centralWidget)
        self.buttonPoster.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.buttonPoster.setMinimumSize(640, 480)
        self.buttonPoster.setStyleSheet("text-align:center;")
        self.buttonPoster.setIcon(QIcon(":/images/poster_nzt.jpg"))
        self.buttonPoster.setIconSize(QSize(1280, 720))
        mainLayout.addWidget(self.buttonPoster)

        # Right side: Login form
        self.widget = QWidget(centralWidget)
        self.widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.widget.setMinimumWidth(250)
        self.widget.setMaximumWidth(250)
        self.widget.setStyleSheet("QLabel{ font: 13px 'Microsoft YaHei' }")

        formLayout = QVBoxLayout(self.widget)
        formLayout.setSpacing(9)
        formLayout.setContentsMargins(20, 20, 20, 20)

        # Top spacer
        formLayout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Logo
        logoLabel = QLabel(self.widget)
        logoLabel.setMinimumSize(100, 100)
        logoLabel.setMaximumSize(100, 100)
        logoLabel.setPixmap(QPixmap(":/images/logo.png"))
        logoLabel.setScaledContents(True)
        formLayout.addWidget(logoLabel, 0, Qt.AlignHCenter)

        # Spacer after logo
        formLayout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Username label
        labelUsername = BodyLabel(self.tr("Username"), self.widget)
        formLayout.addWidget(labelUsername)

        # Username input
        self.inputAccount = LineEdit(self.widget)
        self.inputAccount.setClearButtonEnabled(True)
        formLayout.addWidget(self.inputAccount)

        # Password label
        labelPassword = BodyLabel(self.tr("Password"), self.widget)
        formLayout.addWidget(labelPassword)

        # Password input
        self.inputPassword = LineEdit(self.widget)
        self.inputPassword.setEchoMode(LineEdit.Password)
        self.inputPassword.setClearButtonEnabled(True)
        formLayout.addWidget(self.inputPassword)

        # Spacer
        formLayout.addSpacerItem(QSpacerItem(20, 5, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Save password checkbox
        self.checkSavePassword = CheckBox(self.tr("Save Password"), self.widget)
        formLayout.addWidget(self.checkSavePassword)

        # Spacer
        formLayout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Login button
        self.buttonLogin = PrimaryPushButton(self.tr("Login"), self.widget)
        formLayout.addWidget(self.buttonLogin)

        # Spacer
        formLayout.addSpacerItem(QSpacerItem(20, 2, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # Proxy settings button
        self.buttonProxy = PushButton(FIF.CLOUD, self.tr("Proxy Settings"), self.widget)
        formLayout.addWidget(self.buttonProxy)

        # Reset password link
        self.buttonFindPassword = HyperlinkButton("", self.tr("Reset Password"), self.widget)
        formLayout.addWidget(self.buttonFindPassword)

        mainLayout.addWidget(self.widget)

        # Set central widget
        self.setLayout(mainLayout)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        pixmap = QPixmap(":/images/poster_nzt.jpg").scaled(
            self.buttonPoster.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        self.buttonPoster.setIcon(pixmap)

    def load_settings(self):
        if self.settings.value("savePassword", False):
            self.checkSavePassword.setChecked(True)
            self.inputPassword.setText(self.settings.value("password", ""))
        self.inputAccount.setText(self.settings.value("account", ""))

    def save_settings(self):
        self.settings.setValue("savePassword", self.checkSavePassword.isChecked())
        self.settings.setValue("account", self.inputAccount.text())
        if self.checkSavePassword.isChecked():
            self.settings.setValue("password", self.inputPassword.text())

    def showProxyDialog(self):
        dialog = ProxyDialog(self)
        dialog.exec()

    def submit(self):
        auth = None
        try:
            account = self.inputAccount.text()
            password = self.inputPassword.text()
            self.save_settings()

            recv = requests.post(
                f"https://www.{get_api_domain()}/api/login",
                data={"username": account, "password": password},
                proxies=get_proxies()
            )
            auth = recv.cookies
            error = recv.text
        except Exception as e:
            error = str(e)

        if auth:
            self.loginSuccess.emit(account, password, auth)
        else:
            InfoBar.error(
                title=self.tr("Login Failed"),
                content=error,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,  # won't disappear automatically
                parent=self,
            )
