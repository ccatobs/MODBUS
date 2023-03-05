#!/usr/bin/env python3
"""
MODBUS Client, version 2.0 - 2023/02/22

For a detailed description, see https://github.com/ccatp/MODBUS

For running and testing

python3 mb_client_reader_v2.py --device <device extention> (default: default) \
                               --path <path to config files> (default: .)

python3 mb_client_writer_v2.py --device <device extention> (default: default) \
                               --path <path to config files> (default: .) \
                               --payload "{\"test 32 bit int\": 720.04, ...}"

Copyright (C) 2021-23 Dr. Ralf Antonius Timmermann,
Argelander Institute for Astronomy (AIfA), University Bonn.
"""

from __future__ import annotations
from pymodbus.payload import BinaryPayloadDecoder, BinaryPayloadBuilder
from pymodbus.client import ModbusTcpClient as ModbusTcpClient
import pymodbus.exceptions
import json
import re
import sys
import logging
from os import path
from typing import Dict, List
# internal
from mb_client_aux import mytimer

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
2021/11/30
- version 1.0
    * variable filenames
2021/12/18
- version 1.1
    * strings modified
2023/02/23
-version 2.0
    * MODBUS client as library for housekeeping purposes
    * merge reader and writer methods
    * pymodbus v3.1.3
"""

__author__ = "Dr. Ralf Antonius Timmermann"
__copyright__ = "Copyright (C) Dr. Ralf Antonius Timmermann, AIfA, University Bonn"
__credits__ = ""
__license__ = "BSD-3"
__version__ = "2.0"
__maintainer__ = "Dr. Ralf Antonius Timmermann"
__email__ = "rtimmermann@astro.uni-bonn.de"
__status__ = "Dev"

myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: " \
           "%(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")

UNIT = 0x1
FUNCTION2AVRO = {
    "decode_bits": "boolean",
    "decode_8bit_int": "int",
    "decode_8bit_uint": "int",
    "decode_16bit_int": "int",
    "decode_16bit_uint": "int",
    "decode_16bit_float": "float",
    "decode_32bit_int": "int",
    "decode_32bit_uint": "int",
    "decode_32bit_float": "float",
    "decode_64bit_int": "long",
    "decode_64bit_uint": "long",
    "decode_64bit_float": "double",
    "decode_string": "string"
}


class _MappingKeyError(Exception):
    """Base class for other exceptions"""
    pass


class _DuplicateParameterError(Exception):
    """Base class for other exceptions"""
    pass


class _ObjectType(object):

    def __init__(self, init: Dict, entity: str):
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

    @staticmethod
    def __register_width(address: str) -> Dict:
        """
        determine the number of registers to read for a given key
        :param address: string
        :return: Dict
            start - address to start from,
            width - byte widths
            no_bytes - no of total bytes contained
            pos_byte - position of the byte to extract
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
        result = {
            "start": start,
            "width": width,
            "no_bytes": no_bytes,
            "pos_byte": pos_byte
        }
        logging.debug("register:{0} -> {1}".format(address, json.dumps(result)))

        return result

    @staticmethod
    def __binary_map(binarystring: str) -> int:
        """
        position of True in binary string. Report if malformated in mapping.
        source for regular expression:
        https://stackoverflow.com/questions/469913/regular-expressions-is-there-an-and-operator
        :param binarystring: str
        :return: integer
        """
        if re.match(r"^0b(?=[01]{8}$)(?=[^1]*1[^1]*$)", binarystring):
            return binarystring.split("0b")[1][::-1].index('1')
        else:
            logging.error("Error in binary string in mapping.")
            sys.exit(500)

    @staticmethod
    def __trailing_byte_check(address: str) -> bool:
        if len(address.split("/")) == 2:
            return address.split("/")[1] == "2"
        return False

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
                               'datatype'}
            }
        else:
            optional = dict()
        for key, name in self.__register_maps[register]['map'].items():
            decoded.append(dict(
                {
                    "parameter":
                        self.__register_maps[register]['parameter'],
                    "value": value[self.__binary_map(binarystring=key)],
                    "description": name,
                    "datatype": FUNCTION2AVRO[function]
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
        datatype = FUNCTION2AVRO[function]
        optional = {
            key: self.__register_maps[register][key]
            for key in self.__register_maps[register]
            if key not in {'map',
                           'description',
                           'function',
                           'datatype',
                           'multiplier',
                           'offset'}
        }
        if datatype in ['int', 'long'] and not maps:
            # multiplier and/or offset make sense for int datatypes and when
            # no map is defined
            multiplier = self.__register_maps[register].get('multiplier', 1)
            offset = self.__register_maps[register].get('offset', 0)
            value = value * multiplier + offset
            if isinstance(value, float):
                datatype = "float"
        di = {"value": value,
              "datatype": datatype}
        if maps is not None:
            desc = maps.get(str(round(value)))
        if desc is not None:
            di["description"] = desc

        return [dict(**di, **optional)]

    def __formatter(self,
                    decoder: pymodbus.payload.BinaryPayloadDecoder,
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
        if function not in FUNCTION2AVRO:
            logging.error("Decoding function not defined.")
            sys.exit(500)
        if function == 'decode_bits':
            value = getattr(decoder, function)()
            return self.__decode_byte(register=register,
                                      value=value,
                                      function=function)
        elif function == "decode_string":
            encod = getattr(decoder, function)(no_bytes)
            # ToDo what kind of characters need to be removed?
            # value = re.sub(r'[^\x01-\x7F]+', r'', encod.decode())
            try:
                value = "".join(
                    list(s for s in encod.decode() if s.isprintable())
                    ).rstrip()
            except UnicodeDecodeError as e:
                logging.error(str(e))
                sys.exit(500)
        else:
            value = getattr(decoder, function)()

        return self.__decode_prop(register=register,
                                  value=value,
                                  function=function)

    def __formatter_bit(self, decoder: List, register: str) -> List[Dict]:
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: str
        :return: List of Dict
        """
        return [
            dict(
                **self.__register_maps[register],
                **{"datatype": FUNCTION2AVRO["decode_bits"],
                   "value": decoder[0]}
            )
        ]

    def __holding(self, wr: Dict) -> int:
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
                        multiplier = attributes.get('multiplier', 1)
                        offset = attributes.get('offset', 0)
                        value = int((value - offset) / multiplier)
                    if "string" in function:
                        if len(value) > reg_info['no_bytes']:
                            logging.error("'{0}' too long for parameter '{1}'".format(value, parameter))
                            sys.exit(500)
                        # fill entire string with spaces
                        s = list(" " * (2*reg_info['width']))
                        s[reg_info['pos_byte'] - 1] = value
                        value = "".join(s)
                    if "bits" in function:
                        if len(value) / 16 > reg_info['width']:
                            logging.error("'{0}' too long for parameter '{1}'".format(value, parameter))
                            sys.exit(500)
                    getattr(builder, function)(value)
                    payload = builder.to_registers()
                    rq = self.__client.write_registers(
                        address=reg_info['start'],
                        values=payload,
                        slave=UNIT)
                    assert (not rq.isError())  # test we are not an error
                    builder.reset()  # reset builder
                    break  # if parameter matched

        return 0

    def register_readout(self):
        """
        reads the coil discrete input, input, or holding registers according
        to their length defined in key and decodes them accordingly. The
        list of dictionary/ies is appended to the result
        :return: List
        """
        result = None
        decoded = list()

        for key in self.__register_maps.keys():
            reg_info = self.__register_width(key)
            # read appropriate register(s)
            if self.__entity == '0':
                result = self.__client.read_coils(
                    address=reg_info['start'],
                    count=1,
                    slave=UNIT
                )
            elif self.__entity == '1':
                result = self.__client.read_discrete_inputs(
                    address=reg_info['start'],
                    count=1,
                    slave=UNIT
                )
            elif self.__entity == '3':
                result = self.__client.read_input_registers(
                    address=reg_info['start'],
                    count=reg_info['width'],
                    slave=UNIT
                )
            elif self.__entity == '4':
                result = self.__client.read_holding_registers(
                    address=reg_info['start'],
                    count=reg_info['width'],
                    slave=UNIT
                )
            assert (not result.isError())
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
                if self.__trailing_byte_check(key):
                    decoder.skip_bytes(nbytes=1)
                decoded = decoded + self.__formatter(
                    decoder=decoder,
                    register=key,
                    no_bytes=reg_info['no_bytes']
                )

        return decoded

    def register_write(self, wr: Dict) -> int:
        """
        call coil or holding register writes
        :param wr: dictionary with {parameter: value} pairs
        :return:
        """
        if self.__entity == '4':
            self.__holding(wr=wr)

        elif self.__entity == '0':
            for parameter, value in wr.items():
                for address, attributes in self.__register_maps.items():
                    if attributes['parameter'] == parameter:
                        # coil register updates one-by-one
                        rq = self.__client.write_coil(
                            address=int(address),
                            value=value,
                            slave=UNIT)
                        assert (not rq.isError())  # test we are not an error
                        break

        return 0


class MODBUSClient(object):

    def __init__(self, device: str = "default", **kwargs):
        """
        initializing the modbus client and perform checks on
        mb_client_mapping_<device>.json:
        1) format of register key
        2) existance and uniqueness of "parameter"
        3) connection to modbus server via synchronous TCP
        :return:
        object - modbus client
        dictionary - mapping
        """
        self.__device = device
        path_additional = kwargs.get("path_additional")
        path_additional = path_additional.rstrip('/') if path_additional is not None else "."
        file_config = "{1}/mb_client_config_{0}.json".format(device,
                                                             path_additional)
        file_mapping = "{1}/mb_client_mapping_{0}.json".format(device,
                                                               path_additional)
        # verify existance of both files
        if not path.isfile(file_config):
            logging.error("Client config file {0} not found".format(
                file_config))
            sys.exit(404)
        if not path.isfile(file_mapping):
            logging.error("Client config file {0} not found".format(
                file_mapping))
            sys.exit(404)
        with open(file_config) as config_file:
            client_config = json.load(config_file)
        with open(file_mapping) as json_file:
            mapping = json.load(json_file)
        logging.info("Config File: {0} and Mapping File: {1}".format(file_config, file_mapping))
        # logging toggle debug (default INFO)
        debug = client_config.get('debug', False)
        logging.getLogger().setLevel(getattr(logging, "DEBUG" if debug else "INFO"))

        # make integrity checks
        self.__client_mapping_checks(mapping=mapping)

        try:
            client = ModbusTcpClient(host=client_config["server"]["listenerAddress"],
                                     port=client_config["server"]["listenerPort"],
                                     debug=debug)
            if not client.connect():
                raise pymodbus.exceptions.ConnectionException
        #    client.de
        except pymodbus.exceptions.ConnectionException:
            logging.error("Could not connect to server.")
            sys.exit(503)

        self.__init = {
            "client": client,
            "mapping": mapping,
            # if endianness not found, apply default:
            # "byteorder": Endian.Big, "wordorder": Endian.Big
            "endianness": client_config.get("endianness",
                                            {"byteorder": ">",
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

    def __client_mapping_checks(self, mapping: Dict) -> None:
        """
        perform checks on the client mapping
        parameter must not be duplicate
        :param mapping: Dict
        :return:
        """
        rev_dict = dict()
        key = None
        parameter = None
        try:
            for key, value in mapping.items():
                if not self.__register_integrity(address=key):
                    raise _MappingKeyError
                rev_dict.setdefault(value["parameter"], set()).add(key)
            parameter = [key for key, values in rev_dict.items()
                         if len(values) > 1]
            if parameter:
                raise _DuplicateParameterError
        except _MappingKeyError:
            logging.error("Wrong key in mapping: {0}.".format(key))
            sys.exit(500)
        except _DuplicateParameterError:
            logging.error("Duplicate parameter: {0}.".format(parameter))
            sys.exit(500)

    @staticmethod
    def __register_integrity(address: str) -> bool:
        """
        check integrity of dictionary keys in mapping file
        key formate: '0xxxx', '3xxxx/3xxxx', or '4xxxx/y, where x=0000-9999 and y=1|2
        :param address: str
        :return: bool
        """
        if not re.match(r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$", address):
            return False
        comp = address.split("/")
        if len(comp) == 2:
            if comp[1] not in ["1", "2"] and \
                    (comp[0][0] != comp[1][0] or
                     int(comp[1]) - int(comp[0]) < 1):
                return False
        return True

    @mytimer
    def read_register(self) -> List[Dict]:
        """
        invoke for monitoring
        :return: List of Dict (in asc order) for housekeeping
        """
        decoded = list()
        try:
            for entity in self.__entity_list:
                decoded = decoded + entity.register_readout()
        except SystemExit as e:
            sys.exit(e.code)
        return [dict(sorted(item.items())) for item in decoded]

    @mytimer
    def write_register(self, wr: Dict) -> None:
        """
        invoke for writing to registers
        :param wr: list of dicts {parameter: value} to write to register
        :return:
        """
        try:
            for entity in self.__entity_list:
                entity.register_write(wr)
        except SystemExit as e:
            sys.exit(e.code)

    def close(self):
        client = self.__init.get("client")
        if client:
            logging.debug("Closing {}".format(client))
            client.close()
