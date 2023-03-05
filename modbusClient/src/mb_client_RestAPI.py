#!/usr/bin/env python3
"""
here comes docu!
"""
from fastapi import HTTPException, status, FastAPI, Path, Body
from fastapi.responses import JSONResponse
import logging
import argparse
import os
import uvicorn
from typing import Dict
# internal
from mb_client_v2 import MODBUSClient
from mb_client_aux import LockGroup

"""
version history:
2023/03/04 - Ralf A. Timmermann
- version 1.0
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, University Bonn"
__credits__ = ""
__license__ = "BSD"
__version__ = "0.1"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

print(__doc__)

lock_mb_client = LockGroup()
app = FastAPI()
clients = dict()


def mb_clients(device: str) -> MODBUSClient:
    if device not in clients:
        clients[device] = MODBUSClient(device=device,
                                       path_additional="../configFiles")
    return clients[device]


@app.get("/modbus/read/{device}",
         summary="List values of all registers for MODBUS device <device_extention>")
async def read_register(device: str = Path(title="Device Extention",
                                           description="Device Extention")):
    try:
        lock_mb_client(device).acquire()
        result = mb_clients(device=device).read_register()
        lock_mb_client(device).release()
        return JSONResponse(result)
    except SystemExit as e:
        raise HTTPException(status_code=e.code)


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
        mb_clients(device=device).write_register(wr=payload)
        lock_mb_client(device).release()
        return JSONResponse(payload)
    except SystemExit as e:
        raise HTTPException(status_code=e.code)


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

    logging.info("PID: {0}".format(os.getpid()))
    logging.info("Host: {0}, Port: {1}".format(
        argparser.parse_args().host,
        argparser.parse_args().port)
    )

    uvicorn.run(app,
                host=argparser.parse_args().host,
                port=argparser.parse_args().port)
