# File location: 5G_Emulator_API/core_network/transport.py
# Reusable 3GPP transport helpers for real protocol mode
# - GTP-U (UDP port 2152) for user plane (N3)
# - PFCP (UDP port 8805) for session management (N4)
# - SCTP/TCP (port 38412) for NGAP signaling (N2)
# - TUN/TAP interface for N6 data network connectivity

import asyncio
import struct
import socket
import logging
import os
import sys
import json
from typing import Optional, Dict, Callable, Tuple, Any

logger = logging.getLogger(__name__)

# ============================================================================
# GTP-U Protocol (3GPP TS 29.281) - UDP port 2152
# ============================================================================

GTPU_PORT = 2152
GTPU_VERSION = 1
GTPU_PT = 1        # Protocol Type: GTP
GTPU_GPDU = 0xFF   # G-PDU message type


def parse_gtpu(data: bytes) -> Tuple[int, bytes]:
    """
    Parse GTP-U header and extract TEID + inner IP payload.
    GTP-U header: flags(1) + type(1) + length(2) + TEID(4) = 8 bytes minimum
    Reference: TS 29.281 Section 5.1
    """
    if len(data) < 8:
        raise ValueError(f"GTP-U packet too short: {len(data)} bytes")
    flags, msg_type, length, teid = struct.unpack('!BBHI', data[:8])
    version = (flags >> 5) & 0x07
    if version != GTPU_VERSION:
        raise ValueError(f"Unsupported GTP-U version: {version}")
    payload = data[8:]
    return teid, payload


def build_gtpu(teid: int, payload: bytes) -> bytes:
    """
    Build GTP-U packet with header prepended to payload.
    Flags: version=1, PT=1, E=0, S=0, PN=0 -> 0x30
    Reference: TS 29.281 Section 5.1
    """
    flags = 0x30  # Version 1, PT=1
    msg_type = GTPU_GPDU
    length = len(payload)
    header = struct.pack('!BBHI', flags, msg_type, length, teid)
    return header + payload


class GtpuTransport:
    """
    Asyncio-based GTP-U transport over UDP.
    Binds to UDP port 2152 for user plane data forwarding.
    """

    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = GTPU_PORT):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.transport = None
        self.protocol = None
        self._packet_handler: Optional[Callable] = None
        self._stats = {
            'packets_rx': 0, 'packets_tx': 0,
            'bytes_rx': 0, 'bytes_tx': 0,
            'decap_errors': 0
        }

    async def start(self, packet_handler: Callable):
        """Start GTP-U UDP listener. packet_handler(teid, payload, addr) called per packet."""
        self._packet_handler = packet_handler
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: _GtpuProtocol(self),
            local_addr=(self.bind_addr, self.bind_port)
        )
        logger.info(f"GTP-U transport listening on {self.bind_addr}:{self.bind_port}")

    async def send_gpdu(self, teid: int, payload: bytes, dest_addr: Tuple[str, int]):
        """Send GTP-U G-PDU (encapsulated packet) to remote endpoint."""
        if not self.transport:
            logger.warning("GTP-U transport not started, cannot send")
            return
        packet = build_gtpu(teid, payload)
        self.transport.sendto(packet, dest_addr)
        self._stats['packets_tx'] += 1
        self._stats['bytes_tx'] += len(packet)

    async def stop(self):
        """Stop GTP-U transport."""
        if self.transport:
            self.transport.close()
            self.transport = None
            logger.info("GTP-U transport stopped")

    @property
    def stats(self) -> Dict:
        return dict(self._stats)


class _GtpuProtocol(asyncio.DatagramProtocol):
    """Internal asyncio protocol for GTP-U UDP socket."""

    def __init__(self, gtpu: GtpuTransport):
        self.gtpu = gtpu

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        self.gtpu._stats['packets_rx'] += 1
        self.gtpu._stats['bytes_rx'] += len(data)
        try:
            teid, payload = parse_gtpu(data)
            if self.gtpu._packet_handler:
                # Schedule handler as a task so it can be async
                asyncio.ensure_future(
                    self.gtpu._packet_handler(teid, payload, addr)
                )
        except ValueError as e:
            self.gtpu._stats['decap_errors'] += 1
            logger.warning(f"GTP-U decap error from {addr}: {e}")

    def error_received(self, exc):
        logger.error(f"GTP-U UDP error: {exc}")


# ============================================================================
# PFCP Protocol (3GPP TS 29.244) - UDP port 8805
# ============================================================================

PFCP_PORT = 8805
PFCP_VERSION = 1

# PFCP Message Types (subset for lab use)
PFCP_HEARTBEAT_REQUEST = 1
PFCP_HEARTBEAT_RESPONSE = 2
PFCP_ASSOCIATION_SETUP_REQUEST = 5
PFCP_ASSOCIATION_SETUP_RESPONSE = 6
PFCP_SESSION_ESTABLISHMENT_REQUEST = 50
PFCP_SESSION_ESTABLISHMENT_RESPONSE = 51
PFCP_SESSION_MODIFICATION_REQUEST = 52
PFCP_SESSION_MODIFICATION_RESPONSE = 53
PFCP_SESSION_DELETION_REQUEST = 54
PFCP_SESSION_DELETION_RESPONSE = 55


def parse_pfcp_header(data: bytes) -> Tuple[int, int, int, bytes]:
    """
    Parse PFCP message header.
    Returns: (msg_type, seid, seq_number, ie_data)
    Reference: TS 29.244 Section 7.2.2

    Header format (SEID present, S=1):
      version_flags(1) + msg_type(1) + length(2) + SEID(8) + seq(3) + spare(1) = 16 bytes
    Header format (SEID absent, S=0):
      version_flags(1) + msg_type(1) + length(2) + seq(3) + spare(1) = 8 bytes
    """
    if len(data) < 4:
        raise ValueError(f"PFCP packet too short: {len(data)} bytes")

    version_flags = data[0]
    version = (version_flags >> 5) & 0x07
    s_flag = (version_flags >> 0) & 0x01  # SEID flag

    msg_type = data[1]
    length = struct.unpack('!H', data[2:4])[0]

    if s_flag:
        # SEID present
        if len(data) < 16:
            raise ValueError(f"PFCP with SEID too short: {len(data)} bytes")
        seid = struct.unpack('!Q', data[4:12])[0]
        seq_bytes = data[12:15]
        seq_number = (seq_bytes[0] << 16) | (seq_bytes[1] << 8) | seq_bytes[2]
        ie_data = data[16:]
    else:
        # No SEID
        seid = 0
        seq_bytes = data[4:7]
        seq_number = (seq_bytes[0] << 16) | (seq_bytes[1] << 8) | seq_bytes[2]
        ie_data = data[8:]

    return msg_type, seid, seq_number, ie_data


def build_pfcp_header(msg_type: int, seid: int, seq_number: int,
                      ie_data: bytes = b'') -> bytes:
    """
    Build PFCP message with header.
    Reference: TS 29.244 Section 7.2.2
    """
    s_flag = 1 if seid > 0 else 0
    version_flags = (PFCP_VERSION << 5) | s_flag

    if s_flag:
        # With SEID: header is 16 bytes (flags+type+length+seid+seq+spare)
        total_length = 12 + len(ie_data)  # length field covers seid+seq+spare+ies
        header = struct.pack('!BBH', version_flags, msg_type, total_length)
        header += struct.pack('!Q', seid)
        header += bytes([(seq_number >> 16) & 0xFF,
                         (seq_number >> 8) & 0xFF,
                         seq_number & 0xFF, 0])
    else:
        # Without SEID: header is 8 bytes
        total_length = 4 + len(ie_data)
        header = struct.pack('!BBH', version_flags, msg_type, total_length)
        header += bytes([(seq_number >> 16) & 0xFF,
                         (seq_number >> 8) & 0xFF,
                         seq_number & 0xFF, 0])

    return header + ie_data


class PfcpTransport:
    """
    Asyncio-based PFCP transport over UDP.
    Used by SMF (client) and UPF (server) on the N4 interface.
    """

    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = PFCP_PORT):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.transport = None
        self.protocol = None
        self._message_handler: Optional[Callable] = None
        self._seq_counter = 0
        self._pending_responses: Dict[int, asyncio.Future] = {}
        self._stats = {
            'messages_rx': 0, 'messages_tx': 0,
            'heartbeats': 0, 'parse_errors': 0
        }

    async def start(self, message_handler: Callable):
        """
        Start PFCP UDP listener.
        message_handler(msg_type, seid, seq, ie_data, addr) called per message.
        """
        self._message_handler = message_handler
        loop = asyncio.get_running_loop()
        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: _PfcpProtocol(self),
            local_addr=(self.bind_addr, self.bind_port)
        )
        logger.info(f"PFCP transport listening on {self.bind_addr}:{self.bind_port}")

    def _next_seq(self) -> int:
        self._seq_counter = (self._seq_counter + 1) & 0xFFFFFF
        return self._seq_counter

    async def send_message(self, msg_type: int, seid: int, ie_data: bytes,
                           dest_addr: Tuple[str, int],
                           seq_number: Optional[int] = None) -> int:
        """Send PFCP message. Returns sequence number used."""
        if not self.transport:
            logger.warning("PFCP transport not started, cannot send")
            return 0
        if seq_number is None:
            seq_number = self._next_seq()
        packet = build_pfcp_header(msg_type, seid, seq_number, ie_data)
        self.transport.sendto(packet, dest_addr)
        self._stats['messages_tx'] += 1
        return seq_number

    async def stop(self):
        """Stop PFCP transport."""
        if self.transport:
            self.transport.close()
            self.transport = None
            logger.info("PFCP transport stopped")

    @property
    def stats(self) -> Dict:
        return dict(self._stats)


class _PfcpProtocol(asyncio.DatagramProtocol):
    """Internal asyncio protocol for PFCP UDP socket."""

    def __init__(self, pfcp: PfcpTransport):
        self.pfcp = pfcp

    def datagram_received(self, data: bytes, addr: Tuple[str, int]):
        self.pfcp._stats['messages_rx'] += 1
        try:
            msg_type, seid, seq, ie_data = parse_pfcp_header(data)
            if msg_type == PFCP_HEARTBEAT_REQUEST:
                self.pfcp._stats['heartbeats'] += 1
                # Auto-respond to heartbeats
                response = build_pfcp_header(PFCP_HEARTBEAT_RESPONSE, 0, seq)
                self.pfcp.transport.sendto(response, addr)
                self.pfcp._stats['messages_tx'] += 1
                return
            if self.pfcp._message_handler:
                asyncio.ensure_future(
                    self.pfcp._message_handler(msg_type, seid, seq, ie_data, addr)
                )
        except ValueError as e:
            self.pfcp._stats['parse_errors'] += 1
            logger.warning(f"PFCP parse error from {addr}: {e}")

    def error_received(self, exc):
        logger.error(f"PFCP UDP error: {exc}")


# ============================================================================
# NGAP Signaling Transport - SCTP/TCP (3GPP TS 38.412) - port 38412
# ============================================================================

NGAP_PORT = 38412
NGAP_PPID = 60  # NGAP Payload Protocol Identifier

# Simple length-prefixed framing for TCP fallback:
# [4 bytes: payload length][payload]
FRAME_HEADER_SIZE = 4


async def ngap_frame_write(writer: asyncio.StreamWriter, data: bytes):
    """Write a length-prefixed NGAP frame to a TCP stream."""
    header = struct.pack('!I', len(data))
    writer.write(header + data)
    await writer.drain()


async def ngap_frame_read(reader: asyncio.StreamReader) -> Optional[bytes]:
    """Read a length-prefixed NGAP frame from a TCP stream. Returns None on EOF."""
    header = await reader.readexactly(FRAME_HEADER_SIZE)
    if not header or len(header) < FRAME_HEADER_SIZE:
        return None
    length = struct.unpack('!I', header)[0]
    if length == 0 or length > 65535:
        return None
    data = await reader.readexactly(length)
    return data


class NgapServer:
    """
    NGAP signaling server (runs in AMF).
    Listens on TCP port 38412 (SCTP fallback) for gNB connections.
    Each connection is an NG association.
    """

    def __init__(self, bind_addr: str = '0.0.0.0', bind_port: int = NGAP_PORT):
        self.bind_addr = bind_addr
        self.bind_port = bind_port
        self.server = None
        self._message_handler: Optional[Callable] = None
        self._connections: Dict[str, Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self._stats = {
            'connections': 0, 'messages_rx': 0, 'messages_tx': 0
        }

    async def start(self, message_handler: Callable):
        """
        Start NGAP server.
        message_handler(data, peer_id, writer) called per message.
        """
        self._message_handler = message_handler
        self.server = await asyncio.start_server(
            self._handle_connection,
            self.bind_addr, self.bind_port
        )
        logger.info(f"NGAP server listening on {self.bind_addr}:{self.bind_port} (TCP fallback)")

    async def _handle_connection(self, reader: asyncio.StreamReader,
                                  writer: asyncio.StreamWriter):
        """Handle an incoming gNB connection (NG association)."""
        peer = writer.get_extra_info('peername')
        peer_id = f"{peer[0]}:{peer[1]}"
        self._connections[peer_id] = (reader, writer)
        self._stats['connections'] += 1
        logger.info(f"NGAP: gNB connected from {peer_id}")
        try:
            while True:
                data = await ngap_frame_read(reader)
                if data is None:
                    break
                self._stats['messages_rx'] += 1
                if self._message_handler:
                    await self._message_handler(data, peer_id, writer)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            self._connections.pop(peer_id, None)
            writer.close()
            logger.info(f"NGAP: gNB disconnected: {peer_id}")

    async def send_to_peer(self, peer_id: str, data: bytes):
        """Send NGAP message to a specific gNB."""
        conn = self._connections.get(peer_id)
        if conn:
            _, writer = conn
            await ngap_frame_write(writer, data)
            self._stats['messages_tx'] += 1
        else:
            logger.warning(f"NGAP: No connection to peer {peer_id}")

    async def broadcast(self, data: bytes):
        """Send NGAP message to all connected gNBs."""
        for peer_id in list(self._connections.keys()):
            await self.send_to_peer(peer_id, data)

    async def stop(self):
        """Stop NGAP server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            for peer_id, (_, writer) in self._connections.items():
                writer.close()
            self._connections.clear()
            logger.info("NGAP server stopped")

    @property
    def stats(self) -> Dict:
        return dict(self._stats)


class NgapClient:
    """
    NGAP signaling client (runs in gNB).
    Connects to AMF on TCP port 38412 for NG association.
    """

    def __init__(self):
        self.reader = None
        self.writer = None
        self.connected = False
        self._message_handler: Optional[Callable] = None
        self._recv_task = None
        self._stats = {'messages_rx': 0, 'messages_tx': 0}

    async def connect(self, amf_addr: str, amf_port: int = NGAP_PORT,
                      message_handler: Optional[Callable] = None) -> bool:
        """Connect to AMF NGAP server."""
        self._message_handler = message_handler
        try:
            self.reader, self.writer = await asyncio.open_connection(amf_addr, amf_port)
            self.connected = True
            logger.info(f"NGAP client connected to AMF at {amf_addr}:{amf_port}")
            # Start receiving messages in background
            self._recv_task = asyncio.create_task(self._recv_loop())
            return True
        except (ConnectionError, OSError) as e:
            logger.error(f"NGAP client failed to connect to AMF {amf_addr}:{amf_port}: {e}")
            self.connected = False
            return False

    async def _recv_loop(self):
        """Background task to receive NGAP messages from AMF."""
        try:
            while self.connected and self.reader:
                data = await ngap_frame_read(self.reader)
                if data is None:
                    break
                self._stats['messages_rx'] += 1
                if self._message_handler:
                    await self._message_handler(data)
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            self.connected = False
            logger.info("NGAP client: connection to AMF lost")

    async def send(self, data: bytes):
        """Send NGAP message to AMF."""
        if self.writer and self.connected:
            await ngap_frame_write(self.writer, data)
            self._stats['messages_tx'] += 1
        else:
            logger.warning("NGAP client: not connected, cannot send")

    async def close(self):
        """Close NGAP connection."""
        self.connected = False
        if self._recv_task:
            self._recv_task.cancel()
        if self.writer:
            self.writer.close()
        logger.info("NGAP client closed")

    @property
    def stats(self) -> Dict:
        return dict(self._stats)


# ============================================================================
# TUN Interface for N6 (UPF -> Data Network)
# ============================================================================

# Linux TUN/TAP constants
TUNSETIFF = 0x400454ca
IFF_TUN = 0x0001
IFF_NO_PI = 0x1000


class TunInterface:
    """
    TUN interface for forwarding decapsulated UE traffic to the data network (N6).
    Requires root/CAP_NET_ADMIN on Linux. On macOS, uses utun.
    Falls back gracefully if unavailable.
    """

    def __init__(self, name: str = 'ogstun'):
        self.name = name
        self.fd = None
        self.active = False
        self._read_task = None
        self._packet_handler: Optional[Callable] = None

    async def open(self, packet_handler: Optional[Callable] = None) -> bool:
        """
        Open TUN interface.
        packet_handler(packet_bytes) is called for each packet read from TUN (downlink from DN).
        Returns True if successful.
        """
        self._packet_handler = packet_handler

        if sys.platform == 'linux':
            return await self._open_linux()
        elif sys.platform == 'darwin':
            return await self._open_macos()
        else:
            logger.warning(f"TUN interface not supported on {sys.platform}, "
                           "running in simulation mode")
            return False

    async def _open_linux(self) -> bool:
        """Open TUN on Linux using /dev/net/tun."""
        try:
            import fcntl
            tun_fd = os.open('/dev/net/tun', os.O_RDWR)
            # Configure TUN interface
            ifr = struct.pack('16sH', self.name.encode(), IFF_TUN | IFF_NO_PI)
            fcntl.ioctl(tun_fd, TUNSETIFF, ifr)
            self.fd = tun_fd
            self.active = True
            logger.info(f"TUN interface '{self.name}' opened (fd={tun_fd})")

            # Start background read task
            if self._packet_handler:
                self._read_task = asyncio.create_task(self._read_loop())

            return True
        except PermissionError:
            logger.warning(f"TUN interface '{self.name}' requires root/CAP_NET_ADMIN, "
                           "running in simulation mode")
            return False
        except (OSError, ImportError) as e:
            logger.warning(f"TUN interface '{self.name}' unavailable: {e}, "
                           "running in simulation mode")
            return False

    async def _open_macos(self) -> bool:
        """Open TUN on macOS using utun."""
        try:
            # macOS uses utun devices via a system socket
            # For lab purposes, we log and simulate
            logger.info(f"TUN interface: macOS detected. utun devices require "
                        "special handling. Running in simulation mode. "
                        "Use 'sudo python' with Open5GS tun setup for real forwarding.")
            return False
        except Exception as e:
            logger.warning(f"TUN interface unavailable on macOS: {e}")
            return False

    async def _read_loop(self):
        """Read packets from TUN interface (downlink from data network)."""
        loop = asyncio.get_running_loop()
        while self.active and self.fd is not None:
            try:
                data = await loop.run_in_executor(None, lambda: os.read(self.fd, 65535))
                if data and self._packet_handler:
                    await self._packet_handler(data)
            except OSError:
                break

    async def write(self, packet: bytes) -> bool:
        """Write packet to TUN interface (uplink toward data network)."""
        if self.fd is not None and self.active:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, lambda: os.write(self.fd, packet))
                return True
            except OSError as e:
                logger.error(f"TUN write error: {e}")
                return False
        else:
            # Simulation mode - log the packet
            logger.debug(f"TUN(sim): would forward {len(packet)} byte packet to data network")
            return True

    async def close(self):
        """Close TUN interface."""
        self.active = False
        if self._read_task:
            self._read_task.cancel()
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
            logger.info(f"TUN interface '{self.name}' closed")


# ============================================================================
# Simplified NGAP message encoding for transport over SCTP/TCP
# ============================================================================

def encode_ngap_json(ngap_dict: dict) -> bytes:
    """Encode NGAP message dict as JSON bytes for transport."""
    return json.dumps(ngap_dict).encode('utf-8')


def decode_ngap_json(data: bytes) -> dict:
    """Decode NGAP message from JSON bytes."""
    return json.loads(data.decode('utf-8'))
