# P2P File Sharing com PyRO5

Este projeto é uma aplicação distribuída para compartilhamento de arquivos entre 5 peers, com um tracker eleito dinamicamente, utilizando PyRO5.

## Componentes
- `main_peer.py`: inicializa cada peer.
- `peer.py`: lógica de peer.
- `tracker.py`: tracker (índice central).
- `election.py`: eleição de tracker.
- `heartbeat.py`: detecção de falhas.
- `utils.py`: funções auxiliares.
- `start_ns.sh`: script para iniciar o name server.

## Como Executar

### 1. Inicie o Name Server
```bash
chmod +x start_ns.sh
./start_ns.sh
```

### 2. Crie diretórios para cada peer
```bash
mkdir -p peer_data/peer1
echo "conteudo" > peer_data/peer1/arquivo.txt
```

### 3. Inicie os peers
```bash
python3 main_peer.py peer1
python3 main_peer.py peer2
...
```

Cada peer pode se tornar tracker dinamicamente com base em eleição e falha do atual tracker.

