from libopenttd import packets
from .base import AdminPacket

class AdminRecvPacket(AdminPacket):
    class Meta:
        direction = packets.Direction.RECV
        abstract = True
Packet = AdminRecvPacket

class Full(Packet):
    pid = 100

class Banned(Packet):
    pid = 101

class Error(Packet):
    pid = 102
    errorcode   = packets.UInt8Field(ordering=1)

class Protocol(Packet):
    pid = 103
    version     = packets.UInt8Field(ordering=1)
    settings    = packets.DictField(ordering=2, key=packets.UInt16Field(ordering=1),
                                    value=packets.UInt16Field(ordering=2),
                                    is_next=packets.BooleanField(ordering=3, is_next=True))

class Welcome(Packet):
    pid = 104
    name        = packets.StringField(ordering=1)
    version     = packets.StringField(ordering=2)
    dedicated   = packets.BooleanField(ordering=3)
    map_name    = packets.StringField(ordering=4)
    seed        = packets.UInt32Field(ordering=5)
    landscape   = packets.UInt8Field(ordering=6)
    startyear   = packets.UInt32Field(ordering=7)
    size_x      = packets.UInt16Field(ordering=8)
    size_y      = packets.UInt16Field(ordering=9)

class NewGame(Packet):
    pid = 105

class Shutdown(Packet):
    pid = 106

class Date(Packet):
    pid = 107
    date        = packets.DateField(ordering=1)

class ClientJoin(Packet):
    pid = 108
    client_id   = packets.UInt32Field(ordering=1)

class ClientInfo(Packet):
    pid = 109
    client_id   = packets.UInt32Field(ordering=1)
    hostname    = packets.StringField(ordering=2)
    name        = packets.StringField(ordering=3)
    language    = packets.UInt8Field(ordering=4)
    joindate    = packets.DateField(ordering=5)
    play_as     = packets.UInt8Field(ordering=6)

class ClientUpdate(Packet):
    pid = 110
    client_id   = packets.UInt32Field(ordering=1)
    name        = packets.StringField(ordering=2)
    play_as     = packets.UInt8Field(ordering=3)

class ClientQuit(Packet):
    pid = 111
    client_id   = packets.UInt32Field(ordering=1)

class ClientError(Packet):
    pid = 112
    client_id   = packets.UInt32Field(ordering=1)
    errorcode   = packets.UInt8Field(ordering=2)
