"""
Python wrapper for getting data from Thermie Genesis heatpump using Modbus TCP
"""
import logging

import datetime
import asyncio
import traceback

from time import sleep

from datetime import timedelta
from operator import itemgetter, attrgetter
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

    def __init__(self, host, port=502, kind='inverter', delay=0.1, max_registers=16):
        """Initialize."""

        self.data = {}
        self._client = ModbusClient(host, port=port, unit_id=1, auto_open=True)
        self.firmware = None
        if(kind == MODEL_MEGA): self.model = "Mega"
        else: self.model = "Diplomat Inverter"
        self._host = host
        self._port = port
        self._kind = kind
        self._delay = delay
        self.MAX_REGISTERS = max_registers

        _LOGGER.debug("Using host: %s:%d", host, port)

    async def async_set(self, register, value):  # pylint:disable=too-many-branches
        """Write data to heat pump."""
        ret_value = await self._set_data(register, value)
        self._client.close()

    async def async_update(self, register_types=REG_TYPES, only_registers = None):  # pylint:disable=too-many-branches
        """Update data from heat pump."""
        use_registers = []
        if(only_registers != None):
            #Make sure to sort registers by type and address
            use_registers = sorted(only_registers, key=(lambda x: f"{REGISTERS[x][KEY_REG_TYPE]}-{REGISTERS[x][KEY_ADDRESS]:03}"))
        else:
            use_registers = dict(filter(lambda x: x[1][self._kind], REGISTERS.items())).keys()

        raw_data = await self._get_data(use_registers)
        self._client.close()

        if not raw_data:
            #self.data = {}
            return

        #_LOGGER.debug("RAW data: %s", raw_data)
        #data = {}
        try:
            for i, (name, val) in enumerate(raw_data.items()):
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
        await asyncio.sleep(self._delay)
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


    async def _get_data(self, registers):
        """Retreive data from heat pump."""
        raw_data = {}
        #Split into requests that reads up to self.MAX_REGISTERS within REGISTER_RANGES (register blocks) for the requested registers
        first_chunk_address = 0
        current_type = None
        chunks = []
        chunk = None
        for name in registers:
            meta = REGISTERS[name]

            if(name == ATTR_HOLDING_FIXED_SYSTEM_SUPPLY_SET_POINT):
                #This will give an errror unless coil 42 is True, so skip if we don't know this or if it's false
                enableAttr = ATTR_COIL_ENABLE_FIXED_SYSTEM_SUPPLY_SET_POINT
                if(enableAttr not in raw_data and enableAttr not in self.data): 
                    _LOGGER.debug(f"Will not read {name} since we don't know if {ATTR_COIL_ENABLE_FIXED_SYSTEM_SUPPLY_SET_POINT} is set, include this register in the request to read this")
                    continue
                if(not raw_data[ATTR_COIL_ENABLE_FIXED_SYSTEM_SUPPLY_SET_POINT] and not self.data[ATTR_COIL_ENABLE_FIXED_SYSTEM_SUPPLY_SET_POINT]):
                    _LOGGER.debug(f"Will not read {name} since {ATTR_COIL_ENABLE_FIXED_SYSTEM_SUPPLY_SET_POINT} is False which disables this register")
                    continue

            reg_address = meta[KEY_ADDRESS]
            if(chunk == None #First iteration
                    or chunk[KEY_REG_TYPE] != meta[KEY_REG_TYPE] #New register type
                    or (reg_address - chunk['start']) >= self.MAX_REGISTERS #Exceeds max number of registers per request
                    or reg_address > chunk['range_end']): #Address belongs to another register block
                if(chunk != None):
                    chunks.append(chunk)
                start = meta[KEY_ADDRESS]
                chunk = { KEY_REG_TYPE: meta[KEY_REG_TYPE], 'start': start, 'slots': { name: 0 } }

                if(meta[KEY_DATATYPE] == TYPE_LONG): 
                    chunk['end'] = start + 1
                else: 
                    chunk['end'] = start

                in_range = list(filter(lambda x: x[0] <= start and x[1] >= start, REGISTER_RANGES[self._kind][meta[KEY_REG_TYPE]]))
                chunk['range_end'] = in_range[0][1]

            else:
                chunk['slots'][name] = reg_address - start
                if(meta[KEY_DATATYPE] == TYPE_LONG):
                    chunk['end'] = reg_address + 1
                else:
                    chunk['end'] = reg_address
        if(chunk != None): chunks.append(chunk)
        _LOGGER.info(f"Will make {len(chunks)} requests to read {len(registers)} registers")
        #print(f"Will make {len(chunks)} requests to read {len(registers)} registers")

        try:
            for chunk in chunks:
                await asyncio.sleep(self._delay)
                start_address = chunk['start']
                length = chunk['end'] - chunk['start'] + 1
                #Insert 0 if there is a gap
                regtype = chunk[KEY_REG_TYPE]
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
                    for i, (name, address) in enumerate(chunk['slots'].items()):
                        info = REGISTERS[name]
                        datatype = info[KEY_DATATYPE]
                        scale = info[KEY_SCALE]
                        val = read_data[address]
                        if(datatype == TYPE_LONG):
                            regs = read_data[address:(address+2)]
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
                        raw_data[name] = val
                else:
                    if self._client.last_error() > 0:
                        _LOGGER.error(f'error {self._client.last_error()}')
                    raise Exception(f"Failed to read {regtype} {start_address} length {length}", self._client.last_error())
            #for regtype in register_types:
            #    last_chunk_address = 0
            #    values = []
            #    for chunk in REGISTER_RANGES[self._kind][regtype]:
            #        await asyncio.sleep(self._delay)
            #        start_address = chunk[0]
            #        length = chunk[1] - start_address
            #        #Insert 0 if there is a gap
            #        values.extend([0] * (start_address - last_chunk_address))
            #        _LOGGER.debug(f"Reading {regtype} {start_address} length {length}")
            #        read_data = None
            #        if(regtype == REG_COIL):
            #            read_data = self._client.read_coils(start_address, length)
            #        elif(regtype == REG_DISCRETE_INPUT):
            #            read_data = self._client.read_discrete_inputs(start_address, length)
            #        elif(regtype == REG_INPUT):
            #            read_data = self._client.read_input_registers(start_address, length)
            #        elif(regtype == REG_HOLDING):
            #            read_data = self._client.read_holding_registers(start_address, length)
            #        if read_data:
            #            values.extend(read_data)
            #        else:
            #            if self._client.last_error() > 0:
            #                print(f'error {self._client.last_error()}')
            #                _LOGGER.error(f'error {self._client.last_error()}')
            #            raise Exception(f"Failed to read {regtype} {start_address} length {length}", self._client.last_error())
            #        last_chunk_address = chunk[1]
            #    raw_data[regtype] = values
        except Exception as e:
            _LOGGER.error(f'exception: {e}')
            print(traceback.format_exc())

        return raw_data
