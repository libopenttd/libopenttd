from .base import FieldBase, PacketBase
from libopenttd.utils import six

class PacketField(six.with_metaclass(PacketBase, FieldBase)):

    class Meta:
        force_virtual = True
