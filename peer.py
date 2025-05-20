import os
import random
import re
import Pyro5.api
from election import Election
from heartbeat import HeartbeatMonitor
from project_utils import PEER_PREFIX, get_name_service, logger, call_proxy_method, bind_name, get_peer_id, get_tracker_id
from tracker_manager import TrackerManager
from datetime import datetime

class Peer:
    def __init__(self, peer_id, tracker_uri=None):
        self.id = peer_id
        self.files = self.load_files()
        self.tracker_name = tracker_uri if tracker_uri else None
        logger.debug(f"[{self.id}] Tracker URI: {self.tracker_name}")
        self.epoch = call_proxy_method(self.tracker_name, function=lambda t: t.get_epoch()) if self.tracker_name else 0
        self.file_index = {}
        self.heartbeat_monitor = None
        logger.debug(f"[{self.id}] Peer initialized with ID: {self.id}, Tracker: {tracker_uri} Epoch: {self.epoch}")
        self.is_tracker = False

    def load_files(self):
        peer_dir = f"peer_data/{self.id}"
        os.makedirs(peer_dir, exist_ok=True); 
        logger.debug(f"[{self.id}] Peer directory created: {peer_dir}")
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

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def register_with_tracker(self, tracker_name):
        logger.debug(f"[{self.id}] Registering with tracker: {tracker_name}")
        self.tracker_name = tracker_name
        if not self.is_tracker:
            logger.debug(f"[{self.id}] Starting heartbeat monitor for tracker: {self.tracker_name}")
            self.heartbeat_monitor = HeartbeatMonitor(self.tracker_name, lambda: self.promote_tracker())
            self.heartbeat_monitor.start(random.randint(150, 300))
        if self.tracker_name:
            logger.debug(f"[{self.id}] Updating index with tracker: {self.tracker_name}")
            call_proxy_method(self.tracker_name, function=lambda tracker: tracker.update_index(self.id, self.files))
        self.epoch = call_proxy_method(self.tracker_name, function=lambda t: t.get_epoch()) if self.tracker_name else 0

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
        if epoch > self.epoch:
            self.epoch = epoch
            logger.debug(f"[{self.id}] Vote accepted for epoch: {epoch}")
            return True
        logger.debug(f"[{self.id}] Vote denied for epoch: {epoch}, current epoch: {self.epoch}")
        return False

    @Pyro5.api.expose
    def get_epoch(self):
        return self.epoch
    
    @Pyro5.api.expose
    @Pyro5.api.oneway
    def update_index(self, peer_id, files):
        for f in files:
            self.file_index.setdefault(f, set()).add(peer_id)

    @Pyro5.api.expose
    def lookup_file(self, filename):
        return list(self.file_index.get(filename, []))
    
    @Pyro5.api.expose
    def show_index(self):
        return list(self.file_index.keys())
    
    @Pyro5.api.expose
    def heartbeat(self):
        hb = random.choice([True, True, True, True, True, False])
        logger.debug(f"[{self.id}] Heartbeat check: {hb}")
        return hb
    
    @Pyro5.api.expose
    def promote_tracker(self):
        logger.debug(f"[{self.id}] Starting election with epoch: {self.epoch + 1}")
        election = Election(self, self.epoch + 1)
        name_service = get_name_service()
        self.heartbeat_monitor.stop()
        if election.execute():
            logger.debug(f"[{self.id}] Election successful. Promoting to tracker.")
            if self.tracker_name:
                call_proxy_method(self.tracker_name, function=lambda t: t.demote_tracker())
            self.is_tracker = True
            all_peer_entries = {name: uri for name, uri in name_service.list().items() if re.match(PEER_PREFIX, name) and name != get_peer_id(self.id)}
            self.is_tracker = True
            self.tracker_name = get_tracker_id(self.epoch)
            bind_name(self.tracker_name, self.fetch_peer_uri())
            self.register_with_tracker(self.tracker_name)

            for _, uri in all_peer_entries.items():
                self.load_index(uri)
                call_proxy_method(uri, function=lambda p: p.register_with_tracker(self.tracker_name))
            logger.info(f"[{self.id}] [epoch: {self.epoch}] Elected as new tracker with ID: {id}")
        else:
            logger.warning("Election failed.")

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def demote_tracker(self):
        logger.debug(f"[{self.id}] Demoting tracker")
        self.is_tracker = False
        self.tracker_name = None

    def load_index(self, uri):
        id, files = call_proxy_method(uri, function=lambda p: p.list_files())
        logger.debug(f"[{self.id}] Updating index for peer {id} with files: {files}")
        self.update_index(id, files)

    def fetch_peer_uri(self):
        return get_name_service().lookup(get_peer_id(self.id))