import datetime
import os
import random
import threading
import time
import Pyro5
from election import Election
from project_utils import bind_name, get_name_service, get_tracker_id, logger, call_proxy_method, get_epoch_from_name, get_peer_name, PEER_PREFIX
from tracker_manager import TrackerManager

class Peer:
    def __init__(self, peer_id, daemon, tracker_name=None):
        self.is_tracker = False
        self.id = peer_id
        self.tracker_name = tracker_name if tracker_name else None
        self.epoch = get_epoch_from_name(self.tracker_name) if self.tracker_name else 0
        self.timeout = random.uniform(0.15, 0.3)
        self.timer = None
        self.files = self._load_files()
        self.election = None
        #tracker atributes
        self.file_index = {}
        self.peers = [] # # pega todos os peers do ns
        self.lock = threading.Lock()
        self.heartbeater = None
        self._stop_heartbeat = threading.Event()
        self.blacklist = set()

        self.uri = self._register(daemon)
        self._find_tracker()

    def _load_files(self):
        peer_dir = f"peer_data/{self.id}"
        os.makedirs(peer_dir, exist_ok=True); 
        logger(__name__, self.status(), f"[{self.id}] Peer directory created: {peer_dir}")
        return os.listdir(peer_dir); 

    def _register(self, daemon):
        name = f"{PEER_PREFIX}{self.id}"
        uri = daemon.register(self)
        bind_name(name, uri)
        logger(__name__, self.status(), f"[{self.id}] Peer registered with name: {name}, URI: {uri}")
        return uri
    
    def status(self):
        return 'TRACKER' if  self.is_tracker else 'PEER'
    
    def _find_tracker(self):
        tracker_name = TrackerManager.lookup_tracker()
        if tracker_name:
            try:
                tracker_uri = get_name_service().lookup(tracker_name)
                logger(__name__, self.status(), f"[{self.id}] Tracker URI found: {tracker_uri}")
                self.tracker = Pyro5.api.Proxy(tracker_uri)
                self.tracker.new_peer(get_peer_name(self.id), list(self.files))
                logger(__name__, self.status(), f"[{self.id}] Registered with tracker: {tracker_name}")
                time.sleep(0.1)  # Wait for tracker to process the new peer
                self.epoch = get_epoch_from_name(tracker_name)
                logger(__name__, self.status(), f"[{self.id}] Current epoch set to: {self.epoch}")
                self.tracker_name = tracker_name
                logger(__name__, self.status(), f"[{self.id}] Tracker found: {tracker_uri}")
            except Pyro5.errors.NamingError:
                logger(__name__, self.status(), f"[{self.id}] Tracker not found")
            except Pyro5.errors.CommunicationError:
                logger(__name__, self.status(), f"[{self.id}] Communication error with tracker")
        self.reset_monitor()

                                                                  
    @Pyro5.api.expose
    def get_file(self, filename):
        if filename in self.files:
            with open(f"peer_data/{self.id}/{filename}", "rb") as f:
                return f.read()
        return None
    
    @Pyro5.api.expose
    def vote(self, epoch):
        self.reset_monitor()
        self.election_running = True
        if epoch > self.epoch:
            self.epoch = epoch # pro tracker n variar durante eleição
            logger(__name__, self.status(), f"[{self.id}] Vote accepted for epoch: {epoch}")
            return True
        logger(__name__, self.status(), f"[{self.id}] Vote denied for epoch: {epoch}, current epoch: {self.epoch}")
        return False
    
    @Pyro5.api.expose
    def reset_monitor(self):
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
        
        timeout = random.uniform(2.15, 2.3)  # 150-300 ms
        self.timer = threading.Timer(timeout, self.promote_tracker)
        self.timer.start()
        # logger(__name__, self.status(), f"[{self.id}] Heartbeat monitor reset with timeout: {timeout:.2f} seconds for tracker: {self.tracker_name}")

    @Pyro5.api.expose
    @Pyro5.api.oneway
    def heartbeat_receiver(self, tracker_name, epoch):
        self.reset_monitor()
        # logger(__name__, self.status(), f"[{self.id}] Heartbeat received from tracker: {tracker_name}, epoch: {epoch}")
        if epoch > self.epoch:
            self.epoch = epoch
            logger(__name__, self.status(), f"[{self.id}] Updating epoch to: {self.epoch}")
            try:
                tracker_name = get_tracker_id(epoch)
                tracker_uri = get_name_service().lookup(tracker_name)
                tracker = Pyro5.api.Proxy(tracker_uri)
                tracker.register_files(get_peer_name(self.id), list(self.files))
                self.tracker_name = tracker_name
                logger(__name__, self.status(), f"Updating tracker name to: {self.tracker_name}")
            except Exception as e:
                logger(__name__, self.status(), f"Failed to update tracker: {e}")

        if self.election and self.election.is_alive():
            self.election.join()  # End the election thread if it's running
    
    @Pyro5.api.expose
    def heartbeat(self): #executa em uma thread
        if self.heartbeater:
            self._stop_heartbeat.set()
            self.heartbeater.join()
       
        self.blacklist.clear()
        self._stop_heartbeat.clear()
        self.heartbeater = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeater.start()

    def send_heartbeat(self):
        while not self._stop_heartbeat.is_set():
            with self.lock:
                active_peer_uris = get_name_service().list(prefix=PEER_PREFIX)
                for item in active_peer_uris.items():
                    name, uri = item
                    if str(uri) == str(self.uri) or name in self.blacklist:
                        continue
                    try:
                        peer = Pyro5.api.Proxy(uri)
                        peer.heartbeat_receiver(self.tracker_name, self.epoch)
                        # logger(__name__, self.status(), f"Heartbeat sent to {name} at {uri}")
                    except Exception as e:
                        self.blacklist.add(name)
                        self.remove_peer_files(name)
                        #logger(__name__, self.status(), f"Failed to contact {name}: {e}")
            time.sleep(0.1)

    @Pyro5.api.expose
    def promote_tracker(self):
        logger(__name__, self.status(), f"[{self.id}] Promoting to tracker due to heartbeat timeout.")
        self.epoch += 1
        logger(__name__, self.status(), f"[{self.id}] Starting election with epoch: {self.epoch}")
        election = Election(self, self.epoch)
        
        def election_task():
            if election.execute():
                logger(__name__, self.status(), f"[{self.id}] Election successful. Promoting to tracker.")
                self.is_tracker = True
                self.tracker_name = get_tracker_id(self.epoch)
                bind_name(self.tracker_name, self.uri)
                self.register_files(get_peer_name(self.id), list(self.files))
                self.heartbeat()
                if self.timer:
                    self.timer.cancel()
                logger(__name__, self.status(), f"[{self.id}] [epoch: {self.epoch}] Elected as new tracker with name: {self.tracker_name}")
                print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Elected as new tracker with name: {self.tracker_name}")
            else:
                self.reset_monitor()
                logger(__name__, self.status(), "Election failed.")
        
        self.election = threading.Thread(target=election_task, daemon=True)
        self.election.start()

    # @Pyro5.api.expose
    # def add_peer(self, peer_uri, files):
    #     with self.lock:
    #         if peer_uri not in self.peers:
    #             self.peers.append(peer_uri)
    #         self.register_files(peer_uri, files)

    @Pyro5.api.expose
    def register_files(self, peer_name, files):
        for f in files:
            self.file_index.setdefault(f, set()).add(peer_name)
    
    def remove_peer_files(self, peer_name):
        try:
            for f in list(self.file_index.keys()):
                if peer_name in self.file_index[f]:
                    self.file_index[f].remove(peer_name)
                    if not self.file_index[f]:
                        del self.file_index[f]
        except Exception as e:
            print(f"Error removing files for peer {peer_name}: {e}")
        logger(__name__, self.status(), f"[{self.id}] Removed files for peer: {peer_name}")

    @Pyro5.api.expose
    def new_peer(self, peer_name, files):
        self.register_files(peer_name, files)
        self.heartbeat()

    def fetch_peer_uri(self):
        return get_name_service().lookup(get_peer_name(self.id))
    
    def add_file(self, filename):
        self.files.add(filename)
        if self.current_tracker_uri:
            try:
                tracker_uri = get_name_service().lookup(self.tracker_name)
                tracker_proxy = Pyro5.api.Proxy(tracker_uri)
                tracker_proxy.register_files(self.name, [filename])
            except Pyro5.errors.CommunicationError:
                logger.error("Falha ao registrar arquivo no tracker")
    
    @Pyro5.api.expose
    def show_index(self):
        logger(__name__, self.status(), f"[{self.id}] Showing file index: {list(self.file_index.keys())}")
        return list(self.file_index.keys())

    @Pyro5.api.expose
    def lookup_file(self, filename):
        logger(__name__, self.status(), f"[{self.id}] Looking up file: {filename}")
        return list(self.file_index.get(filename, []))
    
    @Pyro5.api.expose
    def get_file(self, filename):
        if filename in self.files:
            with open(f"peer_data/{self.id}/{filename}", "rb") as f:
                return f.read()
        return None
    
    @Pyro5.api.expose
    def update_index(self):
        self.files = self._load_files()
        tracker_uri = get_name_service().lookup(self.tracker_name)
        tracker = Pyro5.api.Proxy(tracker_uri)
        tracker.register_files(get_peer_name(self.id), list(self.files))

