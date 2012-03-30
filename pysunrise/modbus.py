#!/usr/bin/python

# pysunrise - Reads performance information from Solectria PVI inverters.
#
# Copyright (C) 2012 Philippe Gauthier <philippe.gauthier@deuxpi.ca>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import struct

from pymodbus.client.sync import ModbusSerialClient as ModbusClient
from pymodbus.exceptions import ConnectionException
from pymodbus.factory import ClientDecoder
from pymodbus.transaction import ModbusBinaryFramer
from pymodbus.utilities import checkCRC, computeCRC

__all__ = ["InverterModbusClient"]


class InverterModbusFramer(ModbusBinaryFramer):
    """This class builds Modbus frames (ADU) which are compatible with
    Solectria inverters.

    Messages to and from the inverter are verified by an error checksum and
    start by a carriage return (0x0A) and end with a line feed (0x0D). The
    error checksum is represented by a cyclic redundancy check (CRC16).
    """

    def __init__(self, decoder):
        ModbusBinaryFramer.__init__(self, decoder)
        self.__buffer = ''
        self.__header = {'crc': 0x0000, 'len': 0, 'uid': 0x00}
        self.__hsize = 0x02
        self.__start = '\x0a'
        self.__end = '\x0d'

    def checkFrame(self):
        start = self.__buffer.find(self.__start)
        if start == -1:
            return False
        self.__buffer = self.__buffer[start:]
        end = self.__buffer.rfind(self.__end)
        if end == -1:
            return False
        if end - start < 3:
            return False
        self.__header['len'] = end - start + 1
        self.__header['uid'] = struct.unpack('>B', self.__buffer[start + 1])
        self.__header['crc'] = struct.unpack('>H',
                                             self.__buffer[end - 2:end])[0]
        data = self.__buffer[start + 1:end - 2]
        return checkCRC(data, self.__header['crc'])

    def advanceFrame(self):
        self.__buffer = self.__buffer[self.__header['len']:]
        self.__header = {'crc': 0x0000, 'len': 0, 'uid': 0x00}

    def isFrameReady(self):
        return len(self.__buffer) > 1

    def addToFrame(self, message):
        self.__buffer += message

    def getFrame(self):
        start = self.__hsize
        end = self.__header['len'] - 3
        buffer = self.__buffer[start:end]
        if end > 0:
            return buffer
        return ''

    def populateResult(self, result):
        result.unit_id = self.__header['uid']

    def buildPacket(self, message):
        packet = struct.pack('>BB',
            message.unit_id,
            message.function_code) + message.encode()
        packet += struct.pack(">H", computeCRC(packet))
        packet = '%s%s%s' % (self.__start, packet, self.__end)
        return packet


class InverterModbusClient(ModbusClient):
    def __init__(self, **kwargs):
        ModbusClient.__init__(self, method='binary', **kwargs)
        self.framer = InverterModbusFramer(ClientDecoder())

    def execute(self, request=None):
        if not self.connect():
            raise ConnectionException("Failed to connect[%s]" % (self.__str__()))
        if self.transaction:
            # FIXME This is an ugly hack to allow the transaction manager
            # to multiplex the client connections.
            self.transaction.client = self
            return self.transaction.execute(request)
        raise ConnectionException("Client Not Connected")

    def _recv(self, size):
        while True:
            data = self.socket.read(1)
            if data == "":
                break
            self.framer.addToFrame(data)
            if self.framer.checkFrame():
                break
        return ""
