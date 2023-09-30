#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MODBUS Reader & Writer
version {0}

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

import json
import sys
from timeit import default_timer as timer
import argparse
import os
import asyncio
import logging
# internal
if os.environ.get('PYTHONPATH') is None:
    sys.path.append("{0}{1}".format(
        os.path.dirname(os.path.realpath(__file__)),
        "/../"))
from modbusClientSync import MODBUSClientSync, MyException, __version__
from modbusClientAsync import MODBUSClientAsync

'''
test writer module with, e.g.
python3 mb_client_readwrite.py
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
'''
print(__doc__.format(__version__))

myformat = ("%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - "
            "%(lineno)s - %(funcName)s()\t%(message)s")
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

argparser = argparse.ArgumentParser(
    description="Universal MODBUS Client Reader & Writer"
)
argparser.add_argument(
    '--host',
    required=True,
    help='MODBUS Server Device IP/Name',
    type=str
)
argparser.add_argument(
    '--port',
    required=False,
    help='MODBUS Server Port (default: 502)',
    type=int
)
argparser.add_argument(
    '--debug',
    required=False,
    help='Debug Mode (default: False)',
    action="store_true"
)
argparser.add_argument(
    '--timeout_connect',
    required=False,
    help='Timeout Connect (default: 3 [sec])',
    type=float
)
argparser.add_argument(
    '--payload',
    required=False,
    help="Payload ('{parameter1: value1, parameter2: value2, ...}')"
)
argparser.add_argument(
    '--async_reader',
    required=False,
    help='Asynchronous Reader (default: False)',
    action="store_true"
)
argparser.add_argument(
    '--config_filename',
    required=False,
    default=None,
    help="Path to alternative config file"
)
args = argparser.parse_args()


async def async_main():
    try:
        mb_client = MODBUSClientAsync(
            host=args.host,
            port=args.port,
            debug=args.debug,
            timeout_connect=args.timeout_connect,
            config_filename=args.config_filename
        )
        if args.payload:
            print(json.dumps(await mb_client.write_register(
                json.loads(args.payload)),
                             indent=2))
        else:
            print(json.dumps(await mb_client.read_register(),
                             indent=2))
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)
    sys.exit(0)


def sync_main():
    if args.timeout_connect:
        logging.warning("The 'timeout_connect' option has no effect on the "
                        "syncronous reader")
    try:
        mb_client = MODBUSClientSync(
            host=args.host,
            port=args.port,
            debug=args.debug,
            config_filename=args.config_filename
        )
        if args.payload:
            print(json.dumps(mb_client.write_register(json.loads(args.payload)),
                             indent=2))
        else:
            print(json.dumps(mb_client.read_register(),
                             indent=2))
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    _start_time = timer()
    if args.async_reader:
        asyncio.run(async_main())
    else:
        sync_main()
    print("Time consumed to process MODBUS interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1_000)
    )
