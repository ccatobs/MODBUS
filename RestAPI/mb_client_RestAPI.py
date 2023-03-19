#!/usr/bin/env python3

"""
FastAPI to serve the read and write methods of the MODBUSClient class. Implements
a locking mechanism, such that reader and writer for each device can not be
invoked simulaneously.

"""
from fastapi import HTTPException, status, FastAPI, Path, Body
from fastapi.responses import JSONResponse
import logging
import argparse
import os
import uvicorn
from typing import Dict
# internal
from modbusClient import MODBUSClient
from modbusClient import LockGroup

"""
version history:
2023/03/04 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.0
2023/03/08 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.1
    * lock release in try-finally
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, University Bonn"
__credits__ = ""
__license__ = "BSD 3-Clause"
__version__ = "1.1"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "QA"

print(__doc__)

lock_mb_client = LockGroup()
app = FastAPI()
clients = dict()


def mb_clients(device: str, path_additional: str = '.') -> MODBUSClient:
    """
    Helper to store MODBUSClient instances over the entire time the RestAPI is
    running once it was called the first time
    :param device: str
    :param path_additional: str, path to ConfigFiles, default = '.'
    :return: MODBUSClient instance for each device
    """
    if device not in clients:
        clients[device] = MODBUSClient(device=device,
                                       path_additional=path_additional)
    return clients[device]


@app.get("/modbus/read/{device}",
         summary="List values of all registers for MODBUS device <device_extention>")
async def read_register(device: str = Path(title="Device Extention",
                                           description="Device Extention")):
    try:
        lock_mb_client(device).acquire()
        result = mb_clients(device=device, path_additional=path_additional).read_register()
        return JSONResponse(result)
    except SystemExit as e:
        raise HTTPException(status_code=e.code)
    finally:
        lock_mb_client(device).release()


@app.post("/modbus/write/{device}",
          summary="Write values to one or multiple register(s) for MODBUS device <device_extention>")
async def write_register(device: str = Path(title="Device Extention",
                                            description="Device Extention"),
                         payload: Dict = Body(title="Data",
                                              description="Data to be written into registers")
                         ):
    if not payload:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT,
                            detail="Empty payload")
    try:
        lock_mb_client(device).acquire()
        result = mb_clients(device=device, path_additional=path_additional).write_register(wr=payload)
        return JSONResponse(result)
    except SystemExit as e:
        raise HTTPException(status_code=e.code)
    finally:
        lock_mb_client(device).release()


@app.on_event("shutdown")
def shutdown_event():
    for items, value in clients.items():
        logging.info("Closing client for device extenstion: {}".format(items))
        value.close()


if __name__ == '__main__':
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
        help='Port (default: 5000)',
        default=5000
    )
    argparser.add_argument(
        '--path',
        required=False,
        type=str,
        help='Path to config files (default: /../configFiles)'
    )

    path_additional = argparser.parse_args().path

    logging.info("PID: {0}".format(os.getpid()))
    logging.info("Host: {0}, Port: {1}".format(
        argparser.parse_args().host,
        argparser.parse_args().port)
    )
    logging.info("Path to configFiles: {}".
                 format(path_additional if path_additional else "'default'"))

    uvicorn.run(app,
                host=argparser.parse_args().host,
                port=argparser.parse_args().port)
