import sys
sys.path.insert(0, '')
from client import peer
import os

this_file_path = os.path.dirname(os.path.realpath(__file__))
sender = peer.SenderPeer('127.0.0.1', 1234, this_file_path + '/sender/')

sender.publish(fname='image.png')

while True:
    prompt = input()
    print("Inputed prompt:|" + prompt + "|")
    print("Executing...")

    if (prompt == 'share'):
        sender.share(fname='image.png')
        print("Shared.")
    elif (prompt == 'stop'):
        print("Stopped.")
        break

sender.stop_publish()