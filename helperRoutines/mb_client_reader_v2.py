#!/usr/bin/env python3

"""
MODBUS READER
version {0}

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

import json
import sys
from timeit import default_timer as timer
import argparse
# internal
from modbusClient import MODBUSClient, MyException
from modbusClient import __version__

print(__doc__.format(__version__))


def main():

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Client Reader")
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

    _start_time = timer()
    print("Device IP: {0}".format(argparser.parse_args().ip))
    try:
        mb_client = MODBUSClient(
            ip=argparser.parse_args().ip,
            port=argparser.parse_args().port,
            debug=argparser.parse_args().debug
        )
        to_housekeeping = mb_client.read_register()
        mb_client.close()
    except MyException as e:
        print("Code={}, detail={}".format(e.status_code,
                                          e.detail))
        sys.exit(1)
    print(json.dumps(to_housekeeping,
                     indent=4))
    print("Time consumed to process modbus interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    sys.exit(0)


if __name__ == '__main__':
    main()
