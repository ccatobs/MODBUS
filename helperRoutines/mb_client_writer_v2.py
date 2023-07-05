#!/usr/bin/env python3

"""
MODBUS WRITER
version {0}

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

import json
from timeit import default_timer as timer
import argparse
import sys
# internal
from modbusClient import MODBUSClient, MyException
from modbusClient import __version__

print(__doc__.format(__version__))


def main():

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Writer")
    argparser.add_argument('--ip',
                           required=True,
                           help='MODBUS Server Device IP'
                           )
    argparser.add_argument('--port',
                           required=False,
                           help='MODBUS Server Port (default: 502)'
                           )
    argparser.add_argument('--debug',
                           required=False,
                           default=False,
                           help='Debug Mode (default: False)'
                           )
    argparser.add_argument('--payload',
                           required=True,
                           help="Payload ('{parameter1: value1, "
                                "parameter2: value2, ...}')"
                           )
    """
    test = {"decode_16bit_int_4": 720.04,
            "write int register": 10,
            "string of register/1": "YZ",
            "Write bits/1": [
                True, True, True, False, True, False, True, False,
                True, False, True, False, True, False, False, False
            ],
            "Coil 0": True,
            "Coil 1": True,
            "Coil 10": True
            }
    """
    _start_time = timer()
    print("Device IP: {0}".format(argparser.parse_args().ip))
    try:
        mb_client = MODBUSClient(
            ip=argparser.parse_args().ip,
            port=argparser.parse_args().port,
            debug=argparser.parse_args().debug
        )
        to_monitoring = mb_client.write_register(
            json.loads(argparser.parse_args().payload)
        )
        mb_client.close()
    except MyException as e:
        print("Status code: {1}, Detail: {0}", e.detail, e.status_code)
        sys.exit(1)
    print(to_monitoring)
    print("Time consumed to process the modbus writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    sys.exit(0)


if __name__ == '__main__':
    main()
