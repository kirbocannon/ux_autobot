import os
import time
import json

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

PATH = get_abs_path(__file__)
TEST_DATA_PATH = f"{PATH}/modules/apptests/data/instagram"

CFG = load_yaml(f"{PATH}/config.yaml")
GLOBAL_DL_THREHOLD = CFG["global"]["download_threshold"]


def run(minutes_browsing):
    ig_cfg = CFG["websites"]["thegram"]

    timestamp = time.time()

    with FireFoxBrowser() as browser:
        ig = InstagramTest(
            username=ig_cfg["username"],
            password=ig_cfg["password"],
            driver=browser.driver,
        )
        ig.browse_hashtag(hashtag="cars", duration=minutes_browsing)

    har_saved_results = save_har(
        location=PATH, data=browser.har, timestamp=timestamp, prefix="instagram"
    )

    return dict(timestamp=timestamp, har_filename=har_saved_results["filename"])


def analyze_harfile(har_filename, dl_threshold, save_urls=False):
    with open(f"hars/{har_filename}", "r") as f:
        har_parser = HarParser(json.loads(f.read()))
        first_start_time = None
        interesting_entries = []
        for (
            page
        ) in (
            har_parser.pages
        ):  # TODO: this function only supports one page really, this doesn't make a lot of sense
            entries = page.filter_entries(
                content_type="(image|video)",
                receive_time__gt=dl_threshold,
                status_code="200",
            )
            num_entries = len(entries)
            first_start_time = entries[0].startTime if num_entries else None
            for entry in entries:
                interesting_entries.append(entry)
                print(
                    f"{entry.startTime} - Downloaded {entry.response.mimeType!r} ({convert_bytes(entry.response.bodySize)}) in {ms_to_s(entry.timings['receive'])} seconds from {entry.response.url.split('https://')[1].split('/')[0]} ({entry.serverAddress})"
                )

        print(f"First download time of image/video content {first_start_time}")
        print(
            f"Images and Videos downloaded above {dl_threshold} milliseconds {num_entries}"
        )

        total_images_download_size = convert_bytes(page.image_size)
        total_images_load_time = ms_to_s(page.image_load_time)
        try:
            score = round(
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
        except ZeroDivisionError:
            score = 0

        print(
            f"{len(page.image_files)} ({total_images_download_size}) images downloaded in {total_images_load_time} second(s). Score {score}"
        )

        print(f"Total Load time: {ms_to_s(page.get_load_time(content_type='(image|video)'))}s")

    report_entry = ReportEntry(
        page, interesting_entries, first_start_time, har_filename
    )

    dl_urls = generate_repeatable_test_urls(page) if save_urls else []
    
    return dict(
        report=report_entry, 
        dl_urls=dl_urls
        )


def main():
    results = run(minutes_browsing=CFG["global"]["browsing_minutes"])
    har_filename = results["har_filename"]
    report_entry = analyze_harfile(
        har_filename=f"{har_filename}", dl_threshold=GLOBAL_DL_THREHOLD, save_urls=True
    )
    dump_report(
        report_entry=report_entry['report'], root_path=PATH, dl_threshold=GLOBAL_DL_THREHOLD
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
    # Randomized Test
    #_ = main()

    # repeatable test
    #creds = load_yaml(f"{PATH}/config.yaml")["websites"]["thegram"]
    with open('modules/apptests/data/instagram/urls.json') as f:
        urls = json.load(f)

    with FireFoxBrowser() as browser:
        timestamp = time.time()
        basic = BaseTest(driver=browser.driver)
        basic.get_content(urls[-10:], wait=3)
        
    har_saved_results = save_har(
        location=PATH, data=browser.har, timestamp=timestamp, prefix="instagram-static-urls"
    )

    report_entry = analyze_harfile(har_saved_results["filename"], 1, save_urls=False)
    
    dump_report(
        report_entry=report_entry['report'], root_path=PATH, dl_threshold=1
    )
