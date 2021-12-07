import asyncio
import logging
from sys import argv

from pythermiagenesis import ThermiaGenesis
from pythermiagenesis import ThermiaConnectionError
from pythermiagenesis.const import (
        REGISTERS, 
        REG_INPUT, 
        KEY_ADDRESS, 
        ATTR_COIL_ENABLE_HEAT, 
        ATTR_COIL_ENABLE_BRINE_IN_MONITORING, 
        )

# heatpum IP address/hostname
HOST = "10.0.20.8"
PORT = 502
logging.basicConfig(level=logging.DEBUG)
#logging.basicConfig(level=logging.INFO)


async def main():
    host = argv[1] if len(argv) > 1 else HOST
    port = argv[2] if len(argv) > 2 else PORT
    kind = argv[3] if len(argv) > 3 else "inverter"

    # argument kind: inverter - for Diplomat Inverter
    #                mega     - for Mega
    thermia = ThermiaGenesis(host, port=port, kind=kind, delay=0.15)
    try:
        #Get all register types
        #await thermia.async_update()
        #Get only input registers
        #await thermia.async_update([REG_INPUT])
        #Get one specific register
        #await thermia.async_update(only_registers=[ATTR_COIL_ENABLE_BRINE_IN_MONITORING, ATTR_COIL_ENABLE_HEAT])
        await thermia.async_update([])

    except (ThermiaConnectionError) as error:
        print(f"Failed to connect: {error.message}")
        return
    except (ConnectionError) as error:
        print(f"Connection error {error}")
        return

    if thermia.available:
        print(f"Data available: {thermia.available}")
        print(f"Model: {thermia.model}")
        print(f"Firmware: {thermia.firmware}")
        for i, (name, val) in enumerate(thermia.data.items()):
            print(f"{REGISTERS[name][KEY_ADDRESS]}\t{name}\t{val}")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
