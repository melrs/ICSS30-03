import threading
import Pyro5
from peer import Peer
from tracker_manager import TrackerManager
from project_utils import logger, register_object

def launch_peer_instance(peer_id):
    logger.debug("Starting peer application")                                                                 
    
    daemon = Pyro5.api.Daemon();                                                                    
    logger.debug("Pyro5 daemon created")

    peer = Peer(peer_id)
    peer_uri = register_object(peer, daemon);                            
    logger.debug(f"Peer registered with URI: {peer_uri}")
    
    peer.register_with_tracker(TrackerManager.lookup_tracker());                                                                  
    logger.debug(f"[{peer_id}] Registered with tracker");         
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    return peer