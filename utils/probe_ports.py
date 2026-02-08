import socket
import time

TARGET_IP = "159.69.240.215"
# TARGET_IP = "91.202.25.110" # Debug with known good

print(f"Scanning ports on {TARGET_IP} with GS4 query...")
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(0.5) # Fast scan

payload = b'\xFE\xFD\x00\x00\x00\x00\x00' # Basic GS4

for port in range(5120, 5135):
    try:
        sock.sendto(payload, (TARGET_IP, port))
        try:
            data, addr = sock.recvfrom(1024)
            print(f"[FOUND] Port {port}: Received {len(data)} bytes")
        except socket.timeout:
            pass
            # print(f"Port {port}: Timeout")
    except Exception as e:
        print(f"Port {port}: Error {e}")

print("Scan complete.")
sock.close()
