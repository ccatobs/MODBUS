#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SYNCHRONOUS MODBUS REST API
version {0}

Web API to serve the read and write methods of the MODBUSClient class.
Implements a locking mechanism for each
device, such that reader and writer can not be invoked simulaneously.
"""

import logging
import os
from enum import Enum
from typing import Dict

import click
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Path, status
from fastapi.responses import JSONResponse

from .config.config import settings
from .mb_client_aux_sync import LockGroup, MyException
from .mb_client_sync import MODBUSClientSync, __version__

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

log_format = (
    "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - "
    "%(lineno)s - %(funcName)s()\t%(message)s"
)

log_level = logging.INFO
if settings.LOG_LEVEL == "DEBUG":
    log_level = logging.DEBUG
logging.basicConfig(format=log_format, level=log_level, datefmt="%Y-%m-%d %H:%M:%S")


lock_mb_client = LockGroup()
CLIENTS = dict()

app = FastAPI(
    title="MODBUS API",
    version=__version__,
    description="Connects with MODBUS devices. Enables to read/write from/to "
    "MODBUS registers. Register mappings to parameters are defined "
    "in config files available in modbusClient/configFiles.",
)


def mb_clients(host: str) -> MODBUSClientSync:
    """
    Helper to store MODBUSClient instances over the entire time the RestAPI is
    running once it was called the first time
    :param host: device ip or name
    :return: MODBUSClient instance each device
    """
    if host not in CLIENTS:
        CLIENTS[host] = MODBUSClientSync(
            host=host,
            port=settings.PORT,  # from environment variable
            debug=settings.DEBUG,  # from environment variable
            config_filename=settings.MODBUS_CLIENTS[host],
        )

    return CLIENTS[host]


@app.get(
    "/modbus/hosts",
    summary="List all host names for present device class",
    tags=["monitoring"],
)
async def read_hosts():
    return JSONResponse([ip for ip in settings.MODBUS_CLIENTS.keys()])


@app.get(
    "/modbus/read/{host}",
    summary="List values of all registers for MODBUS Device IP/Name",
    tags=["monitoring", "operations"],
)
async def read_register(host: str):
    try:
        lock_mb_client(host).acquire()
        return JSONResponse(mb_clients(host).read_register_bulk())
    except MyException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    finally:
        lock_mb_client(host).release()


@app.put(
    "/modbus/write/{host}",
    summary="Write values to register(s) for MODBUS Device IP/Name",
    tags=["operations"],
)
async def write_register(
    payload: Dict = Body(
        title="Payload", description="Data to be written into registers"
    ),
    host: str = Path(..., title="Device IP", description="Device IP"),
):
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Empty request body, nothing to show!",
        )
    try:
        lock_mb_client(host).acquire()
        return JSONResponse(mb_clients(host=host).write_register(wr=payload))
    except MyException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    finally:
        lock_mb_client(host).release()


@app.on_event("shutdown")
def shutdown_event():
    for ip, mb_client in CLIENTS.items():
        logging.info("Closing client for device extention: {}".format(ip))
        mb_client.close()


@click.command()
@click.option(
    "--host",
    default="127.0.0.1",
    type=str,
    help='IP address for REST API (default: "127.0.0.1")',
)
@click.option("--port", default=5100, type=int, help="Port (default: 5100)")
def main(host, port):
    """Rest API for MODBUS client"""
    logging.info("PID: %s", os.getpid())
    logging.info("Host: %s, Port: %s", host, port)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
