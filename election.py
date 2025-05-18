import Pyro5.api
from project_utils import get_name_service, logger, call_proxy_method

class Election:
    def __init__(self, peer, epoch):
        self.ns = get_name_service()
        self.candidates = [k for k in self.ns.list().keys() if k.startswith("peer.")]
        self.peer = peer
        self.epoch = epoch
        logger.debug(f"Election initialized with peer_id={peer.id}, epoch={epoch}, candidates={self.candidates}")

    def execute(self):
        votes = 0 
        logger.debug(f"Starting election with {len(self.candidates)} candidates")
        if f"peer.{self.peer.id}" not in self.candidates:
            logger.debug(f"Peer {self.peer.id} not in candidates list, aborting election.")
            return False

        quorum = (len(self.candidates) // 2) + 1
        logger.debug(f"Quorum calculated as {quorum}")
        
        for name in self.candidates:
            try:
                logger.debug(f"Attempting to contact candidate {name}")
                if name == f"peer.{self.peer.id}":
                    if self.peer.vote(self.epoch):
                        votes += 1
                        logger.debug(f"Vote received from self ({name})")
                    else:
                        logger.debug(f"Vote denied by self ({name})")
                    continue
                if call_proxy_method(self.ns.lookup(name), function=lambda p: p.vote(self.epoch)):
                    votes += 1
                    logger.debug(f"Vote received from {name}")
                else:
                    logger.debug(f"Vote denied by {name}")
            except Exception as e:
                logger.debug(f"Failed to contact {name}: {e}")
                continue
        
        logger.debug(f"Total votes: {votes}, Quorum: {quorum}")
        return votes >= quorum
