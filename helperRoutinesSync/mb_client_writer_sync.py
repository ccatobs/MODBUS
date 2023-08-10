#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sychronous MODBUS Writer
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
from modbusClientSync import MODBUSClientSync, MyException
from modbusClientSync import __version__

print(__doc__.format(__version__))


def main():
    """
test with, e.g.
python3 mb_client_writer_v2.py
--ip 127.0.0.40
--port 5020
--payload "{\"decode_16bit_int_4\": 720.04, \"decode_8bit_int_4\": 7,
\"decode_string_1_4\": \"abd \", \"decode_string_1h\": \"Cd\",
\"decode_string_fullh\": \"xy\", \"Dummy_4\": [1,0,0,1,0,0,0,1,1,1,0,1,0,1,0,1]}"
    """
    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Writer")
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
                           default=False,
                           help='Debug Mode (default: False)',
                           action="store_true"
                           )
    argparser.add_argument('--payload',
                           required=True,
                           help="Payload ('{parameter1: value1, "
                                "parameter2: value2, ...}')"
                           )

    _start_time = timer()
    try:
        mb_client = MODBUSClientSync(
            host=argparser.parse_args().host,
            port=argparser.parse_args().port,
            debug=argparser.parse_args().debug
        )
        to_monitoring = mb_client.write_register(
            json.loads(argparser.parse_args().payload)
        )
        mb_client.close()
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)
    print(json.dumps(to_monitoring, indent=2))
    print("Time consumed to process the MODBUS writer: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    sys.exit(0)


if __name__ == '__main__':
    main()
