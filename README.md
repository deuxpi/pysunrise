# PySunrise

PySunrise is a Python library and associated scripts that are used to
communicate with Solectria Renewables PVI 3000-7500 solar grid-tied inverters.

## Features

* Queries cumulative output statistics and real-time data from the inverters.
* Sends live data to [PVOutput](http://pvoutput.org/).

## How it works

PySunrise uses the RS-485 port available on the inverters to send commands
using a modified Modbus protocol. It requires a custom cable to interface with
the computer that may be built according to the inverter documentation. This
typically involves a RS-232 to RS-485 adapter.

You can see live data at [PVOutput](http://pvoutput.org/intraday.jsp?sid=6360)
as an example of a solar inverter system using PySunrise to publish to
PVOutput.

## This is experimental software

This code as currently used on the system is a much simpler version that is
available from the `current` branch. However, this code is closely tied to my
own configuration and would be bothersome to adapt for any other system.

## Getting the source

The source code is available from the repository on
[GitHub](https://github.com/deuxpi/pysunrise).

PySunrise is available under the GPL v3 license.

Contact me at philippe.gauthier@deuxpi.ca.
