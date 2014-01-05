.. _field-reference:

========
 Fields 
========

The following fields are available for use by default:

.. index:: Field

Field
-----
The Field class is the main class from which all fields (must) inherit.

.. index:: Field;Members

Field members
^^^^^^^^^^^^^

All Field subclasses implement the following members:

Field.is_fixed_length()
"""""""""""""""""""""""

Returns True or False whether this field has a fixed length on the datastream.
This function is not normally called, however, it can be used for certain
packets to see how long this packet (should) be.

Field.get_field_size()
""""""""""""""""""""""

Returns the amount of bytes (if fixed length) this field takes on the
datastream.

Field.can_merge(other)
""""""""""""""""""""""

Returns True or False whether or not this class can merge together with the
`other` field.
When not defined, this will always return False.

Field.merge(other)
""""""""""""""""""

If Field.can_merge returns True, Field.merge is called to actually do the 
merging. By default, this appends ``other`` to the neighbours list of the Field.

Field.is_valid(value)
"""""""""""""""""""""
This function will, by default, iterate over ``Field.validators`` and raise an
``InvalidFieldData`` if any of the validators returned False.

Field.validate(value)
"""""""""""""""""""""

When defined, this function will be added to the validators list (even if 
validators are specified in the __init__ call.).
This function returns True or False depending if the value is valid for this
field type; and can (in theory) raise an ``InvalidFieldData`` exception to
specify a more detailed error message.

Field._prepare()
""""""""""""""""

This method is called by the metaclass after any sorting and merging has been
done. This allows the Field to do extra processing based upon it's merged
neighbours.

Field.from_python(value)
""""""""""""""""""""""""

This abstract method converts ``value`` to it's **binary** representation. this
way we can use (for example) a ``datetime.datetime`` object to specify a
date/time, while we send a unix timestamp over the wire.

Field.to_python(value)
""""""""""""""""""""""

This abstract method converts ``value`` to it's **python** representation. this
way we can use (for example) a ``datetime.datetime`` object to specify a
date/time, while we send a unix timestamp over the wire.

Field.write_bytes(data, datastream, extra)
""""""""""""""""""""""""""""""""""""""""""

This abstract method is responsible for converting the data of this and any
neighbouring fields, and appending it to the ``datastream``

The ``data`` variable holds all the data for this packet object (so this and
any other neighbouring fields' data is available here).

The ``extra`` variable (for now) holds the protocol's running version.

Field.read_bytes(data, index, obj_data, extra)
""""""""""""""""""""""""""""""""""""""""""""""

This abstract method is responsible for reading the data from ``data``, and
converting this field (and any neighbouring fields) to its value.
The value for this field should be added to the ``obj_data`` dict. the Field
can use the ``name`` property to get the name of this field.

This method returns the size of the datastream that has been consumed, so that
the next field will be pointed to the right location in the datastream for its
data.

The ``data`` variable contains the full datastream for this current packet,
including any previous fields. the ``index`` variable points to the current
position on the datastream and should be followed.

The ``extra`` variable (for now) holds the protocol's running version.
