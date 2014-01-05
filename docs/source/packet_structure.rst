==================
 Packet Structure 
==================

While the main structure of a packet should be self-explanatory, there are
some things to keep in mind while building your own packets.

Packet ID
---------

Each Packet has it's own Packet ID; this is the identifier to which it is
known in the protocol. This, together with the protocol type and direction,
must be unique in the packet registry (unless it is overwriting another).

Packet IDs are represented on the network as a single byte, and will be
checked prior to sending a packet over the network.

.. note::
    While it is possible to register a packet with a Packet ID larger than
    255 (the maximum value of a byte), it should be noted that libopenttd
    will not validate this until the packet is sent, as it is the task of
    the socket to validate the data prior to sending it, instead of when the
    packet is created.

.. note::
    This is mainly done to ensure that libopenttd is future-proof; if OpenTTD
    decides that the protocol should allow Packet IDs larger than 255, very
    little will have to be changed to allow so on our end.

Fields
------

Packets usually have several fields to indicate what data is sent with this
packet.

On the class definition, these fields contain the information pertaining to
what kind of data we expect, however, when using the classes to send/receive
data, the fields will hold the actual data itself.

All fields are describes :ref:`here <field-reference>`, and should provide enough
information to understand the built-in packet, and be sufficient to create
your own packets/fields.

.. note::
    Please note that fields are optional. There are some packets who only
    serve to send a 'notification' of sorts, and as such, have no fields.

Metadata
--------

Any settings (other than the above mentioned Packet ID) is located in the
metadata of the Packet class.

Most settings are inherited by any subclass packet, allowing one to easily set
certain settings for multiple packets (such as the Direction or Protocol).

.. note::
    If a meta setting is -not- inherited, it will be noted as such, otherwise
    all settings are inherited by subclasses.
