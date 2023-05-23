#!/usr/bin/env python3

"""
mb_client_RestAPI.py

Web API to serve the read and write methods of the MODBUSClient class.
Implements a locking mechanism for each
device, such that reader and writer can not be invoked simulaneously.
"""

from fastapi import HTTPException, status, FastAPI, Path, Body
from fastapi.responses import JSONResponse
import logging
import argparse
import os
import uvicorn
from typing import Dict
import glob
import re
from enum import Enum
# internal
from modbusClient import MODBUSClient, LockGroup
from modbusClient import __version__

"""
version history:
2023/03/04 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.0
2023/03/08 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.1
    * lock release in try-finally
2023/05/20 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.2
    * Predefined enumeration values for devices as fetched from configFiles
henceforth version history of modbusClient adopted
"""

print(__doc__)

app = FastAPI(
    title="MODBUS API",
    version=__version__,
    description="Connects with the MODBUS devices. Mappings of MODBUS "
                "registers are defined in config files as found "
                "in modbusClient/configFiles."
)
lock_mb_client = LockGroup()
clients = dict()
devices = dict()

path_additional = "{0}{1}".format(
    os.path.dirname(os.path.realpath(__file__)),
    "/../modbusClient/configFiles"
)
for txt in glob.glob1(path_additional,
                      "mb_client_config_*.json"):
    d = re.findall(r'mb_client_config_(.+?).json', txt)[0]
    devices[d] = d
DevicesEnum = Enum("DevicesEnum", devices)


def mb_clients(device: str) -> MODBUSClient:
    """
    Helper to store MODBUSClient instances over the entire time the RestAPI is
    running once it was called the first time
    :param device
    :return: MODBUSClient instance for each device
    """
    if device not in clients:
        clients[device] = MODBUSClient(
            device=device,
            path_additional=path_additional
        )

    return clients[device]


@app.get("/modbus/read/{device}",
         summary="List values of all registers for MODBUS "
                 "device <device_extention>")
async def read_register(
        device: DevicesEnum = Path(title="Device Extention",
                                   description="Device Extention")
):
    try:
        lock_mb_client(device).acquire()
        return JSONResponse(
            mb_clients(device=device.value).read_register()
        )
    except SystemExit as e:
        raise HTTPException(status_code=e.code)
    finally:
        lock_mb_client(device).release()


@app.post("/modbus/write/{device}",
          summary="Write values to one or multiple register(s) for "
                  "MODBUS device <device_extention>")
async def write_register(
        payload: Dict = Body(title="Payload",
                             description="Data to be written into registers"),
        device: DevicesEnum = Path(title="Device Extention",
                                   description="Device Extention")
):
    if not payload:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT,
                            detail="Empty payload")
    try:
        lock_mb_client(device).acquire()
        return JSONResponse(
            mb_clients(device=device.value).write_register(wr=payload)
        )
    except SystemExit as e:
        raise HTTPException(status_code=e.code)
    finally:
        lock_mb_client(device).release()


@app.on_event("shutdown")
def shutdown_event():
    for items, value in clients.items():
        logging.info("Closing client for device extenstion: {}".format(items))
        value.close()


def main():
    argparser = argparse.ArgumentParser(
        description="Rest API for MODBUS client")
    argparser.add_argument(
        '--host',
        required=False,
        help='IP address for REST API (default: "127.0.0.1")',
        default='127.0.0.1'
    )
    argparser.add_argument(
        '--port',
        required=False,
        type=int,
        help='Port (default: 5100)',
        default=5100
    )
    # for the time being we fetch all configurations from a predefined directory
    #    argparser.add_argument(
    #        '--path',
    #        required=False,
    #        type=str,
    #        help='Path to config files (default: /../configFiles)'
    #    )
    #    path_additional = argparser.parse_args().path

    logging.info("PID: {0}".format(os.getpid()))
    logging.info("Host: {0}, Port: {1}".format(
        argparser.parse_args().host,
        argparser.parse_args().port)
    )
    logging.info("Path to configFiles: {}".format(path_additional))

    uvicorn.run(app,
                host=argparser.parse_args().host,
                port=argparser.parse_args().port)


if __name__ == '__main__':
    main()
