from libopenttd.utils.enums import EnumHelper

class Direction(EnumHelper):
    is_flag             = True
    SEND                = 0x01
    RECV                = 0x02
    BOTH                = 0x03

class Protocol(EnumHelper):
    is_flag             = True
    ADMIN               = 0x01
    CLIENT              = 0x02
    MSU                 = 0x04

    NONE                = 0xFF
