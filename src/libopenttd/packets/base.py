#
# Some parts (well, a quite a lot actually) is inspired by Django's ModelBase.
#
import copy
from libopenttd.util import six

OPTIONS_DEFAULT_NAMES = (
    )

class PacketOptions(object):
    def __init__(self, meta):
        self.meta = meta
        self.fields = []

    def contribute_to_class(self, cls, name):
        cls._meta = self
        self.packet = cls
        self.pid = cls.pid

        if self.meta:
            meta_attrs = self.meta.__dict__.copy()
            for name in self.meta.__dict:
                if name.startswith('_'):
                    del meta_attrs[name]
            for attr_name in OPTIONS_DEFAULT_NAMES:
                if attr_name in meta_attrs:
                    setattr(self, attr_name, meta_attrs.pop(attr_name))
                elif hasattr(self.meta, attr_name):
                    setattr(self, attr_name, getattr(self.meta, attr_name))
        del self.meta

    def add_field(self, field):
        self.fields.append(field)

class PacketBase(type):
    def __new__(mcs, name, bases, attrs):
        print "__NEW__"
        print mcs, name, bases, attrs
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
        if not attr_meta:
            meta = getattr(new_class, 'Meta', None)
        else:
            meta = attr_meta
        new_class.add_to_class('_meta', PacketOptions(meta))

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

        return new_class
    
    def add_to_class(cls, name, value):
        if hasattr(value, 'contribute_to_class'):
            value.contribute_to_class(cls, name)
        else:
            setattr(cls, name, value)

class PacketFieldBase(object):
    def __init__(self, name = None, is_struct_field = False):
        self.name = name
        self.is_struct_field = is_struct_field

    def set_attributes_from_name(self, name):
        if not self.name:
            self.name = name

    def contribute_to_class(self, cls, name):
        self.set_attributes_from_name(name)
        cls._meta.add_field(self)
