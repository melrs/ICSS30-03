import re
import Pyro5.api
from project_utils import logger, get_name_service, get_tracker_id, PEER_PREFIX, TRACKER_PREFIX, call_proxy_method
from election import Election
from heartbeat import HeartbeatMonitor

class TrackerManager:
    
    @staticmethod
    def lookup_tracker():
        tracker_name = None
        try:
            with get_name_service() as ns:
                all_entries = ns.list()
                trackers = {name: uri for name, uri in all_entries.items() if re.match(TRACKER_PREFIX, name)}
                if not trackers:
                    logger.warning("Tracker not found")
                    return
                latest_tracker = max(trackers.items(), key=lambda x: int(re.search(r"\d+", x[0]).group()))
                tracker_name = latest_tracker[0]
                logger.debug(f"Tracker found: {tracker_name}")
        except Exception as e:
            logger.warning(f"Tracker not found: {e}")
        
        return tracker_name
