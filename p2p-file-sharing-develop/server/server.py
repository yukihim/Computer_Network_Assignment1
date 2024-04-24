import socket
import threading
import time
import os
import xml.etree.ElementTree as ET
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)

sys.path.append(parent)
from config.request import RequestTypes


def wlan_ip():
    import subprocess
    result=subprocess.run('ipconfig',stdout=subprocess.PIPE,text=True).stdout.lower()
    scan=0
    for i in result.split('\n'):
        if 'wireless' in i: scan=1
        if scan:
            if 'ipv4' in i: return i.split(':')[1].strip()

MAX_CONNECTIONS = 5
#SERVER_HOST = '127.0.0.1'
SERVER_HOST = wlan_ip()
SERVER_PORT = 12345  
BROADCAST_START_PORT = 13000
BROADCAST_END_PORT = 13010

PING_ACTIVE_CLIENT_CLOCK = 5  # seconds
BROADCAST_CYCLE_TIME = 2 # seconds

LISTEN_DURATION = 4 # seconds

class Server:
    def __init__(self):
        self._lock = threading.Lock()
        
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind((SERVER_HOST, SERVER_PORT))
        self._server_socket.listen(MAX_CONNECTIONS)
        print(SERVER_HOST, SERVER_PORT)
        
        self._broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        self._peers = {}  # A dictionary to store peer information [(address, port)] = list of available files
        self._conntected_client_threads = {} # A dictionary to store connected client [(client socket)] = (client threads)
        self._connected_client_ping_responses = {} # A dictionary to store ping timer [(client socket)] = (boolean)

        self._running = True

        self._listen_thread = threading.Thread(target=self._update_listen_to_new_client)
        self._ping_thread = threading.Thread(target=self._update_ping_active_clients)
        self._broadcast_thread = threading.Thread(target=self._update_broadcast_server_address)

        # Receive commands from clients (POST, REQUEST_END, GET_PEER) 
        # Update the self._peers dictionary as needed
        # Return a list of peer with requested file to the cilent
    
    def _parse_packet(self, data):
        if not data.strip().startswith('<root>'):
            data = '<root>' + data + '</root>'  # Add a single root element
        root = ET.fromstring(data)
        packets = []
        for child in root:
            packet = {}
            packet['request'] = child.tag
            ip_port_data = child.text.split('|')
            packet['ip'] = ip_port_data[0]
            packet['port'] = ip_port_data[1]
            packet['data'] = ip_port_data[2] if len(ip_port_data) > 2 else ''
            packets.append(packet)
        return packets

    def _handle_client_packet(self, client_socket : socket.socket):
        # Assuming every request is send like this:
        # <REQUEST>HOST/PORT/DATA</REQUEST> 
        # DATA can be comma-seperated
        # example: <post>192.168.1.1/8000/text.txt,img.png</post>

        
        #*nvhuy: a while loop should ensure the server keep receive request from a client until the client is terminated
        while self._running:
            # Seperate request and data from the package
            try :
                packet = client_socket.recv(1024).decode("utf-8").strip()
            except:
                print(f"Client {client_socket} cannot be reached")
                break
            
            if not packet:
                continue
            
            packet_lines = self._parse_packet(packet)
            #print(packet, packet_lines)

            for packet_line in packet_lines:
                request = packet_line['request']
                ip = packet_line['ip']
                port = packet_line['port']
                data = packet_line['data']
                
                #print(request, ip, port, data)

                try:
                    if request == RequestTypes.PUBLISH.value:  
                    # Process a POST request from a peer to announce its available files
                        
                        available_files = data.split(",")
                        self._publish_file(ip, port, available_files)
                        
                    elif(request == RequestTypes.UNPUBLISH.value):
                    # Process a REQUEST_END request from a peer to remove a file from its list
                    # or remove itself from the server
                        removed_file = data
                        self._unpublish_file(ip, port, removed_file)


                    elif request == RequestTypes.GET_PEER.value:
                    # Process a GET_PEER request from a peer looking for a file
                    # Return a list of peers with the requested file
                        self._get_peer(client_socket, data)

                    elif request == RequestTypes.PONG.value:
                        self._connected_client_ping_responses[client_socket] = True
                        #print(f"Client {client_socket} is alive at {time.time()}")

                    elif request == RequestTypes.REVEAL.value:
                        available_files = data.split(",")
                        self._update_peers(ip, port, available_files)
                        #print(f"Client {client_socket} is alive at {time.time()}")

                    elif request == RequestTypes.DISCONNECT.value:
                        self._disconnect_client(client_socket)
                        continue

                    else: 
                        print("Unknown request")
                
                except Exception as e:
                    print("Error: {}", str(e))

            #*nvhuy: We do not want to close the socket here
            # finally:
            #     client_socket.close()

    def _publish_file(self, host, port, available_files):
        # Add the peer to the self._peers dictionary
        # with the list of available files
        # or update the list of available files if the peer is already in the dictionary

        with self._lock:
            if (host, int(port)) in self._peers:
                # Only add files that are not already in the list
                for file in available_files:
                    if file not in self._peers[(host, int(port))]:
                        self._peers[(host, int(port))].append(file)
            else:
                self._peers[(host, int(port))] = available_files

    def _update_peers(self, host, port, available_files):
        with self._lock:
            # If the peer already exists in the dictionary
            if (host, int(port)) in self._peers:
                current_files = set(self._peers[(host, int(port))])
                new_files = set(available_files)

                # Add files from available_files that are not in current_files
                files_to_add = new_files - current_files
                self._peers[(host, int(port))].extend(files_to_add)

                # Remove files from current_files that are not in available_files
                files_to_remove = current_files - new_files
                updated_files = []
                for file in self._peers[(host, int(port))]:
                    if file not in files_to_remove:
                        updated_files.append(file)

                self._peers[(host, int(port))] = updated_files

            else:
                # If the peer does not exist in the dictionary, add it
                self._peers[(host, int(port))] = available_files

    def _unpublish_file(self, host, port, removed_file):
        # Remove the specified file from the peer's list of available files
        # or remove the peer from the self._peers dictionary if no file is specified

        print("removed ", removed_file)
        with self._lock:
            if not removed_file:
                del self._peer[(host, int(port))]
            else:
                if (host, int(port)) in self._peers:
                    if removed_file in self._peers[(host, int(port))]:
                        self._peers[(host, int(port))].remove(removed_file)
    
    def _disconnect_client(self, client_socket : socket.socket):
        with self._lock:
            
            self._conntected_client_threads.pop(client_socket)
            self._connected_client_ping_responses.pop(client_socket)
            

            for peer, files in self._peers.items():
                if peer[0] == client_socket.getpeername()[0] and peer[1] == client_socket.getpeername()[1]:
                    self._peers.pop(peer)
                    break
            
            client_socket.close()


    def _handle_send_request_to_client(self, client_socket : socket.socket, request : RequestTypes, data):
        # Send a 'GET_PEER' command

        server_ip, server_port = client_socket.getpeername()

        request_string = request.value
        ip_string = str(server_ip)
        port_string = str(server_port)
        data_string = str(data)
        #Handle command data packet to send to server
        send_packet = "<"+request_string+">"+ip_string+"|"+ port_string +"|"+ data_string+"</"+request_string+">"
        send_packet = send_packet.encode("utf-8")
        try:
            client_socket.send(send_packet)
        except:
            print(f"Client {client_socket} cannot be reached")
        # Return a list of peers with the requested file
        # in the form of a string (comma seperated between each)
        # Should looks like this:

    def _get_peer(self, client_socket, filename):
        # Return a list of peers with the requested file
        # in the form of a string (comma seperated between each)
        # Should looks like this:

        matching_peers = []

        with self._lock:
            for peer, files in self._peers.items():
                if filename in files:
                    matching_peers.append(f"{peer[0]}:{peer[1]}")

        if matching_peers:
            # Send a list of peers with the requested file to the client
            # in the form of a string (comma seperated between each)
            # Should looks like this: 127.0.0.1:1234,222.222.3.4:3456
            
            self._handle_send_request_to_client(client_socket, RequestTypes.RETURN_PEER, "".join(matching_peers))
        else:
            # No peer with the requested file
            self._handle_send_request_to_client(client_socket, RequestTypes.RETURN_PEER, "")

    def _ping_client(self, client_socket):
        try:
            # Send a 'PING' command
            
            self._handle_send_request_to_client(client_socket, RequestTypes.PING, str( time.time() ))
            # Wait for a response
            self._connected_client_ping_responses[client_socket] = False
            #print(f"Pinging client {client_socket} at {time.time()}")

            return True

        except socket.error:
            return False
    
    def _check_ping_alive(self, client_socket):
        if client_socket in self._connected_client_ping_responses:
            return self._connected_client_ping_responses[client_socket]
        return False


    def _discover_clients(self, client_socket):
        try:
            self._handle_send_request_to_client(client_socket, RequestTypes.DISCOVER, "")
        except socket.error:
            print(f"Client {client_socket} cannot be discovered")
    

    def _update_listen_to_new_client(self):
        print("start listening...")
        while self._running:
            try:
                self._server_socket.settimeout(LISTEN_DURATION) # Set a timeout 
                client_socket, client_address = self._server_socket.accept()
            except socket.timeout:
                #print("No client connected within the timeout period.")
                continue
            except Exception as e:
                print(f"An error occurred: {e}")
                continue

            if client_address: 
                print(f"Accepted socket with address {client_address}")
            client_handler = threading.Thread(target=self._handle_client_packet, args=(client_socket,))
            client_handler.start()

            self._conntected_client_threads[client_socket] = client_handler

        self._server_socket.close()

        print("end listening")


    def _update_ping_active_clients(self):
        # Remove dead peers from the self._peers dictionary
        # A peer is considered dead if it does not respond to a ping
        print("start pinging...")

        while self._running:
            time.sleep(PING_ACTIVE_CLIENT_CLOCK)

            print("Pinging...")
            
            
            with self._lock:
                
                pinged_timer_clients = list(self._connected_client_ping_responses.keys()) # Create a copy of keys to iterate over
                for client_socket in pinged_timer_clients:
                    if not self._check_ping_alive(client_socket):
                        print(f"Client {client_socket} is timeout at {time.time()}")
                        self._disconnect_client(client_socket)
                        continue


                connected_clients = list(self._conntected_client_threads.items()) # Create a copy of keys to iterate over
                for client_socket, client_thread in connected_clients:
                    # try to ping the client
                    if not self._ping_client(client_socket):
                        print(f"Client {client_socket} cannot be pinged")

                        self._disconnect_client(client_socket)
                        continue

                    # try to discover the client files
                    self._discover_clients(client_socket)
                        
                for peer in list(self._peers.keys()):
                    #If any peer does not have publish file anymore, pop that peer from _peers dict 
                    print(f"client {peer} with fname {self._peers[peer]}")
                    if not self._peers[peer]:
                        self._peers.pop(peer)

        print("end pinging")

    def _update_broadcast_server_address(self):
        while self._running:
            try:

                for port in range(BROADCAST_START_PORT, BROADCAST_END_PORT):
                    message = f"SERVER_ADDRESS {SERVER_HOST}:{SERVER_PORT}"
                    self._broadcast_socket.sendto(message.encode(), ('<broadcast>', port))
                
                time.sleep(BROADCAST_CYCLE_TIME)
            except Exception as e:
                print(f"Error broadcasting server address: {e}")


    def start(self):
        self._listen_thread.start()
        self._ping_thread.start()
        self._broadcast_thread.start()
        print("Server started")

    def stop(self):
        self._running = False
        self._listen_thread.join()
        self._ping_thread.join()
        self._broadcast_thread.join()

        print("Server stopped")







