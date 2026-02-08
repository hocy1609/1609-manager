import socket
import time

# Known ONLINE server
TARGET_IP = "91.202.25.110" 
TARGET_PORT = 5121

print(f"Verifying UDP on {TARGET_IP}:{TARGET_PORT} with socket bind...")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3.0)

# IMPORTANT: Bind to receiving port, let OS choose
try:
    sock.bind(('', 0))
    print(f"Bound to local port {sock.getsockname()[1]}")
except Exception as e:
    print(f"Bind failed: {e}")

# GS4 Payload
msg = b'\xFE\xFD\x00\xE0\xEB\x2D\x0E'

try:
    print("Sending...")
    sock.sendto(msg, (TARGET_IP, TARGET_PORT))
    data, addr = sock.recvfrom(4096)
    print(f"SUCCESS! Received {len(data)} bytes from {addr}")
except Exception as e:
    print(f"FAILED: {e}")

sock.close()
