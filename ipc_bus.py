import json
import os
import threading
import time
from datetime import datetime
from multiprocessing.connection import Listener


def _ipc_address():
    if os.name == 'nt':
        return r'\\.\pipe\carequeue_ipc'
    return ('localhost', 6077)


class NotificationIPCServer:
    """
    Lightweight named-pipe / socket based publisher so auxiliary tools (CLI dashboards,
    monitoring scripts, etc.) can tap into real-time hospital events.
    """

    def __init__(self):
        self.address = _ipc_address()
        self.authkey = b'carequeue@ipc'
        self.listener = None
        self.thread = None
        self.subscribers = set()
        self._gate = threading.RLock()

    def start(self):
        with self._gate:
            if self.listener:
                return
            try:
                self.listener = Listener(self.address, authkey=self.authkey)
            except OSError as exc:
                print(f"[IPC ⚠] Unable to start listener ({exc}). Retrying in background...")
                threading.Thread(target=self._retry_start, daemon=True).start()
                return
            self.thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.thread.start()
            print(f"[IPC ⚡] Listening for subscribers on {self.address}")

    def _retry_start(self):
        while not self.listener:
            time.sleep(2)
            try:
                with self._gate:
                    if self.listener:
                        break
                    self.listener = Listener(self.address, authkey=self.authkey)
                    self.thread = threading.Thread(target=self._accept_loop, daemon=True)
                    self.thread.start()
                    print(f"[IPC ⚡] Listener recovered on {self.address}")
            except OSError:
                continue

    def _accept_loop(self):
        while True:
            try:
                conn = self.listener.accept()
            except (OSError, EOFError):
                break
            print(f"[IPC 👥] Subscriber connected")
            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn):
        with self._gate:
            self.subscribers.add(conn)
        try:
            while True:
                try:
                    ping = conn.recv()
                    if ping == "__ping__":
                        conn.send({"status": "ok"})
                except EOFError:
                    break
        finally:
            with self._gate:
                self.subscribers.discard(conn)
            conn.close()
            print("[IPC 👋] Subscriber disconnected")

    def broadcast(self, payload):
        self.start()
        serialized = json.dumps(payload)
        dead = []
        with self._gate:
            for conn in list(self.subscribers):
                try:
                    conn.send(serialized)
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self.subscribers.discard(conn)
        if self.subscribers:
            print(f"[IPC 📣] Broadcast to {len(self.subscribers)} subscriber(s)")


notification_ipc = NotificationIPCServer()


def publish_ipc_event(channel, data):
    """
    Publish a structured event (lab_report, billing_update, etc.) over the named pipe.
    External tooling can subscribe via multiprocessing.connection.Client.
    """
    envelope = {
        "channel": channel,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "data": data
    }
    notification_ipc.broadcast(envelope)
    return envelope


__all__ = ["publish_ipc_event", "notification_ipc"]


