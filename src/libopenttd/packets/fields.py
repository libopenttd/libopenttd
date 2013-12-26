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

    def from_python(self, value):
        raise NotImplementedError()

    def write_bytes(self, data):
        raise NotImplementedError()

    def to_python(self, value):
        raise NotImplementedError()

    def read_bytes(self, data, index):
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

    def from_python(self, value):
        return value

    def write_bytes(self, data):
        pass

    def to_python(self, value):
        return value

    def read_bytes(self, data, index):
        pass

class CharField(StructField):
    struct_type = 'c'

class BooleanField(StructField):
    struct_type = 'c'
    def to_python(self, value):
        return bool(value)

    def from_python(self, value):
        return 1 if value else 0

class UByteField(StructField):
    struct_type = 'B'

ByteField = UInt8Field = UByteField

class SByteField(StructField):
    struct_type = 'b'

Int8Field = SByteField

class UShortField(StructField):
    struct_type = 'H'

UInt16Field = UShortField

class SShortField(StructField):
    struct_type = 'h'

Int16Field = SShortField

class UIntField(StructField):
    struct_type = 'I'

ULongField = UInt32Field = UIntField

class SIntField(StructField):
    struct_type = 'i'

LongField = Int32Field = SIntField

class ULongLongField(StructField):
    struct_type = 'Q'

UInt64Field = ULongLongField

class SLongLongField(StructField):
    struct_type = 'q'

Int64Field = SLongLongField
