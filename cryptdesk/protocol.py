from __future__ import annotations

import json
import socket
import struct
from typing import Any

HEADER_STRUCT = struct.Struct("!II")
MAX_HEADER_BYTES = 64 * 1024
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024


class ProtocolError(RuntimeError):
    """Raised when a packet does not match the CryptDesk framing rules."""


def encode_packet(header: dict[str, Any], payload: bytes = b"") -> bytes:
    header_bytes = json.dumps(header, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(header_bytes) > MAX_HEADER_BYTES:
        raise ProtocolError("Header exceeds maximum size")
    if len(payload) > MAX_PAYLOAD_BYTES:
        raise ProtocolError("Payload exceeds maximum size")
    return HEADER_STRUCT.pack(len(header_bytes), len(payload)) + header_bytes + payload


def decode_packet(raw: bytes) -> tuple[dict[str, Any], bytes]:
    if len(raw) < HEADER_STRUCT.size:
        raise ProtocolError("Packet too short")
    header_size, payload_size = HEADER_STRUCT.unpack(raw[: HEADER_STRUCT.size])
    if header_size > MAX_HEADER_BYTES or payload_size > MAX_PAYLOAD_BYTES:
        raise ProtocolError("Packet exceeds protocol limits")
    start = HEADER_STRUCT.size
    header_end = start + header_size
    payload_end = header_end + payload_size
    if len(raw) != payload_end:
        raise ProtocolError("Packet length does not match framing metadata")
    header = json.loads(raw[start:header_end].decode("utf-8"))
    if not isinstance(header, dict):
        raise ProtocolError("Header must be a JSON object")
    return header, raw[header_end:payload_end]


def send_packet(sock: socket.socket, header: dict[str, Any], payload: bytes = b"") -> None:
    sock.sendall(encode_packet(header, payload))


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        try:
            chunk = sock.recv(size - len(chunks))
        except socket.timeout:
            continue
        if not chunk:
            raise EOFError("Socket closed")
        chunks.extend(chunk)
    return bytes(chunks)


def recv_packet(sock: socket.socket) -> tuple[dict[str, Any], bytes]:
    prefix = recv_exact(sock, HEADER_STRUCT.size)
    header_size, payload_size = HEADER_STRUCT.unpack(prefix)
    if header_size > MAX_HEADER_BYTES or payload_size > MAX_PAYLOAD_BYTES:
        raise ProtocolError("Incoming packet exceeds protocol limits")
    header_bytes = recv_exact(sock, header_size)
    payload = recv_exact(sock, payload_size)
    header = json.loads(header_bytes.decode("utf-8"))
    if not isinstance(header, dict):
        raise ProtocolError("Incoming header must be a JSON object")
    return header, payload
