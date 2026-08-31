"""
Implementación ligera de WebSockets (RFC 6455) en Python estándar utilizando asyncio.
Zero-dependencies: No requiere 'websockets', 'aiohttp' ni librerías C externas.
Funciona 100% en Termux y cualquier entorno Python 3.8+.
"""

import asyncio
import base64
import hashlib
import json
import struct
from typing import Optional, Tuple, Dict, Any, Union

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA


class WebSocketError(Exception):
    pass


class WebSocketConnection:
    """Manejador de conexión WebSocket bidireccional sobre asyncio StreamReader/StreamWriter."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, is_client: bool = False):
        self.reader = reader
        self.writer = writer
        self.is_client = is_client
        self.closed = False
        self._lock = asyncio.Lock()

    @staticmethod
    def compute_accept_key(sec_key: str) -> str:
        sha1 = hashlib.sha1((sec_key.strip() + WS_GUID).encode("utf-8")).digest()
        return base64.b64encode(sha1).decode("utf-8")

    @classmethod
    async def server_handshake(
        cls, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, headers: Dict[str, str]
    ) -> Optional["WebSocketConnection"]:
        """Completa el handshake de WebSocket en el lado del servidor."""
        sec_key = headers.get("sec-websocket-key")
        if not sec_key:
            return None

        accept_key = cls.compute_accept_key(sec_key)
        response_headers = [
            "HTTP/1.1 101 Switching Protocols\r\n",
            "Upgrade: websocket\r\n",
            "Connection: Upgrade\r\n",
            f"Sec-WebSocket-Accept: {accept_key}\r\n",
            "\r\n",
        ]
        writer.write("".join(response_headers).encode("utf-8"))
        await writer.drain()
        return cls(reader, writer, is_client=False)

    @classmethod
    async def client_connect(
        cls, host: str, port: int, path: str = "/", ssl_context=None, extra_headers: Optional[Dict[str, str]] = None
    ) -> "WebSocketConnection":
        """Conecta como cliente WebSocket a un servidor remoto."""
        reader, writer = await asyncio.open_connection(host, port, ssl=ssl_context)
        raw_nonce = struct.pack("!IIII", 12345, 67890, 54321, 98760)
        sec_key = base64.b64encode(raw_nonce).decode("utf-8")

        headers = [
            f"GET {path} HTTP/1.1\r\n",
            f"Host: {host}:{port}\r\n",
            "Upgrade: websocket\r\n",
            "Connection: Upgrade\r\n",
            f"Sec-WebSocket-Key: {sec_key}\r\n",
            "Sec-WebSocket-Version: 13\r\n",
        ]
        if extra_headers:
            for k, v in extra_headers.items():
                headers.append(f"{k}: {v}\r\n")
        headers.append("\r\n")

        writer.write("".join(headers).encode("utf-8"))
        await writer.drain()

        # Leer respuesta HTTP 101
        status_line = await reader.readline()
        if not status_line or b"101" not in status_line:
            writer.close()
            raise WebSocketError(f"Handshake fallido: {status_line.decode('utf-8', errors='ignore')}")

        # Consumir cabeceras hasta \r\n
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break

        return cls(reader, writer, is_client=True)

    async def send_frame(self, opcode: int, payload: bytes):
        """Envía un frame WebSocket con máscara si es cliente, sin máscara si es servidor."""
        if self.closed:
            return

        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))

        length = len(payload)
        mask_bit = 0x80 if self.is_client else 0x00

        if length <= 125:
            header.append(mask_bit | length)
        elif length <= 65535:
            header.append(mask_bit | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(mask_bit | 127)
            header.extend(struct.pack("!Q", length))

        if self.is_client:
            mask_key = b"\x12\x34\x56\x78"
            header.extend(mask_key)
            masked_payload = bytearray(payload)
            for i in range(len(masked_payload)):
                masked_payload[i] ^= mask_key[i % 4]
            frame = bytes(header) + bytes(masked_payload)
        else:
            frame = bytes(header) + payload

        async with self._lock:
            try:
                self.writer.write(frame)
                await self.writer.drain()
            except (ConnectionError, BrokenPipeError, asyncio.CancelledError):
                self.closed = True

    async def send_text(self, text: str):
        await self.send_frame(OPCODE_TEXT, text.encode("utf-8"))

    async def send_binary(self, data: bytes):
        await self.send_frame(OPCODE_BINARY, data)

    async def send_json(self, data: Any):
        await self.send_text(json.dumps(data))

    async def send_ping(self, payload: bytes = b""):
        await self.send_frame(OPCODE_PING, payload)

    async def send_pong(self, payload: bytes = b""):
        await self.send_frame(OPCODE_PONG, payload)

    async def recv_frame(self) -> Tuple[int, bytes]:
        """Recibe y decodifica un frame completo."""
        if self.closed:
            raise WebSocketError("Conexión cerrada")

        head = await self.reader.readexactly(2)
        fin = bool(head[0] & 0x80)
        opcode = head[0] & 0x0F
        masked = bool(head[1] & 0x80)
        length = head[1] & 0x7F

        if length == 126:
            data = await self.reader.readexactly(2)
            length = struct.unpack("!H", data)[0]
        elif length == 127:
            data = await self.reader.readexactly(8)
            length = struct.unpack("!Q", data)[0]

        mask_key = None
        if masked:
            mask_key = await self.reader.readexactly(4)

        payload = await self.reader.readexactly(length) if length > 0 else b""

        if masked and mask_key:
            unmasked = bytearray(payload)
            for i in range(len(unmasked)):
                unmasked[i] ^= mask_key[i % 4]
            payload = bytes(unmasked)

        if opcode == OPCODE_PING:
            await self.send_pong(payload)
            return await self.recv_frame()
        elif opcode == OPCODE_CLOSE:
            self.closed = True
            await self.send_frame(OPCODE_CLOSE, payload)
            return opcode, payload

        return opcode, payload

    async def recv_text(self) -> Optional[str]:
        """Recibe el siguiente mensaje de texto."""
        try:
            opcode, payload = await self.recv_frame()
            if opcode == OPCODE_CLOSE or self.closed:
                return None
            if opcode == OPCODE_TEXT:
                return payload.decode("utf-8", errors="replace")
            return None
        except (asyncio.IncompleteReadError, ConnectionError, WebSocketError):
            self.closed = True
            return None

    async def recv_json(self) -> Optional[Dict[str, Any]]:
        """Recibe el siguiente mensaje parseado como JSON."""
        text = await self.recv_text()
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    async def close(self):
        if not self.closed:
            self.closed = True
            try:
                await self.send_frame(OPCODE_CLOSE, b"")
            except Exception:
                pass
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
