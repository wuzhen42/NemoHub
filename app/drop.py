import os
import sys
import subprocess

from PySide6.QtCore import Qt, QSize, QMargins, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFileDialog
from qfluentwidgets import ToolButton
from qfluentwidgets import FluentIcon as FIF


class DropFileButton(ToolButton):
    pathChanged = Signal(str)

    def __init__(self, acceptFile, parent=None):
        super().__init__(parent)

        self.setIconSize(QSize(48, 48))
        self.setFixedSize(300, 200)
        self.setStyleSheet("border: 2px dashed;")
        self.setAcceptDrops(True)

        if acceptFile:
            self.acceptFolder = False
            self.setIcon(FIF.DOCUMENT)
            self.clicked.connect(self.openFile)
        else:
            self.acceptFolder = True
            self.setIcon(FIF.FOLDER)
            self.clicked.connect(self.openFolder)
        self.extensions = []
        self.path = ""

    def setExtensions(self, extensions):
        self.extensions = extensions

    def composeTooltip(self):
        if self.acceptFolder:
            text = "Click or Drop Folder here"
        else:
            text = "Click or Drop ma/mb File here"
        return text

    def openFile(self):
        extensions = ["ma", "mb"]
        filter_list = (
            "File(%s)" % (" ".join(["*" + e for e in extensions]))
            if extensions
            else "Any File(*)"
        )
        path, _ = QFileDialog.getOpenFileName(
            self, "Browse File", self.path, filter_list
        )
        self.setPath(path)

    def setPath(self, path):
        self.path = path
        self.pathChanged.emit(self.path)

    def openFolder(self):
        path = QFileDialog.getExistingDirectory(self, "Browse Folder", self.path)
        self.setPath(path)

    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QPainter(self)

        rect = self.rect().marginsRemoved(QMargins(0, 0, 0, 10))
        painter.drawText(rect, Qt.AlignBottom | Qt.AlignCenter, self.composeTooltip())

    def dragEnterEvent(self, event):
        if not event.mimeData().hasFormat("text/uri-list"):
            return

        if self.acceptFolder:
            folder_list = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if os.path.isdir(url.toLocalFile())
            ]
            if len(folder_list) == 1:
                event.acceptProposedAction()
                return
        else:
            file_list = self._get_valid_file_list(event.mimeData().urls())
            if len(file_list) == 1:
                event.acceptProposedAction()
                return

    def dropEvent(self, event):
        if self.acceptFolder:
            folder_list = [
                url.toLocalFile()
                for url in event.mimeData().urls()
                if os.path.isdir(url.toLocalFile())
            ]
            self.setPath(folder_list[0])
        else:
            file_list = self._get_valid_file_list(event.mimeData().urls())
            self.setPath(file_list[0])

    def _get_valid_file_list(self, url_list):
        file_list = []
        for url in url_list:
            file_name = url.toLocalFile()
            if sys.platform == "darwin":
                sub_process = subprocess.Popen(
                    "osascript -e 'get posix path of posix file \"file://{}\" -- kthxbai'".format(
                        file_name
                    ),
                    stdout=subprocess.PIPE,
                    shell=True,
                )
                file_name = sub_process.communicate()[0].strip()
                sub_process.wait()

            if os.path.isfile(file_name):
                if self.extensions:
                    if file_name.split(".")[-1] in self.extensions:
                        file_list.append(file_name)
                else:
                    file_list.append(file_name)

        return file_list
