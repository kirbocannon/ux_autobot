import psutil
import logging
import time
from typing import Optional, List

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


def kill_existing_proc(proc_names: List[str], kill_wait: Optional[int] = 10):
    for proc in psutil.process_iter():
        # check whether the process name matches
        for proc_name in proc_names:
            if proc.name() == proc_name:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    logger.warning(f"Process {proc_name!r} is not found")

    time.sleep(kill_wait)

    return
