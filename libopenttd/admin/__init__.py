from libopenttd.packets import PacketSocket, enums
from .packets import send, recv

class AdminSocket(PacketSocket):
    DEFAULT_PROTOCOL = enums.Protocol.ADMIN
    DEFAULT_DIRECTION = enums.Direction.RECV
