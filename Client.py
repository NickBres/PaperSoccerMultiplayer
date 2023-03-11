import pickle
import time

from scapy.all import *
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from random import randint

import Model
import View
import Packet


class Client:
    # ///////////////////////////////////////
    # //       Dont forget to check        //
    # ///////////////////////////////////////
    DEVICE = "enp0s1"  # en0 for mac, enp0s1 for VM ubuntu
    # ///////////////////////////////////////

    CLIENT_PORT = 5050
    CLIENT_IP = '127.0.0.1'
    CLIENT_MAC = str(get_if_hwaddr(DEVICE))

    DHCP_PORT = 67
    DNS_IP = None
    GAME_SERVER_IP = '127.0.0.1'
    GAME_SERVER_PORT = 5000
    GAME_SERVER_PORT_UDP = 5001

    game = Model.Game()
    view = None
    view_thread = None
    client_socket = None
    client_socket_udp = None

    def __init__(self):
        # self.CLIENT_IP, self.DNS_IP = self.get_ip_from_dhcp()
        # self.GAME_SERVER_IP = self.get_game_ip()
        self.connect_to_game()
        print("Done. Starting game...")

    def get_ip_from_dhcp(self):
        print("Broadcasting DHCP request...")

        # Create a DHCP discover packet
        eth = Ether(src=self.CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
        ip = IP(src="0.0.0.0", dst="255.255.255.255")
        udp = UDP(sport=self.CLIENT_PORT, dport=self.DHCP_PORT)
        bootp = BOOTP(chaddr=self.CLIENT_MAC, xid=randint(0, 2 ** 32))
        dhcp = DHCP(options=[("message-type", "discover"), "end"])
        packet_discover = eth / ip / udp / bootp / dhcp

        # Send the packet and wait for a response
        sendp(packet_discover, iface=self.DEVICE)

        # Wait for a DHCP offer packet
        print("Waiting for DHCP offer...")
        packet_offer = sniff(iface=self.DEVICE, filter=f"udp and port {self.CLIENT_PORT}", count=1)[0]
        print("DHCP offer received")

        if packet_offer and packet_offer.haslayer(DHCP):
            # Get the IP address from the DHCP offer packet
            client_ip = packet_offer[BOOTP].yiaddr
            dns_ip = packet_offer[BOOTP].siaddr
            options = packet_offer[DHCP].options

            print(f"IP address: {client_ip}")
            print(f"DNS server IP address: {dns_ip}")

            # Create a DHCP request packet
            eth = Ether(src=self.CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
            ip = IP(src="0.0.0.0", dst="255.255.255.255")
            udp = UDP(sport=self.CLIENT_PORT, dport=self.DHCP_PORT)
            bootp = BOOTP(chaddr=self.CLIENT_MAC, xid=packet_offer[BOOTP].xid)
            dhcp = DHCP(options=[("message-type", "request"), ("server_id", packet_offer[BOOTP].siaddr),
                                 ("requested_addr", client_ip), "end"])
            packet_request = eth / ip / udp / bootp / dhcp

            time.sleep(1)
            # Send the packet and wait for a response
            sendp(packet_request, iface=self.DEVICE)

            # Wait for a DHCP ACK packet
            ack = sniff(iface=self.DEVICE, filter=f"udp and port {self.CLIENT_PORT}", count=1)[0]

            if ack and ack.haslayer(DHCP):
                print("DHCP ACK received")
                return client_ip, dns_ip

    def get_game_ip(self):
        print("Create DNS request...")

        # Create a DNS request packet
        eth = Ether(src=self.CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
        ip = IP(src=self.CLIENT_IP, dst=self.DNS_IP)
        udp = UDP(sport=self.CLIENT_PORT, dport=53)
        dns = DNS(rd=1, qd=DNSQR(qname="PaperSoccer"))
        packet_request = eth / ip / udp / dns

        time.sleep(1)
        # Send the packet and wait for a response
        sendp(packet_request, iface=self.DEVICE)

        # Wait for a DNS response packet
        print("Waiting for DNS response...")
        packet_response = sniff(iface=self.DEVICE, filter=f"udp and port {self.CLIENT_PORT}", count=1)[0]
        print("DNS response received")

        if packet_response and packet_response.haslayer(DNS):
            # Get the IP address from the DNS response packet
            game_ip = packet_response[DNS].an.rdata
            print(f"Game server IP address: {game_ip}")

            return game_ip

    def connect_to_game(self):
        print("Connecting to game server...")
        self.client_socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP socket for receiving game data
        self.client_socket_udp.settimeout(2)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:  # TCP socket for sending commands
            client_socket.connect((self.GAME_SERVER_IP, self.GAME_SERVER_PORT))
            print("Connected to game server")
            self.client_socket = client_socket
            packet = Packet.Packet("connect")  # Ask the server to connect the client to the game
            client_socket.sendall(packet.serialize())
            # self.get_game_from_server(client_socket)  # TCP
            self.view = View.View(self)  # Create the view (GUI)
            self.view.run()  # Start the view

    def game_update(self):
        print("Updating game...")
        packet = Packet.Packet("update")  # Ask the server to update the game
        self.client_socket.sendall(packet.serialize())
        # self.get_game_from_server(client_socket) # TCP
        isUpdated = self.get_game_from_server_udp()
        if not isUpdated:
            self.send_update_failed()
            return self.ask_for_update()
        self.view.set_game(self.game)  # Update the view with the new game
        self.view.change_screen()  # Change the screen if needed (e.g. from menu to game)

    def get_game_from_server(self, client_socket):
        data = client_socket.recv(64000)
        packet = Packet.PacketGame()  # Create a packet to deserialize the game
        packet.deserialize(data)  # Deserialize the game from received data
        self.game = packet.game

    def send_update_failed(self):
        packet = Packet.Packet("update failed")  # Ask the server to update the game
        self.client_socket.sendall(packet.serialize())

    def three_way_handshake(self):
        print("Three way handshake...")
        while True:
            self.client_socket_udp.sendto(b"connect", (
                self.GAME_SERVER_IP, self.GAME_SERVER_PORT_UDP))
            try:
                packet, addr = self.client_socket_udp.recvfrom(1024)  # Receive SynAck from the server
            except socket.timeout:
                print("Timeout No SynAck")
                continue
            if packet == b"SYNACK":
                self.client_socket_udp.sendto(b"ACK", (self.GAME_SERVER_IP, self.GAME_SERVER_PORT_UDP))
                break

    def get_game_from_server_udp(self):
        print("Getting game from server rudp...")
        SEPARATOR = "<BARAK>"

        self.three_way_handshake()

        count = 0
        packets = [None] * 64
        print("Loading game...")
        break_count = 0
        while True:
            try:
                packet, addr = self.client_socket_udp.recvfrom(2048)  # Receive a packet from the server
            except socket.timeout:
                print("Timeout")
                break_count += 1
                if break_count == 5:
                    return False
                continue
            if packet == b"END":
                print("Game received")
                self.client_socket_udp.sendto(b"ACK", (self.GAME_SERVER_IP, self.GAME_SERVER_PORT_UDP))
                break

            try:
                part, seq, first, last = packet.split(
                    SEPARATOR.encode())  # Split the packet to the data, the sequence number and the window size
            except ValueError:
                print("Error in packet")
                continue
            seq = int(seq)
            first = int(first)  # 1 if first in window, 2 if last in window
            last = int(last)
            print(f"Received packet {seq} in window ({first} : {last})")
            packets[seq] = part  # Add the data to the packets list
            count += 1

            if seq == last and count != last - first + 1:  # If the sequence number is not the expected one
                print(f'got {count} packets but expected {last - first + 1}')
                self.client_socket_udp.sendto(b"NACK", (self.GAME_SERVER_IP, self.GAME_SERVER_PORT_UDP))
                window_size = last - first + 1
                count = 0
                print('something went wrong. NACK sent')
            elif seq == last:
                count = 0
                self.client_socket_udp.sendto(b"ACK", (self.GAME_SERVER_IP, self.GAME_SERVER_PORT_UDP))
                print('window received properly. ACK sent')
                break_count = 0
            # time.sleep(0.1)

        print(f"Game received")
        count = 0
        for packet in packets:
            if packet is None:
                break
            else:
                count += 1
        data = b"".join(packets[:count])

        packetGame = Packet.PacketGame()  # Create a packet to deserialize the game
        packetGame.deserialize(data)  # Deserialize the game from received data
        self.game = packetGame.game  # Update the game
        print("Game deserialized")
        return True

    def ask_for_update(self):
        print("Asking for update...")
        packet = Packet.Packet("update?")
        self.client_socket.sendall(packet.serialize())
        try:
            data = self.client_socket.recv(1024)
        except socket.timeout:
            print("Timeout")
            return self.ask_for_update()
        packet.deserialize(data)
        if packet.message == "yes":
            print("Update is available")
            self.game_update()
        else:
            print("No update available")

    def send_options(self, width, height):  # Send the options to the server to create a new game
        packet = Packet.PacketOptions(width, height)  # Create a packet with the options
        self.client_socket.sendall(packet.serialize())  # Send the packet to the server
        time.sleep(1)
        self.ask_for_update()  # Ask for an update to get the game

    def send_move(self, toX, toY):
        print(f"Sending move to ({toX}, {toY})")
        packet = Packet.PacketMove(toX, toY)  # Create a packet with the move
        self.client_socket.sendall(packet.serialize())  # Send the packet to the server
        time.sleep(1)
        self.ask_for_update()  # Ask for an update to get the updated game

    def send_again(self):  # Send a message to the server to start a new game
        print("Sending again...")
        packet = Packet.Packet("again")  # Create a packet with the message
        self.client_socket.sendall(packet.serialize())  # Send the packet to the server
        self.view = View.View(self)  # Initialize the view (GUI)
        self.view.run()  # Start the view

    def send_exit(self):  # Send a message to the server about the client's exit
        print("Sending exit...")
        packet = Packet.Packet("exit")
        self.client_socket.sendall(packet.serialize())
        time.sleep(1)
        self.client_socket.close()
        self.client_socket_udp.close()


if __name__ == '__main__':
    Client()
