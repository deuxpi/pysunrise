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

import binascii
import curl
import datetime
import math
import sched
import serial
import struct
import sys
import time

__author__ = "Philippe Gauthier"
__copyright__ = "Copyright (C) 2012 Philippe Gauthier"
__license__ = """License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law."""
__version__ = "0.1"

__all__ = ["PVInverter", "READ_REGISTERS"]

READ_REGISTERS = 3

def crc(s):
    rem = 0xffff
    for c in s:
        rem = rem ^ ord(c)
        for i in range(8):
            if rem & 0x0001 == 0:
                rem >>= 1
            else:
                rem = (rem >> 1) ^ 0xa001
    # Note that the CRC bytes are swapped relatively to big endian encoding.
    # This is as specified for MODBUS.
    return struct.pack("<H", rem)

class PVInverter:
    def __init__(self, address, ser):
        self.ser = ser
        self.address = address
        self.last_response = {}

    def reset(self):
        self.last_response = {}

    def _command(self, function, data):
        pdu = "%s%s%s" % (chr(self.address), chr(function), data)
        return "\x0a%s%s\x0d" % (pdu, crc(pdu))

    def _send_and_read(self, data, expected_length):
        junk = self.ser.read(51200)
        if junk:
            print >>sys.stderr, "Read junk: %s" % binascii.hexlify(junk)
        time.sleep(0.1)
        payload = self._command(READ_REGISTERS, data)
        self.ser.write(payload)
        self.ser.flush()
        for i in range(2):
            response = self.ser.read(expected_length)
            if response == "":
                #print >>sys.stderr, "Zero read"
                return
            if response[0] == '\x00':
                continue
            elif response[0] != '\x0a':
                print >>sys.stderr, "Bad read: %s while writing %s" % (binascii.hexlify(response), binascii.hexlify(payload))
                return
            else:
                break
        if response[0] == '\x00':
            return
        received_crc = response[-3:-1]
        computed_crc = crc(response[1:-3])
        if received_crc != computed_crc:
            print >>sys.stderr, "Bad CRC"
            return
        return response

    def read_registers(self, starting_address, num_points):
        data = struct.pack(">HH", starting_address, num_points)
        response = self._send_and_read(data, num_points * 2 + 7)
        if response:
            self.last_response[starting_address] = struct.unpack(">%dH" % num_points, response[4:-3])[0]
        if starting_address in self.last_response:
            return self.last_response[starting_address], response is not None
        else:
            return 0, False

class PVStack:
    def __init__(self, inverters):
        self.inverters = inverters

    def _get_sum(self, register):
        value = 0.0
        n = 0
        for pvi in self.inverters:
            response, real = pvi.read_registers(register, 1)
            value += response
            if real:
                n += 1
        return value, n

    def _get_mean(self, register):
        s, n = self._get_sum(register)
        if n != 0:
            return s / n
        raise

    def reset(self):
        for pvi in self.inverters:
           pvi.reset()

    def get_energy_today(self):
        e, n = self._get_sum(0xd9)
        if n != 0:
            return e * 0.1
        else:
            return None

    def get_hours_today(self):
        try:
            hours = []
            for pvi in self.inverters:
                response, real = pvi.read_registers(0xcc, 1)
                if real:
                    hours.append(response / 2048.0)
                else:
                    hours.append(0.0)
            return hours
        except:
            return None

    def get_hours_total(self):
        try:
            return self._get_mean(0xd1)
        except:
            return None

    def get_total_energy(self):
        try:
            energy_hi = self._get_sum(0xc4)[0]
            energy_low = self._get_sum(0xc5)[0]
            return (energy_hi * 1000.0) + (energy_low * 0.1)
        except Exception, e:
            return None

    def get_pv_voltage(self):
        try:
            return self._get_mean(0xba) * 0.1
        except:
            return None

    def get_pv_power(self):
        try:
            return self._get_sum(0xbd)[0]
        except:
            return None

    def get_ac_voltage(self):
        try:
            return self._get_mean(0xc0) * 0.1
        except:
            return None

    def get_ac_power(self):
        e, n = self._get_sum(0xc1)
        if n != 0:
            return e
        else:
            if n != 3:
                print "%d systems active only" % n
            return None

    def get_ac_current(self):
        try:
            return self._get_sum(0xc2)[0] * 0.1
        except:
            return None

    def get_ac_frequency(self):
        try:
            return self._get_mean(0xc3) * 0.01
        except:
            return None

class PVOutputSession(curl.Curl):
    def __init__(self, sid, key):
        self.url = "http://pvoutput.org/service/r2/"
        curl.Curl.__init__(self, self.url)
        self.set_option(curl.pycurl.URL, self.url)
        self.set_option(curl.pycurl.HTTPHEADER, [
            "X-Pvoutput-SystemId: %s" % sid,
            "X-Pvoutput-Apikey: %s" % key])

    def get_status(self):
        d = time.strftime("%Y%m%d")
        status = self.get("getstatus.jsp?d=%s&h=1" % d)
        return status

    def _int(self, value):
        if value == "NaN":
            return None
        return int(value)

    def _time(self, value):
        if value == "NaN":
            return None
        return datetime.time(*time.strptime(value, '%H:%M')[3:5])

    def get_output(self, from_date, to_date):
        data = self.get("getoutput.jsp?df=%s&dt=%s" % (from_date, to_date))
        result = []
        for line in data.split(";"):
            points = line.split(",")
            result.append({
                'date': datetime.datetime.strptime(points[0], "%Y%m%d"),
                'generated': int(points[1]),
                'efficiency': float(points[2]),
                'exported': int(points[3]),
                'used': int(points[4]),
                'peak_power': self._int(points[5]),
                'peak_time': self._time(points[6]),
                'condition': points[7],
                'min_temperature': self._int(points[8]),
                'max_temperature': self._int(points[9]),
                'peak_import': self._int(points[10]),
                'off-peak_import': self._int(points[11]),
                'shoulder_import': self._int(points[12]),
                'high-shoulder_import': self._int(points[13])
            })
        return result

    def add_output(self, date, generated, peak_power=None, peak_time=None, condition=None, min_temp=None, max_temp=None):
        params = [('d', date.strftime("%Y%m%d")),
                  ('g', "%d" % generated)]
        if peak_power is not None:
            params.append(('pp', str(peak_power)))
        if peak_time is not None:
            params.append(('pt', peak_time.strftime("%H:%M")))
        if condition is not None:
            params.append(('cd', condition))
        if min_temp is not None:
            params.append(('tm', str(min_temp)))
        if max_temp is not None:
            params.append(('tx', str(max_temp)))
        #print params
        return self.post("addoutput.jsp", tuple(params))

    def add_status(self, status_date, status_time, energy, power, voltage, cumulative=False):
        params = (('d', status_date.strftime("%Y%m%d")),
                  ('t', status_time.strftime("%H:%M")),
                  ('v1', str(energy)),
                  ('v2', str(power)),
                  ('v6', str(voltage)),
                  ('c1', int(cumulative)))
        return self.post("addstatus.jsp", tuple(params))

def display(label, value, units, precision=6):
    if value is None:
        value = "%11s" % "n/a"
    elif type(value) == list:
        value_format = "%%11.%df" % precision
        value = " ".join([value_format % v for v in value])
    else:
        value_format = "%%11.%df" % precision
        value = value_format % value
    print "%-26s = %s %s" % (label, value, units)

class Dummy:
    pass

scheduler = sched.scheduler(time.time, time.sleep)

def loop(stack):
    now = datetime.datetime.today()
    status_date = now.date()
    status_time = now.time()
    print "%s" % now
    #print

    energy_today = stack.get_energy_today()
    display("Energy Today", energy_today, "kWh", 3)

    hours_today = stack.get_hours_today()
    display("Hours Today", hours_today, "h", 3)

    runtime = stack.get_hours_total()
    display("Running Hours", runtime, "h", 3)

    total_energy = stack.get_total_energy()
    display("Total Energy", total_energy, "kWh", 3)
    #print

    pv_power = None
    ac_power = None

    pv_voltage = stack.get_pv_voltage()
    display("PV Voltage", pv_voltage, "V")

    pv_power = stack.get_pv_power()
    display("PV Power", pv_power, "W")
    #print

    #ac_voltage = stack.get_ac_voltage()
    #display("AC Voltage", ac_voltage, "V")

    #ac_current = stack.get_ac_current()
    #display("AC Current", ac_current, "A")

    #ac_power = stack.get_ac_power()
    #display("AC Power", ac_power, "W")

    #ac_frequency = stack.get_ac_frequency()
    #display("AC Frequency", ac_frequency, "Hz")
    #print

    if pv_power is not None and pv_power != 0.0 and ac_power is not None:
        eff = (ac_power / pv_power) * 100.0
        display("DC/AC Conversion Efficiency", eff, "%", 1)

    sid = "6360"
    key = "PUT PVOUTPUT KEY HERE"
    pvoutput = PVOutputSession(sid, key)

    energy = stack.get_energy_today()
    if energy is not None:
        energy *= 1000.0
    power = stack.get_ac_power()
    voltage = stack.get_pv_voltage()
    if energy is not None and power is not None and voltage is not None:
        try:
            print pvoutput.add_status(status_date, status_time, energy, power, voltage, False)
        except Exception, e:
            print "Could not add PVOutput status:", e

    time.sleep(10.0)

    if energy is not None:
        try:
            print pvoutput.add_output(status_date, energy)
        except Exception, e:
            print "Could not add PVOutput output:", e

    t = datetime.datetime.now() + datetime.timedelta(minutes=5)
    next_minutes = int(math.floor(t.minute / 5) * 5)
    t = t.replace(minute=next_minutes, second=0)
    scheduler.enterabs(time.mktime(t.timetuple()), 1, loop, (stack,))

    if t.hour == 0:
        stack.reset()

    sys.stdout.flush()

if __name__ == '__main__':
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']
    for port in ports:
        try:
            ser = serial.Serial(port, 19200, timeout=0.5)
        except serial.SerialException:
            print "Port %s is not available" % port
            pass
        else:
            break
    else:
        raise RuntimeError("No available serial ports")
    pvi1 = PVInverter(15, ser)
    pvi2 = PVInverter(3, ser)
    pvi3 = PVInverter(13, ser)
    stack = PVStack([pvi1, pvi2, pvi3])

    loop(stack)
    scheduler.run()
