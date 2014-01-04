from libopenttd.packets import PacketSocket, enums, constants
from .packets import send, recv

class AdminSocket(PacketSocket):
    DEFAULT_PROTOCOL = enums.Protocol.ADMIN
    DEFAULT_DIRECTION = enums.Direction.RECV
    DEFAULT_PORT = constants.NETWORK_ADMIN_PORT
    DEFAULT_VERSION = constants.NETWORK_GAME_ADMIN_VERSION
