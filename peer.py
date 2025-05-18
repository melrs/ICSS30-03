import os
import random
import Pyro5.api
from project_utils import logger, call_proxy_method

class Peer:
    def __init__(self, peer_id, tracker_uri=None):
        self.id = peer_id
        self.files = self.load_files()
        self.tracker_uri = tracker_uri if tracker_uri else None
        self.epoch = call_proxy_method(self.tracker_uri, function=lambda t: t.get_epoch()) if self.tracker_uri else 0
        self.file_index = {}
        logger.debug(f"Peer initialized with ID: {self.id}, Tracker URI: {tracker_uri}")
        self.is_tracker = False
        self.register_with_tracker()

    def load_files(self):
        peer_dir = f"peer_data/{self.id}"
        os.makedirs(peer_dir, exist_ok=True); 
        logger.debug(f"Peer directory created: {peer_dir}")
        return os.listdir(peer_dir); 

    @Pyro5.api.expose
    def list_files(self):
        return (self.id, self.files)

    @Pyro5.api.expose
    def has_file(self, filename):
        return filename in self.files

    @Pyro5.api.expose
    def get_file(self, filename):
        if filename in self.files:
            with open(f"peer_data/{self.id}/{filename}", "rb") as f:
                return f.read()
        return None

    def register_with_tracker(self):
        if self.tracker_uri:
            call_proxy_method(self.tracker_uri, function=lambda tracker: tracker.update_index(self.id, self.files))

    @Pyro5.api.expose
    def receive_file(self, filename, data):
        with open(f"peer_data/{self.id}/{filename}", "wb") as f:
            f.write(data)
        if filename not in self.files:
            self.files.append(filename)
        if self.tracker:
            self.tracker.update_index(self.id, self.files)

    @Pyro5.api.expose
    def vote(self, epoch):
        logger.debug(f"Vote received for epoch {epoch} from peer {self.id}")
        if epoch > self.epoch:
            self.epoch = epoch
            return True
        return False

    @Pyro5.api.expose
    def get_epoch(self):
        return self.epoch
    
    @Pyro5.api.expose
    def update_index(self, peer_id, files):
        for f in files:
            self.file_index.setdefault(f, set()).add(peer_id)

    @Pyro5.api.expose
    def lookup_file(self, filename):
        return list(self.file_index.get(filename, []))

    @Pyro5.api.expose
    def heartbeat(self):
        hb = random.choice([True, True, False])
        logger.debug(f"Heartbeat check: {hb}")
        return hb
