import webbrowser
import requests


from PySide6.QtCore import Qt, QSize, Signal, QSettings
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from qframelesswindow import FramelessWindow
from qfluentwidgets import setThemeColor, SplitTitleBar, InfoBar, InfoBarPosition

from ui_loginwindow import Ui_Form


class LoginWindow(FramelessWindow, Ui_Form):
    loginSuccess = Signal(str, str)

    def __init__(self):
        super().__init__()

        self.settings = QSettings("NemoHub", "login")

        self.setupUi(self)
        # setTheme(Theme.DARK)
        setThemeColor("#28afe9")

        self.setTitleBar(SplitTitleBar(self))
        self.titleBar.raise_()

        self.setWindowTitle("Nemo Hub")
        self.setWindowIcon(QIcon(":/images/logo.png"))
        inputFormWidth = 250
        self.widget.setMinimumSize(QSize(inputFormWidth, 0))
        self.resize(500 / 9 * 16 + inputFormWidth, 500)

        self.load_settings()

        # self.windowEffect.setMicaEffect(self.winId(), isDarkMode=False)
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
                "https://www.nemopuppet.com/login", new=0, autoraise=True
            )
        )
        self.buttonPoster.clicked.connect(
            lambda _: webbrowser.open(
                "https://jobs.mihoyo.com/m/?recommendationCode=NTAXtp1&isRecommendation=true#/position/2537",
                new=0,
                autoraise=True,
            )
        )
        self.buttonLogin.clicked.connect(self.submit)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        pixmap = QPixmap(":/images/poster_zzz.jpg").scaled(
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

    def submit(self):
        auth = None
        try:
            account = self.inputAccount.text()
            password = self.inputPassword.text()
            self.save_settings()

            recv = requests.post(
                "https://www.nemopuppet.com/api/login",
                data={"username": account, "password": password},
            )
            auth = recv.cookies
            error = recv.text
        except Exception as e:
            error = str(e)

        if auth:
            self.loginSuccess.emit(account, password)
        else:
            InfoBar.error(
                title="Login Failed",
                content=error,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.BOTTOM_RIGHT,
                duration=-1,  # won't disappear automatically
                parent=self,
            )
