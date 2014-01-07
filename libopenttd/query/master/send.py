from libopenttd import packets
from libopenttd.packets import validators
from libopenttd.packets import constants
from libopenttd.packets import enums
from .base import QueryPacket

class MasterServerSendPacket(QueryPacket):
    class Meta:
        direction = packets.Direction.SEND
        abstract = True
Packet = MasterServerSendPacket 

class Register(Packet):
    pid = 4

class ServerList(Packet):
    pid = 6

class Unregister(Packet):
    pid = 8
