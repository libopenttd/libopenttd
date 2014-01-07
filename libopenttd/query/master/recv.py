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

class Register(Packet):
    pid = 5

class ServerList(Packet):
    pid = 7

class SessionKey(Packet):
    pid  = 11
