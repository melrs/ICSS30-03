import threading
import Pyro5
from peer import Peer
from tracker_manager import TrackerManager
from project_utils import logger, register_object

def status(peer_id):
    return 'TRACKER' if peer_id.startswith("tracker") else 'PEER'

def launch_peer_instance(peer_id):
    logger(__name__, status(peer_id),"Starting peer application")                                                                 
    
    daemon = Pyro5.api.Daemon();                                                                    
    logger(__name__, status(peer_id),"Pyro5 daemon created")

    peer = Peer(peer_id, TrackerManager.lookup_tracker())
    peer_uri = register_object(peer, daemon);                            
    logger(__name__, status(peer_id),f"Peer registered with URI: {peer_uri}")
    
    peer.register_with_tracker(TrackerManager.lookup_tracker());                                                                  
    logger(__name__, status(peer_id),f"[{peer_id}] Registered with tracker");         
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    return peer
