import datetime
import os
import socket
import subprocess

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QTableWidgetItem
from qfluentwidgets import SettingCard, InfoBar, InfoBarPosition, TableWidget, PrimaryPushButton, PushButton, MessageDialog, PrimaryPushSettingCard
from qfluentwidgets import FluentIcon as FIF

from app import utils
from app.api import ApiError
from app.license_store import LicenseStore, PendingIssuance, as_datetime, next_month, read_license
from app.worker import Worker


class LicenseWidget(QFrame):
    sessionExpired = Signal()

    def __init__(self, api, parent=None):
        super().__init__(parent=parent)
        self.api = api
        self.seats = []
        self.seatData = None
        self.hostName = socket.gethostname()
        from app.fingerprint import getFingerprint
        self.machineID = getFingerprint() or None
        self.store = LicenseStore(api, utils.get_license_path(), self.machineID, self.hostName)
        self.worker = None
        self._expired = False
        self._reload_after = False
        self.setObjectName('License')
        self.setup()
        self.getSeatLicense()
        self.fetchSeatLicense()

    def _error(self, error):
        if isinstance(error, ApiError) and error.status == 401:
            self._expired = True
            text = self.tr('Your session has expired. Please sign in again. Your offline license is unchanged.')
        elif isinstance(error, ApiError) and error.status == 403:
            text = self.tr('This operation is not allowed or no allocated months remain. Contact your studio administrator.') if self.api.is_subaccount else str(error)
        elif isinstance(error, PendingIssuance):
            text = self.tr('The previous request is not confirmed. Download the current license or retry the same operation. A retry will reuse the original request to avoid spending another month.')
            text += '\n' + str(error)
        else:
            text = str(error)
        if isinstance(error, ApiError) and error.status == 409:
            self._reload_after = True
        InfoBar.error(title=self.tr('License request failed'), content=text, orient=Qt.Horizontal,
                      isClosable=True, position=InfoBarPosition.TOP, duration=-1, parent=self)

    def _run(self, operation, success, reload=False):
        if self.worker is not None:
            return
        self._success_callback = success
        self._reload_after = False
        self._reload_on_success = reload
        self.worker = Worker(operation, self)
        self.worker.succeeded.connect(self._succeeded)
        self.worker.failed.connect(self._error)
        self.worker.finished.connect(self._finished)
        self.updateLicenseCard()
        self.worker.start()

    def _succeeded(self, result):
        try:
            self._success_callback(result)
            self._reload_after = self._reload_on_success
        except Exception as exc:
            self._error(exc)

    def _finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.updateLicenseCard()
        if self._expired:
            self._expired = False
            self.sessionExpired.emit()
        elif self._reload_after:
            self.fetchSeatLicense()

    def selectedSeat(self):
        row = self.tableSeats.currentRow()
        return self.seats[row] if 0 <= row < len(self.seats) else None

    def fetchSeatLicense(self):
        self._run(self.api.licenses, self._show_seats)

    def _show_seats(self, seats):
        previous = self.selectedSeat()
        selected_id = previous['id'] if previous else (self.seatData or {}).get('seat_id')
        self.seats = sorted(seats, key=lambda seat: seat['id'])
        self.tableSeats.blockSignals(True)
        self.tableSeats.setRowCount(len(self.seats))
        selected_row = None
        for row, seat in enumerate(self.seats):
            dates = [as_datetime(seat.get(key)) for key in ('refresh_at', 'to_renew_at', 'expired_at')]
            values = [seat.get('hostname') or '—', seat['product'], seat['pack'],
                      self.tr('{} Months').format(seat['months']),
                      *[value.astimezone().strftime('%Y-%m-%d') if value else '—' for value in dates],
                      seat.get('fingerprint') or '—']
            for column, value in enumerate(values):
                self.tableSeats.setItem(row, column, QTableWidgetItem(value))
            if seat['id'] == selected_id:
                selected_row = row
        if selected_row is not None:
            self.tableSeats.selectRow(selected_row)
        elif self.seats:
            self.tableSeats.selectRow(0)
        self.tableSeats.blockSignals(False)
        self.tableSeats.resizeColumnsToContents()
        for column in range(self.tableSeats.columnCount()):
            heading = self.tableSeats.horizontalHeaderItem(column).text()
            width = self.tableSeats.fontMetrics().horizontalAdvance(heading) + 40
            self.tableSeats.setColumnWidth(column, max(width, self.tableSeats.columnWidth(column)))
        if self.api.is_studio_owner:
            self.infoCard.setContent(self.tr('Use a studio subaccount to activate a license. Your main account can still use conversion and task services.'))
        self.updateLicenseCard()

    def getSeatLicense(self):
        self.seatData = None
        renew_by = None
        try:
            if os.path.exists(self.store.path):
                data = read_license(self.store.path)
                if data['machine'] == self.machineID:
                    renew_by = as_datetime(data.get('to_renew_at'))
                    self.seatData = data
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            self._error(exc)
        self.licenseCard.setContent(self.tr('Machine: ') + (self.machineID or self.tr('Unknown')))
        if renew_by:
            self.licenseCard.setTitle(self.tr('License') + ' | ' + self.tr('Renew by: {date}').format(date=renew_by.astimezone().strftime('%Y-%m-%d %H:%M')))
        else:
            self.licenseCard.setTitle(self.tr('License') + ' | ' + self.tr('No License Found'))
        self.updateLicenseCard()

    def _confirm(self, title, text):
        return MessageDialog(title, text, self.window()).exec()

    def _confirm_overwrite(self, seat):
        if not self.seatData or self.seatData['seat_id'] == seat['id']:
            return True
        return self._confirm(self.tr('Replace local license'), self.tr('This machine has a license from a different seat. Saving this license will replace the local file. Continue?'))

    def _saved(self, data):
        self.getSeatLicense()
        InfoBar.success(title=self.tr('License saved'), content=self.tr('The license is saved locally and can be used offline until its renewal deadline.'),
                        orient=Qt.Horizontal, isClosable=True, position=InfoBarPosition.TOP, duration=5000, parent=self)

    def activateSeatLicense(self):
        seat = self.selectedSeat()
        if not seat or not self.machineID or self.worker:
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        renew_by = as_datetime(seat.get('to_renew_at'))
        same_machine = seat.get('fingerprint') == self.machineID
        if self.api.is_subaccount and same_machine and renew_by and renew_by > now:
            return self.downloadLicense()
        if not self._confirm_overwrite(seat):
            return
        replacement = bool(seat.get('fingerprint') and not same_machine)
        if not self.api.is_subaccount and seat.get('hostname') and seat['hostname'] != self.hostName:
            self._error(ApiError(403, self.tr('This seat has been activated on another machine.')))
            return
        text = self.tr('Activate a license on this machine? This consumes one allocated month. Remaining balance: {months} month(s).').format(months=seat['months'])
        if replacement and self.api.is_subaccount:
            text += '\n\n' + self.tr('Replacing the machine consumes a new month. The old offline license remains valid until its expiry; no time is refunded.')
        if self._confirm(self.tr('Activate License'), text):
            self._run(lambda: self.store.issue('activate', seat, replace_machine=replacement), self._saved, reload=True)

    def downloadLicense(self):
        seat = self.selectedSeat()
        if seat and self._confirm_overwrite(seat):
            self._run(lambda: self.store.download(seat), self._saved, reload=True)

    def refreshSeatLicense(self):
        seat = self.selectedSeat()
        if not seat or self.worker or not self._confirm_overwrite(seat):
            return
        now = datetime.datetime.now(datetime.timezone.utc)
        end = next_month(max(now, as_datetime(seat.get('to_renew_at')) or now))
        text = self.tr('Renewing consumes one allocated month, including an early renewal. The new renewal deadline will be {date}. This charge cannot be reclaimed. Continue?').format(date=end.astimezone().strftime('%Y-%m-%d'))
        if self._confirm(self.tr('Refresh License'), text):
            self._run(lambda: self.store.issue('refresh', seat), self._saved, reload=True)

    def retryPendingLicense(self):
        try:
            pending = self.store.pending()
            if not pending:
                return
            seat = next((item for item in self.seats if item['id'] == pending['payload']['seat']), None)
            if not seat:
                raise PendingIssuance(self.tr('Sign in with the original subaccount and reload its balances to recover this request.'))
            if self._confirm_overwrite(seat) and self._confirm(self.tr('Retry pending request'), self.tr('Retry the interrupted license request? If it already completed, the issued license will be downloaded without another charge.')):
                self._run(lambda: self.store.issue(pending['action'], seat), self._saved, reload=True)
        except Exception as exc:
            self._error(exc)

    def deactivateSeatLicense(self):
        seat = self.selectedSeat()
        if not seat or self.api.is_subaccount or self.worker:
            return
        if self._confirm(self.tr('Deactivate License - Warning'), self.tr('Deactivate this seat and remove its local license? Remaining paid days will not be refunded.')):
            self._run(lambda: self.store.deactivate(seat), lambda _: self.getSeatLicense(), reload=True)

    def updateLicenseCard(self):
        seat = self.selectedSeat()
        ready = bool(seat and self.machineID and self.worker is None and not self.api.is_studio_owner)
        same = bool(seat and seat.get('fingerprint') == self.machineID)
        local_matches = bool(seat and self.seatData and self.seatData.get('seat_id') == seat['id'])
        balance = bool(seat and seat['months'] > 0)
        now = datetime.datetime.now(datetime.timezone.utc)
        renew_by = as_datetime(seat.get('to_renew_at')) if seat else None
        current = bool(same and renew_by and renew_by > now)
        # Studio users can explicitly renew early before a planned offline period.
        renew_allowed = self.api.is_subaccount or bool(renew_by and renew_by - datetime.timedelta(days=5) <= now)
        can_activate = not current if self.api.is_subaccount else not seat or not seat.get('fingerprint')
        self.buttonActivate.setEnabled(ready and balance and can_activate)
        self.buttonRetry.setVisible(self.api.is_subaccount and self.store.pending_path.exists())
        self.buttonRetry.setEnabled(self.worker is None)
        self.buttonRefresh.setEnabled(ready and same and balance and renew_allowed)
        self.buttonDeactivate.setEnabled(ready and same and local_matches and not self.api.is_subaccount)
        self.buttonDownload.setEnabled(ready and same)
        self.buttonReload.setEnabled(self.worker is None)

    def showLicenseFileInFolder(self):
        if self.store.path.exists():
            if os.name == 'nt':
                os.startfile(str(self.store.path.parent))
            else:
                subprocess.Popen(['xdg-open', str(self.store.path.parent)])

    def setup(self):
        self.layout = QVBoxLayout(self)
        self.infoCard = SettingCard(FIF.INFO, self.tr('How Seat Licenses Work'),
            self.tr('Activation and renewal each use one month. The local file works offline until its renewal deadline.\nOverall expiry includes unused months. Downloading an issued license uses no additional months.'))
        self.infoCard.contentLabel.setWordWrap(True)
        self.infoCard.vBoxLayout.setAlignment(self.infoCard.contentLabel, Qt.Alignment())
        self.infoCard.hBoxLayout.setStretch(2, 1)
        self.infoCard.hBoxLayout.setStretch(self.infoCard.hBoxLayout.count() - 1, 0)
        self.infoCard.setFixedHeight(90)
        self.layout.addWidget(self.infoCard)
        self.layout.addWidget(SettingCard(FIF.GLOBE, self.tr('Host Name'), self.hostName))
        self.licenseCard = PrimaryPushSettingCard(self.tr('Show in Folder'), FIF.FINGERPRINT, self.tr('License'), self.tr('Machine: ') + (self.machineID or self.tr('Unknown')))
        self.licenseCard.clicked.connect(self.showLicenseFileInFolder)
        self.layout.addWidget(self.licenseCard)
        self.tableSeats = TableWidget(self)
        self.tableSeats.setBorderVisible(True)
        self.tableSeats.setWordWrap(False)
        self.tableSeats.verticalHeader().hide()
        self.tableSeats.setSelectionBehavior(TableWidget.SelectRows)
        self.tableSeats.setSelectionMode(TableWidget.SingleSelection)
        self.tableSeats.setEditTriggers(TableWidget.NoEditTriggers)
        self.tableSeats.setColumnCount(8)
        self.tableSeats.setHorizontalHeaderLabels([self.tr('Name'), self.tr('Product'), self.tr('Pack'), self.tr('Balance'), self.tr('Period starts'), self.tr('Renew by'), self.tr('Expires'), self.tr('Machine')])
        self.tableSeats.itemSelectionChanged.connect(self.updateLicenseCard)
        self.layout.addWidget(self.tableSeats)
        buttons = QHBoxLayout()
        self.buttonRetry = PushButton(self.tr('Retry pending request'))
        self.layout.addWidget(self.buttonRetry)
        self.buttonRetry.clicked.connect(self.retryPendingLicense)
        self.buttonReload = PushButton(self.tr('Reload balances'))
        self.buttonRefresh = PushButton(self.tr('Refresh'))
        self.buttonDownload = PushButton(self.tr('Download current license'))
        self.buttonDeactivate = PrimaryPushButton(self.tr('Deactivate'))
        self.buttonActivate = PrimaryPushButton(self.tr('Activate'))
        for button in (self.buttonReload, self.buttonRefresh, self.buttonDownload, self.buttonDeactivate, self.buttonActivate):
            buttons.addWidget(button)
        self.buttonDownload.setVisible(self.api.is_subaccount)
        self.buttonDeactivate.setVisible(not self.api.is_subaccount)
        self.buttonReload.clicked.connect(self.fetchSeatLicense)
        self.buttonRefresh.clicked.connect(self.refreshSeatLicense)
        self.buttonDownload.clicked.connect(self.downloadLicense)
        self.buttonDeactivate.clicked.connect(self.deactivateSeatLicense)
        self.buttonActivate.clicked.connect(self.activateSeatLicense)
        self.layout.addLayout(buttons)
