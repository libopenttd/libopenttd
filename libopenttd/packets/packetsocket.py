import io
import socket

from .packet import Packet
import fields
from .enums import Protocol, Direction
from .registry import registry

from threading import Lock

class OpenTTDPacket(Packet):
    pid = -1
    length              = fields.UInt16Field(ordering=1)
    packet_id           = fields.UInt8Field(ordering=2)
    class Meta:
        protocol = Protocol.NONE
        direction = Direction.BOTH

class BufferedSocket(socket.socket):
    """
    BufferedSocket implement's python's socket class and wraps it in such a way
    that it uses socket's read_into function to fill a buffer.

    This allows for faster processing of buffer data, while doing packet processing
    on a different level.
    """

    BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE / 2

    def __init__(self, *args, **kwargs):
        super(BufferedSocket, self).__init__(*args, **kwargs)
        self.primary_buffer = bytearray()
        self.secondary_buffer = bytearray(self.BUFFER_SIZE)
        self.mem_buf  = None
        self.mem_buf_idx = 0
        self.mem_buf_size = 0
        self.buffer_lock = Lock()

    def buffer_fill(self):
        with self.buffer_lock:
            read = self.recv_into(self.secondary_buffer)
            if read == 0:
                pass # TODO : Handle 0-read.
            self.primary_buffer.extend(self.secondary_buffer[0:read])
        return read

    def _start_memory_buffer(self):
        """
        Prepares the current buffer for reading.
        This action also prevents the buffer from being written to,
        so we create a new write-buffer to write to.
        """
        with self.buffer_lock:
            self.mem_buf = memoryview(self.primary_buffer)
            self.mem_buf_size = len(self.mem_buf)
            self.mem_buf_idx = 0
            self.primary_buffer = bytearray()

    def _end_memory_buffer(self):
        """
        Indicates we are done reading the memory buffer.
        This restores the write buffer with the remaining data from
        the memory buffer before any other data that might have been
        written to it.
        """
        with self.buffer_lock:
            new_buffer = bytearray(self.mem_buf[self.mem_buf_idx:])
            new_buffer.extend(self.primary_buffer)
            self.primary_buffer = new_buffer
            self.mem_buf = None
            self.mem_buf_size = 0
            self.mem_buf_idx = 0

class PacketSocket(BufferedSocket):
    DEFAULT_FAMILY      = socket.AF_INET
    DEFAULT_TYPE        = socket.SOCK_STREAM

    DEFAULT_PROTOCOL    = Protocol.NONE
    DEFAULT_DIRECTION   = Direction.BOTH

    def __init__(self, family = None, _type = None, protocol = None, direction = None):
        if family is None:
            family = self.DEFAULT_FAMILY
        if _type is None:
            _type = self.DEFAULT_TYPE
        if protocol is None:
            protocol = self.DEFAULT_PROTOCOL
        if direction is None:
            direction = self.DEFAULT_DIRECTION
        super(PacketSocket, self).__init__(family, _type)

        self.openttd_protocol = protocol
        self.openttd_direction = direction
        self.packet_registry = registry.get_packets_dict(protocol, direction)

    def connect(self, ip, port = None):
        if not (isinstance(ip, tuple) and len(ip) == 2):
            ip = (ip, port)
        return super(PacketSocket, self).connect(ip)

    def process_recv(self):
        return self.buffer_fill()

    def process_recv_full(self):
        self.process_recv()
        return self.process_packets()

    def process_packets(self):
        try:
            self._start_memory_buffer()
            header_size = OpenTTDPacket.get_packet_size()

            while True:
                if self.mem_buf_size < self.mem_buf_idx + header_size:
                    # Not enough data in buffer to parse a header
                    break
                info = OpenTTDPacket.manager.from_data(
                        self.mem_buf[self.mem_buf_idx:self.mem_buf_idx+header_size].tobytes()
                        )
                if self.mem_buf_size < self.mem_buf_idx + info.length:
                    # Not enough data in buffer to parse the full packet
                    break
                packet_data = self.mem_buf[self.mem_buf_idx + header_size:self.mem_buf_idx + info.length]
                self.mem_buf_idx += info.length
                packet = self.packet_registry.get(info.packet_id)
                if not packet:
                    # We don't understand this packet.. maybe we should log this.
                    # TODO: Add Logging
                    continue
                try:
                    obj = packet.manager.from_data(packet_data.tobytes())
                except: # pylint: disable=W0702
                    # Something went wrong while parsing this packet.. maybe we should log this.
                    # TODO: Add Logging
                    continue
                yield obj
        finally:
            self._end_memory_buffer()

    def send_packet(self, packet, *args, **kwargs):
        if isinstance(packet, type):
            packet = packet(*args, **kwargs)

        data = packet.write()
        info = OpenTTDPacket(length = len(data) + OpenTTDPacket.get_packet_size(), packet_id = packet.pid)
        data = '%s%s' % (info.write(), data)
        self.sendall(data)
