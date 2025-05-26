import threading
from typing import List
import Pyro5
from project_utils import get_name_service, logger, call_proxy_method

class Election:
    def __init__(self, peer, epoch):
        self.ns = get_name_service()
        self.election_in_progress = False
        self.candidates = self.ns.list(prefix="peer.").values()
        self.peer = peer
        self.epoch = epoch
        self.peers_lock = threading.Lock()
        logger(__name__, self.status(), f"Election initialized with peer_id={peer.id}, epoch={epoch}, candidates={self.candidates}")

        
    def _get_peers(self) -> List[str]:
        with self.peers_lock:
            try:
                return [uri for uri in get_name_service().list(prefix="Peer_").values()] # Testar com keys para pegar os names
            except Pyro5.errors.NamingError:
                return []
            
    def status(self):
        return 'PEER'
        
    def execute(self) -> None:
        if self.election_in_progress:
            return

        self.election_in_progress = True
        try:
            peers = self._get_peers()
            votes = 1  # self-vote

            for peer_uri in peers:
                try:
                    if call_proxy_method(peer_uri, function=lambda proxy: proxy.vote(self.epoch)):
                        votes += 1
                        logger(__name__, self.status(), f"Vote received from {peer_uri}")
                except Pyro5.errors.CommunicationError:
                    continue

            if votes > (len(peers) // 2):
                self.election_in_progress = False
                return True
            else:
                print(f"Election failed. Waiting for new leader...")
                
        finally:
            self.election_in_progress = False
