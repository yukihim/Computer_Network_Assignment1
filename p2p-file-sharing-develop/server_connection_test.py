import socket
import threading
import os
from client import peer

this_file_path = os.path.dirname(os.path.realpath(__file__))

host = '127.0.0.5'
port = 1235        
repo_dir = this_file_path + "/sender_repo_test/"

sender = peer.SenderPeer(host, port, repo_dir)

while True:
    print("command pattern")
    print("Command: publish lname fname  | Usage: Publish file fname to server")
    print("Not use lname yet, so put what ever")
    print("Example: publish Test test.txt")
    print("Command: stop fname  | Usage: stop publish file fname")
    print("Example: stop test.txt")
    print("Command: end | Usage: shutdown this client" )
    print("Example: end")
    prompt = input()
    print("Inputed prompt:|" + prompt + "|")
    print("Executing...")

    arg = []
    arg = prompt.split(" ")
    if (arg[0] == 'publish'):
        sender.publish(lname= arg[1], fname= arg[2])
        print("publish.")
    elif (arg[0] == 'stop'):
        sender.stop_publish_specific_file(fname= arg[1])
        print("Stopped.")
    elif (arg[0] == 'end'):
        sender.stop_publish()
        print("End.")
        break