import socket
import threading
import time
import xml.etree.ElementTree as ET

from config.request import RequestTypes

"""
For socket.listen(MAX_NONACCEPTED_CONN).

socket.listen([backlog]) backlog here controls how many 
non-accept()-ed connections are allowed to be outstanding.
Should be set to 5

https://stackoverflow.com/questions/2444459/python-sock-listen
"""
MAX_NONACCEPTED_CONN = 5

BUFF_SIZE = 1024

"""
Server Host address and Port 
Any peer should have a connection to server
To be able to request any action regarding it type (senderPeer or receiverPeer)
"""
#SERVER_HOST = '127.0.0.1'

BROADCAST_IP = '0.0.0.0'
SERVER_PORT = 12345  

BROADCAST_START_PORT = 13000
BROADCAST_END_PORT = 13010

PEER_CONNECTION_TIME = 5
class Peer:
    def __init__(self, host, port, repo_dir):
        self._is_running = True
        
        self._host_ip = host
        self._port = port

        self._socket_for_server_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_ip = None
        
        self._connections = []
    
        self._repo_dir = repo_dir
        self._published_file = []
        
        self._listen_server_broadcast_thread = threading.Thread(target=self._handle_server_address_broadcast, args=())
        self._listen_server_broadcast_thread.start()

   
    def _handle_server_address_broadcast(self):
        while self._is_running:
            try:
                broadcast_socket = self._get_broadcast_socket()
                
                data, addr = broadcast_socket.recvfrom(BUFF_SIZE)
                message = data.decode()
                if message.startswith("SERVER_ADDRESS"):
                    _, server_address = message.split()
                    server_ip, server_port = server_address.split(':')
                    print(f"Received server IP: {server_ip}, server broadcast port: {server_port}")
                    self._server_ip = server_ip

                    self._connect_to_server()

                    broadcast_socket.close()
                    break
            except Exception as e:
                print(f"Error handling server address broadcast: {e}")

    def _get_broadcast_socket(self):
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for port in range(BROADCAST_START_PORT, BROADCAST_END_PORT):
            try:
                broadcast_socket.bind((BROADCAST_IP, port))
                broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                break
            except Exception as e:
                continue
        return broadcast_socket


    def _connect_to_server(self):
        """
        Connect to existing server
        If we can not have a connection, This peer consider doing nothing
        We should close the socket and terminate this peer object 
        (Python have a garbage collector so i think manual termination is not necessary in this case)
        """
        try:
            self._server_connection_edge = self._socket_for_server_connection.connect((self._server_ip, SERVER_PORT))
            print(f"Connected to server with edge {self._server_connection_edge}")
            self._server_listen_thread = threading.Thread(target=self._listen_to_server)
            self._server_listen_thread.start()

        except socket.error as connection_error:
            print(f"Error code: {connection_error}")
            self._socket_for_server_connection.close()
            

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
    
    def _send_packet_to_server(self, request : RequestTypes , data = ""):
        # Assuming every request is send like this:
        # <REQUEST>HOST/PORT/DATA</REQUEST> 
        # DATA can be comma-seperated
        # example: <post>192.168.1.1|8000|text.txt,img.png</post>
        
        request_string = request.value
        ip_string = str(self._host_ip)
        port_string = str(self._port)
        data_string = str(data)
        
        #Handle command data packet to send to server
        send_packet = "<"+request_string+">"+ip_string+"|"+ port_string +"|"+ data_string+"</"+request_string+">"
        send_packet = send_packet.encode("utf-8")
        print(send_packet)
        try:
            self._socket_for_server_connection.sendto(send_packet, (self._server_ip, SERVER_PORT))
        except socket.error as error:
            print(f"Error occur trying to send request to server. Error code: {error}") 

    def _listen_to_server(self):
        raise NotImplementedError("Subclass must implement this method")
    
    
    def _reveal_all_published_file(self):
        all_published_file = ""        
        
        for fname in self._published_file:
            all_published_file += fname + ","
        
        all_published_file = all_published_file.rstrip(',') # Remove the last comma

        if all_published_file != "":
            self._send_packet_to_server( RequestTypes.REVEAL , all_published_file)

    def _terminate_peer(self):
        self._is_running = False

        self._send_packet_to_server( RequestTypes.DISCONNECT , "")

        self._server_listen_thread.join()
        self._listen_server_broadcast_thread.join()

        if self._socket_for_server_connection:
            self._socket_for_server_connection.close()
        

        print("Peer connection ended.")



class SenderPeer(Peer):
    def __init__(self, host, port, repo_dir):
        super().__init__(host, port, repo_dir)
        
        # Create a separate thread for listening to other peers
        #*nvhuy: should only create 1 thread for 1 peer lifetime, so i put itt at init
        self._peer_listen_thread = threading.Thread(
            target=self._listening_to_receiver_peer_connect
        )
        self._peer_listen_thread.start()


    def _listen_to_server(self):
        while self._is_running:
            try:
                packet = self._socket_for_server_connection.recv(BUFF_SIZE).decode('utf-8')
            except socket.error as e:
                print(f"End of connection with server: {e}")
                break
            if not packet:
                continue
            
            packet_lines = self._parse_packet(packet)
            #print(packet, packet_lines)

            for packet_line in packet_lines:
                request = packet_line['request']
                data = packet_line['data']
                print(request, data)
                
                if request == RequestTypes.PING.value:
                    print("SP Pinged from server ", data, " at ", time.time())
                    self._send_packet_to_server(RequestTypes.PONG)
                elif request == RequestTypes.DISCOVER.value:
                    self._reveal_all_published_file()
                else :
                    print("Unknown request from server")

            
                

    def _listening_to_receiver_peer_connect(self):
        """
        Continuously looping to listen to any peer peer connection.
        """
        print(f"{self._host_ip} and {self._port}")
        self._socket_for_peer_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_for_peer_connection.bind((self._host_ip, self._port))
        self._socket_for_peer_connection.listen(MAX_NONACCEPTED_CONN)

        # print(f"Listening for new connection to {self._host} : {self._port}")
        while self._is_running:
            self._socket_for_peer_connection.settimeout(PEER_CONNECTION_TIME)  # Set a timeout of 5 seconds

            try:
                connectionEdge, otherPeerAddress = self._socket_for_peer_connection.accept()
            except socket.timeout:
                continue
            with connectionEdge:
                print('Connected by', otherPeerAddress, connectionEdge)
                self._connections.append(connectionEdge)
                #*Assume package send from receiver:
                #*FNAME
                fname = connectionEdge.recv(BUFF_SIZE)
                fname = fname.decode('utf-8')
                self.share(fname)
                self._connections.remove(connectionEdge)
                connectionEdge.close()
            # (otherPeerHost, otherPeerPort) = socket.getnameinfo(otherPeerAddress, True)
            # otherPeerPort = int(otherPeerPort)
            # print(f"connection : {connectionEdge}")
            # print(f"Allow connection from {otherPeerAddress}")

        self._socket_for_peer_connection.close()
        print("Peer connection ended.")
    
   

    def publish(self, lname: str = "", fname: str = "text.txt"):
        """
        Post file information to the server and start listening for any connection
        from other peers to start sharing.
        """
        
        if fname in self._published_file:
            print(f"Already published {fname}")
            #return # Published file should only be check at server side
        

        #Add file to published list
        self._published_file.append(fname)
        # Post file information to the server
        
        self._send_packet_to_server(RequestTypes.PUBLISH, fname)
        
        #? QUESTION: nvhuy, Why did we want to recreate a new thread for every time we publish here?
        
        #? QUESTION: nvhuy, should we have a list of pair (lname, fname) store in sender peer so that
        #? Went the receiver send a fetch request with lname, 
        #? we can find the fname file directory and send this file to receiver
        #* This would match well with nkhoa solution proposal in receiverPeer._connect_with_peer
        
    def stop_publish_specific_file(self, fname):
        """
        Request the server to remove this peer from list of active peers of a specific and close the temporary socket
        connection itself.
        """
        if fname not in self._published_file:
            print(f"Can find published file name {fname}")
            return
        
        self._published_file.remove(fname)
        self._send_packet_to_server(RequestTypes.UNPUBLISH, fname)
        
    def stop_publish(self):
        """
        Request the server to remove this peer from list of active peers and close the socket
        connection itself.
        """

        while len(self._published_file) != 0:
            fname = self._published_file[0]
            self.stop_publish_specific_file(fname=fname)
            print(len(self._published_file))

        while len(self._connections) != 0: # Wait for all connection to be closed
            continue

        self._is_running = False

        self._peer_listen_thread.join()
        self._terminate_peer()
        

    def share(self, fname: str):
        """
        Start broadcasting file 'fname' too all of its connections.
        """

        # ! ISSUE: share could only share one fname. In fact, one SenderPeer
        # should be able to send multiple files to multiple peers differently.
        # $ PROPOSAL: NKhoa, see _connect_with_peer() for more details
        with open(self._repo_dir + fname, "rb") as infile:
            
            #*nvhuy: I found this easier way to send file
            for conn in self._connections:
                        print(f"{conn}")
                        conn.sendfile(infile)
                        
                        
            #*nvhuy: Still want to keep the other way for reference later if needed
            # while True:
            #     data_chunk = infile.read(BUFF_SIZE)
            #     if not data_chunk:
            #         print(f"share {fname} completed")
            #         break

            #     if len(self._connections) > 0:
                    
            #         for conn in self._connections:
            #             print(f"{conn}")
            #             conn.sendall(data_chunk)
            #     else:
            #         print("No peer connection was established.")
            #         print("Waiting for more peers...")
            #         break


class ReceiverPeer(Peer):
    def __init__(self, host, port, repo_dir):
        super().__init__(host, port, repo_dir)
        self._getting_file = None

        self._socket_for_peer_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket_for_peer_connection.bind((self._host_ip, self._port))
        self._fetch_thread = None

    def _listen_to_server(self):
        while self._is_running:
            try:
                packet = self._socket_for_server_connection.recv(BUFF_SIZE).decode('utf-8')
            except socket.error as e:
                print(f"End of connection with server: {e}")
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
                
                print(request, ip, port, data)

                if request == RequestTypes.PING.value:
                    print("RP Pinged from server ", data, " at ", time.time())
                    self._send_packet_to_server(RequestTypes.PONG)

                elif request == RequestTypes.DISCOVER.value:
                    self._reveal_all_published_file()

                elif request == RequestTypes.RETURN_PEER.value:
                    peers = self._handle_receive_peers_string(data)
                    print("RP Received peer list from server ", peers)
                    if len(peers) > 0:
                        self._contact_peer_and_fetch(peers)
                    else:
                        print("No peer has this file")

    

    def _handle_receive_peers_string(self, receiver_peers) -> [(str, int)]:
        """
        This function handle received data from server about peers who have fname
        Return the list of peer (host, port) 
        """
        _peers = []
    
        _peers = receiver_peers.split(',')
        _return_peers = []
        if (len(receiver_peers) < 2): return _return_peers
        if (':' not in receiver_peers): return _return_peers
        for peer in _peers:
            host, port = peer.split(':')
            port = int(port)
            peer = (host, port)
            _return_peers.append(peer)
        return _return_peers


    def fetch(self, fname: str) -> bool:
        """
        API for fetching file 'fname' from another peer. The fetched file will be 
        automatically written into this peer's repository.

        Returns True on successful fetch, False otherwise.
        """
        self._getting_file = fname
        
        self._send_packet_to_server(RequestTypes.GET_PEER,fname)
        
    
    def _contact_peer_and_fetch(self, peers_arr):
        self._fetch_thread = threading.Thread(target=self._fetch_from_peer, args=(peers_arr,))
        self._fetch_thread.start()

    def _fetch_from_peer(self, peers_arr):
        (sender_host, sender_port) = peers_arr[0]
        fname = self._getting_file

        connection_result = self._connect_with_peer(sender_host, sender_port, fname)
       
        if (connection_result != None):

            with open(self._repo_dir + fname, "wb") as outfile:
                while True:
                    print("receive: ")
                    data_chunk = self._socket_for_peer_connection.recv(BUFF_SIZE)
                    if not data_chunk:
                        break

                    outfile.write(data_chunk)

            print("Receiving file completed.")
            return True
        else:
            return False

    def _connect_with_peer(self, other_peer_host, other_peer_port, fname) -> bool:
        """
        Get connected to other_peer.

        Returns True on successful connection, False on failed connection.
        """
        try:
            print(f"Connecting {self._host_ip}:{self._port} peer to {other_peer_host}:{other_peer_port}")
            
            
            self._socket_for_peer_connection.connect((other_peer_host, other_peer_port))
            
            self._socket_for_peer_connection.sendto(fname.encode('utf-8'),(other_peer_host, other_peer_port))
            # ! ISSUE: A Peer connection should also come with the FILENAME that connection
            # is requesting, since one sender could send different files to different receivers
            # at the same time.
            
            # $ PROPOSAL: NKhoa: Perhaps right after connection, we should send some kind of 
            # meta information (such as REQUESTED_FILENAME) to the SenderPeer to make our request explicit
            # about what file this peer is requesting specifically

            return True
        except socket.error as connection_error:
            print(f"Error code: {connection_error}")
            return False
    

    def stop_receive(self):
        '''
        Terminate socket connected with server 
        '''
        self._is_running = False

        if (self._fetch_thread != None):
            self._fetch_thread.join()

        self._socket_for_peer_connection.close()

        self._terminate_peer()