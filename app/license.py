import os
import datetime
import json
import subprocess
import threading
import socket
import platform

import requests
import tzlocal

from qfluentwidgets import SettingCard, PushSettingCard, InfoBar, InfoBarPosition, TableWidget, PrimaryPushButton
from qfluentwidgets import FluentIcon as FIF
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QSpacerItem, QSizePolicy, QTableWidgetItem

import app.utils as utils
from app.config import cfg


class LicenseWidget(QFrame):
    def __init__(self, loginTuple, parent=None):
        super().__init__(parent=parent)
        self.loginTuple = loginTuple
        self.url = "https://www.nemopuppet.com/api"
        self.seat_subscription = []

        self.machineID = None
        self.hostName = socket.gethostname()

        self.setObjectName("License")
        self.setup()

        self.checkFingerprint()
        self.getSeatLicense()
        self.fetchSubscriptionData()

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
            widget.machineID = result.strip()
            card.setContent(self.tr("Machine: ") + widget.machineID)

        thread = threading.Thread(target=run, args=(self, self.licenseCard))
        thread.start()
        thread.join()

    def fetchSubscriptionData(self, refreshUI=True):
        recv = requests.get(self.url + "/users/whoami", proxies=utils.get_proxies(), cookies=self.loginTuple[2])
        subscription = recv.json()['products']
        self.seat_subscription = [x for x in subscription if x['seats'] > 0]
        if not refreshUI:
            return

        self.tableSubscription.setRowCount(len(self.seat_subscription))
        for i, sub in enumerate(self.seat_subscription):
            self.tableSubscription.setItem(i, 0, QTableWidgetItem(sub['product']))
            self.tableSubscription.setItem(i, 1, QTableWidgetItem(str(sub['seats'])))
            self.tableSubscription.setItem(i, 2, QTableWidgetItem(str(sub['months'])))
            self.tableSubscription.setItem(i, 3, QTableWidgetItem(str(sub['softwares'])))
        self.tableSubscription.resizeColumnToContents(0)
        self.tableSubscription.resizeColumnToContents(3)

    def getSeatLicense(self):
        self.expired = None

        license_path = utils.get_license_path()
        if os.path.exists(license_path):
            with open(license_path, "r") as f:
                data = json.loads(json.load(f)["message"])
                if data["machine"] == self.machineID:
                    self.expired = datetime.datetime.fromtimestamp(data["expired_at"])

        if self.expired:
            self.licenseCard.setContent(self.tr("Machine: ") + self.machineID)
            ts = self.expired.astimezone(tzlocal.get_localzone())
            self.licenseCard.setTitle(
                self.tr("License")
                + " | "
                + self.tr("Expired at ")
                + ts.strftime("%Y-%m-%d")
            )
        else:
            self.licenseCard.setTitle(self.tr("License") + " | " + self.tr("No License Found"))

    def updateSeatLicense(self):
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

        if self.tableSubscription.selectedItems() == []:
            InfoBar.error(
                title="No Subscription Selected",
                content=self.tr("Please select a subscription first"),
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=-1,
                parent=self,
            )
            return

        subscription = self.seat_subscription[self.tableSubscription.selectedItems()[0].row()]
        data = {"hostname": self.hostName, "machine": self.machineID, "subscription": subscription['id']}
        recv = requests.post(
            "https://www.nemopuppet.com/api/license/seat/new", params=data, cookies=self.loginTuple[2],
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
        self.fetchSubscriptionData(refreshUI=False)
        self.refreshSubscription()

    def refreshSubscription(self):
        items = self.tableSubscription.selectedItems()
        if not items:
            self.licenseCard.button.setEnabled(False)
            return
        row = items[0].row()
        sub = self.seat_subscription[row]
        seats = sub['authored_seats']
        self.licenseCard.button.setEnabled(sub['seats'] >= len(seats))

        self.tableSeats.setRowCount(len(seats))
        for i, seat in enumerate(seats):
            self.tableSeats.setItem(i, 0, QTableWidgetItem(seat['hostname']))
            self.tableSeats.setItem(i, 1, QTableWidgetItem(seat['applied_at']))
            self.tableSeats.setItem(i, 2, QTableWidgetItem(seat['expired_at']))
            self.tableSeats.setItem(i, 3, QTableWidgetItem(seat['fingerprint']))
        self.tableSeats.resizeColumnsToContents()

    def setup(self):
        self.layout = QVBoxLayout(self)

        self.hostCard = SettingCard(
            FIF.GLOBE,
            self.tr("Host Name"),
            self.hostName
        )
        self.layout.addWidget(self.hostCard)

        spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        self.tableSubscription = TableWidget(self)
        self.tableSubscription.setBorderVisible(True)
        self.tableSubscription.setWordWrap(False)
        self.tableSubscription.verticalHeader().hide()
        self.tableSubscription.setColumnCount(4)
        self.tableSubscription.setHorizontalHeaderLabels(
            [self.tr("Product"), self.tr("Seats"), self.tr("Months"), self.tr("Softwares")])
        self.tableSubscription.itemSelectionChanged.connect(self.refreshSubscription)
        self.layout.addWidget(self.tableSubscription)

        self.tableSeats = TableWidget(self)
        self.tableSeats.setBorderVisible(True)
        self.tableSeats.setWordWrap(False)
        self.tableSeats.verticalHeader().hide()
        self.tableSeats.setColumnCount(4)
        self.tableSeats.setHorizontalHeaderLabels(["Name", "Applied At", "Expires At", "Machine"])
        self.layout.addWidget(self.tableSeats)

        self.licenseCard = PushSettingCard(
            self.tr("Activate"),
            FIF.FINGERPRINT,
            self.tr("License"),
            self.tr("Machine: ") + " Unknown",
        )
        self.licenseCard.clicked.connect(self.updateSeatLicense)
        self.licenseCard.button.setEnabled(False)
        self.layout.addWidget(self.licenseCard)
