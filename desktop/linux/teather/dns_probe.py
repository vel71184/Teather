from __future__ import annotations

import ipaddress
import socket
import struct

from .constants import DNS_SENTINEL, VIRTUAL_DNS_POOL
from .errors import TeatherError


PROBE_NAME = "teather-readiness.invalid"
MAX_DNS_MESSAGE = 4096


def _query(identifier: int) -> bytes:
    labels = PROBE_NAME.split(".")
    question = b"".join(bytes((len(label),)) + label.encode("ascii") for label in labels) + b"\0"
    return struct.pack("!HHHHHH", identifier, 0x0100, 1, 0, 0, 0) + question + struct.pack("!HH", 1, 1)


def _skip_name(message: bytes, offset: int) -> int:
    while True:
        if offset >= len(message):
            raise ValueError("truncated DNS name")
        length = message[offset]
        if length & 0xC0 == 0xC0:
            if offset + 2 > len(message):
                raise ValueError("truncated DNS pointer")
            return offset + 2
        offset += 1
        if length == 0:
            return offset
        if length & 0xC0 or offset + length > len(message):
            raise ValueError("invalid DNS label")
        offset += length


def _answer_address(message: bytes, identifier: int) -> str:
    if len(message) < 12:
        raise ValueError("truncated DNS header")
    response_id, flags, questions, answers, _authority, _additional = struct.unpack("!HHHHHH", message[:12])
    if response_id != identifier or not flags & 0x8000 or flags & 0x000F or questions != 1 or answers < 1:
        raise ValueError("unexpected DNS response")
    offset = _skip_name(message, 12)
    if offset + 4 > len(message):
        raise ValueError("truncated DNS question")
    offset += 4
    for _index in range(answers):
        offset = _skip_name(message, offset)
        if offset + 10 > len(message):
            raise ValueError("truncated DNS answer")
        record_type, record_class, _ttl, length = struct.unpack("!HHIH", message[offset:offset + 10])
        offset += 10
        if offset + length > len(message):
            raise ValueError("truncated DNS record data")
        data = message[offset:offset + length]
        offset += length
        if record_type == 1 and record_class == 1 and length == 4:
            address = str(ipaddress.ip_address(data))
            if ipaddress.ip_address(address) in ipaddress.ip_network(VIRTUAL_DNS_POOL):
                return address
    raise ValueError("no virtual IPv4 answer")


def _recv_exact(connection: socket.socket, length: int) -> bytes:
    result = bytearray()
    while len(result) < length:
        part = connection.recv(length - len(result))
        if not part:
            raise OSError("unexpected DNS TCP EOF")
        result.extend(part)
    return bytes(result)


def probe_virtual_dns(timeout: float = 3.0) -> dict[str, str]:
    identifier = 0x5445
    query = _query(identifier)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.settimeout(timeout)
            udp.sendto(query, (DNS_SENTINEL, 53))
            udp_response, source = udp.recvfrom(MAX_DNS_MESSAGE)
            if source[0] != DNS_SENTINEL or source[1] != 53:
                raise ValueError("unexpected DNS UDP source")
        udp_address = _answer_address(udp_response, identifier)

        with socket.create_connection((DNS_SENTINEL, 53), timeout=timeout) as tcp:
            tcp.settimeout(timeout)
            tcp.sendall(struct.pack("!H", len(query)) + query)
            length = struct.unpack("!H", _recv_exact(tcp, 2))[0]
            if length == 0 or length > MAX_DNS_MESSAGE:
                raise ValueError("invalid DNS TCP response length")
            tcp_response = _recv_exact(tcp, length)
        tcp_address = _answer_address(tcp_response, identifier)
    except (OSError, ValueError, struct.error) as error:
        raise TeatherError("dns-readiness", f"Teather DNS readiness failed: {type(error).__name__}") from error
    return {"udp": udp_address, "tcp": tcp_address}
