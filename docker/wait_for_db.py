"""Block until the configured PostgreSQL TCP port accepts connections."""
import os
import socket
import sys
import time

host = os.environ.get("POSTGRES_HOST", "db")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
deadline = time.time() + 60

while time.time() < deadline:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
        sock.close()
        print(f"[wait_for_db] {host}:{port} is accepting connections.")
        sys.exit(0)
    except OSError:
        time.sleep(1)
    finally:
        sock.close()

print(f"[wait_for_db] Timed out waiting for {host}:{port}", file=sys.stderr)
sys.exit(1)
