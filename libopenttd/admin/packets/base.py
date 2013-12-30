from libopenttd import packets

class AdminPacket(packets.Packet):
    class Meta:
        protocol = packets.Protocol.ADMIN
        abstract = True
