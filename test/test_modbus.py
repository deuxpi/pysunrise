import unittest

from pysunrise.modbus import InverterModbusClient, InverterModbusFramer
from pymodbus.pdu import ModbusRequest
from pymodbus.factory import ServerDecoder

class InverterClientTest(unittest.TestCase):
    def testInverterClientInstantiation(self):
        client = InverterModbusClient()
        self.assertIsNotNone(client)
        self.assertIsInstance(client.framer, InverterModbusFramer)

    def testInverterFramerPacket(self):
        framer = InverterModbusFramer(ServerDecoder())
        old_encode = ModbusRequest.encode
        ModbusRequest.encode = lambda self: ''
        message = ModbusRequest()
        message.unit_id = 0xff
        message.function_code = 0x01
        expected = '\x0a\xff\x01\x81\x80\x0d'
        actual = framer.buildPacket(message)
        ModbusRequest.encode = old_encode
        self.assertEqual(expected, actual)

if __name__ == '__main__':
    unittest.main()

