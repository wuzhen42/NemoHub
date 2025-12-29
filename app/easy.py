import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QGridLayout,
)
from PySide6.QtGui import QFontMetrics
from qfluentwidgets import (
    StrongBodyLabel,
    LineEdit,
    BodyLabel,
    PushButton,
    PillPushButton,
    InfoBar,
    InfoBarPosition,
)
from qfluentwidgets import FluentIcon as FIF

from app.drop import DropFileButton
from app.config import cfg
from app.tasks import new_task


class ElidedLabel(BodyLabel):
    """Label that elides text from the left (beginning) when too long"""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._fullText = text
        self.setWordWrap(False)
        self.setText(text)

    def setText(self, text):
        self._fullText = text
        self._updateElidedText()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._updateElidedText()

    def _updateElidedText(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._fullText, Qt.ElideLeft, self.width())
        super().setText(elided)


class EasyWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)

        self.loginTuple = loginTuple
        self.setObjectName("Convert")


        self.setup()
        self.inputFile.setExtensions(["ma", "mb"])
        self.inputFile.pathChanged.connect(self.setInputPath)
        self.outputFolder.pathChanged.connect(self.setOutputPath)
        self.optionGPU.setChecked(cfg.convertGpuOn.value)
        self.optionDouble.setChecked(cfg.convertDoubleOn.value)
        self.optionForce.setChecked(cfg.convertForceOn.value)
        self.optionModern.setChecked(cfg.convertModernOn.value)
        self.optionNative.setChecked(cfg.convertNativeOn.value)
        self.buttonSubmit.clicked.connect(self.submit)

    def setInputPath(self, path):
        self.textFile.setText(path)
        self.inputName.setText(os.path.basename(path).split(".")[0])

    def setOutputPath(self, path):
        self.textFolder.setText(path)

    def submit(self):
        try:
            if not cfg.mayaVersion.value:
                raise RuntimeError(self.tr("Must select maya version first in Settings"))
            cfg.convertGpuOn.value = self.optionGPU.isChecked()
            cfg.convertDoubleOn.value = self.optionDouble.isChecked()
            cfg.convertForceOn.value = self.optionForce.isChecked()
            cfg.convertModernOn.value = self.optionModern.isChecked()
            cfg.convertNativeOn.value = self.optionNative.isChecked()

            new_task(
                self.loginTuple,
                self.inputName.text(),
                self.inputFile.path,
                self.outputFolder.path,
                self.optionGPU.isChecked(),
                self.optionDouble.isChecked(),
                self.optionForce.isChecked(),
                self.optionModern.isChecked(),
                self.optionNative.isChecked(),
                False
            )
        except Exception as e:
            InfoBar.error(
                title=self.tr("Create Task Failed"),
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,  # won't disappear automatically
                parent=self,
            )
        else:
            InfoBar.info(
                title=self.tr("Task started"),
                content=self.tr("You can process another asset now or check tasks in Assets page"),
                orient=Qt.Horizontal,
                isClosable=False,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self,
            )

    def setup(self):
        self.layout = QVBoxLayout(self)
        spacer = QSpacerItem(2, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        dropLayout = QHBoxLayout()

        dropFileLayout = QVBoxLayout()
        subLayout = QHBoxLayout()
        subLayout.setAlignment(Qt.AlignCenter)
        self.inputFile = DropFileButton(True)
        subLayout.addWidget(self.inputFile)
        dropFileLayout.addLayout(subLayout)

        subLayout = QHBoxLayout()
        spacer = QSpacerItem(60, 2, QSizePolicy.Fixed, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        prefixFile = StrongBodyLabel(self.tr("Original File: "))
        subLayout.addWidget(prefixFile)
        self.textFile = ElidedLabel("")
        self.textFile.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        subLayout.addWidget(self.textFile, 1)
        spacer = QSpacerItem(20, 2, QSizePolicy.Fixed, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        dropFileLayout.addLayout(subLayout)
        dropLayout.addLayout(dropFileLayout)

        dropFolderLayout = QVBoxLayout()
        subLayout = QHBoxLayout()
        subLayout.setAlignment(Qt.AlignCenter)
        self.outputFolder = DropFileButton(False)
        subLayout.addWidget(self.outputFolder)
        dropFolderLayout.addLayout(subLayout)

        subLayout = QHBoxLayout()
        spacer = QSpacerItem(60, 2, QSizePolicy.Fixed, QSizePolicy.Fixed)
        subLayout.addItem(spacer)
        prefixFolder = StrongBodyLabel(self.tr("Output Folder:"))
        subLayout.addWidget(prefixFolder)
        self.textFolder = ElidedLabel("")
        self.textFolder.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        subLayout.addWidget(self.textFolder, 1)
        spacer = QSpacerItem(20, 2, QSizePolicy.Fixed, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        dropFolderLayout.addLayout(subLayout)
        dropLayout.addLayout(dropFolderLayout)

        self.layout.addLayout(dropLayout)

        spacer = QSpacerItem(2, 40, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(spacer)

        subLayout = QHBoxLayout()
        subLayout.setAlignment(Qt.AlignCenter)
        spacer = QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        labelName = BodyLabel(self.tr("Name: "))
        subLayout.addWidget(labelName)
        self.inputName = LineEdit()
        self.inputName.setMaximumWidth(300)
        self.inputName.setClearButtonEnabled(True)
        subLayout.addWidget(self.inputName)
        spacer = QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        self.layout.addLayout(subLayout)

        spacer = QSpacerItem(2, 10, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(spacer)

        subLayout = QGridLayout()
        self.optionDouble = PillPushButton("double")
        self.optionForce = PillPushButton("force")
        self.optionGPU = PillPushButton("gpu")
        self.optionNative = PillPushButton("native")
        self.optionModern = PillPushButton("turbo")
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 0
        )
        subLayout.addWidget(self.optionDouble, 0, 1)
        subLayout.addWidget(self.optionForce, 0, 2)
        subLayout.addWidget(self.optionGPU, 0, 3)
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 4
        )
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 0
        )
        subLayout.addWidget(self.optionNative, 1, 1)
        subLayout.addWidget(self.optionModern, 1, 2)
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 4
        )
        self.layout.addLayout(subLayout)

        spacer = QSpacerItem(2, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(spacer)

        subLayout = QHBoxLayout()
        subLayout.setAlignment(Qt.AlignCenter)
        self.buttonSubmit = PushButton(FIF.SEND, self.tr("GO"))
        subLayout.addWidget(self.buttonSubmit)
        self.layout.addLayout(subLayout)

        spacer = QSpacerItem(2, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)
