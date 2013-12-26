from .base import FieldBase
from libopenttd.utils import six

from struct import Struct

class Field(FieldBase):
    def __init__(self, ordering = -1, *args, **kwargs):
        super(Field, self).__init__(ordering = ordering, *args, **kwargs)
        self.neighbours = []

    def can_merge(self, other):
        return False

    def merge(self, other):
        self.neighbours.append(other)

    def from_python(self, data):
        raise NotImplementedError()

    def to_python(self, data, index):
        raise NotImplementedError()

    def _prepare(self):
        pass

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

    _structCache = {}

    @classmethod
    def get_struct(cls, fmt):
        item = StructField._structCache.get(fmt, None)
        if item is None:
            item = StructField._structCache[fmt] = StructField._build_struct(fmt)
        return item

    @classmethod
    def _build_struct(cls, fmt):
        # We enforce the < prefix
        if fmt[0] in ['@', '=', '<', '>', '!']:
            fmt = fmt[1:]
        fmt = '<%s' % fmt
        return Struct(fmt)

    def __init__(self, *args, **kwargs):
        super(StructField, self).__init__(*args, **kwargs)
        self.struct = None

    def can_merge(self, other):
        return isinstance(other, StructField)

    def _prepare(self):
        fmt = self.struct_type
        for neigh in self.neighbours:
            fmt += neigh.struct_type
        self.struct = StructField.get_struct(fmt)

    def from_python(self, data):
        pass

    def to_python(self, data, index):
        pass
