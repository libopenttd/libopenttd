from libopenttd import packets

class AdminPacket(packets.Packet):
    class Meta:
        protocol        = packets.Protocol.ADMIN
        abstract        = True

class AdminSocket(packets.PacketSocket):
    DEFAULT_PROTOCOL    = packets.Protocol.ADMIN
    DEFAULT_DIRECTION   = packets.Direction.RECV
    DEFAULT_PORT        = packets.constants.NETWORK_ADMIN_PORT
    DEFAULT_VERSION     = packets.constants.NETWORK_GAME_ADMIN_VERSION
