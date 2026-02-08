import socket
import sys
import time

TARGET_IP = "91.202.25.110" # Known online
PORT = 5121

print(f"Probing {TARGET_IP}:{PORT}...")

PAYLOADS = [
    ("GS4", b'\xFE\xFD\x00\x01\x02\x03\x04'),
    ("GS2 Basic", b'\x5C\x62\x61\x73\x69\x63\x5C'), # \basic\
    ("GS2 Status", b'\x5C\x73\x74\x61\x74\x75\x73\x5C'), # \status\
    ("Info", b'\xFF\xFF\xFF\xFF\x69\x6E\x66\x6F'), # Source/A2S_INFO
    ("GetInfo", b'\xFF\xFF\xFF\xFF\x67\x65\x74\x69\x6E\x66\x6F'),
    ("XQuery", b'\x80\x00\x00\x00\x00'),
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3.0)

for name, payload in PAYLOADS:
    print(f"Testing {name}...")
    try:
        sock.sendto(payload, (TARGET_IP, PORT))
        data, addr = sock.recvfrom(2048)
        print(f"  [SUCCESS] {len(data)} bytes")
    except socket.timeout:
        print("  [TIMEOUT]")
    except Exception as e:
        print(f"  [ERROR] {e}")

sock.close()
