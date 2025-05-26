import threading
from datetime import datetime
from time import sleep
from project_utils import logger, call_proxy_method

class HeartbeatMonitor:
    def __init__(self, peer_name, on_failure):
        self.peer_name = peer_name if peer_name else None
        self.on_failure = on_failure
        self.running = True
        self.last_ok = datetime.now()
        logger(__name__, self.status(), f"Initializing HeartbeatMonitor with URI: {peer_name}")

    def status(self):
        return self.peer_name
    
    def start(self, timer=None):
        logger(__name__, self.status(), "Starting heartbeat monitor")
        def monitor():
            while True:
                sleep(1)
                try:
                    if call_proxy_method(self.peer_name, function=lambda peer: peer.heartbeat()): 
                        logger(__name__, self.status(), "Heartbeat received from tracker")
                        self.last_ok = datetime.now()
                except:
                    pass
                if (datetime.now() - self.last_ok).microseconds > timer if timer else 5000:
                    logger(__name__, self.status(), f"No heartbeat received, triggering failure callback, now={datetime.now()}, last_ok={self.last_ok}, timer={timer}")
                    self.on_failure()
                    break

        t = threading.Thread(target=monitor)
        t.daemon = True
        t.start()

    def stop(self):
        self.running = False
