import unittest

from libopenttd import packets
from libopenttd.utils.six.moves import range 

class TestPacket(packets.Packet):
    testa = packets.UInt16Field(ordering=1)
    testb = packets.UInt32Field(ordering=2)
    testc = packets.UInt16Field(ordering=100) # Set to highest to ensure last packet field.
    testd = packets.Int16Field(ordering=3)
    teste = packets.StringField(ordering=4)
    testf = packets.StringField(ordering=5)
    testg = packets.UInt8Field(ordering=6)
    testh = packets.StringField(ordering=90)
    class Meta:
        virtual = True

class TestSimple(unittest.TestCase):
    def setUp(self):
        self.test_data = {
            'testa': 0xFFFF,
            'testb': 5,
            'testc': 0,
            'testd': -0x8000,
            'teste': 'test-string-01',
            'testf': 'test-string-02',
            'testg': 255,
            'testh': 'test-string-03',
        }
        self.merged_counts = [
            2,
            1,
            0,
            0,
            0,
        ]
        self.packet_data = '\xff\xff\x05\x00\x00\x00\x00\x80test-string-01\x00test-string-02\x00\xfftest-string-03\x00\x00\x00'
        self.test_packet = TestPacket(**self.test_data)

    def test_packet_field_count(self):
        self.assertTrue(len(TestPacket._meta.fields) == 8,
                        msg = "TestPacket's fields list does not contain 8 items")

    def test_packet_parsing_field_count(self):
        self.assertTrue(len(TestPacket._meta.parsing_fields) == 5, 
                        msg = "TestPacket's field merging failed.")
        for i in range(len(self.merged_counts)):
            self.assertTrue(len(TestPacket._meta.parsing_fields[i].neighbours) == self.merged_counts[i])

    def test_packet_field_ordering(self):
        self.assertTrue(TestPacket._meta.fields_sorted[-1].name == "testc", 
                        msg = "TestPacket's last field is not 'testc'")

    def test_packet_reading(self):
        packet = TestPacket.manager.from_data(self.packet_data)
        for key, value in self.test_data.items():
            self.assertTrue(getattr(packet, key) == getattr(self.test_packet, key))
            self.assertTrue(getattr(packet, key) == self.test_data[key])

    def test_packet_writing(self):
        data = self.test_packet.write()
        self.assertTrue(data == self.packet_data)
