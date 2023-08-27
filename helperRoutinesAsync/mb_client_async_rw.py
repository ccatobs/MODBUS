#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asynchronous MODBUS Reader & Writer
version {0}

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

import json
import sys
from timeit import default_timer as timer
import argparse
import asyncio
import os
# internal
if os.environ.get('PYTHONPATH') is None:
    sys.path.append("{0}{1}".format(
        os.path.dirname(os.path.realpath(__file__)),
        "/../"))
from modbusClientAsync import MODBUSClientAsync, MyException
from modbusClientAsync import __version__

print(__doc__.format(__version__))


async def main():
    """
test writer module with, e.g.
python3 mb_client_rw_async.py
--ip 127.0.0.40
--port 5020
--payload "{
\"decode_16bit_int_4\": 720.04,
\"decode_8bit_int_4\": 7,
\"decode_string_1_4\": \"abd \",
\"decode_string_1h\": \"Cd\",
\"decode_string_fullh\": \"xy\",
\"Dummy_4\": [1,0,0,1,0,0,0,1,1,1,0,1,0,1,0,1]
}"
    """
    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Client Reader & Writer")
    argparser.add_argument('--host',
                           required=True,
                           help='MODBUS Server Device IP/Name',
                           type=str
                           )
    argparser.add_argument('--port',
                           required=False,
                           help='MODBUS Server Port (default: 502)',
                           type=int
                           )
    argparser.add_argument('--debug',
                           required=False,
                           help='Debug Mode (default: False)',
                           action="store_true"
                           )
    argparser.add_argument('--timeout_connect',
                           required=False,
                           help='Timeout Connect (default: 3 [sec])',
                           type=float
                           )
    argparser.add_argument('--payload',
                           required=False,
                           help="Payload ('{parameter1: value1, "
                                "parameter2: value2, ...}')"
                           )

    _start_time = timer()
    try:
        mb_client = MODBUSClientAsync(
            host=argparser.parse_args().host,
            port=argparser.parse_args().port,
            debug=argparser.parse_args().debug,
            timeout_connect=argparser.parse_args().timeout_connect
        )
        if argparser.parse_args().payload:
            print(json.dumps(await mb_client.write_register(
                json.loads(argparser.parse_args().payload)),
                             indent=2))
        else:
            print(json.dumps(await mb_client.read_register(),
                             indent=2))
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)
    print("Time consumed to process MODBUS interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    sys.exit(0)


if __name__ == '__main__':
    asyncio.run(main())
