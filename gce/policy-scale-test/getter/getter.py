import time
import os
import requests
from datetime import datetime

# Logging
import logging, sys
_log = logging.getLogger(__name__)
stdout_hdlr = logging.StreamHandler(sys.stderr)
_log.addHandler(stdout_hdlr)
_log.setLevel("DEBUG")

now = datetime.now

sleeptime = os.environ.get("SLEEPTIME")
timeout = float(os.environ.get("TIMEOUT", ".001"))
url = os.environ.get("URL", "http://10.100.0.50:80")

if sleeptime:
    time.sleep(float(sleeptime))

end_time = None
start_time = now()
while True:
    try:
        r = requests.head(url, timeout=timeout)
    except requests.exceptions.Timeout:
        _log.debug("Timeout")
    else:
        if r.status_code == 200:
            end_time = now()
            break
        else:
            _log.debug("Bad status: %s", r.status_code)

_log.debug("Started: %s.%s", start_time.second, (start_time.microsecond / 1000))
_log.debug("Completed: %s.%s", end_time.second, (end_time.microsecond / 1000))

elapsed = end_time - start_time
_log.debug("Elapsed: %s", elapsed.total_seconds())

time.sleep(36000)
