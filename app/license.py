import os
import datetime
import json
import subprocess
import threading
import socket

import requests
import tzlocal

from qfluentwidgets import SettingCard, InfoBar, InfoBarPosition, TableWidget, PrimaryPushButton, PushButton, MessageDialog
from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QTableWidgetItem

import app.utils as utils
from app.config import cfg, get_api_domain


class LicenseWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)
        self.loginTuple = loginTuple
        self.url = f"https://www.{get_api_domain()}/api"

        self.seats = []
        self.seatData = None
        self.machineID = None
        self.hostName = socket.gethostname()

        self.refreshEnabled = False
        self.deactivateEnabled = False

        self.setObjectName("License")
        self.setup()

        self.checkFingerprint()
        self.getSeatLicense()
        self.fetchSeatLicense()

    def checkFingerprint(self):
        def run(widget, card):
            if not cfg.mayaVersion.value:
                return
            try:
                result = utils.call_maya(
                    [
                        "import NemoMaya",
                        "print(NemoMaya.getFingerprint())",
                    ]
                )
                if not result:
                    return
            except subprocess.CalledProcessError:
                widget.machineID = None
                card.setContent(widget.tr("Failed to get machine ID"))
                return
            widget.machineID = result.splitlines()[-1].strip()
            card.setContent(widget.tr("Machine: ") + widget.machineID)

        thread = threading.Thread(target=run, args=(self, self.licenseCard))
        thread.start()
        thread.join()

    def fetchSeatLicense(self):
        recv = requests.get(self.url + "/users/whoami", proxies=utils.get_proxies(), cookies=self.loginTuple[2])
        self.seats = sorted(recv.json()['seats'], key=lambda x: x['id'])

        self.tableSeats.setRowCount(len(self.seats))
        for i, seat in enumerate(self.seats):
            self.tableSeats.setItem(i, 0, QTableWidgetItem(seat['hostname']))
            self.tableSeats.setItem(i, 1, QTableWidgetItem(str(seat['product'])))
            self.tableSeats.setItem(i, 2, QTableWidgetItem(str(seat['pack'])))
            self.tableSeats.setItem(i, 3, QTableWidgetItem(str(seat['months'])))
            if seat['refresh_at']:
                time = datetime.datetime.fromisoformat(seat['refresh_at'])
                self.tableSeats.setItem(i, 4, QTableWidgetItem(str(time.date())))
            else:
                self.tableSeats.setItem(i, 4, QTableWidgetItem('N/A'))
            if seat['expired_at']:
                time = datetime.datetime.fromisoformat(seat['expired_at'])
                self.tableSeats.setItem(i, 5, QTableWidgetItem(str(time.date())))
            else:
                self.tableSeats.setItem(i, 5, QTableWidgetItem('N/A'))
            self.tableSeats.setItem(i, 6, QTableWidgetItem(str(seat['fingerprint'])))
        self.tableSeats.resizeColumnsToContents()

    def get_next_renew_date(self, data):
        refresh = datetime.datetime.fromtimestamp(data["refresh_at"])
        if 'to_renew_at' in data:
            to_renew = datetime.datetime.fromtimestamp(data["to_renew_at"])
        else:
            to_renew = refresh + datetime.timedelta(days=30)
        return to_renew

    def getSeatLicense(self):
        self.seatData = None
        expires = None

        license_path = utils.get_license_path()
        if os.path.exists(license_path):
            with open(license_path, "r") as f:
                data = json.loads(json.load(f)["message"])
                if data["machine"] == self.machineID:
                    self.seatData = data
                    refresh = datetime.datetime.fromtimestamp(data["refresh_at"])
                    expires = datetime.datetime.fromtimestamp(data["expires_at"])

        if expires:
            self.licenseCard.setContent(self.tr("Machine: ") + self.machineID)
            title = self.tr("License")
            ts = expires.astimezone(tzlocal.get_localzone())
            title += " | " + self.tr("Expires at {date}").format(date=ts.strftime("%Y-%m-%d"))
            to_renew = self.get_next_renew_date(self.seatData)
            remaining_days = max(0, (to_renew - datetime.datetime.now()).days)
            title += " | " + self.tr("Pause in {days} days").format(days=remaining_days)
            self.licenseCard.setTitle(title)
            self.deactivateEnabled = True
            if refresh + datetime.timedelta(days=25) < datetime.datetime.now():
                self.refreshEnabled = True
            else:
                self.refreshEnabled = False
        else:
            self.licenseCard.setTitle(self.tr("License") + " | " + self.tr("No License Found"))

    def activateSeatLicense(self):
        if not self.machineID:
            InfoBar.error(
                title=self.tr("Failed to get machine ID"),
                content=self.tr("Machine ID should be generated first"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        if self.tableSeats.selectedItems() == []:
            InfoBar.error(
                title=self.tr("No Seat Selected"),
                content=self.tr("Please select a seat first"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        seat = self.seats[self.tableSeats.selectedItems()[0].row()]
        if seat['hostname']:
            InfoBar.error(
                title=self.tr("Seat Already Taken"),
                content=self.tr("This seat has been activated on another machine."),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        remaining_months = seat['months']
        title = self.tr("Activate License")
        to_renew = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        content = self.tr(
            "You are about to activate a license on this machine.<br><br>"
            "This will consume 1 month from your balance (Currently: {months} months)<br>"
            "The license will be valid for one calendar month on this machine only.<br>"
            "You will need to manually refresh it around {date} to continue using it.<br>"
            "Do you want to continue?"
        ).format(months=remaining_months, date=to_renew)

        parent = self.window()
        dialog = MessageDialog(title, content, parent)

        if not dialog.exec():
            return

        data = {"hostname": self.hostName, "machine": self.machineID, "seat": seat['id']}
        recv = requests.post(
            f"https://www.{get_api_domain()}/api/license/seat/activate", params=data, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        if not recv.ok:
            InfoBar.error(
                title=self.tr("Failed to get license"),
                content=self.tr("Response({code}): {text}").format(code=recv.status_code, text=recv.text),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        license = recv.json()
        license_path = utils.get_license_path()
        with open(license_path, "w") as f:
            json.dump(license, f, indent=4)

        InfoBar.success(
            title=self.tr("License Activated"),
            content=self.tr("License activated successfully! Valid for one month."),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self,
        )

        self.getSeatLicense()
        self.fetchSeatLicense()

    def deactivateSeatLicense(self):
        title = self.tr("Deactivate License - Warning")
        expires = datetime.datetime.fromtimestamp(self.seatData["to_renew_at"])
        remaining_days = max(0, (expires - datetime.datetime.now()).days)

        content = self.tr(
            "<b>IMPORTANT: Deactivating will permanently lose your remaining days!</b><br><br>"
            "<b>You have {days} days remaining in this license period.</b><br><br>"
            "• These days will NOT be refunded to your account<br>"
            "• Activating on another machine will consume a new month from your balance<br><br>"
            "This action is designed to prevent license abuse. Only deactivate if you're "
            "permanently moving to a different machine.<br><br>"
            "Are you sure you want to continue?"
        ).format(days=remaining_days)

        # Get parent window for dialog
        parent = self.window()
        dialog = MessageDialog(title, content, parent)

        # Only proceed if user confirms
        if not dialog.exec():
            return

        license_path = utils.get_license_path()
        if os.path.exists(license_path):
            os.remove(license_path)
        seat_id = self.seatData['seat_id']
        requests.post(
            f"https://www.{get_api_domain()}/api/license/seat/deactivate", params={"seat": seat_id}, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        self.getSeatLicense()
        self.fetchSeatLicense()

    def refreshSeatLicense(self):
        title = self.tr("Refresh License")

        to_renew = self.get_next_renew_date(self.seatData).strftime("%Y-%m-%d")
        content = self.tr(
            "Refreshing extends your license for one calendar month and <b>consumes 1 month from your account balance.<b><br>"
            "You must manually refresh your license around {date} to continue using it.<br>"
            "If you don't refresh, the license will pause and billing will stop.<br>"
            "Do you want to continue?"
        ).format(date=to_renew)

        parent = self.window()
        dialog = MessageDialog(title, content, parent)

        if not dialog.exec():
            return

        seat_id = self.seatData['seat_id']
        recv = requests.post(
            f"https://www.{get_api_domain()}/api/license/seat/refresh", params={"seat": seat_id}, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        if not recv.ok:
            InfoBar.error(
                title=self.tr("Failed to refresh license"),
                content=self.tr("Response({code}): {text}").format(code=recv.status_code, text=recv.text),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        license = recv.json()
        license_path = utils.get_license_path()
        with open(license_path, "w") as f:
            json.dump(license, f, indent=4)

        InfoBar.success(
            title=self.tr("License Refreshed"),
            content=self.tr("License has been refreshed successfully! Valid for another month."),
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=5000,
            parent=self,
        )

        self.getSeatLicense()
        self.fetchSeatLicense()

    def updateLicenseCard(self):
        items = self.tableSeats.selectedItems()
        if not self.seatData:
            if not items:
                self.buttonActivate.setEnabled(False)
            else:
                self.buttonActivate.setEnabled(True)
        else:
            itemMachine = items[-1]
            if str(self.seatData['machine']) == itemMachine.text():
                if self.refreshEnabled:
                    self.buttonRefresh.setEnabled(True)
                if self.deactivateEnabled:
                    self.buttonDeactivate.setEnabled(True)
            else:
                self.buttonRefresh.setEnabled(False)
                self.buttonDeactivate.setEnabled(False)

    def setup(self):
        self.layout = QVBoxLayout(self)

        # Add informational card explaining the license system
        self.infoCard = SettingCard(
            FIF.INFO,
            self.tr("How Seat Licenses Work"),
            self.tr(
                "Each activation consumes one month from your balance and needs to be refreshed after one calendar month. <br>"
                "The license will automatically pause and billing will stop if you don’t manually refresh it each month. <br>"
            )
        )
        self.layout.addWidget(self.infoCard)

        self.hostCard = SettingCard(
            FIF.GLOBE,
            self.tr("Host Name"),
            self.hostName
        )
        self.layout.addWidget(self.hostCard)

        self.licenseCard = SettingCard(
            FIF.FINGERPRINT,
            self.tr("License"),
            self.tr("Machine: ") + " Unknown",
        )
        self.layout.addWidget(self.licenseCard)

        self.tableSeats = TableWidget(self)
        self.tableSeats.setBorderVisible(True)
        self.tableSeats.setWordWrap(False)
        self.tableSeats.verticalHeader().hide()
        self.tableSeats.setColumnCount(7)
        self.tableSeats.setHorizontalHeaderLabels([self.tr("Name"), self.tr("Product"), self.tr("Pack"), self.tr("Remaining Months"), self.tr("Refreshed At"), self.tr("Expires At"), self.tr("Machine")])
        self.tableSeats.itemSelectionChanged.connect(self.updateLicenseCard)
        self.layout.addWidget(self.tableSeats)

        buttons = QHBoxLayout()
        self.buttonRefresh = PushButton(self.tr("Refresh"))
        self.buttonDeactivate = PrimaryPushButton(self.tr("Deactivate"))
        self.buttonActivate = PrimaryPushButton(self.tr("Activate"))
        buttons.addWidget(self.buttonRefresh)
        buttons.addWidget(self.buttonDeactivate)
        buttons.addWidget(self.buttonActivate)
        self.layout.addLayout(buttons)

        self.buttonRefresh.clicked.connect(self.refreshSeatLicense)
        self.buttonActivate.clicked.connect(self.activateSeatLicense)
        self.buttonDeactivate.clicked.connect(self.deactivateSeatLicense)

        self.buttonRefresh.setEnabled(False)
        self.buttonActivate.setEnabled(False)
        self.buttonDeactivate.setEnabled(False)