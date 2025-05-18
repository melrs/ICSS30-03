import Pyro5.api
from time import time
import logging
import sys
PEER_PREFIX = "peer."

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger()

def get_name_service():
    return Pyro5.api.locate_ns()

def register_object(peer, daemon, name=None):
    name = name or f"{PEER_PREFIX}{peer.id}"
    uri = daemon.register(peer)
    ns = get_name_service()
    ns.register(name, uri)
    return uri

def now():
    return int(time() * 1000)

def call_proxy_method(uri, function):
    with Pyro5.api.Proxy(uri) as proxy:
        try:
            return function(proxy)
        except Pyro5.errors.CommunicationError as e:
            logger.warning(f"Communication error with {uri}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error calling method on {uri}: {e}")
            return None