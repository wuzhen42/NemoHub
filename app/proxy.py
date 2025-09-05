import threading
from proxy import entry_point
import sys
import os
import signal
import socket

from qfluentwidgets import (
    qconfig,
    TogglePushButton,
    CompactSpinBox,
    LineEdit,
    DisplayLabel,
    SettingCard,
)

from app.config import cfg


class ProxySettingsCard(SettingCard):
    def __init__(self, icon, title, content=None, parent=None):
        super().__init__(icon, title, content, parent)

        self.addressInput = LineEdit()
        self.addressInput.setClearButtonEnabled(True)
        self.addressInput.setMinimumWidth(200)
        self.addressInput.setText(qconfig.get(cfg.proxyServerAddress))
        self.hBoxLayout.addWidget(DisplayLabel('Proxy Server: '))
        self.hBoxLayout.addWidget(self.addressInput)

        self.portInput = CompactSpinBox()
        self.portInput.setMinimum(0)
        self.portInput.setMaximum(9999)
        self.portInput.setValue(qconfig.get(cfg.proxyServerPort))
        self.hBoxLayout.addWidget(DisplayLabel('Port: '))
        self.hBoxLayout.addWidget(self.portInput)

        self.hostToggle = TogglePushButton("Host here")
        self.hBoxLayout.addWidget(self.hostToggle)
        self.hBoxLayout.setSpacing(5)

        self.addressInput.textChanged.connect(lambda text: qconfig.set(cfg.proxyServerAddress, text))
        self.portInput.valueChanged.connect(lambda value: qconfig.set(cfg.proxyServerPort, value))
        self.hostToggle.clicked.connect(lambda: self.toggleHost(self.hostToggle.isChecked()))

        self.proxyManager = ProxyManager()

    def toggleHost(self, host):
        self.addressInput.setDisabled(host)
        self.portInput.setDisabled(host)
        if host:
            ip = get_local_ip()
            if ip:
                self.addressInput.setText('http://' + ip)
            else:
                self.addressInput.clear()
            self.proxyManager.start_proxy(self.portInput.value())
        else:
            self.proxyManager.stop_proxy()


def get_local_ip():
    # Connect to a remote address (doesn't actually send data)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    local_ip = s.getsockname()[0]
    s.close()
    return local_ip


class ProxyManager:
    def __init__(self):
        self.proxy_thread = None
        self.running = False
        self.original_sigint_handler = None

    def start_proxy(self, port=9000):
        """Start proxy server in a separate thread"""
        if self.proxy_thread and self.proxy_thread.is_alive():
            print("Proxy already running")
            return

        self.running = True
        self.proxy_thread = threading.Thread(
            target=self._run_proxy,
            args=(port,),
            daemon=True
        )
        self.proxy_thread.start()
        print(f"Proxy started on port {port}")

    def _run_proxy(self, port):
        """Internal method to run proxy"""
        try:
            # Set up signal handler only for this thread
            def signal_handler(signum, frame):
                print("Proxy received stop signal")
                raise KeyboardInterrupt("Proxy stopped")

            # Store original handler
            if threading.current_thread() is threading.main_thread():
                original_handler = signal.signal(signal.SIGINT, signal_handler)

            # Override sys.argv for proxy.py
            original_argv = sys.argv.copy()
            sys.argv = [
                'proxy',
                '--hostname', '0.0.0.0',
                '--port', str(port)
            ]

            entry_point()

        except KeyboardInterrupt:
            print("Proxy stopped gracefully")
        except Exception as e:
            print(f"Proxy error: {e}")
        finally:
            # Restore original argv
            sys.argv = original_argv
            self.running = False

            # Restore signal handler if we're in main thread
            if threading.current_thread() is threading.main_thread() and 'original_handler' in locals():
                signal.signal(signal.SIGINT, original_handler)

    def stop_proxy(self):
        """Stop the proxy server"""
        if not self.running:
            print("Proxy is not running")
            return

        try:
            # Get the thread ID and send signal
            if self.proxy_thread and self.proxy_thread.is_alive():
                print("Requesting proxy stop...")

                # Set running flag to False
                self.running = False

                # Try to interrupt the proxy thread by raising exception
                import ctypes
                thread_id = self.proxy_thread.ident
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_long(thread_id),
                    ctypes.py_object(KeyboardInterrupt)
                )

                if res > 1:
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                    print("Failed to stop proxy thread")
                else:
                    # Wait for thread to finish
                    self.proxy_thread.join(timeout=5)
                    if self.proxy_thread.is_alive():
                        print("Warning: Proxy thread didn't stop cleanly")
                    else:
                        print("Proxy stopped successfully")

        except Exception as e:
            print(f"Error stopping proxy: {e}")
        finally:
            self.running = False

    def is_running(self):
        """Check if proxy is running"""
        return self.running and self.proxy_thread and self.proxy_thread.is_alive()
