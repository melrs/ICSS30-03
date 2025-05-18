import random
import threading
import time
import Pyro5
from project_utils import now, logger, call_proxy_method

class HeartbeatMonitor:
    def __init__(self, tracker_uri, on_failure):
        logger.debug(f"Initializing HeartbeatMonitor with tracker URI: {tracker_uri}")
        self.tracker_uri = tracker_uri if tracker_uri else None
        self.on_failure = on_failure
        self.running = True
        self.last_ok = now()

    def start(self):
        def monitor():
            while self.running:
                try:
                    if call_proxy_method(self.tracker_uri, function=lambda tracker: tracker.heartbeat()): 
                        logger.debug("Heartbeat received from tracker")
                        self.last_ok = now()
                except:
                    pass
                if now() - self.last_ok > random.uniform(0.15, 0.3):
                    logger.debug("No heartbeat received, triggering failure callback")
                    self.on_failure()
                    break
                time.sleep(1)

        t = threading.Thread(target=monitor)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
