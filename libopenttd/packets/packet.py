from .base import PacketBase
from libopenttd.utils import six
from .exceptions import InvalidFieldName
from itertools import izip_longest

class Packet(six.with_metaclass(PacketBase)):
    pid = -1

    def __init__(self, *args, **kwargs):
        all_names = set([field.name for field in self._meta.fields])
        data = {}

        if len(args) > len(self._meta.fields):
            raise IndexError("Number of args exceeds number of fields")
        for field, arg in izip_longest(self._meta.fields_sorted, args, fillvalue=None):
            if arg is None:
                break
            data[field.name] = arg

        for field in six.iterkeys(kwargs):
            if field not in all_names:
                raise InvalidFieldName("Field name '%s' not found, did you mean: %s" % (field, ', '.join(all_names)))

        data.update(kwargs)

        for field in self._meta.fields:
            value = data.get(field.name, field.default_value)
            setattr(self, field.name, value)

    def as_dict(self):
        return dict([
            (field.name, getattr(self, field.name, field.default_value))
            for field in self._meta.fields
            ])

    def write(self):
        return self.manager.to_data(self)

    @classmethod
    def is_fixed_length(self):
        return all([field.is_fixed_length() for field in self._meta.fields])

    @classmethod
    def get_packet_size(self):
        if not self.is_fixed_length():
            return 0
        else:
            return sum([field.get_field_size() for field in self._meta.fields])

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

    class Meta:
        abstract = True
