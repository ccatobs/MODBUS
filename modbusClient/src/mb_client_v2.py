#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MODBUS Client

For a detailed description, see https://github.com/ccatp/MODBUS
Running and testing:
python3 mb_client_reader_v2.py --ip <device ip address> \
                               [--port <device port (default: 502)] \
                               [--debug]

python3 mb_client_writer_v2.py --ip <device ip address> \
                               [--port <device port (default: 502)] \
                               [--debug] \
                               --payload "{\"test 32 bit int\": 720.04, ...}"

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann,
Argelander Institute for Astronomy (AIfA), University Bonn.
"""

from pymodbus.client import ModbusTcpClient
import re
import logging
from typing import Dict, Any
import datetime
from ipaddress import IPv4Address
from pydantic import BaseModel, ValidationError
# internal
from .mb_client_core import _ObjectType
from .mb_client_aux import mytimer, _client_config, _throw_error, MyException,\
    defined_kwargs

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
__copyright__ = "Copyright (C) Ralf Antonius Timmermann, " \
                "AIfA, University Bonn"
__credits__ = ""
__license__ = "BSD 3-Clause"
__version__ = "3.3.1"
__maintainer__ = "Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "QA"

myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
           "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")


class _IpModel(BaseModel):
    ip: IPv4Address


class MODBUSClient(object):

    def __init__(
            self,
            ip: IPv4Address,
            *,
            port: int = None,
            debug: bool = False
    ):
        """
        initializing the modbus client and perform checks on
        mb_client_config_<device>.json:
        1) format of register key
        2) existance and uniqueness of "parameter"
        3) connection to modbus server via synchronous TCP
        :param ip: str - device ip
        :param port: int - device port
        :param debug: bool - debug mode True/False
        """
        logging.getLogger().setLevel(
            getattr(logging,
                    "DEBUG" if debug else "INFO")
        )
        try:
            self._ip = str(_IpModel(ip=ip).ip)
        except ValidationError:
            detail = "IP value '{0}' is not a valid IPv4 address".format(ip)
            _throw_error(detail)
        client_config = _client_config()

        # integrity checks
        self.__client_mapping_checks(mapping=client_config['mapping'])

        client = ModbusTcpClient(
            host=self._ip,
            debug=debug,
            **defined_kwargs(port=port),
        )
        if not client.connect():
            detail = ("Could not connect to MODBUS server: IP={}"
                      .format(self._ip))
            _throw_error(detail, 503)

        # used for wrapper & output dict
        self.__device = client.comm_params.host
        self.__init = {
            "client": client,
            "mapping": client_config['mapping'],
            # if endianness not found, apply default:
            # "byteorder": Endian.Little, "wordorder": Endian.Big
            "endianness": client_config.get("endianness",
                                            {"byteorder": "<",
                                             "wordorder": ">"})
        }
        # initialize _ObjectType objects for each entity
        self.__entity_list = list()
        for regs in ['0', '1', '3', '4']:
            self.__entity_list.append(
                _ObjectType(
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
        :return: str, empty (no error)
        """
        parms = list()
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

    def __client_mapping_checks(
            self,
            mapping: Dict
    ) -> None:
        """
        perform checks on the client mapping: parameter must not be duplicate
        :param mapping: Dict
        :return:
        """
        rev_dict = dict()
        for key, value in mapping.items():
            if not self.__register_integrity(address=key):
                detail = "Wrong key in mapping: {0}.".format(key)
                _throw_error(detail, 422)
            rev_dict.setdefault(value["parameter"], set()).add(key)
        parameter = [key for key, values in rev_dict.items() if len(values) > 1]
        if parameter:
            detail = "Duplicate parameter: {0}.".format(parameter)
            _throw_error(detail, 422)

    @staticmethod
    def __register_integrity(address: str) -> bool:
        """
        check integrity of dictionary keys in mapping file
        key formate: '0xxxx', '3xxxx/3xxxx', or '4xxxx/y,
        where x=0000-9999 and y=1|2
        :param address: str
        :return: bool = True (NoError)
        """
        if not re.match(r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$", address):
            return False
        comp = address.split("/")
        if len(comp) == 2:
            if comp[1] not in ["1", "2"] and \
                    (comp[0][0] != comp[1][0] or  # test on same register class
                     int(comp[1]) - int(comp[0]) < 1):  # test equal registers

                return False

        return True

    @mytimer
    def read_register(self) -> Dict[str, Any]:
        """
        invoke the read all mapped registers for monitoring
        :return: List of Dict for housekeeping
        """
        return {
            "timestamp": datetime.datetime.now(
                tz=datetime.timezone.utc
            ).isoformat(),
            "ip": self.__device,
            "data": [item for entity in self.__entity_list for item in
                     entity.register_readout()]
        }

    def __updated_registers(self) -> Dict[str, Any]:
        """
        updated registers for coil and holding after write end or failure
        :return: values of register content
        """
        tmp = dict()
        for entity in self.__entity_list:
            if entity.entity in ['0', '4']:
                tmp.update(entity.updated_items)
        return tmp

    @mytimer
    def write_register(
            self,
            wr: Dict
    ) -> Dict[str, str | Dict]:
        """
        invoke the writer to registers, where
        :param wr: list of dicts {parameter: value}
        :return: status
        """
        detail = self.__existance_mapping_checks(wr=wr)
        if detail:
            raise MyException(
                status_code=422,
                detail="{0}, Updated register content: {1}".format(
                    detail,
                    {}
                )
            )

        try:
            for entity in self.__entity_list:
                entity.register_write(wr)
        except MyException as e:
            raise MyException(
                status_code=e.status_code,
                detail="{0}, Updated register content: {1}".format(
                    e.detail,
                    self.__updated_registers()
                )
            )

        return {
            "status": "write success",
            "updated register content": self.__updated_registers()
        }

    def close(self) -> None:
        client = self.__init["client"]
        if client.connect():
            logging.debug("Closing {}".format(client))
            client.close()
