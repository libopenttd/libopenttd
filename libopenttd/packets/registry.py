from collections import defaultdict
from libopenttd.utils import lru_cache

from .enums import Protocol, Direction

import warnings

class PacketRegistry(object):
    def __init__(self):
        # Mapping of ProtocolType => Direction => PacketID => Packet classes.
        # This way we have quick and easy access to the right packets.
        self.all_packets = defaultdict(lambda: defaultdict(dict))

    def register_packet(self, packet):
        directions = [packet._meta.direction]
        if packet._meta.direction & Direction.BOTH == Direction.BOTH:
            directions = [Direction.SEND, Direction.RECV, Direction.BOTH]
        for direction in directions:
            if packet.pid in self.all_packets[packet._meta.protocol][direction] and not packet._meta.override:
                # We don't re-register packets for a specific PID
                existing = self.all_packets[packet._meta.protocol][direction][packet.pid]
                if existing == packet:
                    continue
                warnings.warn("Packet class '%s' collides with class '%s' for the direction '%s' and protocol '%s'. "
                                "as a result, this packet will not register." % (packet._meta.name,
                                existing._meta.name, Direction.get_name(direction), 
                                Protocol.get_name(packet._meta.protocol)))
                continue
            self.all_packets[packet._meta.protocol][direction][packet.pid] = packet

    def get_packets_dict(self, protocol, direction, only_both = False):
        packets = {}
        if direction & Direction.BOTH == Direction.BOTH:
            if only_both:
                directions = [Direction.BOTH]
            else:
                directions = [Direction.SEND, Direction.RECV]
        else:
            directions = [direction]
        for direction in directions:
            packets.update(dict(self.all_packets[protocol][direction].items()))
        return packets

    def get_packets(self, protocol, direction, only_both = False):
        return self.get_packets_dict(protocol, direction, only_both).values()

    def get_registered_packet(self, packet):
        return self.get_packet(packet._meta.protocol, packet._meta.direction, packet.pid)

    def get_packet(self, protocol, direction, pid):
        return self.all_packets[protocol][direction].get(pid)

registry = PacketRegistry() #pylint: disable=C0103
