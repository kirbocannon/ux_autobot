import time
from random import randint
from selenium import webdriver
from typing import List, Optional


class BaseTest:
    def __init__(self, driver: webdriver):
        self.driver = driver

    def get_content(
        self,
        urls: List[str],
        wait: Optional[float] = 0.5,
        randowait: Optional[tuple] = None
    ) -> None:
        """
            Gets any list of URLs containing content provided the URL is accessible. 
        """
        for url in urls:
            self.driver.get(url)
            if randowait:
                time.sleep(randint(randowait[0], randowait[1]))
            else:
                time.sleep(wait)
        return
