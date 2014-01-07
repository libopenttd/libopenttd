from libopenttd import packets
from ..base import QueryPacket

class MasterServerSocket(packets.PacketUDPSocket):
    DEFAULT_PROTOCOL    = packets.Protocol.QUERY
    DEFAULT_DIRECTION   = packets.Direction.RECV
    DEFAULT_PORT        = packets.constants.NETWORK_MASTER_SERVER_PORT
    DEFAULT_VERSION     = packets.constants.NETWORK_MASTER_SERVER_VERSION
