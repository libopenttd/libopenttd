from .base import PacketFieldBase
from libopenttd.utils import six

class Field(PacketFieldBase):
    def __repr__(self):
        try:
            utf = six.text_type(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            utf = '[Bad Unicode data]'
        return '<%s: %s>'  % (self.__class__.__name__, utf)

    def __str__(self):
        if six.PY2 and hasattr(self, '__unicode__'):
            return six.text_type(self).encode('utf-8')
        return '%s field' % self.name
