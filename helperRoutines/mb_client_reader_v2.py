#!/usr/bin/env python3

"""
MODBUS READER
version 2.0 - 2023/02/24

For a detailed description, see https://github.com/ccatp/MODBUS

python3 mb_client_reader_v2.py --device <device extention> (default: default) \
                               --path <path to config files>

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann, Argelander Institute for
Astronomy (AIfA), University Bonn.
"""

import json
from timeit import default_timer as timer
import argparse
from modbusClient import MODBUSClient

print(__doc__)


def main():

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Client Reader")
    argparser.add_argument('--device',
                           required=False,
                           help='Device extentions (default: default)',
                           default='default'
                           )
    argparser.add_argument('--path',
                           required=False,
                           help='Path to config files (default: .)'
                           )

    _start_time = timer()
    print("Device extention: {0}".format(argparser.parse_args().device))
    try:
        mb_client = MODBUSClient(device=argparser.parse_args().device,
                                 path_additional=argparser.parse_args().path)
        to_housekeeping = mb_client.read_register()
        mb_client.close()
    except SystemExit as e:
        exit("Error code {0}".format(e))
    print(json.dumps(to_housekeeping,
                     indent=4))
    print("Time consumed to process modbus interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    exit(0)


if __name__ == '__main__':
    main()
