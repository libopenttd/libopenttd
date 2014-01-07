from libopenttd import packets
from ..base import QueryPacket

class ServerInfoSocket(packets.PacketUDPSocket):
    DEFAULT_PROTOCOL    = packets.Protocol.QUERY
    DEFAULT_DIRECTION   = packets.Direction.RECV
    DEFAULT_PORT        = packets.constants.NETWORK_DEFAULT_PORT
    DEFAULT_VERSION     = packets.constants.NETWORK_GAME_INFO_VERSION
