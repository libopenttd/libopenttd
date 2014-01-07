from libopenttd import packets

class QueryPacket(packets.Packet):
    class Meta:
        protocol        = packets.Protocol.QUERY
        abstract        = True

