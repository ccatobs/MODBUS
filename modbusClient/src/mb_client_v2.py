#!/usr/bin/env python3

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

from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.client import ModbusTcpClient
import json
import re
import logging
from typing import Dict, List
import datetime
# internal
from .mb_client_aux import mytimer, MyException, MODBUS2AVRO, file_config

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
"""

__author__ = "Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Ralf Antonius Timmermann, " \
                "AIfA, University Bonn"
__credits__ = ""
__license__ = "BSD 3-Clause"
__version__ = "3.1.1"
__maintainer__ = "Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "QA"

myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
           "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

UNIT = 0x1


class _ObjectType(object):

    def __init__(self,
                 init: Dict,
                 entity: str):
        """
        :param init: Dict - client parameter
            init["client"] instance - MODBUS client
            init["mapping"] mapping of all registers as from JSON
            init["endianness"] endianness's of byte and word
        :param entity: str - register prefix
        """
        self.__client = init["client"]
        self.__endianness = init["endianness"]
        self.__entity = entity
        # select mapping for each entity and sort by key
        self.__register_maps = {
            key: value for key, value in
            sorted(init["mapping"].items()) if key[0] == self.__entity
        }

    def __register_width(self, address: str) -> Dict:
        """
        determine the specs for an address
        :param address: string
        :return: Dict
            start - address to start from,
            width - no of 16-bit register
            no_bytes - no of total bytes contained
            pos_byte - position of byte in register (1: leading, 2: trailing)
        """
        width, no_bytes, pos_byte = 1, 2, 1  # default
        comp = address.split("/")
        start = int(comp[0][1:])
        if len(comp) == 2:
            if comp[1] in ["1", "2"]:
                no_bytes = 1
                pos_byte = int(comp[1])
            else:
                width = int(comp[1]) - int(comp[0]) + 1
                no_bytes = width * 2
        function = self.__register_maps[address].get('function')
        if function:
            try:
                if MODBUS2AVRO(function).supersede:
                    width = MODBUS2AVRO.width(function)
                    no_bytes = MODBUS2AVRO.no_bytes(function)
            except ValueError:
                detail = "Decoding function '{}' not defined.".format(function)
                logging.error(detail)
                raise MyException(status_code=422,
                                  detail=detail)
        result = {
            "start": start,
            "width": width,
            "no_bytes": no_bytes,
            "pos_byte": pos_byte
        }
        logging.debug("register:{0} -> {1}".format(address,
                                                   json.dumps(result)))

        return result

    @staticmethod
    def __binary_map(binarystring: str) -> int:
        """
        position of True in binary string. Report if malformated in mapping.
        source for regular expression:
        https://stackoverflow.com/questions/469913/regular-expressions-is-there-an-and-operator
        :param binarystring: str
        :return: int
        """
        if re.match(r"^0b(?=[01]{8}$)(?=[^1]*1[^1]*$)", binarystring):
            return binarystring.split("0b")[1][::-1].index('1')
        else:
            detail = "Error in binary string in mapping."
            logging.error(detail)
            raise MyException(status_code=422,
                              detail=detail)

    def __decode_byte(self,
                      register: str,
                      value: List[bool],
                      function: str) -> List[Dict]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: List[bool] - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict
        """
        decoded = list()
        optional = dict()

        if len(self.__register_maps[register]['map']) == 1:
            # if only one entry in map, add optional parameters, otherwise no
            optional = {
                key: self.__register_maps[register][key]
                for key in self.__register_maps[register]
                if key not in {'map',
                               'description',
                               'value',
                               'function',
                               'parameter',
                               'multiplier',
                               'offset',
                               'datatype',
                               'isTag'}
            }
        for key, name in self.__register_maps[register]['map'].items():
            decoded.append(
                dict(
                    {
                        "parameter":
                            self.__register_maps[register]['parameter'],
                        "value": value[self.__binary_map(binarystring=key)],
                        "description": name,
                        "datatype": MODBUS2AVRO(function).datatype,
                        "isTag": self.__register_maps[register].get('isTag', False)

                    },
                    **optional)
            )

        return decoded

    def __decode_prop(self,
                      register: str,
                      value: str | int | float,
                      function: str) -> List[Dict]:
        """
        decode payload messages from a modbus reponse message and enrich with
        add. parameters from input mapping
        :param register: string - key in dictionary mapping
        :param value: str | int | float - result from payload decoder method
        :param function: string - decoder method
        :return: List of Dict
        """
        maps = self.__register_maps[register].get('map')
        desc = self.__register_maps[register].get('description')
        datatype = MODBUS2AVRO(function).datatype
        optional = {
            key: self.__register_maps[register][key]
            for key in self.__register_maps[register]
            if key not in {'map',
                           'description',
                           'function',
                           'datatype',
                           'multiplier',
                           'offset',
                           'isTag'}
        }
        if datatype in ['int', 'long'] and not maps:
            # multiplier and/or offset make sense for int datatypes and when
            # no map is defined
            multiplier = self.__register_maps[register].get('multiplier', 1)
            offset = self.__register_maps[register].get('offset', 0)
            value = value * multiplier + offset
            if isinstance(value, float):
                datatype = "float"  # to serve Reinhold's AVRO schema
        di = {
            "value": value,
            "datatype": datatype,
            "isTag": self.__register_maps[register].get('isTag', False)
        }
        if maps is not None:
            desc = maps.get(str(round(value)))
        if desc is not None:
            di["description"] = desc

        return [
            dict(
                **di,
                **optional)
        ]

    def __formatter(self,
                    decoder: BinaryPayloadDecoder,
                    register: str,
                    no_bytes: int) -> List[Dict]:
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :param no_bytes: int - no of bytes to decode for strings
        :return: List of Dict
        """
        function = self.__register_maps[register]['function']
        match function:
            case 'decode_bits':
                value = getattr(decoder, function)()
                return self.__decode_byte(register=register,
                                          value=value,
                                          function=function)
            case "decode_string":
                encod = getattr(decoder, function)(no_bytes)
                # ToDo what kind of characters need to be removed?
                # value = re.sub(r'[^\x01-\x7F]+', r'', encod.decode())
                try:
                    value = "".join(
                        list(s for s in encod.decode() if s.isprintable())
                        ).rstrip()
                except UnicodeDecodeError as e:
                    logging.error(str(e))
                    raise MyException(status_code=400,
                                      detail=str(e))
            case _:
                value = getattr(decoder, function)()

        return self.__decode_prop(register=register,
                                  value=value,
                                  function=function)

    def __formatter_bit(self,
                        decoder: List,
                        register: str) -> List[Dict]:
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :return: List of Dict
        """
        return [
            dict(
                **self.__register_maps[register],
                **{"datatype": MODBUS2AVRO("decode_bits").datatype,
                   "value": decoder[0],
                   "isTag": self.__register_maps[register].get('isTag', False)
                   }
            )
        ]

    def __coil(self,
               wr: Dict) -> None:
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    # coil register updates one-by-one
                    rq = self.__client.write_coil(
                        address=int(address),
                        value=value,
                        slave=UNIT)
                    if rq.isError():
                        detail = "Error writing coil register at address " \
                                 "'{0}' with payload '{1}'".format(int(address),
                                                                   value)
                        logging.error(detail)
                        raise MyException(status_code=422,
                                          detail=detail)
                    break

    def __holding(self,
                  wr: Dict) -> None:
        """
        dictionary with "parameter: value" pairs to be changed in coil and
        holding registers
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        builder = BinaryPayloadBuilder(
            byteorder=self.__endianness['byteorder'],
            wordorder=self.__endianness['wordorder']
        )

        for parameter, value in wr.items():
            for address, attributes in self.__register_maps.items():
                if attributes['parameter'] == parameter:
                    # holding register updates
                    function = attributes['function'].replace("decode_", "add_")
                    reg_info = self.__register_width(address)
                    if "int" in function:
                        if "8bit" in function and reg_info['pos_byte'] == 2:
                            detail = "Parameter '{0}': Updates for type " \
                                     "8bit (u)int are disabled for the minor" \
                                     "byte of a register.".format(parameter)
                            logging.error(detail)
                            raise MyException(status_code=422,
                                              detail=detail)
                        multiplier = attributes.get('multiplier', 1)
                        offset = attributes.get('offset', 0)
                        value = int((value - offset) / multiplier)
                    if "string" in function:
                        if len(value) > reg_info['no_bytes']:
                            detail = "'{0}' too long for parameter '{1}'"\
                                .format(value, parameter)
                            logging.error(detail)
                            raise MyException(status_code=422,
                                              detail=detail)
                        # fill entire string with spaces
                        s = list(" " * (2*reg_info['width']))
                        s[reg_info['pos_byte'] - 1] = value
                        value = "".join(s)
                    if "bits" in function:
                        if len(value) / 16 > reg_info['width']:
                            detail = "'{0}' too long for parameter '{1}'"\
                                .format(value, parameter)
                            logging.error(detail)
                            raise MyException(status_code=422,
                                              detail=detail)
                    getattr(builder, function)(value)
                    payload = builder.to_registers()
                    rq = self.__client.write_registers(
                        address=reg_info['start'],
                        values=payload,
                        slave=UNIT)
                    # assert (not rq.isError())  # test we are not an error
                    if rq.isError():
                        detail = "Error writing holding register at " \
                                 "address '{0}' with payload '{1}'".\
                            format(reg_info['start'],
                                   payload)
                        logging.error(detail)
                        raise MyException(status_code=422,
                                          detail=detail)
                    builder.reset()  # reset builder
                    break  # if parameter matched

    def register_readout(self):
        """
        reads the coil discrete input, input, or holding registers according
        to their length defined in key and decodes them accordingly. The
        list of dictionary/ies is appended to the result
        :return: List
        """
        f = None
        decoded = list()

        for key in self.__register_maps.keys():
            reg_info = self.__register_width(key)
            # read appropriate register(s)
            match self.__entity:
                case '0':
                    f = "read_coils"
                case '1':
                    f = "read_discrete_inputs"
                case '3':
                    f = "read_input_registers"
                case '4':
                    f = "read_holding_registers"
            result = getattr(self.__client, f)(
                address=reg_info['start'],
                count=reg_info['width'],
                slave=UNIT)
            # assert (not result.isError())
            if result.isError():
                detail = "Error reading register at address '{0}' and " \
                         "width '{1}' for MODBUS class '{2}'". \
                    format(reg_info['start'],
                           reg_info['width'],
                           self.__entity)
                logging.error(detail)
                raise MyException(status_code=400,
                                  detail=detail)

            # decode and append to list
            if self.__entity in ['0', '1']:
                decoder = result.bits
                decoded = decoded + self.__formatter_bit(
                    decoder=decoder,
                    register=key
                )
            elif self.__entity in ['3', '4']:
                decoder = BinaryPayloadDecoder.fromRegisters(
                    registers=result.registers,
                    byteorder=self.__endianness["byteorder"],
                    wordorder=self.__endianness["wordorder"]
                )
                # skip leading byte, if key = "xxxxx/2"
                # if self.__trailing_byte_check(key):
                if reg_info['pos_byte'] == 2:
                    decoder.skip_bytes(nbytes=1)
                decoded = decoded + self.__formatter(
                    decoder=decoder,
                    register=key,
                    no_bytes=reg_info['no_bytes']
                )

        return decoded

    def register_write(self,
                       wr: Dict) -> None:
        """
        call coil or holding register writes
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        match self.__entity:
            case '4':
                self.__holding(wr=wr)
            case '0':
                self.__coil(wr=wr)
            # when attempting to writing to a read-only register, issue warning
            case _:
                for parameter, value in wr.items():
                    for address, attributes in self.__register_maps.items():
                        if attributes['parameter'] == parameter:
                            logging.warning("Parameter '{0}' of MODBUS "
                                            "register class {1} ignored!".
                                            format(parameter,
                                                   self.__entity))
                            break


class MODBUSClient(object):

    def __init__(
            self,
            ip: str,
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
        self.__device = ip  # used for wrapper
        config_device_class = file_config()
        with open(config_device_class) as config_file:
            client_config = json.load(config_file)
        logging.basicConfig()
        logging.getLogger().setLevel(
            getattr(logging, "DEBUG" if debug else "INFO")
        )
        logging.info("Config File: {0}".format(config_device_class))
        # make integrity checks
        self.__client_mapping_checks(mapping=client_config['mapping'])

        if port:
            client = ModbusTcpClient(
                host=ip,
                port=port,
                debug=debug
            )
        else:
            client = ModbusTcpClient(
                host=ip,
                debug=debug
            )

        if not client.connect():
            detail = "Could not connect to MODBUS server."
            logging.error(detail)
            raise MyException(status_code=503,
                              detail=detail)

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

    def __existance_mapping_checks(self,
                                   wr: Dict) -> str:
        """
        check if parameter exists in mapping at all
        :param wr: list of dicts {parameter: value}
        :return: str, empty (no error)
        """
        parms = list()
        text = "Parameter '{0}' not being mapped to registers!"
        for parameter in wr.keys():
            for attributes in self.__init['mapping'].values():
                if attributes['parameter'] == parameter:
                    break
            else:
                parms.append(parameter)
                logging.warning(text.format(parameter))
        if parms:
            return text.format(", ".join(parms))

        return ""

    def __client_mapping_checks(self,
                                mapping: Dict) -> None:
        """
        perform checks on the client mapping
        parameter must not be duplicate
        :param mapping: Dict
        :return:
        """
        rev_dict = dict()
        for key, value in mapping.items():
            if not self.__register_integrity(address=key):
                detail = "Wrong key in mapping: {0}.".format(key)
                logging.error(detail)
                raise MyException(status_code=422,
                                  detail=detail)
            rev_dict.setdefault(value["parameter"], set()).add(key)
        parameter = [key for key, values in rev_dict.items() if len(values) > 1]
        if parameter:
            detail = "Duplicate parameter: {0}.".format(parameter)
            logging.error(detail)
            raise MyException(status_code=422,
                              detail=detail)

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
    def read_register(self) -> List[Dict]:
        """
        invoke the read all mapped registers for monitoring
        :return: List of Dict (in asc order) for housekeeping
        """
        decoded = list()
        for entity in self.__entity_list:
            decoded = decoded + entity.register_readout()

        return {
            "timestamp": datetime.datetime.now(
                tz=datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%S.%f"),
            "ip": self.__device,
            "data": decoded
        }

    @mytimer
    def write_register(self,
                       wr: Dict) -> Dict:
        """
        invoke the writer to registers, where
        :param wr: list of dicts {parameter: value}
        :return: Dict, returns the input unchanged
        """
        detail = self.__existance_mapping_checks(wr=wr)
        if detail != "":
            raise MyException(status_code=422,
                              detail=detail)
        for entity in self.__entity_list:
            entity.register_write(wr)

        return {"status": "success"}

    def close(self) -> None:
        client = self.__init.get("client")
        if client:
            logging.debug("Closing {}".format(client))
            client.close()
