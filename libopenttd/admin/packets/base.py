from libopenttd import packets

class AdminPacket(packets.Packet):
    class Meta:
        protocol = packets.Protocol.ADMIN
        abstract = True
        default_version = packets.constants.NETWORK_GAME_ADMIN_VERSION
