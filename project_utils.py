import Pyro5.api
from time import time
import logging
import sys
PEER_PREFIX = "peer."
TRACKER_PREFIX = "tracker.epoch."
PEER_DIRECTORY = "peer_data/"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"application_{int(time())}.log", mode="a")
    ]
)
logger = logging.getLogger()

def get_peer_id(id):
    return f"{PEER_PREFIX}{id}"

def get_tracker_id(epoch):
    return f"{TRACKER_PREFIX}{epoch}"

def get_name_service():
    return Pyro5.api.locate_ns()

def register_object(peer, daemon, name=None):
    name = name or f"{PEER_PREFIX}{peer.id}"
    uri = daemon.register(peer)
    bind_name(name, uri)
    return uri

def bind_name(name, uri):
    get_name_service().register(name, uri)

def call_proxy_method(name, function):
    with Pyro5.api.Proxy(get_name_service().lookup(name)) as proxy:
        try:
            return function(proxy)
        except Pyro5.errors.CommunicationError as e:
            logger.warning(f"Communication error with {name}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error calling method on {name}: {e}")
            return None