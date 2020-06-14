"""
Python wrapper for getting data from Thermie Genesis heatpump using Modbus TCP
"""
import logging

import datetime
import asyncio
import traceback

from time import sleep

from datetime import timedelta
import logging

from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import *

from .const import *
from struct import unpack

_LOGGER = logging.getLogger(__name__)



def num_to_bin(value):
    if(value > -1): return value
    return 65536 + value

class ThermiaGenesis:  # pylint:disable=too-many-instance-attributes
    """Main class to perform modbus requests to heat pump."""

    def __init__(self, host, port=502, kind='inverter'):
        """Initialize."""

        self.data = {}
        self._client = ModbusClient(host, port=port, unit_id=1, auto_open=True)
        self.firmware = None
        if(kind == MODEL_MEGA): self.model = "Mega"
        else: self.model = "Diplomat Inverter"
        self._host = host
        self._port = port
        self._kind = kind

        _LOGGER.debug("Using host: %s:%d", host, port)

    async def async_set(self, register, value):  # pylint:disable=too-many-branches
        """Write data to heat pump."""
        ret_value = await self._set_data(register, value)

    async def async_update(self, register_types=REG_TYPES):  # pylint:disable=too-many-branches
        """Update data from heat pump."""
        raw_data = await self._get_data(register_types)

        if not raw_data:
            #self.data = {}
            return

        #_LOGGER.debug("RAW data: %s", raw_data)
        model = self._kind
        #data = {}
        i = 0
        last_address = -1
        try:
            for i, (name, info) in enumerate(REGISTERS.items()):
                if(not info[model]): continue
                address = info[KEY_ADDRESS]
                regtype = info[KEY_REG_TYPE]
                if(regtype not in register_types): continue
                datatype = info[KEY_DATATYPE]
                scale = info[KEY_SCALE]
                val = raw_data[regtype][address]
                if(datatype == TYPE_LONG):
                    regs = raw_data[regtype][address:(address+3)]
                    val = word_list_to_long(regs)[0]
                elif(datatype == TYPE_INT):
                    if(val == 32767): val = 0
                    if(val > 32767): val = val - 65536
                elif(datatype == TYPE_STATUS):
                    status_str = "OFF"
                    if val == 1:
                        status_str = "Manual Operation"
                    elif val == 2:
                        status_str = "Defrost"
                    elif val == 3:
                        status_str = "Hot water"
                    elif val == 4:
                        status_str = "Heat"
                    elif val == 5:
                        status_str = "Cool"
                    elif val == 6:
                        status_str = "Pool"
                    elif val == 7:
                        status_str = "Anti legionella"
                    elif val == 98:
                        status_str = "Standby"
                    elif val == 99:
                        status_str = "No demand"
                    val = status_str

                if(scale != 1): val = val / scale
                self.data[name] = val

            self.firmware = f"{self.data[ATTR_INPUT_SOFTWARE_VERSION_MAJOR]}.{self.data[ATTR_INPUT_SOFTWARE_VERSION_MINOR]}.{self.data[ATTR_INPUT_SOFTWARE_VERSION_MICRO]}"

            _LOGGER.debug("------------- REGISTERS ----------------------")
            for i, (name, val) in enumerate(self.data.items()):
                _LOGGER.debug(f"{REGISTERS[name][KEY_ADDRESS]}\t{val}\t{name}")


        except AttributeError as err:
            _LOGGER.debug("Incomplete data from modbus.")
            _LOGGER.debug(err)
        except KeyError as err: 
            _LOGGER.debug("Incomplete data from modbus.")
            _LOGGER.debug(err)
        except TypeError as err:
            _LOGGER.debug("Incomplete data from modbus.")
            _LOGGER.debug(err)
        #self.data = data

    @property
    def available(self):
        """Return True is data is available."""
        return bool(self.data)


    async def _set_data(self, register, value):
        meta = REGISTERS[register]
        regtype = meta[KEY_REG_TYPE]
        address = meta[KEY_ADDRESS]
        scale = meta[KEY_SCALE]
        try:
            if(regtype == REG_COIL):
                _LOGGER.debug(f"Set {regtype} register at {address} value {value} ({value})")
                self._client.write_single_coil(address, value)
            elif(regtype == REG_HOLDING):
                converted_value = int(value * scale)
                if(meta[KEY_DATATYPE] == TYPE_INT):
                    converted_value = num_to_bin(converted_value)
                _LOGGER.debug(f"Set {regtype} register at {address} value {converted_value} ({value}) {scale}")
                self._client.write_single_register(address, converted_value)
            else: 
                raise "This register can not be changed"
        except Exception as e:
            _LOGGER.error(f'exception: {e}')
            print(traceback.format_exc())
        return value


    async def _get_data(self, register_types):
        """Retreive data from heat pump."""
        raw_data = {}
        try:
            for regtype in register_types:
                last_chunk_address = 0
                values = []
                for chunk in REGISTER_RANGES[self._kind][regtype]:
                    start_address = chunk[0]
                    length = chunk[1] - start_address
                    #Insert 0 if there is a gap
                    values.extend([0] * (start_address - last_chunk_address))
                    _LOGGER.debug(f"Reading {regtype} {start_address} length {length}")
                    read_data = None
                    if(regtype == REG_COIL):
                        read_data = self._client.read_coils(start_address, length)
                    elif(regtype == REG_DISCRETE_INPUT):
                        read_data = self._client.read_discrete_inputs(start_address, length)
                    elif(regtype == REG_INPUT):
                        read_data = self._client.read_input_registers(start_address, length)
                    elif(regtype == REG_HOLDING):
                        read_data = self._client.read_holding_registers(start_address, length)
                    if read_data:
                        values.extend(read_data)
                    else:
                        if self._client.last_error() > 0:
                            print(f'error {self._client.last_error()}')
                            _LOGGER.error(f'error {self._client.last_error()}')
                        raise Exception(f"Failed to read {regtype} {start_address} length {length}", self._client.last_error())
                    last_chunk_address = chunk[1]
                raw_data[regtype] = values
        except Exception as e:
            _LOGGER.error(f'exception: {e}')
            print(traceback.format_exc())

        return raw_data
