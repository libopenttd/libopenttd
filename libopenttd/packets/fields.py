from .base import FieldBase
from .exceptions import InvalidReturnCount, InvalidFieldData
from libopenttd.utils import six

from struct import Struct

def between(value, minimum, maximum):
    return value >= minimum and value <= maximum

def _between(minimum, maximum):
    def _inner(self, value):
        return between(value, minimum, maximum)
    return _inner

class Field(FieldBase):
    default_value   = None
    validators      = None
    validate        = None
    def __init__(self, ordering = -1, validators = None, *args, **kwargs):
        super(Field, self).__init__(ordering = ordering, *args, **kwargs)
        self.neighbours = []
        if validators:
            if isinstance(validators, (list, tuple)):
                self.validators = list(validators)
            else:
                self.validators = [validators,]
        else:
            self.validators = []
        if callable(self.validate):
            self.validators.append(self.validate)

    def can_merge(self, other):
        return False

    def merge(self, other):
        self.neighbours.append(other)

    def from_python(self, value):
        raise NotImplementedError()

    def is_valid(self, value):
        if not all([validator(value) for validator in self.validators]):
            raise InvalidFieldData("The value '%r' for field '%s' is invalid" % (value, self.name))
        return True

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

class StringField(Field):
    def __init__(self, trim_length = None, *args, **kwargs):
        super(StringField, self).__init__(*args, **kwargs)
        self.trim_length = trim_length

    def can_merge(self, other):
        return isinstance(other, StringField)

    def from_python(self, value):
        if self.trim_length:
            value = value[:self.trim_length - 1] # allow for the \x00 
        value = six.binary_type(value + '\x00')
        if self.is_valid(value):
            return value

    def write_bytes(self, data):
        values = ''
        for field in [self,] + self.neighbours:
            value = data.get(field.name)
            values += field.from_python(value)
        return values

    def to_python(self, value):
        return six.text_type(value.rstrip('\x00'))

    def read_bytes(self, data, index):
        start = index
        values = {}
        for field in [self,] + self.neighbours:
            end = data.find('\x00', index)
            values[field.name] = field.to_python(data[index:end])
            index = end+1
        return values, index - start

class StructField(Field):
    struct_type = None
    field_count = 1

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
        self.length = 0

    def can_merge(self, other):
        return isinstance(other, StructField)

    def _prepare(self):
        fmt = self.struct_type
        amt = self.field_count
        for neigh in self.neighbours:
            fmt += neigh.struct_type
            amt += neigh.field_count
        self.struct = StructField.get_struct(fmt)
        self.length = self.struct.size
        self.total_fields = amt

    def from_python(self, value):
        if self.is_valid(value):
            return value

    def write_bytes(self, data):
        values = []
        for field in [self,] + self.neighbours:
            value = data.get(field.name)
            if field.field_count == 1:
                values.append(field.from_python(value))
            else:
                values.extend(field.from_python(value))
        packed = self.struct.pack(*values)
        return packed

    def to_python(self, value):
        return value

    def read_bytes(self, data, index):
        unpack = self.struct.unpack_from(data, index)
        if len(unpack) != self.total_fields:
            raise InvalidReturnCount("%d items were returned, but %d were expected" % (len(unpack), self.total_fields))
        read = {}

        i = 0
        for field in [self,] + self.neighbours:
            if field.field_count == 1:
                read[field.name] = field.to_python(unpack[i])
            else:
                read[field.name] = field.to_python(unpack[i:i+field.field_count])
            i += field.field_count
        return read, self.length

class CharField(StructField):
    struct_type = 'c'

class BooleanField(StructField):
    struct_type = 'c'
    def to_python(self, value):
        return bool(value)

    def validate(self, value):
        return value in (True, False)

    def from_python(self, value):
        return 1 if value else 0

class UByteField(StructField):
    struct_type = 'B'

    validate = _between(0, 256)

ByteField = UInt8Field = UByteField

class SByteField(StructField):
    struct_type = 'b'

    validate = _between(-0x80, 0x7F)

Int8Field = SByteField

class UShortField(StructField):
    struct_type = 'H'

    validate = _between(0, 0xFFFF)

UInt16Field = UShortField

class SShortField(StructField):
    struct_type = 'h'

    validate = _between(-0x8000, 0x7FFF)

Int16Field = SShortField

class UIntField(StructField):
    struct_type = 'I'

    validate = _between(0, 0xFFFFFFFF)

ULongField = UInt32Field = UIntField

class SIntField(StructField):
    struct_type = 'i'

    validate = _between(-0x80000000, 0x7FFFFFFF)

LongField = Int32Field = SIntField

class ULongLongField(StructField):
    struct_type = 'Q'

    validate = _between(0, 0xFFFFFFFFFFFFFFFF)

UInt64Field = ULongLongField

class SLongLongField(StructField):
    struct_type = 'q'

    validate = _between(-0x8000000000000000, 0x7FFFFFFFFFFFFFFF)

Int64Field = SLongLongField
