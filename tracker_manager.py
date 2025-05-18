import re
import Pyro5.api
from project_utils import logger, get_name_service, register_object, PEER_PREFIX, call_proxy_method
from election import Election
from heartbeat import HeartbeatMonitor

TRACKER_PREFIX = "tracker.epoch."

class TrackerManager:

    @staticmethod
    def promote_tracker(tracker, daemon):
        peer_id = tracker.id
        epoch = tracker.epoch + 1
        logger.debug(f"Starting election with epoch: {epoch}")
        election = Election(tracker, epoch)
        name_service = get_name_service()
        if election.execute():
            logger.debug("Election successful. Promoting to tracker.")
            tracker.is_tracker = True
            tracker.epoch = epoch
            all_entries = name_service.list()
            id_files = {name: call_proxy_method(uri, function=lambda peer: peer.list_files()) for name, uri in all_entries.items() if re.match(PEER_PREFIX, name)}
            for _, (id, files) in id_files.items():
                logger.debug(f"Updating index for peer {id} with files: {files}")
                tracker.update_index(id, files)
            tracker_uri = name_service.lookup(f"{PEER_PREFIX}{peer_id}")
            name_service.register(f"{TRACKER_PREFIX}{epoch}", tracker_uri)
            tracker.tracker_uri = tracker_uri
            tracker.register_with_tracker()
            logger.info(f"[{peer_id}] Elected as new tracker with URI: {tracker_uri}")
        else:
            logger.warning("Election failed.")

    @staticmethod
    def lookup_tracker():
        tracker_uri = None
        try:
            with get_name_service() as ns:
                all_entries = ns.list()
                trackers = {name: uri for name, uri in all_entries.items() if re.match(TRACKER_PREFIX, name)}
                if not trackers:
                    logger.warning("Tracker not found")
                    return
                latest_tracker = max(trackers.items(), key=lambda x: int(re.search(r"\d+", x[0]).group()))
                tracker_uri = latest_tracker[1]
                logger.debug(f"Tracker URI found: {tracker_uri}")
        except Exception as e:
            logger.warning(f"Tracker not found: {e}")
        
        return tracker_uri

    @staticmethod
    def initialize_peer_monitoring(peer, daemon, tracker_uri):
        logger.debug(f"Initializing heartbeat monitoring for peer {peer.id} with tracker URI: {tracker_uri}")
        monitor = HeartbeatMonitor(tracker_uri, lambda: TrackerManager.promote_tracker(peer, daemon))
        monitor.start()
        logger.info("Heartbeat monitor started")
