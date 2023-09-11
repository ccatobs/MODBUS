#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Synchronous MODBUS Reader
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
from modbusClientSync import MODBUSClientSync, MyException
from modbusClientSync import __version__

print(__doc__.format(__version__))


def main():

    argparser = argparse.ArgumentParser(
        description="Universal MODBUS Client Reader")
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
    argparser.add_argument('--config_filename',
                           required=False,
                           default="",
                           help='path to config file'
                           )
    argparser.add_argument('--bulk_read',
                           default=False,
                           action="store_true",
                           help='toggle bulk read default: False'
                           )    
    _start_time = timer()
    args = argparser.parse_args()
    try:
        mb_client = MODBUSClientSync(
            host=args.host,
            port=args.port,
            debug=args.debug,
            config_filename=args.config_filename
        )
        if args.bulk_read:
            to_housekeeping = mb_client.read_register_bulk()
        else:
            to_housekeeping = mb_client.read_register()
        mb_client.close()
    except MyException as e:
        print("Code={0}, detail={1}".format(e.status_code,
                                            e.detail))
        sys.exit(1)
    print(json.dumps(to_housekeeping,
                     indent=2))
    print("Time consumed to process MODBUS interface: {0:.1f} ms".format(
        (timer() - _start_time) * 1000)
    )

    sys.exit(0)


if __name__ == '__main__':
    main()
