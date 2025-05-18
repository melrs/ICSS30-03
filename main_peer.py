import sys
from peer import Peer
from project_utils import register_object, logger
from tracker_manager import TrackerManager
import Pyro5.api

if __name__ == "__main__":
    logger.info("Starting peer application")
    peer_id = sys.argv[1];                                                                      
    
    daemon = Pyro5.api.Daemon();                                                                    
    logger.debug("Pyro5 daemon created")
    tracker_uri = TrackerManager.lookup_tracker()

    peer = Peer(peer_id, tracker_uri)
    peer_uri = register_object(peer, daemon);                            
    logger.debug(f"Peer registered with URI: {peer_uri}")
    
    TrackerManager.initialize_peer_monitoring(peer, daemon, tracker_uri)
    peer.register_with_tracker();                                                                  
    logger.debug(f"[{peer_id}] Registered with tracker");         
    logger.info(f"[{peer_id}] Running. URI: {peer_uri}")
    daemon.requestLoop()
