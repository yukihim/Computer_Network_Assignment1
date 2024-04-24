import socket
import threading
import os
from client import peer

this_file_path = os.path.dirname(os.path.realpath(__file__))

host = '127.0.0.6'
port = 2415        
repo_dir = this_file_path + "/receiver_repo_test/"

receiver = peer.ReceiverPeer(host, port, repo_dir)

while True:
    print("command pattern")
    print("Command: fetch fname  | Usage: fetch file fname from first sender peer that have fname")
    print("Example: fetch test.txt")
    print("Command: end | Usage: shutdown this client" )
    print("Example: end")
    prompt = input()
    print("Inputed prompt:|" + prompt + "|")
    print("Executing...")

    arg = []
    arg = prompt.split(" ")
    if (arg[0] == 'fetch'):
        receiver.fetch(fname=arg[1])
        print("fetched")
    elif (arg[0] == 'end'):
        receiver.stop_receive()
        print("Stopped.")
        break