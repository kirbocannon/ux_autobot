import os
import time
import json
import random

import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

from utils.applogger import apptest_logger, report_logger

from browsermobproxy import Server

from selenium import webdriver

from utils.data import load_yaml, get_abs_path, save_har, get_filenames
from utils.metrics import ms_to_s, convert_bytes, remove_size_suffix, gb_to_mb
from utils.system import kill_existing_proc
from utils.reports import ReportEntry, dump_report

from modules.browser import FireFoxBrowser
from modules.apptests.instagram import BaseTest, InstagramTest

from modules.haralyzer.assets import HarParser, HarPage

from utils.applogger import apptest_logger as logger

from statistics import mean


PATH = get_abs_path(__file__)
TEST_DATA_PATH = f"{PATH}/modules/apptests/data/instagram"

CFG = load_yaml(f"{PATH}/config.yaml")
GLOBAL_DL_THREHOLD = CFG["global"]["download_threshold"]
ENABLE_QUIC = CFG["global"]["enable_quic"]
LANGUAGE = CFG["language"]

HOUR_IN_SECONDS = 3600


def choose_random_account():
    ig_cfg = CFG["websites"]["thegram"]
    accounts = ig_cfg["accounts"]
    account = random.choice(accounts)

    return account


def story_browsing(handle, duration):
    account = choose_random_account()

    timestamp = time.time()
    har_filename = f"instagram_{timestamp}-{'http3' if ENABLE_QUIC else 'http1.1-2'}"

    with FireFoxBrowser(har_filename=har_filename, enable_quic=ENABLE_QUIC) as browser:
        ig = InstagramTest(
            username=account["username"],
            password=account["password"],
            driver=browser.driver,
            autologin=True,
            default_element_timeout=20,
            searchbox_translation=LANGUAGE["component"]["searchbox"][LANGUAGE["selected"]]
        )
        
        ig.browse_stories(handle=handle, duration=duration)

    # generate report
    report_entry = analyze_harfile(har_filename=har_filename, browsing_time=CFG["global"]["browsing_minutes"], dl_threshold=GLOBAL_DL_THREHOLD, save_urls=False)

    if report_entry["report"]:
        dump_report(
            CFG["global"]["browsing_minutes"], report_entry=report_entry['report'], root_path=PATH, dl_threshold=GLOBAL_DL_THREHOLD
        )

    return

def hashtag_browsing(hashtag, duration):

    account = choose_random_account()

    timestamp = time.time()
    har_filename = f"instagram_{timestamp}-{'http3' if ENABLE_QUIC else 'http1.1-2'}"

    with FireFoxBrowser(har_filename=har_filename, enable_quic=ENABLE_QUIC) as browser:
        ig = InstagramTest(
            username=account["username"],
            password=account["password"],
            driver=browser.driver,
            autologin=True,
            searchbox_translation=LANGUAGE["component"]["searchbox"][LANGUAGE["selected"]]
        )
        
        #ig.get_content(urls[-5:], wait=10)
        #ig.get_content(["https://google.com"], wait=10)
        ig.browse_hashtag(hashtag=hashtag, duration=duration)

    report_entry = analyze_harfile(
        har_filename=f"{har_filename}", browsing_time=duration, dl_threshold=GLOBAL_DL_THREHOLD, save_urls=True
    )
    dump_report(
        duration, report_entry=report_entry['report'], root_path=PATH, dl_threshold=GLOBAL_DL_THREHOLD
    )

    return


def visualize_harfile(har_filenames, filetype):
    filetype = filetype.lower()

    for idx, har_filename in enumerate(hars):

        with open(f"hars/{har_filename}.har", "r") as f:
            har_parser = HarParser(json.loads(f.read()))
            first_start_time = None
            interesting_entries = []
            for (
                page
            ) in (
                har_parser.pages
            ):  # TODO: this function only supports one page really, this doesn't make a lot of sense
                entries = page.filter_entries(
                    content_type=filetype,
                    status_code="(200|206)",
                )

            if filetype == "image":
                total_download_size = convert_bytes(page.image_size)
                total_load_time = ms_to_s(page.image_load_time)
            elif filetype == "video":
                total_download_size = convert_bytes(page.video_size)
                total_load_time = ms_to_s(page.video_load_time)
            else:
                raise Exception(f"File type {filetype!r} not recognized")

            y = np.array([ms_to_s(entry.timings['receive']) for entry in entries])
            x = np.array([entry.startTime for entry in entries])

            p = plt.figure(num=idx + 1)
            #p.set_size_inches(18,18)

            # set labels
            plt.title(f"{filetype.capitalize()} - {har_filename!r} Started: {page.startedDateTime} Downloaded: {total_download_size} Total Time: {total_load_time}s Files Downloaded: {len(entries)}")
            plt.xlabel("start time")
            plt.ylabel("receive time (seconds)")

            # draw plot
            plt.plot(x, y)

            # save plots
            plt.savefig(f'plots/{har_filename}.png')

    plt.show()


def analyze_harfile(har_filename, browsing_time, dl_threshold, save_urls=False, content_type="(image|video|media|mp4)"): # TODO: make more modular. method in instagramtest class?
    with open(f"hars/{har_filename}.har", "r") as f:
        har_parser = HarParser(json.loads(f.read()))
        first_start_time = None
        interesting_entries = []
        num_entries = 0
        page = None
        for (
            page
        ) in (
            har_parser.pages
        ):  # TODO: this function only supports one page really, this doesn't make a lot of sense
            entries = page.filter_entries(
                content_type=content_type,
                receive_time__gt=dl_threshold,
                status_code="(200|206)",
            )
            num_entries = len(entries)
            first_start_time = entries[0].startTime if num_entries else None
            print(f"Analyzed har file: {har_filename!r}.har")
            print(f"Browsed for {browsing_time} minute(s)")
            for entry in entries:
                interesting_entries.append(entry)
                print(
                    f"{entry.startTime} - Downloaded {entry.response.mimeType!r} ({convert_bytes(entry.response.bodySize)}) in {ms_to_s(entry.timings['receive'])} seconds from {entry.response.url.split('https://')[1].split('/')[0]} ({entry.serverAddress})"
                )

        print(f"First download time of image/video content {first_start_time}")
        print(
            f"Number of Images and Videos downloaded above {dl_threshold} milliseconds {num_entries}"
        )

        total_images_download_size = convert_bytes(page.image_size) if page else 0
        total_images_load_time = ms_to_s(page.image_load_time) if page else 0
        total_videos_download_size = convert_bytes(page.video_size) if page else 0
        total_videos_load_time = ms_to_s(page.video_load_time) if page else 0

        try:
            images_score = round(
                10.0
                - (
                    total_images_load_time
                    / remove_size_suffix(
                        gb_to_mb(total_images_download_size)
                        if "G" in total_images_download_size
                        else total_images_download_size
                    )
                ),
                2,
            )  # TODO: hacky but OK for now

        except (ZeroDivisionError, TypeError):
            images_score = 0

        try:
            videos_score = round(
                10.0
                - (
                    total_videos_load_time
                    / remove_size_suffix(
                        gb_to_mb(total_videos_download_size)
                        if "G" in total_videos_download_size
                        else total_videos_download_size
                    )
                ),
                2,
            )  # TODO: hacky but OK for now
        except (ZeroDivisionError, TypeError):
            videos_score = 0

        if images_score and videos_score:
            overall_score = mean([images_score, videos_score])
        
        elif images_score and not videos_score:
            overall_score = images_score
        
        elif videos_score and not images_score:
            overall_score = videos_score 

        if page:

            print(f"Total Load time: {ms_to_s(page.get_load_time(content_type=content_type))}s")
        
            print(f"{len(page.video_files)} ({total_videos_download_size}) videos downloaded in {total_videos_load_time}")

            print(
                f"{len(page.image_files)} ({total_images_download_size}) images downloaded in {total_images_load_time} second(s). Images Score {images_score}. Videos Score {videos_score}"
            )
            print(f"Overall Score: {round(overall_score, 2)}")


    if page:
        report_entry = ReportEntry(
            page, interesting_entries, first_start_time, har_filename
        )

        dl_urls = generate_repeatable_test_urls(page) if save_urls else []
    else:
        report_entry = None
        dl_urls = None
    
    return dict(
        report=report_entry, 
        dl_urls=dl_urls
        )


def generate_repeatable_test_urls(page):
    # get entry URLs for repeatable tests
    content_type = "(image|video)"
    content_size = 200000
    dl_urls = [entry.response.url for entry in page.filter_entries(
        content_type=content_type,
        status_code="200",
        content_size=content_size # images/video > than 0.2 jiggabytes
            )]
    
    os.makedirs(TEST_DATA_PATH, exist_ok=True)

    with open(f"{TEST_DATA_PATH}/urls.json", 'w+') as f:
        json.dump(dl_urls, f)

    return dict(
        content_type=content_type,
        content_size=content_size,
        entries_saved=len(dl_urls)
    )


if __name__ == "__main__":
    # # Randomized Test
    # for _ in range(100000):
    #     try:
    #         #_ = hashtag_browsing(hashtag="cars", duration=30)
    #         _ = story_browsing(handle="thekingofdiet", duration=20)
    #         break
    #     except Exception:
    #         logger.debug("Exception running test. Did not run test for this time slot")
            
    #     time.sleep(HOUR_IN_SECONDS / 4)

    
    #_ = hashtag_browsing(hashtag="cars", duration=.1)

    har_filename = 'test'

    with FireFoxBrowser(har_filename=har_filename, enable_quic=ENABLE_QUIC) as browser:
        browser.driver.get("moz-extension://f1b1fd6e-9b21-4214-924e-511d15bc1580/data/options/options.html")

        # import_file = browser.find_element_by_id('import_file')
        # import_file.send_keys()
        # import_button = self.browser.find_element_by_id('import_button')
        # import_button.click()

        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        
        # set url
        url_box = browser.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='URL (i.e. https://www.google.com/ or *)']"
        )
        url_box.send_keys("https://instagram.com")

        # set header name
        header_key_box = browser.driver.find_element(
            By.CSS_SELECTOR, "input[placeholder='name (i.e. User-Agent)']"
        )
        header_key_box.send_keys("x-fb-product-log")

        # set header value
        header_value_box = browser.driver.find_element(
            By.CSS_SELECTOR, "input[title='Enter a valid value']"
        )
        header_value_box.send_keys("ta:15:starlink-test-")

        header_value_box.send_keys(Keys.ENTER)

        browser.driver.get("https://www.instagram.com/")

        time.sleep(5)


        # body = browser.driver.find_element(By.TAG_NAME, "body")
        # body.send_keys(Keys.CONTROL + 't')
    