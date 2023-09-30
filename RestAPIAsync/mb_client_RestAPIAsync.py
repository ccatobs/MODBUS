#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
mb_client_RestAPI.py
version {0}

Web API to serve the read and write methods of the MODBUSClient class.
"""

from fastapi import HTTPException, FastAPI, Path, Body
from fastapi.responses import JSONResponse
import logging
import argparse
import os
import uvicorn
from typing import Dict
from distutils.util import strtobool
from enum import Enum
from typing import Annotated
# internal
from modbusClientAsync import MODBUSClientAsync, MyException, __version__

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

hosts = os.getenv("ServerHost")
port = int(os.environ.get('ServerPort'))
debug = strtobool(os.environ.get('Debug')) \
    if os.environ.get('Debug') else None
timeout_connect = float(os.environ.get('TimeoutConnect')) \
    if os.environ.get('TimeoutConnect') else None

clients: Dict = dict()
DeviceEnum = Enum(
    "DeviceEnum",
    {host.strip(): host.strip() for host in hosts.split(",")}
)
app = FastAPI(
    title="MODBUS API",
    version=__version__,
    description="Connects with MODBUS devices. Enables to read/write from/to "
                "MODBUS registers. Register mappings to parameters are defined "
                "in config files available in modbusClient/configFiles."
)


def mb_clients(host: str) -> MODBUSClientAsync:
    """
    Helper to store MODBUSClient instances over the entire time the RestAPI is
    running once it was called the first time
    :param host: device ip or name
    :return: MODBUSClient instance each device
    """
    if host not in clients:
        clients[host] = MODBUSClientAsync(
            host=host,
            port=port,  # from environment variable
            debug=debug,  # from environment variable
            timeout_connect=timeout_connect  # from environment variable
        )

    return clients[host]


@app.get(
    "/modbus/hosts",
    summary="List all host names for present device class",
    tags=["monitoring"]
)
async def read_hosts() -> JSONResponse:
    return JSONResponse([e.value for e in DeviceEnum])


@app.get(
    "/modbus/read/{host}",
    summary="List values of all registers for MODBUS Device IP/Name",
    tags=["monitoring", "operations"]
)
async def read_register(
        host: Annotated[DeviceEnum, Path(
            title="Device IP",
            description="Device IP",
            # enum = [e for e in DeviceEnum if len(DeviceEnum) == 1]
        )
        ]
) -> JSONResponse:
    """enabling enum as option:
    in case there's only one enum element, this would show up in the dropdown
    list of openapi's doc#, whilst it'd stay empty at all (bug in openapi)"""
    try:
        return JSONResponse(
            await mb_clients(host=host.value).read_register()
        )
    except MyException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )


@app.put(
    "/modbus/write/{host}",
    summary="Write values to register(s) for MODBUS Device IP/Name",
    tags=["operations"]
)
async def write_register(
        payload: Annotated[Dict, Body(
            title="Payload",
            description="Data to be written into registers")
        ],
        host: Annotated[DeviceEnum, Path(
            title="Device IP",
            description="Device IP")
        ]
) -> JSONResponse:
    try:
        return JSONResponse(
            await mb_clients(host=host.value).write_register(wr=payload)
        )
    except MyException as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.detail
        )


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
