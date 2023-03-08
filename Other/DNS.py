from scapy.all import *
from scapy.layers.dns import DNS, DNSRR
from scapy.layers.inet import IP, UDP
from scapy.layers.l2 import Ether

import socket

DEVICE = "en0"
DNS_PORT = 53
DNS_IP = "127.0.0.3"

if __name__ == "__main__":
    dhcp_mac = str(get_if_hwaddr(DEVICE))

    dns_pool = {'PaperSoccer': "127.0.0.1"}

    while True:
        print("Listening for DNS requests...")
        packet = sniff(iface=DEVICE, filter=f"udp and port {DNS_PORT}", count=1)[0]
        print("DNS request received")

        time.sleep(1)

        if packet and packet.haslayer(DNS):
            name = packet[DNS].qd.qname  # Get the name from the DNS request packet
            name = name.decode("utf-8")
            name = name[:-1]
            ip_ans = None
            port_ans = None
            if name in dns_pool:  # Get the IP address from the DNS pool
                ip_ans = dns_pool[name]

            if ip_ans:
                print(f"Answering DNS request for {name} with {ip_ans}:{port_ans}")

                eth = Ether(src=dhcp_mac, dst=packet[Ether].src)
                ip = IP(src=DNS_IP, dst=packet[IP].src)
                udp = UDP(sport=DNS_PORT, dport=packet[UDP].sport)
                dns = DNS(id=packet[DNS].id, qr=1, qd=packet[DNS].qd,
                          an=DNSRR(rrname=packet[DNS].qd.qname, ttl=10, rdata=ip_ans, type=1))
                packet_ans = eth / ip / udp / dns

                sendp(packet_ans, iface=DEVICE)
                print("DNS request answered")
            else:
                print("Cant find the IP address for the requested name: " + name)

            time.sleep(1)
