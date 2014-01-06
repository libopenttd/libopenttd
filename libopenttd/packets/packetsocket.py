import io
import socket
import time

from .constants import SEND_MTU
from .packet import Packet
from .base import ProtocolInformation
import fields
from .enums import Protocol, Direction
from .registry import registry

from threading import Lock

from libopenttd.utils.six.moves import queue

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

    READ_BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE / 2
    WRITE_BUFFER_QUEUE_SIZE = 64

    def __init__(self, *args, **kwargs):
        super(BufferedSocket, self).__init__(*args, **kwargs)
        self.prim_read_buf = bytearray()
        self.sec_read_buf = bytearray(self.READ_BUFFER_SIZE)

        self.prim_write_buf = queue.Queue(self.WRITE_BUFFER_QUEUE_SIZE)

        self.mem_buf  = None
        self.mem_buf_idx = 0
        self.mem_buf_size = 0

        self._connected = False

        self.read_buf_lock = Lock()

    @property
    def connected(self):
        return self._connected

    def connect(self, *args, **kwargs):
        ret = None
        try:
            self.mem_buf = None
            self.prim_read_buf = bytearray()
            self.sec_read_buf = bytearray(self.READ_BUFFER_SIZE)
            self.prim_write_buf = queue.Queue(self.WRITE_BUFFER_QUEUE_SIZE)
            ret = super(BufferedSocket, self).connect(*args, **kwargs)
        except:
            raise
        else:
            self._connected = True
        return ret

    def queue_write(self, data):
        self.prim_write_buf.put(data, True)

    def write_buffer_flush(self):
        if not self.prim_write_buf.empty():
            try:
                data = self.prim_write_buf.get(False)
            except queue.Empty:
                return
            try:
                self.sendall(data)
            except:
                self._connected = False
                # TODO : Handle errors.
            finally:
                self.prim_write_buf.task_done()

    def read_buffer_fill(self):
        with self.read_buf_lock:
            read = self.recv_into(self.sec_read_buf)
            if read == 0:
                self._connected = False
                # TODO : Handle 0-read.
            self.prim_read_buf.extend(self.sec_read_buf[0:read])
        return read

    def _buffer_data_avail(self):
        return len(self.prim_read_buf)

    def _start_memory_buffer(self):
        """
        Prepares the current buffer for reading.
        This action also prevents the buffer from being written to,
        so we create a new write-buffer to write to.
        """
        with self.read_buf_lock:
            self.mem_buf = memoryview(self.prim_read_buf)
            self.mem_buf_size = len(self.mem_buf)
            self.mem_buf_idx = 0
            self.prim_read_buf = bytearray()

    def _end_memory_buffer(self):
        """
        Indicates we are done reading the memory buffer.
        This restores the write buffer with the remaining data from
        the memory buffer before any other data that might have been
        written to it.
        """
        if self.mem_buf is None:
            return
        with self.read_buf_lock:
            new_buffer = bytearray(self.mem_buf[self.mem_buf_idx:])
            new_buffer.extend(self.prim_read_buf)
            self.prim_read_buf = new_buffer
            self.mem_buf = None
            self.mem_buf_size = 0
            self.mem_buf_idx = 0

class PacketSocket(BufferedSocket):
    DEFAULT_FAMILY      = socket.AF_INET
    DEFAULT_TYPE        = socket.SOCK_STREAM

    DEFAULT_PROTOCOL    = Protocol.NONE
    DEFAULT_DIRECTION   = Direction.BOTH
    DEFAULT_PORT        = -1
    DEFAULT_VERSION     = 0

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

        self.extra_info = ProtocolInformation(self.DEFAULT_VERSION)

    def connect(self, ip, port = None): # pylint: disable=W0221
        if not (isinstance(ip, tuple) and len(ip) == 2):
            if port is None:
                port = self.DEFAULT_PORT
            ip = (ip, port)
        return super(PacketSocket, self).connect(ip)

    def process_recv(self):
        return self.read_buffer_fill()

    def process_recv_full(self):
        self.process_recv()
        return self.process_packets()

    def process_send(self):
        return self.write_buffer_flush()

    def process_packets(self):
        try:
            header_size = OpenTTDPacket.get_packet_size()
            if self._buffer_data_avail() < header_size:
                return
            self._start_memory_buffer()            

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
                    obj = packet.manager.from_data(packet_data.tobytes(), extra=self.extra_info)
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

        data = packet.write(extra=self.extra_info)
        info = OpenTTDPacket(length = len(data) + OpenTTDPacket.get_packet_size(), packet_id = packet.pid)
        data = '%s%s' % (info.write(), data)
        self.queue_write(data)
