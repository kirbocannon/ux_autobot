import os
import time
import logging
from typing import Optional

from utils.applogger import apptest_logger

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils.data import load_yaml, get_abs_path
from utils.metrics import ms_to_s
from utils.system import kill_existing_proc

from browsermobproxy import Server

PATH = get_abs_path(__file__)

PROCS_TO_KILL = ["java.exe", "firefox.exe", "browsermob-proxy"]
PROXY_SERVER_PATH = f"{PATH}/modules/browsermob-proxy-2.1.4/bin/browsermob-proxy.bat"
WINDOWS_PROCS_TO_KILL = ["java.exe", "firefox.exe", "browsermob-proxy"]
LINUX_PROCS_TO_KILL = ["browsermob-prox", "browsermob-proxy", "java"]
WINDOWS_PROXY_SERVER_PATH = (
    f"{PATH}\\browsermob-proxy-2.1.4\\bin\\browsermob-proxy.bat"
)
LINUX_PROXY_SERVER_PATH = (
    f"{PATH}/modules/browsermob-proxy-2.1.4/bin/browsermob-proxy.bat"
)


class FireFoxBrowser: # TODO: add baseclass for browser
    def __init__(
        self,
        host_type: Optional[str] = "windows" if os.name == "nt" else "linux",
        proxy_server_port: Optional[int] = 9091,
        proxy_server_path: Optional[str] = None,
        webdriver_path: Optional[str] = "drivers/geckodriver",
        process_kill_wait: Optional[int] = 5,
        har_name: Optional[str] = "networkanalysis",
    ):
        if host_type == "windows" and not proxy_server_path:
            self.proxy_server_path = WINDOWS_PROXY_SERVER_PATH
            self._procs_to_kill = WINDOWS_PROCS_TO_KILL

        elif host_type == "linux" and not proxy_server_path:
            self.proxy_server_path = LINUX_PROXY_SERVER_PATH
            self._procs_to_kill = LINUX_PROCS_TO_KILL

        self.profile = webdriver.FirefoxProfile()
        self.proxy_server_port = proxy_server_port
        self.proxy_server = None
        self.proxy = None
        self.driver = None
        self.process_kill_wait = process_kill_wait
        self.webdriver_path = webdriver_path
        self.har_name = har_name
        self.har = None

    def __enter__(self):
        _ = kill_existing_proc(self._procs_to_kill, self.process_kill_wait)
        self.proxy_server = Server(
            self.proxy_server_path, options=dict(port=self.proxy_server_port)
        )
        self.proxy_server.start()
        self.proxy = self.proxy_server.create_proxy(params={"trustAllServers": "true"})
        self._build_profile()
        self.driver = webdriver.Firefox(
            executable_path=self.webdriver_path, firefox_profile=self.profile
        )
        self.proxy.new_har(self.har_name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        apptest_logger.debug(f"{exc_type} | {exc_val} | {exc_tb}")
        self.har = self.proxy.har
        self.proxy_server.stop()
        _ = kill_existing_proc(self._procs_to_kill, self.process_kill_wait)
        return True

    def _build_profile(self):
        self.profile.set_preference("network.proxy.type", 1)
        self.profile.set_preference("network.proxy.http", "localhost")
        self.profile.set_preference("network.proxy.http_port", self.proxy.port)
        self.profile.set_preference("network.proxy.ssl", "localhost")
        self.profile.set_preference("network.proxy.ssl_port", self.proxy.port)
        self.profile.webdriver_accept_untrusted_certs = True
        self.profile.update_preferences()
        return


def scrolldown(
    driver: webdriver, cnt: Optional[int] = 1, delay: Optional[int] = 5
) -> None:
    scroll_script = "window.scrollTo(0, document.body.scrollHeight);var scrolldown=document.body.scrollHeight;return scrolldown;"
    for i in range(0, cnt):
        driver.execute_script(scroll_script)
        time.sleep(delay)

    return


def scrollup(
    driver: webdriver, cnt: Optional[int] = 1, delay: Optional[int] = 5
) -> None:
    scroll_script = "window.scrollTo(0, document.body.scrollHeight);var scrollup=document.body.scrollHeight;return scrollup;"
    for i in range(0, cnt):
        driver.execute_script(scroll_script)
        time.sleep(delay)

    return
