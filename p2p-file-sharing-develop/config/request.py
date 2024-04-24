from enum import Enum

class RequestTypes(Enum):
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"

    FETCH = "fetch"
    GET_PEER = "get_peer"
    RETURN_PEER = "return_peer"

    
    PING = "ping"
    PONG = "pong"

    DISCOVER = "discover"
    REVEAL = "reveal"
    
    DISCONNECT = "disconnect"

    