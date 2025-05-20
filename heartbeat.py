import random
import threading
from datetime import datetime
from time import sleep
import Pyro5
from project_utils import logger, call_proxy_method

class HeartbeatMonitor:
    def __init__(self, tracker_uri, on_failure):
        logger.debug(f"Initializing HeartbeatMonitor with tracker URI: {tracker_uri}")
        self.tracker_uri = tracker_uri if tracker_uri else None
        self.on_failure = on_failure
        self.running = True
        self.last_ok = datetime.now()

    def start(self, timer=None):
        logger.debug("Starting heartbeat monitor")
        def monitor():
            while self.running:
                sleep(1)
                try:
                    if call_proxy_method(self.tracker_uri, function=lambda tracker: tracker.heartbeat()): 
                        logger.debug("Heartbeat received from tracker")
                        self.last_ok = datetime.now()
                except:
                    pass
                if (datetime.now() - self.last_ok).microseconds > timer if timer else 5000:
                    logger.debug(f"No heartbeat received, triggering failure callback, now={datetime.now()}, last_ok={self.last_ok}, timer={timer}")
                    self.on_failure()
                    break

        t = threading.Thread(target=monitor)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
