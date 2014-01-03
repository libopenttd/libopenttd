#
# Some parts (well, a quite a lot actually) is inspired by Django's ModelBase.
#
import copy

from .enums import Direction, Protocol
from .registry import registry

from operator import attrgetter

OPTIONS_DEFAULT_NAMES = (
    'abstract', 'direction', 'protocol', 'override', 'virtual', 'force_virtual', 'default_version',
    )
OPTIONS_INHERITED = (
    'protocol', 'direction', 'force_virtual', 'default_version',
    )

class PacketManager(object):
    def __init__(self):
        self.packet = None
        self.opts = None

    def contribute_to_class(self, cls, name):
        self.packet = cls
        self.opts = cls._meta
        setattr(cls, name, self)

    def from_data(self, data, index = 0, extra = None):
        all_fields = {}
        if extra is None:
            extra = {}

        version_field = None
        for field in self.opts.fields:
            if field.is_version_identifier:
                version_field = field.name

        for field in self.opts.parsing_fields:
            if field.required_version:
                if extra.get('version', self.opts.default_version) < field.required_version:
                    continue
            fielddata, length = field.read_bytes(data, index, extra)
            if version_field and version_field in fielddata:
                extra['version'] = fielddata.get(version_field)
            index += length
            all_fields.update(fielddata)

        obj = self.packet()
        for field in self.opts.fields:
            setattr(obj, field.name, all_fields.get(field.name))
        return obj

    def to_data(self, packet, extra = None):

        data = dict([(field.name, getattr(packet, field.name, None)) for field in self.opts.fields])

        segments = []
        for field in self.opts.parsing_fields:
            if field.required_version:
                if extra.get('version', self.opts.default_version) < field.required_version:
                    continue
            segments.append(field.write_bytes(data))

        return ''.join(segments)

class PacketOptions(object):
    def __init__(self, meta, name):
        self.direction = Direction.BOTH
        self.protocol = Protocol.NONE
        self.name = name
        self.meta = meta
        self.abstract = False
        self.override = False
        self.fields = []
        self.fields_sorted = []
        self.parsing_fields = []
        self.default_version = -1

    def contribute_to_class(self, cls, name):
        base_meta = getattr(cls, '_meta', None)
        cls._meta = self
        self.packet = cls
        self.pid = cls.pid

        for option in OPTIONS_INHERITED:
            if not hasattr(base_meta, option):
                continue
            setattr(self, option, getattr(base_meta, option))

        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict__:
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in OPTIONS_DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))
        del self.meta

        self.registry = registry

    def _prepare(self, packet):
        self.fields_sorted = sorted(self.fields, key = attrgetter("ordering"))

        # We iterate over our fields list, and merge the fields that are both adjacent
        #  and inform us they can merge together.
        iterator = iter(self.fields_sorted)
        done = object()

        last_field = None
        field = next(iterator, done)
        while field is not done:
            if last_field and last_field.can_merge(field):
                last_field.merge(field)
                field = next(iterator, done)
                continue
            last_field = field
            self.parsing_fields.append(field)
            field = next(iterator, done)
        # Next up we inform all merged fields that they should prepare for action.
        for field in self.parsing_fields:
            field._prepare()

        #Signal back that we've done our preparations
        packet._prepared = True

    def add_field(self, field):
        self.fields.append(field)

    def add_fields(self, fields):
        if isinstance(fields, (list, tuple, set)):
            self.fields.extend(list(fields))

    def get_field_by_name(self, name):
        for field in self.fields:
            if field.name == name:
                return field
        return None

class PacketBase(type):
    def __new__(mcs, name, bases, attrs):
        super_new = super(PacketBase, mcs).__new__

        # six.with_metaclass() inserts an extra class called 'NewBase' in the
        # inheritance tree: Packet -> NewBase -> object. But the initialization
        # should be executed only once for a given model class.

        # attrs will never be empty for classes declared in the standard way
        # (ie. with the `class` keyword). This is quite robust.
        if name == 'NewBase' and attrs == {}:
            return super_new(mcs, name, bases, attrs)

        # Also ensure initialization is only performed for subclasses of Packet
        # (excluding Packet class itself).
        parents = [base for base in bases if isinstance(base, PacketBase) and
                    not (base.__name__ == 'newBase' and base.__mro__ == (base, object))]
        if not parents:
            return super_new(mcs, name, bases, attrs)

        module = attrs.pop('__module__')
        new_class = super_new(mcs, name, bases, {'__module__': module})
        pid = attrs.pop('pid', getattr(new_class, 'pid', -1)) # Todo: Add exception when no PID is set.

        new_class.add_to_class('pid', pid)

        attr_meta = attrs.pop('Meta', None)

        abstract = getattr(attr_meta, 'abstract', False)
        virtual = getattr(attr_meta, 'virtual', False)
        override = getattr(attr_meta, 'override', False)
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        base_meta = getattr(new_class, '_meta', None)

        force_virtual = getattr(attr_meta, 'force_virtual', getattr(base_meta, 'force_virtual', False))
        
        new_class.add_to_class('_meta', PacketOptions(meta, name))

        # Add all attributes to the class.
        for obj_name, obj in attrs.items():
            new_class.add_to_class(obj_name, obj)

        field_names = set(f.name for f in new_class._meta.fields)

        for base in parents:
            #original_base = base
            if not hasattr(base, '_meta'):
                continue
            parent_fields = base._meta.fields
            for field in parent_fields:
                if field.name not in field_names:
                    # Add non-overlapping fields to our registry
                    new_class.add_to_class(field.name, copy.deepcopy(field))

        if abstract:
            # Abstract packets are not prepared, instead, they are returned as-is.
            attr_meta.abstract = False
            new_class.Meta = attr_meta #pylint: disable=C0103
            return new_class
        
        new_class._prepare()

        if override:
            # Override packets forcefully override themselves in the packet registry
            #  but to prevent their children to do the same, we force it back to False
            #  before we register it
            attr_meta.override = False
            new_class.Meta = attr_meta
        if virtual or force_virtual:
            # Virtual packets are prepared, but not registered, this allows them to be
            #  used as fields of other packets
            if virtual:
                attr_meta.virtual = False
                new_class.Meta = attr_meta
            return new_class

        new_class._meta.registry.register_packet(new_class)

        return new_class

    def _prepare(cls):
        opts = cls._meta
        opts._prepare(cls)
        cls.add_to_class('manager', PacketManager())

    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

    class Meta:
        abstract = True

class FieldBase(object):
    def __init__(self, ordering = None):
        self.name = None
        self.ordering = ordering

    def can_merge(self, other):
        return False

    def merge(self, other):
        pass

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        cls._meta.add_field(self)
