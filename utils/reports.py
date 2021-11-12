import os
import csv
from typing import List, Optional
from datetime import datetime
from utils.metrics import ms_to_s, convert_bytes, remove_size_suffix, gb_to_mb
from utils.applogger import report_logger


class ReportEntry:
    def __init__(
        self,
        page,
        interesting_entries: list,
        first_start_time: datetime,
        har_filename: str,
    ):
        self.interesting_entries = interesting_entries
        self.first_start_time = first_start_time
        self.num_entries = len(interesting_entries)
        self.page = page
        self.overall_image_stats = self._get_overall_image_stats()
        self.overall_video_stats = self._get_overall_video_stats()
        self.entry_stats = self._get_entry_stats()
        self.har_filename = har_filename

    def _get_overall_image_stats(self) -> dict:
        t_img_load_time = ms_to_s(self.page.image_load_time)
        t_dl_size = convert_bytes(self.page.image_size)
        return dict(
            image_files=len(self.page.image_files),
            total_image_size=t_dl_size,
            total_image_load_time=t_img_load_time,
            score=round(
                10.0
                - (
                    t_img_load_time
                    / remove_size_suffix(
                        gb_to_mb(t_dl_size) if "G" in t_dl_size else t_dl_size
                    )
                ),
                2,
            )  # TODO: very hacky and assumes a lot. Re-work
            if self.page.image_files
            else 0,
        )

    def _get_overall_video_stats(self) -> dict:
        t_vid_load_time = ms_to_s(self.page.video_load_time)
        t_dl_size = convert_bytes(self.page.video_size)
        return dict(
            video_files=len(self.page.video_files),
            total_video_size=t_dl_size,
            total_video_load_time=t_vid_load_time,
            score=round(10.0 - (t_vid_load_time / remove_size_suffix(t_dl_size)), 2)
            if self.page.video_files
            else 0,
        )

    def _get_entry_stats(self) -> List[dict]:
        l = []
        for entry in self.interesting_entries:
            l.append(
                dict(
                    startTime=entry.startTime,
                    responseMimeType=entry.response.mimeType,
                    responseBodySize=convert_bytes(entry.response.bodySize),
                    receiveTiming=ms_to_s(entry.timings["receive"]),
                    url=entry.response.url.split("https://")[1].split("/")[0],
                    serverAddress=entry.serverAddress,
                )
            )
        return l


def dump_report(
    report_entry: ReportEntry, root_path: str, dl_threshold: int
) -> None:  # TODO: make more reusable
    """
    Dumps report to reports/ as a txt file and also creates a csv
    """
    now = str(datetime.now())
    dl_threshold = ms_to_s(dl_threshold)

    har_entry_stats = ""
    for har_entry in report_entry.interesting_entries:
        har_entry_stats += f"\t\t{har_entry.startTime} - Downloaded {har_entry.response.mimeType!r} ({convert_bytes(har_entry.response.bodySize)}) in {ms_to_s(har_entry.timings['receive'])} seconds from {har_entry.response.url.split('https://')[1].split('/')[0]} ({har_entry.serverAddress})\n"

    output = f"""
    --------------------------------------------------------------------------------
    Report for {report_entry.har_filename!r} analyzed at @ {now}
    First download time of image/video content {report_entry.first_start_time} (Only includes files over threshold)
    Images and Videos downloaded above threshold: {report_entry.num_entries}
    {report_entry.overall_image_stats["image_files"]} ({report_entry.overall_image_stats["total_image_size"]}) images downloaded in {report_entry.overall_image_stats["total_image_load_time"]} seconds
    {report_entry.overall_video_stats["video_files"]} ({report_entry.overall_video_stats["total_video_size"]}) videos downloaded in {report_entry.overall_video_stats["total_video_load_time"]} seconds
    Score {report_entry.overall_image_stats["score"]}

    Har entries that exceeded the download duration threshold of {dl_threshold / 1000} second(s): \n{har_entry_stats}
    --------------------------------------------------------------------------------
    """
    report_logger.debug(output)

    # create csv
    csv_filename = f"{root_path}/reports/reports.csv"

    fieldnames = [
        "date",
        "har_filename",
        "images_videos_count",
        "image_count",
        "total_image_size",
        "total_image_load_time",
        "video_count",
        "total_video_size",
        "total_video_load_time",
        "score",
    ]
    with open(csv_filename, "a+") as f:
        dw = csv.DictWriter(
            f, delimiter=",", fieldnames=fieldnames, lineterminator="\n"
        )
        if os.stat(csv_filename).st_size == 0:
            dw.writeheader()

        dw.writerow(
            {
                "date": now,
                "har_filename": report_entry.har_filename,
                "images_videos_count": report_entry.num_entries,
                "image_count": report_entry.overall_image_stats["image_files"],
                "total_image_size": report_entry.overall_image_stats[
                    "total_image_size"
                ],
                "total_image_load_time": report_entry.overall_image_stats[
                    "total_image_load_time"
                ],
                "video_count": report_entry.overall_video_stats["video_files"],
                "total_video_size": report_entry.overall_video_stats[
                    "total_video_size"
                ],
                "total_video_load_time": report_entry.overall_video_stats[
                    "total_video_load_time"
                ],
                "score": report_entry.overall_image_stats["score"],
            }
        )

    return
