import socket
import time

SERVERS = [
    ("91.202.25.110", 5121, "Known Online"),
    ("159.69.240.215", 5122, "Target Mirror 1")
]

PAYLOADS = {
    "GS2": b'\x5C\x73\x74\x61\x74\x75\x73\x5C',
    "GS4": b'\xFE\xFD\x00\xE0\xEB\x2D\x0E'
}

print("Verifying UDP with socket.connect()...")

for ip, port, desc in SERVERS:
    print(f"\nScanning {desc} ({ip}:{port})...")
    
    for pname, pdata in PAYLOADS.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            
            # Connect UDP socket to remote address
            # This can help with some firewall/NAT associations
            sock.connect((ip, port))
            
            sock.send(pdata)
            
            # Recv (don't need recvfrom since connected)
            data = sock.recv(4096)
            print(f"  [{pname}] SUCCESS! Received {len(data)} bytes")
            sock.close()
            break # Found a working protocol for this server
            
        except socket.timeout:
            print(f"  [{pname}] Timeout")
        except Exception as e:
            print(f"  [{pname}] Error: {e}")
        finally:
            try:
                sock.close()
            except:
                pass
