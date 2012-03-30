import unittest

from pysunrise.modbus import InverterModbusClient, InverterModbusFramer
from pymodbus.pdu import ModbusRequest
from pymodbus.factory import ServerDecoder


class ModbusTest(unittest.TestCase):
    def setUp(self):
        self.framer = InverterModbusFramer(ServerDecoder())

    def testInverterClientInstantiation(self):
        client = InverterModbusClient()
        self.assertIsNotNone(client)
        self.assertIsInstance(client.framer, InverterModbusFramer)

    def testInverterFramerBufferEmpty(self):
        self.assertFalse(self.framer.isFrameReady())
        self.assertFalse(self.framer.checkFrame())

    def testFramerLineFeedInMessage(self):
        message = '\x0a\x01\x03\x02\x00\x0d\x79\x81\x0d'
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertTrue(self.framer.checkFrame())
        result = self.framer.getFrame()
        self.assertEqual(message[2:-3], result)

    def testFramerIncompleteMessage(self):
        message = '\x0a\x01\x03'
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertFalse(self.framer.checkFrame())

    def testFramerMessageTooShort(self):
        message = '\x0a\x0d'
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertFalse(self.framer.checkFrame())

    def testInverterFramerDecoding(self):
        message = '\x0a\x01\x03\x02\x00\xcb\xf9\xd3\x0d'
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertTrue(self.framer.checkFrame())
        result = self.framer.getFrame()
        self.assertEqual(message[2:-3], result)
        self.framer.advanceFrame()
        self.assertFalse(self.framer.isFrameReady())
        self.assertFalse(self.framer.checkFrame())
        self.assertEqual('', self.framer.getFrame())

    def testInverterFramerDecodeTwice(self):
        message = '\x0a\x01\x03\x02\x00\xcb\xf9\xd3\x0d'
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertTrue(self.framer.checkFrame())
        result = self.framer.getFrame()
        self.assertEqual(message[2:-3], result)
        self.framer.advanceFrame()
        self.framer.addToFrame(message)
        self.assertTrue(self.framer.isFrameReady())
        self.assertTrue(self.framer.checkFrame())

    def testInverterFramerEncoding(self):
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.unit_id = 0xff
        message.function_code = 0x01
        expected = '\x0a\xff\x01\x81\x80\x0d'
        actual = self.framer.buildPacket(message)
        ModbusRequest.encode = old_encode
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()
