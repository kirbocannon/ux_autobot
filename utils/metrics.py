import logging
import math


def ms_to_s(n: int) -> float:
    if isinstance(n, int):
        return n / 1000

    return 0.0


def convert_bytes(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return "%s %s" % (s, size_name[i])


def remove_size_suffix(bytes_: str) -> float:
    try:
        return float(bytes_.split()[0])
    except:

        return 0.0


def gb_to_mb(n):
    return n * 1000
