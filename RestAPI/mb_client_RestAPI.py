#!/usr/bin/env python3

"""
mb_client_RestAPI.py
version {0}

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
from distutils.util import strtobool
from enum import Enum
# internal
from modbusClient import MODBUSClient, LockGroup, MyException
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

print(__doc__.format(__version__))

ips = os.getenv("ServerIPS")
port = int(os.environ.get('ServerPort'))
debug = strtobool(os.environ.get('Debug'))

lock_mb_client = LockGroup()
clients = dict()


def _get_ips() -> Enum:
    devices = dict()
    for ip in ips.split(","):
        devices[ip] = ip.strip()
    return Enum("DeviceEnum", devices)


DeviceEnum = _get_ips()


app = FastAPI(
    title="MODBUS API",
    version=__version__,
    description="Connects with MODBUS devices. Enables to read/write from/to "
                "MODBUS registers. Register mappings to parameters are defined "
                "in config files available in modbusClient/configFiles."
)


def mb_clients(ip: str) -> MODBUSClient:
    """
    Helper to store MODBUSClient instances over the entire time the RestAPI is
    running once it was called the first time
    :param ip: device ip
    :return: MODBUSClient instance each device
    """
    if ip not in clients:
        clients[ip] = MODBUSClient(
            ip=ip,
            port=port,  # from environment variable
            debug=debug  # from environment variable
        )

    return clients[ip]


@app.get("/modbus/read/{device_ip}",
         summary="List values of all registers for MODBUS Device IP")
async def read_register(
        device_ip: DeviceEnum = Path(title="Device IP",
                                     description="Device IP")
):
    try:
        lock_mb_client(device_ip.value).acquire()
        return JSONResponse(
            mb_clients(
                ip=device_ip.value
            ).read_register()
        )
    except MyException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    finally:
        lock_mb_client(device_ip.value).release()


@app.put("/modbus/write/{device_ip}",
         summary="Write values to register(s) for MODBUS Device IP")
async def write_register(
        payload: Dict = Body(title="Payload",
                             description="Data to be written into registers"),
        device_ip: DeviceEnum = Path(title="Device IP",
                                     description="Device IP")
):
    if not payload:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Empty payload")
    try:
        lock_mb_client(device_ip.value).acquire()
        return JSONResponse(
            mb_clients(
                ip=device_ip.value
            ).write_register(wr=payload)
        )
    except MyException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )
    finally:
        lock_mb_client(device_ip.value).release()


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

    logging.info("PID: {0}".format(os.getpid()))
    logging.info("Host: {0}, Port: {1}".format(
        argparser.parse_args().host,
        argparser.parse_args().port)
    )

    uvicorn.run(app,
                host=argparser.parse_args().host,
                port=argparser.parse_args().port)


if __name__ == '__main__':
    main()
