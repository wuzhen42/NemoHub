import os

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QColor
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
        self.last_active_count = 0

        self.setup()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onRefresh)
        self.timer.start(100)

    def getStatusColor(self, status):
        """Return background color based on task status"""
        if status == "Success":
            return QColor(144, 238, 144)  # Light green
        elif "Error" in status or "Failed" in status:
            return QColor(255, 182, 193)  # Light red
        elif "Running" in status or status == "Waiting":
            return QColor(255, 255, 153)  # Light yellow
        else:
            return None  # Default (no color)

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

        for i, task in enumerate(tasks):
            if task.active():
                task.refresh()
                status_item = self.table.item(i, 1)
                if status_item:
                    status_item.setText(task.status)
                color = self.getStatusColor(task.status)
                for col in range(self.table.columnCount()):
                    item = self.table.item(i, col)
                    if item and color:
                        item.setBackground(color)
        self.table.resizeColumnsToContents()

        current_active = len(active_tasks())
        if self.last_active_count != current_active:
            self.last_active_count = current_active
            self.activeTasksChanged.emit(current_active)

        # Update log view only for the currently selected task
        row = self.table.currentRow()
        if row < 0:
            return

        task = tasks[row]

        scrollBar = self.log.verticalScrollBar()
        old_value = scrollBar.value()
        old_max = scrollBar.maximum()
        was_at_bottom = (old_value >= old_max - 10) if old_max > 0 else True

        if self.log.toPlainText() != task.message:
            self.log.setText(task.message)

            if was_at_bottom:
                scrollBar = self.log.verticalScrollBar()
                scrollBar.setValue(scrollBar.maximum())
            else:
                scrollBar = self.log.verticalScrollBar()
                scrollBar.setValue(old_value)

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
        self.table.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Status"), self.tr("Output Folder")])
        self.table.currentCellChanged.connect(self.onCurrentCellChanged)
        self.layout.addWidget(self.table)

        bottom_layout = QHBoxLayout()

        self.log = QTextBrowser()
        self.log.setFixedHeight(200)
        bottom_layout.addWidget(self.log)

        buttons_layout = QVBoxLayout()
        self.btn_show = PushButton(self.tr("Show in Folder"))
        self.btn_show.clicked.connect(self.onShowInFolder)
        self.btn_retry = PushButton(self.tr("Retry"))
        self.btn_stop = PushButton(self.tr("Stop"))
        self.btn_stop.clicked.connect(self.onClose)
        self.btn_refresh = PushButton(self.tr("Refresh"))
        self.btn_refresh.clicked.connect(self.refreshTable)
        buttons_layout.addWidget(self.btn_show)
        buttons_layout.addWidget(self.btn_retry)
        buttons_layout.addWidget(self.btn_stop)
        buttons_layout.addWidget(self.btn_refresh)
        bottom_layout.addLayout(buttons_layout)

        self.layout.addLayout(bottom_layout)
