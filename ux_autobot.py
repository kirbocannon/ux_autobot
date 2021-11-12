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
from modules.apptests.instagram import InstagramTest

from modules.haralyzer.assets import HarParser, HarPage

PATH = get_abs_path(__file__)

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


def analyze_harfile(har_filename, dl_threshold):

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
            f"Images and Videos downloaded above {dl_threshold} seconds {num_entries}"
        )

        total_images_download_size = convert_bytes(page.image_size)
        total_images_load_time = ms_to_s(page.image_load_time)
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

        print(
            f"{len(page.image_files)} ({total_images_download_size}) images downloaded in {total_images_load_time / 1000} second(s). Score {score}"
        )

        print(ms_to_s(page.get_load_time(content_type="(image|video)")))

    report_entry = ReportEntry(
        page, interesting_entries, first_start_time, har_filename
    )

    return report_entry


def main():
    results = run(minutes_browsing=CFG["global"]["browsing_minutes"])
    har_filename = results["har_filename"]
    # har_filename = "instagram_1636621800.4872868.json"
    report_entry = analyze_harfile(
        har_filename=f"{har_filename}", dl_threshold=GLOBAL_DL_THREHOLD
    )
    dump_report(
        report_entry=report_entry, root_path=PATH, dl_threshold=GLOBAL_DL_THREHOLD
    )


if __name__ == "__main__":
    main()

    # b = convert_bytes(2.1e+6)
    # print(b)

    # creds = load_yaml(f"{PATH}/config.yaml")["websites"]["thegram"]
    # with FireFoxBrowser() as browser:
    #     ig = InstagramTest(username=creds["username"], password=creds["password"], driver=browser.driver, autologin=False)
    #     ig.browse_cute_animal_pictures(scroll_count=5)
    #     ig.get_content(urls=["https://google.com"], randowait=(2, 15))
