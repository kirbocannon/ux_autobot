import os
import time
import json
import logging
import functools
from typing import Optional, List, Dict
from utils.applogger import apptest_logger

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from utils.data import load_yaml, get_abs_path
from utils.metrics import ms_to_s
from utils.system import kill_existing_proc

#from browsermobproxy import Server

PATH = get_abs_path(__file__)
PATH_WINDOWS = str(PATH.parent).replace(r'/', r'\\')

PROCS_TO_KILL = ["firefox.exe"]
WINDOWS_PROCS_TO_KILL = ["firefox.exe"]
BASE_EXTENSIONS = [
    "har_export_trigger-0.6.1-an+fx.xpi",
    "header_mod.xpi"
    ]


class FireFoxBrowser: # TODO: add baseclass for browser
    def __init__(
        self,
        host_type: Optional[str] = "windows" if os.name == "nt" else "linux",
        webdriver_path: Optional[str] = "drivers/geckodriver",
        process_kill_wait: Optional[int] = 5,
        har_session_name: Optional[str] = "networkanalysis",
        har_location: Optional[str] = f"{PATH.parent}\hars",
        har_filename: Optional[str] = "harfile",
        extension_path: Optional[str] = None,
        extension_names: Optional[List[str]] = None,
        enable_quic: Optional[bool] = True,
        options: Optional[List[str]] = None,
        headers: Optional[List[Dict[str, str]]] = None
    ):
        if host_type == "windows":
            if not extension_path:
                extension_path = f"{PATH_WINDOWS}\extensions\\firefox\\"

            self._procs_to_kill = WINDOWS_PROCS_TO_KILL

        elif host_type == "linux":
            if not extension_path:
                extension_path = f"{PATH}\extensions\\firefox\\"

            self._procs_to_kill = LINUX_PROCS_TO_KILL

        if not extension_names:
            self.extension_names = BASE_EXTENSIONS
        else:
            self.extension_names = self.extension_names + BASE_EXTENSIONS

        self.profile = webdriver.FirefoxProfile()
        self.driver = None
        self.process_kill_wait = process_kill_wait
        self.webdriver_path = webdriver_path
        self.har_session_name = har_session_name
        self.har_location = har_location
        self.har_filename = har_filename
        self.extension_path = extension_path
        self.har = None
        self.enable_quic = enable_quic
        self.options = options
        self.headers = headers

    def __enter__(self):
        self._build_options()
        kill_existing_proc(self._procs_to_kill, self.process_kill_wait)
        self._build_profile()
        self.driver = webdriver.Firefox(
            executable_path=self.webdriver_path, 
            firefox_profile=self.profile,
            options=self.options
        )

        # Add extensions here
        for extension_name in self.extension_names:
            self.driver.install_addon(self.extension_path + extension_name, temporary=True)
            self.driver.firefox_profile.add_extension(extension=self.extension_path + extension_name)

        # add custom headers here
        if self.headers:
            _ = self._insert_headers(self.headers)

        return self

    @property
    @functools.lru_cache()
    def _extension_mappings(self):
        with open(f"{self.extension_path}mappings.json") as f:
            data = f.read()
        
        return data

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type or exc_val or exc_tb):
            apptest_logger.debug(f"{exc_type} | {exc_val} | {exc_tb}")

        # inject javascript to request HAR file, then download it automatically
        self.driver.execute_script(
            f"""
                HAR.triggerExport().then(harFile => {{
                    let bb = new Blob([JSON.stringify({{log: harFile}}) ], {{ type: 'application/json' }});
                    let a = document.createElement('a');
                    a.download = '{self.har_filename}.har';
                    a.href = window.URL.createObjectURL(bb);
                    a.click();
                }});
            """)

        # wait a bit for cleanup
        time.sleep(20)

        self.driver.quit()
        return True

    def _build_options(self):
        """
            Options to include on FireFox start such as --headless and --devtools
            By default we add --devtools argument. 
        """
        if not self.options:
            self.options = Options()
            self.options.add_argument("--devtools")
        else:
            options_to_add = copy(self.options)
            self.options = Options()
            for argument in self.options:
                self.options.add_argument(argument)
        
        # set the default downloads directory to be the har location directory
        self.options.set_preference("browser.download.useDownloadDir", True)
        self.options.set_preference("browser.download.dir", self.har_location)
        return
        
    def _build_profile(self):
        # QUIC Settings
        self.profile.set_preference("http3", self.enable_quic)
        self.profile.set_preference("network.http.http3.enabled", self.enable_quic)

        # Disable Browser Cache
        self.profile.set_preference("browser.cache.disk.enable", False) # TODO: doesn't work
        self.profile.set_preference("browser.cache.memory.enable", False)
        self.profile.set_preference("browser.cache.check_doc_frequency", 1)

        # enable automatic HAR file export
        self.profile.set_preference("devtools.netmonitor.har.defaultLogDir", self.har_location)
        self.profile.set_preference("devtools.netmonitor.har.includeResponseBodies", False)
        self.profile.set_preference("devtools.netmonitor.har.forceExport", True)
        self.profile.set_preference("extensions.netmonitor.har.enableAutomation", True)
        self.profile.set_preference("extensions.netmonitor.har.contentAPIToken", "test") # Har trigger by script injected into page
        self.profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/json")
        self.profile.set_preference("browser.download.folderList", 2)

        # Statically set uuids for base extensions TODO: (very small chance of collision, try to make dynamic in future)
        self.profile.set_preference("extensions.webextensions.uuids", self._extension_mappings)

        self.profile.webdriver_accept_untrusted_certs = True
        self.profile.update_preferences()
        return

    def _insert_headers(self, headers: List[Dict[str, str]]) -> None:
        """
            Inserts a header into the "Modify Header Value" extension 
            which will send a specified header key/value pair to the specified
            url for every request. This extension is installed as one of the base 
            extensions for this program. More info: https://addons.mozilla.org/en-US/firefox/addon/modify-header-value/
        """

        # go to extension's option page
        # format to get to an extension's page should be like the following: #moz-extension://2bd549f8-aeba-40db-a51c-398f96c7ec16/data/options/options.html
        self.driver.get(f"moz-extension://{json.loads(self._extension_mappings)['jid0-oEwF5ZcskGhjFv4Kk4lYc@jetpack']}/data/options/options.html")

        for header in headers:
            _ = self._insert_header(**header)
        
        return

    def _insert_header(self, url: str, header_key: str, header_value: str) -> None:
        # set url
        url_box = self.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='URL (i.e. https://www.google.com/ or *)']"
        )
        url_box.clear()
        url_box.send_keys(url)
        
        # set header name
        header_key_box = self.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='name (i.e. User-Agent)']"
        )
        header_key_box.clear()
        header_key_box.send_keys(header_key)

        # set header value
        header_value_box = self.driver.find_element(
            By.CSS_SELECTOR, "input[title='Enter a valid value']"
        )
        header_value_box.clear()
        header_value_box.send_keys(header_value)

        header_value_box.send_keys(Keys.ENTER)

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
