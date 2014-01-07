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
    welcome_message = packets.StringField(default = constants.NETWORK_MASTER_SERVER_WELCOME_MESSAGE)
    version         = packets.UInt8Field(default = constants.NETWORK_MASTER_SERVER_VERSION, 
                        is_version_identifier = True)
    server_port     = packets.UInt16Field(default = constants.NETWORK_DEFAULT_PORT)
    session_key     = packets.UInt64Field()

class ServerList(Packet):
    pid = 6
    version         = packets.UInt8Field(default = constants.NETWORK_MASTER_SERVER_VERSION, 
                        is_version_identifier = True)
    server_types    = packets.UInt8Field(default = enums.ServerListType.AUTODETECT)

class Unregister(Packet):
    pid = 8
    version         = packets.UInt8Field(default = constants.NETWORK_MASTER_SERVER_VERSION, 
                        is_version_identifier = True)
    server_port     = packets.UInt16Field(default = constants.NETWORK_DEFAULT_PORT)
