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
from typing import Generator
import re
# internal
if os.environ.get('PYTHONPATH') is None:
    sys.path.append("{0}{1}".format(
        os.path.dirname(os.path.realpath(__file__)),
        "/../"))
from modbusClientSync import MODBUSClientSync, MyException, __version__
from modbusClientAsync import MODBUSClientAsync

'''
test writer module with, e.g.
python3 mb_client_readwrite.py \
--ip 127.0.0.40 \
--port 5020 \
--async_mode \
--payload "{
\"decode_16bit_int_4\": 720.04,
\"decode_8bit_int_4\": 7,
\"decode_string_1_4\": \"abd \",
\"decode_string_1h\": \"Cd\",
\"decode_string_fullh\": \"xy\",
\"Dummy_4\": [1,0,0,1,0,0,0,1,1,1,0,1,0,1,0,1]}"
'''

print(__doc__.format(__version__))

myformat = ("%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - "
            "%(lineno)s - %(funcName)s()\t%(message)s")
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")


class Range(object):
    def __init__(self, scope: str):
        r = re.compile(
            r'^([\[\]]) *([-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][+-]?\d+)?) *'
            r', *([-+]?(?:\d*\.\d+|\d+\.?)(?:[Ee][+-]?\d+)?) *([\[\]])$'
        )
        try:
            i = re.findall(r, scope)[0]
            if float(i[1]) >= float(i[2]):
                raise ArithmeticError
        except (IndexError, ArithmeticError):
            raise SyntaxError("An error occurred with the range provided!")
        self.__st = '{}{}, {}{}'.format(*i)
        self.__lamba = "lambda item: {} {} item {} {}".format(
            i[1],
            {'[': '<=', ']': '<'}[i[0]],
            {']': '<=', '[': '<'}[i[3]],
            i[2]
        )
    def __eq__(self, item: float) -> bool: return eval(self.__lamba)(item)
    def __contains__(self, item: float) -> bool: return self.__eq__(item)
    def __iter__(self) -> Generator[object, None, None]: yield self
    def __str__(self) -> str: return self.__st
    def __repr__(self) -> str: return self.__str__()


argparser = argparse.ArgumentParser(
    description="Reader & Writer for An Universal (A)Synchronous MODBUS Client"
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
    type=float,
    choices=Range('[1, 10]')
)
argparser.add_argument(
    '--payload',
    required=False,
    help="Payload ('{parameter1: value1, parameter2: value2, ...}')"
)
argparser.add_argument(
    '--async_mode',
    required=False,
    help='Asynchronous Mode (default: Synchronous Mode)',
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
            print(json.dumps(
                await mb_client.write_register(json.loads(args.payload)),
                indent=2)
            )
        else:
            print(json.dumps(
                await mb_client.read_register(),
                indent=2)
            )
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)


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
            print(json.dumps(
                mb_client.write_register(json.loads(args.payload)),
                indent=2)
            )
        else:
            print(json.dumps(
                mb_client.read_register(),
                indent=2)
            )
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)


if __name__ == '__main__':
    _start_time = timer()
    if args.async_mode:
        asyncio.run(async_main())
    else:
        sync_main()
    print("Time consumed to process {1}ynchronous MODBUS interface: {0:.1f} ms"
          .format(
              (timer() - _start_time) * 1_000,
              "As" if args.async_mode else "S"))
    sys.exit(0)
