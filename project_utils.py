import Pyro5.api
from time import time
import logging
PEER_PREFIX = "peer."
TRACKER_PREFIX = "tracker.epoch."
PEER_DIRECTORY = "peer_data/"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.FileHandler(f"application_{int(time())}.log", mode="a"),
        #logging.StreamHandler()
    ]
)

def logger(name, status, message):
    logging.getLogger(name).debug(f"[{status}] {message}")

def get_peer_name(id):
    return f"{PEER_PREFIX}{id}"

def get_tracker_id(epoch):
    return f"{TRACKER_PREFIX}{epoch}"

def get_name_service():
    return Pyro5.api.locate_ns()

def register_object(peer, name=None):
    name = name or f"{PEER_PREFIX}{peer.id}"
    uri = Pyro5.api.Daemon().register(peer)
    bind_name(name, uri)
    return uri

def bind_name(name, uri):
    get_name_service().register(name, uri)

def get_epoch_from_name(name):
    try:
        epoch = int(name.split('.')[-1])
        return epoch
    except ValueError:
        logging.getLogger(__name__).warning(f"Invalid tracker name format: {name}")
        return None
    
def call_proxy_method(name, function):
    # print(f"Calling method on {name}")
    with Pyro5.api.Proxy(get_name_service().lookup(name)) as proxy:
        # print(f"Proxy for {name} created")
        # print(proxy)
        try:
            proxy._pyroTimeout = 10
            return function(proxy)
        except Pyro5.errors.TimeoutError as e:
            logging.getLogger(__name__).warning(f"Timeout error with {name}: {e}")
            print(f"Timeout error with {name}: {e}")
            return None
        except Pyro5.errors.CommunicationError as e:
            logging.getLogger(__name__).warning(f"Communication error with {name}: {e}")
            return None
        except Exception as e:
            logging.getLogger(__name__).warning(f"Error calling method on {name}: {e}")
            return None