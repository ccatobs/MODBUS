#!/usr/bin/env python3
"""
MODBUS WRITER
version 2.0 - 2023/02/24

For a detailed description, see https://github.com/ccatp/MODBUS

python3 mb_client_writer_v2.py --device <device extention> (default: default) /
                               --path <path to config files>
                               --payload "{\"test 32 bit int\": 720.04}"

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

from modbusClient import MODBUSClient, MyException
import json
from timeit import default_timer as timer
import argparse
import sys

print(__doc__)


def main():

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Writer")
    argparser.add_argument('--device',
                           required=False,
                           help='Device extention (default: default)',
                           default='default'
                           )
    argparser.add_argument('--path',
                           required=False,
                           help='Path to config files (default: .)'
                           )
    argparser.add_argument('--payload',
                           required=True,
                           help="Payload ('{parameter: value}')"
                           )
    """
    test = {"test 32 bit int": 720.04,
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
    print("Device extention: {0}".format(argparser.parse_args().device))
    # print("payload: ", argparser.parse_args().payload)
    try:
        mb_client = MODBUSClient(
            device=argparser.parse_args().device,
            path_additional=argparser.parse_args().path
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
