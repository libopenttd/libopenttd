========
 Design 
========

libopenttd's Packet structure is designed in such a way that it allows for
easy implementing the OpenTTD network protocols. Using python's metaclass
mechanics allows a more descriptive approach, without having to write a
reader/writer for each packet type.

Another advantage of this approach is that it allows libopenttd to act as a
proxy, or to act as a server for other client libraries to test their working.

To use these packets, a set of socket classes are available to use; these
allow basic functionality to automatically read/write packets to a OpenTTD
(or other libopenttd) server.

Packets imported from modules will automatically be added to a central
registry, so that they can automatically be sent and/or received over the
network. Ofcourse it's also possible to override any existing packet
descriptor, so that all default functionality can be replaced by one's own.
