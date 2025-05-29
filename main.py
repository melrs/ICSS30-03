# main.py
import Pyro5.api
import threading
import time
import random
import argparse
from node import Node  # Supondo que a classe Node esteja em node.py

class P2PNetwork:
    def __init__(self, num_peers=5, ns_host="localhost"):
        self.ns_host = ns_host
        self.peers = []
        self.num_peers = num_peers
        self._start_nameserver()
        
    def _start_nameserver(self):
        try:
            Pyro5.api.locate_ns(self.ns_host)
            print(f"Serviço de nomes já está rodando em {self.ns_host}")
        except Pyro5.errors.NamingError:
            print(f"Iniciando novo serviço de nomes em {self.ns_host}:9090")
            self.ns_thread = threading.Thread(
                target=Pyro5.api.start_ns_loop,
                kwargs={"host": self.ns_host, "port": 9090},
                daemon=True
            )
            self.ns_thread.start()
            time.sleep(1)  # Espera o NS iniciar

    def start_peer(self, peer_id):
        peer = Node(peer_id, ns_host=self.ns_host)
        daemon = Pyro5.api.Daemon();

        with Pyro5.api.locate_ns(self.ns_host) as ns:
            ns.register(f"Peer_{peer_id}", peer.uri)
            if peer_id == 0:  # Primeiro peer inicia como tracker
                ns.register(f"TrackerEpoch0", peer.uri)
        
        print(f"Peer {peer_id} iniciado com URI: {peer.uri}")
        threading.Thread(target=daemon.requestLoop, daemon=True).start()
        return peer

    def start_network(self):
        for i in range(self.num_peers):
            peer = self.start_peer(i)
            self.peers.append(peer)
            time.sleep(0.2)  # Espaço entre inicializações

        print("\nRedes P2P inicializadas. Comandos disponíveis:")
        print("add <arquivo> - Adiciona arquivo ao peer")
        print("remove <arquivo> - Remove arquivo do peer")
        print("list - Lista arquivos disponíveis")
        print("election - Força nova eleição")
        print("exit - Sair do programa\n")

        self.cli_loop()

    def cli_loop(self):
        current_peer = random.choice(self.peers)
        while True:
            try:
                cmd = input(">>> ").split()
                if not cmd:
                    continue

                if cmd[0] == "add" and len(cmd) == 2:
                    current_peer.adicionar_arquivo(cmd[1])
                elif cmd[0] == "remove" and len(cmd) == 2:
                    current_peer.remover_arquivo(cmd[1])
                elif cmd[0] == "list":
                    print("Arquivos disponíveis:", current_peer.listar_arquivos())
                elif cmd[0] == "election":
                    current_peer.iniciar_eleicao()
                elif cmd[0] == "exit":
                    break
                else:
                    print("Comando inválido")
            except Pyro5.errors.CommunicationError:
                print("Erro de comunicação. Tentando novo tracker...")
                current_peer = self._find_new_peer()

    def _find_new_peer(self):
        with Pyro5.api.locate_ns(self.ns_host) as ns:
            peers = ns.list(prefix="Peer_")
            return Pyro5.api.Proxy(random.choice(list(peers.values())))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sistema P2P com Pyro")
    parser.add_argument("-n", "--num-peers", type=int, default=5,
                        help="Número de peers na rede")
    parser.add_argument("--ns-host", default="localhost",
                        help="Host do serviço de nomes")
    
    args = parser.parse_args()
    
    network = P2PNetwork(num_peers=args.num_peers, ns_host=args.ns_host)
    network.start_network()
