import socket
import sys
import time

# Known ONLINE server
IP_ONLINE = "91.202.25.110"
PORT_ONLINE = 5121 # Default port for standard IP? Or 5121? Let's try 5121.

# Target OFFLINE server
IP_TARGET = "159.69.240.215"
PORT_TARGET = 5122

def check_udp(ip, port):
    print(f"Checking {ip}:{port} (UDP)...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2.0)
        # FE FD 00 E0 EB 2D 0E - Standard NWN1 Query
        msg = b'\xFE\xFD\x00\xE0\xEB\x2D\x0E' 
        start = time.time()
        sock.sendto(msg, (ip, port))
        data, addr = sock.recvfrom(1024)
        end = time.time()
        print(f"SUCCESS from {addr}: {len(data)} bytes in {(end-start)*1000:.1f}ms")
        return True
    except Exception as e:
        print(f"Failed: {e}")
        return False

print("--- Validating Query on ONLINE server ---")
check_udp(IP_ONLINE, 5121)

print("\n--- Checking TARGET server ---")
check_udp(IP_TARGET, 5122)
