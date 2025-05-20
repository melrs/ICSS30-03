import os
import sys
import threading
from peer import Peer
from project_utils import register_object, logger, call_proxy_method, get_name_service, get_peer_id, PEER_DIRECTORY
from tracker_manager import TrackerManager
import Pyro5.api
import json
import base64


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
                    file = call_proxy_method(get_peer_id(selected_peer), function=lambda t: t.get_file(filename))
                    os.makedirs(f"{PEER_DIRECTORY}{peer.id}", exist_ok=True)
                    new_file_path = f"{PEER_DIRECTORY}{peer.id}/{filename}"
                    if file:
                        with open(new_file_path, "wb") as f:
                            decoded = base64.b64decode(file['data'])
                            print(decoded)
                            print(decoded.decode('utf-8'))

                            f.write(decoded)
                            success = call_proxy_method(peer.tracker_name, function=lambda t: t.update_index(peer.id, [filename]))
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
            print("Exiting. Goodbye!")
            break
        else:
            print("Invalid option. Please choose 1, 2, or 3.")


if __name__ == "__main__":
    logger.debug("Starting peer application")
    peer_id = sys.argv[1];                                                                      
    
    daemon = Pyro5.api.Daemon();                                                                    
    logger.debug("Pyro5 daemon created")

    peer = Peer(peer_id)
    peer_uri = register_object(peer, daemon);                            
    logger.debug(f"Peer registered with URI: {peer_uri}")
    
    #TrackerManager.initialize_peer_monitoring(peer, tracker_uri)
    peer.register_with_tracker(TrackerManager.lookup_tracker());                                                                  
    logger.debug(f"[{peer_id}] Registered with tracker");         
    threading.Thread(target=daemon.requestLoop, daemon=True).start()
    user_menu(peer);

