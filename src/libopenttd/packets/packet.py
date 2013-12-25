from .base import PacketBase
from libopenttd.util import six

class Packet(six.with_metaclass(PacketBase)):
    pid = -1

    def __repr__(self):
        try:
            utf = six.text_type(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            utf = '[Bad Unicode data]'
        return '<%s (%d): %s>'  % (self.__class__.__name__, self.pid, utf)

    def __str__(self):
        if six.PY2 and hasattr(self, '__unicode__'):
            return six.text_type(self).encode('utf-8')
        return '%s packet' % self.__class__.__name__
