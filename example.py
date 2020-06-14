import asyncio
import logging
from sys import argv

from pythermiagenesis import ThermiaGenesis
from pythermiagenesis.const import REGISTERS, REG_INPUT, KEY_ADDRESS

# heatpum IP address/hostname
HOST = "10.0.20.8"
PORT = 502
logging.basicConfig(level=logging.INFO)


async def main():
    host = argv[1] if len(argv) > 1 else HOST
    port = argv[2] if len(argv) > 2 else PORT
    kind = argv[3] if len(argv) > 3 else "inverter"

    # argument kind: inverter - for Diplomat Inverter
    #                mega     - for Mega
    thermia = ThermiaGenesis(host, port=port, kind=kind)
    try:
        await thermia.async_update() #Get all register types
        #await thermia.async_update([REG_INPUT]) #Get only input registers
    except (ConnectionError) as error:
        print(f"{error}")
        return

    if thermia.available:
        print(f"Data available: {thermia.available}")
        print(f"Model: {thermia.model}")
        print(f"Firmware: {thermia.firmware}")
        for i, (name, val) in enumerate(thermia.data.items()):
            print(f"{REGISTERS[name][KEY_ADDRESS]}\t{val}\t{name}")

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()
