import os
import sys

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QTextBrowser,
    QTableWidgetItem,
    QAbstractItemView,
)
from qfluentwidgets import TableWidget, PushButton

from app.tasks import tasks, active_tasks


class AssetsWidget(QFrame):
    activeTasksChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("Tasks Farm")

        self.setup()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onRefresh)
        self.timer.start(100)

    def onCurrentCellChanged(self, currRow, _0, _1, _2):
        if currRow < 0:
            self.log.clear()
            return
        self.log.setText(tasks[currRow].message)

        scrollBar = self.log.verticalScrollBar()
        scrollBar.setValue(scrollBar.maximum())

    def onShowInFolder(self):
        row = self.table.currentRow()
        if row < 0:
            return
        os.startfile(tasks[row].folder)

    def onClose(self):
        row = self.table.currentRow()
        if row < 0:
            return
        tasks[row].close()
        self.activeTasksChanged.emit(len(active_tasks()))

    def onRefresh(self):
        self.refreshTable()

        row = self.table.currentRow()
        if row < 0:
            return

        task = tasks[row]
        if not task.active():
            return

        task.refresh()
        self.table.setItem(row, 1, QTableWidgetItem(task.status))
        scrollBar = self.log.verticalScrollBar()
        # scrollToBottom = scrollBar.value() == scrollBar.maximum()
        self.log.setText(task.message)
        # if scrollToBottom:
        scrollBar = self.log.verticalScrollBar()
        scrollBar.setValue(scrollBar.maximum())

        if not task.active():
            self.activeTasksChanged.emit(len(active_tasks()))

    def refreshTable(self):
        currRowCount = self.table.rowCount()
        if len(tasks) == currRowCount:
            return

        self.activeTasksChanged.emit(len(active_tasks()))
        self.table.setRowCount(len(tasks))
        for i in range(currRowCount, len(tasks)):
            task = tasks[i]
            self.table.setItem(i, 0, QTableWidgetItem(task.name))
            self.table.setItem(i, 1, QTableWidgetItem(task.status))
            self.table.setItem(i, 2, QTableWidgetItem(task.folder))
        self.table.resizeColumnsToContents()

    def setup(self):
        self.layout = QVBoxLayout(self)

        self.table = TableWidget(self)
        self.table.setBorderVisible(True)
        self.table.setBorderRadius(8)

        self.table.setWordWrap(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Name", "Status", "Output Folder"])
        self.table.currentCellChanged.connect(self.onCurrentCellChanged)
        self.layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()

        self.log = QTextBrowser()
        self.log.setFixedHeight(200)
        bottom_layout.addWidget(self.log)

        buttons_layout = QVBoxLayout()
        self.btn_show = PushButton("Show in Folder")
        self.btn_show.clicked.connect(self.onShowInFolder)
        self.btn_retry = PushButton("Retry")
        self.btn_stop = PushButton("Stop")
        self.btn_stop.clicked.connect(self.onClose)
        self.btn_refresh = PushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refreshTable)
        buttons_layout.addWidget(self.btn_show)
        buttons_layout.addWidget(self.btn_retry)
        buttons_layout.addWidget(self.btn_stop)
        buttons_layout.addWidget(self.btn_refresh)
        bottom_layout.addLayout(buttons_layout)

        self.layout.addLayout(bottom_layout)
