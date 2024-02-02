# pythermiagenesis

A python library for Thermia Diplomat Inverter/Mega heatpumps.

This library communicates with the device using Modbus TCP.
Set BMC to Modbus TCP on your heat pump to enable communication through this library.

## documentation

Thermia Modbus TCP documentation: <https://www.tcmadmin.thermia.se/docroot/dokumentbank/Modbus%20protocol%20for%20Genesis%20platform%2010.pdf>

## notes

1. Be aware that some registers such for example "Compressor operating hours" will require a 32 bit read from two registers if the value is larger than 65535. This library does not handle this automatically, you will have to do this manually. This is explained in the manufacturer documentation.
