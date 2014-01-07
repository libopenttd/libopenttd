from libopenttd import packets
from libopenttd.packets import validators
from libopenttd.packets import constants
from libopenttd.packets import enums
from .base import QueryPacket

class QueryServerRecvPacket(QueryPacket):
    class Meta:
        direction = packets.Direction.SEND
        abstract = True
Packet = QueryServerRecvPacket 

class FindServer(Packet):
    pid = 0

ServerInformation = FindServer

class DetailInformation(Packet):
    pid = 2

class GetNewGRFList(Packet):
    pid = 9
    newgrfs         = packets.RepeatingField(ordering=1,
        count       = packets.UInt8Field(ordering=-1),
        fields      = {
            "id"    : packets.UInt32Field(ordering=1),
            "md5"   : packets.UInt8Field(ordering=2, count=16),
        })

NewGRF = GetNewGRFList
