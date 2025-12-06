import os
import datetime
import json
import subprocess
import threading
import socket

import requests
import tzlocal

from qfluentwidgets import SettingCard, InfoBar, InfoBarPosition, TableWidget, PrimaryPushButton, PushButton
from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QTableWidgetItem

import app.utils as utils
from app.config import cfg


class LicenseWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)
        self.loginTuple = loginTuple
        self.url = "https://www.nemopuppet.com/api"

        self.seats = []
        self.seatData = None
        self.machineID = None
        self.hostName = socket.gethostname()

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
                card.setContent("Failed to get machine ID")
                return
            widget.machineID = result.splitlines()[-1].strip()
            card.setContent(self.tr("Machine: ") + widget.machineID)

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
            ts = expires.astimezone(tzlocal.get_localzone())
            self.licenseCard.setTitle(
                self.tr("License")
                + " | "
                + self.tr("Expires at ")
                + ts.strftime("%Y-%m-%d")
            )
            self.buttonDeactivate.setEnabled(True)
            if refresh + datetime.timedelta(days=27) < datetime.datetime.now():
                self.buttonRefresh.setEnabled(True)
            else:
                self.buttonRefresh.setEnabled(False)
        else:
            self.licenseCard.setTitle(self.tr("License") + " | " + self.tr("No License Found"))
            self.buttonDeactivate.setEnabled(False)
            self.buttonRefresh.setEnabled(False)

    def activateSeatLicense(self):
        if not self.machineID:
            InfoBar.error(
                title="Failed to get machine ID",
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
                title="No Seat Selected",
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
                title="Seat Already Taken",
                content=self.tr("This seat has been activated on another machine."),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        data = {"hostname": self.hostName, "machine": self.machineID, "seat": seat['id']}
        recv = requests.post(
            "https://www.nemopuppet.com/api/license/seat/activate", params=data, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        if not recv.ok:
            InfoBar.error(
                title="Failed to get license",
                content=f"Response({recv.status_code}): {recv.text}",
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

        self.getSeatLicense()
        self.fetchSeatLicense()

    def deactivateSeatLicense(self):
        license_path = utils.get_license_path()
        if os.path.exists(license_path):
            os.remove(license_path)
        seat_id = self.seatData['seat_id']
        requests.post(
            "https://www.nemopuppet.com/api/license/seat/deactivate", params={"seat": seat_id}, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        self.getSeatLicense()
        self.fetchSeatLicense()

    def refreshSeatLicense(self):
        seat_id = self.seatData['seat_id']
        recv = requests.post(
            "https://www.nemopuppet.com/api/license/seat/refresh", params={"seat": seat_id}, cookies=self.loginTuple[2],
            proxies=utils.get_proxies()
        )
        if not recv.ok:
            InfoBar.error(
                title="Failed to refresh license",
                content=f"Response({recv.status_code}): {recv.text}",
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

        self.getSeatLicense()
        self.fetchSeatLicense()

    def updateLicenseCard(self):
        if not self.seatData:
            items = self.tableSeats.selectedItems()
            if not items:
                self.buttonActivate.setEnabled(False)
            else:
                self.buttonActivate.setEnabled(True)

    def setup(self):
        self.layout = QVBoxLayout(self)

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
        self.tableSeats.setHorizontalHeaderLabels(["Name", "Product", "Pack", "Months", "Refresh At", "Expires At", "Machine"])
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
        self.buttonActivate.setEnabled(False)
        self.buttonDeactivate.clicked.connect(self.deactivateSeatLicense)