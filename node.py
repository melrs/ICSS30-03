import Pyro5.api
import threading
import time
import random
from typing import List

from project_utils import register_object


@Pyro5.api.expose
class Node:
    def __init__(self, id, ns_host: str = "localhost"):
        self.ns = Pyro5.api.locate_ns(ns_host)
        self.id = id
        self.uri = None
        self.files = set()
        self.is_tracker = False
        self.current_epoch = 0
        self.nodes_lock = threading.Lock()
        self.registered_nodes = []
        
        # Configuração de heartbeat
        self.heartbeat_interval = 0.1  # 100 ms
        self.tracker_timeout = random.uniform(0.15, 0.3)  # 150-300 ms
        self.heartbeat_timer = None
        
        # Inicialização
        self._register_in_ns()
        self._find_or_elect_tracker()
        self._start_role_specific_threads()

    def _register_in_ns(self):
        """Registra o nó no serviço de nomes"""
        daemon = Pyro5.api.Daemon();
        self.uri = register_object(self, daemon);                            
        print(f"Nó registrado: {self.uri}")

    def _find_or_elect_tracker(self):
        """Tenta encontrar o tracker atual ou inicia eleição"""
        try:
            tracker_uri = self.ns.lookup(f"TrackerEpoch{self.current_epoch}")
            self.tracker = Pyro5.api.Proxy(tracker_uri)
            self.tracker.registrar_no(self.uri, list(self.files))
            print(f"Tracker encontrado: {tracker_uri}")
        except Pyro5.errors.NamingError:
            self._initiate_election()

    def _start_role_specific_threads(self):
        """Inicia threads baseadas no papel atual"""
        if self.is_tracker:
            threading.Thread(target=self._send_heartbeats, daemon=True).start()
        else:
            self._reset_heartbeat_timer()

    def _send_heartbeats(self):
        """Envia heartbeats para todos os nós registrados (modo Tracker)"""
        while self.is_tracker:
            time.sleep(self.heartbeat_interval)
            with self.nodes_lock:
                for node_uri in self.registered_nodes.copy():
                    try:
                        proxy = Pyro5.api.Proxy(node_uri)
                        proxy.receber_heartbeat()
                    except Pyro5.errors.CommunicationError:
                        self.registered_nodes.remove(node_uri)

    def _reset_heartbeat_timer(self):
        """Reinicia o temporizador de detecção de falhas (modo Peer)"""
        if self.heartbeat_timer and self.heartbeat_timer.is_alive():
            self.heartbeat_timer.cancel()
        
        self.heartbeat_timer = threading.Timer(
            self.tracker_timeout, 
            self._detectar_falha_tracker
        )
        self.heartbeat_timer.start()

    def receber_heartbeat(self):
        """Método chamado pelo Tracker atual"""
        if not self.is_tracker:
            self._reset_heartbeat_timer()

    def _detectar_falha_tracker(self):
        """Detecta falha do tracker e inicia eleição"""
        if not self.is_tracker:
            print("Falha do tracker detectada! Iniciando eleição...")
            self._initiate_election()

    def _initiate_election(self):
        """Implementação do algoritmo Bully para eleição"""
        self.current_epoch += 1
        peers = self.ns.list(prefix="Peer_").values()
        higher_peers = [uri for uri in peers if uri > self.uri]
        
        if not higher_peers:
            self._become_tracker()
            return
        
        votes = 1  # Auto-voto
        for peer_uri in higher_peers:
            try:
                proxy = Pyro5.api.Proxy(peer_uri)
                if proxy.votar_eleicao(self.uri, self.current_epoch):
                    votes += 1
            except Pyro5.errors.CommunicationError:
                continue
        
        if votes > (len(peers) // 2):
            self._become_tracker()

    def _become_tracker(self):
        """Assume o papel de tracker"""
        self.is_tracker = True
        self.ns.register(f"TrackerEpoch{self.current_epoch}", self.uri)
        print(f"Novo tracker eleito: {self.uri}")
        self._start_role_specific_threads()
        
        # Notifica todos os peers
        peers = self.ns.list(prefix="Peer_").values()
        for uri in peers:
            if uri != self.uri:
                try:
                    proxy = Pyro5.api.Proxy(uri)
                    proxy.atualizar_tracker(self.uri, self.current_epoch)
                except Pyro5.errors.CommunicationError:
                    continue

    def votar_eleicao(self, candidate_uri: str, epoch: int) -> bool:
        """Lógica de votação para eleição"""
        if epoch == self.current_epoch:
            return candidate_uri > self.uri
        return False

    def atualizar_tracker(self, new_tracker_uri: str, new_epoch: int):
        """Atualiza referência para o novo tracker"""
        self.current_epoch = new_epoch
        self.tracker = Pyro5.api.Proxy(new_tracker_uri)
        self.is_tracker = False
        self._start_role_specific_threads()
        print(f"Tracker atualizado: {new_tracker_uri}")

    def registrar_no(self, node_uri: str, files: List[str]):
        """Registra novo nó (modo Tracker)"""
        with self.nodes_lock:
            if node_uri not in self.registered_nodes:
                self.registered_nodes.append(node_uri)
                print(f"Nó registrado: {node_uri} com arquivos: {files}")

    # Métodos para manipulação de arquivos
    def adicionar_arquivo(self, filename: str):
        self.files.add(filename)
        if not self.is_tracker:
            self.tracker.registrar_no(self.uri, list(self.files))

    def remover_arquivo(self, filename: str):
        self.files.discard(filename)
        if not self.is_tracker:
            self.tracker.registrar_no(self.uri, list(self.files))