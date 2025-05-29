import re
from project_utils import logger, get_name_service, TRACKER_PREFIX, logging

class TrackerManager:

    @staticmethod
    def lookup_tracker():
        tracker_name = None
        try:
            with get_name_service() as ns:
                all_entries = ns.list()
                trackers = {name: uri for name, uri in all_entries.items() if re.match(TRACKER_PREFIX, name)}
                if not trackers:
                    logging.getLogger(__name__).warning("Tracker not found")
                    return
                latest_tracker = max(trackers.items(), key=lambda x: int(re.search(r"\d+", x[0]).group()))
                tracker_name = latest_tracker[0]
                logging.getLogger(__name__).debug(f"Tracker found: {tracker_name} uri: {latest_tracker[1]}")
        except Exception as e:
            logging.getLogger(__name__).warning(f"Tracker not found: {e}")
        
        return tracker_name
