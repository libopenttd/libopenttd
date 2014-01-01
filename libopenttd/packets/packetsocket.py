import io
import socket

from .packet import Packet
import fields
from .enums import Protocol, Direction
from .registry import registry

class OpenTTDPacket(Packet):
    pid = -1
    length              = fields.UInt16Field(ordering=1)
    packet_id           = fields.UInt8Field(ordering=2)
    class Meta:
        protocol = Protocol.NONE
        direction = Direction.BOTH

class PacketSocket(socket.socket):
    DEFAULT_FAMILY      = socket.AF_INET
    DEFAULT_TYPE        = socket.SOCK_STREAM
    DEFAULT_BUFFER_SIZE = io.DEFAULT_BUFFER_SIZE / 2

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
        super(PacketSocket, self).__init__(family, _type, 0)

        self.recv_buffer = None
        self.read_buffer = bytearray()
        self.mbuf = None
        self.mbuf_size = 0

        self.openttd_protocol = protocol
        self.openttd_direction = direction
        self.packet_registry = registry.get_packets_dict(protocol, direction)

    def connect(self, ip, port = None):
        if not (isinstance(ip, tuple) and len(ip) == 2):
            ip = (ip, port)
        return super(PacketSocket, self).connect(ip)

    def buffered_read(self):
        self.recv_buffer = bytearray(self.DEFAULT_BUFFER_SIZE)
        read = self.recv_into(self.recv_buffer)
        if read:
            self.read_buffer.extend(self.recv_buffer[0:read])
        self.mbuf = memoryview(self.read_buffer)
        self.mbuf_size = len(self.mbuf)
        self.mbuf_index = 0
        return read

    def buffered_read_end(self):
        self.read_buffer = bytearray(self.mbuf[self.mbuf_index:])

    def recv_packet(self):
        is_packet_avail = False
        read = self.buffered_read()
        if read == 0:
            pass # TODO: Handle 0 bytes read.
        packet_size = OpenTTDPacket.get_packet_size()
        while True:
            if self.mbuf_size < self.mbuf_index + packet_size:
                break
            info = OpenTTDPacket.manager.from_data(self.mbuf[self.mbuf_index:self.mbuf_index+packet_size].tobytes())
            if self.mbuf_size < info.length + self.mbuf_index:
                break
            packet_data = self.mbuf[self.mbuf_index + packet_size:self.mbuf_index + info.length].tobytes()
            self.mbuf_index += info.length
            packet = self.packet_registry.get(info.packet_id)
            if not packet:
                continue # Ignore packets we don't understand.
            try:
                obj = packet.manager.from_data(packet_data)
            except:
                pass # TODO: Handle invalid packet data
            yield obj
        self.buffered_read_end()

    def send_packet(self, packet, *args, **kwargs):
        if isinstance(packet, type):
            packet = packet(*args, **kwargs)

        data = packet.write()
        info = OpenTTDPacket(length = len(data) + OpenTTDPacket.get_packet_size(), packet_id = packet.pid)
        data = '%s%s' % (info.write(), data)
        self.sendall(data)
