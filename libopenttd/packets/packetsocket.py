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
from collections import defaultdict

from libopenttd.utils import six
from libopenttd.utils.six.moves import queue

class OpenTTDPacket(Packet):
    pid = -1
    length              = fields.UInt16Field(ordering=1)
    packet_id           = fields.UInt8Field(ordering=2)
    class Meta:
        protocol = Protocol.NONE
        direction = Direction.BOTH

class SocketBuffer(object):
    def __init__(self,  write_buffer_size, inactivity_time = 60.0):
        self._write_size = write_buffer_size
        self._inactivity_time = inactivity_time
        self.lock = Lock()

        self.read_buf = bytearray()
        self.write_buf = queue.Queue(self._write_size)

        self.mem_buf = None
        self.mem_buf_idx = 0
        self.mem_buf_size = 0
        self.last_activity = time.time()

    def reset(self):
        self.read_buf = bytearray()
        self.write_buf = queue.Queue(self._write_size)

        self.mem_buf = None
        self.mem_buf_idx = 0
        self.mem_buf_size = 0
        self.last_activity = time.time()

    def queue_write(self, data, block = True, timeout = None):
        self.write_buf.put(data, block, timeout)
        self.last_activity = time.time()

    def dequeue_write(self, block = False, timeout = None):
        try:
            return self.write_buf.get(block, timeout)
        except queue.Empty:
            return None

    def dequeue_done(self):
        self.write_buf.task_done()

    @property
    def write_avail(self):
        return not self.write_buf.empty()

    @property
    def read_avail(self):
        if self.mem_buf:
            return self.mem_buf_size - self.mem_buf_idx
        return len(self.read_buf)

    def __enter__(self):
        with self.lock:
            self.mem_buf = memoryview(self.read_buf)
            self.mem_buf_idx = 0
            self.mem_buf_size = len(self.mem_buf)
            self.read_buf = bytearray()
        return self.mem_buf

    def mark_read(self, amt):
        self.mem_buf_idx += amt

    def extend(self, data):
        with self.lock:
            self.read_buf.extend(data)
            self.last_activity = time.time()

    @property
    def index(self):
        return self.mem_buf_idx
    @index.setter
    def index(self, value):
        self.mem_buf_idx = value

    @property
    def active(self):
        if self._inactivity_time == 0:
            return True
        return time.time() - self.last_activity <= self._inactivity_time 

    def __exit__(self, type, value, traceback):
        with self.lock:
            tmp_read_buf = bytearray(self.mem_buf[self.mem_buf_idx:])
            tmp_read_buf.extend(self.read_buf)
            self.read_buf = tmp_read_buf
            self.mem_buf = None
            self.mem_buf_size = 0
            self.mem_buf_idx = 0

class BufferedSocket(socket.socket):
    """
    BufferedSocket implement's python's socket class and wraps it in such a way
    that it uses socket's read_into function to fill a buffer.

    This allows for faster processing of buffer data, while doing packet processing
    on a different level.
    """

    READ_BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE / 2
    WRITE_BUFFER_QUEUE_SIZE = 64
    PACKET_BURST_SIZE = 10

    def __init__(self, *args, **kwargs):
        super(BufferedSocket, self).__init__(*args, **kwargs)
        self.buffer = SocketBuffer(self.WRITE_BUFFER_QUEUE_SIZE)
        self._connected = False
        self.read_lock = Lock()
        self.read_buf = bytearray(self.READ_BUFFER_SIZE)

    @property
    def connected(self):
        return self._connected

    def connect(self, *args, **kwargs):
        ret = None
        try:
            self.buffer.reset()
            ret = super(BufferedSocket, self).connect(*args, **kwargs)
        except:
            raise
        else:
            self._connected = True
        return ret

    def queue_write(self, data):
        self.buffer.queue_write(data)

    def write_buffer_flush(self):
        i = 0
        while self.buffer.write_avail:
            i += 1
            data = self.buffer.dequeue_write()
            if not data:
                break
            try:
                self.sendall(data)
            except: # pylint: disable=W0702
                self._connected = False
                # TODO : Handle errors.
            finally:
                self.buffer.dequeue_done()
            if i >= self.PACKET_BURST_SIZE and self.PACKET_BURST_SIZE != 0:
                break

    def read_buffer_fill(self):
        read = 0
        with self.read_lock:
            read = self.recv_into(self.read_buf)
            if read == 0:
                self._connected = False
                return 0
                # TODO : Handle 0-read.
            self.buffer.extend(self.read_buf[0:read])
        return read

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
        header_size = OpenTTDPacket.get_packet_size()
        if self.buffer.read_avail < header_size:
            return []
        packets = []
        with self.buffer as data:
            while self.buffer.read_avail >= header_size: # While enough data available for a header.
                info = OpenTTDPacket.manager.from_data(
                    data[self.buffer.index:self.buffer.index+header_size].tobytes()
                    )
                if self.buffer.read_avail < info.length:
                    # Not enough data in buffer to parse the full packet
                    break
                packet_data = data[self.buffer.index + header_size:self.buffer.index + info.length]
                self.buffer.index += info.length
                packet = self.packet_registry.get(info.packet_id)
                if not packet:
                    # We don't understand this packet.. maybe we should log this.
                    # TODO: Add Logging
                    continue
                try:
                    obj = packet.manager.from_data(packet_data.tobytes(), extra = self.extra_info)
                except: # pylint: disable=W0702
                    continue
                packets.append(obj)
        return packets

    def send_packet(self, packet, *args, **kwargs):
        if isinstance(packet, type):
            packet = packet(*args, **kwargs)

        data = packet.write(extra=self.extra_info)
        info = OpenTTDPacket(length = len(data) + OpenTTDPacket.get_packet_size(), packet_id = packet.pid)
        data = '%s%s' % (info.write(), data)
        self.queue_write(data)

class BufferedUDPSocket(BufferedSocket):
    PACKET_BURST_SIZE = 10

    def __init__(self, *args, **kwargs):
        super(BufferedUDPSocket, self).__init__(*args, **kwargs)
        self.buffer = defaultdict(lambda: SocketBuffer(self.WRITE_BUFFER_QUEUE_SIZE))

    def queue_write(self, to, data):
        self.buffer[to].queue_write(data)

    def write_buffer_flush(self):
        i = 0
        for addr, buf in six.iteritems(self.buffer):
            while buf.write_avail:
                i += 1
                data = buf.dequeue_write()
                if not data:
                    break
                try:
                    sent, length = 0, len(data)
                    while sent < length:
                        sent += self.sendto(data[sent:], addr)
                except: # pylint: disable=W0702
                    pass
                finally:
                    buf.dequeue_done()
                if i >= self.PACKET_BURST_SIZE and self.PACKET_BURST_SIZE != 0:
                    return

    def read_buffer_fill(self):
        with self.read_lock:
            read, addr = self.recvfrom_into(self.read_buf)
            if read == 0:
                return 0
                # TODO : Handle 0-read.
            self.buffer[addr].extend(self.read_buf[0:read])

class PacketUDPSocket(BufferedUDPSocket):
    DEFAULT_FAMILY      = socket.AF_INET
    DEFAULT_TYPE        = socket.SOCK_DGRAM

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
        super(PacketUDPSocket, self).__init__(family, _type)

        self.openttd_protocol = protocol
        self.openttd_direction = direction
        self.packet_registry = registry.get_packets_dict(protocol, direction)

        self.extra_info = ProtocolInformation(self.DEFAULT_VERSION)

    def process_recv(self):
        return self.read_buffer_fill()

    def process_recv_full(self):
        self.process_recv()
        return self.process_packets()

    def process_send(self):
        self.process_idle()
        return self.write_buffer_flush()

    def process_idle(self):
        remove = [addr for addr, buf in six.iteritems(self.buffer) if not buf.active]

        for addr in remove:
            del self.buffer[addr]

    def process_packets(self):
        self.process_idle()
        packets = []
        for addr, buf in six.iteritems(self.buffer):
            header_size = OpenTTDPacket.get_packet_size()
            if buf.read_avail < header_size:
                continue
            
            with buf as data:
                while buf.read_avail >= header_size: # While enough data available for a header.
                    info = OpenTTDPacket.manager.from_data(
                        data[buf.index:buf.index+header_size].tobytes()
                        )
                    if buf.read_avail < info.length:
                        # Not enough data in buffer to parse the full packet
                        break
                    packet_data = data[buf.index + header_size:buf.index + info.length]
                    buf.index += info.length
                    packet = self.packet_registry.get(info.packet_id)
                    if not packet:
                        # We don't understand this packet.. maybe we should log this.
                        # TODO: Add Logging
                        continue
                    try:
                        obj = packet.manager.from_data(packet_data.tobytes(), extra = self.extra_info)
                    except: # pylint: disable=W0702
                        continue
                    packets.append((addr, obj))
        return packets

    def send_packet(self, addr, packet, *args, **kwargs):
        if isinstance(packet, type):
            packet = packet(*args, **kwargs)

        data = packet.write(extra=self.extra_info)
        info = OpenTTDPacket(length = len(data) + OpenTTDPacket.get_packet_size(), packet_id = packet.pid)
        data = '%s%s' % (info.write(), data)
        self.queue_write(addr, data)
