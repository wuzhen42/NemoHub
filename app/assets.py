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

        self.setup()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.onRefresh)
        self.timer.start(100)

    def getStatusColor(self, status):
        """Return background color based on task status"""
        if status == "Success":
            return QColor(220, 247, 220)  # Very light green
        elif "Error" in status or "Failed" in status:
            return QColor(255, 220, 220)  # Very light red
        elif "Running" in status or status == "Waiting":
            return QColor(255, 252, 220)  # Very light yellow
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

        row = self.table.currentRow()
        if row < 0:
            return

        task = tasks[row]
        task.refresh()

        # Update status and apply background color
        color = self.getStatusColor(task.status)
        status_item = QTableWidgetItem(task.status)
        if color:
            status_item.setBackground(color)
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(color)
        self.table.setItem(row, 1, status_item)

        # Store scroll position and determine if user is at bottom
        scrollBar = self.log.verticalScrollBar()
        old_value = scrollBar.value()
        old_max = scrollBar.maximum()
        was_at_bottom = (old_value >= old_max - 10) if old_max > 0 else True

        # Only update text if it changed
        if self.log.toPlainText() != task.message:
            self.log.setText(task.message)

            # Auto-scroll only if user was already at bottom
            if was_at_bottom:
                scrollBar = self.log.verticalScrollBar()
                scrollBar.setValue(scrollBar.maximum())
            else:
                # Try to maintain relative position
                scrollBar = self.log.verticalScrollBar()
                scrollBar.setValue(old_value)

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
            name_item = QTableWidgetItem(task.name)
            status_item = QTableWidgetItem(task.status)
            folder_item = QTableWidgetItem(task.folder)

            # Apply background color based on status
            color = self.getStatusColor(task.status)
            if color:
                name_item.setBackground(color)
                status_item.setBackground(color)
                folder_item.setBackground(color)

            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, status_item)
            self.table.setItem(i, 2, folder_item)
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
