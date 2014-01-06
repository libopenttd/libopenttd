from libopenttd import packets
from libopenttd.packets import validators
from libopenttd.packets import constants
from libopenttd.packets import enums
from .base import AdminPacket

class AdminSendPacket(AdminPacket):
    class Meta:
        direction = packets.Direction.SEND
        abstract = True
Packet = AdminSendPacket 

class Join(Packet):
    pid         = 0

    password    = packets.StringField(ordering=1, validators=[
        validators.MaxLength(constants.NETWORK_PASSWORD_LENGTH)
        ])
    name        = packets.StringField(ordering=2, trim_length = constants.NETWORK_CLIENT_NAME_LENGTH)
    version     = packets.StringField(ordering=3, trim_length = constants.NETWORK_REVISION_LENGTH)

class Quit(Packet):
    pid         = 1

class UpdateFrequency(Packet):
    pid         = 2
    update_type = packets.UInt16Field(ordering=1, validators=[enums.UpdateType.is_valid])
    update_freq = packets.UInt16Field(ordering=2, validators=[enums.UpdateFrequency.is_valid])

class Poll(Packet):
    pid         = 3
    poll_type   = packets.UInt8Field(ordering=1, validators=[enums.UpdateType.is_valid])
    poll_extra  = packets.UInt32Field(ordering=2)

class Chat(Packet):
    pid         = 4
    action      = packets.UInt8Field(ordering=1, validators=[enums.Action.is_valid_admin_chat])
    dest_type   = packets.UInt8Field(ordering=2, validators=[enums.DestType.is_valid])
    client_id   = packets.UInt32Field(ordering=3)
    message     = packets.StringField(ordering=4, validators=[
        validators.MaxLength(constants.NETWORK_CHAT_LENGTH)
        ])

class Rcon(Packet):
    pid         = 5
    command     = packets.StringField(ordering=1, validators=[
        validators.MaxLength(constants.NETWORK_RCONCOMMAND_LENGTH)
        ])

class Gamescript(Packet):
    pid         = 6
    data        = packets.JsonField(ordering=1)

class Ping(Packet):
    pid         = 7
    payload     = packets.UInt32Field(ordering=1)
