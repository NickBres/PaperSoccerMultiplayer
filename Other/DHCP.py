from scapy.all import *
from scapy.layers.dhcp import DHCP, BOOTP
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether
import platform

DEVICE = None
DHCP_IP = "127.0.0.2"
DHCP_PORT = 67
DNS_IP = "127.0.0.3"
dhcp_mac = None
dhcp_pool = {'127.0.0.5': True,
             '127.0.0.6': True, }

if __name__ == "__main__":

    dns_pool = {'PaperSoccer': "127.0.0.1"}

    plat = platform.system()
    print(f'Platform: {plat}')
    if plat == 'Linux':
        DEVICE = 'enp0s1'
    elif plat == 'Darwin':  # Mac
        DEVICE = 'en0'
    else:
        print('Unknown platform. Enter device name manually:')
        DEVICE = input()

    dhcp_mac = str(get_if_hwaddr(DEVICE))

while True:
    print("Listening for DHCP requests...")
    packet = sniff(iface=DEVICE, filter=f"udp and port {DHCP_PORT}", count=1)[0]
    print("DHCP request received")

    time.sleep(1)

    if packet and packet.haslayer(DHCP):
        # Get the IP address from the DHCP offer packet
        client_mac = packet[BOOTP].chaddr
        client_xid = packet[BOOTP].xid
        client_port = packet[UDP].sport
        options = packet[DHCP].options

        found = None
        if packet[DHCP].options[0][1] == 1:
            print("DHCP Discover received")
            for ip, available in dhcp_pool.items():
                if available:
                    dhcp_pool[ip] = False
                    found = ip
                    break
            if not found:
                print("No IP addresses available")
                continue

            print(f"Offering IP address: {found}")

            # Create a DHCP offer packet
            eth = Ether(src=dhcp_mac, dst=client_mac)
            ip = IP(src=DHCP_IP, dst="255.255.255.255")
            udp = UDP(sport=DHCP_PORT, dport=client_port)
            bootp = BOOTP(chaddr=client_mac, xid=client_xid, yiaddr=found, siaddr='127.0.0.3', op=2)
            dhcp = DHCP(options=[("message-type", "offer"),
                                 ("server_id", DHCP_IP),
                                 ("requested_addr", found),
                                 ("dns-name", DNS_IP),
                                 'end'])
            packet_offer = eth / ip / udp / bootp / dhcp
            print(DEVICE)
            sendp(packet_offer, iface=DEVICE)
        elif packet[DHCP].options[0][1] == 3:
            print("DHCP Request received")
            client_ip = packet[DHCP].options[2][1]
            if client_ip in dhcp_pool:
                dhcp_pool[client_ip] = False
                print(f"IP address: {client_ip}")

            if not client_ip:
                print("No IP addresses available")
                continue

            # Create a DHCP ACK packet
            eth = Ether(src=dhcp_mac, dst=client_mac)
            ip = IP(src=DHCP_IP, dst="255.255.255.255")
            udp = UDP(sport=DHCP_PORT, dport=client_port)
            bootp = BOOTP(chaddr=client_mac, xid=client_xid)
            dhcp = DHCP(options=[("message-type", "ack"),
                                 'end'])
            packet_ack = eth / ip / udp / bootp / dhcp
            sendp(packet_ack, iface=DEVICE)
            print("DHCP ACK sent")
        else:
            print("DHCP Unknown packet received")
