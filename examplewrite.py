import asyncio
import logging
from sys import argv

from pythermiagenesis import ThermiaGenesis
from pythermiagenesis.const import ATTR_COIL_ENABLE_TAP_WATER, ATTR_HOLDING_EXTERNAL_ADDITIONAL_HEATER_START, ATTR_HOLDING_COMFORT_WHEEL_SETTING

# printer IP address/hostname
HOST = "10.0.20.8"
PORT = 502
logging.basicConfig(level=logging.DEBUG)


async def main():
    host = argv[1] if len(argv) > 1 else HOST
    port = argv[2] if len(argv) > 2 else PORT
    kind = argv[3] if len(argv) > 3 else "inverter"

    # argument kind: inverter - for Diplomat Inverter
    #                mega     - for Mega
    thermia = ThermiaGenesis(host, port=port, kind=kind)
    try:
        await thermia.async_set(ATTR_HOLDING_COMFORT_WHEEL_SETTING, 21.0)
        #await thermia.async_set(ATTR_COIL_ENABLE_TAP_WATER, False)
        #await thermia.async_set(ATTR_COIL_ENABLE_TAP_WATER, True)
        #await thermia.async_set(ATTR_HOLDING_EXTERNAL_ADDITIONAL_HEATER_START, -5)
    except (ConnectionError) as error:
        print(f"{error}")
        return

    if thermia.available:
        print(f"Data available: {thermia.available}")
        print(f"Model: {thermia.model}")
        print(f"Firmware: {thermia.firmware}")
        print(f"Sensors data: {thermia.data}")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()

