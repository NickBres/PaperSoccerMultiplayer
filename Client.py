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
    DEVICE = "en0"

    CLIENT_PORT = 68
    CLIENT_IP = None
    CLIENT_MAC = str(get_if_hwaddr(DEVICE))

    DHCP_PORT = 67
    DNS_IP = None
    GAME_SERVER_IP = '127.0.0.1'
    GAME_SERVER_PORT = 5000

    game = Model.Game()
    view = None
    view_thread = None
    client_socket = None
    isGameInitialized = False

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
        print("Broadcasting DNS request...")

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
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
            client_socket.connect((self.GAME_SERVER_IP, self.GAME_SERVER_PORT))
            print("Connected to game server")
            self.client_socket = client_socket
            packet = Packet.Packet("connect")
            client_socket.sendall(packet.serialize())
            self.get_game_from_server(client_socket)
            self.view = View.View(self, self.game)
            self.view.run()


    def game_update(self):
        print("Updating game...")
        packet = Packet.Packet("update")
        self.client_socket.sendall(packet.serialize())
        self.get_game_from_server(self.client_socket)
        self.view.set_game(self.game)
        if not self.isGameInitialized and self.game.state == 'play':
            self.isGameInitialized = True
            self.view.game_init()
        self.view.change_screen()

    def get_game_from_server(self,client_socket):
        data = client_socket.recv(64000)
        packet = Packet.PacketGame()
        packet.deserialize(data)
        self.game = packet.game

    def send_options(self, width, height):
        packet = Packet.PacketOptions(width, height)
        self.client_socket.sendall(packet.serialize())
        time.sleep(1)
        self.game_update()

    def send_move(self, toX, toY):
        packet = Packet.PacketMove(toX,toY)
        self.client_socket.sendall(packet.serialize())
        time.sleep(1)
        self.game_update()

    def send_again(self):
        packet = Packet.Packet("again")
        self.client_socket.sendall(packet.serialize())
        self.get_game_from_server(self.client_socket)
        self.view = View.View(self, self.game)
        self.game_update()
        self.view.run()


    def send_exit(self):
        packet = Packet.Packet("exit")
        self.client_socket.sendall(packet.serialize())
        time.sleep(1)
        self.client_socket.close()


if __name__ == '__main__':
    Client()
