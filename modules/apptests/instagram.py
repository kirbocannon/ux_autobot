import time
from random import uniform

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from modules.browser import scroll

from modules.apptests.base import BaseTest

from typing import Optional


class InstagramTest(BaseTest):
    def __init__(
        self,
        username: str,
        password: str,
        driver: webdriver,
        autologin: Optional[bool] = True,
    ):
        self.base_url = "https://www.instagram.com"
        self.username = username
        self.password = password
        self.driver = driver
        super().__init__(driver)
        if autologin:
            self.login()

    def login(self) -> bool:
        self.driver.get(self.base_url)
        time.sleep(10)  # TODO: Start randomizing time sleeps

        username = self.driver.find_element(By.XPATH, "//*[@name='username']")
        password = self.driver.find_element(By.XPATH, "//*[@name='password']")
        credentials_submit = self.driver.find_element(By.XPATH, "//*[@type='submit']")

        username.clear()
        password.clear()

        username.send_keys(self.username)
        time.sleep(2)
        password.send_keys(self.password)

        time.sleep(5)

        credentials_submit.click()

        time.sleep(20)

        return True

    def browse_cute_animal_pictures(
        self,
        duration: int,
        wait: Optional[float] = None,
        randowait: Optional[tuple] = None,
    ) -> None:  # TODO: prob change this return type
        """
        Randomly scroll through and browse pictures of cute animals as a user would
        1.) Use IG search bar to browse '#animals'
        2.) Scroll through pictures randomly by default for the duration specified

        :param duration: Duration of browsing in minutes
        :type duration: int
        :param wait: how long to wait between scrolls
        :type wait: float
        :param randowait: limits of the random numbers
        :type randowait: tuple
        :return: Nothing
        :rtype: None
        """

        if not randowait and not wait:
            randowait = (0.3, 2)

        if not randowait:
            wait = 0.3

        # lookup #animals
        searchbox = self.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='Search']"
        )
        searchbox.clear()
        searchbox.send_keys("#animals")
        time.sleep(2)
        searchbox.send_keys(Keys.ENTER)
        time.sleep(2)
        searchbox.send_keys(Keys.ENTER)
        time.sleep(5)

        # TODO: prob create decorator function for the timeout
        timeout = time.time() + 60 * duration  # 5 minutes from now
        while True:
            if time.time() > timeout:
                break

            scrolldown = scroll(self.driver, 1, delay=0)
            if randowait:
                time.sleep(uniform(randowait[0], randowait[1]))
            else:
                time.sleep(wait)

        return
