from .base import FieldBase, PacketOptions
from .constants import NETWORK_GAMESCRIPT_JSON_LENGTH
from .exceptions import InvalidReturnCount, InvalidFieldData, InvalidPacketLayout
from libopenttd.utils import six
from libopenttd.utils.six.moves import range

from struct import Struct
from datetime import datetime, timedelta

GAMEDATE_BASE_DATE = datetime(1, 1, 1)
GAMEDATE_BASE_OFFSET = 366

def gamedate_to_datetime(date):
    if date < GAMEDATE_BASE_OFFSET: # We really only get 0 occasionally, but cover all the cases.
        return datetime.min
    return GAMEDATE_BASE_DATE + timedelta(days = date  - GAMEDATE_BASE_OFFSET)

def datetime_to_gamedate(datetime):
    return (datetime - GAMEDATE_BASE_DATE).days + GAMEDATE_BASE_OFFSET

try:
    import json
except ImportError:
    import simplejson as json

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
    is_next         = False

    def __init__(self, ordering = -1, validators = None, is_next = False, *args, **kwargs):
        super(Field, self).__init__(ordering = ordering, *args, **kwargs)
        self.neighbours = []
        self.is_next = is_next
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

class JsonField(StringField):
    def from_python(self, value):
        value = json.dumps(value)
        return super(JsonField, self).from_python(value)

    def to_python(self, value):
        if isinstance(value, six.string_types):
            value = super(JsonField, self).to_python(value)
            value = json.loads(value)
        elif isinstance(value, (list, dict, tuple, set)):
            pass
        else:
            value = six.text_type(value)
        return value

    def validate(self, value):
        if not isinstance(value, six.string_types):
            value = self.from_python(value)
        return len(value) < NETWORK_GAMESCRIPT_JSON_LENGTH

class RepeatingField(Field):
    _meta       = None
    field_count = 1
    expected_count = 1

    def __init__(self, fields = None, count = 1, *args, **kwargs):
        super(RepeatingField, self).__init__(*args, **kwargs)
        self._meta = PacketOptions(None, None)
        if isinstance(fields, dict):
            for name, field in six.iteritems(fields):
                field.contribute_to_class(self, name)
        self.field_count = self.expected_count = count

    def _prepare(self):
        self._meta._prepare(self)

    def to_python(self, value):
        return value

    def read_bytes(self, data, index):
        start = index
        values = []
        for _ in range(self.field_count):
            value = {}
            for field in self._meta.parsing_fields:
                fielddata, increment = field.read_bytes(data, index)
                index += increment
                value.update(fielddata)
            values.append(value)
        return {self.name: self.to_python(values)}, index - start

    def from_python(self, value):
        return value

    def write_bytes(self, data):
        if not len(data.get(self.name)) == self.expected_count:
            raise InvalidFieldData("Field %s expected %d items, not %d" % 
                (self.name, self.expected_count, len(data.get(self.name))))
        value = ''
        data = self.from_python(data.get(self.name))
        for item in data:
            for field in self._meta.parsing_fields:
                value += field.write_bytes(item)
        return value

class GroupedField(RepeatingField):
    def __init__(self, fields = None, *args, **kwargs):
        super(RepeatingField, self).__init__(*args, **kwargs)
        self._meta = PacketOptions(None, None)
        if isinstance(fields, dict):
            for name, field in six.iteritems(fields):
                field.contribute_to_class(self, name)
        self.expected_count = len(fields)

    def to_python(self, value):
        if isinstance(value, (list, tuple)):
            return value[0]

    def from_python(self, value):
        if not isinstance(value, (list, tuple)):
            return [value,]
        return value

class LoopingField(Field):
    _meta       = None
    next_field  = None

    def __init__(self, fields = None, *args, **kwargs):
        super(LoopingField, self).__init__(*args, **kwargs)
        self._meta = PacketOptions(None, None)
        if isinstance(fields, dict):
            for name, field in six.iteritems(fields):
                field.contribute_to_class(self, name)
        self.next_field = None

    def _prepare(self):
        self._meta._prepare(self)
        for field in self._meta.fields:
            if field.is_next:
                self.next_field = field
                break
        if not self.next_field:
            raise InvalidPacketLayout("No field marked with is_next found")
        self.next_field._prepare()

    def to_python(self, value):
        return value

    def read_bytes(self, data, index):
        start = index
        value, increment = self.next_field.read_bytes(data, index)
        index += increment
        values = []
        while value.get(self.next_field.name):
            value = {}
            for field in self._meta.parsing_fields:
                fielddata, increment = field.read_bytes(data, index)
                index += increment
                value.update(fielddata)
            values.append(value)
        return {self.name: self.to_python(values)}, index - start

    def from_python(self, value):
        return value

    def write_bytes(self, data):
        if not data:
            return  self.next_field.write_bytes({self.next_field.name: False})
        data = self.from_python(data.get(self.name))
        last_index = len(data) - 1
        values = self.next_field.write_bytes({self.next_field.name: True})
        for i, item in enumerate(data):
            item.update({self.next_field.name: i != last_index})
            for field in self._meta.parsing_fields:
                values += field.write_bytes(item)
        return values

    def set_attributes_from_name(self, name):
        super(LoopingField, self).set_attributes_from_name(name)
        self._meta.name = name

class DictField(LoopingField):
    def __init__(self, key = None, value = None, is_next = None, *args, **kwargs):
        fields = {'key': key, 'value': value, 'is_next': is_next}
        kwargs['fields'] = fields
        super(DictField, self).__init__(*args, **kwargs)

    def to_python(self, value):
        return dict([(val['key'], val['value']) for val in value])

    def from_python(self, value):
        return [{'key': key, 'value': value} for key, value in six.iteritems(value)]

class StructField(Field):
    struct_type = None
    field_count = 1

    _structCache = {}

    def get_struct_type(self):
        return self.struct_type * self.field_count

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

    def __init__(self, count = 1, *args, **kwargs):
        super(StructField, self).__init__(*args, **kwargs)
        self.struct = None
        self.field_count = count
        self.length = 0

    def can_merge(self, other):
        return isinstance(other, StructField)

    def _prepare(self):
        fmt = self.get_struct_type()
        amt = self.field_count
        for neigh in self.neighbours:
            fmt += neigh.get_struct_type()
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
            if field.field_count != 1:
                if not len(value) == field.field_count:
                    raise InvalidFieldData("Field '%s' expected %d items but only received %d" % 
                        (field.name, field.field_count, len(value)))
                values.extend([field.from_python(val) for val in value])
            else:
                values.append(field.from_python(value))
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
                read[field.name] = [field.to_python(x) for x in unpack[i:i+field.field_count]]
            i += field.field_count
        return read, self.length

class CharField(StructField):
    struct_type = 'c'

class BooleanField(StructField):
    struct_type = '?'
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

class DateField(UIntField):
    def to_python(self, value):
        return gamedate_to_datetime(value)

    def from_python(self, value):
        return datetime_to_gamedate(value)

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
