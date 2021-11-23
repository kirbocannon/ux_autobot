import os
import time
import logging
from typing import Optional, List

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

#PROCS_TO_KILL = ["java.exe", "firefox.exe", "browsermob-proxy"]
PROCS_TO_KILL = ["firefox.exe"]
#PROXY_SERVER_PATH = f"{PATH}/modules/browsermob-proxy-2.1.4/bin/browsermob-proxy.bat"
#WINDOWS_PROCS_TO_KILL = ["java.exe", "firefox.exe", "browsermob-proxy"]
WINDOWS_PROCS_TO_KILL = ["firefox.exe"]
#LINUX_PROCS_TO_KILL = ["browsermob-prox", "browsermob-proxy", "java"]
# WINDOWS_PROXY_SERVER_PATH = (
#     f"{PATH}\\browsermob-proxy-2.1.4\\bin\\browsermob-proxy.bat"
# )
# LINUX_PROXY_SERVER_PATH = (
#     f"{PATH}/modules/browsermob-proxy-2.1.4/bin/browsermob-proxy.bat"
# )



class FireFoxBrowser: # TODO: add baseclass for browser
    def __init__(
        self,
        host_type: Optional[str] = "windows" if os.name == "nt" else "linux",
        webdriver_path: Optional[str] = "drivers/geckodriver",
        process_kill_wait: Optional[int] = 5,
        har_session_name: Optional[str] = "networkanalysis",
        har_location: Optional[str] = f"{PATH.parent}\hars",
        har_filename: Optional[str] = "harfile",
        har_extension_path: Optional[str] = None,
        enable_quic: Optional[bool] = True,
        options: Optional[List[str]] = None
    ):
        #if host_type == "windows" and not proxy_server_path:
        if host_type == "windows":
            #self.proxy_server_path = WINDOWS_PROXY_SERVER_PATH
            if not har_extension_path:
                har_extension_path = f"{PATH_WINDOWS}\extensions\\firefox\\har_export_trigger-0.6.1-an+fx.xpi"
            self._procs_to_kill = WINDOWS_PROCS_TO_KILL

        #elif host_type == "linux" and not proxy_server_path:
        elif host_type == "linux":
            if not har_extension_path:
                self.har_extension_path = f"{PATH}\extensions\\firefox\\har_export_trigger-0.6.1-an+fx.xpi"
            #self.proxy_server_path = LINUX_PROXY_SERVER_PATH
            self._procs_to_kill = LINUX_PROCS_TO_KILL

        self.profile = webdriver.FirefoxProfile()
        self.driver = None
        self.process_kill_wait = process_kill_wait
        self.webdriver_path = webdriver_path
        self.har_session_name = har_session_name
        self.har_location = har_location
        self.har_filename = har_filename
        self.har = None
        self.har_extension_path = har_extension_path
        self.enable_quic = enable_quic
        self.options = options

    def __enter__(self):
        self._build_options()
        kill_existing_proc(self._procs_to_kill, self.process_kill_wait)
        self._build_profile()
        self.driver = webdriver.Firefox(
            executable_path=self.webdriver_path, 
            firefox_profile=self.profile,
            options=self.options
        )
        self.driver.install_addon(self.har_extension_path, temporary=True)

        # # Add HAR capture extension
        self.driver.firefox_profile.add_extension(extension=self.har_extension_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type or exc_val or exc_tb):
            apptest_logger.debug(f"{exc_type} | {exc_val} | {exc_tb}")

        # inject javascript to request HAR file
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
        time.sleep(10) # TODO: Change back to 60 

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
