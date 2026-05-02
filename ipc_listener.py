import json
import os
import time
from multiprocessing.connection import Client

ADDRESS = r'\\.\pipe\carequeue_ipc' if os.name == 'nt' else ('localhost', 6077)


def main():
    print(f"[IPC LISTENER] Connecting to {ADDRESS}")
    while True:
        try:
            conn = Client(ADDRESS, authkey=b'carequeue@ipc')
            print("[IPC LISTENER] Connected. Waiting for events...\n")
            while True:
                raw = conn.recv()
                try:
                    payload = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    payload = raw
                print(f"[IPC EVENT] {json.dumps(payload, indent=2)}\n")
        except Exception as exc:
            print(f"[IPC LISTENER] Disconnected ({exc}). Reconnecting in 2s...")
            time.sleep(2)


if __name__ == "__main__":
    main()


