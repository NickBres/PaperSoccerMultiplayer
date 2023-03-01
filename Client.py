from scapy.all import *
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.layers.dns import DNS, DNSQR
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
from random import randint

DEVICE = "en0"

CLIENT_PORT = 68
CLIENT_IP = None
CLIENT_MAC = str(get_if_hwaddr(DEVICE))

DHCP_PORT = 67
DNS_IP = None
GAME_SERVER_IP = None


def get_ip_from_dhcp():
    print("Broadcasting DHCP request...")

    # Create a DHCP discover packet
    eth = Ether(src=CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
    ip = IP(src="0.0.0.0", dst="255.255.255.255")
    udp = UDP(sport=CLIENT_PORT, dport=DHCP_PORT)
    bootp = BOOTP(chaddr=CLIENT_MAC, xid=randint(0, 2 ** 32))
    dhcp = DHCP(options=[("message-type", "discover"), "end"])
    packet_discover = eth / ip / udp / bootp / dhcp

    # Send the packet and wait for a response
    sendp(packet_discover, iface=DEVICE)

    # Wait for a DHCP offer packet
    print("Waiting for DHCP offer...")
    packet_offer = sniff(iface=DEVICE, filter=f"udp and port {CLIENT_PORT}", count=1)[0]
    print("DHCP offer received")

    if packet_offer and packet_offer.haslayer(DHCP):
        # Get the IP address from the DHCP offer packet
        client_ip = packet_offer[BOOTP].yiaddr
        dns_ip = packet_offer[BOOTP].siaddr
        options = packet_offer[DHCP].options

        print(f"IP address: {client_ip}")
        print(f"DNS server IP address: {dns_ip}")

        # Create a DHCP request packet
        eth = Ether(src=CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
        ip = IP(src="0.0.0.0", dst="255.255.255.255")
        udp = UDP(sport=CLIENT_PORT, dport=DHCP_PORT)
        bootp = BOOTP(chaddr=CLIENT_MAC, xid=packet_offer[BOOTP].xid)
        dhcp = DHCP(options=[("message-type", "request"), ("server_id", packet_offer[BOOTP].siaddr),
                             ("requested_addr", client_ip), "end"])
        packet_request = eth / ip / udp / bootp / dhcp

        time.sleep(1)
        # Send the packet and wait for a response
        sendp(packet_request, iface=DEVICE)

        # Wait for a DHCP ACK packet
        ack = sniff(iface=DEVICE, filter=f"udp and port {CLIENT_PORT}", count=1)[0]

        if ack and ack.haslayer(DHCP):
            print("DHCP ACK received")
            return client_ip, dns_ip


def get_game_ip():
    print("Broadcasting DNS request...")

    # Create a DNS request packet
    eth = Ether(src=CLIENT_MAC, dst="ff:ff:ff:ff:ff:ff")
    ip = IP(src=CLIENT_IP, dst=DNS_IP)
    udp = UDP(sport=CLIENT_PORT, dport=53)
    dns = DNS(rd=1, qd=DNSQR(qname="PaperSoccer"))
    packet_request = eth / ip / udp / dns

    time.sleep(1)
    # Send the packet and wait for a response
    sendp(packet_request, iface=DEVICE)

    # Wait for a DNS response packet
    print("Waiting for DNS response...")
    packet_response = sniff(iface=DEVICE, filter=f"udp and port {CLIENT_PORT}", count=1)[0]
    print("DNS response received")

    if packet_response and packet_response.haslayer(DNS):
        # Get the IP address from the DNS response packet
        game_ip = packet_response[DNS].an.rdata

        print(f"Game server IP address: {game_ip}")

        return game_ip


if __name__ == "__main__":
    CLIENT_IP, DNS_IP = get_ip_from_dhcp()
    GAME_SERVER_IP = get_game_ip()
    print("Done. Starting game...")
