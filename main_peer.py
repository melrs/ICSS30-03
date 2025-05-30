import os
import sys
import threading
import Pyro5
from peer import Peer
from project_utils import call_proxy_method, get_peer_name, PEER_DIRECTORY, logger, register_object
import base64

from tracker_manager import TrackerManager

def status(peer_id):
    return 'TRACKER' if peer_id.startswith("tracker") else 'PEER'

def launch_peer_instance(peer_id):
    logger(__name__, status(peer_id),"Starting peer application")
    daemon = Pyro5.api.Daemon()                                                                
    peer = Peer(peer_id, daemon)
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    return peer


def user_menu(peer):
    while True:
        print("\n=== Peer-to-Peer File Sharing ===")
        print("1 - Search for a file")
        print("2 - List all files from tracker")
        print("3 - Exit")
        option = input("Enter your choice: ").strip()

        if option == "1":
            filename = input("Enter the file name: ").strip()
            owners = call_proxy_method(peer.tracker_name, function=lambda t: t.lookup_file(filename))

            if not owners:
                print(f"No peers have the file '{filename}'.")
            else:
                print(f"Peers that have '{filename}':")
                for i, owner in enumerate(owners, start=1):
                    print(f"  {i}. {owner}")

                choice = input("Download from which peer? (type number or leave blank to cancel): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(owners):
                    selected_peer = owners[int(choice) - 1]
                    file = call_proxy_method(selected_peer, function=lambda t: t.get_file(filename))
                    os.makedirs(f"{PEER_DIRECTORY}{peer.id}", exist_ok=True)
                    new_file_path = f"{PEER_DIRECTORY}{peer.id}/{filename}"
                    if file:
                        with open(new_file_path, "wb") as f:
                            decoded = base64.b64decode(file['data'])
                            f.write(decoded)
                            print(f"File '{filename}' downloaded from {selected_peer}.")
                            call_proxy_method(selected_peer, function=lambda p: p.update_index())
                        print(f"File '{filename}' downloaded successfully from {selected_peer}.")
                    else:
                        print(f"Failed to download file from {selected_peer}.")
                else:
                    print("Download canceled.")

        elif option == "2":
            files = call_proxy_method(peer.tracker_name, function=lambda t: t.show_index())
            if not files:
                print("No files are currently registered with the tracker.")
            else:
                print("Files available on the tracker:")
                for file in files:
                    print(f"  - {file}")

        elif option == "3":
            logger(__name__, peer.status(),f"[{peer.id}] Exiting peer application")
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1, 2, or 3.")

if __name__ == "__main__":
    peer = launch_peer_instance(sys.argv[1])
    user_menu(peer);

