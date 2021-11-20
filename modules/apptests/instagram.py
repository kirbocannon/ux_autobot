import time
from random import uniform
from copy import copy

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from modules.browser import scrolldown, scrollup

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

        username = self.driver.find_element(By.XPATH, "//*[@name='username']") # TODO: Major error handling with context manager/etc
        password = self.driver.find_element(By.XPATH, "//*[@name='password']")
        credentials_submit = self.driver.find_element(By.XPATH, "//*[@type='submit']")

        username.clear()
        password.clear()

        username.send_keys(self.username)
        time.sleep(2)
        password.send_keys(self.password)

        time.sleep(5)

        credentials_submit.click()

        time.sleep(60)

        return True

    def browse_hashtag(
        self,
        hashtag: str,
        duration: int,
        wait: Optional[float] = None,
        randowait: Optional[tuple] = None,
    ) -> None:  # TODO: prob change this return type
        """
        Randomly scroll through and browse pictures of cute animals as a user would
        1.) Use IG search bar to browse '#animals'
        2.) Scroll through pictures randomly by default for the duration specified

        :param hashtag: Hashtag to search
        :type hashtag: str
        :param duration: Duration of browsing in minutes
        :type duration: int
        :param wait: how long to wait between scrolls
        :type wait: float
        :param randowait: limits of the random numbers
        :type randowait: tuple
        :return: Nothing
        :rtype: None
        """

        hashtag = hashtag.split("#")[1] if hashtag.startswith("#") else hashtag

        if not randowait and not wait:
            randowait = (0.3, 2)

        if not randowait:
            wait = 0.3

        time.sleep(20)

        # lookup a hashtag
        searchbox = self.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='Search']"
        )
        searchbox.clear()
        searchbox.send_keys(f"#{hashtag}")
        time.sleep(2)
        searchbox.send_keys(Keys.ENTER)
        time.sleep(2)
        searchbox.send_keys(Keys.ENTER)
        time.sleep(5)

        # TODO: prob create decorator function for the timeout
        start_time = time.time()
        start_time_relative_after_timer = copy(
            start_time
        )  # relative start time after inner timer is reached
        timeout = start_time + 60 * duration
        times_scrolled_down_global = 0
        times_scrolled_down = 0
        while True:
            if time.time() > timeout:
                break

            scrolldown(driver=self.driver, cnt=1, delay=0)
            scrollup(
                driver=self.driver, cnt=15, delay=0.1
            )  # just add an additional scroll up here....
            times_scrolled_down += 1
            times_scrolled_down_global += 1

            if randowait:
                time.sleep(uniform(randowait[0], randowait[1]))
            else:
                time.sleep(wait)

            if times_scrolled_down > 4:  # Prevent scrolling bug of instagram
                times_scrolled_down = 0
                scrollup(driver=self.driver, cnt=80, delay=0.5)
            # every now and then the scroll will get stuck. So do some big
            # scrolling here, prob could make this a whole lot better
            # also scroll if it's been 5 minutes
            if times_scrolled_down_global > 40:
                scrollup(driver=self.driver, cnt=20, delay=0.3)
                times_scrolled_down_global = 0

            # scroll every 60 seconds regardless
            if (time.time() - start_time_relative_after_timer) > 60:
                scrollup(driver=self.driver, cnt=20, delay=1)
                start_time_relative_after_timer = start_time_relative_after_timer + 60

        return
