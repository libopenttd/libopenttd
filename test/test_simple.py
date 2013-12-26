import unittest

from libopenttd import packets

class TestPacket(packets.Packet):
    testa = packets.UInt16Field(ordering=001)
    testb = packets.UInt32Field(ordering=002)
    testc = packets.UInt16Field(ordering=100) # Set to highest to ensure last packet field.
    testd = packets.UInt32Field(ordering=003)
    class Meta:
        virtual = True

class TestSimple(unittest.TestCase):
    def setUp(self):
        self.packet_data = '\x00\x00\x00\x01\x00\x00\x00\x02\x00\x03\x00\x00'
        self.test_packet = TestPacket(testa=0, testb=256, testc=0, testd=50332160)

    def test_packet_field_count(self):
        self.assertTrue(len(TestPacket._meta.fields) == 4,
                        msg = "TestPacket's fields list does not contain 4 items")

    def test_packet_parsing_field_count(self):
        self.assertTrue(len(TestPacket._meta.parsing_fields) == 1, 
                        msg = "TestPacket's field merging failed.")

    def test_packet_field_ordering(self):
        self.assertTrue(TestPacket._meta.fields_sorted[-1].name == "testc", 
                        msg = "TestPacket's last field is not 'testc'")

    def test_packet_reading(self):
        packet = TestPacket.manager.from_data(self.packet_data)
        self.assertTrue(packet.testa == self.test_packet.testa)
        self.assertTrue(packet.testb == self.test_packet.testb)
        self.assertTrue(packet.testc == self.test_packet.testc)
        self.assertTrue(packet.testd == self.test_packet.testd)

    def test_packet_writing(self):
        data = self.test_packet.write()
        self.assertTrue(data == self.packet_data)
