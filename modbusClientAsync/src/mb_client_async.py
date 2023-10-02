#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Asychronous MODBUS Client

For a detailed description, see https://github.com/ccatp/MODBUS

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann,
Argelander Institute for Astronomy (AIfA), University Bonn.
"""

from pymodbus.client import AsyncModbusTcpClient
import asyncio
import re
import logging
from typing import Dict, Any, List
import datetime
# internal
from .mb_client_core_async import _ObjectTypeAsync, FEATURE_ALLOWED_SET
from .mb_client_aux_async import (_client_config, _throw_error, mytimer,
                                  MyException, defined_kwargs, MODBUS2AVRO)

"""
change history
2021/10/20 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.1
2021/10/24 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.2
    * for additional key/value pairs in client mapping pass them through.
2021/10/27 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.3
    * adapted for hk
    * also function passed-through as indicator for data type     
2021/11/01 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.4
    * skip first byte of register if starts with 'xxxxx/2'
2021/11/08 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.5
    * introduce datatype for avro, disregard function for output dictionary
2021/11/11 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.6
    * complete redesign: registers are read consecutively, one-by-one.
    * multiplier & offset are processed for output to hk
2021/11/22 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.7
    * introduce endiannesses of byte- and wordorder
2021/11/24 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 0.8
    * strings of variable length to be decoded as well
2021/11/30 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.0
    * variable filenames
2021/12/18 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 1.1
    * strings modified
2023/02/23 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.0
    * MODBUS client as library for housekeeping purposes
    * merge reader and writer methods
    * pymodbus v3.1.3
2023/03/07 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.1
    * config and mapping files merged
    * number of bytes allocated for integers or floats is checked
    * notify when attempting to write to read-only registers
2023/03/08 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.2
    * assert replaced by sys.exit
    * new modules created from to long code
    * notify if non-existing parameter
    * docstrings
    * error handling
    * replace if by match
    * from __future__ removed
2023/03/19 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.2.1
    * Exception handling when connection to ModbusTcpClient
    * License included
2023/05/16 - Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.2.2
    * PEP8
2023/05/30
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.3.0
    * modified from sys.exit to MyException
2023/06/05
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.4.0
    * register's width and no of byte as defined in Enum
    * comments need to be cleansed next version
2023/06/13
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 2.4.1
    * comments removed
2023/06/30
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 3.0.1
    * client input parameter: ip, port, debug
2023/07/07
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 3.1.1
    * output dict with additional timestamp, ip, and isTag info
2023/07/09
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 3.1.2
    * deploys pymodbus 3.3.2
2023/07/11
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 3.1.3
    * device ip dropdown list in RestAPI serves as validator
2023/07/11
- Ralf A. Timmermann <rtimmermann@astro.uni-bonn.de>
- version 3.1.4
    * check on availability of decode function for classes 3 & 4
    * improved writer for holding registers
    * ip validator

henceforth version history continued in CHANGELOG.md 
"""

__author__ = "Ralf Antonius Timmermann"
__copyright__ = ("Copyright (C) Ralf Antonius Timmermann, "
                 "AIfA, University Bonn")
__credits__ = ""
__license__ = "BSD 3-Clause"
__version__ = "5.3.0"
__maintainer__ = "Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "QA"

myformat = ("%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - "
            "%(lineno)s - %(funcName)s()\t%(message)s")
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")


class MODBUSClientAsync(object):

    def __init__(
            self,
            host: str,
            *,
            port: int = None,
            debug: bool = None,
            timeout_connect: float = None,
            config_filename: str = None
    ):
        """
        initializing the async modbus client and perform integrity checks on
        mb_client_config_<device>.json:
        :param host: device ip or name
        :param port: device port
        :param debug: debug mode (True/False)
        :param timeout_connect: timeout for connecting to server (sec)
        """
        logging.getLogger().setLevel(
            getattr(logging,
                    "DEBUG" if debug else "INFO")
        )
        self._ip = host
        client_config = _client_config(config_filename=config_filename)

        # integrity checks
        self.__client_mapping_checks(mapping=client_config['mapping'])

        self.__client = AsyncModbusTcpClient(
            host=self._ip,
            **defined_kwargs(port=port,
                             debug=debug),
        )
        if timeout_connect:
            self.__client.comm_params.timeout_connect = timeout_connect

        self.__init = {
            "client": self.__client,
            "mapping": client_config['mapping'],
            # if endianness not found, apply default:
            # "byteorder": Endian.Little, "wordorder": Endian.Big
            "endianness": client_config.get("endianness",
                                            {"byteorder": "<",
                                             "wordorder": ">"})
        }
        # initialize _ObjectType objects for each entity
        self.__entity_list: List = list()
        for regs in ['0', '1', '3', '4']:
            self.__entity_list.append(
                _ObjectTypeAsync(
                    init=self.__init,
                    entity=regs
                )
            )

    def __existance_mapping_checks(
            self,
            wr: Dict
    ) -> str:
        """
        check if parameter exists in mapping at all
        :param wr: list of dicts {parameter: value}
        :return: str (empty = no error)
        """
        parms: List = list()
        text = "Parameter {0} not mapped to register"
        for parameter in wr.keys():
            for attributes in self.__init['mapping'].values():
                if attributes['parameter'] == parameter:
                    break
            else:
                parms.append("'{}'".format(parameter))
        if parms:
            return text.format(", ".join(parms))

        return ""

    @staticmethod
    def __client_mapping_checks(mapping: Dict) -> None:
        """
        perform checks on the client mapping: parameter must not be duplicate,
        available features must be taken from README.md
        :param mapping: Dict
        :return:
        """

        def check_register_integrity() -> None:
            """
            check registry integrity of dictionary keys in mapping file
            key formate, e.g. '0xxxx', '3xxxx/3xxxx', or '4xxxx/y,
            where x=0000-9999 and y=1|2
            """
            msg = "Wrong register in mapping: {0}".format(register)
            if not re.match(r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$",
                            register):
                _throw_error(msg, 422)
            comp = register.split("/")
            if len(comp) == 2:
                if (comp[1] not in ["1", "2"]
                    and (comp[0][0] != comp[1][0]  # same register class
                         or int(comp[1]) - int(comp[0]) < 1)):  # ascending
                    _throw_error(msg, 422)

        def check_feature_integrity() -> None:
            if feature not in FEATURE_ALLOWED_SET:
                _throw_error(("Feature '{1}' in register '{0}' is not supported"
                              .format(register, feature)), 422)
            if re.match("(min|max)", feature):  # check features min or max
                if not re.match("(int|long|float|double)", datatype):
                    _throw_error(("Feature min or max not permitted for "
                                  "register '{0}'".format(register)), 422)
                if type(v) not in (int, float):
                    _throw_error(("Feature '{1}' in register '{0}' is not "
                                  "numerical".format(register, feature)), 422)
            if re.match("map", feature):  # check feature map
                if re.match("boolean", datatype):
                    for binarystring in v.keys():
                        if not re.match(r"^0b(?=[01]{8}$)(?=[^1]*1[^1]*$)",
                                        binarystring):
                            _throw_error("Binary string error in map for "
                                         "register '{0}'".format(register),
                                         422)

        def function_available() -> str:
            function = "decode_bits"
            if register[0] in ['3', '4']:  # discrete input or holding
                try:
                    function = value['function']
                    return MODBUS2AVRO(function).datatype
                except ValueError:
                    _throw_error(("Decoding function '{0}' not defined for "
                                  "register '{1}'").format(function,
                                                           register), 422)
                except KeyError:
                    _throw_error(("Decoding function not provided for "
                                  "register '{0}'").format(register), 422)
            return MODBUS2AVRO(function).datatype  # coil & input register

        def parameter_available() -> str:
            try:
                return value["parameter"]
            except KeyError:
                _throw_error(("Feature parameter missing for register '{0}'"
                              .format(register)), 422)

        def seek_parameter_duplicate() -> None:
            parameter_duplicate = [
                reg for reg, parm in rev_dict.items() if len(parm) > 1
            ]
            if parameter_duplicate:
                _throw_error(("Duplicate parameter '{0}'"
                              .format(", ".join(parameter_duplicate))), 422)
        # end nested functions

        rev_dict: Dict = dict()
        for register, value in mapping.items():
            check_register_integrity()
            parameter = parameter_available()
            rev_dict.setdefault(parameter, set()).add(register)
            datatype = function_available()
            for feature, v in value.items():  # investigate features
                check_feature_integrity()
        seek_parameter_duplicate()

    @mytimer
    async def read_register(self) -> Dict[str, Any]:
        """
        invoke the read all mapped registers for monitoring
        :return: List of Dict for housekeeping
        """
        await self.__client.connect()
        if not self.__client.connected:
            _throw_error(("Could not connect to MODBUS server: IP={}"
                         .format(self._ip)), 503)
        logging.debug("MODBUS Communication Parameters: {}"
                      .format(self.__client.comm_params))
        decoded: List = list()
        coros = [entity.register_readout() for entity in self.__entity_list]
        try:
            for item in await asyncio.gather(*coros):
                decoded += item
        except asyncio.CancelledError:
            _throw_error(("Async tasks could not be processed within {} sec. "
                          "Consider to increase value for 'timeout_connect'"
                          .format(self.__client.comm_params.timeout_connect)),
                         504)
        if self.__client.connected:
            self.__client.close()
            logging.debug("Closing {}".format(self.__client))

        return {
            "timestamp": datetime.datetime.now(
                tz=datetime.timezone.utc
            ).isoformat(),
            "host": self._ip,
            "data": decoded
        }

    def __updated_registers(self) -> Dict[str, Any]:
        """
        updated registers for coil and holding after write end or failure
        :return: values of register content
        """
        tmp: Dict = dict()
        for entity in self.__entity_list:
            if entity.entity in ['0', '4']:
                tmp.update(entity.updated_items)
        return tmp

    @mytimer
    async def write_register(
            self,
            wr: Dict
    ) -> Dict[str, str | Dict]:
        """
        invoke the writer to registers, where
        :param wr: list of dicts {parameter: value}
        :return: status
        """
        await self.__client.connect()
        if not self.__client.connected:
            _throw_error(("Could not connect to MODBUS server: IP={}"
                         .format(self._ip)),
                         503)
        logging.debug("MODBUS Communication Parameters: {}"
                      .format(self.__client.comm_params))
        detail = self.__existance_mapping_checks(wr=wr)
        if detail:
            raise MyException(
                status_code=422,
                detail="{0}, updated register content: {1}".format(
                    detail,
                    {}
                )
            )
        try:
            for entity in self.__entity_list:
                await entity.register_write(wr)
        except MyException as e:
            raise MyException(
                status_code=e.status_code,
                detail="{0}, updated register content: {1}".format(
                    e.detail,
                    self.__updated_registers()
                )
            )
        if self.__client.connected:
            self.__client.close()
            logging.debug("Closing {}".format(self.__client))

        return {
            "status": "write success",
            "updated register content": self.__updated_registers()
        }
