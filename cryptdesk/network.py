from __future__ import annotations

import socket
import threading
from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal

from cryptdesk.crypto import SessionCipher, derive_session, generate_identity
from cryptdesk.protocol import ProtocolError, decode_packet, encode_packet, recv_packet, send_packet

APP_NAME = "CryptDesk"
PROTOCOL_VERSION = 1


@dataclass(slots=True)
class ConnectionInfo:
    peer_name: str
    peer_address: str
    safety_code: str


class PeerConnection(QObject):
    status_changed = Signal(str)
    connected = Signal(object)
    disconnected = Signal(str)
    packet_received = Signal(object, object)
    error_occurred = Signal(str)

    def __init__(self, role: str, passphrase: str = "", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.role = role
        self.passphrase = passphrase
        self._state_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self._listener_socket: socket.socket | None = None
        self._socket: socket.socket | None = None
        self._session: SessionCipher | None = None
        self._connection_info: ConnectionInfo | None = None
        self._stop_event: threading.Event | None = None
        self._receiver_thread: threading.Thread | None = None
        self._worker_thread: threading.Thread | None = None

    @property
    def is_connected(self) -> bool:
        with self._state_lock:
            return self._socket is not None and self._session is not None

    def start_host(self, host: str = "0.0.0.0", port: int = 48555) -> None:
        self.close(silent=True)
        stop_event = threading.Event()
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            listener.bind((host, port))
            listener.listen(1)
            listener.settimeout(1.0)
        except OSError as exc:
            listener.close()
            self._emit_error(f"Unable to listen on {host}:{port}: {exc}")
            return
        with self._state_lock:
            self._listener_socket = listener
            self._stop_event = stop_event
        self.status_changed.emit(f"Listening on {host}:{port}")
        self._worker_thread = threading.Thread(
            target=self._accept_worker,
            args=(listener, stop_event),
            daemon=True,
            name="cryptdesk-host-worker",
        )
        self._worker_thread.start()

    def connect_to(self, host: str, port: int) -> None:
        self.close(silent=True)
        stop_event = threading.Event()
        with self._state_lock:
            self._stop_event = stop_event
        self.status_changed.emit(f"Connecting to {host}:{port}")
        self._worker_thread = threading.Thread(
            target=self._connect_worker,
            args=(host, port, stop_event),
            daemon=True,
            name="cryptdesk-viewer-worker",
        )
        self._worker_thread.start()

    def send_message(self, header: dict[str, Any], payload: bytes = b"") -> bool:
        with self._state_lock:
            sock = self._socket
            session = self._session
        if sock is None or session is None:
            return False
        try:
            self._send_secure(sock, session, header, payload)
        except Exception as exc:
            self._emit_error(f"Failed to send packet: {exc}")
            self._disconnect(f"Connection closed: {exc}")
            return False
        return True

    def close(self, reason: str = "Session closed", silent: bool = False) -> None:
        self._disconnect(reason, silent=silent)

    def _accept_worker(self, listener: socket.socket, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                try:
                    client_socket, client_address = listener.accept()
                    break
                except socket.timeout:
                    continue
            else:
                return
        except OSError as exc:
            if not stop_event.is_set():
                self._emit_error(f"Listener failed: {exc}")
            return
        finally:
            try:
                listener.close()
            except OSError:
                pass
            with self._state_lock:
                if self._listener_socket is listener:
                    self._listener_socket = None
        if stop_event.is_set():
            client_socket.close()
            return
        self._finish_connection(client_socket, client_address, stop_event)

    def _connect_worker(self, host: str, port: int, stop_event: threading.Event) -> None:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10.0)
        try:
            client_socket.connect((host, port))
        except OSError as exc:
            client_socket.close()
            if not stop_event.is_set():
                self._emit_error(f"Unable to connect to {host}:{port}: {exc}")
            return
        if stop_event.is_set():
            client_socket.close()
            return
        self._finish_connection(client_socket, (host, port), stop_event)

    def _finish_connection(self, client_socket: socket.socket, client_address: tuple[Any, ...], stop_event: threading.Event) -> None:
        try:
            client_socket.settimeout(10.0)
            session, info = self._perform_handshake(client_socket, client_address)
            client_socket.settimeout(1.0)
        except Exception as exc:
            client_socket.close()
            if not stop_event.is_set():
                self._emit_error(f"Handshake failed: {exc}")
            return
        if stop_event.is_set():
            client_socket.close()
            return
        with self._state_lock:
            self._socket = client_socket
            self._session = session
            self._connection_info = info
        self.status_changed.emit(f"Connected to {info.peer_name} at {info.peer_address}")
        self.connected.emit(info)
        self._receiver_thread = threading.Thread(
            target=self._receive_worker,
            args=(client_socket, session, stop_event),
            daemon=True,
            name="cryptdesk-receiver",
        )
        self._receiver_thread.start()

    def _perform_handshake(self, sock: socket.socket, client_address: tuple[Any, ...]) -> tuple[SessionCipher, ConnectionInfo]:
        identity = generate_identity()
        local_name = socket.gethostname()
        send_packet(
            sock,
            {
                "type": "hello",
                "app": APP_NAME,
                "version": PROTOCOL_VERSION,
                "role": self.role,
                "name": local_name,
                "public_key": identity.public_key_b64,
            },
        )
        peer_hello, _ = recv_packet(sock)
        if peer_hello.get("type") != "hello":
            raise ProtocolError("Expected hello packet")
        if peer_hello.get("app") != APP_NAME:
            raise ProtocolError("Peer is not speaking the CryptDesk protocol")
        if peer_hello.get("version") != PROTOCOL_VERSION:
            raise ProtocolError("Unsupported protocol version")
        peer_public_key = peer_hello.get("public_key")
        if not isinstance(peer_public_key, str):
            raise ProtocolError("Peer hello did not include a valid public key")
        session = derive_session(identity.private_key, peer_public_key, self.role, self.passphrase)
        self._send_secure(sock, session, {"type": "session_ready", "name": local_name})
        ready_header, _ = self._recv_secure(sock, session)
        if ready_header.get("type") != "session_ready":
            raise ProtocolError("Expected session_ready packet")
        peer_host, peer_port = client_address[0], client_address[1]
        peer_name = str(ready_header.get("name") or peer_hello.get("name") or peer_hello.get("role") or "peer")
        return session, ConnectionInfo(
            peer_name=peer_name,
            peer_address=f"{peer_host}:{peer_port}",
            safety_code=session.safety_code,
        )

    def _receive_worker(self, sock: socket.socket, session: SessionCipher, stop_event: threading.Event) -> None:
        try:
            while not stop_event.is_set():
                header, payload = self._recv_secure(sock, session)
                self.packet_received.emit(header, payload)
        except EOFError:
            if not stop_event.is_set():
                self._disconnect("Peer disconnected")
        except (OSError, ProtocolError, ValueError) as exc:
            if not stop_event.is_set():
                self._emit_error(f"Connection error: {exc}")
                self._disconnect(f"Connection closed: {exc}")

    def _send_secure(self, sock: socket.socket, session: SessionCipher, header: dict[str, Any], payload: bytes = b"") -> None:
        plaintext = encode_packet(header, payload)
        encrypted = session.encrypt(plaintext)
        with self._send_lock:
            send_packet(sock, {"type": "secure"}, encrypted)

    def _recv_secure(self, sock: socket.socket, session: SessionCipher) -> tuple[dict[str, Any], bytes]:
        outer_header, outer_payload = recv_packet(sock)
        if outer_header.get("type") != "secure":
            raise ProtocolError("Expected secure packet")
        plaintext = session.decrypt(outer_payload)
        return decode_packet(plaintext)

    def _disconnect(self, reason: str, silent: bool = False) -> None:
        with self._state_lock:
            stop_event = self._stop_event
            listener = self._listener_socket
            sock = self._socket
            had_connection = self._connection_info is not None
            self._stop_event = None
            self._listener_socket = None
            self._socket = None
            self._session = None
            self._connection_info = None
        if stop_event is not None:
            stop_event.set()
        for item in (listener, sock):
            if item is None:
                continue
            try:
                item.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                item.close()
            except OSError:
                pass
        if not silent:
            self.status_changed.emit(reason)
            if had_connection:
                self.disconnected.emit(reason)

    def _emit_error(self, message: str) -> None:
        self.status_changed.emit(message)
        self.error_occurred.emit(message)
