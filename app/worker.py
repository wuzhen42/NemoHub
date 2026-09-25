from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    succeeded = Signal(object)
    failed = Signal(object)

    def __init__(self, operation, parent=None):
        super().__init__(parent)
        self.operation = operation

    def run(self):
        try:
            self.succeeded.emit(self.operation())
        except Exception as exc:
            self.failed.emit(exc)
