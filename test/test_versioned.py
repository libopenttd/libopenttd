import unittest

from libopenttd import packets
from libopenttd.utils.six.moves import range


class TestPacket(packets.Packet):
    version = packets.UInt8Field(ordering=1, is_version_identifier=True)
    testa = packets.UInt32Field(ordering=2, required_version = 1)
    testb = packets.UInt16Field(ordering=3, required_version = 2)
    testc = packets.Int16Field(ordering=4, required_version = 3)
    testd = packets.StringField(ordering=5, required_version = 1)
    class Meta:
        virtual = True

class TestVersions(unittest.TestCase):
    def setUp(self):
        self.test_data = {
            'testa': 5,
            'testb': 0,
            'testc': -0x8000,
            'testd': 'test-string-01',
        }
        self.packet_data = {
            1:  '\x01\x05\x00\x00\x00test-string-01\x00',
            2:  '\x02\x05\x00\x00\x00\x00\x00test-string-01\x00',
            3:  '\x03\x05\x00\x00\x00\x00\x00\x00\x80test-string-01\x00',
            4:  '\x04\x05\x00\x00\x00\x00\x00\x00\x80test-string-01\x00',
        }
        self.versioned_fields = {
            1: ['testa', 'testd'],
            2: ['testa', 'testb', 'testd'],
            3: ['testa', 'testb', 'testc', 'testd'],
            4: ['testa', 'testb', 'testc', 'testd'],
        }
        self.versioned_missing = {
            1: ['testb', 'testc'],
            2: ['testc'],
        }

    def test_versioned_writing(self):
        for i in range(1, 5):
            packet = TestPacket(**self.test_data)
            packet.version = i
            self.assertTrue(packet.write(extra={'version': i}) == self.packet_data[i])

    def test_versioned_reading(self):
        packetdata = dict([(i, TestPacket.manager.from_data(self.packet_data[i])) for i in range(1, 5)])
        for i, packet in packetdata.items():
            for field in self.versioned_fields[i]:
                self.assertTrue(getattr(packet, field) == self.test_data[field])

        for i, fields in self.versioned_missing.items():
            for field in fields:
                self.assertTrue(getattr(packetdata[i], field) == None)
