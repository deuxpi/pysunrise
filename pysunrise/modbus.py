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
from pymodbus.factory import ClientDecoder
from pymodbus.transaction import ModbusBinaryFramer
from pymodbus.utilities import computeCRC

import logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

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
        self.__start = '\x0a'
        self.__end = '\x0d'

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

