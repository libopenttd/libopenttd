from libopenttd import packets
from libopenttd.packets import validators
from libopenttd.packets import constants
from libopenttd.packets import enums
from .base import QueryPacket

class QueryServerSendPacket(QueryPacket):
    class Meta:
        direction = packets.Direction.RECV
        abstract = True
Packet = QueryServerSendPacket 

class GameInformation(Packet):
    pid = 1
    version         = packets.UInt8Field(ordering=1, is_version_identifier = True)
    grfinfo         = packets.RepeatingField(ordering=2,
        count       = packets.UInt8Field(ordering=-1),
        fields      = {
            "id"    : packets.UInt32Field(ordering=1),
            "md5"   : packets.MD5Field(ordering=2),
        })
    game_date       = packets.DateField(ordering=3)
    start_date      = packets.DateField(ordering=4)

    companies_max   = packets.UInt8Field(ordering=5)
    companies_on    = packets.UInt8Field(ordering=6)
    spectators_max  = packets.UInt8Field(ordering=7)
    name            = packets.StringField(ordering=8, trim_length=constants.NETWORK_NAME_LENGTH)
    revision        = packets.StringField(ordering=9, trim_length=constants.NETWORK_REVISION_LENGTH)
    language        = packets.UInt8Field(ordering=10)
    passworded      = packets.BooleanField(ordering=11)
    clients_max     = packets.UInt8Field(ordering=12)
    clients_on      = packets.UInt8Field(ordering=13)
    spectators_on   = packets.UInt8Field(ordering=14)
    map_name        = packets.StringField(ordering=15)
    map_width       = packets.UInt16Field(ordering=16)
    map_height      = packets.UInt16Field(ordering=17)
    map_set         = packets.UInt8Field(ordering=18)
    dedicated       = packets.UInt8Field(ordering=19)

class DetailInformation(Packet):
    pid = 3
    company_info_version = packets.UInt8Field(ordering=1)
    companies       = packets.RepeatingField(ordering=2,
        count       = packets.UInt8Field(ordering=-1),
        fields      = {
            "index" : packets.UInt8Field(ordering=1),
            "name"  : packets.StringField(ordering=2),
            "inaugurated_year": packets.UInt32Field(ordering=3),
            "value" : packets.Int64Field(ordering=4),
            "money" : packets.Int64Field(ordering=5),
            "income": packets.Int64Field(ordering=6),
            "performance": packets.UInt16Field(ordering=7),
            "passworded": packets.BooleanField(ordering=8),
            "vehicles": packets.GroupedField(ordering=9, fields = {
                'train' : packets.UInt16Field(ordering=1),
                'lorry' : packets.UInt16Field(ordering=2),
                'bus'   : packets.UInt16Field(ordering=3),
                'plane' : packets.UInt16Field(ordering=4),
                'ship'  : packets.UInt16Field(ordering=5),
                }),
            "stations": packets.GroupedField(ordering=10, fields = {
                'train' : packets.UInt16Field(ordering=1),
                'lorry' : packets.UInt16Field(ordering=2),
                'bus'   : packets.UInt16Field(ordering=3),
                'plane' : packets.UInt16Field(ordering=4),
                'ship'  : packets.UInt16Field(ordering=5),
                }),
            "is_ai" : packets.BooleanField(ordering=11),
        })

class NewGRF(Packet):
    pid = 10
    newgrfs         = packets.RepeatingField(ordering=1,
        count       = packets.UInt8Field(ordering=-1),
        fields      = {
            "id"    : packets.UInt32Field(ordering=1),
            "md5"   : packets.MD5Field(ordering=2),
            "name"  : packets.StringField(ordering=3),
        })
