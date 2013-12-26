from .base import FieldBase
from libopenttd.utils import six

class Field(FieldBase):
    def __init__(self, name = None, ordering = -1, *args, **kwargs):
        super(Field, self).__init__(name, ordering = -1, *args, **kwargs)
        self.neighbours = []

    def can_merge(self, other):
        return False

    def merge(self, other):
        self.neighbours.append(other)

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

class StructField(Field):
    struct_type = None

