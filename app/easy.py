import os
import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QGridLayout,
)
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


class EasyWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)

        self.loginTuple = loginTuple
        self.setObjectName("Easy Convert")

        self.setup()
        self.inputFile.setExtensions(["ma", "mb"])
        self.inputFile.pathChanged.connect(self.setInputPath)
        self.outputFolder.pathChanged.connect(self.setOutputPath)
        self.optionGPU.setChecked(True)
        self.optionForce.setChecked(True)
        self.optionModern.setChecked(True)
        self.buttonSubmit.clicked.connect(self.submit)

    def setInputPath(self, path):
        self.textFile.setText(path)
        self.inputName.setText(os.path.basename(path).split(".")[0])

    def setOutputPath(self, path):
        self.textFolder.setText(path)

    def submit(self):
        try:
            mayapy = f'"C:/Program Files/Autodesk/maya{cfg.mayaVersion.value}/bin/mayapy.exe"'
            args = [
                self.inputName.text(),
                self.inputFile.path,
                self.outputFolder.path,
            ]
            kargs = {
                "username": self.loginTuple[0],
                "password": self.loginTuple[1],
                "double": self.optionDouble.isChecked(),
                "ctrl_proxy": self.optionModern.isChecked(),
                "overwrite": self.optionForce.isChecked(),
                "gpu": self.optionGPU.isChecked(),
            }

            def cast(x):
                return f"'{x}'" if isinstance(x, str) else str(x)

            args = [cast(x) for x in args]
            kargs = [f"{k}={cast(v)}" for k, v in kargs.items()]
            func_call = f"convert.process({','.join(args)}, {','.join(kargs)})"
            command = f"{mayapy} -c \"from maya import standalone; standalone.initialize(name='python'); from nemo.pipeline import convert; {func_call}\""
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            new_task(self.inputName.text(), self.outputFolder.path, proc)
            # subprocess.check_output(command, shell=True)
        except Exception as e:
            InfoBar.error(
                title="Create Task Failed",
                content=str(e),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,  # won't disappear automatically
                parent=self,
            )
        else:
            InfoBar.info(
                title="Task started",
                content=f"You can process another asset now or check tasks in Assets page",
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
        prefixFile = StrongBodyLabel("File: ")
        prefixFile.setFixedWidth(30)
        subLayout.addWidget(prefixFile)
        self.textFile = BodyLabel("")
        self.textFile.setMaximumWidth(310 - 30)
        subLayout.addWidget(self.textFile)
        spacer = QSpacerItem(20, 2, QSizePolicy.Minimum, QSizePolicy.Minimum)
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
        spacer = QSpacerItem(60, 2, QSizePolicy.Fixed, QSizePolicy.Minimum)
        subLayout.addItem(spacer)
        prefixFolder = StrongBodyLabel("Folder:")
        prefixFolder.setFixedWidth(45)
        subLayout.addWidget(prefixFolder)
        self.textFolder = BodyLabel("")
        self.textFolder.setMaximumWidth(310 - 45)
        subLayout.addWidget(self.textFolder)
        spacer = QSpacerItem(20, 2, QSizePolicy.Minimum, QSizePolicy.Minimum)
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
        labelName = BodyLabel("Name: ")
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
        self.optionModern = PillPushButton("modern")
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 0
        )
        subLayout.addWidget(self.optionDouble, 0, 1)
        subLayout.addWidget(self.optionForce, 0, 2)
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 3
        )
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 0
        )
        subLayout.addWidget(self.optionGPU, 1, 1)
        subLayout.addWidget(self.optionModern, 1, 2)
        subLayout.addItem(
            QSpacerItem(20, 2, QSizePolicy.Expanding, QSizePolicy.Minimum), 1, 3
        )
        self.layout.addLayout(subLayout)

        spacer = QSpacerItem(2, 30, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.layout.addItem(spacer)

        subLayout = QHBoxLayout()
        subLayout.setAlignment(Qt.AlignCenter)
        self.buttonSubmit = PushButton(FIF.SEND, "GO")
        subLayout.addWidget(self.buttonSubmit)
        self.layout.addLayout(subLayout)

        spacer = QSpacerItem(2, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)
