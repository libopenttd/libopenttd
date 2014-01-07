from libopenttd import packets
from libopenttd.packets import validators
from libopenttd.packets import constants
from libopenttd.packets import enums
from .base import QueryPacket

class MasterServerRecvPacket(QueryPacket):
    class Meta:
        direction = packets.Direction.RECV
        abstract = True
Packet = MasterServerRecvPacket 

class Registered(Packet):
    pid = 5

class ServerList(Packet):
    pid = 7
    ip_type         = packets.IPAddrPrefixField(ordering=1)
    addresses       = packets.RepeatingField(ordering=2,
        count       = packets.UInt16Field(ordering=-1),
        fields      = {
            "ip"    : packets.IPAddrField(ordering=1),
            "port"  : packets.UInt16Field(ordering=2),
        })

class SessionKey(Packet):
    pid  = 11
    session_key     = packets.UInt64Field()
