import sys
sys.path.insert(0, '')
from client import peer
import os

this_file_path = os.path.dirname(os.path.realpath(__file__))
receiver = peer.ReceiverPeer('127.0.0.1', 8000, this_file_path + '/receiver/')

while True:
    receiver._socket.recv(1024);